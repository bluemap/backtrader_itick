"""
简化信号生成器

不依赖Backtrader框架，用于实时信号生成
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

from .base_strategy import TradeSignal


class SimpleSignalGenerator:
    """简化信号生成器"""
    
    def __init__(self, strategy_type: str = "MA_Crossover", **params):
        """
        初始化简化信号生成器
        
        Args:
            strategy_type: 策略类型
            **params: 策略参数
        """
        self.logger = logging.getLogger(__name__)
        self.strategy_type = strategy_type
        self.params = params
        
        # 默认参数
        self.short_window = params.get('short_window', 10)
        self.long_window = params.get('long_window', 50)
        self.rsi_period = params.get('period', 14)
        self.rsi_oversold = params.get('oversold', 30)
        self.rsi_overbought = params.get('overbought', 70)
        self.bb_period = params.get('period', 20)
        self.bb_std = params.get('std_dev', 2)
        self.stop_loss_pct = params.get('stop_loss_pct', 0.05)
        self.take_profit_pct = params.get('take_profit_pct', 0.10)
        
        # 信号回调
        self.signal_callbacks: List[Callable[[TradeSignal], None]] = []
        
        self.logger.info(f"简化信号生成器初始化: {strategy_type}")
    
    def add_signal_callback(self, callback: Callable[[TradeSignal], None]) -> None:
        """添加信号回调函数"""
        self.signal_callbacks.append(callback)
    
    def generate_signals(self, data: pd.DataFrame) -> List[TradeSignal]:
        """
        为回测生成信号列表
        
        Args:
            data: 历史价格数据 (OHLCV)
            
        Returns:
            List[TradeSignal]: 信号列表
        """
        signals = []
        
        # 需要足够的数据点来计算技术指标
        min_periods = max(self.short_window, self.long_window, self.rsi_period, self.bb_period)
        if len(data) < min_periods:
            return signals
        
        # 从最小周期开始逐步生成信号
        for i in range(min_periods, len(data)):
            try:
                # 获取到当前时间点的数据
                current_data = data.iloc[:i+1].copy()
                current_price = current_data['close'].iloc[-1]
                current_time = current_data.index[-1]
                
                if hasattr(current_time, 'to_pydatetime'):
                    current_time = current_time.to_pydatetime()
                
                signal = None
                
                if self.strategy_type == "MA_Crossover":
                    signal = self._ma_crossover_signal("BACKTEST", current_data, current_price, current_time)
                elif self.strategy_type == "RSI_Strategy":
                    signal = self._rsi_signal("BACKTEST", current_data, current_price, current_time)
                elif self.strategy_type == "BollingerBands":
                    signal = self._bollinger_signal("BACKTEST", current_data, current_price, current_time)
                elif self.strategy_type == "Momentum":
                    signal = self._momentum_signal("BACKTEST", current_data, current_price, current_time)
                
                if signal:
                    signals.append(signal)
                    
            except Exception as e:
                self.logger.warning(f"在第{i}个数据点生成信号失败: {e}")
                continue
        
        return signals
    
    def process_data(self, symbol: str, data: pd.DataFrame) -> None:
        """
        处理数据并生成信号
        
        Args:
            symbol: 股票代码
            data: 历史价格数据 (OHLCV)
        """
        if len(data) < max(self.short_window, self.long_window, self.rsi_period, self.bb_period):
            return
        
        try:
            current_price = data['close'].iloc[-1]
            current_time = data.index[-1] if hasattr(data.index[-1], 'to_pydatetime') else datetime.now()
            
            if hasattr(current_time, 'to_pydatetime'):
                current_time = current_time.to_pydatetime()
            
            signal = None
            
            if self.strategy_type == "MA_Crossover":
                signal = self._ma_crossover_signal(symbol, data, current_price, current_time)
            elif self.strategy_type == "RSI_Strategy":
                signal = self._rsi_signal(symbol, data, current_price, current_time)
            elif self.strategy_type == "BollingerBands":
                signal = self._bollinger_signal(symbol, data, current_price, current_time)
            elif self.strategy_type == "Momentum":
                signal = self._momentum_signal(symbol, data, current_price, current_time)
            
            if signal:
                self._emit_signal(signal)
                
        except Exception as e:
            self.logger.error(f"处理数据失败: {e}")
    
    def _ma_crossover_signal(self, symbol: str, data: pd.DataFrame, 
                           current_price: float, current_time: datetime) -> Optional[TradeSignal]:
        """均线交叉信号"""
        try:
            # 计算移动平均线
            short_ma = data['close'].rolling(window=self.short_window).mean()
            long_ma = data['close'].rolling(window=self.long_window).mean()
            
            if len(short_ma) < 2 or len(long_ma) < 2:
                return None
            
            # 当前和前一个值
            short_ma_current = short_ma.iloc[-1]
            short_ma_prev = short_ma.iloc[-2]
            long_ma_current = long_ma.iloc[-1]
            long_ma_prev = long_ma.iloc[-2]
            
            # 检查交叉
            if short_ma_prev <= long_ma_prev and short_ma_current > long_ma_current:
                # 金叉 - 买入信号
                confidence = min(1.0, abs(short_ma_current - long_ma_current) / long_ma_current * 10)
                reason = f"金叉买入: 短期MA({short_ma_current:.2f}) > 长期MA({long_ma_current:.2f})"
                
                return TradeSignal(
                    symbol=symbol,
                    timestamp=current_time,
                    action="BUY",
                    price=current_price,
                    stop_loss=current_price * (1 - self.stop_loss_pct),
                    take_profit=current_price * (1 + self.take_profit_pct),
                    strategy="MA_Crossover",
                    confidence=confidence,
                    reason=reason
                )
            
            elif short_ma_prev >= long_ma_prev and short_ma_current < long_ma_current:
                # 死叉 - 卖出信号
                confidence = min(1.0, abs(short_ma_current - long_ma_current) / long_ma_current * 10)
                reason = f"死叉卖出: 短期MA({short_ma_current:.2f}) < 长期MA({long_ma_current:.2f})"
                
                return TradeSignal(
                    symbol=symbol,
                    timestamp=current_time,
                    action="SELL",
                    price=current_price,
                    stop_loss=current_price * (1 + self.stop_loss_pct),
                    take_profit=current_price * (1 - self.take_profit_pct),
                    strategy="MA_Crossover",
                    confidence=confidence,
                    reason=reason
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"MA交叉信号计算失败: {e}")
            return None
    
    def _rsi_signal(self, symbol: str, data: pd.DataFrame,
                   current_price: float, current_time: datetime) -> Optional[TradeSignal]:
        """RSI信号"""
        try:
            # 计算RSI
            rsi = self._calculate_rsi(data['close'], self.rsi_period)
            
            if len(rsi) < 2:
                return None
            
            current_rsi = rsi.iloc[-1]
            
            if current_rsi <= self.rsi_oversold:
                # 超卖买入
                confidence = (self.rsi_oversold - current_rsi) / self.rsi_oversold
                reason = f"RSI超卖买入: RSI={current_rsi:.1f}"
                
                return TradeSignal(
                    symbol=symbol,
                    timestamp=current_time,
                    action="BUY",
                    price=current_price,
                    stop_loss=current_price * (1 - self.stop_loss_pct),
                    take_profit=current_price * (1 + self.take_profit_pct),
                    strategy="RSI_Strategy",
                    confidence=confidence,
                    reason=reason
                )
            
            elif current_rsi >= self.rsi_overbought:
                # 超买卖出
                confidence = (current_rsi - self.rsi_overbought) / (100 - self.rsi_overbought)
                reason = f"RSI超买卖出: RSI={current_rsi:.1f}"
                
                return TradeSignal(
                    symbol=symbol,
                    timestamp=current_time,
                    action="SELL",
                    price=current_price,
                    stop_loss=current_price * (1 + self.stop_loss_pct),
                    take_profit=current_price * (1 - self.take_profit_pct),
                    strategy="RSI_Strategy",
                    confidence=confidence,
                    reason=reason
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"RSI信号计算失败: {e}")
            return None
    
    def _bollinger_signal(self, symbol: str, data: pd.DataFrame,
                         current_price: float, current_time: datetime) -> Optional[TradeSignal]:
        """布林带信号"""
        try:
            # 计算布林带
            middle = data['close'].rolling(window=self.bb_period).mean()
            std = data['close'].rolling(window=self.bb_period).std()
            upper = middle + (std * self.bb_std)
            lower = middle - (std * self.bb_std)
            
            if len(middle) < 2:
                return None
            
            bb_upper = upper.iloc[-1]
            bb_lower = lower.iloc[-1]
            bb_middle = middle.iloc[-1]
            
            # 布林带位置
            bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)
            
            if bb_position <= 0.1:  # 接近下轨
                confidence = (0.1 - bb_position) / 0.1
                reason = f"布林带下轨反弹: 价格={current_price:.2f}, 下轨={bb_lower:.2f}"
                
                return TradeSignal(
                    symbol=symbol,
                    timestamp=current_time,
                    action="BUY",
                    price=current_price,
                    stop_loss=current_price * (1 - self.stop_loss_pct),
                    take_profit=current_price * (1 + self.take_profit_pct),
                    strategy="BollingerBands",
                    confidence=confidence,
                    reason=reason
                )
            
            elif bb_position >= 0.9:  # 接近上轨
                confidence = (bb_position - 0.9) / 0.1
                reason = f"布林带上轨回调: 价格={current_price:.2f}, 上轨={bb_upper:.2f}"
                
                return TradeSignal(
                    symbol=symbol,
                    timestamp=current_time,
                    action="SELL",
                    price=current_price,
                    stop_loss=current_price * (1 + self.stop_loss_pct),
                    take_profit=current_price * (1 - self.take_profit_pct),
                    strategy="BollingerBands",
                    confidence=confidence,
                    reason=reason
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"布林带信号计算失败: {e}")
            return None
    
    def _momentum_signal(self, symbol: str, data: pd.DataFrame,
                        current_price: float, current_time: datetime) -> Optional[TradeSignal]:
        """动量信号"""
        try:
            period = 10
            if len(data) < period + 1:
                return None
            
            # 计算价格动量
            price_change = (current_price - data['close'].iloc[-(period+1)]) / data['close'].iloc[-(period+1)]
            volume_ratio = data['volume'].iloc[-period:].mean() / data['volume'].iloc[-20:-period].mean() if len(data) >= 20 else 1.0
            
            threshold = 0.02  # 2%动量阈值
            
            if price_change > threshold and volume_ratio > 1.2:
                # 上涨动量
                confidence = min(1.0, price_change / (threshold * 2))
                reason = f"上涨动量: {price_change:.2%}, 成交量放大{volume_ratio:.1f}倍"
                
                return TradeSignal(
                    symbol=symbol,
                    timestamp=current_time,
                    action="BUY",
                    price=current_price,
                    stop_loss=current_price * (1 - self.stop_loss_pct),
                    take_profit=current_price * (1 + self.take_profit_pct),
                    strategy="Momentum",
                    confidence=confidence,
                    reason=reason
                )
            
            elif price_change < -threshold and volume_ratio > 1.2:
                # 下跌动量
                confidence = min(1.0, abs(price_change) / (threshold * 2))
                reason = f"下跌动量: {price_change:.2%}, 成交量放大{volume_ratio:.1f}倍"
                
                return TradeSignal(
                    symbol=symbol,
                    timestamp=current_time,
                    action="SELL",
                    price=current_price,
                    stop_loss=current_price * (1 + self.stop_loss_pct),
                    take_profit=current_price * (1 - self.take_profit_pct),
                    strategy="Momentum",
                    confidence=confidence,
                    reason=reason
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"动量信号计算失败: {e}")
            return None
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """计算RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _emit_signal(self, signal: TradeSignal) -> None:
        """发出信号"""
        for callback in self.signal_callbacks:
            try:
                callback(signal)
            except Exception as e:
                self.logger.error(f"信号回调执行失败: {e}")
        
        self.logger.info(f"生成交易信号: {signal.action} {signal.symbol} @ {signal.price:.2f}")