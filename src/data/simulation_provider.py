"""
模拟数据提供者

用于测试系统功能，生成模拟的股价数据和交易信号
"""

import time
import random
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import logging

from .data_types import TickData, KlineData


class SimulationProvider:
    """模拟数据提供者"""
    
    def __init__(self, config_manager=None):
        """
        初始化模拟数据提供者
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # 模拟数据状态
        self.is_running = False
        self.subscribed_symbols = set()
        
        # 股票初始价格
        self.base_prices = {
            'AAPL': 175.0,
            'MSFT': 330.0,
            'GOOGL': 140.0,
            'TSLA': 250.0,
            'AMZN': 145.0,
            'META': 320.0,
            'NVDA': 450.0
        }
        
        # 当前价格
        self.current_prices = self.base_prices.copy()
        
        # 数据回调
        self.tick_callbacks: List[Callable[[TickData], None]] = []
        self.kline_callbacks: List[Callable[[KlineData], None]] = []
        
        # 模拟线程
        self.simulation_thread = None
        
        self.logger.info("模拟数据提供者初始化完成")
    
    def connect_websocket(self) -> bool:
        """
        模拟 WebSocket 连接
        
        Returns:
            bool: 总是返回 True（模拟连接成功）
        """
        self.is_running = True
        self.logger.info("模拟 WebSocket 连接已建立")
        
        # 启动模拟数据生成线程
        self.simulation_thread = threading.Thread(target=self._generate_simulation_data)
        self.simulation_thread.daemon = True
        self.simulation_thread.start()
        
        return True
    
    def disconnect_websocket(self) -> None:
        """断开模拟 WebSocket 连接"""
        self.is_running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=2)
        self.subscribed_symbols.clear()
        self.logger.info("模拟 WebSocket 连接已断开")
    
    def subscribe_tick(self, symbol: str) -> bool:
        """
        订阅实时tick数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            bool: 是否订阅成功
        """
        if symbol not in self.base_prices:
            # 为新股票生成随机基础价格
            self.base_prices[symbol] = random.uniform(50, 500)
            self.current_prices[symbol] = self.base_prices[symbol]
        
        self.subscribed_symbols.add(symbol)
        self.logger.info(f"订阅模拟tick数据: {symbol}")
        return True
    
    def subscribe_kline(self, symbol: str, timeframe: str = "1m") -> bool:
        """
        订阅实时K线数据
        
        Args:
            symbol: 股票代码
            timeframe: 时间周期
            
        Returns:
            bool: 是否订阅成功
        """
        return self.subscribe_tick(symbol)  # 复用tick订阅
    
    def subscribe_kline(self, symbol: str, timeframe: str = "1m") -> bool:
        """
        订阅实时K线数据
        
        Args:
            symbol: 股票代码
            timeframe: 时间周期
            
        Returns:
            bool: 是否订阅成功
        """
        return self.subscribe_tick(symbol)  # 复用tick订阅
    
    def unsubscribe(self, symbol: str, data_type: str = "all") -> bool:
        """
        取消订阅
        
        Args:
            symbol: 股票代码
            data_type: 数据类型
            
        Returns:
            bool: 是否取消成功
        """
        if symbol in self.subscribed_symbols:
            self.subscribed_symbols.remove(symbol)
            self.logger.info(f"取消订阅模拟数据: {symbol}")
        return True
    
    def add_tick_callback(self, callback: Callable[[TickData], None]) -> None:
        """添加tick数据回调函数"""
        self.tick_callbacks.append(callback)
        self.logger.debug("添加tick数据回调函数")
    
    def add_kline_callback(self, callback: Callable[[KlineData], None]) -> None:
        """添加K线数据回调函数"""
        self.kline_callbacks.append(callback)
        self.logger.debug("添加K线数据回调函数")
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        获取最新价格
        
        Args:
            symbol: 股票代码
            
        Returns:
            Optional[float]: 最新价格
        """
        return self.current_prices.get(symbol)
    
    def get_historical_klines(self, symbol: str, timeframe: str = "1d",
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None,
                            limit: int = 1000) -> List[KlineData]:
        """
        生成模拟历史K线数据
        
        Args:
            symbol: 股票代码
            timeframe: 时间周期
            start_date: 开始日期
            end_date: 结束日期
            limit: 数据条数限制
            
        Returns:
            List[KlineData]: 模拟K线数据列表
        """
        if symbol not in self.base_prices:
            self.base_prices[symbol] = random.uniform(50, 500)
        
        # 确定时间范围
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            if timeframe == "1m":
                start_date = end_date - timedelta(hours=limit)
            elif timeframe == "5m":
                start_date = end_date - timedelta(hours=limit * 5)
            elif timeframe == "1h":
                start_date = end_date - timedelta(days=limit)
            else:  # 1d
                start_date = end_date - timedelta(days=limit)
        
        # 生成模拟数据
        klines = []
        current_time = start_date
        current_price = self.base_prices[symbol]
        
        time_delta = self._get_time_delta(timeframe)
        
        while current_time <= end_date and len(klines) < limit:
            # 生成随机价格变动
            price_change = random.uniform(-0.05, 0.05)  # ±5%变动
            new_price = current_price * (1 + price_change)
            
            # 生成OHLC数据
            open_price = current_price
            close_price = new_price
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.02))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.02))
            volume = random.randint(10000, 1000000)
            
            kline = KlineData(
                symbol=symbol,
                timestamp=current_time,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
                timeframe=timeframe
            )
            klines.append(kline)
            
            current_price = new_price
            current_time += time_delta
        
        self.logger.info(f"生成模拟历史K线数据: {symbol}, {len(klines)} 条记录")
        return klines
    
    def _generate_simulation_data(self) -> None:
        """生成模拟实时数据的后台线程"""
        self.logger.info("开始生成模拟实时数据")
        
        while self.is_running:
            try:
                for symbol in self.subscribed_symbols:
                    # 生成模拟tick数据
                    self._generate_tick_data(symbol)
                    
                    # 每分钟生成一次K线数据
                    if datetime.now().second == 0:
                        self._generate_kline_data(symbol)
                
                time.sleep(1)  # 每秒更新一次
                
            except Exception as e:
                self.logger.error(f"生成模拟数据失败: {e}")
    
    def _generate_tick_data(self, symbol: str) -> None:
        """生成模拟tick数据"""
        if symbol not in self.current_prices:
            return
        
        # 生成随机价格变动
        price_change = random.uniform(-0.001, 0.001)  # ±0.1%变动
        new_price = self.current_prices[symbol] * (1 + price_change)
        self.current_prices[symbol] = new_price
        
        # 生成买卖价差
        spread = new_price * 0.001  # 0.1%价差
        bid = new_price - spread / 2
        ask = new_price + spread / 2
        
        tick_data = TickData(
            symbol=symbol,
            timestamp=datetime.now(),
            price=new_price,
            volume=random.randint(100, 10000),
            bid=bid,
            ask=ask,
            bid_size=random.randint(100, 5000),
            ask_size=random.randint(100, 5000)
        )
        
        # 调用回调函数
        for callback in self.tick_callbacks:
            try:
                callback(tick_data)
            except Exception as e:
                self.logger.error(f"Tick回调函数执行失败: {e}")
    
    def _generate_kline_data(self, symbol: str) -> None:
        """生成模拟K线数据"""
        if symbol not in self.current_prices:
            return
        
        current_time = datetime.now().replace(second=0, microsecond=0)
        
        # 生成1分钟K线数据
        base_price = self.current_prices[symbol]
        price_change = random.uniform(-0.02, 0.02)  # ±2%变动
        
        open_price = base_price
        close_price = base_price * (1 + price_change)
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.01))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.01))
        volume = random.randint(10000, 100000)
        
        kline_data = KlineData(
            symbol=symbol,
            timestamp=current_time,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            timeframe="1m"
        )
        
        # 更新当前价格
        self.current_prices[symbol] = close_price
        
        # 调用回调函数
        for callback in self.kline_callbacks:
            try:
                callback(kline_data)
            except Exception as e:
                self.logger.error(f"K线回调函数执行失败: {e}")
    
    def _get_time_delta(self, timeframe: str) -> timedelta:
        """获取时间间隔"""
        if timeframe == "1m":
            return timedelta(minutes=1)
        elif timeframe == "5m":
            return timedelta(minutes=5)
        elif timeframe == "15m":
            return timedelta(minutes=15)
        elif timeframe == "30m":
            return timedelta(minutes=30)
        elif timeframe == "1h":
            return timedelta(hours=1)
        elif timeframe == "1d":
            return timedelta(days=1)
        else:
            return timedelta(minutes=1)
    
    def get_market_status(self) -> Dict[str, any]:
        """获取模拟市场状态"""
        return {
            "market": "US",
            "status": "open",
            "timezone": "US/Eastern",
            "simulation": True
        }