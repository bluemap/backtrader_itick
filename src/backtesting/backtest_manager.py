"""
回测管理器

提供高级回测接口和结果管理
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .backtest_engine import BacktestEngine
from .backtest_result import BacktestResult
from ..data.data_types import KlineData


class BacktestManager:
    """回测管理器"""
    
    def __init__(self, config_manager=None, data_provider=None):
        """
        初始化回测管理器
        
        Args:
            config_manager: 配置管理器
            data_provider: 数据提供者
        """
        self.config_manager = config_manager
        self.data_provider = data_provider
        self.logger = logging.getLogger(__name__)
        
        self.backtest_engine = BacktestEngine(config_manager)
        
        # 结果存储
        self.results_dir = "backtest_results"
        os.makedirs(self.results_dir, exist_ok=True)
    
    def run_backtest(self,
                    symbol: str,
                    strategy: str,
                    days: int = 30,
                    initial_cash: float = 100000,
                    strategy_params: Dict[str, Any] = None,
                    **kwargs) -> Dict[str, Any]:
        """
        运行回测（兼容多策略调用）
        
        Args:
            symbol: 股票代码
            strategy: 策略名称
            days: 回测天数
            initial_cash: 初始资金
            strategy_params: 策略参数
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 回测结果
        """
        try:
            if strategy_params is None:
                strategy_params = {}
            
            # 调用原有的回测方法
            result = self.run_strategy_backtest(
                symbol=symbol,
                strategy_name=strategy,
                days=days,
                initial_cash=initial_cash,
                **strategy_params
            )
            
            if result:
                # 计算最终总价值
                final_value = result.final_cash + result.final_position_value
                
                # 转换为标准格式
                return {
                    "status": "success",
                    "symbol": symbol,
                    "strategy": strategy,
                    "total_return_pct": result.total_return_pct,
                    "total_trades": result.total_trades,
                    "winning_trades": result.winning_trades,
                    "win_rate": result.win_rate,
                    "max_drawdown": result.max_drawdown_pct,
                    "sharpe_ratio": result.sharpe_ratio or 0,
                    "final_value": final_value,
                    "initial_cash": result.initial_cash,
                    "details": result
                }
            else:
                return {
                    "status": "error",
                    "error": f"回测 {symbol} - {strategy} 失败"
                }
                
        except Exception as e:
            self.logger.error(f"回测失败: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def run_strategy_backtest(self,
                            symbol: str,
                            strategy_name: str,
                            days: int = 30,
                            initial_cash: float = 100000,
                            **strategy_params) -> Optional[BacktestResult]:
        """
        运行策略回测
        
        Args:
            symbol: 股票代码
            strategy_name: 策略名称
            days: 回测天数
            initial_cash: 初始资金
            **strategy_params: 策略参数
            
        Returns:
            Optional[BacktestResult]: 回测结果
        """
        try:
            self.logger.info(f"开始回测 {symbol} - {strategy_name} ({days}天)")
            
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 获取历史数据
            kline_data = self._get_historical_data(symbol, start_date, end_date)
            if not kline_data:
                self.logger.error(f"无法获取 {symbol} 的历史数据")
                return None
            
            # 运行回测
            result = self.backtest_engine.run_backtest(
                symbol=symbol,
                strategy_name=strategy_name,
                start_date=start_date,
                end_date=end_date,
                kline_data=kline_data,
                initial_cash=initial_cash,
                **strategy_params
            )
            
            # 保存结果
            self._save_result(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"回测失败: {e}")
            return None
    
    def run_multi_symbol_backtest(self,
                                symbols: List[str],
                                strategy_name: str,
                                days: int = 30,
                                initial_cash: float = 100000,
                                **strategy_params) -> List[BacktestResult]:
        """
        运行多股票回测
        
        Args:
            symbols: 股票代码列表
            strategy_name: 策略名称
            days: 回测天数
            initial_cash: 初始资金
            **strategy_params: 策略参数
            
        Returns:
            List[BacktestResult]: 回测结果列表
        """
        results = []
        
        for symbol in symbols:
            self.logger.info(f"回测股票: {symbol}")
            result = self.run_strategy_backtest(
                symbol=symbol,
                strategy_name=strategy_name,
                days=days,
                initial_cash=initial_cash,
                **strategy_params
            )
            
            if result:
                results.append(result)
        
        # 生成汇总报告
        if results:
            self._generate_summary_report(results, strategy_name)
        
        return results
    
    def run_multi_strategy_backtest(self,
                                  symbol: str,
                                  strategies: List[Dict[str, Any]],
                                  days: int = 30,
                                  initial_cash: float = 100000) -> List[BacktestResult]:
        """
        运行多策略回测
        
        Args:
            symbol: 股票代码
            strategies: 策略配置列表，格式: [{'name': '策略名', 'params': {...}}]
            days: 回测天数
            initial_cash: 初始资金
            
        Returns:
            List[BacktestResult]: 回测结果列表
        """
        results = []
        
        for strategy_config in strategies:
            strategy_name = strategy_config['name']
            strategy_params = strategy_config.get('params', {})
            
            self.logger.info(f"回测策略: {strategy_name}")
            result = self.run_strategy_backtest(
                symbol=symbol,
                strategy_name=strategy_name,
                days=days,
                initial_cash=initial_cash,
                **strategy_params
            )
            
            if result:
                results.append(result)
        
        # 生成策略对比报告
        if results:
            self._generate_strategy_comparison(results, symbol)
        
        return results
    
    def _get_historical_data(self, symbol: str, start_date: datetime, end_date: datetime) -> List[KlineData]:
        """获取历史数据 - 只使用真实iTick数据"""
        if not self.data_provider:
            raise ValueError("数据提供者未初始化")
        
        try:
            # 直接使用iTick数据提供者
            if hasattr(self.data_provider, 'itick_provider'):
                # 如果是RateLimitedProvider，使用其iTick提供者
                provider = self.data_provider.itick_provider
            else:
                # 如果是ItickDataProvider，直接使用
                provider = self.data_provider
            
            self.logger.info(f"使用iTick API获取 {symbol} 历史数据")
            
            # 尝试获取真实历史数据
            kline_data = provider.get_historical_klines(
                symbol=symbol,
                timeframe="1d",
                start_date=start_date,
                end_date=end_date,
                limit=1000
            )
            
            if not kline_data:
                raise Exception(f"无法获取 {symbol} 的真实历史数据")
            
            if len(kline_data) < 10:
                raise Exception(f"{symbol} 的历史数据不足，只有 {len(kline_data)} 条数据")
            
            self.logger.info(f"✅ 成功获取 {len(kline_data)} 条真实历史数据")
            return kline_data
            
        except Exception as e:
            error_msg = f"获取真实历史数据失败: {e}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def _save_result(self, result: BacktestResult) -> None:
        """保存回测结果"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"backtest_{result.symbol}_{result.strategy}_{timestamp}.json"
            filepath = os.path.join(self.results_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"回测结果已保存: {filepath}")
            
        except Exception as e:
            self.logger.error(f"保存回测结果失败: {e}")
    
    def _generate_summary_report(self, results: List[BacktestResult], strategy_name: str) -> None:
        """生成汇总报告"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"summary_{strategy_name}_{timestamp}.txt"
            filepath = os.path.join(self.results_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"多股票回测汇总报告 - {strategy_name}\n")
                f.write("=" * 60 + "\n\n")
                
                f.write(f"回测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"策略: {strategy_name}\n")
                f.write(f"股票数量: {len(results)}\n\n")
                
                # 按收益率排序
                sorted_results = sorted(results, key=lambda x: x.total_return_pct, reverse=True)
                
                f.write("股票收益排名:\n")
                f.write("-" * 40 + "\n")
                for i, result in enumerate(sorted_results, 1):
                    f.write(f"{i:2d}. {result.symbol}: {result.total_return_pct:+6.2f}% ")
                    f.write(f"(胜率: {result.win_rate:.1f}%, 交易: {result.total_trades}次)\n")
                
                # 统计信息
                avg_return = sum(r.total_return_pct for r in results) / len(results)
                profitable_count = sum(1 for r in results if r.total_return_pct > 0)
                
                f.write(f"\n总体统计:\n")
                f.write("-" * 20 + "\n")
                f.write(f"平均收益率: {avg_return:.2f}%\n")
                f.write(f"盈利股票数: {profitable_count}/{len(results)}\n")
                f.write(f"盈利比例: {profitable_count/len(results)*100:.1f}%\n")
            
            self.logger.info(f"汇总报告已生成: {filepath}")
            
        except Exception as e:
            self.logger.error(f"生成汇总报告失败: {e}")
    
    def _generate_strategy_comparison(self, results: List[BacktestResult], symbol: str) -> None:
        """生成策略对比报告"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"strategy_comparison_{symbol}_{timestamp}.txt"
            filepath = os.path.join(self.results_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"策略对比报告 - {symbol}\n")
                f.write("=" * 60 + "\n\n")
                
                f.write(f"回测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"股票: {symbol}\n")
                f.write(f"策略数量: {len(results)}\n\n")
                
                # 按收益率排序
                sorted_results = sorted(results, key=lambda x: x.total_return_pct, reverse=True)
                
                f.write("策略收益排名:\n")
                f.write("-" * 60 + "\n")
                f.write(f"{'排名':>4} {'策略名称':>15} {'收益率':>8} {'胜率':>6} {'交易次数':>6} {'夏普比率':>8}\n")
                f.write("-" * 60 + "\n")
                
                for i, result in enumerate(sorted_results, 1):
                    sharpe = f"{result.sharpe_ratio:.3f}" if result.sharpe_ratio else "N/A"
                    f.write(f"{i:>4} {result.strategy:>15} {result.total_return_pct:>+7.2f}% ")
                    f.write(f"{result.win_rate:>5.1f}% {result.total_trades:>6} {sharpe:>8}\n")
            
            self.logger.info(f"策略对比报告已生成: {filepath}")
            
        except Exception as e:
            self.logger.error(f"生成策略对比报告失败: {e}")
