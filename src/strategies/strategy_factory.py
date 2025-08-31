"""
策略工厂

用于创建和管理不同类型的策略
"""

import logging
from typing import Dict, Type, Any, Optional

from .base_strategy import BaseStrategy
from .ma_crossover_strategies import (
    MovingAverageCrossoverStrategy,
    AdaptiveMovingAverageCrossoverStrategy, 
    TripleMovingAverageCrossoverStrategy
)
from .rsi_strategies import (
    RSIStrategy,
    RSIDivergenceStrategy,
    RSIBollingerStrategy
)
from .bollinger_strategies import (
    BollingerBandsStrategy,
    BollingerBreakoutStrategy,
    BollingerMeanReversionStrategy
)
from .breakout_strategies import (
    BreakoutStrategy,
    DonchianBreakoutStrategy,
    VolatilityBreakoutStrategy
)
from .momentum_strategies import (
    MomentumStrategy,
    AcceleratedMomentumStrategy,
    RelativeStrengthMomentumStrategy,
    TrendFollowingMomentumStrategy
)
from .macd_strategies import (
    MACDCrossoverStrategy,
    MACDDivergenceStrategy,
    MACDTrendStrategy
)


class StrategyFactory:
    """策略工厂类"""
    
    # 策略注册表
    _strategies: Dict[str, Type[BaseStrategy]] = {}
    
    @classmethod
    def register_strategy(cls, name: str, strategy_class: Type[BaseStrategy]) -> None:
        """
        注册策略
        
        Args:
            name: 策略名称
            strategy_class: 策略类
        """
        cls._strategies[name] = strategy_class
        logging.info(f"策略已注册: {name}")
    
    @classmethod
    def get_strategy_class(cls, name: str) -> Optional[Type[BaseStrategy]]:
        """
        获取策略类
        
        Args:
            name: 策略名称
            
        Returns:
            Optional[Type[BaseStrategy]]: 策略类
        """
        return cls._strategies.get(name)
    
    @classmethod
    def create_strategy(cls, name: str, **kwargs) -> Optional[BaseStrategy]:
        """
        创建策略实例
        
        Args:
            name: 策略名称
            **kwargs: 策略参数
            
        Returns:
            Optional[BaseStrategy]: 策略实例
        """
        strategy_class = cls.get_strategy_class(name)
        if strategy_class:
            return strategy_class(**kwargs)
        else:
            logging.error(f"未找到策略: {name}")
            return None
    
    @classmethod
    def list_strategies(cls) -> Dict[str, str]:
        """
        列出所有可用策略
        
        Returns:
            Dict[str, str]: 策略名称和描述的字典
        """
        strategies = {}
        for name, strategy_class in cls._strategies.items():
            doc = strategy_class.__doc__ or "无描述"
            strategies[name] = doc.strip().split('\n')[0]
        
        return strategies
    
    @classmethod
    def get_strategy_params(cls, name: str) -> Dict[str, Any]:
        """
        获取策略的默认参数
        
        Args:
            name: 策略名称
            
        Returns:
            Dict[str, Any]: 策略参数
        """
        strategy_class = cls.get_strategy_class(name)
        if not strategy_class:
            return {}
        
        params = {}
        
        # 尝试多种方式获取参数
        try:
            # 方法1: 检查是否有params属性且可迭代
            if hasattr(strategy_class, 'params') and hasattr(strategy_class.params, '__iter__'):
                for param_tuple in strategy_class.params:
                    if isinstance(param_tuple, (tuple, list)) and len(param_tuple) >= 2:
                        param_name = param_tuple[0]
                        param_default = param_tuple[1]
                        params[param_name] = param_default
            
            # 方法2: 检查是否有_getdefaults方法（Backtrader特有）
            elif hasattr(strategy_class, '_getdefaults'):
                defaults = strategy_class._getdefaults()
                if isinstance(defaults, dict):
                    params.update(defaults)
            
            # 方法3: 直接检查类属性
            elif hasattr(strategy_class, 'params'):
                param_obj = getattr(strategy_class, 'params', None)
                if hasattr(param_obj, '__dict__'):
                    params.update(param_obj.__dict__)
                    
        except Exception as e:
            logging.warning(f"获取策略参数失败: {e}")
            # 返回一些通用默认值
            params = {
                'stop_loss_pct': 0.05,
                'take_profit_pct': 0.10,
                'debug': False
            }
        
        return params


# 注册所有策略
def register_all_strategies():
    """注册所有内置策略"""
    
    # 均线交叉策略
    StrategyFactory.register_strategy("MA_Crossover", MovingAverageCrossoverStrategy)
    StrategyFactory.register_strategy("Adaptive_MA_Crossover", AdaptiveMovingAverageCrossoverStrategy)
    StrategyFactory.register_strategy("Triple_MA_Crossover", TripleMovingAverageCrossoverStrategy)
    
    # RSI策略
    StrategyFactory.register_strategy("RSI_Strategy", RSIStrategy)
    StrategyFactory.register_strategy("RSI_Divergence", RSIDivergenceStrategy)
    StrategyFactory.register_strategy("RSI_Bollinger", RSIBollingerStrategy)
    
    # 布林带策略
    StrategyFactory.register_strategy("BollingerBands", BollingerBandsStrategy)
    StrategyFactory.register_strategy("Bollinger_Breakout", BollingerBreakoutStrategy)
    StrategyFactory.register_strategy("Bollinger_MeanReversion", BollingerMeanReversionStrategy)
    
    # 突破策略
    StrategyFactory.register_strategy("Breakout", BreakoutStrategy)
    StrategyFactory.register_strategy("Donchian_Breakout", DonchianBreakoutStrategy)
    StrategyFactory.register_strategy("Volatility_Breakout", VolatilityBreakoutStrategy)
    
    # 动量策略
    StrategyFactory.register_strategy("Momentum", MomentumStrategy)
    StrategyFactory.register_strategy("Accelerated_Momentum", AcceleratedMomentumStrategy)
    StrategyFactory.register_strategy("RelativeStrength_Momentum", RelativeStrengthMomentumStrategy)
    StrategyFactory.register_strategy("TrendFollowing_Momentum", TrendFollowingMomentumStrategy)
    
    # MACD策略
    StrategyFactory.register_strategy("MACD_Crossover", MACDCrossoverStrategy)
    StrategyFactory.register_strategy("MACD_Divergence", MACDDivergenceStrategy)
    StrategyFactory.register_strategy("MACD_Trend", MACDTrendStrategy)


# 策略配置映射
STRATEGY_CONFIG_MAP = {
    "MA_Crossover": "ma_crossover",
    "Adaptive_MA_Crossover": "ma_crossover",
    "Triple_MA_Crossover": "ma_crossover",
    "RSI_Strategy": "rsi_strategy",
    "RSI_Divergence": "rsi_strategy", 
    "RSI_Bollinger": "rsi_strategy",
    "BollingerBands": "bollinger_bands",
    "Bollinger_Breakout": "bollinger_bands",
    "Bollinger_MeanReversion": "bollinger_bands",
    "Breakout": "breakout",
    "Donchian_Breakout": "breakout",
    "Volatility_Breakout": "breakout",
    "Momentum": "momentum",
    "Accelerated_Momentum": "momentum",
    "RelativeStrength_Momentum": "momentum",
    "TrendFollowing_Momentum": "momentum",
    "MACD_Crossover": "macd",
    "MACD_Divergence": "macd",
    "MACD_Trend": "macd"
}


def get_strategy_config_from_manager(config_manager, strategy_name: str) -> Dict[str, Any]:
    """
    从配置管理器获取策略配置
    
    Args:
        config_manager: 配置管理器
        strategy_name: 策略名称
        
    Returns:
        Dict[str, Any]: 策略配置参数
    """
    if not config_manager:
        return {}
    
    # 获取策略配置
    strategy_config = config_manager.get_strategy_config()
    
    # 根据策略名称获取对应的配置部分
    config_key = STRATEGY_CONFIG_MAP.get(strategy_name)
    if config_key:
        config_section = getattr(strategy_config, config_key, None)
        if config_section:
            return config_section
    
    return {}


def create_strategy_from_config(config_manager, override_params: Dict[str, Any] = None) -> Optional[BaseStrategy]:
    """
    根据配置创建策略
    
    Args:
        config_manager: 配置管理器
        override_params: 覆盖参数
        
    Returns:
        Optional[BaseStrategy]: 策略实例
    """
    if not config_manager:
        logging.error("配置管理器为空")
        return None
    
    strategy_config = config_manager.get_strategy_config()
    strategy_name = strategy_config.type
    
    # 获取策略默认参数
    default_params = StrategyFactory.get_strategy_params(strategy_name)
    
    # 获取配置文件中的参数
    config_params = get_strategy_config_from_manager(config_manager, strategy_name)
    
    # 合并参数
    final_params = {}
    final_params.update(default_params)
    final_params.update(config_params)
    
    if override_params:
        final_params.update(override_params)
    
    # 添加风险控制参数
    risk_config = config_manager.get_risk_control_config()
    final_params.update({
        'stop_loss_pct': risk_config.default_stop_loss,
        'take_profit_pct': risk_config.default_take_profit
    })
    
    logging.info(f"创建策略: {strategy_name}, 参数: {final_params}")
    
    return StrategyFactory.create_strategy(strategy_name, **final_params)


# 初始化时注册所有策略
register_all_strategies()


# 策略描述
STRATEGY_DESCRIPTIONS = {
    "MA_Crossover": "基于短期和长期移动平均线交叉的经典策略",
    "Adaptive_MA_Crossover": "自适应移动平均线交叉策略，根据市场波动率动态调整参数",
    "Triple_MA_Crossover": "三重移动平均线策略，提供更多确认信号",
    "RSI_Strategy": "基于RSI超买超卖信号的策略",
    "RSI_Divergence": "RSI背离策略，寻找价格与RSI的背离信号",
    "RSI_Bollinger": "RSI与布林带组合策略",
    "BollingerBands": "布林带均值回归策略",
    "Bollinger_Breakout": "布林带突破策略，在窄幅震荡后寻找突破机会",
    "Bollinger_MeanReversion": "布林带均值回归策略，结合RSI确认",
    "Breakout": "价格突破策略，基于支撑阻力位突破",
    "Donchian_Breakout": "唐奇安通道突破策略",
    "Volatility_Breakout": "波动率突破策略，在低波动后寻找突破",
    "Momentum": "价格动量策略，跟随强势动量",
    "Accelerated_Momentum": "加速动量策略，寻找动量加速的机会",
    "RelativeStrength_Momentum": "相对强度动量策略",
    "TrendFollowing_Momentum": "趋势跟随动量策略，结合ADX确认趋势强度",
    "MACD_Crossover": "MACD交叉策略，基于MACD线与信号线的交叉信号",
    "MACD_Divergence": "MACD背离策略，寻找价格与MACD的背离信号",
    "MACD_Trend": "MACD趋势策略，结合长期趋势的MACD信号"
}


def get_strategy_description(strategy_name: str) -> str:
    """
    获取策略描述
    
    Args:
        strategy_name: 策略名称
        
    Returns:
        str: 策略描述
    """
    return STRATEGY_DESCRIPTIONS.get(strategy_name, "无描述")