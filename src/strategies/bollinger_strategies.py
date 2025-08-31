"""
布林带策略

基于布林带指标的回归和突破策略
"""

import backtrader as bt
from .base_strategy import BaseStrategy


class BollingerBandsStrategy(BaseStrategy):
    """布林带回归策略"""
    
    params = (
        ('period', 20),               # 布林带周期
        ('std_dev', 2),               # 标准差倍数
        ('stop_loss_pct', 0.05),      # 止损百分比
        ('take_profit_pct', 0.08),    # 止盈百分比
        ('volume_threshold', 1.2),    # 成交量阈值倍数
        ('squeeze_threshold', 0.1),   # 窄幅震荡阈值
    )
    
    def __init__(self):
        """初始化布林带策略"""
        super().__init__()
        
        # 布林带指标
        self.bb = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.period,
            devfactor=self.params.std_dev
        )
        
        # 布林带宽度（用于判断震荡或趋势）
        self.bb_width = (self.bb.lines.top - self.bb.lines.bot) / self.bb.lines.mid
        
        # 成交量均线
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=self.params.period
        )
        
        # 价格在布林带中的位置指标
        self.bb_percent = bt.indicators.BollingerBandsPct(
            self.data.close,
            period=self.params.period,
            devfactor=self.params.std_dev
        )
        
        self.logger.info(f"布林带策略初始化完成: 周期={self.params.period}, "
                        f"标准差={self.params.std_dev}")
    
    def next(self):
        """策略主逻辑"""
        if len(self.data) < self.params.period:
            return
        
        current_price = self.get_current_price()
        current_volume = self.data.volume[0]
        
        # 布林带数值
        bb_upper = self.bb.lines.top[0]
        bb_lower = self.bb.lines.bot[0]
        bb_middle = self.bb.lines.mid[0]
        bb_width = self.bb_width[0]
        bb_percent = self.bb_percent[0]
        
        # 成交量确认
        volume_confirmed = current_volume > self.volume_ma[0] * self.params.volume_threshold
        
        # 判断市场状态
        is_squeeze = bb_width < self.params.squeeze_threshold  # 窄幅震荡
        
        # 买入信号：价格触及下轨反弹
        if (bb_percent <= 0.05 and  # 价格接近或触及下轨
            current_price > bb_lower and  # 价格开始反弹
            volume_confirmed and
            not self.has_position()):
            
            # 在震荡市中更倾向于回归交易
            if is_squeeze:
                confidence = 0.8
                reason = f"布林带下轨反弹(震荡市): 价格{current_price:.2f}接近下轨{bb_lower:.2f}"
            else:
                confidence = 0.6
                reason = f"布林带下轨反弹: 价格{current_price:.2f}接近下轨{bb_lower:.2f}"
            
            self.emit_signal("BUY", current_price, reason, confidence)
        
        # 卖出信号：价格触及上轨回落
        elif (bb_percent >= 0.95 and  # 价格接近或触及上轨
              current_price < bb_upper and  # 价格开始回落
              self.is_long_position()):
            
            if is_squeeze:
                confidence = 0.8
                reason = f"布林带上轨回落(震荡市): 价格{current_price:.2f}接近上轨{bb_upper:.2f}"
            else:
                confidence = 0.6
                reason = f"布林带上轨回落: 价格{current_price:.2f}接近上轨{bb_upper:.2f}"
            
            self.emit_signal("SELL", current_price, reason, confidence)
        
        # 中轨支撑/阻力信号
        elif (abs(current_price - bb_middle) / bb_middle < 0.005 and  # 接近中轨
              volume_confirmed):
            
            # 价格从下方接近中轨（可能的阻力）
            if current_price < bb_middle and self.is_long_position():
                confidence = 0.4
                reason = f"布林带中轨阻力: 价格{current_price:.2f}接近中轨{bb_middle:.2f}"
                self.emit_signal("SELL", current_price, reason, confidence)
        
        # 调试信息
        self.log_debug(f"布林带 - 上轨: {bb_upper:.2f}, 中轨: {bb_middle:.2f}, "
                      f"下轨: {bb_lower:.2f}, 宽度: {bb_width:.3f}, "
                      f"位置: {bb_percent:.2f}")


class BollingerBreakoutStrategy(BaseStrategy):
    """布林带突破策略"""
    
    params = (
        ('period', 20),               # 布林带周期
        ('std_dev', 2),               # 标准差倍数
        ('squeeze_period', 10),       # 窄幅震荡判断周期
        ('breakout_volume', 2.0),     # 突破确认成交量倍数
        ('min_squeeze_bars', 5),      # 最小震荡K线数
        ('atr_period', 14),           # ATR周期
    )
    
    def __init__(self):
        """初始化布林带突破策略"""
        super().__init__()
        
        # 布林带指标
        self.bb = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.period,
            devfactor=self.params.std_dev
        )
        
        # 布林带宽度
        self.bb_width = (self.bb.lines.top - self.bb.lines.bot) / self.bb.lines.mid
        
        # ATR指标（用于动态止损）
        self.atr = bt.indicators.AverageTrueRange(period=self.params.atr_period)
        
        # 成交量均线
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=20
        )
        
        # 记录窄幅震荡状态
        self.squeeze_count = 0
        self.min_bb_width = float('inf')
        
        self.logger.info("布林带突破策略初始化完成")
    
    def next(self):
        """策略主逻辑"""
        if len(self.data) < max(self.params.period, self.params.atr_period):
            return
        
        current_price = self.get_current_price()
        current_volume = self.data.volume[0]
        
        # 布林带数值
        bb_upper = self.bb.lines.top[0]
        bb_lower = self.bb.lines.bot[0]
        bb_middle = self.bb.lines.mid[0]
        bb_width = self.bb_width[0]
        
        # 更新窄幅震荡状态
        self._update_squeeze_status(bb_width)
        
        # 成交量突破确认
        volume_breakout = current_volume > self.volume_ma[0] * self.params.breakout_volume
        
        # 向上突破信号
        if (current_price > bb_upper and  # 价格突破上轨
            self.squeeze_count >= self.params.min_squeeze_bars and  # 经历了足够的震荡
            volume_breakout and  # 成交量确认
            not self.has_position()):
            
            # 使用ATR计算动态止损
            atr_stop_loss = self.atr[0] * 2 / current_price
            self.params.stop_loss_pct = min(0.1, atr_stop_loss)  # 最大10%止损
            
            confidence = min(1.0, self.squeeze_count / self.params.min_squeeze_bars)
            reason = (f"布林带向上突破: 价格{current_price:.2f}突破上轨{bb_upper:.2f}, "
                     f"震荡{self.squeeze_count}根K线")
            
            self.emit_signal("BUY", current_price, reason, confidence)
            self.squeeze_count = 0  # 重置震荡计数
        
        # 向下突破信号（如果持有多头仓位）
        elif (current_price < bb_lower and  # 价格跌破下轨
              volume_breakout and
              self.is_long_position()):
            
            confidence = 0.8
            reason = f"布林带向下突破: 价格{current_price:.2f}跌破下轨{bb_lower:.2f}"
            
            self.emit_signal("SELL", current_price, reason, confidence)
        
        # 中轨突破确认信号
        elif (self.squeeze_count > 0 and  # 刚结束震荡
              ((current_price > bb_middle and self.data.close[-1] <= bb_middle) or  # 向上突破中轨
               (current_price < bb_middle and self.data.close[-1] >= bb_middle)) and  # 向下突破中轨
              volume_breakout):
            
            if current_price > bb_middle and not self.has_position():
                confidence = 0.6
                reason = f"中轨向上突破: 价格{current_price:.2f}突破中轨{bb_middle:.2f}"
                self.emit_signal("BUY", current_price, reason, confidence)
            
            elif current_price < bb_middle and self.is_long_position():
                confidence = 0.6
                reason = f"中轨向下突破: 价格{current_price:.2f}跌破中轨{bb_middle:.2f}"
                self.emit_signal("SELL", current_price, reason, confidence)
        
        # 调试信息
        self.log_debug(f"布林带突破 - 价格: {current_price:.2f}, 上轨: {bb_upper:.2f}, "
                      f"下轨: {bb_lower:.2f}, 宽度: {bb_width:.3f}, "
                      f"震荡计数: {self.squeeze_count}")
    
    def _update_squeeze_status(self, bb_width):
        """更新窄幅震荡状态"""
        # 计算最近10个周期的平均宽度
        if len(self.data) >= self.params.squeeze_period:
            recent_widths = [self.bb_width[-i] for i in range(self.params.squeeze_period)]
            avg_width = sum(recent_widths) / len(recent_widths)
            
            # 当前宽度小于平均宽度的80%时认为是窄幅震荡
            if bb_width < avg_width * 0.8:
                self.squeeze_count += 1
                self.min_bb_width = min(self.min_bb_width, bb_width)
            else:
                # 窄幅震荡结束
                if self.squeeze_count > 0:
                    self.logger.info(f"窄幅震荡结束: 持续{self.squeeze_count}根K线, "
                                   f"最小宽度: {self.min_bb_width:.3f}")
                
                self.squeeze_count = 0
                self.min_bb_width = float('inf')


class BollingerMeanReversionStrategy(BaseStrategy):
    """布林带均值回归策略"""
    
    params = (
        ('period', 20),               # 布林带周期
        ('std_dev', 2),               # 标准差倍数
        ('rsi_period', 14),           # RSI周期
        ('rsi_oversold', 30),         # RSI超卖线
        ('rsi_overbought', 70),       # RSI超买线
        ('ma_trend_period', 50),      # 趋势均线周期
    )
    
    def __init__(self):
        """初始化布林带均值回归策略"""
        super().__init__()
        
        # 布林带指标
        self.bb = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.period,
            devfactor=self.params.std_dev
        )
        
        # RSI指标
        self.rsi = bt.indicators.RelativeStrengthIndex(
            self.data.close, period=self.params.rsi_period
        )
        
        # 趋势过滤均线
        self.trend_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.ma_trend_period
        )
        
        # 布林带百分比位置
        self.bb_percent = bt.indicators.BollingerBandsPct(
            self.data.close,
            period=self.params.period,
            devfactor=self.params.std_dev
        )
        
        self.logger.info("布林带均值回归策略初始化完成")
    
    def next(self):
        """策略主逻辑"""
        if len(self.data) < max(self.params.period, self.params.rsi_period, 
                               self.params.ma_trend_period):
            return
        
        current_price = self.get_current_price()
        current_rsi = self.rsi[0]
        bb_percent = self.bb_percent[0]
        
        # 趋势判断
        uptrend = current_price > self.trend_ma[0]
        downtrend = current_price < self.trend_ma[0]
        
        # 布林带位置
        bb_upper = self.bb.lines.top[0]
        bb_lower = self.bb.lines.bot[0]
        bb_middle = self.bb.lines.mid[0]
        
        # 均值回归买入信号：
        # 1. 价格接近下轨
        # 2. RSI超卖
        # 3. 整体趋势向上（或震荡）
        if (bb_percent <= 0.1 and  # 价格在下轨附近
            current_rsi <= self.params.rsi_oversold and  # RSI超卖
            uptrend and  # 趋势向上
            not self.has_position()):
            
            # 信号强度计算
            bb_strength = (0.1 - bb_percent) / 0.1  # 越接近下轨强度越大
            rsi_strength = (self.params.rsi_oversold - current_rsi) / self.params.rsi_oversold
            confidence = min(1.0, (bb_strength + rsi_strength) / 2)
            
            reason = (f"均值回归买入: 价格{current_price:.2f}接近下轨{bb_lower:.2f}, "
                     f"RSI={current_rsi:.1f}超卖")
            
            self.emit_signal("BUY", current_price, reason, confidence)
        
        # 回归中轨卖出信号：价格回到中轨附近
        elif (abs(bb_percent - 0.5) <= 0.1 and  # 价格回到中轨附近
              self.is_long_position() and
              current_price > self.data.close[-5]):  # 价格近期上涨
            
            confidence = 0.6
            reason = f"回归中轨: 价格{current_price:.2f}回到中轨{bb_middle:.2f}附近"
            
            self.emit_signal("SELL", current_price, reason, confidence)
        
        # 极端位置卖出信号：
        # 1. 价格接近上轨
        # 2. RSI超买
        elif (bb_percent >= 0.9 and  # 价格接近上轨
              current_rsi >= self.params.rsi_overbought and  # RSI超买
              self.is_long_position()):
            
            bb_strength = (bb_percent - 0.9) / 0.1
            rsi_strength = (current_rsi - self.params.rsi_overbought) / (100 - self.params.rsi_overbought)
            confidence = min(1.0, (bb_strength + rsi_strength) / 2)
            
            reason = (f"极端位置卖出: 价格{current_price:.2f}接近上轨{bb_upper:.2f}, "
                     f"RSI={current_rsi:.1f}超买")
            
            self.emit_signal("SELL", current_price, reason, confidence)
        
        # 调试信息
        self.log_debug(f"均值回归 - 布林带位置: {bb_percent:.2f}, RSI: {current_rsi:.1f}, "
                      f"趋势: {'上涨' if uptrend else '下跌' if downtrend else '震荡'}")