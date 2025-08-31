# 港美股量化交易通知系统

基于 iTick 实时行情和 Backtrader 策略引擎的量化交易信号生成和通知系统。

## 🚀 项目特色

- **多策略支持**: 内置 15+ 种经典量化策略，包括均线交叉、RSI、布林带、突破、动量等
- **实时信号**: 基于 iTick 实时行情数据生成交易信号
- **智能通知**: 支持飞书、微信等多种通知方式
- **风险控制**: 内置信号过滤、仓位管理、止损止盈机制
- **系统监控**: 完整的日志记录、性能监控和健康检查
- **易于扩展**: 模块化设计，支持自定义策略和通知方式

## 📋 目录

- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [安装部署](#安装部署)
- [配置说明](#配置说明)
- [使用指南](#使用指南)
- [策略介绍](#策略介绍)
- [API 文档](#api-文档)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)

## 🏗️ 系统架构

```
[iTick 行情 API]  →  [数据预处理模块] → [Backtrader 策略引擎] → [信号生成模块] → [飞书/微信通知] → [用户手动下单]
                                 ↑
                          [用户自定义股票池]
```

### 核心组件

- **配置管理**: 统一的 YAML 配置文件管理
- **股票池管理**: 支持手动输入和 CSV 文件导入
- **数据模块**: iTick 实时行情接入和历史数据存储
- **策略引擎**: 基于 Backtrader 的多策略框架
- **信号生成**: 智能信号过滤和风险控制
- **通知系统**: 多渠道消息推送
- **监控系统**: 完整的日志和性能监控

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-org/backtrader-itick.git
cd backtrader-itick
```

### 2. 安装依赖

```bash
# 方式一：使用自动安装脚本（推荐）
./install.sh          # Linux/macOS
# 或
python3 install.py    # 跨平台

# 方式二：手动安装
pip install -r requirements.txt

# 方式三：使用 make
make install
```

### 3. 配置系统

复制配置文件并编辑：

```bash
cp config/config.yaml config/config_local.yaml
```

编辑 `config/config_local.yaml`，设置您的 iTick API Key 和通知配置。

### 4. 运行系统

```bash
# 直接运行
python main.py

# 或使用命令行工具
python cli.py run

# 或使用 make
make run
```

### 5. 测试通知

```bash
python cli.py test-notifications
```

## 📦 安装部署

### 系统要求

- Python 3.8+
- 内存: 最少 2GB，推荐 4GB+
- 磁盘: 最少 1GB 可用空间
- 网络: 稳定的互联网连接

### 安装方式

#### 方式一：从源码安装

```bash
git clone https://github.com/your-org/backtrader-itick.git
cd backtrader-itick
pip install -r requirements.txt
```

#### 方式二：使用 setup.py

```bash
python setup.py install
```

#### 方式三：开发模式安装

```bash
pip install -e .
```

### Docker 部署 (可选)

```bash
# 构建镜像
docker build -t backtrader-itick .

# 运行容器
docker run -d \
  -v $(PWD)/config:/app/config \
  -v $(PWD)/logs:/app/logs \
  --name quant-trading \
  backtrader-itick
```

## ⚙️ 配置说明

### 主配置文件 (config/config.yaml)

```yaml
# iTick API 配置
itick:
  api_key: "your_itick_api_key_here"  # 必须配置
  base_url: "https://api.itick.com"
  websocket_url: "wss://api.itick.com/ws"

# 股票池配置
stock_pool:
  symbols:
    - AAPL
    - MSFT
    - TSLA
  
# 策略配置
strategy:
  type: "MA_Crossover"  # 策略类型
  ma_crossover:
    short_window: 10
    long_window: 50

# 通知配置
notification:
  enabled: true
  feishu:
    enabled: true
    webhook_url: "your_feishu_webhook_url"
  wechat:
    enabled: false
    webhook_url: "your_wechat_webhook_url"
```

### 配置项详解

详细的配置说明请参考：[配置文档](docs/configuration.md)

## 📖 使用指南

### 命令行工具

系统提供了便捷的命令行工具：

```bash
# 查看系统状态
python cli.py status

# 查看配置信息
python cli.py config

# 列出所有策略
python cli.py strategies

# 更新股票池
python cli.py update-pool --symbols "AAPL,MSFT,GOOGL"

# 运行回测
python cli.py backtest --start-date 2023-01-01 --end-date 2023-12-31

# 查看日志
python cli.py logs --lines 50 --type main

# 导出信号
python cli.py export-signals --format csv --output signals.csv
```

### 程序化接口

```python
from main import QuantTradingSystem

# 创建系统实例
system = QuantTradingSystem("config/config.yaml")

# 启动系统
system.start()

# 获取系统状态
status = system.get_system_status()

# 停止系统
system.stop()
```

## 📊 策略介绍

### 内置策略列表

| 策略名称 | 描述 | 适用场景 |
|---------|------|----------|
| MA_Crossover | 移动平均线交叉策略 | 趋势跟踪 |
| RSI_Strategy | RSI 超买超卖策略 | 震荡市场 |
| BollingerBands | 布林带回归策略 | 均值回归 |
| Breakout | 价格突破策略 | 突破行情 |
| Momentum | 动量策略 | 强势股票 |

### 策略参数调优

每个策略都支持参数调优，例如：

```yaml
strategy:
  type: "MA_Crossover"
  ma_crossover:
    short_window: 5    # 快速均线周期
    long_window: 20    # 慢速均线周期
    stop_loss_pct: 0.05  # 止损百分比
    take_profit_pct: 0.10  # 止盈百分比
```

详细的策略文档请参考：[策略指南](docs/strategies.md)

## 🔧 API 文档

### 核心 API

```python
# 配置管理
from src.core.config_manager import config_manager

# 股票池管理
from src.core.stock_pool_manager import StockPoolManager

# 信号生成
from src.core.signal_generator import SignalGenerator

# 通知管理
from src.notifications.notification_manager import NotificationManager
```

详细的 API 文档请参考：[API 参考](docs/api.md)

## 📈 性能监控

系统内置完整的监控功能：

### 系统指标

- CPU 和内存使用率
- 磁盘空间和网络流量
- 进程和线程数量

### 应用指标

- 信号生成数量和质量
- 通知发送成功率
- API 调用统计
- 错误和警告数量

### 健康检查

- 实时健康状态监控
- 自动问题检测
- 改进建议生成

### 查看监控数据

```bash
# 查看仪表盘
python cli.py dashboard

# 查看详细状态
python cli.py status
```

## 🛠️ 开发指南

### 开发环境设置

```bash
# 克隆代码
git clone https://github.com/your-org/backtrader-itick.git
cd backtrader-itick

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装开发依赖
make install-dev
```

### 代码规范

```bash
# 代码格式化
make format

# 代码检查
make lint

# 运行测试
make test
```

### 自定义策略

创建新策略的步骤：

1. 继承 `BaseStrategy` 类
2. 实现 `next()` 方法
3. 在策略工厂中注册

```python
from src.strategies.base_strategy import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    def next(self):
        # 实现策略逻辑
        if self.should_buy():
            self.emit_signal("BUY", self.get_current_price(), "买入信号")
```

详细的开发指南请参考：[开发文档](docs/development.md)

## 🔒 安全注意事项

- **API 密钥安全**: 不要将 API 密钥提交到版本控制系统
- **网络安全**: 使用 HTTPS 和 WSS 连接
- **访问控制**: 限制系统访问权限
- **日志安全**: 确保敏感信息不被记录到日志中

## ❓ 常见问题

### Q: 如何获取 iTick API Key？
A: 请访问 [iTick 官网](https://www.itick.com) 注册账户并申请 API 密钥。

### Q: 系统支持哪些股票市场？
A: 目前支持美股（NYSE、NASDAQ）和港股（HKEX），具体以 iTick 支持的市场为准。

### Q: 可以同时运行多个策略吗？
A: 当前版本每次只能运行一个策略，多策略支持在计划中。

### Q: 如何自定义通知模板？
A: 可以修改 `src/notifications/notification_manager.py` 中的消息模板。

### Q: 系统是否会自动下单？
A: 不会。系统只生成交易信号并发送通知，需要用户手动在券商平台下单。

更多问题请查看：[FAQ 文档](docs/faq.md)

## 🤝 贡献指南

我们欢迎社区贡献！请参考：[贡献指南](docs/contributing.md)

### 贡献方式

- 🐛 报告 Bug
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码修复
- 📊 贡献新策略

### 开发流程

1. Fork 项目
2. 创建功能分支
3. 提交代码
4. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。详情请见 [LICENSE](LICENSE) 文件。

## 📞 联系我们

- 📧 邮箱: quant@example.com
- 💬 微信群: [加入微信群]
- 🐛 问题反馈: [GitHub Issues](https://github.com/your-org/backtrader-itick/issues)

## 🙏 致谢

感谢以下开源项目：

- [Backtrader](https://www.backtrader.com/) - 强大的量化交易框架
- [pandas](https://pandas.pydata.org/) - 数据分析库
- [requests](https://requests.readthedocs.io/) - HTTP 客户端库

## ⚠️ 免责声明

本系统仅供学习和研究使用。投资有风险，使用本系统进行实际交易的风险由用户自行承担。作者不对任何投资损失负责。

---

⭐ 如果这个项目对您有帮助，请给我们一个 Star！