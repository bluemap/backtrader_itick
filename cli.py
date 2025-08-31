#!/usr/bin/env python3
"""
量化交易系统命令行工具

提供便捷的命令行接口来管理和操作系统
"""

import os
import sys
import json
import click
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import QuantTradingSystem
from src.core.config_manager import config_manager
from src.strategies.strategy_factory import StrategyFactory, STRATEGY_DESCRIPTIONS


@click.group()
@click.option('--config', type=str, help='配置文件路径')
@click.pass_context
def cli(ctx, config):
    """港美股量化交易通知系统命令行工具"""
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config


@cli.command()
@click.pass_context
def status(ctx):
    """查看系统状态"""
    try:
        system = QuantTradingSystem(ctx.obj['config_path'])
        status_info = system.get_system_status()
        
        click.echo("=== 系统状态 ===")
        click.echo(f"运行状态: {'运行中' if status_info.get('is_running') else '未运行'}")
        
        if status_info.get('start_time'):
            click.echo(f"启动时间: {status_info['start_time']}")
            click.echo(f"运行时间: {status_info.get('uptime_seconds', 0):.0f} 秒")
        
        # 股票池信息
        if 'stock_pool' in status_info:
            pool_info = status_info['stock_pool']
            click.echo(f"\n=== 股票池 ===")
            click.echo(f"总股票数: {pool_info.get('total_stocks', 0)}")
            click.echo(f"有效股票数: {pool_info.get('valid_stocks', 0)}")
            click.echo(f"股票列表: {', '.join(pool_info.get('stock_list', [])[:10])}")
        
        # 信号统计
        if 'signals' in status_info:
            signals_info = status_info['signals']
            click.echo(f"\n=== 信号统计 ===")
            click.echo(f"总信号数: {signals_info.get('total_signals', 0)}")
            click.echo(f"买入信号: {signals_info.get('buy_signals', 0)}")
            click.echo(f"卖出信号: {signals_info.get('sell_signals', 0)}")
            click.echo(f"平均置信度: {signals_info.get('avg_confidence', 0):.2%}")
        
        # 通知状态
        if 'notifications' in status_info:
            notif_info = status_info['notifications']
            click.echo(f"\n=== 通知状态 ===")
            click.echo(f"通知功能: {'启用' if notif_info.get('enabled') else '禁用'}")
            click.echo(f"通知方式: {', '.join(notif_info.get('providers', []))}")
            click.echo(f"发送成功: {notif_info.get('send_stats', {}).get('success_count', 0)}")
            click.echo(f"发送失败: {notif_info.get('send_stats', {}).get('failed_count', 0)}")
        
    except Exception as e:
        click.echo(f"获取状态失败: {e}", err=True)


@cli.command()
@click.pass_context
def config(ctx):
    """查看配置信息"""
    try:
        system = QuantTradingSystem(ctx.obj['config_path'])
        
        click.echo("=== 当前配置 ===")
        
        # 策略配置
        strategy_config = system.config_manager.get_strategy_config()
        click.echo(f"策略类型: {strategy_config.type}")
        
        # iTick 配置
        itick_config = system.config_manager.get_itick_config()
        click.echo(f"iTick API: {'已配置' if itick_config.api_key and itick_config.api_key != 'your_itick_api_key_here' else '未配置'}")
        
        # 通知配置
        notification_config = system.config_manager.get_notification_config()
        click.echo(f"通知功能: {'启用' if notification_config.enabled else '禁用'}")
        
        # 股票池
        stock_pool = system.config_manager.get_stock_pool()
        click.echo(f"股票池: {len(stock_pool)} 只股票")
        
        # 风险控制
        risk_config = system.config_manager.get_risk_control_config()
        click.echo(f"默认止损: {risk_config.default_stop_loss:.1%}")
        click.echo(f"默认止盈: {risk_config.default_take_profit:.1%}")
        
    except Exception as e:
        click.echo(f"获取配置失败: {e}", err=True)


@cli.command()
def strategies():
    """列出所有可用策略"""
    click.echo("=== 可用策略 ===")
    
    for name, description in STRATEGY_DESCRIPTIONS.items():
        click.echo(f"\n{name}:")
        click.echo(f"  {description}")
        
        # 显示默认参数
        params = StrategyFactory.get_strategy_params(name)
        if params:
            click.echo("  默认参数:")
            for param_name, param_value in params.items():
                click.echo(f"    {param_name}: {param_value}")


@cli.command()
@click.option('--symbols', type=str, help='股票代码，用逗号分隔')
@click.option('--file', type=str, help='股票池CSV文件路径')
@click.pass_context
def update_pool(ctx, symbols, file):
    """更新股票池"""
    try:
        system = QuantTradingSystem(ctx.obj['config_path'])
        
        if symbols:
            # 从命令行参数更新
            symbol_list = [s.strip().upper() for s in symbols.split(',')]
            success = system.update_stock_pool(symbol_list)
            
            if success:
                click.echo(f"股票池更新成功，添加了 {len(symbol_list)} 只股票")
            else:
                click.echo("股票池更新失败", err=True)
        
        elif file:
            # 从CSV文件更新
            if not os.path.exists(file):
                click.echo(f"文件不存在: {file}", err=True)
                return
            
            results = system.stock_pool_manager.load_from_csv(file)
            success_count = sum(results.values())
            
            click.echo(f"从CSV文件加载股票池完成: 成功 {success_count}/{len(results)}")
        
        else:
            click.echo("请指定 --symbols 或 --file 参数", err=True)
        
    except Exception as e:
        click.echo(f"更新股票池失败: {e}", err=True)


@cli.command()
@click.option('--start-date', type=str, help='开始日期 (YYYY-MM-DD)')
@click.option('--end-date', type=str, help='结束日期 (YYYY-MM-DD)')
@click.option('--initial-cash', type=float, default=100000, help='初始资金')
@click.pass_context
def backtest(ctx, start_date, end_date, initial_cash):
    """运行回测"""
    try:
        system = QuantTradingSystem(ctx.obj['config_path'])
        
        click.echo("开始运行回测...")
        
        results = system.run_backtest(start_date, end_date, initial_cash)
        
        click.echo("\n=== 回测结果 ===")
        click.echo(json.dumps(results, indent=2, ensure_ascii=False))
        
    except Exception as e:
        click.echo(f"回测失败: {e}", err=True)


@cli.command()
@click.pass_context
def test_notifications(ctx):
    """测试通知功能"""
    try:
        system = QuantTradingSystem(ctx.obj['config_path'])
        
        click.echo("测试通知功能...")
        
        test_results = system.notification_manager.test_notifications()
        
        click.echo("\n=== 测试结果 ===")
        for provider, success in test_results.items():
            status = "✅ 成功" if success else "❌ 失败"
            click.echo(f"{provider}: {status}")
        
    except Exception as e:
        click.echo(f"测试通知失败: {e}", err=True)


@cli.command()
@click.option('--lines', type=int, default=50, help='显示行数')
@click.option('--type', type=click.Choice(['main', 'error', 'signals', 'performance']), 
              default='main', help='日志类型')
@click.pass_context
def logs(ctx, lines, type):
    """查看日志"""
    try:
        system = QuantTradingSystem(ctx.obj['config_path'])
        
        log_lines = system.monitoring_system.log_manager.get_recent_logs(type, lines)
        
        click.echo(f"=== 最近 {len(log_lines)} 行 {type} 日志 ===")
        for line in log_lines:
            click.echo(line.rstrip())
        
    except Exception as e:
        click.echo(f"获取日志失败: {e}", err=True)


@cli.command()
@click.pass_context
def run(ctx):
    """启动系统"""
    try:
        system = QuantTradingSystem(ctx.obj['config_path'])
        
        if system.start():
            click.echo("系统启动成功！")
            click.echo("按 Ctrl+C 停止系统")
            
            try:
                while system.is_running:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                click.echo("\n正在停止系统...")
                system.stop()
                click.echo("系统已停止")
        else:
            click.echo("系统启动失败", err=True)
        
    except Exception as e:
        click.echo(f"运行系统失败: {e}", err=True)


@cli.command()
@click.option('--format', type=click.Choice(['csv', 'json']), default='csv', help='导出格式')
@click.option('--symbol', type=str, help='指定股票代码')
@click.option('--output', type=str, help='输出文件路径')
@click.pass_context
def export_signals(ctx, format, symbol, output):
    """导出交易信号"""
    try:
        system = QuantTradingSystem(ctx.obj['config_path'])
        
        if not output:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output = f"signals_{timestamp}.{format}"
        
        if format == 'csv':
            success = system.signal_generator.export_signals_to_csv(output, symbol)
        else:
            success = system.signal_generator.export_signals_to_json(output, symbol)
        
        if success:
            click.echo(f"信号已导出到: {output}")
        else:
            click.echo("信号导出失败", err=True)
        
    except Exception as e:
        click.echo(f"导出信号失败: {e}", err=True)


@cli.command()
@click.pass_context
def dashboard(ctx):
    """显示仪表盘"""
    try:
        system = QuantTradingSystem(ctx.obj['config_path'])
        
        dashboard_data = system.monitoring_system.get_dashboard_data()
        
        click.echo("=== 量化交易系统仪表盘 ===")
        
        # 健康状态
        health = dashboard_data.get('health_status', {})
        status_emoji = {"healthy": "✅", "warning": "⚠️", "critical": "🚨"}.get(health.get('overall_status'), "❓")
        click.echo(f"\n系统健康: {status_emoji} {health.get('overall_status', 'unknown').upper()}")
        
        # 指标摘要
        metrics = dashboard_data.get('metrics_summary', {})
        if 'system' in metrics:
            sys_metrics = metrics['system']
            click.echo(f"\nCPU使用率: {sys_metrics.get('cpu_avg', 0):.1f}% (最高: {sys_metrics.get('cpu_max', 0):.1f}%)")
            click.echo(f"内存使用率: {sys_metrics.get('memory_avg', 0):.1f}% (最高: {sys_metrics.get('memory_max', 0):.1f}%)")
            click.echo(f"磁盘使用率: {sys_metrics.get('latest_disk_usage', 0):.1f}%")
        
        if 'application' in metrics:
            app_metrics = metrics['application']
            click.echo(f"\n信号生成: {app_metrics.get('signals_generated', 0)} 个")
            click.echo(f"通知发送: {app_metrics.get('notifications_sent', 0)} 条")
            click.echo(f"API调用: {app_metrics.get('api_calls_made', 0)} 次")
            click.echo(f"错误数量: {app_metrics.get('errors_count', 0)} 个")
            click.echo(f"运行时间: {app_metrics.get('uptime_hours', 0):.1f} 小时")
        
        # 最近错误
        recent_logs = dashboard_data.get('recent_logs', {})
        if recent_logs.get('errors'):
            click.echo(f"\n=== 最近错误 ===")
            for log_line in recent_logs['errors'][-3:]:  # 只显示最近3条
                click.echo(log_line.strip())
        
    except Exception as e:
        click.echo(f"获取仪表盘数据失败: {e}", err=True)


if __name__ == '__main__':
    cli()