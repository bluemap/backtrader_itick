"""
数据结构定义

定义系统中使用的各种数据结构
"""

from datetime import datetime
from dataclasses import dataclass
from typing import Optional


@dataclass
class TickData:
    """Tick 数据结构"""
    symbol: str
    timestamp: datetime
    price: float
    volume: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None


@dataclass
class KlineData:
    """K线数据结构"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    timeframe: str  # 1m, 5m, 15m, 30m, 1h, 1d