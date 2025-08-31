#!/usr/bin/env python3
"""
回测命令行工具

提供简单易用的回测功能
"""

import sys
import argparse
from datetime import datetime
from main import QuantTradingSystem


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="量化交易策略回测工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 单股票回测
  python backtest_cli.py --symbol AAPL --strategy MA_Crossover --days 30
  
  # 多股票回测
  python backtest_cli.py --strategy RSI_Strategy --days 60
  
  # 策略对比
  python backtest_cli.py --symbol MSFT --compare
  
  # 快速回测
  python backtest_cli.py --symbol GOOGL --quick
        """
    )
    
    parser.add_argument('--symbol', '-s', 
                       help='股票代码 (如: AAPL, MSFT)')
    
    parser.add_argument('--strategy', '-st', 
                       choices=['MA_Crossover', 'RSI_Strategy', 'BollingerBands', 'Momentum'],
                       default='MA_Crossover',
                       help='策略名称 (默认: MA_Crossover)')
    
    parser.add_argument('--days', '-d', 
                       type=int, default=30,
                       help='回测天数 (默认: 30)')
    
    parser.add_argument('--cash', '-c', 
                       type=float, default=100000,
                       help='初始资金 (默认: 100000)')
    
    parser.add_argument('--compare', 
                       action='store_true',
                       help='进行策略对比')
    
    parser.add_argument('--quick', '-q',
                       action='store_true', 
                       help='快速回测模式')
    
    args = parser.parse_args()
    
    try:
        # 初始化交易系统
        print("正在初始化量化交易系统...")
        system = QuantTradingSystem()
        
        if args.quick:
            # 快速回测模式
            if not args.symbol:
                print("错误: 快速回测需要指定股票代码")
                return
            
            system.quick_backtest(args.symbol, args.strategy)
        
        elif args.compare:
            # 策略对比模式
            print(f"开始策略对比回测...")
            result = system.run_strategy_comparison(
                symbol=args.symbol,
                days=args.days,
                initial_cash=args.cash
            )
            
            if result['status'] != 'success':
                print(f"策略对比失败: {result.get('message', '未知错误')}")
        
        else:
            # 标准回测模式
            print(f"开始回测...")
            print(f"股票: {args.symbol or '股票池'}")
            print(f"策略: {args.strategy}")
            print(f"天数: {args.days}")
            print(f"初始资金: ¥{args.cash:,.0f}")
            print("-" * 40)
            
            result = system.run_backtest(
                symbol=args.symbol,
                strategy=args.strategy,
                days=args.days,
                initial_cash=args.cash
            )
            
            if result['status'] != 'success':
                print(f"回测失败: {result.get('message', '未知错误')}")
    
    except KeyboardInterrupt:
        print("\n回测被用户中断")
    except Exception as e:
        print(f"回测过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()