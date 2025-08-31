"""
配置管理模块

负责加载和管理系统配置，支持 YAML 格式配置文件
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ItickConfig:
    """iTick API 配置"""
    api_key: str
    base_url: str = "https://api.itick.com"
    websocket_url: str = "wss://api.itick.com/ws"
    timeout: int = 30
    simulation_mode: bool = False  # 模拟模式
    requests_per_minute: int = 5  # 每分钟请求限制
    enable_rate_limiting: bool = True  # 启用限流


@dataclass
class StrategyConfig:
    """策略配置"""
    type: str
    ma_crossover: Optional[Dict[str, Any]] = None
    rsi_strategy: Optional[Dict[str, Any]] = None
    bollinger_bands: Optional[Dict[str, Any]] = None
    breakout: Optional[Dict[str, Any]] = None
    momentum: Optional[Dict[str, Any]] = None
    macd: Optional[Dict[str, Any]] = None


@dataclass
class NotificationConfig:
    """通知配置"""
    enabled: bool = True
    feishu: Optional[Dict[str, Any]] = None
    wechat: Optional[Dict[str, Any]] = None
    frequency: Optional[Dict[str, Any]] = None
    message_template: Optional[Dict[str, Any]] = None


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    log_dir: str = "logs"
    max_file_size: str = "10MB"
    backup_count: int = 5
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class DataConfig:
    """数据配置"""
    historical_dir: str = "data/historical"
    format: str = "csv"
    update_interval: int = 60
    timeframe: str = "1m"


@dataclass
class RiskControlConfig:
    """风险控制配置"""
    max_signals_per_day: int = 100
    max_position_per_stock: float = 0.1
    default_stop_loss: float = 0.05
    default_take_profit: float = 0.10


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为 config/config.yaml
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "config", "config.yaml")
        
        self.config_path = config_path
        self.config_data = {}
        self.load_config()
    
    def load_config(self) -> None:
        """加载配置文件"""
        try:
            if not os.path.exists(self.config_path):
                raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self.config_data = yaml.safe_load(file)
            
            logging.info(f"配置文件加载成功: {self.config_path}")
        
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}")
            raise
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点分隔的嵌套键，如 'itick.api_key'
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config_data
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_itick_config(self) -> ItickConfig:
        """获取 iTick 配置"""
        itick_data = self.config_data.get('itick', {})
        rate_limit = itick_data.get('rate_limit', {})
        
        return ItickConfig(
            api_key=itick_data.get('api_key', ''),
            base_url=itick_data.get('base_url', 'https://api.itick.com'),
            websocket_url=itick_data.get('websocket_url', 'wss://api.itick.com/ws'),
            timeout=itick_data.get('timeout', 30),
            simulation_mode=itick_data.get('simulation_mode', False),
            requests_per_minute=rate_limit.get('requests_per_minute', 5),
            enable_rate_limiting=rate_limit.get('enable_rate_limiting', True)
        )
    
    def get_stock_pool(self) -> list:
        """获取股票池配置"""
        return self.config_data.get('stock_pool', {}).get('symbols', [])
    
    def get_strategy_config(self) -> StrategyConfig:
        """获取策略配置"""
        strategy_data = self.config_data.get('strategy', {})
        return StrategyConfig(
            type=strategy_data.get('type', 'MA_Crossover'),
            ma_crossover=strategy_data.get('ma_crossover'),
            rsi_strategy=strategy_data.get('rsi_strategy'),
            bollinger_bands=strategy_data.get('bollinger_bands'),
            breakout=strategy_data.get('breakout'),
            momentum=strategy_data.get('momentum'),
            macd=strategy_data.get('macd')
        )
    
    def get_notification_config(self) -> NotificationConfig:
        """获取通知配置"""
        notification_data = self.config_data.get('notification', {})
        return NotificationConfig(
            enabled=notification_data.get('enabled', True),
            feishu=notification_data.get('feishu'),
            wechat=notification_data.get('wechat'),
            frequency=notification_data.get('frequency'),
            message_template=notification_data.get('message_template')
        )
    
    def get_logging_config(self) -> LoggingConfig:
        """获取日志配置"""
        logging_data = self.config_data.get('logging', {})
        return LoggingConfig(
            level=logging_data.get('level', 'INFO'),
            log_dir=logging_data.get('log_dir', 'logs'),
            max_file_size=logging_data.get('max_file_size', '10MB'),
            backup_count=logging_data.get('backup_count', 5),
            format=logging_data.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
    
    def get_data_config(self) -> DataConfig:
        """获取数据配置"""
        data_config = self.config_data.get('data', {})
        return DataConfig(
            historical_dir=data_config.get('historical_dir', 'data/historical'),
            format=data_config.get('format', 'csv'),
            update_interval=data_config.get('update_interval', 60),
            timeframe=data_config.get('timeframe', '1m')
        )
    
    def get_risk_control_config(self) -> RiskControlConfig:
        """获取风险控制配置"""
        risk_data = self.config_data.get('risk_control', {})
        return RiskControlConfig(
            max_signals_per_day=risk_data.get('max_signals_per_day', 100),
            max_position_per_stock=risk_data.get('max_position_per_stock', 0.1),
            default_stop_loss=risk_data.get('default_stop_loss', 0.05),
            default_take_profit=risk_data.get('default_take_profit', 0.10)
        )
    
    def update_config(self, key: str, value: Any) -> None:
        """
        更新配置值
        
        Args:
            key: 配置键，支持点分隔的嵌套键
            value: 新的配置值
        """
        keys = key.split('.')
        config = self.config_data
        
        # 导航到正确的位置
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置值
        config[keys[-1]] = value
    
    def save_config(self) -> None:
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as file:
                yaml.dump(self.config_data, file, default_flow_style=False, allow_unicode=True)
            
            logging.info(f"配置文件保存成功: {self.config_path}")
        
        except Exception as e:
            logging.error(f"保存配置文件失败: {e}")
            raise
    
    def reload_config(self) -> None:
        """重新加载配置文件"""
        self.load_config()
    
    def validate_config(self) -> bool:
        """
        验证配置文件的有效性
        
        Returns:
            bool: 配置是否有效
        """
        required_keys = [
            'itick.api_key',
            'stock_pool.symbols',
            'strategy.type'
        ]
        
        for key in required_keys:
            if self.get_config(key) is None:
                logging.error(f"缺少必需的配置项: {key}")
                return False
        
        # 验证策略类型
        valid_strategies = ['MA_Crossover', 'RSI_Strategy', 'BollingerBands', 'Breakout', 'Momentum', 
                           'MACD_Crossover', 'MACD_Divergence', 'MACD_Trend']
        strategy_type = self.get_config('strategy.type')
        if strategy_type not in valid_strategies:
            logging.error(f"无效的策略类型: {strategy_type}")
            return False
        
        # 验证 iTick API Key
        api_key = self.get_config('itick.api_key')
        if not api_key or api_key == 'your_itick_api_key_here':
            logging.warning("请设置有效的 iTick API Key")
        
        return True


# 全局配置管理器实例
config_manager = ConfigManager()