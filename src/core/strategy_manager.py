"""
多策略管理器

负责管理多个策略的并行运行，包括：
- 策略实例创建和管理
- 资金分配管理
- 信号冲突解决
- 策略间风险控制
- 性能监控和统计
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from collections import defaultdict
import pandas as pd

from ..strategies.strategy_factory import StrategyFactory
from ..strategies.base_strategy import TradeSignal
from ..core.stock_pool_manager import StockPoolManager


@dataclass
class StrategyInstance:
    """策略实例"""
    name: str
    strategy_type: str
    enabled: bool
    stock_symbols: List[str]
    capital_allocation: Dict[str, Any]
    parameters: Dict[str, Any]
    risk_control: Dict[str, Any]
    notification: Dict[str, Any]
    
    # 运行时状态
    instance: Any = None
    signal_generator: Any = None
    last_signal_time: Optional[datetime] = None
    daily_signal_count: int = 0
    total_signals: int = 0
    
    # 性能统计
    performance_stats: Dict[str, Any] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.performance_stats is None:
            self.performance_stats = {
                'total_signals': 0,
                'buy_signals': 0,
                'sell_signals': 0,
                'avg_confidence': 0.0,
                'last_signal_time': None,
                'daily_signals': defaultdict(int),
                'stock_signals': defaultdict(int)
            }


@dataclass
class SignalConflict:
    """信号冲突"""
    symbol: str
    signals: List[TradeSignal]
    resolution: str
    resolved_signal: Optional[TradeSignal] = None


class StrategyManager:
    """多策略管理器"""
    
    def __init__(self, config_manager, data_provider):
        """
        初始化策略管理器
        
        Args:
            config_manager: 配置管理器
            data_provider: 数据提供者
        """
        self.config_manager = config_manager
        self.data_provider = data_provider
        self.logger = logging.getLogger(__name__)
        
        # 策略实例管理
        self.strategy_instances: Dict[str, StrategyInstance] = {}
        self.strategy_factory = StrategyFactory()
        
        # 信号管理
        self.signal_callbacks: List[Callable] = []
        self.signal_buffer: List[TradeSignal] = []
        self.signal_conflicts: List[SignalConflict] = []
        
        # 运行状态
        self.is_running = False
        self.worker_threads: Dict[str, threading.Thread] = {}
        self.stop_event = threading.Event()
        
        # 资金管理
        self.total_capital = 0.0
        self.allocated_capital: Dict[str, float] = {}
        self.available_capital = 0.0
        
        # 性能监控
        self.global_stats = {
            'total_signals': 0,
            'conflicts_resolved': 0,
            'strategies_active': 0,
            'start_time': None,
            'last_rebalance': None
        }
        
        # 加载策略配置
        self._load_strategies_from_config()
    
    def _load_strategies_from_config(self):
        """从配置文件加载策略"""
        try:
            # 获取多策略配置
            strategies_config = self.config_manager.get_config('strategies', [])
            strategy_management = self.config_manager.get_config('strategy_management', {})
            
            self.total_capital = strategy_management.get('total_capital', 100000)
            self.available_capital = self.total_capital
            
            self.logger.info(f"开始加载 {len(strategies_config)} 个策略配置")
            
            for strategy_config in strategies_config:
                try:
                    strategy_instance = self._create_strategy_instance(strategy_config)
                    if strategy_instance:
                        self.strategy_instances[strategy_instance.name] = strategy_instance
                        self.logger.info(f"策略 {strategy_instance.name} 加载成功")
                    
                except Exception as e:
                    self.logger.error(f"加载策略失败: {strategy_config.get('name', 'Unknown')}, 错误: {e}")
            
            # 验证资金分配
            self._validate_capital_allocation()
            
            self.logger.info(f"策略管理器初始化完成，共加载 {len(self.strategy_instances)} 个策略")
            
        except Exception as e:
            self.logger.error(f"加载策略配置失败: {e}")
            raise
    
    def _create_strategy_instance(self, config: Dict[str, Any]) -> Optional[StrategyInstance]:
        """创建策略实例"""
        try:
            # 解析配置
            name = config['name']
            strategy_type = config['type']
            enabled = config.get('enabled', True)
            
            if not enabled:
                self.logger.info(f"策略 {name} 已禁用，跳过创建")
                return None
            
            # 处理股票池
            stock_pool_config = config.get('stock_pool', {})
            if stock_pool_config:
                stock_symbols = stock_pool_config.get('symbols', [])
            else:
                # 使用全局股票池
                global_stock_pool = self.config_manager.get_config('global_stock_pool', {})
                stock_symbols = global_stock_pool.get('symbols', [])
            
            # 验证股票符号
            if not stock_symbols:
                self.logger.warning(f"策略 {name} 没有配置股票池")
                return None
            
            # 创建策略实例
            strategy_instance = StrategyInstance(
                name=name,
                strategy_type=strategy_type,
                enabled=enabled,
                stock_symbols=stock_symbols,
                capital_allocation=config.get('capital_allocation', {}),
                parameters=config.get('parameters', {}),
                risk_control=config.get('risk_control', {}),
                notification=config.get('notification', {})
            )
            
            # 计算资金分配
            self._calculate_capital_allocation(strategy_instance)
            
            return strategy_instance
            
        except Exception as e:
            self.logger.error(f"创建策略实例失败: {e}")
            return None
    
    def _calculate_capital_allocation(self, strategy: StrategyInstance):
        """计算策略资金分配"""
        allocation_config = strategy.capital_allocation
        
        if 'percentage' in allocation_config:
            # 按百分比分配
            percentage = allocation_config['percentage'] / 100.0
            allocated_amount = self.total_capital * percentage
        elif 'amount' in allocation_config:
            # 固定金额分配
            allocated_amount = allocation_config['amount']
        else:
            # 默认平均分配
            total_strategies = len([s for s in self.strategy_instances.values() if s.enabled])
            allocated_amount = self.total_capital / max(1, total_strategies)
        
        # 检查最大金额限制
        max_amount = allocation_config.get('max_amount', float('inf'))
        allocated_amount = min(allocated_amount, max_amount)
        
        # 更新分配记录
        self.allocated_capital[strategy.name] = allocated_amount
        
        self.logger.info(f"策略 {strategy.name} 分配资金: ${allocated_amount:,.2f}")
    
    def _validate_capital_allocation(self):
        """验证资金分配"""
        total_allocated = sum(self.allocated_capital.values())
        
        if total_allocated > self.total_capital:
            self.logger.warning(f"资金分配超额: 总分配 ${total_allocated:,.2f} > 总资金 ${self.total_capital:,.2f}")
            
            # 按比例调整
            scale_factor = self.total_capital / total_allocated
            for strategy_name in self.allocated_capital:
                self.allocated_capital[strategy_name] *= scale_factor
            
            self.logger.info("已按比例调整资金分配")
        
        self.available_capital = self.total_capital - sum(self.allocated_capital.values())
        self.logger.info(f"资金分配验证完成，剩余资金: ${self.available_capital:,.2f}")
    
    def start(self) -> bool:
        """启动策略管理器"""
        if self.is_running:
            self.logger.warning("策略管理器已在运行")
            return True
        
        try:
            self.logger.info("启动多策略管理器...")
            
            # 重置停止事件
            self.stop_event.clear()
            
            # 为每个策略创建工作线程
            for strategy_name, strategy in self.strategy_instances.items():
                if strategy.enabled:
                    thread = threading.Thread(
                        target=self._strategy_worker,
                        args=(strategy,),
                        name=f"Strategy-{strategy_name}"
                    )
                    thread.daemon = True
                    self.worker_threads[strategy_name] = thread
                    thread.start()
                    
                    self.logger.info(f"策略 {strategy_name} 工作线程已启动")
            
            # 启动信号处理线程
            signal_thread = threading.Thread(
                target=self._signal_processor,
                name="SignalProcessor"
            )
            signal_thread.daemon = True
            signal_thread.start()
            
            self.is_running = True
            self.global_stats['start_time'] = datetime.now()
            self.global_stats['strategies_active'] = len(self.worker_threads)
            
            self.logger.info(f"策略管理器启动成功，运行 {len(self.worker_threads)} 个策略")
            return True
            
        except Exception as e:
            self.logger.error(f"启动策略管理器失败: {e}")
            return False
    
    def stop(self):
        """停止策略管理器"""
        if not self.is_running:
            return
        
        self.logger.info("正在停止策略管理器...")
        
        # 设置停止事件
        self.stop_event.set()
        
        # 等待所有工作线程结束
        for strategy_name, thread in self.worker_threads.items():
            self.logger.info(f"等待策略 {strategy_name} 线程结束...")
            thread.join(timeout=10)
            if thread.is_alive():
                self.logger.warning(f"策略 {strategy_name} 线程未能正常结束")
        
        self.worker_threads.clear()
        self.is_running = False
        
        # 输出最终统计
        self._log_final_statistics()
        
        self.logger.info("策略管理器已停止")
    
    def _strategy_worker(self, strategy: StrategyInstance):
        """策略工作线程"""
        try:
            self.logger.info(f"策略 {strategy.name} 开始运行")
            
            # 创建策略的信号生成器
            from ..core.signal_generator import SignalGenerator
            strategy.signal_generator = SignalGenerator(self.config_manager)
            
            # 设置策略类型
            strategy.signal_generator.strategy_type = strategy.strategy_type
            strategy.signal_generator.strategy_params = strategy.parameters
            
            # 添加信号回调
            strategy.signal_generator.add_signal_callback(
                lambda signal: self._on_strategy_signal(strategy.name, signal)
            )
            
            # 运行策略监控循环
            while not self.stop_event.is_set():
                try:
                    # 为每个股票生成信号
                    for symbol in strategy.stock_symbols:
                        if self.stop_event.is_set():
                            break
                        
                        # 获取历史数据
                        end_date = datetime.now()
                        start_date = end_date - timedelta(days=7)
                        
                        klines = self.data_provider.get_historical_klines(
                            symbol=symbol,
                            timeframe=self.config_manager.get_data_config().timeframe,
                            start_date=start_date,
                            end_date=end_date,
                            limit=100
                        )
                        
                        if klines and len(klines) > 20:
                            # 生成信号
                            signals = strategy.signal_generator.generate_signals_for_symbol(symbol, klines)
                            
                            if signals:
                                for signal in signals:
                                    signal.strategy_name = strategy.name
                                    self._add_signal_to_buffer(signal)
                        
                        # 避免请求过于频繁
                        time.sleep(1)
                    
                    # 等待下一轮检查
                    if not self.stop_event.wait(300):  # 5分钟检查一次
                        continue
                        
                except Exception as e:
                    self.logger.error(f"策略 {strategy.name} 运行出错: {e}")
                    time.sleep(60)  # 出错后等待1分钟
            
        except Exception as e:
            self.logger.error(f"策略 {strategy.name} 工作线程异常: {e}")
        finally:
            self.logger.info(f"策略 {strategy.name} 工作线程结束")
    
    def _signal_processor(self):
        """信号处理线程"""
        try:
            self.logger.info("信号处理器启动")
            
            while not self.stop_event.is_set():
                try:
                    # 处理信号缓冲区
                    if self.signal_buffer:
                        signals_to_process = self.signal_buffer.copy()
                        self.signal_buffer.clear()
                        
                        # 按股票分组信号
                        signals_by_symbol = defaultdict(list)
                        for signal in signals_to_process:
                            signals_by_symbol[signal.symbol].append(signal)
                        
                        # 处理每个股票的信号
                        for symbol, signals in signals_by_symbol.items():
                            if len(signals) > 1:
                                # 有冲突，需要解决
                                conflict = SignalConflict(symbol=symbol, signals=signals, resolution="")
                                resolved_signal = self._resolve_signal_conflict(conflict)
                                
                                if resolved_signal:
                                    self._emit_resolved_signal(resolved_signal)
                            else:
                                # 单个信号，直接发送
                                self._emit_resolved_signal(signals[0])
                    
                    # 短暂休眠
                    time.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"信号处理出错: {e}")
                    time.sleep(5)
        
        except Exception as e:
            self.logger.error(f"信号处理器异常: {e}")
        finally:
            self.logger.info("信号处理器结束")
    
    def _on_strategy_signal(self, strategy_name: str, signal: TradeSignal):
        """处理策略信号"""
        try:
            # 更新策略统计
            strategy = self.strategy_instances.get(strategy_name)
            if strategy:
                strategy.performance_stats['total_signals'] += 1
                if signal.action == 'BUY':
                    strategy.performance_stats['buy_signals'] += 1
                else:
                    strategy.performance_stats['sell_signals'] += 1
                
                # 更新置信度平均值
                total_signals = strategy.performance_stats['total_signals']
                current_avg = strategy.performance_stats['avg_confidence']
                strategy.performance_stats['avg_confidence'] = (
                    (current_avg * (total_signals - 1) + signal.confidence) / total_signals
                )
                
                strategy.performance_stats['last_signal_time'] = signal.timestamp
                
                # 日信号计数
                today = signal.timestamp.date()
                strategy.performance_stats['daily_signals'][today] += 1
                strategy.performance_stats['stock_signals'][signal.symbol] += 1
                
                # 检查日信号限制
                daily_limit = strategy.risk_control.get('max_signals_per_day', 50)
                if strategy.performance_stats['daily_signals'][today] > daily_limit:
                    self.logger.warning(f"策略 {strategy_name} 今日信号数量超限: {strategy.performance_stats['daily_signals'][today]}")
                    return
            
            # 添加到信号缓冲区
            signal.strategy_name = strategy_name
            self._add_signal_to_buffer(signal)
            
        except Exception as e:
            self.logger.error(f"处理策略信号失败: {e}")
    
    def _add_signal_to_buffer(self, signal: TradeSignal):
        """添加信号到缓冲区"""
        self.signal_buffer.append(signal)
        self.global_stats['total_signals'] += 1
    
    def _resolve_signal_conflict(self, conflict: SignalConflict) -> Optional[TradeSignal]:
        """解决信号冲突"""
        try:
            strategy_management = self.config_manager.get_config('strategy_management', {})
            conflict_resolution = strategy_management.get('conflict_resolution', {})
            mode = conflict_resolution.get('mode', 'highest_confidence')
            
            self.logger.info(f"解决信号冲突: {conflict.symbol}, {len(conflict.signals)} 个信号, 模式: {mode}")
            
            if mode == 'first_wins':
                # 第一个信号优先
                resolved_signal = min(conflict.signals, key=lambda s: s.timestamp)
                conflict.resolution = "第一个信号优先"
                
            elif mode == 'highest_confidence':
                # 最高置信度优先
                resolved_signal = max(conflict.signals, key=lambda s: s.confidence)
                conflict.resolution = "最高置信度优先"
                
            elif mode == 'combine_signals':
                # 组合信号
                resolved_signal = self._combine_signals(conflict.signals, conflict_resolution)
                conflict.resolution = "信号组合"
                
            else:
                self.logger.warning(f"未知的冲突解决模式: {mode}")
                resolved_signal = conflict.signals[0]
                conflict.resolution = "默认第一个"
            
            conflict.resolved_signal = resolved_signal
            self.signal_conflicts.append(conflict)
            self.global_stats['conflicts_resolved'] += 1
            
            self.logger.info(f"信号冲突已解决: {conflict.symbol}, 选择策略: {resolved_signal.strategy_name}")
            
            return resolved_signal
            
        except Exception as e:
            self.logger.error(f"解决信号冲突失败: {e}")
            return conflict.signals[0] if conflict.signals else None
    
    def _combine_signals(self, signals: List[TradeSignal], config: Dict[str, Any]) -> TradeSignal:
        """组合多个信号"""
        try:
            signal_weights = config.get('signal_weights', {})
            
            # 计算加权置信度
            total_weight = 0
            weighted_confidence = 0
            combined_reason = []
            
            for signal in signals:
                strategy_type = signal.strategy_name.split('_')[0] if '_' in signal.strategy_name else signal.strategy_name
                weight = signal_weights.get(strategy_type, 1.0)
                
                total_weight += weight
                weighted_confidence += signal.confidence * weight
                combined_reason.append(f"{signal.strategy_name}({signal.confidence:.2f})")
            
            # 创建组合信号
            base_signal = signals[0]  # 使用第一个信号作为基础
            
            combined_signal = TradeSignal(
                symbol=base_signal.symbol,
                action=base_signal.action,
                price=base_signal.price,
                timestamp=base_signal.timestamp,
                confidence=weighted_confidence / total_weight,
                reason=f"组合信号: {', '.join(combined_reason)}",
                strategy_name="COMBINED"
            )
            
            return combined_signal
            
        except Exception as e:
            self.logger.error(f"组合信号失败: {e}")
            return signals[0]
    
    def _emit_resolved_signal(self, signal: TradeSignal):
        """发送解决后的信号"""
        try:
            # 调用所有信号回调
            for callback in self.signal_callbacks:
                try:
                    callback(signal)
                except Exception as e:
                    self.logger.error(f"信号回调执行失败: {e}")
            
        except Exception as e:
            self.logger.error(f"发送信号失败: {e}")
    
    def add_signal_callback(self, callback: Callable[[TradeSignal], None]):
        """添加信号回调"""
        self.signal_callbacks.append(callback)
    
    def get_strategy_performance(self, strategy_name: str = None) -> Dict[str, Any]:
        """获取策略性能统计"""
        if strategy_name:
            strategy = self.strategy_instances.get(strategy_name)
            return strategy.performance_stats if strategy else {}
        else:
            # 返回所有策略的性能统计
            performance = {}
            for name, strategy in self.strategy_instances.items():
                performance[name] = strategy.performance_stats
            return performance
    
    def get_global_statistics(self) -> Dict[str, Any]:
        """获取全局统计信息"""
        stats = self.global_stats.copy()
        stats.update({
            'total_strategies': len(self.strategy_instances),
            'active_strategies': len([s for s in self.strategy_instances.values() if s.enabled]),
            'total_capital': self.total_capital,
            'allocated_capital': sum(self.allocated_capital.values()),
            'available_capital': self.available_capital,
            'signal_conflicts_count': len(self.signal_conflicts)
        })
        return stats
    
    def _log_final_statistics(self):
        """记录最终统计信息"""
        try:
            self.logger.info("=" * 60)
            self.logger.info("多策略运行统计报告")
            self.logger.info("=" * 60)
            
            global_stats = self.get_global_statistics()
            self.logger.info(f"运行策略数: {global_stats['active_strategies']}")
            self.logger.info(f"总信号数: {global_stats['total_signals']}")
            self.logger.info(f"信号冲突数: {global_stats['conflicts_resolved']}")
            
            # 各策略统计
            for name, strategy in self.strategy_instances.items():
                stats = strategy.performance_stats
                self.logger.info(f"策略 {name}: 信号 {stats['total_signals']}, 买入 {stats['buy_signals']}, 卖出 {stats['sell_signals']}")
            
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"记录统计信息失败: {e}")