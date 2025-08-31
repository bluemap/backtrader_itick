"""
日志记录和监控模块

提供系统日志记录、性能监控和健康检查功能
"""

import os
import sys
import json
import time
import psutil
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from dataclasses import dataclass, asdict
import queue


@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used: float  # MB
    memory_total: float  # MB
    disk_percent: float
    disk_used: float  # GB
    disk_total: float  # GB
    network_sent: float  # MB
    network_recv: float  # MB
    process_count: int
    thread_count: int


@dataclass
class ApplicationMetrics:
    """应用指标"""
    timestamp: datetime
    signals_generated: int
    notifications_sent: int
    api_calls_made: int
    errors_count: int
    warnings_count: int
    active_strategies: int
    active_symbols: int
    uptime_seconds: float


@dataclass
class HealthStatus:
    """健康状态"""
    timestamp: datetime
    overall_status: str  # healthy, warning, critical
    components: Dict[str, str]  # 组件名 -> 状态
    issues: List[str]  # 问题描述
    recommendations: List[str]  # 建议


class LogManager:
    """日志管理器"""
    
    def __init__(self, config_manager=None):
        """
        初始化日志管理器
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        
        # 默认配置
        self.log_level = logging.INFO
        self.log_dir = "logs"
        self.max_file_size = "10MB"
        self.backup_count = 5
        self.log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # 从配置加载
        self._load_config()
        
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 设置日志记录器
        self._setup_loggers()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("日志管理器初始化完成")
    
    def _load_config(self) -> None:
        """从配置文件加载日志配置"""
        if not self.config_manager:
            return
        
        try:
            logging_config = self.config_manager.get_logging_config()
            
            # 转换日志级别
            level_map = {
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR': logging.ERROR,
                'CRITICAL': logging.CRITICAL
            }
            
            self.log_level = level_map.get(logging_config.level.upper(), logging.INFO)
            self.log_dir = logging_config.log_dir
            self.max_file_size = logging_config.max_file_size
            self.backup_count = logging_config.backup_count
            self.log_format = logging_config.format
            
        except Exception as e:
            print(f"加载日志配置失败: {e}")
    
    def _setup_loggers(self) -> None:
        """设置日志记录器"""
        # 根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # 清除已有的处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 创建格式化器
        formatter = logging.Formatter(self.log_format)
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # 文件处理器 - 主日志
        main_log_file = os.path.join(self.log_dir, "main.log")
        file_handler = RotatingFileHandler(
            main_log_file,
            maxBytes=self._parse_size(self.max_file_size),
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        # 错误日志处理器
        error_log_file = os.path.join(self.log_dir, "error.log")
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=self._parse_size(self.max_file_size),
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)
        
        # 交易信号日志处理器
        signal_log_file = os.path.join(self.log_dir, "signals.log")
        signal_handler = TimedRotatingFileHandler(
            signal_log_file,
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        signal_handler.setLevel(logging.INFO)
        signal_handler.setFormatter(formatter)
        
        # 为信号日志创建专门的记录器
        signal_logger = logging.getLogger('signals')
        signal_logger.addHandler(signal_handler)
        signal_logger.propagate = False  # 防止重复记录
        
        # 性能日志处理器
        performance_log_file = os.path.join(self.log_dir, "performance.log")
        performance_handler = TimedRotatingFileHandler(
            performance_log_file,
            when='H',  # 每小时轮转
            interval=1,
            backupCount=24 * 7,  # 保留一周
            encoding='utf-8'
        )
        performance_handler.setLevel(logging.INFO)
        performance_handler.setFormatter(formatter)
        
        # 为性能日志创建专门的记录器
        performance_logger = logging.getLogger('performance')
        performance_logger.addHandler(performance_handler)
        performance_logger.propagate = False
    
    def _parse_size(self, size_str: str) -> int:
        """解析大小字符串，返回字节数"""
        size_str = size_str.upper()
        
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def log_signal(self, signal_data: Dict[str, Any]) -> None:
        """记录交易信号"""
        signal_logger = logging.getLogger('signals')
        signal_logger.info(json.dumps(signal_data, ensure_ascii=False, default=str))
    
    def log_performance(self, metrics_data: Dict[str, Any]) -> None:
        """记录性能指标"""
        performance_logger = logging.getLogger('performance')
        performance_logger.info(json.dumps(metrics_data, ensure_ascii=False, default=str))
    
    def get_log_files(self) -> List[str]:
        """获取所有日志文件"""
        log_files = []
        if os.path.exists(self.log_dir):
            for file in os.listdir(self.log_dir):
                if file.endswith('.log'):
                    log_files.append(os.path.join(self.log_dir, file))
        return sorted(log_files)
    
    def get_recent_logs(self, log_type: str = "main", lines: int = 100) -> List[str]:
        """
        获取最近的日志
        
        Args:
            log_type: 日志类型 (main, error, signals, performance)
            lines: 行数
            
        Returns:
            List[str]: 日志行
        """
        log_file = os.path.join(self.log_dir, f"{log_type}.log")
        
        if not os.path.exists(log_file):
            return []
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return all_lines[-lines:] if lines > 0 else all_lines
        except Exception as e:
            logging.error(f"读取日志文件失败: {e}")
            return []


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, config_manager=None):
        """
        初始化指标收集器
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # 指标历史
        self.system_metrics: List[SystemMetrics] = []
        self.app_metrics: List[ApplicationMetrics] = []
        
        # 应用计数器
        self.counters = {
            'signals_generated': 0,
            'notifications_sent': 0,
            'api_calls_made': 0,
            'errors_count': 0,
            'warnings_count': 0
        }
        
        # 应用状态
        self.app_state = {
            'active_strategies': 0,
            'active_symbols': 0,
            'start_time': datetime.now()
        }
        
        # 网络基线
        self.network_baseline = self._get_network_stats()
        
        # 收集间隔
        self.collection_interval = 60  # 秒
        
        # 历史数据保留时间
        self.retention_hours = 24
        
        self.logger.info("指标收集器初始化完成")
    
    def _get_network_stats(self) -> Dict[str, float]:
        """获取网络统计基线"""
        try:
            net_io = psutil.net_io_counters()
            return {
                'bytes_sent': net_io.bytes_sent / 1024 / 1024,  # MB
                'bytes_recv': net_io.bytes_recv / 1024 / 1024   # MB
            }
        except:
            return {'bytes_sent': 0, 'bytes_recv': 0}
    
    def collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        try:
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used / 1024 / 1024  # MB
            memory_total = memory.total / 1024 / 1024  # MB
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_used = disk.used / 1024 / 1024 / 1024  # GB
            disk_total = disk.total / 1024 / 1024 / 1024  # GB
            
            # 网络使用情况
            net_io = psutil.net_io_counters()
            network_sent = (net_io.bytes_sent / 1024 / 1024) - self.network_baseline['bytes_sent']
            network_recv = (net_io.bytes_recv / 1024 / 1024) - self.network_baseline['bytes_recv']
            
            # 进程和线程数
            process_count = len(psutil.pids())
            thread_count = threading.active_count()
            
            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used=memory_used,
                memory_total=memory_total,
                disk_percent=disk_percent,
                disk_used=disk_used,
                disk_total=disk_total,
                network_sent=max(0, network_sent),
                network_recv=max(0, network_recv),
                process_count=process_count,
                thread_count=thread_count
            )
            
            # 添加到历史
            self.system_metrics.append(metrics)
            self._cleanup_old_metrics()
            
            return metrics
        
        except Exception as e:
            self.logger.error(f"收集系统指标失败: {e}")
            return None
    
    def collect_app_metrics(self) -> ApplicationMetrics:
        """收集应用指标"""
        try:
            uptime = (datetime.now() - self.app_state['start_time']).total_seconds()
            
            metrics = ApplicationMetrics(
                timestamp=datetime.now(),
                signals_generated=self.counters['signals_generated'],
                notifications_sent=self.counters['notifications_sent'],
                api_calls_made=self.counters['api_calls_made'],
                errors_count=self.counters['errors_count'],
                warnings_count=self.counters['warnings_count'],
                active_strategies=self.app_state['active_strategies'],
                active_symbols=self.app_state['active_symbols'],
                uptime_seconds=uptime
            )
            
            # 添加到历史
            self.app_metrics.append(metrics)
            self._cleanup_old_metrics()
            
            return metrics
        
        except Exception as e:
            self.logger.error(f"收集应用指标失败: {e}")
            return None
    
    def _cleanup_old_metrics(self) -> None:
        """清理过期的指标数据"""
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
        
        self.system_metrics = [m for m in self.system_metrics if m.timestamp > cutoff_time]
        self.app_metrics = [m for m in self.app_metrics if m.timestamp > cutoff_time]
    
    def increment_counter(self, counter_name: str, value: int = 1) -> None:
        """增加计数器"""
        if counter_name in self.counters:
            self.counters[counter_name] += value
    
    def set_app_state(self, key: str, value: Any) -> None:
        """设置应用状态"""
        if key in self.app_state:
            self.app_state[key] = value
    
    def get_latest_metrics(self) -> Dict[str, Any]:
        """获取最新指标"""
        latest_system = self.system_metrics[-1] if self.system_metrics else None
        latest_app = self.app_metrics[-1] if self.app_metrics else None
        
        return {
            'system': asdict(latest_system) if latest_system else None,
            'application': asdict(latest_app) if latest_app else None,
            'collection_time': datetime.now().isoformat()
        }
    
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """
        获取指标摘要
        
        Args:
            hours: 统计时间范围（小时）
            
        Returns:
            Dict[str, Any]: 指标摘要
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # 过滤指标
        recent_system = [m for m in self.system_metrics if m.timestamp > cutoff_time]
        recent_app = [m for m in self.app_metrics if m.timestamp > cutoff_time]
        
        summary = {
            'time_range_hours': hours,
            'system_metrics_count': len(recent_system),
            'app_metrics_count': len(recent_app)
        }
        
        # 系统指标摘要
        if recent_system:
            cpu_values = [m.cpu_percent for m in recent_system]
            memory_values = [m.memory_percent for m in recent_system]
            
            summary['system'] = {
                'cpu_avg': sum(cpu_values) / len(cpu_values),
                'cpu_max': max(cpu_values),
                'memory_avg': sum(memory_values) / len(memory_values),
                'memory_max': max(memory_values),
                'latest_disk_usage': recent_system[-1].disk_percent
            }
        
        # 应用指标摘要
        if recent_app:
            latest_app = recent_app[-1]
            oldest_app = recent_app[0]
            
            summary['application'] = {
                'signals_generated': latest_app.signals_generated - oldest_app.signals_generated,
                'notifications_sent': latest_app.notifications_sent - oldest_app.notifications_sent,
                'api_calls_made': latest_app.api_calls_made - oldest_app.api_calls_made,
                'errors_count': latest_app.errors_count - oldest_app.errors_count,
                'active_strategies': latest_app.active_strategies,
                'active_symbols': latest_app.active_symbols,
                'uptime_hours': latest_app.uptime_seconds / 3600
            }
        
        return summary


class HealthChecker:
    """健康检查器"""
    
    def __init__(self, config_manager=None, metrics_collector=None):
        """
        初始化健康检查器
        
        Args:
            config_manager: 配置管理器
            metrics_collector: 指标收集器
        """
        self.config_manager = config_manager
        self.metrics_collector = metrics_collector
        self.logger = logging.getLogger(__name__)
        
        # 健康检查阈值
        self.thresholds = {
            'cpu_warning': 70,
            'cpu_critical': 90,
            'memory_warning': 80,
            'memory_critical': 95,
            'disk_warning': 80,
            'disk_critical': 95,
            'error_rate_warning': 10,  # 每小时错误数
            'error_rate_critical': 50
        }
        
        # 组件检查器
        self.component_checkers: Dict[str, Callable[[], str]] = {}
        
        # 注册默认检查器
        self._register_default_checkers()
        
        self.logger.info("健康检查器初始化完成")
    
    def _register_default_checkers(self) -> None:
        """注册默认的组件检查器"""
        self.component_checkers['system_resources'] = self._check_system_resources
        self.component_checkers['application_metrics'] = self._check_application_metrics
        self.component_checkers['log_files'] = self._check_log_files
    
    def register_component_checker(self, name: str, checker: Callable[[], str]) -> None:
        """
        注册组件检查器
        
        Args:
            name: 组件名称
            checker: 检查函数，返回状态字符串 (healthy/warning/critical)
        """
        self.component_checkers[name] = checker
        self.logger.info(f"注册组件检查器: {name}")
    
    def check_health(self) -> HealthStatus:
        """执行完整的健康检查"""
        timestamp = datetime.now()
        components = {}
        issues = []
        recommendations = []
        
        # 检查所有组件
        for component_name, checker in self.component_checkers.items():
            try:
                status = checker()
                components[component_name] = status
                
                if status == 'warning':
                    issues.append(f"{component_name} 组件状态警告")
                elif status == 'critical':
                    issues.append(f"{component_name} 组件状态严重")
            
            except Exception as e:
                self.logger.error(f"组件 {component_name} 健康检查失败: {e}")
                components[component_name] = 'critical'
                issues.append(f"{component_name} 组件检查失败: {str(e)}")
        
        # 确定整体状态
        if any(status == 'critical' for status in components.values()):
            overall_status = 'critical'
        elif any(status == 'warning' for status in components.values()):
            overall_status = 'warning'
        else:
            overall_status = 'healthy'
        
        # 生成建议
        if overall_status != 'healthy':
            recommendations = self._generate_recommendations(components, issues)
        
        return HealthStatus(
            timestamp=timestamp,
            overall_status=overall_status,
            components=components,
            issues=issues,
            recommendations=recommendations
        )
    
    def _check_system_resources(self) -> str:
        """检查系统资源"""
        if not self.metrics_collector or not self.metrics_collector.system_metrics:
            return 'warning'
        
        latest_metrics = self.metrics_collector.system_metrics[-1]
        
        # 检查 CPU
        if latest_metrics.cpu_percent > self.thresholds['cpu_critical']:
            return 'critical'
        elif latest_metrics.cpu_percent > self.thresholds['cpu_warning']:
            return 'warning'
        
        # 检查内存
        if latest_metrics.memory_percent > self.thresholds['memory_critical']:
            return 'critical'
        elif latest_metrics.memory_percent > self.thresholds['memory_warning']:
            return 'warning'
        
        # 检查磁盘
        if latest_metrics.disk_percent > self.thresholds['disk_critical']:
            return 'critical'
        elif latest_metrics.disk_percent > self.thresholds['disk_warning']:
            return 'warning'
        
        return 'healthy'
    
    def _check_application_metrics(self) -> str:
        """检查应用指标"""
        if not self.metrics_collector:
            return 'warning'
        
        # 检查错误率
        summary = self.metrics_collector.get_metrics_summary(hours=1)
        
        if 'application' in summary:
            errors_per_hour = summary['application'].get('errors_count', 0)
            
            if errors_per_hour > self.thresholds['error_rate_critical']:
                return 'critical'
            elif errors_per_hour > self.thresholds['error_rate_warning']:
                return 'warning'
        
        return 'healthy'
    
    def _check_log_files(self) -> str:
        """检查日志文件"""
        try:
            log_dir = "logs"
            if not os.path.exists(log_dir):
                return 'warning'
            
            # 检查日志文件大小
            for file in os.listdir(log_dir):
                if file.endswith('.log'):
                    file_path = os.path.join(log_dir, file)
                    file_size = os.path.getsize(file_path)
                    
                    # 如果单个日志文件超过 100MB，可能有问题
                    if file_size > 100 * 1024 * 1024:
                        return 'warning'
            
            return 'healthy'
        
        except Exception:
            return 'critical'
    
    def _generate_recommendations(self, components: Dict[str, str], issues: List[str]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if 'system_resources' in components and components['system_resources'] != 'healthy':
            recommendations.append("建议监控系统资源使用情况，考虑优化或扩容")
        
        if 'application_metrics' in components and components['application_metrics'] != 'healthy':
            recommendations.append("建议检查应用错误日志，修复潜在问题")
        
        if 'log_files' in components and components['log_files'] != 'healthy':
            recommendations.append("建议检查日志配置，清理或归档大文件")
        
        return recommendations


class MonitoringSystem:
    """监控系统"""
    
    def __init__(self, config_manager=None):
        """
        初始化监控系统
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.log_manager = LogManager(config_manager)
        self.metrics_collector = MetricsCollector(config_manager)
        self.health_checker = HealthChecker(config_manager, self.metrics_collector)
        
        # 监控线程
        self.monitor_thread = None
        self.is_running = False
        
        # 监控间隔
        self.metrics_interval = 60  # 秒
        self.health_check_interval = 300  # 秒
        
        # 回调函数
        self.health_callbacks: List[Callable[[HealthStatus], None]] = []
        
        self.logger.info("监控系统初始化完成")
    
    def start(self) -> None:
        """启动监控系统"""
        if self.is_running:
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("监控系统已启动")
    
    def stop(self) -> None:
        """停止监控系统"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        self.logger.info("监控系统已停止")
    
    def _monitor_loop(self) -> None:
        """监控循环"""
        last_metrics_time = datetime.now()
        last_health_check_time = datetime.now()
        
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # 收集指标
                if (current_time - last_metrics_time).total_seconds() >= self.metrics_interval:
                    system_metrics = self.metrics_collector.collect_system_metrics()
                    app_metrics = self.metrics_collector.collect_app_metrics()
                    
                    # 记录性能日志
                    if system_metrics:
                        self.log_manager.log_performance({
                            'type': 'system_metrics',
                            'data': asdict(system_metrics)
                        })
                    
                    if app_metrics:
                        self.log_manager.log_performance({
                            'type': 'app_metrics',
                            'data': asdict(app_metrics)
                        })
                    
                    last_metrics_time = current_time
                
                # 健康检查
                if (current_time - last_health_check_time).total_seconds() >= self.health_check_interval:
                    health_status = self.health_checker.check_health()
                    
                    # 记录健康状态
                    self.log_manager.log_performance({
                        'type': 'health_status',
                        'data': asdict(health_status)
                    })
                    
                    # 调用健康状态回调
                    for callback in self.health_callbacks:
                        try:
                            callback(health_status)
                        except Exception as e:
                            self.logger.error(f"健康状态回调执行失败: {e}")
                    
                    last_health_check_time = current_time
                
                time.sleep(10)  # 主循环间隔
            
            except Exception as e:
                self.logger.error(f"监控循环异常: {e}")
                time.sleep(30)  # 出错后等待更长时间
    
    def add_health_callback(self, callback: Callable[[HealthStatus], None]) -> None:
        """添加健康状态回调"""
        self.health_callbacks.append(callback)
    
    def get_current_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        health_status = self.health_checker.check_health()
        latest_metrics = self.metrics_collector.get_latest_metrics()
        
        return {
            'health': asdict(health_status),
            'metrics': latest_metrics,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表盘数据"""
        return {
            'health_status': asdict(self.health_checker.check_health()),
            'metrics_summary': self.metrics_collector.get_metrics_summary(hours=1),
            'recent_logs': {
                'errors': self.log_manager.get_recent_logs('error', 10),
                'signals': self.log_manager.get_recent_logs('signals', 10)
            },
            'system_info': {
                'python_version': sys.version,
                'platform': sys.platform,
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024
            }
        }