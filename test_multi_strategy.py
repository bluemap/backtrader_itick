#!/usr/bin/env python3
"""
多策略量化交易系统测试

测试多策略并行运行的所有功能组件
"""

import sys
import os
import time
import logging
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_multi_strategy_config():
    """测试多策略配置加载"""
    print("=" * 60)
    print("📋 多策略配置测试")
    print("=" * 60)
    
    try:
        from src.core.config_manager import ConfigManager
        
        # 使用多策略配置文件
        config_manager = ConfigManager("config/multi_strategy_config.yaml")
        
        # 检查是否为多策略模式
        is_multi_mode = config_manager.is_multi_strategy_mode()
        print(f"多策略模式: {'✅' if is_multi_mode else '❌'}")
        
        if is_multi_mode:
            # 获取策略配置
            strategies = config_manager.get_multi_strategies_config()
            print(f"配置的策略数量: {len(strategies)}")
            
            for strategy in strategies:
                print(f"  - {strategy.name} ({strategy.type}) {'启用' if strategy.enabled else '禁用'}")
                print(f"    股票池: {strategy.stock_pool.get('symbols', []) if strategy.stock_pool else '使用全局'}")
                print(f"    资金分配: {strategy.capital_allocation}")
            
            # 获取策略管理配置
            management = config_manager.get_strategy_management_config()
            print(f"总资金: ${management.total_capital:,}")
            print(f"执行模式: {management.execution_mode}")
            print(f"冲突解决: {management.conflict_resolution}")
        
        # 验证配置
        valid = config_manager.validate_config()
        print(f"配置验证: {'✅ 通过' if valid else '❌ 失败'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_strategy_manager():
    """测试策略管理器"""
    print("\n" + "=" * 60)
    print("🎯 策略管理器测试")
    print("=" * 60)
    
    try:
        from src.core.config_manager import ConfigManager
        from src.core.strategy_manager import StrategyManager
        from src.data.itick_provider import ItickDataProvider
        
        # 加载配置
        config_manager = ConfigManager("config/multi_strategy_config.yaml")
        
        # 创建数据提供者（测试模式）
        config_manager.config_data['itick']['simulation_mode'] = True
        data_provider = ItickDataProvider(config_manager)
        
        # 创建策略管理器
        strategy_manager = StrategyManager(config_manager, data_provider)
        
        print(f"加载的策略实例数: {len(strategy_manager.strategy_instances)}")
        
        # 显示策略信息
        for name, strategy in strategy_manager.strategy_instances.items():
            print(f"  策略: {name}")
            print(f"    类型: {strategy.strategy_type}")
            print(f"    股票: {strategy.stock_symbols}")
            print(f"    资金: ${strategy_manager.allocated_capital.get(name, 0):,.2f}")
            print(f"    状态: {'启用' if strategy.enabled else '禁用'}")
        
        # 测试资金分配验证
        total_allocated = sum(strategy_manager.allocated_capital.values())
        print(f"总分配资金: ${total_allocated:,.2f}")
        print(f"剩余资金: ${strategy_manager.available_capital:,.2f}")
        
        # 获取全局统计
        stats = strategy_manager.get_global_statistics()
        print(f"活跃策略数: {stats['active_strategies']}")
        print(f"总策略数: {stats['total_strategies']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 策略管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multi_strategy_backtest():
    """测试多策略回测"""
    print("\n" + "=" * 60)
    print("📈 多策略回测测试")
    print("=" * 60)
    
    try:
        from src.core.config_manager import ConfigManager
        from src.data.itick_provider import ItickDataProvider  
        from src.backtesting.multi_strategy_backtest import MultiStrategyBacktest
        
        # 加载配置
        config_manager = ConfigManager("config/multi_strategy_config.yaml")
        
        # 创建数据提供者
        data_provider = ItickDataProvider(config_manager)
        
        # 创建多策略回测管理器
        backtest_manager = MultiStrategyBacktest(config_manager, data_provider)
        
        print("开始多策略回测测试（5天数据）...")
        
        # 运行回测
        result = backtest_manager.run_multi_strategy_backtest(
            days=5,
            initial_cash=100000,
            parallel=False,  # 顺序执行便于观察
            save_results=True
        )
        
        if result.get('status') == 'success':
            print("✅ 多策略回测成功！")
            
            # 显示整体表现
            performance = result.get('overall_performance', {})
            print(f"总资金: ${performance.get('total_allocated_capital', 0):,.2f}")
            print(f"加权平均收益: {performance.get('weighted_average_return_pct', 0):.2f}%")
            print(f"总交易数: {performance.get('total_trades', 0)}")
            print(f"整体胜率: {performance.get('overall_win_rate', 0):.1f}%")
            
            # 显示策略排名
            ranking = result.get('strategy_ranking', [])
            print("\n🏆 策略排名:")
            for rank_info in ranking:
                print(f"  {rank_info['rank']}. {rank_info['strategy_name']} "
                      f"({rank_info['strategy_type']}) - "
                      f"收益: {rank_info['return_pct']:.2f}%, "
                      f"胜率: {rank_info['win_rate']:.1f}%")
            
            # 显示建议
            recommendations = result.get('recommendations', [])
            print("\n💡 投资建议:")
            for rec in recommendations:
                print(f"  {rec}")
            
        else:
            print(f"❌ 多策略回测失败: {result.get('error')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 多策略回测测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multi_strategy_system():
    """测试完整的多策略系统"""
    print("\n" + "=" * 60)
    print("🚀 多策略系统集成测试")
    print("=" * 60)
    
    try:
        from main_multi_strategy import MultiStrategyQuantTradingSystem
        
        # 创建系统实例
        system = MultiStrategyQuantTradingSystem("config/multi_strategy_config.yaml")
        
        print("系统初始化:", "✅ 成功" if system._initialize_system() else "❌ 失败")
        print(f"运行模式: {'多策略' if system.is_multi_strategy_mode else '单策略'}")
        
        if system.is_multi_strategy_mode:
            # 获取系统状态
            status = system.get_system_status()
            print(f"系统状态: {status}")
            
            # 测试启动（不实际启动，避免长时间运行）
            print("准备启动测试...")
            
            # 检查策略管理器
            if system.strategy_manager:
                print(f"策略管理器: ✅ 已初始化")
                print(f"配置的策略数: {len(system.strategy_manager.strategy_instances)}")
                
                # 显示策略信息
                for name, strategy in system.strategy_manager.strategy_instances.items():
                    print(f"  - {name}: {strategy.strategy_type} ({len(strategy.stock_symbols)} 股票)")
            
            # 测试多策略回测
            print("\n测试多策略回测功能...")
            backtest_result = system.run_backtest(days=3)
            
            if backtest_result.get('status') == 'success':
                print("✅ 多策略回测成功")
                results = backtest_result.get('results', {})
                print(f"回测策略数: {len(results)}")
                
                for strategy_name, strategy_results in results.items():
                    print(f"  {strategy_name}: {len(strategy_results)} 只股票回测完成")
            else:
                print(f"❌ 多策略回测失败: {backtest_result.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 多策略系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_signal_conflict_resolution():
    """测试信号冲突解决"""
    print("\n" + "=" * 60)
    print("⚔️ 信号冲突解决测试")
    print("=" * 60)
    
    try:
        from src.core.strategy_manager import StrategyManager, SignalConflict
        from src.strategies.base_strategy import TradeSignal
        from src.core.config_manager import ConfigManager
        from src.data.itick_provider import ItickDataProvider
        from datetime import datetime
        
        # 加载配置
        config_manager = ConfigManager("config/multi_strategy_config.yaml")
        data_provider = ItickDataProvider(config_manager)
        
        # 创建策略管理器
        strategy_manager = StrategyManager(config_manager, data_provider)
        
        # 创建模拟信号冲突 - 确保所有必需参数都有值
        now = datetime.now()
        
        signal1 = TradeSignal(
            symbol="AAPL",
            timestamp=now,
            action="BUY",
            price=150.0,
            confidence=0.8,
            reason="布林带下轨反弹",
            strategy_name="bollinger_aapl_msft"
        )
        
        signal2 = TradeSignal(
            symbol="AAPL",
            timestamp=now,
            action="BUY", 
            price=150.5,
            confidence=0.6,
            reason="RSI超卖反弹",
            strategy_name="rsi_tech_stocks"
        )
        
        signal3 = TradeSignal(
            symbol="AAPL",
            timestamp=now,
            action="SELL",
            price=149.8,
            confidence=0.7,
            reason="MACD死叉",
            strategy_name="macd_momentum"
        )
        
        # 创建冲突
        conflict = SignalConflict(
            symbol="AAPL",
            signals=[signal1, signal2, signal3],
            resolution=""
        )
        
        print(f"测试信号冲突: {len(conflict.signals)} 个信号")
        for i, signal in enumerate(conflict.signals):
            print(f"  信号{i+1}: {signal.action} @{signal.price} ({signal.strategy_name}, 置信度:{signal.confidence})")
        
        # 测试不同的冲突解决策略
        resolution_modes = ['highest_confidence', 'first_wins', 'combine_signals']
        
        for mode in resolution_modes:
            print(f"\n测试解决模式: {mode}")
            
            # 设置解决模式
            original_mode = config_manager.get_config('strategy_management.conflict_resolution.mode')
            config_manager.update_config('strategy_management.conflict_resolution.mode', mode)
            
            try:
                resolved_signal = strategy_manager._resolve_signal_conflict(conflict)
                
                if resolved_signal:
                    print(f"  ✅ 解决结果: {resolved_signal.action} @{resolved_signal.price:.2f} "
                          f"(策略: {resolved_signal.strategy_name}, 置信度: {resolved_signal.confidence:.2f})")
                else:
                    print("  ❌ 解决失败")
                    
            finally:
                # 恢复原设置
                if original_mode:
                    config_manager.update_config('strategy_management.conflict_resolution.mode', original_mode)
        
        return True
        
    except Exception as e:
        print(f"❌ 信号冲突解决测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance_monitoring():
    """测试性能监控"""
    print("\n" + "=" * 60)
    print("📊 性能监控测试")
    print("=" * 60)
    
    try:
        from src.core.config_manager import ConfigManager
        from src.core.strategy_manager import StrategyManager
        from src.data.itick_provider import ItickDataProvider
        
        # 加载配置
        config_manager = ConfigManager("config/multi_strategy_config.yaml")
        data_provider = ItickDataProvider(config_manager)
        
        # 创建策略管理器
        strategy_manager = StrategyManager(config_manager, data_provider)
        
        # 获取性能统计
        performance = strategy_manager.get_strategy_performance()
        print(f"监控的策略数: {len(performance)}")
        
        for strategy_name, stats in performance.items():
            print(f"\n策略: {strategy_name}")
            print(f"  总信号数: {stats.get('total_signals', 0)}")
            print(f"  买入信号: {stats.get('buy_signals', 0)}")
            print(f"  卖出信号: {stats.get('sell_signals', 0)}")
            print(f"  平均置信度: {stats.get('avg_confidence', 0):.2f}")
            print(f"  最后信号时间: {stats.get('last_signal_time', 'None')}")
        
        # 获取全局统计
        global_stats = strategy_manager.get_global_statistics()
        print(f"\n全局统计:")
        print(f"  总策略数: {global_stats.get('total_strategies', 0)}")
        print(f"  活跃策略数: {global_stats.get('active_strategies', 0)}")
        print(f"  总资金: ${global_stats.get('total_capital', 0):,.2f}")
        print(f"  已分配资金: ${global_stats.get('allocated_capital', 0):,.2f}")
        print(f"  剩余资金: ${global_stats.get('available_capital', 0):,.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 性能监控测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🎯 多策略量化交易系统全面测试")
    print("=" * 60)
    
    test_results = []
    
    # 执行所有测试
    tests = [
        ("多策略配置加载", test_multi_strategy_config),
        ("策略管理器", test_strategy_manager),
        ("多策略回测", test_multi_strategy_backtest),
        ("多策略系统集成", test_multi_strategy_system),
        ("信号冲突解决", test_signal_conflict_resolution),
        ("性能监控", test_performance_monitoring)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔄 正在执行: {test_name}")
            result = test_func()
            test_results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name} 测试通过")
            else:
                print(f"❌ {test_name} 测试失败")
                
        except Exception as e:
            print(f"❌ {test_name} 执行异常: {e}")
            test_results.append((test_name, False))
        
        # 测试间间隔
        time.sleep(1)
    
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
    pass_rate = (passed / total) * 100
    print(f"通过率: {pass_rate:.1f}%")
    
    if passed == total:
        print("\n🎉 所有多策略测试均通过！系统可以投入使用。")
    elif pass_rate >= 80:
        print("\n⚠️ 大部分测试通过，系统基本可用，建议修复失败的测试。")
    else:
        print("\n❌ 测试通过率偏低，建议解决问题后重新测试。")
    
    print("\n" + "=" * 60)
    print("🚀 多策略系统使用指南")
    print("=" * 60)
    print("1. 使用多策略配置文件: config/multi_strategy_config.yaml")
    print("2. 运行多策略系统: python main_multi_strategy.py")
    print("3. 单独测试回测: python -c \"from src.backtesting.multi_strategy_backtest import *; test_backtest()\"")
    print("4. 查看回测结果: backtest_results/multi_strategy_backtest_*.json")
    print("5. 监控日志文件: logs/")

if __name__ == "__main__":
    main()