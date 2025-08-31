"""
iTick 数据接入模块

负责从 iTick API 获取实时行情和历史数据
"""

import os
import json
import time
import pandas as pd
import requests
import websocket
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
import queue
from collections import deque

# 导入数据结构
from .data_types import TickData, KlineData
# 导入模拟数据提供者
from .simulation_provider import SimulationProvider



class ItickDataProvider:
    """iTick 数据提供者"""
    
    def __init__(self, config_manager=None):
        """
        初始化 iTick 数据提供者
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # API 配置
        self.api_key = ""
        self.base_url = "https://api.itick.com"
        self.websocket_url = "wss://api.itick.com/ws"
        self.timeout = 30
        self.simulation_mode = False
        self.requests_per_minute = 5
        self.enable_rate_limiting = True
        
        # 加载配置
        if config_manager:
            itick_config = config_manager.get_itick_config()
            self.api_key = itick_config.api_key
            self.base_url = itick_config.base_url
            self.websocket_url = itick_config.websocket_url
            self.timeout = itick_config.timeout
            self.simulation_mode = itick_config.simulation_mode
            self.requests_per_minute = itick_config.requests_per_minute
            self.enable_rate_limiting = itick_config.enable_rate_limiting
        
        # API限流相关
        self.request_times = deque()  # 记录请求时间
        self.rate_limit_lock = threading.Lock()  # 限流锁
        
        # 模拟数据提供者
        self.simulation_provider = None
        if self.simulation_mode:
            self.simulation_provider = SimulationProvider(config_manager)
            self.logger.info("启用模拟数据模式")
        
        # WebSocket 连接
        self.ws = None
        self.is_connected = False
        self.subscriptions = set()
        
        # 数据回调
        self.tick_callbacks: List[Callable[[TickData], None]] = []
        self.kline_callbacks: List[Callable[[KlineData], None]] = []
        
        # 数据队列
        self.tick_queue = queue.Queue()
        self.kline_queue = queue.Queue()
        
        # 线程锁
        self.lock = threading.Lock()
    
    def _get_ktype_from_timeframe(self, timeframe: str) -> int:
        """
        将时间周期转换为iTick的kType格式
        
        Args:
            timeframe: 时间周期 (1m, 5m, 15m, 30m, 1h, 1d)
            
        Returns:
            int: kType值
        """
        timeframe_map = {
            '1m': 1,    # 1分钟
            '5m': 2,    # 5分钟  
            '15m': 3,   # 15分钟
            '30m': 4,   # 30分钟
            '1h': 5,    # 1小时
            '1d': 6     # 1日
        }
        return timeframe_map.get(timeframe, 2)  # 默认5分钟
    
    def set_api_key(self, api_key: str) -> None:
        """设置 API Key"""
        self.api_key = api_key
        self.logger.info("API Key 已更新")
    
    def _check_rate_limit(self) -> bool:
        """
        检查API限流
        
        Returns:
            bool: 是否可以发起请求
        """
        if not self.enable_rate_limiting:
            return True
        
        with self.rate_limit_lock:
            now = time.time()
            
            # 清理超过一分钟的记录
            while self.request_times and now - self.request_times[0] > 60:
                self.request_times.popleft()
            
            # 检查是否超过限制
            if len(self.request_times) >= self.requests_per_minute:
                wait_time = 60 - (now - self.request_times[0])
                self.logger.warning(f"API请求超过限制，需要等待 {wait_time:.1f} 秒")
                return False
            
            # 记录请求时间
            self.request_times.append(now)
            return True
    
    def _wait_for_rate_limit(self) -> None:
        """等待直到可以发起请求"""
        if not self.enable_rate_limiting:
            return
        
        while not self._check_rate_limit():
            time.sleep(1)  # 等待1秒再检查
    
    def get_historical_klines(self, symbol: str, timeframe: str = "1d", 
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None,
                            limit: int = 1000) -> List[KlineData]:
        """
        获取历史K线数据
        
        Args:
            symbol: 股票代码
            timeframe: 时间周期 (1m, 5m, 15m, 30m, 1h, 1d)
            start_date: 开始日期
            end_date: 结束日期
            limit: 数据条数限制
            
        Returns:
            List[KlineData]: K线数据列表
        """
        if self.simulation_mode:
            return self.simulation_provider.get_historical_klines(
                symbol, timeframe, start_date, end_date, limit
            )
            
        if not self.api_key:
            self.logger.error("API Key 未设置")
            return []
        
        # 构建请求参数 - 使用官方API格式
        params = {
            'region': 'US',  # 美股，港股用HK
            'code': symbol,
            'kType': self._get_ktype_from_timeframe(timeframe),
            'limit': limit
        }
        
        headers = {
            'accept': 'application/json',
            'token': self.api_key
        }
        
        try:
            # 使用官方K线 API
            url = f"{self.base_url}/stock/kline"
            response = requests.get(url, params=params, headers=headers, timeout=self.timeout, verify=False)
            response.raise_for_status()
            
            data = response.json()
            
            # 解析数据
            klines = []
            if data.get('code') == 0 and 'data' in data:
                for item in data['data']:
                    # 根据实际返回格式解析（可能需要调整）
                    kline = KlineData(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(item.get('t', 0) / 1000),  # 时间戳
                        open=float(item.get('o', 0)),   # 开盘价
                        high=float(item.get('h', 0)),   # 最高价
                        low=float(item.get('l', 0)),    # 最低价
                        close=float(item.get('c', 0)),  # 收盘价
                        volume=int(item.get('v', 0)),   # 成交量
                        timeframe=timeframe
                    )
                    klines.append(kline)
            
            self.logger.info(f"获取历史K线数据成功: {symbol}, {len(klines)} 条记录")
            return klines
        
        except Exception as e:
            self.logger.error(f"获取历史K线数据失败: {e}")
            return []
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        获取最新价格
        
        Args:
            symbol: 股票代码
            
        Returns:
            Optional[float]: 最新价格
        """
        if self.simulation_mode:
            return self.simulation_provider.get_latest_price(symbol)
        
        if not self.api_key:
            self.logger.error("API Key 未设置")
            return None
        
        # 检查API限流
        if not self._check_rate_limit():
            self.logger.warning(f"获取 {symbol} 价格被API限流阻止")
            return None
        
        headers = {
            'token': self.api_key,  # 修正：根据官方示例使用token而不是Authorization Bearer
            'Content-Type': 'application/json'
        }
        
        try:
            # 使用K线接口获取最新价格（获取最近1条K线数据）
            url = f"{self.base_url}/stock/kline"
            params = {
                'region': 'US',  # 美股，港股用HK
                'code': symbol,
                'kType': 1,  # 1分钟K线获取最新数据
                'limit': 1   # 只获取最新1条
            }
            
            # 优化SSL配置
            session = requests.Session()
            session.verify = False  # 忽略SSL证书验证（仅测试用）
            
            response = session.get(url, headers=headers, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            # 从最新K线数据中获取收盘价作为最新价格
            if data.get('code') == 0 and data.get('data') and len(data['data']) > 0:
                latest_kline = data['data'][0]
                price = float(latest_kline.get('c', 0))  # c为收盘价
            else:
                price = 0
            
            self.logger.debug(f"获取最新价格: {symbol} = {price}")
            return price if price > 0 else None
        
        except Exception as e:
            self.logger.error(f"获取最新价格失败: {e}")
            return None
    
    def get_market_status(self) -> Dict[str, Any]:
        """
        获取市场状态
        
        Returns:
            Dict[str, Any]: 市场状态信息
        """
        if not self.api_key:
            self.logger.error("API Key 未设置")
            return {}
        
        headers = {
            'token': self.api_key,  # 修正：根据官方示例使用token
            'Content-Type': 'application/json'
        }
        
        try:
            url = f"{self.base_url}/v1/market/status"
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            self.logger.debug("获取市场状态成功")
            return data
        
        except Exception as e:
            self.logger.error(f"获取市场状态失败: {e}")
            return {}
    
    def connect_websocket(self) -> bool:
        """
        连接 WebSocket
        
        Returns:
            bool: 是否连接成功
        """
        if self.simulation_mode:
            # 使用模拟数据提供者
            return self.simulation_provider.connect_websocket()
        
        if self.is_connected:
            self.logger.warning("WebSocket 已连接")
            return True
        
        try:
            self.ws = websocket.WebSocketApp(
                self.websocket_url,
                header=[f"token: {self.api_key}"],  # 修正：根据官方示例使用token而不是Authorization
                on_open=self._on_websocket_open,
                on_message=self._on_websocket_message,
                on_error=self._on_websocket_error,
                on_close=self._on_websocket_close
            )
            
            # 在新线程中运行 WebSocket
            ws_thread = threading.Thread(target=self.ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            # 等待连接建立
            for _ in range(10):  # 最多等待10秒
                if self.is_connected:
                    return True
                time.sleep(1)
            
            self.logger.error("WebSocket 连接超时")
            return False
        
        except Exception as e:
            self.logger.error(f"WebSocket 连接失败: {e}")
            return False
    
    def disconnect_websocket(self) -> None:
        """断开 WebSocket 连接"""
        if self.simulation_mode:
            self.simulation_provider.disconnect_websocket()
            return
            
        if self.ws:
            self.ws.close()
        self.is_connected = False
        self.subscriptions.clear()
        self.logger.info("WebSocket 已断开")
    
    def subscribe_tick(self, symbol: str) -> bool:
        """
        订阅实时tick数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            bool: 是否订阅成功
        """
        if self.simulation_mode:
            return self.simulation_provider.subscribe_tick(symbol)
            
        if not self.is_connected:
            self.logger.error("WebSocket 未连接")
            return False
        
        subscribe_msg = {
            'action': 'subscribe',
            'type': 'tick',
            'symbol': symbol
        }
        
        try:
            self.ws.send(json.dumps(subscribe_msg))
            self.subscriptions.add(f"tick_{symbol}")
            self.logger.info(f"订阅实时tick数据: {symbol}")
            return True
        
        except Exception as e:
            self.logger.error(f"订阅实时tick数据失败: {e}")
            return False
    
    def subscribe_kline(self, symbol: str, timeframe: str = "1m") -> bool:
        """
        订阅实时K线数据
        
        Args:
            symbol: 股票代码
            timeframe: 时间周期
            
        Returns:
            bool: 是否订阅成功
        """
        if self.simulation_mode:
            return self.simulation_provider.subscribe_kline(symbol, timeframe)
            
        if not self.is_connected:
            self.logger.error("WebSocket 未连接")
            return False
        
        subscribe_msg = {
            'action': 'subscribe',
            'type': 'kline',
            'symbol': symbol,
            'interval': timeframe
        }
        
        try:
            self.ws.send(json.dumps(subscribe_msg))
            self.subscriptions.add(f"kline_{symbol}_{timeframe}")
            self.logger.info(f"订阅实时K线数据: {symbol} ({timeframe})")
            return True
        
        except Exception as e:
            self.logger.error(f"订阅实时K线数据失败: {e}")
            return False
    
    def unsubscribe(self, symbol: str, data_type: str = "all") -> bool:
        """
        取消订阅
        
        Args:
            symbol: 股票代码
            data_type: 数据类型 (tick, kline, all)
            
        Returns:
            bool: 是否取消成功
        """
        if not self.is_connected:
            return True
        
        if data_type == "all":
            # 取消所有订阅
            subscriptions_to_remove = [s for s in self.subscriptions if symbol in s]
        else:
            subscriptions_to_remove = [s for s in self.subscriptions if f"{data_type}_{symbol}" in s]
        
        for subscription in subscriptions_to_remove:
            parts = subscription.split("_")
            msg_type = parts[0]
            msg_symbol = parts[1]
            
            unsubscribe_msg = {
                'action': 'unsubscribe',
                'type': msg_type,
                'symbol': msg_symbol
            }
            
            if len(parts) > 2:  # K线包含时间周期
                unsubscribe_msg['interval'] = parts[2]
            
            try:
                self.ws.send(json.dumps(unsubscribe_msg))
                self.subscriptions.remove(subscription)
                self.logger.info(f"取消订阅: {subscription}")
            
            except Exception as e:
                self.logger.error(f"取消订阅失败: {e}")
                return False
        
        return True
    
    def add_tick_callback(self, callback: Callable[[TickData], None]) -> None:
        """添加tick数据回调函数"""
        self.tick_callbacks.append(callback)
        if self.simulation_mode:
            self.simulation_provider.add_tick_callback(callback)
    
    def add_kline_callback(self, callback: Callable[[KlineData], None]) -> None:
        """添加K线数据回调函数"""
        self.kline_callbacks.append(callback)
        if self.simulation_mode:
            self.simulation_provider.add_kline_callback(callback)
    
    def get_tick_data(self, timeout: float = 1.0) -> Optional[TickData]:
        """
        从队列获取tick数据
        
        Args:
            timeout: 超时时间
            
        Returns:
            Optional[TickData]: tick数据
        """
        try:
            return self.tick_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_kline_data(self, timeout: float = 1.0) -> Optional[KlineData]:
        """
        从队列获取K线数据
        
        Args:
            timeout: 超时时间
            
        Returns:
            Optional[KlineData]: K线数据
        """
        try:
            return self.kline_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def _on_websocket_open(self, ws) -> None:
        """WebSocket 连接打开回调"""
        self.is_connected = True
        self.logger.info("WebSocket 连接已建立")
    
    def _on_websocket_message(self, ws, message: str) -> None:
        """WebSocket 消息回调"""
        try:
            data = json.loads(message)
            
            if data.get('type') == 'tick':
                tick_data = TickData(
                    symbol=data['symbol'],
                    timestamp=datetime.fromtimestamp(data['timestamp'] / 1000),
                    price=float(data['price']),
                    volume=int(data.get('volume', 0)),
                    bid=float(data['bid']) if data.get('bid') else None,
                    ask=float(data['ask']) if data.get('ask') else None,
                    bid_size=int(data['bid_size']) if data.get('bid_size') else None,
                    ask_size=int(data['ask_size']) if data.get('ask_size') else None
                )
                
                # 添加到队列
                self.tick_queue.put(tick_data)
                
                # 调用回调函数
                for callback in self.tick_callbacks:
                    try:
                        callback(tick_data)
                    except Exception as e:
                        self.logger.error(f"Tick回调函数执行失败: {e}")
            
            elif data.get('type') == 'kline':
                kline_data = KlineData(
                    symbol=data['symbol'],
                    timestamp=datetime.fromtimestamp(data['timestamp'] / 1000),
                    open=float(data['open']),
                    high=float(data['high']),
                    low=float(data['low']),
                    close=float(data['close']),
                    volume=int(data['volume']),
                    timeframe=data.get('interval', '1m')
                )
                
                # 添加到队列
                self.kline_queue.put(kline_data)
                
                # 调用回调函数
                for callback in self.kline_callbacks:
                    try:
                        callback(kline_data)
                    except Exception as e:
                        self.logger.error(f"K线回调函数执行失败: {e}")
        
        except Exception as e:
            self.logger.error(f"处理WebSocket消息失败: {e}")
    
    def _on_websocket_error(self, ws, error) -> None:
        """WebSocket 错误回调"""
        self.logger.error(f"WebSocket 错误: {error}")
    
    def _on_websocket_close(self, ws, close_status_code, close_msg) -> None:
        """WebSocket 关闭回调"""
        self.is_connected = False
        self.subscriptions.clear()
        self.logger.info("WebSocket 连接已关闭")


class DataStorage:
    """数据存储管理器"""
    
    def __init__(self, config_manager=None):
        """
        初始化数据存储管理器
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # 默认配置
        self.storage_dir = "data/historical"
        self.storage_format = "csv"
        
        # 从配置加载
        if config_manager:
            data_config = config_manager.get_data_config()
            self.storage_dir = data_config.historical_dir
            self.storage_format = data_config.format
        
        # 确保存储目录存在
        os.makedirs(self.storage_dir, exist_ok=True)
    
    def save_klines(self, klines: List[KlineData], symbol: str = None) -> bool:
        """
        保存K线数据
        
        Args:
            klines: K线数据列表
            symbol: 股票代码（如果为None，从数据中获取）
            
        Returns:
            bool: 是否保存成功
        """
        if not klines:
            return True
        
        try:
            # 按股票和时间周期分组
            grouped_data = {}
            for kline in klines:
                key = f"{kline.symbol}_{kline.timeframe}"
                if key not in grouped_data:
                    grouped_data[key] = []
                grouped_data[key].append(kline)
            
            # 保存每个分组
            for key, data in grouped_data.items():
                symbol_name, timeframe = key.split('_')
                self._save_klines_group(data, symbol_name, timeframe)
            
            self.logger.info(f"保存K线数据成功，共 {len(klines)} 条记录")
            return True
        
        except Exception as e:
            self.logger.error(f"保存K线数据失败: {e}")
            return False
    
    def _save_klines_group(self, klines: List[KlineData], symbol: str, timeframe: str) -> None:
        """保存单个分组的K线数据"""
        if self.storage_format == "csv":
            self._save_klines_csv(klines, symbol, timeframe)
        elif self.storage_format == "parquet":
            self._save_klines_parquet(klines, symbol, timeframe)
        else:
            raise ValueError(f"不支持的存储格式: {self.storage_format}")
    
    def _save_klines_csv(self, klines: List[KlineData], symbol: str, timeframe: str) -> None:
        """保存K线数据为CSV格式"""
        filename = f"{symbol}_{timeframe}.csv"
        filepath = os.path.join(self.storage_dir, filename)
        
        # 转换为DataFrame
        data = []
        for kline in klines:
            data.append({
                'timestamp': kline.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'open': kline.open,
                'high': kline.high,
                'low': kline.low,
                'close': kline.close,
                'volume': kline.volume
            })
        
        df = pd.DataFrame(data)
        
        # 如果文件存在，追加数据
        if os.path.exists(filepath):
            existing_df = pd.read_csv(filepath)
            df = pd.concat([existing_df, df], ignore_index=True)
            # 去重并排序
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
            df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        df.to_csv(filepath, index=False)
    
    def _save_klines_parquet(self, klines: List[KlineData], symbol: str, timeframe: str) -> None:
        """保存K线数据为Parquet格式"""
        filename = f"{symbol}_{timeframe}.parquet"
        filepath = os.path.join(self.storage_dir, filename)
        
        # 转换为DataFrame
        data = []
        for kline in klines:
            data.append({
                'timestamp': kline.timestamp,
                'open': kline.open,
                'high': kline.high,
                'low': kline.low,
                'close': kline.close,
                'volume': kline.volume
            })
        
        df = pd.DataFrame(data)
        
        # 如果文件存在，追加数据
        if os.path.exists(filepath):
            existing_df = pd.read_parquet(filepath)
            df = pd.concat([existing_df, df], ignore_index=True)
            # 去重并排序
            df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
        
        df.to_parquet(filepath, index=False)
    
    def load_klines(self, symbol: str, timeframe: str = "1d",
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> List[KlineData]:
        """
        加载K线数据
        
        Args:
            symbol: 股票代码
            timeframe: 时间周期
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            List[KlineData]: K线数据列表
        """
        filename = f"{symbol}_{timeframe}.{self.storage_format}"
        filepath = os.path.join(self.storage_dir, filename)
        
        if not os.path.exists(filepath):
            self.logger.warning(f"数据文件不存在: {filepath}")
            return []
        
        try:
            if self.storage_format == "csv":
                df = pd.read_csv(filepath)
            elif self.storage_format == "parquet":
                df = pd.read_parquet(filepath)
            else:
                raise ValueError(f"不支持的存储格式: {self.storage_format}")
            
            # 转换时间戳
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 过滤日期范围
            if start_date:
                df = df[df['timestamp'] >= start_date]
            if end_date:
                df = df[df['timestamp'] <= end_date]
            
            # 转换为KlineData对象
            klines = []
            for _, row in df.iterrows():
                kline = KlineData(
                    symbol=symbol,
                    timestamp=row['timestamp'].to_pydatetime(),
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=int(row['volume']),
                    timeframe=timeframe
                )
                klines.append(kline)
            
            self.logger.info(f"加载K线数据成功: {symbol}_{timeframe}, {len(klines)} 条记录")
            return klines
        
        except Exception as e:
            self.logger.error(f"加载K线数据失败: {e}")
            return []