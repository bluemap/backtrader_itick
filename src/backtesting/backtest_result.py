"""
回测结果数据结构

定义回测过程中的交易记录和回测结果
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class OrderType(Enum):
    """订单类型"""
    BUY = "买入"
    SELL = "卖出"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "待执行"
    FILLED = "已成交"
    CANCELLED = "已取消"


@dataclass
class TradeRecord:
    """交易记录"""
    timestamp: datetime
    symbol: str
    order_type: OrderType
    price: float
    quantity: int
    amount: float  # 交易金额
    strategy: str
    reason: str  # 买卖原因
    status: OrderStatus = OrderStatus.FILLED
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': self.symbol,
            'order_type': self.order_type.value,
            'price': self.price,
            'quantity': self.quantity,
            'amount': self.amount,
            'strategy': self.strategy,
            'reason': self.reason,
            'status': self.status.value
        }


@dataclass
class PositionRecord:
    """持仓记录"""
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    unrealized_pnl: float
    
    @property
    def market_value(self) -> float:
        """市值"""
        return self.quantity * self.current_price
    
    @property
    def cost_basis(self) -> float:
        """成本"""
        return self.quantity * self.avg_price


@dataclass
class BacktestResult:
    """回测结果"""
    
    # 基本信息
    symbol: str
    strategy: str
    start_date: datetime
    end_date: datetime
    initial_cash: float
    
    # 交易记录
    trades: List[TradeRecord]
    
    # 最终结果
    final_cash: float
    final_position_value: float
    total_return: float
    total_return_pct: float
    
    # 统计数据
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # 收益统计
    total_profit: float
    total_loss: float
    avg_profit_per_trade: float
    max_profit: float
    max_loss: float
    
    # 风险指标
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: Optional[float] = None
    
    # 持仓时间统计
    avg_holding_days: float = 0.0
    max_holding_days: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'basic_info': {
                'symbol': self.symbol,
                'strategy': self.strategy,
                'start_date': self.start_date.strftime('%Y-%m-%d'),
                'end_date': self.end_date.strftime('%Y-%m-%d'),
                'initial_cash': self.initial_cash,
                'backtest_days': (self.end_date - self.start_date).days
            },
            'final_result': {
                'final_cash': self.final_cash,
                'final_position_value': self.final_position_value,
                'total_value': self.final_cash + self.final_position_value,
                'total_return': self.total_return,
                'total_return_pct': f'{self.total_return_pct:.2f}%'
            },
            'trade_statistics': {
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades,
                'win_rate': f'{self.win_rate:.2f}%'
            },
            'profit_statistics': {
                'total_profit': self.total_profit,
                'total_loss': self.total_loss,
                'avg_profit_per_trade': self.avg_profit_per_trade,
                'max_profit': self.max_profit,
                'max_loss': self.max_loss
            },
            'risk_metrics': {
                'max_drawdown': self.max_drawdown,
                'max_drawdown_pct': f'{self.max_drawdown_pct:.2f}%',
                'sharpe_ratio': self.sharpe_ratio
            },
            'holding_statistics': {
                'avg_holding_days': f'{self.avg_holding_days:.1f}',
                'max_holding_days': f'{self.max_holding_days:.1f}'
            },
            'trades': [trade.to_dict() for trade in self.trades]
        }
    
    def print_summary(self):
        """打印回测结果摘要"""
        print("=" * 60)
        print(f"回测结果摘要 - {self.symbol} ({self.strategy})")
        print("=" * 60)
        
        print(f"\n【基本信息】")
        print(f"回测期间: {self.start_date.strftime('%Y-%m-%d')} ~ {self.end_date.strftime('%Y-%m-%d')}")
        print(f"回测天数: {(self.end_date - self.start_date).days} 天")
        print(f"初始资金: ¥{self.initial_cash:,.2f}")
        
        print(f"\n【最终结果】")
        total_value = self.final_cash + self.final_position_value
        print(f"最终资金: ¥{self.final_cash:,.2f}")
        print(f"持仓价值: ¥{self.final_position_value:,.2f}")
        print(f"总资产: ¥{total_value:,.2f}")
        print(f"总收益: ¥{self.total_return:,.2f} ({self.total_return_pct:+.2f}%)")
        
        print(f"\n【交易统计】")
        print(f"总交易次数: {self.total_trades}")
        print(f"盈利交易: {self.winning_trades} 次")
        print(f"亏损交易: {self.losing_trades} 次")
        print(f"胜率: {self.win_rate:.2f}%")
        
        print(f"\n【收益分析】")
        print(f"总盈利: ¥{self.total_profit:,.2f}")
        print(f"总亏损: ¥{self.total_loss:,.2f}")
        print(f"平均每笔收益: ¥{self.avg_profit_per_trade:,.2f}")
        print(f"最大单笔盈利: ¥{self.max_profit:,.2f}")
        print(f"最大单笔亏损: ¥{self.max_loss:,.2f}")
        
        print(f"\n【风险指标】")
        print(f"最大回撤: ¥{self.max_drawdown:,.2f} ({self.max_drawdown_pct:.2f}%)")
        if self.sharpe_ratio:
            print(f"夏普比率: {self.sharpe_ratio:.3f}")
        
        print(f"\n【持仓时间】")
        print(f"平均持仓天数: {self.avg_holding_days:.1f} 天")
        print(f"最长持仓天数: {self.max_holding_days:.1f} 天")
        
        print("=" * 60)