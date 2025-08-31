"""
均线交叉策略

基于短期均线和长期均线的交叉信号进行交易
"""

import backtrader as bt
from .base_strategy import BaseStrategy


class MovingAverageCrossoverStrategy(BaseStrategy):
    """均线交叉策略"""
    
    params = (
        ('short_window', 10),         # 短期均线周期
        ('long_window', 50),          # 长期均线周期
        ('stop_loss_pct', 0.05),      # 止损百分比
        ('take_profit_pct', 0.10),    # 止盈百分比
        ('min_volume', 1000),         # 最小成交量过滤
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        # 计算均线
        self.short_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.short_window
        )
        self.long_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.long_window
        )
        
        # 交叉信号
        self.crossover = bt.indicators.CrossOver(self.short_ma, self.long_ma)
        
        # 成交量指标
        self.volume = self.data.volume
        
        # 记录上一次交叉状态
        self.last_crossover = 0
        
        self.logger.info(f"均线交叉策略初始化完成: 短期={self.params.short_window}, "
                        f"长期={self.params.long_window}")
    
    def next(self):
        """策略主逻辑"""
        # 检查数据完整性
        if len(self.data) < self.params.long_window:
            return
        
        current_price = self.get_current_price()
        current_volume = self.volume[0]
        
        # 成交量过滤
        if current_volume < self.params.min_volume:
            self.log_debug(f"成交量过低，跳过信号: {current_volume}")
            return
        
        # 金叉信号 - 短期均线上穿长期均线
        if self.crossover[0] == 1 and self.last_crossover != 1:
            if not self.has_position():
                reason = (f"金叉信号: 短期均线({self.short_ma[0]:.2f}) "
                         f"上穿长期均线({self.long_ma[0]:.2f})")
                
                # 计算信号置信度
                ma_spread = (self.short_ma[0] - self.long_ma[0]) / self.long_ma[0]
                confidence = min(1.0, abs(ma_spread) * 100)  # 基于均线差距的置信度
                
                self.emit_signal("BUY", current_price, reason, confidence)
        
        # 死叉信号 - 短期均线下穿长期均线
        elif self.crossover[0] == -1 and self.last_crossover != -1:
            if self.is_long_position():
                reason = (f"死叉信号: 短期均线({self.short_ma[0]:.2f}) "
                         f"下穿长期均线({self.long_ma[0]:.2f})")
                
                # 计算信号置信度
                ma_spread = (self.long_ma[0] - self.short_ma[0]) / self.long_ma[0]
                confidence = min(1.0, abs(ma_spread) * 100)
                
                self.emit_signal("SELL", current_price, reason, confidence)
        
        # 更新交叉状态
        self.last_crossover = self.crossover[0]
        
        # 调试信息
        self.log_debug(f"价格: {current_price:.2f}, 短期MA: {self.short_ma[0]:.2f}, "
                      f"长期MA: {self.long_ma[0]:.2f}, 交叉: {self.crossover[0]}")


class AdaptiveMovingAverageCrossoverStrategy(BaseStrategy):
    """自适应均线交叉策略"""
    
    params = (
        ('short_window', 10),         # 短期均线周期
        ('long_window', 50),          # 长期均线周期
        ('atr_period', 14),           # ATR周期
        ('atr_multiplier', 2.0),      # ATR倍数
        ('volume_ma_period', 20),     # 成交量均线周期
        ('volatility_threshold', 0.02), # 波动率阈值
    )
    
    def __init__(self):
        """初始化自适应均线交叉策略"""
        super().__init__()
        
        # 计算均线
        self.short_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.short_window
        )
        self.long_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.long_window
        )
        
        # EMA 均线
        self.short_ema = bt.indicators.ExponentialMovingAverage(
            self.data.close, period=self.params.short_window
        )
        self.long_ema = bt.indicators.ExponentialMovingAverage(
            self.data.close, period=self.params.long_window
        )
        
        # ATR 指标用于动态止损
        self.atr = bt.indicators.AverageTrueRange(period=self.params.atr_period)
        
        # 成交量均线
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=self.params.volume_ma_period
        )
        
        # 波动率指标
        self.volatility = bt.indicators.StandardDeviation(
            self.data.close, period=20
        ) / self.short_ma
        
        # 交叉信号
        self.ma_crossover = bt.indicators.CrossOver(self.short_ma, self.long_ma)
        self.ema_crossover = bt.indicators.CrossOver(self.short_ema, self.long_ema)
        
        self.logger.info("自适应均线交叉策略初始化完成")
    
    def next(self):
        """策略主逻辑"""
        if len(self.data) < max(self.params.long_window, self.params.atr_period, 
                               self.params.volume_ma_period):
            return
        
        current_price = self.get_current_price()
        current_volume = self.data.volume[0]
        current_volatility = self.volatility[0]
        
        # 市场环境判断
        is_high_volume = current_volume > self.volume_ma[0] * 1.2
        is_low_volatility = current_volatility < self.params.volatility_threshold
        
        # 动态调整参数
        dynamic_stop_loss = self.atr[0] * self.params.atr_multiplier / current_price
        dynamic_take_profit = dynamic_stop_loss * 2
        
        # 信号强度评估
        ma_signal_strength = abs(self.short_ma[0] - self.long_ma[0]) / self.long_ma[0]
        ema_signal_strength = abs(self.short_ema[0] - self.long_ema[0]) / self.long_ema[0]
        
        # 综合信号判断
        ma_bullish = self.ma_crossover[0] == 1
        ema_bullish = self.ema_crossover[0] == 1
        ma_bearish = self.ma_crossover[0] == -1
        ema_bearish = self.ema_crossover[0] == -1
        
        # 买入信号
        if (ma_bullish or ema_bullish) and not self.has_position():
            # 信号确认条件
            signal_confirmed = (
                is_high_volume and  # 成交量放大
                is_low_volatility and  # 低波动环境
                (ma_signal_strength > 0.01 or ema_signal_strength > 0.01)  # 信号强度足够
            )
            
            if signal_confirmed:
                confidence = min(1.0, (ma_signal_strength + ema_signal_strength) * 50)
                reason = f"自适应金叉信号: MA强度={ma_signal_strength:.3f}, EMA强度={ema_signal_strength:.3f}"
                
                # 使用动态止损止盈
                self.params.stop_loss_pct = dynamic_stop_loss
                self.params.take_profit_pct = dynamic_take_profit
                
                self.emit_signal("BUY", current_price, reason, confidence)
        
        # 卖出信号
        elif (ma_bearish or ema_bearish) and self.is_long_position():
            signal_confirmed = (
                is_high_volume and
                (ma_signal_strength > 0.01 or ema_signal_strength > 0.01)
            )
            
            if signal_confirmed:
                confidence = min(1.0, (ma_signal_strength + ema_signal_strength) * 50)
                reason = f"自适应死叉信号: MA强度={ma_signal_strength:.3f}, EMA强度={ema_signal_strength:.3f}"
                
                self.emit_signal("SELL", current_price, reason, confidence)
        
        # 调试信息
        self.log_debug(f"价格: {current_price:.2f}, ATR: {self.atr[0]:.2f}, "
                      f"波动率: {current_volatility:.3f}, 成交量比: {current_volume/self.volume_ma[0]:.2f}")


class TripleMovingAverageCrossoverStrategy(BaseStrategy):
    """三重均线交叉策略"""
    
    params = (
        ('fast_window', 5),           # 快速均线周期
        ('medium_window', 20),        # 中速均线周期
        ('slow_window', 60),          # 慢速均线周期
        ('trend_filter', True),       # 是否启用趋势过滤
        ('volume_filter', True),      # 是否启用成交量过滤
    )
    
    def __init__(self):
        """初始化三重均线交叉策略"""
        super().__init__()
        
        # 三条均线
        self.fast_ma = bt.indicators.ExponentialMovingAverage(
            self.data.close, period=self.params.fast_window
        )
        self.medium_ma = bt.indicators.ExponentialMovingAverage(
            self.data.close, period=self.params.medium_window
        )
        self.slow_ma = bt.indicators.ExponentialMovingAverage(
            self.data.close, period=self.params.slow_window
        )
        
        # 交叉信号
        self.fast_medium_cross = bt.indicators.CrossOver(self.fast_ma, self.medium_ma)
        self.medium_slow_cross = bt.indicators.CrossOver(self.medium_ma, self.slow_ma)
        
        # 趋势指标
        if self.params.trend_filter:
            self.trend_ma = bt.indicators.SimpleMovingAverage(
                self.data.close, period=200
            )
        
        # 成交量指标
        if self.params.volume_filter:
            self.volume_ma = bt.indicators.SimpleMovingAverage(
                self.data.volume, period=20
            )
        
        self.logger.info("三重均线交叉策略初始化完成")
    
    def next(self):
        """策略主逻辑"""
        if len(self.data) < self.params.slow_window:
            return
        
        current_price = self.get_current_price()
        
        # 均线排列判断
        bullish_alignment = (self.fast_ma[0] > self.medium_ma[0] > self.slow_ma[0])
        bearish_alignment = (self.fast_ma[0] < self.medium_ma[0] < self.slow_ma[0])
        
        # 趋势过滤
        if self.params.trend_filter and len(self.data) >= 200:
            uptrend = current_price > self.trend_ma[0]
            downtrend = current_price < self.trend_ma[0]
        else:
            uptrend = downtrend = True
        
        # 成交量过滤
        if self.params.volume_filter:
            volume_confirmed = self.data.volume[0] > self.volume_ma[0] * 1.1
        else:
            volume_confirmed = True
        
        # 买入信号: 快速均线上穿中速均线，且均线多头排列
        if (self.fast_medium_cross[0] == 1 and bullish_alignment and 
            uptrend and volume_confirmed and not self.has_position()):
            
            # 计算信号强度
            ma_spread = ((self.fast_ma[0] - self.slow_ma[0]) / self.slow_ma[0]) * 100
            confidence = min(1.0, abs(ma_spread) / 5)  # 基于均线差距计算置信度
            
            reason = f"三重均线金叉: 快线={self.fast_ma[0]:.2f}, 中线={self.medium_ma[0]:.2f}, 慢线={self.slow_ma[0]:.2f}"
            self.emit_signal("BUY", current_price, reason, confidence)
        
        # 卖出信号: 快速均线下穿中速均线，且均线空头排列
        elif (self.fast_medium_cross[0] == -1 and bearish_alignment and 
              downtrend and volume_confirmed and self.is_long_position()):
            
            ma_spread = ((self.slow_ma[0] - self.fast_ma[0]) / self.slow_ma[0]) * 100
            confidence = min(1.0, abs(ma_spread) / 5)
            
            reason = f"三重均线死叉: 快线={self.fast_ma[0]:.2f}, 中线={self.medium_ma[0]:.2f}, 慢线={self.slow_ma[0]:.2f}"
            self.emit_signal("SELL", current_price, reason, confidence)
        
        # 调试信息
        self.log_debug(f"三重均线状态 - 快线: {self.fast_ma[0]:.2f}, "
                      f"中线: {self.medium_ma[0]:.2f}, 慢线: {self.slow_ma[0]:.2f}, "
                      f"多头排列: {bullish_alignment}, 空头排列: {bearish_alignment}")