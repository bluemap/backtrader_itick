"""
RSI 相对强弱指标策略

基于 RSI 指标的超买超卖信号进行交易
"""

import backtrader as bt
from .base_strategy import BaseStrategy


class RSIStrategy(BaseStrategy):
    """RSI 策略"""
    
    params = (
        ('period', 14),               # RSI 计算周期
        ('oversold', 30),             # 超卖阈值
        ('overbought', 70),           # 超买阈值
        ('stop_loss_pct', 0.05),      # 止损百分比
        ('take_profit_pct', 0.10),    # 止盈百分比
        ('ma_filter', True),          # 是否启用均线过滤
        ('ma_period', 50),            # 均线周期
    )
    
    def __init__(self):
        """初始化 RSI 策略"""
        super().__init__()
        
        # RSI 指标
        self.rsi = bt.indicators.RelativeStrengthIndex(
            self.data.close, period=self.params.period
        )
        
        # 均线过滤器
        if self.params.ma_filter:
            self.ma = bt.indicators.SimpleMovingAverage(
                self.data.close, period=self.params.ma_period
            )
        
        # RSI 信号线
        self.rsi_oversold = self.params.oversold
        self.rsi_overbought = self.params.overbought
        
        # 记录上一次 RSI 状态
        self.last_rsi_state = 'neutral'  # 'oversold', 'overbought', 'neutral'
        
        self.logger.info(f"RSI策略初始化完成: 周期={self.params.period}, "
                        f"超卖={self.params.oversold}, 超买={self.params.overbought}")
    
    def next(self):
        """策略主逻辑"""
        if len(self.data) < max(self.params.period, self.params.ma_period if self.params.ma_filter else 0):
            return
        
        current_price = self.get_current_price()
        current_rsi = self.rsi[0]
        
        # 均线趋势过滤
        if self.params.ma_filter:
            uptrend = current_price > self.ma[0]
            downtrend = current_price < self.ma[0]
        else:
            uptrend = downtrend = True
        
        # 当前 RSI 状态判断
        if current_rsi <= self.rsi_oversold:
            current_rsi_state = 'oversold'
        elif current_rsi >= self.rsi_overbought:
            current_rsi_state = 'overbought'
        else:
            current_rsi_state = 'neutral'
        
        # 超卖反弹信号
        if (self.last_rsi_state == 'oversold' and current_rsi > self.rsi_oversold and
            uptrend and not self.has_position()):
            
            # 计算信号强度
            rsi_strength = (self.rsi_oversold - min(self.rsi[0], self.rsi[-1])) / self.rsi_oversold
            confidence = min(1.0, rsi_strength * 2)
            
            reason = f"RSI超卖反弹: RSI从{self.rsi[-1]:.1f}回升至{current_rsi:.1f}"
            self.emit_signal("BUY", current_price, reason, confidence)
        
        # 超买回调信号
        elif (self.last_rsi_state == 'overbought' and current_rsi < self.rsi_overbought and
              downtrend and self.is_long_position()):
            
            rsi_strength = (max(self.rsi[0], self.rsi[-1]) - self.rsi_overbought) / (100 - self.rsi_overbought)
            confidence = min(1.0, rsi_strength * 2)
            
            reason = f"RSI超买回调: RSI从{self.rsi[-1]:.1f}回落至{current_rsi:.1f}"
            self.emit_signal("SELL", current_price, reason, confidence)
        
        # 更新 RSI 状态
        self.last_rsi_state = current_rsi_state
        
        # 调试信息
        self.log_debug(f"RSI: {current_rsi:.1f}, 状态: {current_rsi_state}, "
                      f"价格: {current_price:.2f}")


class RSIDivergenceStrategy(BaseStrategy):
    """RSI 背离策略"""
    
    params = (
        ('period', 14),               # RSI 计算周期
        ('lookback', 20),             # 背离检测回看周期
        ('min_rsi_diff', 5),          # 最小 RSI 差值
        ('min_price_diff', 0.02),     # 最小价格差值百分比
        ('confirmation_bars', 2),     # 确认K线数量
    )
    
    def __init__(self):
        """初始化 RSI 背离策略"""
        super().__init__()
        
        # RSI 指标
        self.rsi = bt.indicators.RelativeStrengthIndex(
            self.data.close, period=self.params.period
        )
        
        # 价格高点和低点
        self.highs = []
        self.lows = []
        self.rsi_highs = []
        self.rsi_lows = []
        
        # 确认计数器
        self.bullish_divergence_count = 0
        self.bearish_divergence_count = 0
        
        self.logger.info("RSI背离策略初始化完成")
    
    def next(self):
        """策略主逻辑"""
        if len(self.data) < self.params.period + self.params.lookback:
            return
        
        current_price = self.get_current_price()
        current_rsi = self.rsi[0]
        
        # 更新高点和低点
        self._update_extremes()
        
        # 检测看涨背离
        bullish_divergence = self._detect_bullish_divergence()
        if bullish_divergence:
            self.bullish_divergence_count += 1
        else:
            self.bullish_divergence_count = 0
        
        # 检测看跌背离
        bearish_divergence = self._detect_bearish_divergence()
        if bearish_divergence:
            self.bearish_divergence_count += 1
        else:
            self.bearish_divergence_count = 0
        
        # 看涨背离买入信号
        if (self.bullish_divergence_count >= self.params.confirmation_bars and
            not self.has_position()):
            
            confidence = min(1.0, self.bullish_divergence_count / self.params.confirmation_bars)
            reason = f"RSI看涨背离: 价格创新低但RSI未创新低"
            self.emit_signal("BUY", current_price, reason, confidence)
            
            self.bullish_divergence_count = 0  # 重置计数器
        
        # 看跌背离卖出信号
        elif (self.bearish_divergence_count >= self.params.confirmation_bars and
              self.is_long_position()):
            
            confidence = min(1.0, self.bearish_divergence_count / self.params.confirmation_bars)
            reason = f"RSI看跌背离: 价格创新高但RSI未创新高"
            self.emit_signal("SELL", current_price, reason, confidence)
            
            self.bearish_divergence_count = 0  # 重置计数器
    
    def _update_extremes(self):
        """更新价格和RSI的高点低点"""
        lookback = self.params.lookback
        
        # 如果数据不够，直接返回
        if len(self.data) < lookback * 2:
            return
        
        # 寻找价格高点和低点
        highs = []
        lows = []
        rsi_highs = []
        rsi_lows = []
        
        for i in range(lookback, len(self.data)):
            # 检查是否为局部高点
            if i >= lookback and i < len(self.data) - 1:
                is_high = True
                is_low = True
                
                for j in range(max(0, i - lookback), min(len(self.data), i + lookback + 1)):
                    if j != i:
                        if self.data.high[i] <= self.data.high[j]:
                            is_high = False
                        if self.data.low[i] >= self.data.low[j]:
                            is_low = False
                
                if is_high:
                    highs.append((i, self.data.high[i]))
                    rsi_highs.append((i, self.rsi[i]))
                
                if is_low:
                    lows.append((i, self.data.low[i]))
                    rsi_lows.append((i, self.rsi[i]))
        
        # 只保留最近的几个高点和低点
        self.highs = highs[-5:] if len(highs) > 5 else highs
        self.lows = lows[-5:] if len(lows) > 5 else lows
        self.rsi_highs = rsi_highs[-5:] if len(rsi_highs) > 5 else rsi_highs
        self.rsi_lows = rsi_lows[-5:] if len(rsi_lows) > 5 else rsi_lows
    
    def _detect_bullish_divergence(self):
        """检测看涨背离"""
        if len(self.lows) < 2 or len(self.rsi_lows) < 2:
            return False
        
        # 获取最近两个低点
        recent_low = self.lows[-1]
        previous_low = self.lows[-2]
        recent_rsi_low = self.rsi_lows[-1]
        previous_rsi_low = self.rsi_lows[-2]
        
        # 价格创新低，但RSI未创新低
        price_new_low = recent_low[1] < previous_low[1]
        rsi_higher_low = recent_rsi_low[1] > previous_rsi_low[1]
        
        # 检查差值是否足够
        price_diff = abs(recent_low[1] - previous_low[1]) / previous_low[1]
        rsi_diff = abs(recent_rsi_low[1] - previous_rsi_low[1])
        
        return (price_new_low and rsi_higher_low and 
                price_diff >= self.params.min_price_diff and
                rsi_diff >= self.params.min_rsi_diff)
    
    def _detect_bearish_divergence(self):
        """检测看跌背离"""
        if len(self.highs) < 2 or len(self.rsi_highs) < 2:
            return False
        
        # 获取最近两个高点
        recent_high = self.highs[-1]
        previous_high = self.highs[-2]
        recent_rsi_high = self.rsi_highs[-1]
        previous_rsi_high = self.rsi_highs[-2]
        
        # 价格创新高，但RSI未创新高
        price_new_high = recent_high[1] > previous_high[1]
        rsi_lower_high = recent_rsi_high[1] < previous_rsi_high[1]
        
        # 检查差值是否足够
        price_diff = abs(recent_high[1] - previous_high[1]) / previous_high[1]
        rsi_diff = abs(recent_rsi_high[1] - previous_rsi_high[1])
        
        return (price_new_high and rsi_lower_high and 
                price_diff >= self.params.min_price_diff and
                rsi_diff >= self.params.min_rsi_diff)


class RSIBollingerStrategy(BaseStrategy):
    """RSI + 布林带组合策略"""
    
    params = (
        ('rsi_period', 14),           # RSI 周期
        ('bb_period', 20),            # 布林带周期
        ('bb_std', 2),                # 布林带标准差
        ('rsi_oversold', 30),         # RSI 超卖线
        ('rsi_overbought', 70),       # RSI 超买线
        ('volume_factor', 1.5),       # 成交量放大倍数
    )
    
    def __init__(self):
        """初始化 RSI + 布林带策略"""
        super().__init__()
        
        # RSI 指标
        self.rsi = bt.indicators.RelativeStrengthIndex(
            self.data.close, period=self.params.rsi_period
        )
        
        # 布林带指标
        self.bb = bt.indicators.BollingerBands(
            self.data.close, 
            period=self.params.bb_period,
            devfactor=self.params.bb_std
        )
        
        # 成交量均线
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=20
        )
        
        self.logger.info("RSI + 布林带策略初始化完成")
    
    def next(self):
        """策略主逻辑"""
        if len(self.data) < max(self.params.rsi_period, self.params.bb_period):
            return
        
        current_price = self.get_current_price()
        current_rsi = self.rsi[0]
        current_volume = self.data.volume[0]
        
        # 布林带位置
        bb_upper = self.bb.lines.top[0]
        bb_lower = self.bb.lines.bot[0]
        bb_middle = self.bb.lines.mid[0]
        
        # 价格在布林带中的位置（0-1，0.5为中轨）
        bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)
        
        # 成交量确认
        volume_confirmed = current_volume > self.volume_ma[0] * self.params.volume_factor
        
        # 组合买入信号：RSI超卖 + 价格接近布林带下轨 + 成交量放大
        if (current_rsi <= self.params.rsi_oversold and 
            bb_position <= 0.2 and  # 接近下轨
            volume_confirmed and
            not self.has_position()):
            
            # 信号强度基于RSI和布林带位置
            rsi_strength = (self.params.rsi_oversold - current_rsi) / self.params.rsi_oversold
            bb_strength = (0.2 - bb_position) / 0.2
            confidence = min(1.0, (rsi_strength + bb_strength) / 2)
            
            reason = (f"RSI+布林带买入: RSI={current_rsi:.1f}(超卖), "
                     f"布林带位置={bb_position:.2f}(接近下轨)")
            
            self.emit_signal("BUY", current_price, reason, confidence)
        
        # 组合卖出信号：RSI超买 + 价格接近布林带上轨
        elif (current_rsi >= self.params.rsi_overbought and 
              bb_position >= 0.8 and  # 接近上轨
              self.is_long_position()):
            
            rsi_strength = (current_rsi - self.params.rsi_overbought) / (100 - self.params.rsi_overbought)
            bb_strength = (bb_position - 0.8) / 0.2
            confidence = min(1.0, (rsi_strength + bb_strength) / 2)
            
            reason = (f"RSI+布林带卖出: RSI={current_rsi:.1f}(超买), "
                     f"布林带位置={bb_position:.2f}(接近上轨)")
            
            self.emit_signal("SELL", current_price, reason, confidence)
        
        # 调试信息
        self.log_debug(f"RSI: {current_rsi:.1f}, 布林带位置: {bb_position:.2f}, "
                      f"成交量比: {current_volume/self.volume_ma[0]:.2f}")