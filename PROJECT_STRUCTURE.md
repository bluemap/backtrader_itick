# 项目结构

```
backtrader_itick/
├── README.md                           # 项目说明文档
├── requirements.txt                    # Python依赖包
├── setup.py                           # 安装配置文件
├── Makefile                           # 构建和管理脚本
├── .gitignore                         # Git忽略文件
├── install.sh                         # 自动安装脚本（Linux/macOS）
├── install.py                         # 自动安装脚本（跨平台Python）
├── main.py                            # 主应用程序入口
├── cli.py                             # 命令行工具
│
├── config/                            # 配置文件目录
│   └── config.yaml                    # 主配置文件模板
│
├── src/                               # 源代码目录
│   ├── __init__.py
│   ├── core/                          # 核心模块
│   │   ├── __init__.py
│   │   ├── config_manager.py          # 配置管理
│   │   ├── stock_pool_manager.py      # 股票池管理
│   │   └── signal_generator.py        # 信号生成
│   │
│   ├── data/                          # 数据模块
│   │   ├── __init__.py
│   │   └── itick_provider.py          # iTick数据提供者
│   │
│   ├── strategies/                    # 策略模块
│   │   ├── __init__.py
│   │   ├── base_strategy.py           # 策略基类
│   │   ├── strategy_factory.py        # 策略工厂
│   │   ├── ma_crossover_strategies.py # 均线策略
│   │   ├── rsi_strategies.py          # RSI策略
│   │   ├── bollinger_strategies.py    # 布林带策略
│   │   ├── breakout_strategies.py     # 突破策略
│   │   └── momentum_strategies.py     # 动量策略
│   │
│   ├── notifications/                 # 通知模块
│   │   ├── __init__.py
│   │   └── notification_manager.py    # 通知管理器
│   │
│   └── utils/                         # 工具模块
│       ├── __init__.py
│       └── monitoring.py              # 监控系统
│
├── data/                              # 数据目录
│   ├── sample_stock_pool.csv          # 示例股票池
│   └── historical/                    # 历史数据存储
│
├── logs/                              # 日志目录
│   ├── main.log                       # 主日志
│   ├── error.log                      # 错误日志
│   ├── signals.log                    # 信号日志
│   └── performance.log                # 性能日志
│
├── tests/                             # 测试目录
│   ├── __init__.py
│   ├── test_config.py                 # 配置测试
│   ├── test_strategies.py             # 策略测试
│   └── test_notifications.py          # 通知测试
│
└── docs/                              # 文档目录
    ├── quick_start.md                 # 快速入门
    ├── configuration.md               # 配置指南
    ├── strategies.md                  # 策略指南
    ├── api.md                         # API文档
    ├── development.md                 # 开发指南
    ├── faq.md                         # 常见问题
    └── contributing.md                # 贡献指南
```

## 核心模块说明

### 1. 配置管理 (`src/core/config_manager.py`)
- 统一的YAML配置文件管理
- 配置验证和热重载
- 环境变量支持

### 2. 股票池管理 (`src/core/stock_pool_manager.py`)
- 支持手动输入和CSV文件导入
- 股票代码验证和规范化
- 市场分类和过滤

### 3. 数据模块 (`src/data/itick_provider.py`)
- iTick实时行情接入
- WebSocket连接管理
- 历史数据存储和回放

### 4. 策略引擎 (`src/strategies/`)
- 基于Backtrader的策略框架
- 15+种内置策略模板
- 策略工厂和参数管理

### 5. 信号生成 (`src/core/signal_generator.py`)
- 智能信号过滤和验证
- 风险控制和仓位管理
- 信号历史记录和导出

### 6. 通知系统 (`src/notifications/notification_manager.py`)
- 多渠道消息推送（飞书、微信）
- 批量和实时通知模式
- 通知模板自定义

### 7. 监控系统 (`src/utils/monitoring.py`)
- 系统性能监控
- 健康检查和告警
- 日志管理和分析

## 文件说明

### 主要文件

| 文件 | 说明 |
|------|------|
| `main.py` | 主应用程序，整合所有模块 |
| `cli.py` | 命令行工具，提供管理界面 |
| `install.sh` | Shell自动安装脚本（Linux/macOS） |
| `install.py` | Python自动安装脚本（跨平台） |
| `config/config.yaml` | 主配置文件模板 |
| `requirements.txt` | Python依赖包列表 |
| `setup.py` | 项目安装配置 |

### 配置文件

| 文件 | 说明 |
|------|------|
| `config/config.yaml` | 默认配置模板 |
| `config/config_local.yaml` | 本地配置（用户创建） |
| `config/config_prod.yaml` | 生产环境配置（可选） |

### 数据文件

| 文件/目录 | 说明 |
|-----------|------|
| `data/sample_stock_pool.csv` | 示例股票池文件 |
| `data/historical/` | 历史数据存储目录 |
| `logs/` | 系统日志目录 |

### 文档文件

| 文件 | 说明 |
|------|------|
| `README.md` | 项目主文档 |
| `docs/quick_start.md` | 快速入门指南 |
| `docs/configuration.md` | 详细配置说明 |
| `docs/faq.md` | 常见问题解答 |

## 设计特点

### 1. 模块化设计
- 每个功能独立成模块
- 松耦合，易于扩展
- 支持插件化开发

### 2. 配置驱动
- 所有参数通过配置文件管理
- 支持多环境配置
- 配置验证和错误提示

### 3. 异步处理
- WebSocket异步数据接收
- 多线程信号处理
- 非阻塞通知发送

### 4. 监控完善
- 全面的日志记录
- 性能指标监控
- 健康状态检查

### 5. 易于部署
- 单机部署，无外部依赖
- Docker支持（可扩展）
- 命令行工具管理

## 扩展点

### 1. 新增策略
在 `src/strategies/` 目录下添加新的策略文件，并在策略工厂中注册。

### 2. 新增通知方式
在 `src/notifications/` 目录下添加新的通知提供者。

### 3. 新增数据源
在 `src/data/` 目录下添加新的数据提供者。

### 4. 新增监控指标
在 `src/utils/monitoring.py` 中添加新的监控指标。

## 开发工作流

1. **克隆代码** → **安装依赖** → **配置系统** → **运行测试** → **启动系统**
2. **监控运行** → **查看日志** → **优化配置** → **扩展功能** → **部署上线**

---

这个项目结构支持从简单的个人使用到复杂的生产环境部署，具有良好的可扩展性和可维护性。