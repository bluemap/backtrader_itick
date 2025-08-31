#!/usr/bin/env python3
"""
测试修复后的iTick API获取真实历史数据
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from src.core.config_manager import ConfigManager
from src.data.itick_provider import ItickDataProvider

def test_real_itick_data():
    """测试获取真实iTick历史数据"""
    print("=" * 60)
    print("测试真实iTick历史数据获取")
    print("=" * 60)
    
    # 初始化配置
    config_manager = ConfigManager()
    
    # 创建iTick数据提供者
    provider = ItickDataProvider(config_manager)
    
    # 测试股票
    test_symbols = ['AAPL', 'MSFT']
    
    # 计算日期范围（最近10天）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=10)
    
    print(f"查询日期范围: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    for symbol in test_symbols:
        print(f"\n--- 测试股票: {symbol} ---")
        
        try:
            # 获取历史K线数据
            klines = provider.get_historical_klines(
                symbol=symbol,
                timeframe="1d",
                start_date=start_date,
                end_date=end_date,
                limit=20
            )
            
            if klines:
                print(f"✅ 成功获取 {len(klines)} 条真实K线数据")
                
                # 显示前3条数据
                for i, kline in enumerate(klines[:3]):
                    print(f"  {i+1}. {kline.timestamp.strftime('%Y-%m-%d')} - "
                          f"开:{kline.open:.2f} 高:{kline.high:.2f} "
                          f"低:{kline.low:.2f} 收:{kline.close:.2f} "
                          f"量:{kline.volume:,}")
                
                if len(klines) > 3:
                    print(f"  ... 还有 {len(klines)-3} 条数据")
                    
            else:
                print("❌ 未获取到任何数据")
                
        except Exception as e:
            print(f"❌ 获取数据失败: {e}")

def test_backtest_with_real_data():
    """测试使用真实数据进行回测"""
    print("\n" + "=" * 60)
    print("测试真实数据回测")
    print("=" * 60)
    
    try:
        from main import QuantTradingSystem
        
        # 创建量化交易系统
        system = QuantTradingSystem()
        
        print("正在使用真实iTick数据进行回测...")
        
        # 运行回测 - 现在只会使用真实数据
        result = system.run_backtest(
            symbol="AAPL",
            strategy="MA_Crossover",
            days=10,  # 较少天数以减少API调用
            initial_cash=100000
        )
        
        if result and result.get('status') == 'success':
            print("✅ 真实数据回测成功!")
            print(f"  股票: {result.get('symbol', 'N/A')}")
            print(f"  策略: {result.get('strategy', 'N/A')}")
            print(f"  收益率: {result.get('total_return_pct', 0):.2f}%")
            print(f"  交易次数: {result.get('total_trades', 0)}")
            print(f"  胜率: {result.get('win_rate', 0):.1f}%")
        else:
            print("❌ 回测失败")
            if result:
                print(f"  错误信息: {result.get('error', 'Unknown error')}")
                
    except Exception as e:
        print(f"❌ 回测失败: {e}")

if __name__ == "__main__":
    # 测试真实数据获取
    test_real_itick_data()
    
    # 测试真实数据回测
    test_backtest_with_real_data()