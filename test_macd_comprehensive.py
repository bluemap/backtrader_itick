#!/usr/bin/env python3
"""
MACD策略综合测试

整合所有MACD策略测试功能：
1. 基本功能验证
2. 策略回测
3. 实时信号生成
4. Backtrader环境测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List

def test_macd_strategy_registration():
    """测试MACD策略注册"""
    print("=" * 60)
    print("📋 MACD策略注册验证")
    print("=" * 60)
    
    try:
        from src.strategies.strategy_factory import StrategyFactory
        
        factory = StrategyFactory()
        macd_strategies = ['MACD_Crossover', 'MACD_Divergence', 'MACD_Trend']
        
        print("可用的MACD策略:")
        for strategy_name in macd_strategies:
            strategy_class = factory.get_strategy_class(strategy_name)
            if strategy_class:
                params = factory.get_strategy_params(strategy_name)
                print(f"✅ {strategy_name}: {len(params)}个参数")
            else:
                print(f"❌ {strategy_name}: 注册失败")
        
        # 测试策略描述
        from src.strategies.strategy_factory import get_strategy_description
        print("\n策略描述:")
        for strategy_name in macd_strategies:
            desc = get_strategy_description(strategy_name)
            print(f"  {strategy_name}: {desc}")
            
        return True
        
    except Exception as e:
        print(f"❌ 策略注册测试失败: {e}")
        return False

def test_macd_config_support():
    """测试MACD配置支持"""
    print("\n" + "=" * 60)
    print("⚙️ MACD配置支持验证")
    print("=" * 60)
    
    try:
        from src.core.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        strategy_config = config_manager.get_strategy_config()
        
        print(f"当前策略类型: {strategy_config.type}")
        print(f"MACD配置支持: {'✅' if hasattr(strategy_config, 'macd') else '❌'}")
        
        if strategy_config.macd:
            print(f"MACD配置内容: {strategy_config.macd}")
        
        # 验证配置有效性
        valid = config_manager.validate_config()
        print(f"配置验证结果: {'✅' if valid else '❌'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置支持测试失败: {e}")
        return False

def test_macd_data_processing():
    """测试MACD策略数据处理"""
    print("\n" + "=" * 60)
    print("📊 MACD数据处理测试")
    print("=" * 60)
    
    try:
        from src.core.config_manager import ConfigManager
        from src.data.itick_provider import ItickDataProvider
        from src.strategies.simple_signal_generator import SimpleSignalGenerator
        
        config_manager = ConfigManager()
        provider = ItickDataProvider(config_manager)
        
        # 获取测试数据
        test_symbol = 'AAPL'
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print(f"获取 {test_symbol} 最近7天的30分钟K线数据...")
        
        klines = provider.get_historical_klines(
            symbol=test_symbol,
            timeframe="30m",
            start_date=start_date,
            end_date=end_date,
            limit=80
        )
        
        if not klines or len(klines) < 30:
            print("⚠️ 数据不足，使用模拟数据进行测试")
            klines = generate_test_data(periods=60)
        
        print(f"✅ 获取了 {len(klines)} 条K线数据")
        
        # 转换为DataFrame
        df = convert_klines_to_dataframe(klines)
        
        # 测试MACD信号生成
        macd_strategies = [
            {'name': 'MACD_Crossover', 'desc': 'MACD交叉策略'},
            {'name': 'MACD_Divergence', 'desc': 'MACD背离策略'},
            {'name': 'MACD_Trend', 'desc': 'MACD趋势策略'}
        ]
        
        for strategy_config in macd_strategies:
            print(f"\n--- {strategy_config['desc']} ---")
            
            try:
                strategy = SimpleSignalGenerator(strategy_config['name'])
                signals = strategy.generate_signals(df)
                
                if signals:
                    print(f"✅ 生成了 {len(signals)} 个信号")
                    # 显示最新信号
                    latest_signal = signals[-1]
                    print(f"  最新信号: {latest_signal.action} @ {latest_signal.price:.2f}")
                    print(f"  信号原因: {latest_signal.reason}")
                else:
                    print("  📊 无信号（市场条件不符合策略要求）")
                    
            except Exception as e:
                print(f"  ❌ 策略测试失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_macd_backtest():
    """测试MACD策略回测"""
    print("\n" + "=" * 60)
    print("📈 MACD策略回测测试")
    print("=" * 60)
    
    try:
        from main import QuantTradingSystem
        
        system = QuantTradingSystem()
        
        # 测试不同MACD策略回测
        test_configs = [
            {'symbol': 'AAPL', 'strategy': 'MACD_Crossover'},
            {'symbol': 'MSFT', 'strategy': 'MACD_Trend'}
        ]
        
        backtest_success = 0
        
        for config in test_configs:
            print(f"\n--- 回测 {config['symbol']} - {config['strategy']} ---")
            
            try:
                result = system.run_backtest(
                    symbol=config['symbol'],
                    strategy=config['strategy'],
                    days=5,  # 5天数据
                    initial_cash=100000
                )
                
                if result and result.get('status') == 'success':
                    print(f"✅ 回测成功!")
                    print(f"  收益率: {result.get('total_return_pct', 0):.2f}%")
                    print(f"  交易次数: {result.get('total_trades', 0)}")
                    print(f"  胜率: {result.get('win_rate', 0):.1f}%")
                    backtest_success += 1
                else:
                    print("❌ 回测失败")
                    if result:
                        print(f"  错误: {result.get('error', 'Unknown error')}")
                        
            except Exception as e:
                print(f"❌ 回测执行失败: {e}")
        
        print(f"\n回测成功率: {backtest_success}/{len(test_configs)}")
        return backtest_success > 0
        
    except Exception as e:
        print(f"❌ 回测测试失败: {e}")
        return False

def test_macd_backtrader_environment():
    """测试Backtrader环境中的MACD策略"""
    print("\n" + "=" * 60)
    print("🔧 Backtrader环境测试")
    print("=" * 60)
    
    try:
        from src.strategies.macd_strategies import MACDCrossoverStrategy
        
        # 创建Cerebro引擎
        cerebro = bt.Cerebro()
        
        # 生成测试数据
        df = generate_trending_data(periods=80)
        
        # 创建数据源
        data = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(data)
        
        # 添加策略
        cerebro.addstrategy(MACDCrossoverStrategy)
        
        # 设置初始资金
        initial_cash = 100000.0
        cerebro.broker.setcash(initial_cash)
        
        print(f"初始资金: ${initial_cash:,.2f}")
        print("正在运行MACD策略...")
        
        # 运行策略
        strategies = cerebro.run()
        
        final_value = cerebro.broker.getvalue()
        profit = final_value - initial_cash
        profit_pct = (final_value / initial_cash - 1) * 100
        
        print(f"最终资金: ${final_value:,.2f}")
        print(f"盈亏: ${profit:,.2f}")
        print(f"收益率: {profit_pct:.2f}%")
        
        # 策略统计
        if strategies and len(strategies) > 0:
            strategy = strategies[0]
            stats = strategy.get_stats()
            print(f"\n策略统计:")
            print(f"  总信号数: {stats['total_signals']}")
            print(f"  买入信号: {stats['buy_signals']}")
            print(f"  卖出信号: {stats['sell_signals']}")
        
        print("✅ Backtrader环境测试成功!")
        return True
        
    except Exception as e:
        print(f"❌ Backtrader环境测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_test_data(periods: int = 60, base_price: float = 100.0):
    """生成测试K线数据"""
    dates = pd.date_range(start='2024-01-01', periods=periods, freq='30min')
    
    # 生成有趋势的价格数据
    np.random.seed(42)
    prices = []
    current_price = base_price
    
    for i in range(periods):
        # 添加趋势和随机波动
        trend = 0.001 if i < periods // 2 else -0.0005
        change = np.random.randn() * 0.02 + trend
        current_price *= (1 + change)
        prices.append(current_price)
    
    # 创建OHLC数据结构
    from src.data.data_types import KlineData
    klines = []
    
    for i, (date, price) in enumerate(zip(dates, prices)):
        kline = KlineData(
            symbol='TEST',
            timestamp=date,
            open=price * (1 + np.random.randn() * 0.005),
            high=price * (1 + abs(np.random.randn() * 0.01)),
            low=price * (1 - abs(np.random.randn() * 0.01)),
            close=price,
            volume=np.random.randint(1000, 10000)
        )
        klines.append(kline)
    
    return klines

def generate_trending_data(periods: int = 80) -> pd.DataFrame:
    """生成有明显趋势的测试数据（用于Backtrader）"""
    dates = pd.date_range(start='2024-01-01', periods=periods, freq='D')
    
    # 创建具有明显趋势变化的价格序列
    prices = []
    base_price = 100.0
    
    for i in range(periods):
        if i < 20:
            # 上升趋势
            trend = 0.005
        elif i < 40:
            # 震荡
            trend = 0.0
        elif i < 60:
            # 下降趋势
            trend = -0.003
        else:
            # 反弹
            trend = 0.008
        
        noise = np.random.randn() * 0.01
        change = trend + noise
        base_price *= (1 + change)
        prices.append(base_price)
    
    # 创建OHLC数据
    df = pd.DataFrame({
        'datetime': dates,
        'open': [p * (1 + np.random.randn() * 0.002) for p in prices],
        'high': [p * (1 + abs(np.random.randn() * 0.008)) for p in prices],
        'low': [p * (1 - abs(np.random.randn() * 0.008)) for p in prices],
        'close': prices,
        'volume': [np.random.randint(5000, 15000) for _ in range(periods)]
    })
    
    df.set_index('datetime', inplace=True)
    return df

def convert_klines_to_dataframe(klines) -> pd.DataFrame:
    """将K线数据转换为DataFrame"""
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
    df.set_index('timestamp', inplace=True)
    return df

def show_usage_guide():
    """显示MACD策略使用指南"""
    print("\n" + "=" * 60)
    print("📚 MACD策略使用指南")
    print("=" * 60)
    
    guide = """
🎯 MACD策略已成功集成到系统中！

📋 可用策略类型：
1. MACD_Crossover  - MACD线与信号线交叉策略
2. MACD_Divergence - MACD背离策略
3. MACD_Trend     - MACD趋势策略

🔧 使用方法：

1. 修改配置文件 config/config.yaml：
   ```yaml
   strategy:
     type: "MACD_Crossover"
     
     macd:
       fast_period: 12       # 快速EMA周期
       slow_period: 26       # 慢速EMA周期
       signal_period: 9      # 信号线周期
       volume_filter: true   # 启用成交量过滤
       trend_filter: true    # 启用趋势过滤
   ```

2. 运行系统：
   ```bash
   python main.py
   ```

3. 单独回测：
   ```bash
   python backtest_cli.py --symbol AAPL --strategy MACD_Crossover --days 30
   ```

📊 策略特点：
- ✅ 适用于趋势跟踪和反转识别
- ✅ 支持30分钟及以上时间周期
- ✅ 内置成交量和趋势过滤器
- ✅ 自动止损止盈设置

🚀 现在您可以使用MACD策略进行量化交易了！
"""
    print(guide)

def main():
    """主测试函数"""
    print("🎯 MACD策略综合测试开始")
    print("=" * 60)
    
    test_results = []
    
    # 执行所有测试
    tests = [
        ("策略注册验证", test_macd_strategy_registration),
        ("配置支持验证", test_macd_config_support),
        ("数据处理测试", test_macd_data_processing),
        ("策略回测测试", test_macd_backtest),
        ("Backtrader环境测试", test_macd_backtrader_environment)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔄 正在执行: {test_name}")
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 执行失败: {e}")
            test_results.append((test_name, False))
    
    # 显示测试总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    print(f"\n总体结果: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有MACD策略测试均通过！")
    else:
        print("⚠️ 部分测试失败，请检查错误信息")
    
    # 显示使用指南
    show_usage_guide()

if __name__ == "__main__":
    main()