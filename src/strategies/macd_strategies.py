"""
MACD 策略

基于 MACD (Moving Average Convergence Divergence) 指标的交易策略
"""

import backtrader as bt
from .base_strategy import BaseStrategy


class MACDCrossoverStrategy(BaseStrategy):
    """MACD 交叉策略"""
    
    params = (
        ('fast_period', 12),          # 快速EMA周期
        ('slow_period', 26),          # 慢速EMA周期
        ('signal_period', 9),         # 信号线EMA周期
        ('stop_loss_pct', 0.05),      # 止损百分比
        ('take_profit_pct', 0.12),    # 止盈百分比
        ('volume_filter', True),      # 是否启用成交量过滤
        ('volume_ma_period', 20),     # 成交量均线周期
        ('min_volume_ratio', 1.2),    # 最小成交量倍数
        ('trend_filter', True),       # 是否启用趋势过滤
        ('trend_ma_period', 50),      # 趋势均线周期
        ('histogram_threshold', 0.0), # 柱状图阈值
    )
    
    def __init__(self):
        """初始化 MACD 策略"""
        super().__init__()
        
        # MACD 指标
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.fast_period,
            period_me2=self.params.slow_period,
            period_signal=self.params.signal_period
        )
        
        # MACD 信号线交叉
        self.macd_crossover = bt.indicators.CrossOver(
            self.macd.macd, self.macd.signal
        )
        
        # 成交量过滤器
        if self.params.volume_filter:
            self.volume_ma = bt.indicators.SimpleMovingAverage(
                self.data.volume, period=self.params.volume_ma_period
            )
        
        # 趋势过滤器
        if self.params.trend_filter:
            self.trend_ma = bt.indicators.ExponentialMovingAverage(
                self.data.close, period=self.params.trend_ma_period
            )
        
        # 价格动量
        self.momentum = bt.indicators.Momentum(self.data.close, period=10)
        
        # 记录状态
        self.last_macd_signal = 0
        self.signal_strength = 0
        
        self.logger.info(f"MACD策略初始化完成: 快速EMA={self.params.fast_period}, "
                        f"慢速EMA={self.params.slow_period}, 信号线={self.params.signal_period}")
    
    def next(self):
        """策略主逻辑"""
        # 检查数据完整性
        if len(self.data) < max(self.params.slow_period, self.params.trend_ma_period):
            return
        
        current_price = self.data.close[0]
        macd_value = self.macd.macd[0]
        signal_value = self.macd.signal[0]
        histogram = macd_value - signal_value  # 柱状图 = MACD - Signal
        
        # 趋势方向判断
        trend_direction = 0
        if self.params.trend_filter:
            if current_price > self.trend_ma[0]:
                trend_direction = 1  # 上升趋势
            elif current_price < self.trend_ma[0]:
                trend_direction = -1  # 下降趋势
        
        # 成交量确认
        volume_confirmed = True
        if self.params.volume_filter:
            volume_confirmed = (self.data.volume[0] > 
                              self.volume_ma[0] * self.params.min_volume_ratio)
        
        # MACD 信号强度计算
        self.signal_strength = abs(macd_value - signal_value)
        
        # 买入信号
        if (self.macd_crossover[0] > 0 and  # MACD线上穿信号线
            histogram > self.params.histogram_threshold and  # 柱状图为正
            not self.has_position() and  # 无持仓
            volume_confirmed):  # 成交量确认
            
            # 趋势过滤
            if not self.params.trend_filter or trend_direction >= 0:
                reason = f"MACD金叉信号: MACD={macd_value:.4f}, Signal={signal_value:.4f}, Histo={histogram:.4f}"
                
                # 根据信号强度调整置信度
                confidence = min(1.0, 0.6 + self.signal_strength * 20)
                
                self.emit_signal("BUY", current_price, reason, confidence=confidence)
                self.last_macd_signal = 1
        
        # 卖出信号
        elif (self.macd_crossover[0] < 0 and  # MACD线下穿信号线
              histogram < -self.params.histogram_threshold and  # 柱状图为负
              self.has_position() and  # 有持仓
              volume_confirmed):  # 成交量确认
            
            # 趋势过滤
            if not self.params.trend_filter or trend_direction <= 0:
                reason = f"MACD死叉信号: MACD={macd_value:.4f}, Signal={signal_value:.4f}, Histo={histogram:.4f}"
                
                # 根据信号强度调整置信度
                confidence = min(1.0, 0.6 + self.signal_strength * 20)
                
                self.emit_signal("SELL", current_price, reason, confidence=confidence)
                self.last_macd_signal = -1
        
        # 记录调试信息
        self.log_debug(f"MACD={macd_value:.4f}, Signal={signal_value:.4f}, "
                      f"Histo={histogram:.4f}, Trend={trend_direction}, "
                      f"Volume={volume_confirmed}, Price={current_price:.2f}")


class MACDDivergenceStrategy(BaseStrategy):
    """MACD 背离策略"""
    
    params = (
        ('fast_period', 12),          # 快速EMA周期
        ('slow_period', 26),          # 慢速EMA周期
        ('signal_period', 9),         # 信号线EMA周期
        ('lookback_period', 20),      # 背离检测回看周期
        ('min_divergence_bars', 5),   # 最小背离持续K线数
        ('price_threshold', 0.02),    # 价格变化阈值
        ('macd_threshold', 0.001),    # MACD变化阈值
        ('rsi_period', 14),           # RSI确认周期
        ('rsi_oversold', 30),         # RSI超卖线
        ('rsi_overbought', 70),       # RSI超买线
    )
    
    def __init__(self):
        """初始化 MACD 背离策略"""
        super().__init__()
        
        # MACD 指标
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.fast_period,
            period_me2=self.params.slow_period,
            period_signal=self.params.signal_period
        )
        
        # RSI 确认指标
        self.rsi = bt.indicators.RelativeStrengthIndex(
            self.data.close, period=self.params.rsi_period
        )
        
        # 最高价和最低价
        self.highest_high = bt.indicators.Highest(
            self.data.high, period=self.params.lookback_period
        )
        self.lowest_low = bt.indicators.Lowest(
            self.data.low, period=self.params.lookback_period
        )
        
        # 背离检测状态
        self.bullish_divergence_count = 0
        self.bearish_divergence_count = 0
        
        self.logger.info("MACD背离策略初始化完成")
    
    def detect_bullish_divergence(self) -> bool:
        """检测看涨背离"""
        if len(self.data) < self.params.lookback_period:
            return False
        
        # 价格创新低，但MACD未创新低
        current_low = self.data.low[0]
        previous_low = min(self.data.low[-self.params.lookback_period:0])
        
        current_macd = self.macd.macd[0]
        previous_macd_low = min(self.macd.macd[-self.params.lookback_period:0])
        
        price_makes_lower_low = current_low < previous_low * (1 - self.params.price_threshold)
        macd_not_lower = current_macd > previous_macd_low + self.params.macd_threshold
        
        return price_makes_lower_low and macd_not_lower
    
    def detect_bearish_divergence(self) -> bool:
        """检测看跌背离"""
        if len(self.data) < self.params.lookback_period:
            return False
        
        # 价格创新高，但MACD未创新高
        current_high = self.data.high[0]
        previous_high = max(self.data.high[-self.params.lookback_period:0])
        
        current_macd = self.macd.macd[0]
        previous_macd_high = max(self.macd.macd[-self.params.lookback_period:0])
        
        price_makes_higher_high = current_high > previous_high * (1 + self.params.price_threshold)
        macd_not_higher = current_macd < previous_macd_high - self.params.macd_threshold
        
        return price_makes_higher_high and macd_not_higher
    
    def next(self):
        """策略主逻辑"""
        if len(self.data) < self.params.lookback_period:
            return
        
        current_price = self.data.close[0]
        
        # 检测看涨背离
        if self.detect_bullish_divergence():
            self.bullish_divergence_count += 1
            self.bearish_divergence_count = 0
            
            # 确认信号
            if (self.bullish_divergence_count >= self.params.min_divergence_bars and
                self.rsi[0] < self.params.rsi_oversold and
                not self.has_position()):
                
                reason = f"MACD看涨背离确认: RSI={self.rsi[0]:.1f}, 背离持续{self.bullish_divergence_count}根K线"
                confidence = min(1.0, 0.7 + self.bullish_divergence_count * 0.05)
                
                self.emit_signal("BUY", current_price, reason, confidence=confidence)
                self.bullish_divergence_count = 0
        
        # 检测看跌背离
        elif self.detect_bearish_divergence():
            self.bearish_divergence_count += 1
            self.bullish_divergence_count = 0
            
            # 确认信号
            if (self.bearish_divergence_count >= self.params.min_divergence_bars and
                self.rsi[0] > self.params.rsi_overbought and
                self.has_position()):
                
                reason = f"MACD看跌背离确认: RSI={self.rsi[0]:.1f}, 背离持续{self.bearish_divergence_count}根K线"
                confidence = min(1.0, 0.7 + self.bearish_divergence_count * 0.05)
                
                self.emit_signal("SELL", current_price, reason, confidence=confidence)
                self.bearish_divergence_count = 0
        
        else:
            # 重置计数器
            self.bullish_divergence_count = max(0, self.bullish_divergence_count - 1)
            self.bearish_divergence_count = max(0, self.bearish_divergence_count - 1)


class MACDTrendStrategy(BaseStrategy):
    """MACD 趋势策略"""
    
    params = (
        ('fast_period', 12),          # 快速EMA周期
        ('slow_period', 26),          # 慢速EMA周期  
        ('signal_period', 9),         # 信号线EMA周期
        ('trend_ma_period', 200),     # 长期趋势均线
        ('histogram_min', 0.001),     # 最小柱状图值
        ('histogram_acceleration', True), # 柱状图加速确认
        ('volume_surge', 1.5),        # 成交量激增倍数
        ('atr_period', 14),           # ATR周期
        ('atr_multiplier', 2.0),      # ATR止损倍数
    )
    
    def __init__(self):
        """初始化 MACD 趋势策略"""
        super().__init__()
        
        # MACD 指标
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.fast_period,
            period_me2=self.params.slow_period,
            period_signal=self.params.signal_period
        )
        
        # 长期趋势均线
        self.trend_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.trend_ma_period
        )
        
        # ATR 指标
        self.atr = bt.indicators.AverageTrueRange(period=self.params.atr_period)
        
        # 成交量均线
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=20
        )
        
        # 柱状图变化率（手动计算）
        self.histogram_values = []  # 存储柱状图值用于计算变化率
        
        self.logger.info("MACD趋势策略初始化完成")
    
    def next(self):
        """策略主逻辑"""
        if len(self.data) < self.params.trend_ma_period:
            return
        
        current_price = self.data.close[0]
        macd_value = self.macd.macd[0]
        signal_value = self.macd.signal[0]
        histogram = macd_value - signal_value  # 柱状图 = MACD - Signal
        
        # 长期趋势判断
        in_uptrend = current_price > self.trend_ma[0]
        in_downtrend = current_price < self.trend_ma[0]
        
        # 成交量确认
        volume_surge = self.data.volume[0] > self.volume_ma[0] * self.params.volume_surge
        
        # 柱状图加速度（手动计算）
        histogram_accelerating = True
        if self.params.histogram_acceleration and len(self.data) > 5:
            # 存储当前柱状图值
            current_histogram = histogram
            self.histogram_values.append(current_histogram)
            
            # 保持最近N个值
            if len(self.histogram_values) > 5:
                self.histogram_values.pop(0)
            
            # 计算趋势（简单对比）
            if len(self.histogram_values) >= 3:
                recent_avg = sum(self.histogram_values[-2:]) / 2
                earlier_avg = sum(self.histogram_values[:-2]) / max(1, len(self.histogram_values)-2)
                histogram_accelerating = recent_avg > earlier_avg
        
        # 上升趋势中的买入信号
        if (in_uptrend and
            macd_value > signal_value and  # MACD在信号线上方
            histogram > self.params.histogram_min and  # 柱状图为正且足够大
            histogram_accelerating and  # 柱状图加速上升
            volume_surge and  # 成交量激增
            not self.has_position()):
            
            # 动态止损位
            stop_loss_price = current_price - (self.atr[0] * self.params.atr_multiplier)
            
            reason = (f"MACD趋势买入: 趋势向上, MACD={macd_value:.4f}>{signal_value:.4f}, "
                     f"柱状图={histogram:.4f}, 成交量激增")
            
            self.emit_signal("BUY", current_price, reason, confidence=0.8)
        
        # 下降趋势中的卖出信号
        elif (in_downtrend and
              macd_value < signal_value and  # MACD在信号线下方
              histogram < -self.params.histogram_min and  # 柱状图为负且足够大
              self.has_position()):
            
            reason = (f"MACD趋势卖出: 趋势向下, MACD={macd_value:.4f}<{signal_value:.4f}, "
                     f"柱状图={histogram:.4f}")
            
            self.emit_signal("SELL", current_price, reason, confidence=0.8)