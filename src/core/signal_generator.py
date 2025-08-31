"""
信号生成模块

负责整合策略信号、过滤、验证并生成标准化的交易信号
"""

import json
import logging
import threading
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
import queue

from ..strategies.base_strategy import TradeSignal, StrategyRunner
from ..strategies.simple_signal_generator import SimpleSignalGenerator
from ..data.data_types import KlineData


@dataclass
class SignalFilter:
    """信号过滤器配置"""
    min_confidence: float = 0.5           # 最小置信度
    max_signals_per_day: int = 100        # 每日最大信号数
    min_interval_minutes: int = 30        # 最小信号间隔（分钟）
    max_position_per_stock: float = 0.1   # 单只股票最大仓位比例
    blacklist_symbols: List[str] = None   # 黑名单股票
    whitelist_symbols: List[str] = None   # 白名单股票
    
    def __post_init__(self):
        if self.blacklist_symbols is None:
            self.blacklist_symbols = []
        if self.whitelist_symbols is None:
            self.whitelist_symbols = []


class SignalGenerator:
    """信号生成器"""
    
    def __init__(self, config_manager=None):
        """
        初始化信号生成器
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # 信号过滤器
        self.signal_filter = self._load_signal_filter()
        
        # 信号队列
        self.signal_queue = queue.Queue()
        
        # 信号历史记录
        self.signal_history: List[TradeSignal] = []
        
        # 信号回调函数
        self.signal_callbacks: List[Callable[[TradeSignal], None]] = []
        
        # 当前持仓状态（模拟）
        self.positions: Dict[str, Dict[str, Any]] = {}
        
        # 每日信号计数
        self.daily_signal_count = 0
        self.last_signal_date = None
        
        # 最后信号时间记录
        self.last_signal_time: Dict[str, datetime] = {}
        
        # 线程锁
        self.lock = threading.Lock()
        
        # 多策略支持
        self.strategy_type = None
        self.strategy_params = None
        
        self.logger.info("信号生成器初始化完成")
    
    def _load_signal_filter(self) -> SignalFilter:
        """从配置加载信号过滤器"""
        if not self.config_manager:
            return SignalFilter()
        
        try:
            risk_config = self.config_manager.get_risk_control_config()
            return SignalFilter(
                max_signals_per_day=risk_config.max_signals_per_day,
                max_position_per_stock=risk_config.max_position_per_stock
            )
        except Exception as e:
            self.logger.error(f"加载信号过滤器配置失败: {e}")
            return SignalFilter()
    
    def add_signal_callback(self, callback: Callable[[TradeSignal], None]) -> None:
        """
        添加信号回调函数
        
        Args:
            callback: 回调函数
        """
        self.signal_callbacks.append(callback)
        self.logger.info("添加信号回调函数")
    
    def process_signal(self, signal: TradeSignal) -> bool:
        """
        处理原始信号
        
        Args:
            signal: 原始交易信号
            
        Returns:
            bool: 是否处理成功
        """
        with self.lock:
            try:
                # 验证信号
                if not self._validate_signal(signal):
                    return False
                
                # 过滤信号
                if not self._filter_signal(signal):
                    return False
                
                # 增强信号
                enhanced_signal = self._enhance_signal(signal)
                
                # 添加到队列和历史
                self.signal_queue.put(enhanced_signal)
                self.signal_history.append(enhanced_signal)
                
                # 更新状态
                self._update_signal_state(enhanced_signal)
                
                # 调用回调函数
                for callback in self.signal_callbacks:
                    try:
                        callback(enhanced_signal)
                    except Exception as e:
                        self.logger.error(f"信号回调函数执行失败: {e}")
                
                self.logger.info(f"信号处理成功: {enhanced_signal.action} {enhanced_signal.symbol} @ {enhanced_signal.price}")
                return True
            
            except Exception as e:
                self.logger.error(f"信号处理失败: {e}")
                return False
    
    def _validate_signal(self, signal: TradeSignal) -> bool:
        """
        验证信号有效性
        
        Args:
            signal: 交易信号
            
        Returns:
            bool: 是否有效
        """
        # 基本字段验证
        if not signal.symbol or not signal.action or signal.price <= 0:
            self.logger.warning(f"信号基本字段无效: {signal}")
            return False
        
        # 动作验证
        if signal.action not in ['BUY', 'SELL']:
            self.logger.warning(f"无效的交易动作: {signal.action}")
            return False
        
        # 置信度验证
        if not (0 <= signal.confidence <= 1):
            self.logger.warning(f"无效的置信度: {signal.confidence}")
            return False
        
        # 价格合理性验证
        if signal.stop_loss and signal.stop_loss <= 0:
            self.logger.warning(f"无效的止损价格: {signal.stop_loss}")
            return False
        
        if signal.take_profit and signal.take_profit <= 0:
            self.logger.warning(f"无效的止盈价格: {signal.take_profit}")
            return False
        
        return True
    
    def _filter_signal(self, signal: TradeSignal) -> bool:
        """
        过滤信号
        
        Args:
            signal: 交易信号
            
        Returns:
            bool: 是否通过过滤
        """
        # 置信度过滤
        if signal.confidence < self.signal_filter.min_confidence:
            self.logger.debug(f"信号置信度不足: {signal.confidence} < {self.signal_filter.min_confidence}")
            return False
        
        # 黑名单过滤
        if signal.symbol in self.signal_filter.blacklist_symbols:
            self.logger.debug(f"股票在黑名单中: {signal.symbol}")
            return False
        
        # 白名单过滤
        if (self.signal_filter.whitelist_symbols and 
            signal.symbol not in self.signal_filter.whitelist_symbols):
            self.logger.debug(f"股票不在白名单中: {signal.symbol}")
            return False
        
        # 每日信号数量限制
        today = signal.timestamp.date()
        if self.last_signal_date != today:
            self.daily_signal_count = 0
            self.last_signal_date = today
        
        if self.daily_signal_count >= self.signal_filter.max_signals_per_day:
            self.logger.debug(f"达到每日最大信号数量: {self.daily_signal_count}")
            return False
        
        # 信号间隔过滤
        last_time = self.last_signal_time.get(signal.symbol)
        if last_time:
            time_diff = signal.timestamp - last_time
            min_interval = timedelta(minutes=self.signal_filter.min_interval_minutes)
            if time_diff < min_interval:
                self.logger.debug(f"信号间隔过短: {time_diff} < {min_interval}")
                return False
        
        # 仓位限制过滤
        if signal.action == 'BUY':
            current_position = self.positions.get(signal.symbol, {}).get('size', 0)
            if current_position >= self.signal_filter.max_position_per_stock:
                self.logger.debug(f"超过单只股票最大仓位: {current_position}")
                return False
        
        return True
    
    def _enhance_signal(self, signal: TradeSignal) -> TradeSignal:
        """
        增强信号，添加额外信息
        
        Args:
            signal: 原始信号
            
        Returns:
            TradeSignal: 增强后的信号
        """
        # 创建信号副本
        enhanced_signal = TradeSignal(
            symbol=signal.symbol,
            timestamp=signal.timestamp,
            action=signal.action,
            price=signal.price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            strategy=signal.strategy,
            confidence=signal.confidence,
            volume=signal.volume,
            reason=signal.reason
        )
        
        # 添加风险控制信息
        if not enhanced_signal.stop_loss:
            if self.config_manager:
                risk_config = self.config_manager.get_risk_control_config()
                if enhanced_signal.action == 'BUY':
                    enhanced_signal.stop_loss = enhanced_signal.price * (1 - risk_config.default_stop_loss)
                    enhanced_signal.take_profit = enhanced_signal.price * (1 + risk_config.default_take_profit)
                else:  # SELL
                    enhanced_signal.stop_loss = enhanced_signal.price * (1 + risk_config.default_stop_loss)
                    enhanced_signal.take_profit = enhanced_signal.price * (1 - risk_config.default_take_profit)
        
        # 添加建议交易量
        if not enhanced_signal.volume:
            # 简单的资金管理：假设总资金的2%用于单笔交易
            enhanced_signal.volume = int(10000 * 0.02 / enhanced_signal.price)  # 假设1万美金
        
        return enhanced_signal
    
    def _update_signal_state(self, signal: TradeSignal) -> None:
        """
        更新信号状态
        
        Args:
            signal: 交易信号
        """
        # 更新每日信号计数
        self.daily_signal_count += 1
        
        # 更新最后信号时间
        self.last_signal_time[signal.symbol] = signal.timestamp
        
        # 更新模拟仓位（简化处理）
        if signal.symbol not in self.positions:
            self.positions[signal.symbol] = {'size': 0, 'avg_price': 0}
        
        if signal.action == 'BUY':
            # 增加仓位
            current_size = self.positions[signal.symbol]['size']
            current_avg = self.positions[signal.symbol]['avg_price']
            new_size = current_size + (signal.volume or 100)
            
            if current_size > 0:
                new_avg = (current_avg * current_size + signal.price * (signal.volume or 100)) / new_size
            else:
                new_avg = signal.price
            
            self.positions[signal.symbol]['size'] = new_size
            self.positions[signal.symbol]['avg_price'] = new_avg
        
        elif signal.action == 'SELL':
            # 减少或清空仓位
            sell_size = signal.volume or self.positions[signal.symbol]['size']
            self.positions[signal.symbol]['size'] = max(0, self.positions[signal.symbol]['size'] - sell_size)
            
            if self.positions[signal.symbol]['size'] == 0:
                self.positions[signal.symbol]['avg_price'] = 0
    
    def get_signal(self, timeout: float = 1.0) -> Optional[TradeSignal]:
        """
        获取信号
        
        Args:
            timeout: 超时时间
            
        Returns:
            Optional[TradeSignal]: 交易信号
        """
        try:
            return self.signal_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_signal_history(self, symbol: str = None, limit: int = 100) -> List[TradeSignal]:
        """
        获取信号历史
        
        Args:
            symbol: 股票代码，None表示所有股票
            limit: 返回数量限制
            
        Returns:
            List[TradeSignal]: 信号历史
        """
        with self.lock:
            if symbol:
                history = [s for s in self.signal_history if s.symbol == symbol]
            else:
                history = self.signal_history.copy()
            
            return history[-limit:] if limit > 0 else history
    
    def get_signal_statistics(self) -> Dict[str, Any]:
        """
        获取信号统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        with self.lock:
            total_signals = len(self.signal_history)
            buy_signals = len([s for s in self.signal_history if s.action == 'BUY'])
            sell_signals = len([s for s in self.signal_history if s.action == 'SELL'])
            
            # 按股票统计
            symbol_stats = {}
            for signal in self.signal_history:
                if signal.symbol not in symbol_stats:
                    symbol_stats[signal.symbol] = {'buy': 0, 'sell': 0, 'total': 0}
                symbol_stats[signal.symbol][signal.action.lower()] += 1
                symbol_stats[signal.symbol]['total'] += 1
            
            # 按策略统计
            strategy_stats = {}
            for signal in self.signal_history:
                if signal.strategy not in strategy_stats:
                    strategy_stats[signal.strategy] = {'buy': 0, 'sell': 0, 'total': 0}
                strategy_stats[signal.strategy][signal.action.lower()] += 1
                strategy_stats[signal.strategy]['total'] += 1
            
            # 平均置信度
            avg_confidence = sum(s.confidence for s in self.signal_history) / total_signals if total_signals > 0 else 0
            
            return {
                'total_signals': total_signals,
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'daily_signal_count': self.daily_signal_count,
                'avg_confidence': avg_confidence,
                'symbol_stats': symbol_stats,
                'strategy_stats': strategy_stats,
                'positions': self.positions.copy()
            }
    
    def clear_history(self) -> None:
        """清空信号历史"""
        with self.lock:
            self.signal_history.clear()
            self.daily_signal_count = 0
            self.last_signal_date = None
            self.last_signal_time.clear()
            self.positions.clear()
            
            # 清空队列
            while not self.signal_queue.empty():
                try:
                    self.signal_queue.get_nowait()
                except queue.Empty:
                    break
        
        self.logger.info("信号历史已清空")
    
    def export_signals_to_csv(self, filename: str, symbol: str = None) -> bool:
        """
        导出信号到CSV文件
        
        Args:
            filename: 文件名
            symbol: 股票代码，None表示所有股票
            
        Returns:
            bool: 是否成功
        """
        try:
            signals = self.get_signal_history(symbol)
            
            if not signals:
                self.logger.warning("没有信号可导出")
                return False
            
            # 转换为DataFrame
            data = []
            for signal in signals:
                data.append({
                    'timestamp': signal.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'symbol': signal.symbol,
                    'action': signal.action,
                    'price': signal.price,
                    'stop_loss': signal.stop_loss,
                    'take_profit': signal.take_profit,
                    'strategy': signal.strategy,
                    'confidence': signal.confidence,
                    'volume': signal.volume,
                    'reason': signal.reason
                })
            
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False)
            
            self.logger.info(f"信号已导出到: {filename}")
            return True
        
        except Exception as e:
            self.logger.error(f"导出信号失败: {e}")
            return False
    
    def export_signals_to_json(self, filename: str, symbol: str = None) -> bool:
        """
        导出信号到JSON文件
        
        Args:
            filename: 文件名
            symbol: 股票代码，None表示所有股票
            
        Returns:
            bool: 是否成功
        """
        try:
            signals = self.get_signal_history(symbol)
            
            if not signals:
                self.logger.warning("没有信号可导出")
                return False
            
            # 转换为字典列表
            data = []
            for signal in signals:
                signal_dict = asdict(signal)
                # 转换时间格式
                signal_dict['timestamp'] = signal.timestamp.isoformat()
                data.append(signal_dict)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"信号已导出到: {filename}")
            return True
        
        except Exception as e:
            self.logger.error(f"导出信号失败: {e}")
            return False
    
    def update_filter_config(self, **kwargs) -> None:
        """
        更新过滤器配置
        
        Args:
            **kwargs: 配置参数
        """
        for key, value in kwargs.items():
            if hasattr(self.signal_filter, key):
                setattr(self.signal_filter, key, value)
                self.logger.info(f"更新过滤器配置: {key} = {value}")
    
    def generate_signals_for_symbol(self, symbol: str, klines: List[KlineData]) -> List[TradeSignal]:
        """
        为特定股票生成信号（多策略支持）
        
        Args:
            symbol: 股票代码
            klines: K线数据
            
        Returns:
            List[TradeSignal]: 生成的信号列表
        """
        try:
            if not klines or len(klines) < 20:
                return []
            
            # 转换为pandas DataFrame
            data_list = []
            for kline in klines:
                data_list.append({
                    'timestamp': kline.timestamp,
                    'open': kline.open,
                    'high': kline.high,
                    'low': kline.low,
                    'close': kline.close,
                    'volume': kline.volume
                })
            
            df = pd.DataFrame(data_list)
            df.set_index('timestamp', inplace=True)
            
            # 使用策略类型和参数创建策略
            if self.strategy_type and self.strategy_params:
                from ..strategies.simple_signal_generator import SimpleSignalGenerator
                strategy = SimpleSignalGenerator(self.strategy_type, **self.strategy_params)
                
                # 生成信号
                signals = strategy.generate_signals(df)
                
                # 设置股票代码
                for signal in signals:
                    signal.symbol = symbol
                
                return signals
            else:
                self.logger.warning(f"未设置策略类型和参数，无法为 {symbol} 生成信号")
                return []
            
        except Exception as e:
            self.logger.error(f"为 {symbol} 生成信号失败: {e}")
            return []


class RealTimeSignalGenerator:
    """实时信号生成器"""
    
    def __init__(self, config_manager=None, data_provider=None):
        """
        初始化实时信号生成器
        
        Args:
            config_manager: 配置管理器
            data_provider: 数据提供者
        """
        self.config_manager = config_manager
        self.data_provider = data_provider
        self.logger = logging.getLogger(__name__)
        
        # 信号生成器
        self.signal_generator = SignalGenerator(config_manager)
        
        # 策略实例
        self.strategy = None
        
        # 数据缓存
        self.data_cache: Dict[str, List[KlineData]] = {}
        
        # 运行状态
        self.is_running = False
        
        self.logger.info("实时信号生成器初始化完成")
    
    def start(self, stock_symbols: List[str]) -> bool:
        """
        启动实时信号生成
        
        Args:
            stock_symbols: 股票代码列表
            
        Returns:
            bool: 是否启动成功
        """
        try:
            self.logger.debug(f"接收到的stock_symbols类型: {type(stock_symbols)}, 值: {stock_symbols}")
            
            # 获取策略配置
            strategy_config = self.config_manager.get_strategy_config()
            strategy_type = strategy_config.type
            
            # 获取策略参数
            strategy_params = {}
            if strategy_config.ma_crossover:
                strategy_params.update(strategy_config.ma_crossover)
            if strategy_config.rsi_strategy:
                strategy_params.update(strategy_config.rsi_strategy)
            if strategy_config.bollinger_bands:
                strategy_params.update(strategy_config.bollinger_bands)
            if strategy_config.momentum:
                strategy_params.update(strategy_config.momentum)
            
            # 添加风险控制参数
            risk_config = self.config_manager.get_risk_control_config()
            strategy_params.update({
                'stop_loss_pct': risk_config.default_stop_loss,
                'take_profit_pct': risk_config.default_take_profit
            })
            
            # 创建简化信号生成器
            self.strategy = SimpleSignalGenerator(strategy_type, **strategy_params)
            if not self.strategy:
                self.logger.error("策略创建失败")
                return False
            
            # 添加信号回调
            self.strategy.add_signal_callback(self.signal_generator.process_signal)
            
            # 订阅数据
            if self.data_provider:
                # 检查是否为模拟模式
                from ..core.config_manager import config_manager
                if config_manager.get_itick_config().simulation_mode:
                    # 模拟模式 - 使用K线回调
                    for symbol in stock_symbols:
                        self.data_provider.subscribe_kline(symbol, "1m")
                        self.data_cache[symbol] = []
                    
                    # 添加数据回调
                    self.data_provider.add_kline_callback(self._on_kline_data)
                else:
                    # 真实模式 - 使用限流提供者的价格回调
                    for symbol in stock_symbols:
                        self.data_cache[symbol] = []
                    
                    # 添加价格变化回调
                    self.data_provider.add_price_callback(self._on_kline_data)
            
            self.is_running = True
            self.logger.info("实时信号生成器已启动")
            return True
        
        except Exception as e:
            self.logger.error(f"启动实时信号生成器失败: {e}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            return False
    
    def stop(self) -> None:
        """停止实时信号生成"""
        self.is_running = False
        self.data_cache.clear()
        self.logger.info("实时信号生成器已停止")
    
    def _on_kline_data(self, kline: KlineData) -> None:
        """K线数据回调"""
        if not self.is_running or not self.strategy:
            return
        
        try:
            # 更新数据缓存
            if kline.symbol not in self.data_cache:
                self.data_cache[kline.symbol] = []
            
            self.data_cache[kline.symbol].append(kline)
            
            # 保持最近200个数据点
            if len(self.data_cache[kline.symbol]) > 200:
                self.data_cache[kline.symbol] = self.data_cache[kline.symbol][-200:]
            
            # 转换为pandas DataFrame
            data_list = []
            for k in self.data_cache[kline.symbol]:
                data_list.append({
                    'timestamp': k.timestamp,
                    'open': k.open,
                    'high': k.high,
                    'low': k.low,
                    'close': k.close,
                    'volume': k.volume
                })
            
            if len(data_list) < 50:  # 需要足够的历史数据
                return
            
            df = pd.DataFrame(data_list)
            df.set_index('timestamp', inplace=True)
            
            # 使用简化信号生成器处理数据
            self.strategy.process_data(kline.symbol, df)
            
        except Exception as e:
            self.logger.error(f"处理K线数据失败: {e}")
    
    def add_signal_callback(self, callback: Callable[[TradeSignal], None]) -> None:
        """添加信号回调"""
        self.signal_generator.add_signal_callback(callback)
    
    def get_signal_statistics(self) -> Dict[str, Any]:
        """获取信号统计"""
        return self.signal_generator.get_signal_statistics()