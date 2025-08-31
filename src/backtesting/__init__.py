"""
回测模块

提供策略回测功能
"""

from .backtest_engine import BacktestEngine
from .backtest_result import BacktestResult, TradeRecord

__all__ = ['BacktestEngine', 'BacktestResult', 'TradeRecord']