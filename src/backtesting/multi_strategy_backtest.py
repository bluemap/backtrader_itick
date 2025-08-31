"""
多策略回测管理器

支持同时回测多个策略并汇总结果
"""

import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

from ..backtesting.backtest_manager import BacktestManager


class MultiStrategyBacktest:
    """多策略回测管理器"""
    
    def __init__(self, config_manager, data_provider):
        """
        初始化多策略回测管理器
        
        Args:
            config_manager: 配置管理器
            data_provider: 数据提供者
        """
        self.config_manager = config_manager
        self.data_provider = data_provider
        self.logger = logging.getLogger(__name__)
        
        # 单策略回测管理器
        self.backtest_manager = BacktestManager(config_manager, data_provider)
        
        self.logger.info("多策略回测管理器初始化完成")
    
    def run_multi_strategy_backtest(self, 
                                    days: int = 30,
                                    initial_cash: float = 100000,
                                    parallel: bool = True,
                                    save_results: bool = True) -> Dict[str, Any]:
        """
        运行多策略回测
        
        Args:
            days: 回测天数
            initial_cash: 初始资金
            parallel: 是否并行执行
            save_results: 是否保存结果
            
        Returns:
            Dict[str, Any]: 回测结果
        """
        try:
            self.logger.info("开始多策略回测...")
            
            # 获取策略配置
            strategies = self.config_manager.get_multi_strategies_config()
            strategy_management = self.config_manager.get_strategy_management_config()
            
            if not strategies:
                return {"status": "error", "error": "没有配置策略"}
            
            # 过滤启用的策略
            enabled_strategies = [s for s in strategies if s.enabled]
            if not enabled_strategies:
                return {"status": "error", "error": "没有启用的策略"}
            
            self.logger.info(f"准备回测 {len(enabled_strategies)} 个策略")
            
            # 执行回测
            if parallel:
                results = self._run_parallel_backtest(enabled_strategies, days, initial_cash)
            else:
                results = self._run_sequential_backtest(enabled_strategies, days, initial_cash)
            
            # 汇总结果
            summary = self._summarize_results(results, strategy_management)
            
            # 保存结果
            if save_results:
                self._save_results(summary)
            
            self.logger.info("多策略回测完成")
            return summary
            
        except Exception as e:
            self.logger.error(f"多策略回测失败: {e}")
            return {"status": "error", "error": str(e)}
    
    def _run_parallel_backtest(self, strategies: List, days: int, initial_cash: float) -> Dict[str, Any]:
        """并行执行回测"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=min(len(strategies), 4)) as executor:
            # 提交回测任务
            future_to_strategy = {
                executor.submit(self._backtest_single_strategy, strategy, days, initial_cash): strategy
                for strategy in strategies
            }
            
            # 收集结果
            for future in as_completed(future_to_strategy):
                strategy = future_to_strategy[future]
                try:
                    result = future.result()
                    results[strategy.name] = result
                    self.logger.info(f"策略 {strategy.name} 回测完成")
                except Exception as e:
                    self.logger.error(f"策略 {strategy.name} 回测失败: {e}")
                    results[strategy.name] = {"status": "error", "error": str(e)}
        
        return results
    
    def _run_sequential_backtest(self, strategies: List, days: int, initial_cash: float) -> Dict[str, Any]:
        """顺序执行回测"""
        results = {}
        
        for strategy in strategies:
            try:
                self.logger.info(f"开始回测策略: {strategy.name}")
                result = self._backtest_single_strategy(strategy, days, initial_cash)
                results[strategy.name] = result
                self.logger.info(f"策略 {strategy.name} 回测完成")
            except Exception as e:
                self.logger.error(f"策略 {strategy.name} 回测失败: {e}")
                results[strategy.name] = {"status": "error", "error": str(e)}
        
        return results
    
    def _backtest_single_strategy(self, strategy, days: int, initial_cash: float) -> Dict[str, Any]:
        """回测单个策略"""
        try:
            # 计算策略分配的资金
            strategy_capital = self._calculate_strategy_capital(strategy, initial_cash)
            
            # 为每个股票执行回测
            stock_results = []
            total_return = 0
            total_trades = 0
            win_trades = 0
            
            for symbol in self._get_strategy_symbols(strategy):
                try:
                    # 执行单只股票的回测
                    result = self.backtest_manager.run_backtest(
                        symbol=symbol,
                        strategy=strategy.type,
                        days=days,
                        initial_cash=strategy_capital / len(self._get_strategy_symbols(strategy)),
                        strategy_params=strategy.parameters
                    )
                    
                    if result.get('status') == 'success':
                        stock_results.append(result)
                        total_return += result.get('total_return_pct', 0)
                        total_trades += result.get('total_trades', 0)
                        win_trades += result.get('winning_trades', 0)
                    
                except Exception as e:
                    self.logger.error(f"回测 {symbol} 失败: {e}")
            
            # 汇总策略结果
            if stock_results:
                avg_return = total_return / len(stock_results)
                win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
                
                return {
                    "status": "success",
                    "strategy_name": strategy.name,
                    "strategy_type": strategy.type,
                    "allocated_capital": strategy_capital,
                    "stock_count": len(self._get_strategy_symbols(strategy)),
                    "successful_stocks": len(stock_results),
                    "average_return_pct": avg_return,
                    "total_trades": total_trades,
                    "winning_trades": win_trades,
                    "win_rate": win_rate,
                    "stock_results": stock_results
                }
            else:
                return {
                    "status": "error",
                    "error": "没有成功的回测结果"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _get_strategy_symbols(self, strategy) -> List[str]:
        """获取策略的股票符号列表"""
        if strategy.stock_pool and 'symbols' in strategy.stock_pool:
            return strategy.stock_pool['symbols']
        else:
            # 使用全局股票池
            global_pool = self.config_manager.get_global_stock_pool()
            return global_pool.get('symbols', [])
    
    def _calculate_strategy_capital(self, strategy, total_capital: float) -> float:
        """计算策略分配的资金"""
        try:
            allocation = strategy.capital_allocation
            
            if not allocation:
                # 默认平均分配
                return total_capital / 3  # 假设最多3个策略
            
            if 'percentage' in allocation:
                return total_capital * (allocation['percentage'] / 100)
            elif 'amount' in allocation:
                return min(allocation['amount'], total_capital)
            else:
                return total_capital / 3
                
        except Exception as e:
            self.logger.error(f"计算策略资金分配失败: {e}")
            return total_capital / 3
    
    def _summarize_results(self, results: Dict[str, Any], strategy_management) -> Dict[str, Any]:
        """汇总回测结果"""
        try:
            successful_strategies = [r for r in results.values() if r.get('status') == 'success']
            failed_strategies = [r for r in results.values() if r.get('status') == 'error']
            
            if not successful_strategies:
                return {
                    "status": "error",
                    "error": "所有策略回测都失败了",
                    "failed_count": len(failed_strategies)
                }
            
            # 计算整体统计
            total_capital = sum(r.get('allocated_capital', 0) for r in successful_strategies)
            total_return = sum(r.get('average_return_pct', 0) * r.get('allocated_capital', 0) 
                             for r in successful_strategies) / total_capital if total_capital > 0 else 0
            total_trades = sum(r.get('total_trades', 0) for r in successful_strategies)
            total_wins = sum(r.get('winning_trades', 0) for r in successful_strategies)
            overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
            
            # 策略排名
            strategy_ranking = sorted(
                successful_strategies, 
                key=lambda x: x.get('average_return_pct', 0), 
                reverse=True
            )
            
            # 风险分析
            returns = [r.get('average_return_pct', 0) for r in successful_strategies]
            risk_metrics = self._calculate_risk_metrics(returns)
            
            summary = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "total_strategies": len(results),
                "successful_strategies": len(successful_strategies),
                "failed_strategies": len(failed_strategies),
                
                # 整体表现
                "overall_performance": {
                    "total_allocated_capital": total_capital,
                    "weighted_average_return_pct": total_return,
                    "total_trades": total_trades,
                    "winning_trades": total_wins,
                    "overall_win_rate": overall_win_rate
                },
                
                # 风险指标
                "risk_metrics": risk_metrics,
                
                # 策略排名
                "strategy_ranking": [
                    {
                        "rank": i + 1,
                        "strategy_name": s.get('strategy_name'),
                        "strategy_type": s.get('strategy_type'),
                        "return_pct": s.get('average_return_pct', 0),
                        "win_rate": s.get('win_rate', 0),
                        "trades": s.get('total_trades', 0)
                    }
                    for i, s in enumerate(strategy_ranking)
                ],
                
                # 详细结果
                "detailed_results": results,
                
                # 推荐
                "recommendations": self._generate_recommendations(strategy_ranking, risk_metrics)
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"汇总结果失败: {e}")
            return {"status": "error", "error": str(e)}
    
    def _calculate_risk_metrics(self, returns: List[float]) -> Dict[str, float]:
        """计算风险指标"""
        try:
            if not returns:
                return {}
            
            import numpy as np
            
            returns_array = np.array(returns)
            
            metrics = {
                "average_return": float(np.mean(returns_array)),
                "volatility": float(np.std(returns_array)),
                "max_return": float(np.max(returns_array)),
                "min_return": float(np.min(returns_array)),
                "sharpe_ratio": float(np.mean(returns_array) / np.std(returns_array)) if np.std(returns_array) > 0 else 0
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"计算风险指标失败: {e}")
            return {}
    
    def _generate_recommendations(self, strategy_ranking: List[Dict], risk_metrics: Dict) -> List[str]:
        """生成投资建议"""
        recommendations = []
        
        try:
            if not strategy_ranking:
                return ["没有成功的策略可以推荐"]
            
            # 最佳策略
            best_strategy = strategy_ranking[0]
            recommendations.append(f"🏆 推荐策略: {best_strategy.get('strategy_name')} "
                                 f"({best_strategy.get('strategy_type')}) - "
                                 f"收益率: {best_strategy.get('return_pct', 0):.2f}%")
            
            # 风险评估
            volatility = risk_metrics.get('volatility', 0)
            if volatility > 10:
                recommendations.append("⚠️ 策略波动性较高，建议适当降低仓位")
            elif volatility < 3:
                recommendations.append("✅ 策略波动性较低，风险可控")
            
            # 胜率评估
            best_win_rate = best_strategy.get('win_rate', 0)
            if best_win_rate > 60:
                recommendations.append("✅ 最佳策略胜率较高，可考虑增加投入")
            elif best_win_rate < 40:
                recommendations.append("⚠️ 最佳策略胜率偏低，建议谨慎投资")
            
            # 多样化建议
            if len(strategy_ranking) > 1:
                top_2_strategies = strategy_ranking[:2]
                recommendations.append(f"💡 建议组合投资: {top_2_strategies[0].get('strategy_name')} + "
                                     f"{top_2_strategies[1].get('strategy_name')} 以分散风险")
            
        except Exception as e:
            self.logger.error(f"生成建议失败: {e}")
            recommendations.append("生成建议时出错")
        
        return recommendations
    
    def _save_results(self, summary: Dict[str, Any]):
        """保存回测结果"""
        try:
            # 创建结果目录
            results_dir = "backtest_results"
            os.makedirs(results_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"multi_strategy_backtest_{timestamp}.json"
            filepath = os.path.join(results_dir, filename)
            
            # 保存为JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"多策略回测结果已保存: {filepath}")
            
        except Exception as e:
            self.logger.error(f"保存回测结果失败: {e}")
    
    def compare_strategies(self, strategy_names: List[str] = None, 
                          days: int = 30, 
                          metrics: List[str] = None) -> Dict[str, Any]:
        """
        策略对比分析
        
        Args:
            strategy_names: 要对比的策略名称，None表示所有策略
            days: 回测天数
            metrics: 对比指标
            
        Returns:
            Dict[str, Any]: 对比结果
        """
        try:
            if metrics is None:
                metrics = ['return_pct', 'win_rate', 'total_trades', 'volatility']
            
            # 运行回测
            backtest_result = self.run_multi_strategy_backtest(days=days, save_results=False)
            
            if backtest_result.get('status') != 'success':
                return backtest_result
            
            # 提取对比数据
            comparison_data = []
            for strategy_result in backtest_result.get('detailed_results', {}).values():
                if strategy_result.get('status') == 'success':
                    if strategy_names is None or strategy_result.get('strategy_name') in strategy_names:
                        comparison_data.append(strategy_result)
            
            # 生成对比表
            comparison_table = self._create_comparison_table(comparison_data, metrics)
            
            return {
                "status": "success",
                "comparison_table": comparison_table,
                "summary": backtest_result.get('overall_performance'),
                "recommendations": self._generate_comparison_recommendations(comparison_data)
            }
            
        except Exception as e:
            self.logger.error(f"策略对比失败: {e}")
            return {"status": "error", "error": str(e)}
    
    def _create_comparison_table(self, strategies: List[Dict], metrics: List[str]) -> Dict[str, Any]:
        """创建策略对比表"""
        try:
            table = {
                "headers": ["策略名称", "策略类型"] + metrics,
                "rows": []
            }
            
            for strategy in strategies:
                row = [
                    strategy.get('strategy_name', 'Unknown'),
                    strategy.get('strategy_type', 'Unknown')
                ]
                
                for metric in metrics:
                    if metric == 'return_pct':
                        row.append(f"{strategy.get('average_return_pct', 0):.2f}%")
                    elif metric == 'win_rate':
                        row.append(f"{strategy.get('win_rate', 0):.1f}%")
                    elif metric == 'total_trades':
                        row.append(str(strategy.get('total_trades', 0)))
                    elif metric == 'volatility':
                        # 这里可以添加波动率计算
                        row.append("N/A")
                    else:
                        row.append(str(strategy.get(metric, 'N/A')))
                
                table["rows"].append(row)
            
            return table
            
        except Exception as e:
            self.logger.error(f"创建对比表失败: {e}")
            return {"headers": [], "rows": []}
    
    def _generate_comparison_recommendations(self, strategies: List[Dict]) -> List[str]:
        """生成对比建议"""
        recommendations = []
        
        try:
            if not strategies:
                return ["没有策略数据可供对比"]
            
            # 按收益率排序
            sorted_by_return = sorted(strategies, key=lambda x: x.get('average_return_pct', 0), reverse=True)
            
            # 按胜率排序
            sorted_by_winrate = sorted(strategies, key=lambda x: x.get('win_rate', 0), reverse=True)
            
            recommendations.append(f"📈 收益率最高: {sorted_by_return[0].get('strategy_name')} "
                                 f"({sorted_by_return[0].get('average_return_pct', 0):.2f}%)")
            
            recommendations.append(f"🎯 胜率最高: {sorted_by_winrate[0].get('strategy_name')} "
                                 f"({sorted_by_winrate[0].get('win_rate', 0):.1f}%)")
            
            # 如果收益率最高和胜率最高是不同策略
            if sorted_by_return[0].get('strategy_name') != sorted_by_winrate[0].get('strategy_name'):
                recommendations.append("💡 建议: 可以考虑组合使用收益率最高和胜率最高的策略")
            
        except Exception as e:
            self.logger.error(f"生成对比建议失败: {e}")
        
        return recommendations