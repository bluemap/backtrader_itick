"""
回测引擎

提供完整的策略回测功能
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from .backtest_result import BacktestResult, TradeRecord, PositionRecord, OrderType, OrderStatus
from ..data.data_types import KlineData
from ..strategies.base_strategy import TradeSignal
from ..strategies.strategy_factory import StrategyFactory


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, config_manager=None):
        """
        初始化回测引擎
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # 回测参数
        self.initial_cash = 100000  # 初始资金
        self.commission = 0.001    # 手续费率
        self.min_commission = 5    # 最小手续费
        self.slippage = 0.001      # 滑点
        
        # 仓位管理
        self.position_size_pct = 0.1  # 单次买入占总资金的比例
        
        if config_manager:
            # 从配置加载回测参数
            pass
    
    def run_backtest(self, 
                    symbol: str,
                    strategy_name: str,
                    start_date: datetime,
                    end_date: datetime,
                    kline_data: List[KlineData],
                    initial_cash: Optional[float] = None,
                    **strategy_params) -> BacktestResult:
        """
        运行回测
        
        Args:
            symbol: 股票代码
            strategy_name: 策略名称
            start_date: 开始日期
            end_date: 结束日期
            kline_data: K线数据
            initial_cash: 初始资金
            **strategy_params: 策略参数
            
        Returns:
            BacktestResult: 回测结果
        """
        self.logger.info(f"开始回测 {symbol} - {strategy_name}")
        
        if initial_cash:
            self.initial_cash = initial_cash
        
        # 创建策略实例
        strategy = self._create_strategy(strategy_name, **strategy_params)
        if not strategy:
            raise ValueError(f"无法创建策略: {strategy_name}")
        
        # 准备数据
        df = self._prepare_data(kline_data)
        if df.empty:
            raise ValueError("没有有效的K线数据")
        
        # 初始化回测状态
        cash = self.initial_cash
        position = 0  # 持仓数量
        position_cost = 0.0  # 持仓成本
        
        trades = []
        equity_curve = []
        max_equity = self.initial_cash
        max_drawdown = 0.0
        
        # 持仓追踪
        position_entry_time = None
        holding_periods = []
        
        self.logger.info(f"数据准备完成，共 {len(df)} 条K线数据")
        
        # 逐日回测
        for i, (timestamp, row) in enumerate(df.iterrows()):
            current_price = row['close']
            
            # 计算当前资产价值
            position_value = position * current_price
            total_equity = cash + position_value
            equity_curve.append(total_equity)
            
            # 更新最大回撤
            if total_equity > max_equity:
                max_equity = total_equity
            drawdown = max_equity - total_equity
            if drawdown > max_drawdown:
                max_drawdown = drawdown
            
            # 获取足够的历史数据用于策略计算
            if i < 50:  # 需要至少50个数据点来计算技术指标
                continue
            
            # 准备策略所需的历史数据
            hist_data = df.iloc[:i+1].copy()
            
            try:
                # 获取策略信号
                signals = strategy.generate_signals(hist_data)
                
                if not signals:
                    continue
                
                # 处理最新信号
                latest_signal = signals[-1]
                
                # 执行交易
                if latest_signal.action == 'BUY' and position == 0:
                    # 买入信号且当前空仓
                    trade_cash = cash * self.position_size_pct
                    trade_price = current_price * (1 + self.slippage)  # 考虑滑点
                    commission = max(trade_cash * self.commission, self.min_commission)
                    
                    if trade_cash > commission:
                        quantity = int((trade_cash - commission) / trade_price)
                        if quantity > 0:
                            total_cost = quantity * trade_price + commission
                            
                            cash -= total_cost
                            position = quantity
                            position_cost = trade_price
                            position_entry_time = timestamp
                            
                            # 记录交易
                            trade = TradeRecord(
                                timestamp=timestamp,
                                symbol=symbol,
                                order_type=OrderType.BUY,
                                price=trade_price,
                                quantity=quantity,
                                amount=total_cost,
                                strategy=strategy_name,
                                reason=latest_signal.reason
                            )
                            trades.append(trade)
                            
                            self.logger.debug(f"买入: {quantity} 股 @ ¥{trade_price:.2f}")
                
                elif latest_signal.action == 'SELL' and position > 0:
                    # 卖出信号且当前持仓
                    trade_price = current_price * (1 - self.slippage)  # 考虑滑点
                    trade_amount = position * trade_price
                    commission = max(trade_amount * self.commission, self.min_commission)
                    
                    cash += trade_amount - commission
                    
                    # 记录持仓期间
                    if position_entry_time:
                        holding_days = (timestamp - position_entry_time).days
                        holding_periods.append(holding_days)
                    
                    # 记录交易
                    trade = TradeRecord(
                        timestamp=timestamp,
                        symbol=symbol,
                        order_type=OrderType.SELL,
                        price=trade_price,
                        quantity=position,
                        amount=trade_amount - commission,
                        strategy=strategy_name,
                        reason=latest_signal.reason
                    )
                    trades.append(trade)
                    
                    self.logger.debug(f"卖出: {position} 股 @ ¥{trade_price:.2f}")
                    
                    position = 0
                    position_cost = 0.0
                    position_entry_time = None
            
            except Exception as e:
                self.logger.warning(f"处理信号时出错: {e}")
                continue
        
        # 计算最终结果
        final_price = df.iloc[-1]['close']
        final_position_value = position * final_price
        total_return = (cash + final_position_value) - self.initial_cash
        total_return_pct = (total_return / self.initial_cash) * 100
        
        # 分析交易统计
        trade_stats = self._analyze_trades(trades)
        
        # 计算持仓时间统计
        avg_holding_days = np.mean(holding_periods) if holding_periods else 0
        max_holding_days = max(holding_periods) if holding_periods else 0
        
        # 创建回测结果
        result = BacktestResult(
            symbol=symbol,
            strategy=strategy_name,
            start_date=start_date,
            end_date=end_date,
            initial_cash=self.initial_cash,
            trades=trades,
            final_cash=cash,
            final_position_value=final_position_value,
            total_return=total_return,
            total_return_pct=total_return_pct,
            total_trades=trade_stats['total_trades'],
            winning_trades=trade_stats['winning_trades'],
            losing_trades=trade_stats['losing_trades'],
            win_rate=trade_stats['win_rate'],
            total_profit=trade_stats['total_profit'],
            total_loss=trade_stats['total_loss'],
            avg_profit_per_trade=trade_stats['avg_profit_per_trade'],
            max_profit=trade_stats['max_profit'],
            max_loss=trade_stats['max_loss'],
            max_drawdown=max_drawdown,
            max_drawdown_pct=(max_drawdown / max_equity * 100) if max_equity > 0 else 0,
            avg_holding_days=avg_holding_days,
            max_holding_days=max_holding_days,
            sharpe_ratio=self._calculate_sharpe_ratio(equity_curve)
        )
        
        self.logger.info(f"回测完成，总收益: {total_return_pct:.2f}%")
        return result
    
    def _create_strategy(self, strategy_name: str, **params):
        """创建策略实例"""
        try:
            from ..strategies.simple_signal_generator import SimpleSignalGenerator
            return SimpleSignalGenerator(strategy_name, **params)
        except Exception as e:
            self.logger.error(f"创建策略失败: {e}")
            return None
    
    def _prepare_data(self, kline_data: List[KlineData]) -> pd.DataFrame:
        """准备回测数据"""
        if not kline_data:
            return pd.DataFrame()
        
        # 转换为DataFrame
        data = []
        for kline in kline_data:
            data.append({
                'timestamp': kline.timestamp,
                'open': kline.open,
                'high': kline.high,
                'low': kline.low,
                'close': kline.close,
                'volume': kline.volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        
        return df
    
    def _analyze_trades(self, trades: List[TradeRecord]) -> Dict[str, Any]:
        """分析交易统计"""
        if not trades:
            return {
                'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0,
                'win_rate': 0, 'total_profit': 0, 'total_loss': 0,
                'avg_profit_per_trade': 0, 'max_profit': 0, 'max_loss': 0
            }
        
        # 配对买卖交易
        buy_trades = [t for t in trades if t.order_type == OrderType.BUY]
        sell_trades = [t for t in trades if t.order_type == OrderType.SELL]
        
        profits = []
        for i in range(min(len(buy_trades), len(sell_trades))):
            buy_trade = buy_trades[i]
            sell_trade = sell_trades[i]
            
            # 计算盈亏（卖出金额 - 买入金额）
            profit = sell_trade.amount - buy_trade.amount
            profits.append(profit)
        
        if not profits:
            return {
                'total_trades': len(trades), 'winning_trades': 0, 'losing_trades': 0,
                'win_rate': 0, 'total_profit': 0, 'total_loss': 0,
                'avg_profit_per_trade': 0, 'max_profit': 0, 'max_loss': 0
            }
        
        winning_trades = sum(1 for p in profits if p > 0)
        losing_trades = sum(1 for p in profits if p < 0)
        win_rate = (winning_trades / len(profits) * 100) if profits else 0
        
        total_profit = sum(p for p in profits if p > 0)
        total_loss = sum(p for p in profits if p < 0)
        avg_profit_per_trade = sum(profits) / len(profits)
        max_profit = max(profits) if profits else 0
        max_loss = min(profits) if profits else 0
        
        return {
            'total_trades': len(profits) * 2,  # 每笔完整交易包含买入和卖出
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'total_loss': abs(total_loss),
            'avg_profit_per_trade': avg_profit_per_trade,
            'max_profit': max_profit,
            'max_loss': max_loss
        }
    
    def _calculate_sharpe_ratio(self, equity_curve: List[float]) -> Optional[float]:
        """计算夏普比率"""
        if len(equity_curve) < 2:
            return None
        
        try:
            returns = np.diff(equity_curve) / equity_curve[:-1]
            if len(returns) == 0 or np.std(returns) == 0:
                return None
            
            # 假设无风险利率为3%年化
            risk_free_rate = 0.03 / 252  # 日无风险利率
            excess_returns = returns - risk_free_rate
            
            sharpe = np.mean(excess_returns) / np.std(returns) * np.sqrt(252)
            return sharpe
        except:
            return None