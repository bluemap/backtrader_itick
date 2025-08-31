"""
限流数据提供者

专门为免费iTick账户设计的数据获取策略
"""

import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

from .itick_provider import ItickDataProvider
from .data_types import KlineData


class RateLimitedProvider:
    """限流数据提供者 - 专为免费账户优化"""
    
    def __init__(self, config_manager=None):
        """
        初始化限流数据提供者
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.itick_provider = ItickDataProvider(config_manager)
        
        # 轮询配置
        self.polling_interval = 300  # 5分钟轮询一次
        self.active_symbols = []
        self.is_running = False
        
        # 数据缓存
        self.latest_prices = {}
        self.last_update_times = defaultdict(lambda: datetime.min)
        
        # 回调函数
        self.price_callbacks = []
        
        # 轮询线程
        self.polling_thread = None
        
        self.logger.info("限流数据提供者初始化完成")
    
    def start_polling(self, symbols: List[str]) -> bool:
        """
        启动轮询获取数据
        
        Args:
            symbols: 股票代码列表
            
        Returns:
            bool: 是否启动成功
        """
        try:
            self.active_symbols = symbols[:3]  # 限制最多3只股票，避免API限制
            self.is_running = True
            
            # 启动轮询线程
            self.polling_thread = threading.Thread(target=self._polling_worker)
            self.polling_thread.daemon = True
            self.polling_thread.start()
            
            self.logger.info(f"开始轮询 {len(self.active_symbols)} 只股票价格")
            return True
            
        except Exception as e:
            self.logger.error(f"启动轮询失败: {e}")
            return False
    
    def stop_polling(self) -> None:
        """停止轮询"""
        self.is_running = False
        if self.polling_thread:
            self.polling_thread.join(timeout=5)
        self.logger.info("轮询已停止")
    
    def add_price_callback(self, callback) -> None:
        """添加价格更新回调"""
        self.price_callbacks.append(callback)
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """获取最新缓存的价格"""
        return self.latest_prices.get(symbol)
    
    def _polling_worker(self) -> None:
        """轮询工作线程"""
        self.logger.info("轮询工作线程已启动")
        
        while self.is_running:
            try:
                self._poll_prices()
                
                # 等待下一次轮询
                for _ in range(self.polling_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"轮询过程中发生错误: {e}")
                time.sleep(30)  # 出错时等待30秒
    
    def _poll_prices(self) -> None:
        """轮询获取价格"""
        if not self.active_symbols:
            return
        
        self.logger.info("开始获取实时价格...")
        
        # 按顺序获取每只股票的价格，确保不超过API限制
        for i, symbol in enumerate(self.active_symbols):
            try:
                # 在获取之间添加延迟，确保不超过限制
                if i > 0:
                    time.sleep(15)  # 每次请求间隔15秒
                
                price = self.itick_provider.get_latest_price(symbol)
                
                if price and price > 0:
                    old_price = self.latest_prices.get(symbol)
                    self.latest_prices[symbol] = price
                    self.last_update_times[symbol] = datetime.now()
                    
                    # 检查价格变化
                    if old_price and abs(price - old_price) / old_price > 0.005:  # 0.5%变化
                        self.logger.info(f"{symbol} 价格更新: {old_price:.2f} -> {price:.2f}")
                        self._notify_price_change(symbol, price, old_price)
                    else:
                        self.logger.debug(f"{symbol} 价格: ${price:.2f}")
                
                else:
                    self.logger.warning(f"获取 {symbol} 价格失败")
                    
            except Exception as e:
                self.logger.error(f"获取 {symbol} 价格时出错: {e}")
        
        self.logger.info(f"价格轮询完成，下次轮询时间: {(datetime.now() + timedelta(seconds=self.polling_interval)).strftime('%H:%M:%S')}")
    
    def _notify_price_change(self, symbol: str, new_price: float, old_price: float) -> None:
        """通知价格变化"""
        try:
            # 创建简化的K线数据用于策略分析
            now = datetime.now()
            
            # 模拟K线数据（在实际应用中应该使用历史数据）
            kline = KlineData(
                symbol=symbol,
                timestamp=now,
                open=old_price,
                high=max(old_price, new_price),
                low=min(old_price, new_price),
                close=new_price,
                volume=100000,  # 模拟成交量
                timeframe="5m"
            )
            
            # 调用回调函数
            for callback in self.price_callbacks:
                try:
                    callback(kline)
                except Exception as e:
                    self.logger.error(f"价格回调函数执行失败: {e}")
                    
        except Exception as e:
            self.logger.error(f"通知价格变化失败: {e}")
    
    def get_status(self) -> Dict[str, any]:
        """获取提供者状态"""
        return {
            'is_running': self.is_running,
            'active_symbols': self.active_symbols,
            'latest_prices': self.latest_prices.copy(),
            'last_update_times': {k: v.isoformat() for k, v in self.last_update_times.items()},
            'next_poll_time': (datetime.now() + timedelta(seconds=self.polling_interval)).isoformat() if self.is_running else None
        }