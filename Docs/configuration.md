# 配置指南

本文档详细介绍了系统的所有配置选项。

## 📁 配置文件结构

```
config/
├── config.yaml              # 默认配置模板
├── config_local.yaml        # 本地配置（您的实际配置）
└── config_production.yaml   # 生产环境配置（可选）
```

## 🔧 主要配置项

### iTick API 配置

```yaml
itick:
  api_key: "your_itick_api_key_here"    # 必须：您的 iTick API 密钥
  base_url: "https://api.itick.com"     # 可选：API 基础 URL
  websocket_url: "wss://api.itick.com/ws"  # 可选：WebSocket URL
  timeout: 30                           # 可选：请求超时时间（秒）
```

**获取 API Key**:
1. 访问 [iTick 官网](https://www.itick.com)
2. 注册账户并登录
3. 在开发者中心申请 API 密钥
4. 将密钥替换配置中的 `your_itick_api_key_here`

### 股票池配置

#### 方式一：直接列表

```yaml
stock_pool:
  symbols:                    # 股票代码列表
    - AAPL                   # 苹果
    - MSFT                   # 微软
    - GOOGL                  # 谷歌
    - AMZN                   # 亚马逊
    - TSLA                   # 特斯拉
  deduplicate: true          # 是否去重
  validate: true             # 是否验证股票有效性
```

#### 方式二：CSV 文件

```yaml
stock_pool:
  csv_file: "data/my_stocks.csv"  # CSV 文件路径
  deduplicate: true
  validate: true
```

CSV 文件格式：
```csv
symbol,name,market
AAPL,Apple Inc.,US
MSFT,Microsoft Corporation,US
0700,Tencent Holdings,HK
```

### 策略配置

#### 主策略设置

```yaml
strategy:
  type: "MA_Crossover"       # 策略类型（必须）
```

#### 支持的策略类型

| 策略类型 | 说明 | 适用场景 |
|---------|------|----------|
| `MA_Crossover` | 移动平均线交叉 | 趋势跟踪 |
| `Adaptive_MA_Crossover` | 自适应均线交叉 | 动态趋势 |
| `Triple_MA_Crossover` | 三重均线交叉 | 强确认信号 |
| `RSI_Strategy` | RSI 超买超卖 | 震荡市场 |
| `RSI_Divergence` | RSI 背离 | 反转信号 |
| `RSI_Bollinger` | RSI+布林带组合 | 综合信号 |
| `BollingerBands` | 布林带回归 | 均值回归 |
| `Bollinger_Breakout` | 布林带突破 | 突破行情 |
| `Breakout` | 价格突破 | 关键位突破 |
| `Donchian_Breakout` | 唐奇安通道突破 | 趋势突破 |
| `Momentum` | 动量策略 | 强势股票 |

#### 策略参数配置

##### 均线交叉策略

```yaml
strategy:
  type: "MA_Crossover"
  ma_crossover:
    short_window: 10         # 短期均线周期
    long_window: 50          # 长期均线周期
    stop_loss_pct: 0.05      # 止损百分比
    take_profit_pct: 0.10    # 止盈百分比
    min_volume: 1000         # 最小成交量过滤
```

##### RSI 策略

```yaml
strategy:
  type: "RSI_Strategy"
  rsi_strategy:
    period: 14               # RSI 计算周期
    oversold: 30             # 超卖阈值
    overbought: 70           # 超买阈值
    ma_filter: true          # 是否启用均线过滤
    ma_period: 50            # 均线周期
```

##### 布林带策略

```yaml
strategy:
  type: "BollingerBands"
  bollinger_bands:
    period: 20               # 布林带周期
    std_dev: 2               # 标准差倍数
    volume_threshold: 1.2    # 成交量阈值倍数
```

##### 突破策略

```yaml
strategy:
  type: "Breakout"
  breakout:
    period: 20               # 突破判断周期
    min_breakout_pct: 0.02   # 最小突破幅度
    volume_factor: 1.5       # 成交量确认倍数
```

##### 动量策略

```yaml
strategy:
  type: "Momentum"
  momentum:
    period: 10               # 动量计算周期
    threshold: 0.02          # 动量阈值
    volume_factor: 1.3       # 成交量确认倍数
```

### 数据配置

```yaml
data:
  historical_dir: "data/historical"  # 历史数据存储目录
  format: "csv"                      # 数据格式：csv, sqlite, parquet
  update_interval: 60                # 数据更新间隔（秒）
  timeframe: "1m"                    # K线周期：1m, 5m, 15m, 30m, 1h, 1d
```

### 通知配置

#### 基础设置

```yaml
notification:
  enabled: true              # 是否启用通知
```

#### 飞书机器人配置

```yaml
notification:
  feishu:
    enabled: true
    webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/your_webhook_token"
```

**获取飞书 Webhook**:
1. 在飞书群中添加机器人
2. 选择"自定义机器人"
3. 配置机器人名称和描述
4. 复制生成的 Webhook URL

#### 微信通知配置

##### 企业微信机器人

```yaml
notification:
  wechat:
    enabled: true
    webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key"
```

##### Server 酱

```yaml
notification:
  wechat:
    enabled: true
    server_chan_key: "your_server_chan_key"
```

#### 通知频率控制

```yaml
notification:
  frequency:
    mode: "immediate"        # 推送模式：immediate, batch
    batch_interval: 5        # 批量推送间隔（分钟）
```

#### 消息模板自定义

```yaml
notification:
  message_template:
    include_stop_loss: true      # 是否包含止损信息
    include_take_profit: true    # 是否包含止盈信息
    include_strategy_name: true  # 是否包含策略名称
```

### 日志配置

```yaml
logging:
  level: "INFO"                    # 日志级别：DEBUG, INFO, WARNING, ERROR
  log_dir: "logs"                  # 日志目录
  max_file_size: "10MB"           # 单个日志文件最大大小
  backup_count: 5                  # 备份文件数量
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### 监控配置

```yaml
monitoring:
  enabled: true                    # 是否启用监控
  max_retries: 3                   # 错误重试次数
  retry_interval: 60               # 重试间隔（秒）
  health_check_interval: 300       # 健康检查间隔（秒）
```

### 风险控制配置

```yaml
risk_control:
  max_signals_per_day: 100         # 每日最大交易信号数
  max_position_per_stock: 0.1      # 单只股票最大仓位比例
  default_stop_loss: 0.05          # 默认止损百分比
  default_take_profit: 0.10        # 默认止盈百分比
```

## 🔐 敏感配置管理

### 环境变量方式

您可以使用环境变量来管理敏感配置：

```bash
# 设置环境变量
export ITICK_API_KEY="your_api_key"
export FEISHU_WEBHOOK="your_webhook_url"
```

然后在配置文件中引用：

```yaml
itick:
  api_key: "${ITICK_API_KEY}"

notification:
  feishu:
    webhook_url: "${FEISHU_WEBHOOK}"
```

### 单独的密钥文件

创建 `config/secrets.yaml`（确保加入 `.gitignore`）：

```yaml
itick_api_key: "your_real_api_key"
feishu_webhook: "your_real_webhook_url"
```

## 🌍 多环境配置

### 开发环境

`config/config_dev.yaml`:
```yaml
# 开发环境配置
logging:
  level: "DEBUG"

notification:
  enabled: false  # 开发时关闭通知

stock_pool:
  symbols:
    - AAPL  # 只测试少量股票
```

### 生产环境

`config/config_prod.yaml`:
```yaml
# 生产环境配置
logging:
  level: "INFO"

notification:
  enabled: true

risk_control:
  max_signals_per_day: 50  # 生产环境更保守
```

### 指定配置文件

```bash
# 使用特定配置文件运行
python main.py --config config/config_prod.yaml
python cli.py --config config/config_dev.yaml run
```

## ✅ 配置验证

### 自动验证

系统启动时会自动验证配置：

```bash
python -c "from src.core.config_manager import config_manager; print('配置验证:', config_manager.validate_config())"
```

### 手动检查配置

```bash
# 查看当前配置
python cli.py config

# 测试通知配置
python cli.py test-notifications
```

## 🔧 配置最佳实践

### 1. 安全性

- 不要将 API 密钥提交到版本控制
- 使用 `.gitignore` 忽略敏感配置文件
- 定期更换 API 密钥

### 2. 可维护性

- 使用有意义的配置文件名
- 添加详细的注释
- 分离敏感和非敏感配置

### 3. 环境管理

- 为不同环境创建不同配置文件
- 使用环境变量管理部署差异
- 定期备份重要配置

### 4. 性能优化

- 根据系统资源调整参数
- 合理设置日志级别
- 优化数据更新间隔

## 📋 配置检查清单

部署前请确认：

- [ ] iTick API Key 已正确配置
- [ ] 至少配置一种通知方式
- [ ] 股票池包含有效的股票代码
- [ ] 策略参数符合您的交易策略
- [ ] 风险控制参数合理
- [ ] 日志目录有写入权限
- [ ] 敏感配置已正确保护

## ❓ 常见配置问题

### 问题 1：API Key 无效

```
错误：iTick API authentication failed
解决：检查 API Key 是否正确，是否已激活
```

### 问题 2：通知发送失败

```
错误：Notification delivery failed
解决：检查 Webhook URL 是否有效，网络是否可达
```

### 问题 3：股票代码无效

```
错误：Invalid stock symbol
解决：确认股票代码格式正确，在支持的市场中
```

### 问题 4：权限问题

```
错误：Permission denied writing to logs
解决：确保日志目录有写入权限
```

---

有配置问题？请查看 [FAQ](faq.md) 或提交 [Issue](https://github.com/your-org/backtrader-itick/issues)。