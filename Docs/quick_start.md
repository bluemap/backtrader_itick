# 快速入门指南

本指南将帮助您在 10 分钟内快速上手港美股量化交易通知系统。

## 📋 准备工作

### 1. 系统要求

- **操作系统**: Windows 10+, macOS 10.14+, 或 Linux
- **Python 版本**: 3.8 或更高版本
- **内存**: 至少 2GB RAM
- **存储**: 至少 1GB 可用空间
- **网络**: 稳定的互联网连接

### 2. 账户准备

在开始之前，您需要准备：

- **iTick API 账户**: 访问 [iTick 官网](https://www.itick.com) 注册并获取 API Key
- **通知账户**: 
  - 飞书机器人 Webhook URL（可选）
  - 企业微信机器人 Webhook URL（可选）
  - Server 酱密钥（可选）

## 🚀 安装步骤

### 第一步：下载项目

```bash
# 克隆项目（如果有 Git）
git clone https://github.com/your-org/backtrader-itick.git
cd backtrader-itick

# 或直接下载压缩包并解压
```

### 第二步：安装依赖

#### 🚀 自动安装（推荐）

**方式一：使用Shell脚本（Linux/macOS）**
```bash
# 使用Shell自动安装脚本（推荐，一键完成所有安装）
./install.sh
```

**方式二：使用Python脚本（跨平台）**
```bash
# 使用Python自动安装脚本（适用于Windows/Linux/macOS）
python3 install.py
```

自动安装脚本会：
- 检测Python环境和版本
- 自动创建虚拟环境
- 检测网络并选择最佳镜像源
- 安装所有依赖包
- 验证安装结果
- 创建必要的目录和配置文件

#### 🔧 手动安装

如果您更喜欢手动控制安装过程：

```bash
# 方式一：使用 pip
pip install -r requirements.txt

# 方式二：使用 make
make install

# 方式三：创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 第三步：配置系统

1. 复制配置模板：
```bash
cp config/config.yaml config/config_local.yaml
```

2. 编辑配置文件：
```bash
# 使用您喜欢的编辑器
nano config/config_local.yaml
# 或
vim config/config_local.yaml
```

3. 必须配置的项目：
```yaml
# iTick API 配置（必须）
itick:
  api_key: "YOUR_ITICK_API_KEY"  # 替换为您的实际 API Key

# 股票池（可选，使用默认值即可开始）
stock_pool:
  symbols:
    - AAPL
    - MSFT
    - TSLA

# 通知配置（至少配置一种）
notification:
  enabled: true
  feishu:
    enabled: true
    webhook_url: "YOUR_FEISHU_WEBHOOK_URL"
```

## 🎯 第一次运行

### 1. 测试配置

```bash
# 检查配置是否正确
python cli.py config

# 测试通知功能
python cli.py test-notifications
```

### 2. 启动系统

```bash
# 方式一：使用主程序
python main.py

# 方式二：使用命令行工具
python cli.py run

# 方式三：使用 make
make run
```

如果一切正常，您应该看到类似的输出：

```
2024-01-01 10:00:00 - INFO - 量化交易系统启动成功
2024-01-01 10:00:01 - INFO - 已订阅 3 只股票的实时数据
2024-01-01 10:00:02 - INFO - 实时信号生成已启动
系统运行中，按 Ctrl+C 停止...
```

### 3. 查看系统状态

在另一个终端窗口中：

```bash
# 查看系统状态
python cli.py status

# 查看仪表盘
python cli.py dashboard

# 查看日志
python cli.py logs
```

## 📊 理解输出

### 系统启动信息

```
🚀 量化交易系统已启动

启动时间: 2024-01-01 10:00:00
监控股票数量: 3
策略类型: MA_Crossover
通知方式: feishu

系统正在监控市场行情，等待交易信号...
```

### 交易信号示例

当系统生成交易信号时，您会收到通知：

```
🔥 BUY 信号 🔥

📈 股票代码: AAPL
💰 价格: $189.23
📊 策略: MA_Crossover
⚡ 置信度: ⭐⭐⭐⭐ (80%)
🕐 时间: 2024-01-01 10:30:00

🎯 止盈: $195.00 (+3.0%)
🛡️ 止损: $185.00 (-2.2%)

📝 原因: 短期均线(190.5)上穿长期均线(188.2)
```

## ⚙️ 基础配置说明

### 策略选择

您可以选择不同的交易策略：

```yaml
strategy:
  type: "MA_Crossover"     # 移动平均线交叉
  # type: "RSI_Strategy"   # RSI 策略
  # type: "BollingerBands" # 布林带策略
  # type: "Breakout"       # 突破策略
  # type: "Momentum"       # 动量策略
```

### 股票池管理

```yaml
stock_pool:
  symbols:
    - AAPL    # 苹果
    - MSFT    # 微软
    - GOOGL   # 谷歌
    - AMZN    # 亚马逊
    - TSLA    # 特斯拉
```

或使用 CSV 文件：

```yaml
stock_pool:
  csv_file: "data/my_stocks.csv"
```

### 风险控制

```yaml
risk_control:
  max_signals_per_day: 50      # 每日最大信号数
  default_stop_loss: 0.05      # 默认止损 5%
  default_take_profit: 0.10    # 默认止盈 10%
```

## 🔧 常用命令

```bash
# 查看所有可用策略
python cli.py strategies

# 更新股票池
python cli.py update-pool --symbols "AAPL,MSFT,GOOGL"

# 运行回测
python cli.py backtest --start-date 2023-01-01 --end-date 2023-12-31

# 导出信号历史
python cli.py export-signals --format csv

# 查看最近的错误日志
python cli.py logs --type error --lines 20
```

## 🚨 故障排除

### 常见问题

1. **API Key 错误**
   ```
   错误: iTick API Key 未设置或无效
   解决: 检查 config_local.yaml 中的 api_key 配置
   ```

2. **网络连接失败**
   ```
   错误: WebSocket 连接失败
   解决: 检查网络连接和防火墙设置
   ```

3. **通知发送失败**
   ```
   错误: 飞书消息发送失败
   解决: 检查 webhook_url 是否正确
   ```

### 获取帮助

```bash
# 查看命令帮助
python cli.py --help

# 查看特定命令帮助
python cli.py run --help
```

## 📈 下一步

现在您已经成功运行了系统！接下来可以：

1. **优化策略参数**: 根据市场情况调整策略参数
2. **扩展股票池**: 添加更多您关注的股票
3. **设置多种通知**: 配置多个通知渠道
4. **运行回测**: 使用历史数据测试策略效果
5. **监控系统**: 定期查看系统状态和日志

## 📚 学习资源

- [完整配置指南](configuration.md)
- [策略详解](strategies.md)
- [API 参考](api.md)
- [常见问题](faq.md)

## ⚠️ 重要提醒

1. **仅供通知**: 系统只生成信号和通知，不会自动下单
2. **风险控制**: 请根据个人风险承受能力调整参数
3. **市场风险**: 投资有风险，策略仅供参考
4. **实盘测试**: 建议先用小资金测试策略效果

---

🎉 恭喜您成功完成快速入门！如有问题，请查看 [FAQ](faq.md) 或提交 [Issue](https://github.com/your-org/backtrader-itick/issues)。