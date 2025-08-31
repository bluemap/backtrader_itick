"""
股票池管理模块

负责管理用户自定义的股票池，支持手动输入和CSV文件导入
"""

import os
import csv
import re
import logging
from typing import List, Set, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class StockInfo:
    """股票信息"""
    symbol: str
    name: Optional[str] = None
    market: Optional[str] = None
    currency: Optional[str] = None
    is_valid: bool = True


class StockPoolManager:
    """股票池管理器"""
    
    # 支持的市场和股票格式
    SUPPORTED_MARKETS = {
        'US': ['NASDAQ', 'NYSE', 'AMEX'],  # 美股
        'HK': ['HKEX']  # 港股
    }
    
    # 美股股票代码正则表达式（1-5个字母）
    US_STOCK_PATTERN = re.compile(r'^[A-Z]{1,5}$')
    
    # 港股股票代码正则表达式（4-5位数字）
    HK_STOCK_PATTERN = re.compile(r'^\d{4,5}$')
    
    def __init__(self, config_manager=None):
        """
        初始化股票池管理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.stock_pool: Set[str] = set()
        self.stock_info: Dict[str, StockInfo] = {}
        self.logger = logging.getLogger(__name__)
    
    def load_from_config(self) -> None:
        """从配置文件加载股票池"""
        if self.config_manager:
            symbols = self.config_manager.get_stock_pool()
            self.add_stocks(symbols)
            self.logger.info(f"从配置文件加载 {len(symbols)} 只股票")
    
    def add_stock(self, symbol: str) -> bool:
        """
        添加单只股票到股票池
        
        Args:
            symbol: 股票代码
            
        Returns:
            bool: 是否添加成功
        """
        # 标准化股票代码
        symbol = self.normalize_symbol(symbol)
        
        if not symbol:
            self.logger.warning(f"无效的股票代码: {symbol}")
            return False
        
        # 验证股票代码格式
        if not self.is_valid_symbol_format(symbol):
            self.logger.warning(f"股票代码格式无效: {symbol}")
            return False
        
        # 添加到股票池
        self.stock_pool.add(symbol)
        
        # 创建股票信息
        if symbol not in self.stock_info:
            market = self.detect_market(symbol)
            self.stock_info[symbol] = StockInfo(
                symbol=symbol,
                market=market,
                is_valid=True
            )
        
        self.logger.info(f"添加股票到股票池: {symbol}")
        return True
    
    def add_stocks(self, symbols: List[str]) -> Dict[str, bool]:
        """
        批量添加股票到股票池
        
        Args:
            symbols: 股票代码列表
            
        Returns:
            Dict[str, bool]: 每只股票的添加结果
        """
        results = {}
        for symbol in symbols:
            results[symbol] = self.add_stock(symbol)
        
        successful_count = sum(results.values())
        self.logger.info(f"批量添加股票完成: 成功 {successful_count}/{len(symbols)}")
        
        return results
    
    def remove_stock(self, symbol: str) -> bool:
        """
        从股票池移除股票
        
        Args:
            symbol: 股票代码
            
        Returns:
            bool: 是否移除成功
        """
        symbol = self.normalize_symbol(symbol)
        
        if symbol in self.stock_pool:
            self.stock_pool.remove(symbol)
            if symbol in self.stock_info:
                del self.stock_info[symbol]
            self.logger.info(f"从股票池移除股票: {symbol}")
            return True
        
        self.logger.warning(f"股票不在股票池中: {symbol}")
        return False
    
    def load_from_csv(self, csv_file_path: str, symbol_column: str = 'symbol') -> Dict[str, bool]:
        """
        从CSV文件加载股票池
        
        Args:
            csv_file_path: CSV文件路径
            symbol_column: 股票代码列名
            
        Returns:
            Dict[str, bool]: 每只股票的加载结果
        """
        if not os.path.exists(csv_file_path):
            self.logger.error(f"CSV文件不存在: {csv_file_path}")
            return {}
        
        results = {}
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                if symbol_column not in reader.fieldnames:
                    self.logger.error(f"CSV文件中未找到列: {symbol_column}")
                    return {}
                
                symbols = []
                for row in reader:
                    symbol = row.get(symbol_column, '').strip()
                    if symbol:
                        symbols.append(symbol)
                        
                        # 如果有其他信息，也保存
                        if 'name' in row:
                            symbol_normalized = self.normalize_symbol(symbol)
                            if symbol_normalized in self.stock_info:
                                self.stock_info[symbol_normalized].name = row['name'].strip()
                
                results = self.add_stocks(symbols)
                self.logger.info(f"从CSV文件加载股票池完成: {csv_file_path}")
        
        except Exception as e:
            self.logger.error(f"加载CSV文件失败: {e}")
        
        return results
    
    def save_to_csv(self, csv_file_path: str) -> bool:
        """
        保存股票池到CSV文件
        
        Args:
            csv_file_path: CSV文件路径
            
        Returns:
            bool: 是否保存成功
        """
        try:
            os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)
            
            with open(csv_file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['symbol', 'name', 'market', 'is_valid'])
                
                for symbol in sorted(self.stock_pool):
                    info = self.stock_info.get(symbol, StockInfo(symbol=symbol))
                    writer.writerow([
                        info.symbol,
                        info.name or '',
                        info.market or '',
                        info.is_valid
                    ])
            
            self.logger.info(f"股票池已保存到CSV文件: {csv_file_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"保存CSV文件失败: {e}")
            return False
    
    def get_stock_pool(self) -> List[str]:
        """
        获取股票池列表
        
        Returns:
            List[str]: 股票代码列表
        """
        return list(self.stock_pool)
    
    def get_valid_stocks(self) -> List[str]:
        """
        获取有效的股票列表
        
        Returns:
            List[str]: 有效股票代码列表
        """
        return [
            symbol for symbol in self.stock_pool
            if self.stock_info.get(symbol, StockInfo(symbol=symbol)).is_valid
        ]
    
    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """
        获取股票信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            Optional[StockInfo]: 股票信息
        """
        symbol = self.normalize_symbol(symbol)
        return self.stock_info.get(symbol)
    
    def get_stocks_by_market(self, market: str) -> List[str]:
        """
        按市场获取股票列表
        
        Args:
            market: 市场代码（US/HK）
            
        Returns:
            List[str]: 股票代码列表
        """
        return [
            symbol for symbol in self.stock_pool
            if self.stock_info.get(symbol, StockInfo(symbol=symbol)).market == market
        ]
    
    def clear_stock_pool(self) -> None:
        """清空股票池"""
        self.stock_pool.clear()
        self.stock_info.clear()
        self.logger.info("股票池已清空")
    
    def deduplicate(self) -> int:
        """
        股票池去重
        
        Returns:
            int: 去除的重复股票数量
        """
        original_count = len(self.stock_pool)
        # Set 本身就是去重的，这里主要是为了清理 stock_info
        valid_symbols = set(self.stock_pool)
        
        # 清理无效的股票信息
        invalid_symbols = set(self.stock_info.keys()) - valid_symbols
        for symbol in invalid_symbols:
            del self.stock_info[symbol]
        
        removed_count = original_count - len(self.stock_pool)
        if removed_count > 0:
            self.logger.info(f"股票池去重完成，移除 {removed_count} 只重复股票")
        
        return removed_count
    
    def validate_stocks(self) -> Dict[str, bool]:
        """
        验证股票池中所有股票的有效性
        
        Returns:
            Dict[str, bool]: 每只股票的验证结果
        """
        results = {}
        
        for symbol in self.stock_pool:
            is_valid = self.validate_stock(symbol)
            results[symbol] = is_valid
            
            # 更新股票信息
            if symbol in self.stock_info:
                self.stock_info[symbol].is_valid = is_valid
        
        valid_count = sum(results.values())
        self.logger.info(f"股票验证完成: {valid_count}/{len(self.stock_pool)} 只股票有效")
        
        return results
    
    def normalize_symbol(self, symbol: str) -> str:
        """
        标准化股票代码
        
        Args:
            symbol: 原始股票代码
            
        Returns:
            str: 标准化后的股票代码
        """
        if not symbol:
            return ""
        
        # 去除空格并转换为大写
        symbol = symbol.strip().upper()
        
        # 移除常见的前缀后缀
        symbol = symbol.replace('.', '')
        
        return symbol
    
    def is_valid_symbol_format(self, symbol: str) -> bool:
        """
        验证股票代码格式
        
        Args:
            symbol: 股票代码
            
        Returns:
            bool: 格式是否有效
        """
        if not symbol:
            return False
        
        # 美股格式验证
        if self.US_STOCK_PATTERN.match(symbol):
            return True
        
        # 港股格式验证（如果以数字开头）
        if symbol.isdigit() and self.HK_STOCK_PATTERN.match(symbol):
            return True
        
        return False
    
    def detect_market(self, symbol: str) -> str:
        """
        检测股票所属市场
        
        Args:
            symbol: 股票代码
            
        Returns:
            str: 市场代码
        """
        if self.US_STOCK_PATTERN.match(symbol):
            return 'US'
        elif symbol.isdigit() and self.HK_STOCK_PATTERN.match(symbol):
            return 'HK'
        else:
            return 'UNKNOWN'
    
    def validate_stock(self, symbol: str) -> bool:
        """
        验证单只股票是否有效
        这里只做基本的格式验证，实际验证需要调用 iTick API
        
        Args:
            symbol: 股票代码
            
        Returns:
            bool: 是否有效
        """
        # 基本格式验证
        if not self.is_valid_symbol_format(symbol):
            return False
        
        # TODO: 这里可以集成 iTick API 进行实际验证
        # 目前只返回格式验证结果
        return True
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取股票池摘要信息
        
        Returns:
            Dict[str, Any]: 摘要信息
        """
        total_count = len(self.stock_pool)
        valid_count = len(self.get_valid_stocks())
        
        market_counts = {}
        for market in ['US', 'HK', 'UNKNOWN']:
            market_counts[market] = len(self.get_stocks_by_market(market))
        
        return {
            'total_stocks': total_count,
            'valid_stocks': valid_count,
            'invalid_stocks': total_count - valid_count,
            'market_distribution': market_counts,
            'stock_list': sorted(self.stock_pool)
        }