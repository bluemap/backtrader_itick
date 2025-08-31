"""
量化交易系统主应用程序

整合所有模块，提供完整的量化交易信号生成和通知功能
"""

import os
import sys
import time
import signal
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config_manager import config_manager
from src.core.stock_pool_manager import StockPoolManager
from src.core.signal_generator import SignalGenerator, RealTimeSignalGenerator
from src.data.rate_limited_provider import RateLimitedProvider
from src.notifications.notification_manager import NotificationManager
from src.utils.monitoring import MonitoringSystem
from src.strategies.strategy_factory import StrategyFactory, create_strategy_from_config
from src.strategies.base_strategy import TradeSignal
from src.backtesting.backtest_manager import BacktestManager


class QuantTradingSystem:
    """量化交易系统主类"""
    
    def __init__(self, config_path: str = None):
        """
        初始化量化交易系统
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.logger = None
        
        # 系统组件
        self.config_manager = None
        self.stock_pool_manager = None
        self.data_provider = None
        self.data_storage = None
        self.signal_generator = None
        self.notification_manager = None
        self.monitoring_system = None
        self.backtest_manager = None
        
        # 运行状态
        self.is_running = False
        self.start_time = None
        
        # 初始化系统
        self._initialize_system()
    
    def _initialize_system(self) -> bool:
        """
        初始化系统组件
        
        Returns:
            bool: 是否初始化成功
        """
        try:
            # 加载配置
            if self.config_path:
                self.config_manager = config_manager
                self.config_manager.config_path = self.config_path
                self.config_manager.load_config()
            else:
                self.config_manager = config_manager
            
            # 验证配置
            if not self.config_manager.validate_config():
                print("配置验证失败，请检查配置文件")
                return False
            
            # 初始化日志（必须先初始化）
            self._setup_logging()
            
            self.logger.info("开始初始化量化交易系统...")
            
            # 初始化监控系统
            self.monitoring_system = MonitoringSystem(self.config_manager)
            
            # 初始化股票池管理器
            self.stock_pool_manager = StockPoolManager(self.config_manager)
            self.stock_pool_manager.load_from_config()
            
            # 初始化数据提供者
            if self.config_manager.get_itick_config().simulation_mode:
                from src.data.itick_provider import ItickDataProvider, DataStorage
                self.data_provider = ItickDataProvider(self.config_manager)
                self.data_storage = DataStorage(self.config_manager)
            else:
                # 使用限流提供者适应免费账户，但保留iTick提供者用于回测
                self.data_provider = RateLimitedProvider(self.config_manager)
                from src.data.itick_provider import DataStorage
                self.data_storage = DataStorage(self.config_manager)
            
            # 初始化信号生成器
            self.signal_generator = SignalGenerator(self.config_manager)
            
            # 初始化通知管理器
            self.notification_manager = NotificationManager(self.config_manager)
            
            # 初始化回测管理器
            self.backtest_manager = BacktestManager(self.config_manager, self.data_provider)
            
            # 设置信号回调
            self.signal_generator.add_signal_callback(self._on_trading_signal)
            
            # 设置健康检查回调
            self.monitoring_system.add_health_callback(self._on_health_status_change)
            
            self.logger.info("系统初始化完成")
            return True
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"系统初始化失败: {e}")
            else:
                print(f"系统初始化失败: {e}")
            return False
    
    def _setup_logging(self) -> None:
        """设置日志"""
        # 监控系统会初始化日志管理器
        self.logger = logging.getLogger(__name__)
    
    def start(self) -> bool:
        """
        启动系统
        
        Returns:
            bool: 是否启动成功
        """
        if self.is_running:
            self.logger.warning("系统已在运行")
            return True
        
        try:
            self.logger.info("启动量化交易系统...")
            self.start_time = datetime.now()
            
            # 启动监控系统
            self.monitoring_system.start()
            
            # 启动通知管理器
            self.notification_manager.start()
            
            # 测试通知功能
            self._test_notifications()
            
            # 获取股票池
            stock_symbols = self.stock_pool_manager.get_valid_stocks()
            if not stock_symbols:
                self.logger.error("股票池为空，无法启动系统")
                return False
            
            self.logger.info(f"监控股票: {stock_symbols}")
            
            # 启动数据连接
            if not self._start_data_connection(stock_symbols):
                self.logger.error("数据连接启动失败")
                return False
            
            # 启动信号生成
            if not self._start_signal_generation(stock_symbols):
                self.logger.error("信号生成启动失败")
                return False
            
            self.is_running = True
            
            # 发送启动通知
            start_message = f"""
🚀 量化交易系统已启动

启动时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
监控股票数量: {len(stock_symbols)}
策略类型: {self.config_manager.get_strategy_config().type}
通知方式: {', '.join(self.notification_manager.providers.keys())}

系统正在监控市场行情，等待交易信号...
            """.strip()
            
            self.notification_manager.send_message(start_message, "系统启动通知")
            
            self.logger.info("量化交易系统启动成功")
            return True
        
        except Exception as e:
            self.logger.error(f"系统启动失败: {e}")
            return False
    
    def stop(self) -> None:
        """停止系统"""
        if not self.is_running:
            return
        
        self.logger.info("正在停止量化交易系统...")
        
        try:
            # 停止信号生成
            if hasattr(self, 'real_time_generator'):
                self.real_time_generator.stop()
            
            # 断开数据连接
            if self.data_provider:
                if self.config_manager.get_itick_config().simulation_mode:
                    # 模拟模式 - 断开WebSocket
                    self.data_provider.disconnect_websocket()
                else:
                    # 真实模式 - 停止轮询
                    self.data_provider.stop_polling()
            
            # 停止通知管理器
            if self.notification_manager:
                self.notification_manager.stop()
            
            # 停止监控系统
            if self.monitoring_system:
                self.monitoring_system.stop()
            
            self.is_running = False
            
            # 计算运行时间
            if self.start_time:
                uptime = datetime.now() - self.start_time
                uptime_str = str(uptime).split('.')[0]  # 去掉微秒
                
                # 发送停止通知
                stop_message = f"""
🛑 量化交易系统已停止

停止时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
运行时长: {uptime_str}
信号统计: {self.signal_generator.get_signal_statistics()}

感谢使用量化交易系统！
                """.strip()
                
                self.notification_manager.send_message(stop_message, "系统停止通知")
            
            self.logger.info("量化交易系统已停止")
        
        except Exception as e:
            self.logger.error(f"系统停止时发生错误: {e}")
    
    def _start_data_connection(self, stock_symbols: List[str]) -> bool:
        """启动数据连接"""
        try:
            # 检查是否为模拟模式
            if self.config_manager.get_itick_config().simulation_mode:
                # 模拟模式 - 使用WebSocket
                if not self.data_provider.connect_websocket():
                    self.logger.error("WebSocket 连接失败")
                    return False
                
                # 订阅股票数据
                for symbol in stock_symbols:
                    self.data_provider.subscribe_kline(symbol, "1m")
                    time.sleep(0.1)  # 避免订阅过快
                
                self.logger.info(f"已订阅 {len(stock_symbols)} 只股票的实时数据")
            else:
                # 真实模式 - 使用限流轮询（适配免费账户）
                self.logger.info("使用限流轮询模式获取真实iTick数据...")
                
                if not self.data_provider.start_polling(stock_symbols):
                    self.logger.error("启动限流轮询失败")
                    return False
                
                self.logger.info(f"已启动 {len(stock_symbols)} 只股票的限流轮询（每5分钟更新）")
                self.logger.info("注意：由于免费账户限制，数据更新频率为5分钟一次")
            
            return True
        
        except Exception as e:
            self.logger.error(f"启动数据连接失败: {e}")
            return False
    
    def _start_signal_generation(self, stock_symbols: List[str]) -> bool:
        """启动信号生成"""
        try:
            # 创建实时信号生成器
            self.real_time_generator = RealTimeSignalGenerator(
                self.config_manager, 
                self.data_provider
            )
            
            # 添加信号回调
            self.real_time_generator.add_signal_callback(self._on_trading_signal)
            
            # 启动实时信号生成
            if not self.real_time_generator.start(stock_symbols):
                return False
            
            self.logger.info("实时信号生成已启动")
            return True
        
        except Exception as e:
            self.logger.error(f"启动信号生成失败: {e}")
            return False
    
    def _test_notifications(self) -> None:
        """测试通知功能"""
        try:
            test_results = self.notification_manager.test_notifications()
            
            if any(test_results.values()):
                self.logger.info(f"通知测试结果: {test_results}")
            else:
                self.logger.warning("所有通知方式测试失败，请检查配置")
        
        except Exception as e:
            self.logger.error(f"通知测试失败: {e}")
    
    def _on_trading_signal(self, signal: TradeSignal) -> None:
        """
        交易信号回调处理
        
        Args:
            signal: 交易信号
        """
        try:
            # 记录信号到日志
            self.monitoring_system.log_manager.log_signal({
                'symbol': signal.symbol,
                'action': signal.action,
                'price': signal.price,
                'confidence': signal.confidence,
                'strategy': signal.strategy,
                'timestamp': signal.timestamp.isoformat(),
                'reason': signal.reason
            })
            
            # 发送通知
            self.notification_manager.send_signal_notification(signal)
            
            # 更新指标
            self.monitoring_system.metrics_collector.increment_counter('signals_generated')
            
            self.logger.info(f"处理交易信号: {signal.action} {signal.symbol} @ {signal.price}")
        
        except Exception as e:
            self.logger.error(f"处理交易信号失败: {e}")
    
    def _on_health_status_change(self, health_status) -> None:
        """
        健康状态变化回调
        
        Args:
            health_status: 健康状态
        """
        try:
            if health_status.overall_status != 'healthy':
                # 发送健康状态警告
                status_emoji = "⚠️" if health_status.overall_status == 'warning' else "🚨"
                
                message = f"""
{status_emoji} 系统健康状态警报

状态: {health_status.overall_status.upper()}
时间: {health_status.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

问题:
{chr(10).join(f"• {issue}" for issue in health_status.issues)}

建议:
{chr(10).join(f"• {rec}" for rec in health_status.recommendations)}
                """.strip()
                
                self.notification_manager.send_message(message, "系统健康警报")
        
        except Exception as e:
            self.logger.error(f"处理健康状态变化失败: {e}")
    
    def run_backtest(self, symbol: str = None, strategy: str = None,
                    days: int = 30, initial_cash: float = 100000) -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            symbol: 股票代码（为None则使用股票池）
            strategy: 策略名称（为None则使用配置中的策略）
            days: 回测天数
            initial_cash: 初始资金
            
        Returns:
            Dict[str, Any]: 回测结果
        """
        try:
            self.logger.info("开始运行回测...")
            
            # 确定股票池
            if symbol:
                symbols = [symbol]
            else:
                symbols = self.stock_pool_manager.get_valid_stocks()
                if not symbols:
                    raise ValueError("股票池为空")
            
            # 确定策略
            if not strategy:
                strategy = self.config_manager.get_strategy_config().type
            
            # 获取策略参数
            strategy_config = self.config_manager.get_strategy_config()
            strategy_params = {}
            
            if strategy == "MA_Crossover" and strategy_config.ma_crossover:
                strategy_params.update(strategy_config.ma_crossover)
            elif strategy == "RSI_Strategy" and strategy_config.rsi_strategy:
                strategy_params.update(strategy_config.rsi_strategy)
            elif strategy == "BollingerBands" and strategy_config.bollinger_bands:
                strategy_params.update(strategy_config.bollinger_bands)
            elif strategy == "Momentum" and strategy_config.momentum:
                strategy_params.update(strategy_config.momentum)
            
            # 添加风险控制参数
            risk_config = self.config_manager.get_risk_control_config()
            strategy_params.update({
                'stop_loss_pct': risk_config.default_stop_loss,
                'take_profit_pct': risk_config.default_take_profit
            })
            
            # 执行回测
            if len(symbols) == 1:
                # 单股回测
                result = self.backtest_manager.run_strategy_backtest(
                    symbol=symbols[0],
                    strategy_name=strategy,
                    days=days,
                    initial_cash=initial_cash,
                    **strategy_params
                )
                
                if result:
                    result.print_summary()
                    return result.to_dict()
                else:
                    return {'status': 'failed', 'message': '回测执行失败'}
            
            else:
                # 多股回测
                results = self.backtest_manager.run_multi_symbol_backtest(
                    symbols=symbols,
                    strategy_name=strategy,
                    days=days,
                    initial_cash=initial_cash,
                    **strategy_params
                )
                
                if results:
                    print(f"\n多股回测结果 ({len(results)}只股票):")
                    print("=" * 60)
                    
                    # 按收益率排序
                    sorted_results = sorted(results, key=lambda x: x.total_return_pct, reverse=True)
                    
                    for i, result in enumerate(sorted_results, 1):
                        print(f"{i:2d}. {result.symbol}: {result.total_return_pct:+6.2f}% "
                              f"(胜率: {result.win_rate:.1f}%, 交易: {result.total_trades}次)")
                    
                    # 返回统计结果
                    avg_return = sum(r.total_return_pct for r in results) / len(results)
                    profitable_count = sum(1 for r in results if r.total_return_pct > 0)
                    
                    return {
                        'status': 'success',
                        'strategy': strategy,
                        'symbols_count': len(results),
                        'avg_return_pct': avg_return,
                        'profitable_count': profitable_count,
                        'profitable_rate': profitable_count / len(results) * 100,
                        'individual_results': [r.to_dict() for r in results]
                    }
                else:
                    return {'status': 'failed', 'message': '多股回测执行失败'}
        
        except Exception as e:
            self.logger.error(f"回测运行失败: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def run_strategy_comparison(self, symbol: str = None, days: int = 30, 
                              initial_cash: float = 100000) -> Dict[str, Any]:
        """
        运行多策略对比回测
        
        Args:
            symbol: 股票代码（为None则使用第一只股票）
            days: 回测天数
            initial_cash: 初始资金
            
        Returns:
            Dict[str, Any]: 对比结果
        """
        try:
            if not symbol:
                symbols = self.stock_pool_manager.get_valid_stocks()
                if not symbols:
                    raise ValueError("股票池为空")
                symbol = symbols[0]
            
            # 定义要对比的策略
            strategies = [
                {'name': 'MA_Crossover', 'params': {'short_window': 10, 'long_window': 50}},
                {'name': 'RSI_Strategy', 'params': {'period': 14, 'oversold': 30, 'overbought': 70}},
                {'name': 'BollingerBands', 'params': {'period': 20, 'std_dev': 2}},
                {'name': 'Momentum', 'params': {'period': 10, 'threshold': 0.02}}
            ]
            
            results = self.backtest_manager.run_multi_strategy_backtest(
                symbol=symbol,
                strategies=strategies,
                days=days,
                initial_cash=initial_cash
            )
            
            if results:
                print(f"\n策略对比结果 - {symbol}:")
                print("=" * 80)
                print(f"{'\u7b56\u7565\u540d\u79f0':>15} {'\u6536\u76ca\u7387':>8} {'\u80dc\u7387':>6} {'\u4ea4\u6613\u6b21\u6570':>6} {'\u590f\u666e\u6bd4\u7387':>8} {'\u6700\u5927\u56de\u64a4':>8}")
                print("-" * 80)
                
                # 按收益率排序
                sorted_results = sorted(results, key=lambda x: x.total_return_pct, reverse=True)
                
                for result in sorted_results:
                    sharpe = f"{result.sharpe_ratio:.3f}" if result.sharpe_ratio else "N/A"
                    print(f"{result.strategy:>15} {result.total_return_pct:>+7.2f}% "
                          f"{result.win_rate:>5.1f}% {result.total_trades:>6} {sharpe:>8} "
                          f"{result.max_drawdown_pct:>7.2f}%")
                
                return {
                    'status': 'success',
                    'symbol': symbol,
                    'strategies_count': len(results),
                    'best_strategy': sorted_results[0].strategy if results else None,
                    'best_return': sorted_results[0].total_return_pct if results else 0,
                    'results': [r.to_dict() for r in results]
                }
            else:
                return {'status': 'failed', 'message': '策略对比失败'}
        
        except Exception as e:
            self.logger.error(f"策略对比失败: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def quick_backtest(self, symbol: str, strategy: str = "MA_Crossover") -> None:
        """
        快速回测（用于简单测试）
        
        Args:
            symbol: 股票代码
            strategy: 策略名称
        """
        print(f"\n开始快速回测: {symbol} - {strategy}")
        print("=" * 50)
        
        result = self.run_backtest(symbol=symbol, strategy=strategy, days=30)
        
        if result.get('status') == 'success':
            basic_info = result.get('basic_info', {})
            final_result = result.get('final_result', {})
            trade_stats = result.get('trade_statistics', {})
            
            print(f"股票: {basic_info.get('symbol', symbol)}")
            print(f"策略: {basic_info.get('strategy', strategy)}")
            print(f"回测期间: {basic_info.get('start_date')} ~ {basic_info.get('end_date')}")
            print(f"总收益率: {final_result.get('total_return_pct', 'N/A')}")
            print(f"交易次数: {trade_stats.get('total_trades', 0)}")
            print(f"胜率: {trade_stats.get('win_rate', 'N/A')}")
        else:
            print(f"回测失败: {result.get('message', '未知错误')}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            # 基本状态
            status = {
                'is_running': self.is_running,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'uptime_seconds': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            }
            
            # 股票池状态
            if self.stock_pool_manager:
                status['stock_pool'] = self.stock_pool_manager.get_summary()
            
            # 信号统计
            if self.signal_generator:
                status['signals'] = self.signal_generator.get_signal_statistics()
            
            # 通知状态
            if self.notification_manager:
                status['notifications'] = self.notification_manager.get_notification_stats()
            
            # 数据连接状态
            if self.data_provider:
                status['data_connection'] = {
                    'connected': self.data_provider.is_connected,
                    'subscriptions': len(self.data_provider.subscriptions)
                }
            
            # 监控状态
            if self.monitoring_system:
                status['monitoring'] = self.monitoring_system.get_current_status()
            
            return status
        
        except Exception as e:
            self.logger.error(f"获取系统状态失败: {e}")
            return {'error': str(e)}
    
    def update_stock_pool(self, symbols: List[str]) -> bool:
        """
        更新股票池
        
        Args:
            symbols: 股票代码列表
            
        Returns:
            bool: 是否更新成功
        """
        try:
            # 清空现有股票池
            self.stock_pool_manager.clear_stock_pool()
            
            # 添加新股票
            results = self.stock_pool_manager.add_stocks(symbols)
            
            success_count = sum(results.values())
            self.logger.info(f"股票池更新完成: 成功添加 {success_count}/{len(symbols)} 只股票")
            
            # 如果系统正在运行，重新订阅数据
            if self.is_running:
                valid_symbols = self.stock_pool_manager.get_valid_stocks()
                
                # 取消所有订阅
                for symbol in self.data_provider.subscriptions.copy():
                    self.data_provider.unsubscribe(symbol.split('_')[1])
                
                # 重新订阅
                for symbol in valid_symbols:
                    self.data_provider.subscribe_kline(symbol, "1m")
                
                self.logger.info(f"重新订阅了 {len(valid_symbols)} 只股票的数据")
            
            return success_count > 0
        
        except Exception as e:
            self.logger.error(f"更新股票池失败: {e}")
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='港美股量化交易通知系统')
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--mode', choices=['run', 'backtest', 'test'], default='run', help='运行模式')
    parser.add_argument('--start-date', type=str, help='回测开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='回测结束日期 (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # 创建系统实例
    system = QuantTradingSystem(args.config)
    
    if args.mode == 'test':
        # 测试模式
        print("运行系统测试...")
        system.notification_manager.test_notifications()
        print("测试完成")
        
    elif args.mode == 'backtest':
        # 回测模式
        print("运行回测...")
        results = system.run_backtest(args.start_date, args.end_date)
        print("回测结果:")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        
    else:
        # 正常运行模式
        def signal_handler(signum, frame):
            """信号处理器"""
            print("\n收到停止信号，正在关闭系统...")
            system.stop()
            sys.exit(0)
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 启动系统
        if system.start():
            try:
                print("系统运行中，按 Ctrl+C 停止...")
                
                # 主循环
                while system.is_running:
                    time.sleep(10)
                    
                    # 定期输出状态信息
                    if int(time.time()) % 300 == 0:  # 每5分钟
                        status = system.get_system_status()
                        print(f"系统状态: 运行时间 {status.get('uptime_seconds', 0):.0f}秒, "
                              f"信号数 {status.get('signals', {}).get('total_signals', 0)}")
            
            except KeyboardInterrupt:
                pass
            finally:
                system.stop()
        else:
            print("系统启动失败")
            sys.exit(1)


if __name__ == "__main__":
    main()