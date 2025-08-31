"""
多策略量化交易系统主应用程序

整合所有模块，支持单策略和多策略并行运行模式
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
from src.core.strategy_manager import StrategyManager
from src.data.rate_limited_provider import RateLimitedProvider
from src.notifications.notification_manager import NotificationManager
from src.utils.monitoring import MonitoringSystem
from src.strategies.strategy_factory import StrategyFactory, create_strategy_from_config
from src.strategies.base_strategy import TradeSignal
from src.backtesting.backtest_manager import BacktestManager


class MultiStrategyQuantTradingSystem:
    """多策略量化交易系统主类"""
    
    def __init__(self, config_path: str = None):
        """
        初始化多策略量化交易系统
        
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
        self.strategy_manager = None
        self.notification_manager = None
        self.monitoring_system = None
        self.backtest_manager = None
        
        # 运行状态
        self.is_running = False
        self.start_time = None
        self.is_multi_strategy_mode = False
        
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
            
            self.logger.info("开始初始化多策略量化交易系统...")
            
            # 检查运行模式
            self.is_multi_strategy_mode = self.config_manager.is_multi_strategy_mode()
            self.logger.info(f"运行模式: {'多策略并行' if self.is_multi_strategy_mode else '单策略'}")
            
            # 初始化监控系统
            self.monitoring_system = MonitoringSystem(self.config_manager)
            
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
            
            # 根据模式初始化相应组件
            if self.is_multi_strategy_mode:
                # 多策略模式
                self._initialize_multi_strategy_components()
            else:
                # 单策略模式
                self._initialize_single_strategy_components()
            
            # 初始化通知管理器
            self.notification_manager = NotificationManager(self.config_manager)
            
            # 初始化回测管理器
            self.backtest_manager = BacktestManager(self.config_manager, self.data_provider)
            
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
    
    def _initialize_multi_strategy_components(self):
        """初始化多策略组件"""
        self.logger.info("初始化多策略组件...")
        
        # 初始化策略管理器
        self.strategy_manager = StrategyManager(self.config_manager, self.data_provider)
        
        # 设置信号回调
        self.strategy_manager.add_signal_callback(self._on_trading_signal)
        
        self.logger.info("多策略组件初始化完成")
    
    def _initialize_single_strategy_components(self):
        """初始化单策略组件"""
        self.logger.info("初始化单策略组件...")
        
        # 初始化股票池管理器
        self.stock_pool_manager = StockPoolManager(self.config_manager)
        self.stock_pool_manager.load_from_config()
        
        # 初始化信号生成器
        self.signal_generator = SignalGenerator(self.config_manager)
        
        # 设置信号回调
        self.signal_generator.add_signal_callback(self._on_trading_signal)
        
        self.logger.info("单策略组件初始化完成")
    
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
            self.logger.info("启动多策略量化交易系统...")
            self.start_time = datetime.now()
            
            # 启动监控系统
            self.monitoring_system.start()
            
            # 启动通知管理器
            self.notification_manager.start()
            
            # 测试通知功能
            self._test_notifications()
            
            if self.is_multi_strategy_mode:
                # 多策略模式启动
                success = self._start_multi_strategy_mode()
            else:
                # 单策略模式启动
                success = self._start_single_strategy_mode()
            
            if not success:
                return False
            
            self.is_running = True
            
            # 发送启动通知
            self._send_startup_notification()
            
            self.logger.info("多策略量化交易系统启动成功")
            return True
        
        except Exception as e:
            self.logger.error(f"系统启动失败: {e}")
            return False
    
    def _start_multi_strategy_mode(self) -> bool:
        """启动多策略模式"""
        try:
            self.logger.info("启动多策略模式...")
            
            # 启动策略管理器
            if not self.strategy_manager.start():
                self.logger.error("策略管理器启动失败")
                return False
            
            # 获取所有策略的股票池
            all_symbols = set()
            for strategy_name, strategy in self.strategy_manager.strategy_instances.items():
                if strategy.enabled:
                    all_symbols.update(strategy.stock_symbols)
            
            if not all_symbols:
                self.logger.error("没有可用的股票符号")
                return False
            
            self.logger.info(f"多策略模式监控股票: {list(all_symbols)}")
            
            # 启动数据连接
            if not self._start_data_connection(list(all_symbols)):
                self.logger.error("数据连接启动失败")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"多策略模式启动失败: {e}")
            return False
    
    def _start_single_strategy_mode(self) -> bool:
        """启动单策略模式"""
        try:
            self.logger.info("启动单策略模式...")
            
            # 获取股票池
            stock_symbols = self.stock_pool_manager.get_valid_stocks()
            if not stock_symbols:
                self.logger.error("股票池为空，无法启动系统")
                return False
            
            self.logger.info(f"单策略模式监控股票: {stock_symbols}")
            
            # 启动数据连接
            if not self._start_data_connection(stock_symbols):
                self.logger.error("数据连接启动失败")
                return False
            
            # 启动信号生成
            if not self._start_signal_generation(stock_symbols):
                self.logger.error("信号生成启动失败")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"单策略模式启动失败: {e}")
            return False
    
    def stop(self) -> None:
        """停止系统"""
        if not self.is_running:
            return
        
        self.logger.info("正在停止多策略量化交易系统...")
        
        try:
            if self.is_multi_strategy_mode:
                # 停止策略管理器
                if self.strategy_manager:
                    self.strategy_manager.stop()
            else:
                # 停止单策略信号生成
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
            
            # 发送停止通知
            self._send_shutdown_notification()
            
            self.logger.info("多策略量化交易系统已停止")
        
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
        """启动单策略信号生成"""
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
            
            self.logger.info("单策略信号生成启动成功")
            return True
        
        except Exception as e:
            self.logger.error(f"启动信号生成失败: {e}")
            return False
    
    def _test_notifications(self) -> None:
        """测试通知功能"""
        try:
            test_message = "🔄 系统连接测试 - 通知功能正常"
            self.notification_manager.send_message(test_message, "系统测试")
            self.logger.info("通知功能测试完成")
        except Exception as e:
            self.logger.warning(f"通知功能测试失败: {e}")
    
    def _send_startup_notification(self):
        """发送启动通知"""
        try:
            if self.is_multi_strategy_mode:
                # 多策略启动通知
                strategy_count = len([s for s in self.strategy_manager.strategy_instances.values() if s.enabled])
                all_symbols = set()
                for strategy in self.strategy_manager.strategy_instances.values():
                    if strategy.enabled:
                        all_symbols.update(strategy.stock_symbols)
                
                start_message = f"""
🚀 多策略量化交易系统已启动

启动时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
运行模式: 多策略并行
活跃策略数量: {strategy_count}
监控股票数量: {len(all_symbols)}
策略列表: {', '.join([s.name for s in self.strategy_manager.strategy_instances.values() if s.enabled])}
通知方式: {', '.join(self.notification_manager.providers.keys())}

系统正在监控市场行情，等待交易信号...
                """.strip()
            else:
                # 单策略启动通知
                stock_symbols = self.stock_pool_manager.get_valid_stocks()
                start_message = f"""
🚀 量化交易系统已启动

启动时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
运行模式: 单策略
监控股票数量: {len(stock_symbols)}
策略类型: {self.config_manager.get_strategy_config().type}
通知方式: {', '.join(self.notification_manager.providers.keys())}

系统正在监控市场行情，等待交易信号...
                """.strip()
            
            self.notification_manager.send_message(start_message, "系统启动通知")
            
        except Exception as e:
            self.logger.error(f"发送启动通知失败: {e}")
    
    def _send_shutdown_notification(self):
        """发送停止通知"""
        try:
            # 计算运行时间
            if self.start_time:
                uptime = datetime.now() - self.start_time
                uptime_str = str(uptime).split('.')[0]  # 去掉微秒
                
                if self.is_multi_strategy_mode:
                    # 多策略停止通知
                    stats = self.strategy_manager.get_global_statistics()
                    stop_message = f"""
🛑 多策略量化交易系统已停止

停止时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
运行时长: {uptime_str}
总信号数: {stats.get('total_signals', 0)}
信号冲突数: {stats.get('conflicts_resolved', 0)}
策略数量: {stats.get('active_strategies', 0)}

感谢使用多策略量化交易系统！
                    """.strip()
                else:
                    # 单策略停止通知
                    stop_message = f"""
🛑 量化交易系统已停止

停止时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
运行时长: {uptime_str}
信号统计: {self.signal_generator.get_signal_statistics() if self.signal_generator else "无"}

感谢使用量化交易系统！
                    """.strip()
                
                self.notification_manager.send_message(stop_message, "系统停止通知")
            
        except Exception as e:
            self.logger.error(f"发送停止通知失败: {e}")
    
    def _on_trading_signal(self, signal: TradeSignal) -> None:
        """处理交易信号"""
        try:
            # 记录信号
            strategy_name = getattr(signal, 'strategy_name', 'Unknown')
            self.logger.info(f"收到交易信号: {signal.symbol} {signal.action} @ {signal.price:.2f} "
                           f"[{strategy_name}] 置信度: {signal.confidence:.2f}")
            
            # 构造通知消息
            prefix = ""
            if self.is_multi_strategy_mode:
                # 多策略模式，添加策略前缀
                strategy = self.strategy_manager.strategy_instances.get(strategy_name)
                if strategy and strategy.notification.get('enabled', True):
                    prefix = strategy.notification.get('prefix', f"[{strategy_name}]")
            
            # 格式化信号消息
            message = self._format_signal_message(signal, prefix)
            
            # 发送通知
            self.notification_manager.send_signal(signal, message)
            
        except Exception as e:
            self.logger.error(f"处理交易信号失败: {e}")
    
    def _format_signal_message(self, signal: TradeSignal, prefix: str = "") -> str:
        """格式化信号消息"""
        try:
            action_emoji = "🟢" if signal.action == "BUY" else "🔴"
            confidence_stars = "⭐" * min(5, max(1, int(signal.confidence * 5)))
            
            message = f"""
{prefix} {action_emoji} {signal.action} 信号

股票: {signal.symbol}
价格: ${signal.price:.2f}
时间: {signal.timestamp.strftime('%H:%M:%S')}
置信度: {confidence_stars} ({signal.confidence:.1%})
原因: {signal.reason}

策略: {getattr(signal, 'strategy_name', 'Unknown')}
            """.strip()
            
            return message
            
        except Exception as e:
            self.logger.error(f"格式化信号消息失败: {e}")
            return f"{prefix} {signal.action} {signal.symbol} @ {signal.price:.2f}"
    
    def _on_health_status_change(self, status) -> None:
        """处理健康状态变化"""
        try:
            # 检查状态类型
            if hasattr(status, 'overall_status'):
                # HealthStatus 对象
                if status.overall_status != 'healthy':
                    self.logger.warning(f"系统健康状态异常: {status.overall_status}")
                    if hasattr(status, 'issues') and status.issues:
                        for issue in status.issues:
                            self.logger.warning(f"健康问题: {issue}")
            elif isinstance(status, dict):
                # 字典格式
                if not status.get('healthy', True):
                    self.logger.warning(f"系统健康状态异常: {status}")
            else:
                self.logger.debug(f"收到健康状态更新: {status}")
        except Exception as e:
            self.logger.error(f"处理健康状态变化失败: {e}")
    
    def run_backtest(self, **kwargs) -> Dict[str, Any]:
        """运行回测"""
        try:
            if self.is_multi_strategy_mode:
                # 多策略回测
                return self._run_multi_strategy_backtest(**kwargs)
            else:
                # 单策略回测
                return self.backtest_manager.run_backtest(**kwargs)
        
        except Exception as e:
            self.logger.error(f"回测运行失败: {e}")
            return {"status": "error", "error": str(e)}
    
    def _run_multi_strategy_backtest(self, **kwargs) -> Dict[str, Any]:
        """运行多策略回测"""
        try:
            # 实现多策略回测逻辑
            # 这里可以为每个策略单独运行回测，然后汇总结果
            results = {}
            
            for strategy_name, strategy in self.strategy_manager.strategy_instances.items():
                if strategy.enabled:
                    self.logger.info(f"开始回测策略: {strategy_name}")
                    
                    # 为每个股票运行回测
                    strategy_results = []
                    for symbol in strategy.stock_symbols:
                        result = self.backtest_manager.run_backtest(
                            symbol=symbol,
                            strategy=strategy.strategy_type,
                            **kwargs
                        )
                        if result.get('status') == 'success':
                            strategy_results.append(result)
                    
                    results[strategy_name] = strategy_results
            
            return {
                "status": "success",
                "mode": "multi_strategy",
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"多策略回测失败: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            status = {
                "is_running": self.is_running,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "mode": "multi_strategy" if self.is_multi_strategy_mode else "single_strategy",
                "uptime": str(datetime.now() - self.start_time).split('.')[0] if self.start_time else None
            }
            
            if self.is_multi_strategy_mode and self.strategy_manager:
                status.update(self.strategy_manager.get_global_statistics())
            elif self.signal_generator:
                status["signal_stats"] = self.signal_generator.get_signal_statistics()
            
            return status
            
        except Exception as e:
            self.logger.error(f"获取系统状态失败: {e}")
            return {"error": str(e)}


def main():
    """主函数"""
    try:
        # 创建系统实例
        system = MultiStrategyQuantTradingSystem()
        
        # 设置信号处理
        def signal_handler(signum, frame):
            print("\n收到退出信号，正在停止系统...")
            system.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 启动系统
        if system.start():
            print("系统启动成功！按 Ctrl+C 停止系统")
            
            # 保持运行
            try:
                while system.is_running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        else:
            print("系统启动失败")
            
    except Exception as e:
        print(f"系统运行异常: {e}")
    finally:
        if 'system' in locals():
            system.stop()


if __name__ == "__main__":
    main()