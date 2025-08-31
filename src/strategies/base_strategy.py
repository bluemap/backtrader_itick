"""
Backtrader 策略基础模块

定义策略基类和通用功能
"""

import backtrader as bt
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass


@dataclass
class TradeSignal:
    """交易信号数据结构"""
    symbol: str
    timestamp: datetime
    action: str  # BUY 或 SELL
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy: str = ""
    confidence: float = 1.0  # 信号置信度 0-1
    volume: Optional[int] = None
    reason: str = ""  # 信号产生原因
    strategy_name: str = ""  # 策略名称（多策略支持）


class BaseStrategy(bt.Strategy):
    """策略基类"""
    
    # 策略参数
    params = (
        ('stop_loss_pct', 0.05),      # 止损百分比
        ('take_profit_pct', 0.10),    # 止盈百分比
        ('max_position_size', 1.0),   # 最大仓位比例
        ('debug', False),             # 调试模式
    )
    
    def __init__(self):
        """初始化策略"""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 信号回调函数列表
        self.signal_callbacks: List[Callable[[TradeSignal], None]] = []
        
        # 当前持仓状态
        self.position_status = {}
        
        # 策略统计（重命名避免与Backtrader内置stats冲突）
        self.strategy_stats = {
            'total_signals': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'last_signal_time': None
        }
        
        if self.params.debug:
            self.logger.setLevel(logging.DEBUG)
    
    def add_signal_callback(self, callback: Callable[[TradeSignal], None]) -> None:
        """
        添加信号回调函数
        
        Args:
            callback: 信号回调函数
        """
        self.signal_callbacks.append(callback)
    
    def emit_signal(self, action: str, price: float, reason: str = "",
                   confidence: float = 1.0, volume: Optional[int] = None, 
                   strategy_name: str = "") -> None:
        """
        发出交易信号
        
        Args:
            action: 交易行为 (BUY/SELL)
            price: 价格
            reason: 信号原因
            confidence: 信号置信度
            volume: 交易量
            strategy_name: 策略名称（多策略支持）
        """
        # 计算止损止盈
        if action == "BUY":
            stop_loss = price * (1 - self.params.stop_loss_pct)
            take_profit = price * (1 + self.params.take_profit_pct)
        else:  # SELL
            stop_loss = price * (1 + self.params.stop_loss_pct)
            take_profit = price * (1 - self.params.take_profit_pct)
        
        # 创建信号
        signal = TradeSignal(
            symbol=self.data._name if hasattr(self.data, '_name') else 'UNKNOWN',
            timestamp=bt.num2date(self.data.datetime[0]),
            action=action,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy=self.__class__.__name__,
            confidence=confidence,
            volume=volume,
            reason=reason,
            strategy_name=strategy_name or self.__class__.__name__
        )
        
        # 更新统计
        self.strategy_stats['total_signals'] += 1
        if action == "BUY":
            self.strategy_stats['buy_signals'] += 1
        else:
            self.strategy_stats['sell_signals'] += 1
        self.strategy_stats['last_signal_time'] = signal.timestamp
        
        # 调用回调函数
        for callback in self.signal_callbacks:
            try:
                callback(signal)
            except Exception as e:
                self.logger.error(f"信号回调函数执行失败: {e}")
        
        # 记录日志
        self.logger.info(f"发出交易信号: {action} {signal.symbol} @ {price:.2f}, "
                        f"止损: {stop_loss:.2f}, 止盈: {take_profit:.2f}, 原因: {reason}")
    
    def get_current_price(self) -> float:
        """获取当前价格"""
        return self.data.close[0]
    
    def get_position_size(self) -> int:
        """获取当前持仓大小"""
        return self.position.size
    
    def is_long_position(self) -> bool:
        """是否持有多头仓位"""
        return self.position.size > 0
    
    def is_short_position(self) -> bool:
        """是否持有空头仓位"""
        return self.position.size < 0
    
    def has_position(self) -> bool:
        """是否有持仓"""
        return self.position.size != 0
    
    def log_debug(self, message: str) -> None:
        """记录调试信息"""
        if self.params.debug:
            self.logger.debug(f"{bt.num2date(self.data.datetime[0])}: {message}")
    
    def log_trade(self, order) -> None:
        """记录交易信息"""
        if order.isbuy():
            action = "BUY"
        elif order.issell():
            action = "SELL"
        else:
            action = "UNKNOWN"
        
        self.logger.info(f"交易执行: {action} {order.executed.size} @ {order.executed.price:.2f}")
    
    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            self.log_trade(order)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.logger.warning(f"订单失败: {order.status}")
    
    def notify_trade(self, trade):
        """交易状态通知"""
        if not trade.isclosed:
            return
        
        self.logger.info(f"交易完成: 盈亏 {trade.pnl:.2f}, 净盈亏 {trade.pnlcomm:.2f}")
    
    def next(self):
        """策略主逻辑 - 子类需要实现"""
        raise NotImplementedError("子类必须实现 next() 方法")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取策略统计信息"""
        return self.strategy_stats.copy()


class DataFeed(bt.feeds.PandasData):
    """自定义数据源"""
    
    params = (
        ('datetime', None),
        ('open', 'open'),
        ('high', 'high'), 
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('openinterest', None),
    )


class StrategyRunner:
    """策略运行器"""
    
    def __init__(self, initial_cash: float = 100000.0, commission: float = 0.001):
        """
        初始化策略运行器
        
        Args:
            initial_cash: 初始资金
            commission: 手续费率
        """
        self.cerebro = bt.Cerebro()
        self.cerebro.broker.setcash(initial_cash)
        self.cerebro.broker.setcommission(commission=commission)
        
        self.logger = logging.getLogger(__name__)
        
        # 添加分析器
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    def add_strategy(self, strategy_class, **kwargs) -> None:
        """
        添加策略
        
        Args:
            strategy_class: 策略类
            **kwargs: 策略参数
        """
        self.cerebro.addstrategy(strategy_class, **kwargs)
        self.logger.info(f"添加策略: {strategy_class.__name__}")
    
    def add_data(self, data, name: str = None) -> None:
        """
        添加数据源
        
        Args:
            data: 数据（pandas DataFrame）
            name: 数据名称
        """
        if name:
            data_feed = DataFeed(dataname=data, name=name)
        else:
            data_feed = DataFeed(dataname=data)
        
        self.cerebro.adddata(data_feed)
        self.logger.info(f"添加数据源: {name or 'Unknown'}")
    
    def run(self) -> List[bt.Strategy]:
        """
        运行回测
        
        Returns:
            List[bt.Strategy]: 策略实例列表
        """
        self.logger.info("开始运行策略...")
        
        start_time = datetime.now()
        results = self.cerebro.run()
        end_time = datetime.now()
        
        self.logger.info(f"策略运行完成，耗时: {end_time - start_time}")
        
        return results
    
    def get_portfolio_value(self) -> float:
        """获取当前组合价值"""
        return self.cerebro.broker.getvalue()
    
    def get_cash(self) -> float:
        """获取当前现金"""
        return self.cerebro.broker.getcash()
    
    def plot(self, **kwargs) -> None:
        """绘制回测结果"""
        try:
            self.cerebro.plot(**kwargs)
        except Exception as e:
            self.logger.error(f"绘图失败: {e}")
    
    def get_analysis_results(self, results: List[bt.Strategy]) -> Dict[str, Any]:
        """
        获取分析结果
        
        Args:
            results: 策略运行结果
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        if not results:
            return {}
        
        strategy = results[0]
        
        analysis = {}
        
        try:
            # 夏普比率
            sharpe = strategy.analyzers.sharpe.get_analysis()
            analysis['sharpe_ratio'] = sharpe.get('sharperatio', 0)
            
            # 最大回撤
            drawdown = strategy.analyzers.drawdown.get_analysis()
            analysis['max_drawdown'] = drawdown.get('max', {}).get('drawdown', 0)
            
            # 收益率
            returns = strategy.analyzers.returns.get_analysis()
            analysis['total_return'] = returns.get('rtot', 0)
            analysis['annual_return'] = returns.get('rnorm', 0)
            
            # 交易统计
            trades = strategy.analyzers.trades.get_analysis()
            analysis['total_trades'] = trades.get('total', {}).get('total', 0)
            analysis['winning_trades'] = trades.get('won', {}).get('total', 0)
            analysis['losing_trades'] = trades.get('lost', {}).get('total', 0)
            
            if analysis['total_trades'] > 0:
                analysis['win_rate'] = analysis['winning_trades'] / analysis['total_trades']
            else:
                analysis['win_rate'] = 0
                
        except Exception as e:
            self.logger.error(f"获取分析结果失败: {e}")
        
        return analysis