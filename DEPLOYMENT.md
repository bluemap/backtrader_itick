# 安装和部署指南

## 🎯 系统完成情况

恭喜！根据您的PRD需求，我已经为您创建了一个完整的港美股量化交易通知系统。

### ✅ 已实现的功能

1. **完整的系统架构**
   - 基于 iTick 实时行情和 Backtrader 策略引擎
   - 模块化设计，易于扩展和维护

2. **股票池管理**
   - 支持手动输入股票代码
   - 支持CSV文件导入
   - 股票代码验证和规范化

3. **多策略支持**
   - 15+ 种内置策略模板
   - 均线交叉、RSI、布林带、突破、动量等
   - 策略工厂模式，易于扩展

4. **实时数据接入**
   - iTick WebSocket 实时行情
   - 历史数据存储和管理
   - 数据断线重连机制

5. **智能信号生成**
   - 信号过滤和验证
   - 风险控制机制
   - 置信度评估

6. **多渠道通知**
   - 飞书机器人支持
   - 微信通知支持（企业微信/Server酱）
   - 批量和实时通知模式

7. **系统监控**
   - 完整的日志记录
   - 性能监控和健康检查
   - 错误自动重试

8. **便捷工具**
   - 命令行管理工具
   - 配置验证和测试
   - 信号导出功能

## 🚀 快速部署

### 第一步：环境准备

```bash
# 确保Python 3.8+已安装
python3 --version

# 克隆或下载项目到本地
cd /path/to/your/directory
# 如果有Git: git clone <your-repo>
# 或直接解压项目文件
```

### 第二步：安装依赖

```bash
# 进入项目目录
cd backtrader_itick

# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 第三步：配置系统

```bash
# 复制配置模板
cp config/config.yaml config/config_local.yaml

# 编辑配置文件
nano config/config_local.yaml
```

**必须配置的项目：**

```yaml
# 1. iTick API Key（必须）
itick:
  api_key: "您的iTick_API_Key"

# 2. 通知配置（至少配置一种）
notification:
  feishu:
    enabled: true
    webhook_url: "您的飞书机器人Webhook_URL"
```

### 第四步：测试系统

```bash
# 测试配置
python3 cli.py config

# 测试通知
python3 cli.py test-notifications

# 查看可用策略
python3 cli.py strategies
```

### 第五步：启动系统

```bash
# 启动系统
python3 main.py

# 或使用命令行工具
python3 cli.py run
```

## 📋 配置示例

### 完整配置示例 (config_local.yaml)

```yaml
# iTick API 配置
itick:
  api_key: "YOUR_REAL_API_KEY"  # 替换为真实的API Key

# 股票池
stock_pool:
  symbols:
    - AAPL    # 苹果
    - MSFT    # 微软
    - GOOGL   # 谷歌
    - TSLA    # 特斯拉
    - AMZN    # 亚马逊

# 策略配置
strategy:
  type: "MA_Crossover"
  ma_crossover:
    short_window: 10
    long_window: 50

# 通知配置
notification:
  enabled: true
  feishu:
    enabled: true
    webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_TOKEN"
  frequency:
    mode: "immediate"

# 风险控制
risk_control:
  max_signals_per_day: 50
  default_stop_loss: 0.05
  default_take_profit: 0.10
```

## 🔧 常用命令

```bash
# 系统管理
python3 cli.py status          # 查看系统状态
python3 cli.py run             # 启动系统
python3 cli.py dashboard       # 查看仪表盘

# 配置管理
python3 cli.py config          # 查看当前配置
python3 cli.py strategies      # 查看所有策略

# 股票池管理
python3 cli.py update-pool --symbols "AAPL,MSFT,GOOGL"
python3 cli.py update-pool --file data/my_stocks.csv

# 回测和分析
python3 cli.py backtest --start-date 2023-01-01 --end-date 2023-12-31
python3 cli.py export-signals --format csv

# 日志查看
python3 cli.py logs --type main --lines 50
python3 cli.py logs --type error --lines 20
```

## 📱 通知配置指南

### 飞书机器人配置

1. 在飞书群中添加机器人
2. 选择"自定义机器人"
3. 设置机器人名称为"量化交易助手"
4. 复制生成的Webhook URL
5. 粘贴到配置文件的 `notification.feishu.webhook_url`

### 微信通知配置

#### 企业微信机器人
1. 在企业微信群中添加机器人
2. 获取Webhook URL
3. 配置到 `notification.wechat.webhook_url`

#### Server酱
1. 访问 [Server酱官网](https://sct.ftqq.com/)
2. 获取SendKey
3. 配置到 `notification.wechat.server_chan_key`

## 📊 策略选择建议

| 市场环境 | 推荐策略 | 参数建议 |
|---------|---------|---------|
| 趋势市场 | MA_Crossover | short_window: 5, long_window: 20 |
| 震荡市场 | RSI_Strategy | oversold: 30, overbought: 70 |
| 突破行情 | Breakout | period: 20, min_breakout_pct: 0.02 |
| 高波动 | BollingerBands | period: 20, std_dev: 2 |

## 🚀 后台运行

### Linux/Mac 后台运行

```bash
# 使用 nohup
nohup python3 main.py > logs/system.log 2>&1 &

# 使用 screen
screen -S quant-trading
python3 main.py
# 按 Ctrl+A, D 分离会话

# 查看后台任务
jobs
ps aux | grep python
```

### 开机自启动 (Linux)

创建systemd服务文件：

```bash
sudo nano /etc/systemd/system/quant-trading.service
```

内容：
```ini
[Unit]
Description=Quantitative Trading System
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/backtrader_itick
ExecStart=/path/to/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl enable quant-trading.service
sudo systemctl start quant-trading.service
```

## 📈 系统监控

### 查看系统状态
```bash
python3 cli.py dashboard
```

### 监控关键指标
- CPU和内存使用率
- 信号生成频率
- 通知发送成功率
- 错误和警告数量

### 日志分析
```bash
# 查看最近的交易信号
python3 cli.py logs --type signals --lines 20

# 查看系统错误
python3 cli.py logs --type error --lines 10

# 查看性能指标
python3 cli.py logs --type performance --lines 10
```

## 🔒 安全建议

1. **保护API密钥**
   - 不要提交到版本控制
   - 使用环境变量或单独的密钥文件

2. **网络安全**
   - 确保系统运行在安全的网络环境
   - 定期更新依赖包

3. **访问控制**
   - 限制系统文件访问权限
   - 定期备份重要配置

4. **监控告警**
   - 设置系统异常告警
   - 监控资源使用情况

## ⚡ 性能优化

1. **减少监控股票数量**：建议不超过50只
2. **调整更新频率**：根据需要设置数据更新间隔
3. **优化策略参数**：避免过于复杂的计算
4. **合理设置日志级别**：生产环境使用INFO级别

## 🛠️ 故障排除

### 常见问题

1. **API连接失败**
   ```bash
   # 检查网络连接
   ping api.itick.com
   
   # 验证API Key
   python3 cli.py config
   ```

2. **通知发送失败**
   ```bash
   # 测试通知
   python3 cli.py test-notifications
   
   # 检查日志
   python3 cli.py logs --type error
   ```

3. **内存使用过多**
   ```bash
   # 检查系统状态
   python3 cli.py dashboard
   
   # 减少历史数据保留
   # 在配置中调整 retention_hours
   ```

### 获取帮助

- 查看文档：`docs/` 目录
- 提交问题：GitHub Issues
- 邮件支持：support@example.com

## 🎉 恭喜您！

您的港美股量化交易通知系统已经完成部署！

系统将根据您配置的策略监控股票市场，生成交易信号并推送通知。请记住：

⚠️ **重要提醒**：
- 系统仅生成信号，不会自动下单
- 所有交易决策需要您手动确认
- 投资有风险，请谨慎决策
- 建议先用小资金测试策略效果

祝您交易顺利！ 🚀📈