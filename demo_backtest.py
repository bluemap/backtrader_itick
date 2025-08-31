#!/usr/bin/env python3
"""
回测功能演示

展示如何使用回测功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import QuantTradingSystem


def demo_single_stock_backtest():
    """演示单股票回测"""
    print("=" * 60)
    print("演示 1: 单股票回测")
    print("=" * 60)
    
    system = QuantTradingSystem()
    
    # 回测 AAPL 股票，使用均线交叉策略
    print("正在回测 AAPL (均线交叉策略)...")
    result = system.run_backtest(
        symbol="AAPL",
        strategy="MA_Crossover", 
        days=30,
        initial_cash=100000
    )
    
    if result.get('status') == 'success':
        print("✅ 单股票回测完成")
    else:
        print("❌ 单股票回测失败")


def demo_multi_stock_backtest():
    """演示多股票回测"""
    print("\n" + "=" * 60)
    print("演示 2: 多股票回测")
    print("=" * 60)
    
    system = QuantTradingSystem()
    
    # 回测股票池中的所有股票
    print("正在回测股票池中的所有股票...")
    result = system.run_backtest(
        strategy="RSI_Strategy",
        days=30,
        initial_cash=100000
    )
    
    if result.get('status') == 'success':
        print("✅ 多股票回测完成")
        print(f"平均收益率: {result.get('avg_return_pct', 0):.2f}%")
        print(f"盈利股票: {result.get('profitable_count', 0)}/{result.get('symbols_count', 0)}")
    else:
        print("❌ 多股票回测失败")


def demo_strategy_comparison():
    """演示策略对比"""
    print("\n" + "=" * 60)
    print("演示 3: 策略对比")
    print("=" * 60)
    
    system = QuantTradingSystem()
    
    # 对比多个策略在 MSFT 上的表现
    print("正在对比多个策略在 MSFT 上的表现...")
    result = system.run_strategy_comparison(
        symbol="MSFT",
        days=30,
        initial_cash=100000
    )
    
    if result.get('status') == 'success':
        print("✅ 策略对比完成")
        print(f"最佳策略: {result.get('best_strategy', 'N/A')}")
        print(f"最佳收益: {result.get('best_return', 0):.2f}%")
    else:
        print("❌ 策略对比失败")


def demo_quick_backtest():
    """演示快速回测"""
    print("\n" + "=" * 60)
    print("演示 4: 快速回测")
    print("=" * 60)
    
    system = QuantTradingSystem()
    
    # 快速回测 GOOGL
    system.quick_backtest("GOOGL", "BollingerBands")


def main():
    """主函数"""
    print("量化交易回测功能演示")
    print("=" * 60)
    print("注意: 由于使用模拟数据，结果仅供演示参考")
    print()
    
    try:
        # 演示各种回测功能
        demo_single_stock_backtest()
        demo_multi_stock_backtest() 
        demo_strategy_comparison()
        demo_quick_backtest()
        
        print("\n" + "=" * 60)
        print("✅ 所有回测演示完成!")
        print("=" * 60)
        print("\n回测结果和报告已保存到 backtest_results/ 目录")
        print("\n使用方法:")
        print("1. 命令行工具: python backtest_cli.py --help")
        print("2. 在代码中: from main import QuantTradingSystem")
        print("3. 查看结果文件: ls backtest_results/")
        
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()