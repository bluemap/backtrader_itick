"""
突破策略

基于价格突破关键支撑阻力位的策略
"""

import backtrader as bt
from .base_strategy import BaseStrategy


class BreakoutStrategy(BaseStrategy):
    """价格突破策略"""
    
    params = (
        ('period', 20),               # 突破判断周期
        ('volume_factor', 1.5),       # 成交量确认倍数
        ('min_breakout_pct', 0.02),   # 最小突破幅度
        ('stop_loss_pct', 0.05),      # 止损百分比
        ('take_profit_pct', 0.12),    # 止盈百分比
        ('consolidation_bars', 10),   # 盘整最小K线数
        ('atr_period', 14),           # ATR周期
    )
    
    def __init__(self):
        """初始化突破策略"""
        super().__init__()
        
        # 最高价和最低价指标
        self.highest = bt.indicators.Highest(
            self.data.high, period=self.params.period
        )
        self.lowest = bt.indicators.Lowest(
            self.data.low, period=self.params.period
        )
        
        # ATR指标
        self.atr = bt.indicators.AverageTrueRange(period=self.params.atr_period)
        
        # 成交量均线
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=self.params.period
        )
        
        # 价格范围和波动率
        self.price_range = self.highest - self.lowest
        self.range_pct = self.price_range / self.data.close
        
        # 盘整状态计数
        self.consolidation_count = 0
        self.last_breakout_bar = 0
        
        self.logger.info(f"突破策略初始化完成: 周期={self.params.period}")
    
    def next(self):
        """策略主逻辑"""
        if len(self.data) < max(self.params.period, self.params.atr_period):
            return
        
        current_price = self.get_current_price()
        current_volume = self.data.volume[0]
        
        # 支撑阻力位
        resistance = self.highest[0]
        support = self.lowest[0]
        price_range = resistance - support
        
        # 更新盘整状态
        self._update_consolidation_status(current_price, support, resistance)
        
        # 成交量确认
        volume_breakout = current_volume > self.volume_ma[0] * self.params.volume_factor
        
        # 防止重复信号
        bars_since_last_signal = len(self.data) - self.last_breakout_bar
        
        # 向上突破信号
        if (current_price > resistance and  # 突破阻力位
            (current_price - resistance) / resistance >= self.params.min_breakout_pct and  # 突破幅度足够
            self.consolidation_count >= self.params.consolidation_bars and  # 经历了足够的盘整
            volume_breakout and  # 成交量确认
            bars_since_last_signal > 5 and  # 避免重复信号
            not self.has_position()):
            
            # 使用ATR计算动态止损
            atr_stop = self.atr[0] * 2
            dynamic_stop_loss = min(0.08, atr_stop / current_price)
            self.params.stop_loss_pct = dynamic_stop_loss
            
            # 信号强度计算
            breakout_strength = (current_price - resistance) / price_range
            consolidation_strength = min(1.0, self.consolidation_count / self.params.consolidation_bars)
            volume_strength = min(1.0, current_volume / (self.volume_ma[0] * self.params.volume_factor))
            
            confidence = min(1.0, (breakout_strength + consolidation_strength + volume_strength) / 3)
            
            reason = (f"向上突破: 价格{current_price:.2f}突破阻力位{resistance:.2f}, "
                     f"盘整{self.consolidation_count}根K线")
            
            self.emit_signal("BUY", current_price, reason, confidence)
            self.last_breakout_bar = len(self.data)
            self.consolidation_count = 0
        
        # 向下突破信号（止损）
        elif (current_price < support and  # 跌破支撑位
              (support - current_price) / support >= self.params.min_breakout_pct and
              volume_breakout and
              self.is_long_position()):
            
            confidence = 0.8
            reason = f"向下突破止损: 价格{current_price:.2f}跌破支撑位{support:.2f}"
            
            self.emit_signal("SELL", current_price, reason, confidence)
            self.last_breakout_bar = len(self.data)
        
        # 调试信息
        self.log_debug(f"突破监控 - 阻力: {resistance:.2f}, 支撑: {support:.2f}, "
                      f"当前价: {current_price:.2f}, 盘整: {self.consolidation_count}根")
    
    def _update_consolidation_status(self, current_price, support, resistance):
        """更新盘整状态"""
        price_range = resistance - support
        
        # 判断是否在盘整区间内
        if price_range > 0:
            position_in_range = (current_price - support) / price_range
            
            # 价格在支撑阻力区间的20%-80%之间认为是盘整
            if 0.2 <= position_in_range <= 0.8:
                self.consolidation_count += 1
            else:
                # 重置盘整计数
                if self.consolidation_count > 0:
                    self.logger.debug(f"盘整结束，持续了{self.consolidation_count}根K线")
                self.consolidation_count = 0


class DonchianBreakoutStrategy(BaseStrategy):
    """唐奇安通道突破策略"""
    
    params = (
        ('entry_period', 20),         # 入场通道周期
        ('exit_period', 10),          # 出场通道周期
        ('atr_period', 14),           # ATR周期
        ('atr_multiplier', 2.0),      # ATR止损倍数
        ('volume_filter', True),      # 是否启用成交量过滤
        ('trend_filter', True),       # 是否启用趋势过滤
        ('trend_period', 50),         # 趋势均线周期
    )
    
    def __init__(self):
        """初始化唐奇安通道突破策略"""
        super().__init__()
        
        # 入场通道
        self.entry_high = bt.indicators.Highest(
            self.data.high, period=self.params.entry_period
        )
        self.entry_low = bt.indicators.Lowest(
            self.data.low, period=self.params.entry_period
        )
        
        # 出场通道
        self.exit_high = bt.indicators.Highest(
            self.data.high, period=self.params.exit_period
        )
        self.exit_low = bt.indicators.Lowest(
            self.data.low, period=self.params.exit_period
        )
        
        # ATR指标
        self.atr = bt.indicators.AverageTrueRange(period=self.params.atr_period)
        
        # 趋势过滤
        if self.params.trend_filter:
            self.trend_ma = bt.indicators.SimpleMovingAverage(
                self.data.close, period=self.params.trend_period
            )
        
        # 成交量过滤
        if self.params.volume_filter:
            self.volume_ma = bt.indicators.SimpleMovingAverage(
                self.data.volume, period=20
            )
        
        self.logger.info("唐奇安通道突破策略初始化完成")
    
    def next(self):
        """策略主逻辑"""
        if len(self.data) < max(self.params.entry_period, self.params.atr_period):
            return
        
        current_price = self.get_current_price()
        
        # 通道边界
        entry_upper = self.entry_high[0]
        entry_lower = self.entry_low[0]
        exit_upper = self.exit_high[0]
        exit_lower = self.exit_low[0]
        
        # 趋势过滤
        if self.params.trend_filter and len(self.data) >= self.params.trend_period:
            uptrend = current_price > self.trend_ma[0]
            downtrend = current_price < self.trend_ma[0]
        else:
            uptrend = downtrend = True
        
        # 成交量过滤
        if self.params.volume_filter:
            volume_ok = self.data.volume[0] > self.volume_ma[0] * 1.2
        else:
            volume_ok = True
        
        # 动态止损
        atr_stop = self.atr[0] * self.params.atr_multiplier
        
        # 向上突破入场
        if (current_price > entry_upper and  # 突破上通道
            uptrend and volume_ok and
            not self.has_position()):
            
            # 设置动态止损
            stop_loss_price = current_price - atr_stop
            self.params.stop_loss_pct = (current_price - stop_loss_price) / current_price
            
            confidence = 0.8
            reason = f"唐奇安上轨突破: 价格{current_price:.2f}突破{entry_upper:.2f}"
            
            self.emit_signal("BUY", current_price, reason, confidence)
        
        # 向下突破出场（使用出场通道）
        elif (current_price < exit_lower and  # 跌破下出场通道
              self.is_long_position()):
            
            confidence = 0.9
            reason = f"唐奇安下轨出场: 价格{current_price:.2f}跌破{exit_lower:.2f}"
            
            self.emit_signal("SELL", current_price, reason, confidence)
        
        # ATR止损
        elif self.is_long_position():
            # 计算移动止损位
            trailing_stop = current_price - atr_stop
            
            # 如果价格跌破移动止损位
            if current_price < trailing_stop:
                confidence = 0.7
                reason = f"ATR移动止损: 价格{current_price:.2f}跌破止损位{trailing_stop:.2f}"
                
                self.emit_signal("SELL", current_price, reason, confidence)
        
        # 调试信息
        self.log_debug(f"唐奇安通道 - 入场上轨: {entry_upper:.2f}, 入场下轨: {entry_lower:.2f}, "
                      f"出场下轨: {exit_lower:.2f}, ATR: {self.atr[0]:.2f}")


class VolatilityBreakoutStrategy(BaseStrategy):
    """波动率突破策略"""
    
    params = (
        ('lookback', 20),             # 回看周期
        ('volatility_threshold', 2.0), # 波动率阈值倍数
        ('atr_period', 14),           # ATR周期
        ('volume_factor', 1.8),       # 成交量倍数
        ('min_consolidation', 5),     # 最小盘整周期
        ('max_holding_days', 10),     # 最大持仓天数
    )
    
    def __init__(self):
        """初始化波动率突破策略"""
        super().__init__()
        
        # ATR指标
        self.atr = bt.indicators.AverageTrueRange(period=self.params.atr_period)
        
        # 历史波动率
        self.returns = bt.indicators.PctChange(self.data.close, period=1)
        self.volatility = bt.indicators.StandardDeviation(
            self.returns, period=self.params.lookback
        )
        
        # 平均波动率
        self.avg_volatility = bt.indicators.SimpleMovingAverage(
            self.volatility, period=self.params.lookback
        )
        
        # 成交量均线
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=self.params.lookback
        )
        
        # 价格通道
        self.highest = bt.indicators.Highest(
            self.data.high, period=self.params.lookback
        )
        self.lowest = bt.indicators.Lowest(
            self.data.low, period=self.params.lookback
        )
        
        # 持仓计数器
        self.holding_days = 0
        self.entry_price = 0
        
        self.logger.info("波动率突破策略初始化完成")
    
    def next(self):
        """策略主逻辑"""
        if len(self.data) < max(self.params.lookback, self.params.atr_period):
            return
        
        current_price = self.get_current_price()
        current_volatility = self.volatility[0]
        avg_vol = self.avg_volatility[0]
        
        # 波动率突破判断
        vol_breakout = current_volatility > avg_vol * self.params.volatility_threshold
        
        # 价格通道
        upper_channel = self.highest[0]
        lower_channel = self.lowest[0]
        
        # 成交量确认
        volume_surge = self.data.volume[0] > self.volume_ma[0] * self.params.volume_factor
        
        # 价格变化幅度
        price_change = abs(current_price - self.data.close[-1]) / self.data.close[-1]
        
        # 更新持仓天数
        if self.has_position():
            self.holding_days += 1
        else:
            self.holding_days = 0
        
        # 波动率突破买入信号
        if (vol_breakout and  # 波动率突破
            volume_surge and  # 成交量突破
            current_price > upper_channel and  # 价格突破上轨
            price_change > 0.03 and  # 单日涨幅超过3%
            not self.has_position()):
            
            # 设置基于ATR的止损
            atr_stop_loss = self.atr[0] * 2 / current_price
            self.params.stop_loss_pct = min(0.1, atr_stop_loss)
            
            # 信号强度
            vol_strength = min(1.0, current_volatility / (avg_vol * self.params.volatility_threshold))
            volume_strength = min(1.0, self.data.volume[0] / (self.volume_ma[0] * self.params.volume_factor))
            price_strength = min(1.0, price_change / 0.05)
            
            confidence = (vol_strength + volume_strength + price_strength) / 3
            
            reason = (f"波动率突破: 当前波动率{current_volatility:.3f}vs平均{avg_vol:.3f}, "
                     f"涨幅{price_change:.2%}")
            
            self.emit_signal("BUY", current_price, reason, confidence)
            self.entry_price = current_price
        
        # 波动率回落或达到最大持仓天数卖出
        elif self.is_long_position():
            # 波动率回落到正常水平
            vol_normalized = current_volatility <= avg_vol * 1.2
            
            # 达到最大持仓天数
            max_holding_reached = self.holding_days >= self.params.max_holding_days
            
            # 价格跌破下轨
            price_breakdown = current_price < lower_channel
            
            if vol_normalized or max_holding_reached or price_breakdown:
                if vol_normalized:
                    reason = f"波动率回落: 当前{current_volatility:.3f}回落到正常水平"
                    confidence = 0.6
                elif max_holding_reached:
                    reason = f"达到最大持仓天数: {self.holding_days}天"
                    confidence = 0.7
                else:
                    reason = f"价格跌破下轨: {current_price:.2f} < {lower_channel:.2f}"
                    confidence = 0.8
                
                self.emit_signal("SELL", current_price, reason, confidence)
        
        # 调试信息
        self.log_debug(f"波动率 - 当前: {current_volatility:.3f}, 平均: {avg_vol:.3f}, "
                      f"倍数: {current_volatility/avg_vol:.2f}, 持仓天数: {self.holding_days}")