#!/usr/bin/env python3
"""
30分钟K线策略测试脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from src.core.config_manager import ConfigManager
from src.data.itick_provider import ItickDataProvider
from src.strategies.simple_signal_generator import SimpleSignalGenerator

def test_30m_strategy():
    """测试30分钟K线策略"""
    print("=" * 60)
    print("30分钟K线策略测试")
    print("=" * 60)
    
    # 初始化配置
    config_manager = ConfigManager()
    
    # 创建iTick数据提供者
    provider = ItickDataProvider(config_manager)
    
    # 测试股票
    test_symbols = ['AAPL', 'MSFT', 'GOOGL']
    
    # 计算日期范围（最近7天的30分钟数据）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    print(f"查询30分钟K线数据范围: {start_date.strftime('%Y-%m-%d %H:%M')} ~ {end_date.strftime('%Y-%m-%d %H:%M')}")
    
    for symbol in test_symbols:
        print(f"\n--- 测试股票: {symbol} ---")
        
        try:
            # 获取30分钟K线数据
            klines = provider.get_historical_klines(
                symbol=symbol,
                timeframe="30m",  # 30分钟K线
                start_date=start_date,
                end_date=end_date,
                limit=100
            )
            
            if klines:
                print(f"✅ 成功获取 {len(klines)} 条30分钟K线数据")
                
                # 显示最近3条数据
                print("最近3条30分钟K线数据:")
                for i, kline in enumerate(klines[-3:]):
                    print(f"  {i+1}. {kline.timestamp.strftime('%Y-%m-%d %H:%M')} - "
                          f"开:{kline.open:.2f} 高:{kline.high:.2f} "
                          f"低:{kline.low:.2f} 收:{kline.close:.2f} "
                          f"量:{kline.volume:,}")
                
                # 生成策略信号
                print("\n生成策略信号:")
                test_strategies = ['MA_Crossover', 'RSI_Strategy', 'BollingerBands']
                
                for strategy_name in test_strategies:
                    try:
                        strategy = SimpleSignalGenerator(strategy_name)
                        
                        # 转换为DataFrame格式
                        import pandas as pd
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
                        
                        # 生成信号
                        signals = strategy.generate_signals(df)
                        
                        if signals:
                            latest_signal = signals[-1]
                            print(f"  {strategy_name}: {latest_signal.action} - {latest_signal.reason}")
                        else:
                            print(f"  {strategy_name}: 无信号")
                            
                    except Exception as e:
                        print(f"  {strategy_name}: 策略执行失败 - {e}")
                        
            else:
                print("❌ 未获取到30分钟K线数据")
                
        except Exception as e:
            print(f"❌ 获取数据失败: {e}")

def test_30m_backtest():
    """测试30分钟K线回测"""
    print("\n" + "=" * 60)
    print("30分钟K线回测测试")
    print("=" * 60)
    
    try:
        from main import QuantTradingSystem
        
        # 创建量化交易系统
        system = QuantTradingSystem()
        
        print("正在使用30分钟K线进行回测...")
        
        # 测试不同策略
        test_configs = [
            {'symbol': 'AAPL', 'strategy': 'MA_Crossover'},
            {'symbol': 'MSFT', 'strategy': 'RSI_Strategy'},
            {'symbol': 'GOOGL', 'strategy': 'BollingerBands'}
        ]
        
        for config in test_configs:
            print(f"\n--- 回测 {config['symbol']} - {config['strategy']} ---")
            
            # 临时修改时间周期为30分钟进行回测
            result = system.run_backtest(
                symbol=config['symbol'],
                strategy=config['strategy'],
                days=5,  # 较少天数以减少API调用
                initial_cash=100000
            )
            
            if result and result.get('status') == 'success':
                print(f"✅ 回测成功!")
                print(f"  收益率: {result.get('total_return_pct', 0):.2f}%")
                print(f"  交易次数: {result.get('total_trades', 0)}")
                print(f"  胜率: {result.get('win_rate', 0):.1f}%")
            else:
                print("❌ 回测失败")
                
    except Exception as e:
        print(f"❌ 回测失败: {e}")

if __name__ == "__main__":
    # 测试30分钟K线数据获取和策略信号
    test_30m_strategy()
    
    # 测试30分钟K线回测
    test_30m_backtest()
    
    print("\n" + "=" * 60)
    print("30分钟K线策略测试完成!")
    print("=" * 60)