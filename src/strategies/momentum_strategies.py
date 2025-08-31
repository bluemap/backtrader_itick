"""
动量策略

基于价格和成交量动量的策略
"""

import backtrader as bt
from .base_strategy import BaseStrategy


class MomentumStrategy(BaseStrategy):
    """动量策略"""
    
    params = (
        ('period', 10),               # 动量计算周期
        ('threshold', 0.02),          # 动量阈值
        ('stop_loss_pct', 0.06),      # 止损百分比
        ('take_profit_pct', 0.15),    # 止盈百分比
        ('volume_factor', 1.3),       # 成交量确认倍数
        ('rsi_period', 14),           # RSI周期
        ('rsi_threshold', 50),        # RSI中性线
    )
    
    def __init__(self):
        """初始化动量策略"""
        super().__init__()
        
        # 价格动量
        self.price_momentum = bt.indicators.Momentum(
            self.data.close, period=self.params.period
        )
        
        # 百分比价格动量
        self.price_momentum_pct = (self.data.close - self.data.close(-self.params.period)) / self.data.close(-self.params.period)
        
        # 成交量动量
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=self.params.period
        )
        
        # RSI指标
        self.rsi = bt.indicators.RelativeStrengthIndex(
            self.data.close, period=self.params.rsi_period
        )
        
        # 价格变化率
        self.rate_of_change = bt.indicators.RateOfChange(
            self.data.close, period=self.params.period
        )
        
        # 均线
        self.ma_short = bt.indicators.SimpleMovingAverage(
            self.data.close, period=10
        )
        self.ma_long = bt.indicators.SimpleMovingAverage(
            self.data.close, period=30
        )
        
        self.logger.info(f"动量策略初始化完成: 周期={self.params.period}, "
                        f"阈值={self.params.threshold}")
    
    def next(self):
        """策略主逻辑"""
        if len(self.data) < max(self.params.period, self.params.rsi_period, 30):
            return
        
        current_price = self.get_current_price()
        price_momentum = self.price_momentum_pct[0]
        current_volume = self.data.volume[0]
        current_rsi = self.rsi[0]
        roc = self.rate_of_change[0]
        
        # 成交量确认
        volume_confirmed = current_volume > self.volume_ma[0] * self.params.volume_factor
        
        # 趋势确认
        uptrend = self.ma_short[0] > self.ma_long[0]
        
        # 正向动量买入信号
        if (price_momentum > self.params.threshold and  # 正向动量
            current_rsi > self.params.rsi_threshold and  # RSI确认
            uptrend and  # 趋势确认
            volume_confirmed and  # 成交量确认
            not self.has_position()):
            
            # 信号强度计算
            momentum_strength = min(1.0, price_momentum / (self.params.threshold * 2))
            rsi_strength = (current_rsi - self.params.rsi_threshold) / (100 - self.params.rsi_threshold)
            volume_strength = min(1.0, current_volume / (self.volume_ma[0] * self.params.volume_factor))
            
            confidence = (momentum_strength + rsi_strength + volume_strength) / 3
            
            reason = (f"正向动量: 价格动量{price_momentum:.2%}, RSI={current_rsi:.1f}, "
                     f"ROC={roc:.2%}")
            
            self.emit_signal("BUY", current_price, reason, confidence)
        
        # 负向动量卖出信号
        elif (price_momentum < -self.params.threshold and  # 负向动量
              self.is_long_position()):
            
            momentum_strength = min(1.0, abs(price_momentum) / (self.params.threshold * 2))
            confidence = momentum_strength
            
            reason = f"负向动量: 价格动量{price_momentum:.2%}, ROC={roc:.2%}"
            
            self.emit_signal("SELL", current_price, reason, confidence)
        
        # 动量衰减卖出信号
        elif (price_momentum < self.params.threshold / 2 and  # 动量衰减
              current_rsi < self.params.rsi_threshold and  # RSI回落
              self.is_long_position()):
            
            confidence = 0.6
            reason = f"动量衰减: 价格动量{price_momentum:.2%}, RSI={current_rsi:.1f}"
            
            self.emit_signal("SELL", current_price, reason, confidence)
        
        # 调试信息
        self.log_debug(f"动量状态 - 价格动量: {price_momentum:.2%}, RSI: {current_rsi:.1f}, "
                      f"ROC: {roc:.2%}, 成交量比: {current_volume/self.volume_ma[0]:.2f}")


class AcceleratedMomentumStrategy(BaseStrategy):
    """加速动量策略"""
    
    params = (
        ('fast_period', 5),           # 快速动量周期
        ('slow_period', 20),          # 慢速动量周期
        ('acceleration_threshold', 0.5), # 加速度阈值
        ('volume_surge', 2.0),        # 成交量激增倍数
        ('ma_filter', True),          # 均线过滤
        ('ma_period', 50),            # 均线周期
    )
    
    def __init__(self):
        """初始化加速动量策略"""
        super().__init__()
        
        # 快速和慢速动量
        self.fast_momentum = bt.indicators.RateOfChange(
            self.data.close, period=self.params.fast_period
        )
        self.slow_momentum = bt.indicators.RateOfChange(
            self.data.close, period=self.params.slow_period
        )
        
        # 动量加速度（动量的变化率）
        self.momentum_acceleration = self.fast_momentum - self.slow_momentum
        
        # 成交量指标
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=20
        )
        
        # 价格加速度
        self.price_acceleration = bt.indicators.RateOfChange(
            self.fast_momentum, period=3
        )
        
        # 均线过滤器
        if self.params.ma_filter:
            self.ma = bt.indicators.ExponentialMovingAverage(
                self.data.close, period=self.params.ma_period
            )
        
        self.logger.info("加速动量策略初始化完成")
    
    def next(self):
        """策略主逻辑"""
        if len(self.data) < max(self.params.slow_period, self.params.ma_period if self.params.ma_filter else 0):
            return
        
        current_price = self.get_current_price()
        fast_mom = self.fast_momentum[0]
        slow_mom = self.slow_momentum[0]
        acceleration = self.momentum_acceleration[0]
        price_accel = self.price_acceleration[0]
        
        # 成交量激增
        volume_surge = self.data.volume[0] > self.volume_ma[0] * self.params.volume_surge
        
        # 均线趋势过滤
        if self.params.ma_filter:
            uptrend = current_price > self.ma[0]
            strong_uptrend = current_price > self.ma[0] * 1.02
        else:
            uptrend = strong_uptrend = True
        
        # 动量加速买入信号
        if (acceleration > self.params.acceleration_threshold and  # 动量加速
            fast_mom > slow_mom and  # 快速动量大于慢速动量
            fast_mom > 0 and  # 快速动量为正
            price_accel > 0 and  # 价格加速度为正
            strong_uptrend and  # 强势上涨趋势
            volume_surge and  # 成交量激增
            not self.has_position()):
            
            # 信号强度
            acceleration_strength = min(1.0, acceleration / (self.params.acceleration_threshold * 2))
            momentum_strength = min(1.0, fast_mom / 10)  # 假设10%为强动量
            volume_strength = min(1.0, self.data.volume[0] / (self.volume_ma[0] * self.params.volume_surge))
            
            confidence = (acceleration_strength + momentum_strength + volume_strength) / 3
            
            reason = (f"动量加速: 快速动量{fast_mom:.2%}, 慢速动量{slow_mom:.2%}, "
                     f"加速度{acceleration:.2%}")
            
            self.emit_signal("BUY", current_price, reason, confidence)
        
        # 动量减速卖出信号
        elif (acceleration < -self.params.acceleration_threshold and  # 动量减速
              self.is_long_position()):
            
            deceleration_strength = min(1.0, abs(acceleration) / (self.params.acceleration_threshold * 2))
            confidence = deceleration_strength
            
            reason = f"动量减速: 加速度{acceleration:.2%}, 价格加速度{price_accel:.2%}"
            
            self.emit_signal("SELL", current_price, reason, confidence)
        
        # 快速动量转负卖出信号
        elif (fast_mom < 0 and slow_mom < 0 and  # 双重负动量
              self.is_long_position()):
            
            confidence = 0.8
            reason = f"双重负动量: 快速{fast_mom:.2%}, 慢速{slow_mom:.2%}"
            
            self.emit_signal("SELL", current_price, reason, confidence)
        
        # 调试信息
        self.log_debug(f"加速动量 - 快速: {fast_mom:.2%}, 慢速: {slow_mom:.2%}, "
                      f"加速度: {acceleration:.2%}, 价格加速度: {price_accel:.2%}")


class RelativeStrengthMomentumStrategy(BaseStrategy):
    """相对强度动量策略"""
    
    params = (
        ('period', 14),               # 计算周期
        ('benchmark_symbol', 'SPY'),  # 基准指数符号（此处简化处理）
        ('outperformance_threshold', 0.02), # 超越阈值
        ('momentum_period', 10),      # 动量周期
        ('volume_confirmation', True), # 成交量确认
    )
    
    def __init__(self):
        """初始化相对强度动量策略"""
        super().__init__()
        
        # 价格动量
        self.price_momentum = bt.indicators.RateOfChange(
            self.data.close, period=self.params.momentum_period
        )
        
        # 相对强度（这里简化为价格相对于均线的强度）
        self.ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.period
        )
        self.relative_strength = (self.data.close - self.ma) / self.ma
        
        # 相对强度动量
        self.rs_momentum = bt.indicators.RateOfChange(
            self.relative_strength, period=self.params.momentum_period
        )
        
        # 成交量相对强度
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=self.params.period
        )
        self.volume_rs = self.data.volume / self.volume_ma
        
        # 多时间框架强度
        self.short_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=5
        )
        self.medium_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=20
        )
        self.long_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=60
        )
        
        self.logger.info("相对强度动量策略初始化完成")
    
    def next(self):
        """策略主逻辑"""
        if len(self.data) < max(self.params.period, self.params.momentum_period, 60):
            return
        
        current_price = self.get_current_price()
        price_mom = self.price_momentum[0]
        rs = self.relative_strength[0]
        rs_mom = self.rs_momentum[0]
        vol_rs = self.volume_rs[0]
        
        # 多时间框架强度确认
        short_strength = (current_price - self.short_ma[0]) / self.short_ma[0]
        medium_strength = (current_price - self.medium_ma[0]) / self.medium_ma[0]
        long_strength = (current_price - self.long_ma[0]) / self.long_ma[0]
        
        # 综合强度评分
        strength_score = (short_strength * 0.5 + medium_strength * 0.3 + long_strength * 0.2)
        
        # 成交量确认
        if self.params.volume_confirmation:
            volume_ok = vol_rs > 1.2
        else:
            volume_ok = True
        
        # 强势动量买入信号
        if (rs > self.params.outperformance_threshold and  # 相对强度超越阈值
            rs_mom > 0 and  # 相对强度动量为正
            price_mom > 0 and  # 价格动量为正
            strength_score > 0.02 and  # 综合强度为正
            volume_ok and  # 成交量确认
            not self.has_position()):
            
            # 信号强度
            rs_strength = min(1.0, rs / (self.params.outperformance_threshold * 2))
            momentum_strength = min(1.0, price_mom / 0.05)  # 5%作为强动量标准
            score_strength = min(1.0, strength_score / 0.05)
            
            confidence = (rs_strength + momentum_strength + score_strength) / 3
            
            reason = (f"相对强势动量: 相对强度{rs:.2%}, 强度动量{rs_mom:.2%}, "
                     f"价格动量{price_mom:.2%}")
            
            self.emit_signal("BUY", current_price, reason, confidence)
        
        # 相对强度衰减卖出信号
        elif (rs < 0 and  # 相对强度转负
              rs_mom < -0.01 and  # 相对强度动量明显为负
              self.is_long_position()):
            
            weakness_strength = min(1.0, abs(rs_mom) / 0.02)
            confidence = weakness_strength
            
            reason = f"相对强度衰减: 相对强度{rs:.2%}, 强度动量{rs_mom:.2%}"
            
            self.emit_signal("SELL", current_price, reason, confidence)
        
        # 综合弱势卖出信号
        elif (strength_score < -0.02 and  # 综合强度为负
              price_mom < 0 and  # 价格动量为负
              self.is_long_position()):
            
            confidence = 0.7
            reason = f"综合弱势: 强度评分{strength_score:.2%}, 价格动量{price_mom:.2%}"
            
            self.emit_signal("SELL", current_price, reason, confidence)
        
        # 调试信息
        self.log_debug(f"相对强度 - RS: {rs:.2%}, RS动量: {rs_mom:.2%}, "
                      f"价格动量: {price_mom:.2%}, 强度评分: {strength_score:.2%}")


class TrendFollowingMomentumStrategy(BaseStrategy):
    """趋势跟随动量策略"""
    
    params = (
        ('trend_period', 50),         # 趋势判断周期
        ('momentum_period', 14),      # 动量计算周期
        ('adx_period', 14),           # ADX周期
        ('adx_threshold', 25),        # ADX阈值
        ('momentum_threshold', 0.03), # 动量阈值
        ('pullback_threshold', 0.618), # 回撤阈值（斐波那契）
    )
    
    def __init__(self):
        """初始化趋势跟随动量策略"""
        super().__init__()
        
        # 趋势指标
        self.trend_ma = bt.indicators.ExponentialMovingAverage(
            self.data.close, period=self.params.trend_period
        )
        
        # 动量指标
        self.momentum = bt.indicators.RateOfChange(
            self.data.close, period=self.params.momentum_period
        )
        
        # ADX趋势强度指标
        self.adx = bt.indicators.AverageDirectionalMovementIndex(
            self.data, period=self.params.adx_period
        )
        
        # 短期回撤指标
        self.highest = bt.indicators.Highest(
            self.data.high, period=20
        )
        self.pullback_ratio = (self.highest - self.data.close) / (self.highest - self.trend_ma)
        
        # 多重确认均线
        self.ma_fast = bt.indicators.ExponentialMovingAverage(
            self.data.close, period=12
        )
        self.ma_medium = bt.indicators.ExponentialMovingAverage(
            self.data.close, period=26
        )
        
        self.logger.info("趋势跟随动量策略初始化完成")
    
    def next(self):
        """策略主逻辑"""
        if len(self.data) < max(self.params.trend_period, self.params.adx_period):
            return
        
        current_price = self.get_current_price()
        momentum = self.momentum[0]
        adx_value = self.adx[0]
        pullback = self.pullback_ratio[0]
        
        # 趋势判断
        uptrend = current_price > self.trend_ma[0]
        strong_trend = adx_value > self.params.adx_threshold
        
        # 均线排列确认
        bullish_alignment = self.ma_fast[0] > self.ma_medium[0] > self.trend_ma[0]
        
        # 回撤买入机会
        pullback_opportunity = (0.382 <= pullback <= self.params.pullback_threshold and
                               pullback > 0)
        
        # 趋势跟随买入信号
        if (uptrend and  # 上升趋势
            strong_trend and  # 趋势强劲
            momentum > self.params.momentum_threshold and  # 动量充足
            bullish_alignment and  # 均线多头排列
            not self.has_position()):
            
            # 信号强度
            trend_strength = min(1.0, (current_price - self.trend_ma[0]) / self.trend_ma[0] / 0.1)
            momentum_strength = min(1.0, momentum / (self.params.momentum_threshold * 2))
            adx_strength = min(1.0, (adx_value - self.params.adx_threshold) / 25)
            
            confidence = (trend_strength + momentum_strength + adx_strength) / 3
            
            reason = f"趋势跟随: 动量{momentum:.2%}, ADX={adx_value:.1f}, 趋势强度{trend_strength:.2f}"
            
            self.emit_signal("BUY", current_price, reason, confidence)
        
        # 回撤买入信号
        elif (uptrend and strong_trend and
              pullback_opportunity and
              momentum > 0 and  # 动量仍为正
              not self.has_position()):
            
            confidence = 0.7
            reason = f"趋势回撤买入: 回撤比例{pullback:.2f}, 动量{momentum:.2%}"
            
            self.emit_signal("BUY", current_price, reason, confidence)
        
        # 趋势反转卖出信号
        elif (not uptrend and  # 趋势反转
              momentum < -self.params.momentum_threshold and  # 负动量
              self.is_long_position()):
            
            confidence = 0.9
            reason = f"趋势反转: 价格跌破趋势线, 负动量{momentum:.2%}"
            
            self.emit_signal("SELL", current_price, reason, confidence)
        
        # 趋势减弱卖出信号
        elif (adx_value < self.params.adx_threshold and  # 趋势减弱
              momentum < self.params.momentum_threshold / 2 and  # 动量衰减
              self.is_long_position()):
            
            confidence = 0.6
            reason = f"趋势减弱: ADX={adx_value:.1f}, 动量{momentum:.2%}"
            
            self.emit_signal("SELL", current_price, reason, confidence)
        
        # 调试信息
        self.log_debug(f"趋势跟随 - 动量: {momentum:.2%}, ADX: {adx_value:.1f}, "
                      f"回撤比: {pullback:.2f}, 趋势: {'上涨' if uptrend else '下跌'}")