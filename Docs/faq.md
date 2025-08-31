# 常见问题 (FAQ)

本文档收集了用户在使用量化交易系统时遇到的常见问题和解决方案。

## 📋 目录

- [安装相关](#安装相关)
- [配置相关](#配置相关)
- [运行相关](#运行相关)
- [策略相关](#策略相关)
- [通知相关](#通知相关)
- [数据相关](#数据相关)
- [性能相关](#性能相关)
- [其他问题](#其他问题)

## 🔧 安装相关

### Q1: 安装依赖时出现错误怎么办？

**A**: 常见的安装问题和解决方法：

```bash
# 问题：pip 版本过旧
pip install --upgrade pip

# 问题：网络连接问题，使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 问题：权限问题，使用 --user 参数
pip install --user -r requirements.txt

# 问题：虚拟环境问题，重新创建
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### Q2: Python 版本要求是什么？

**A**: 系统要求 Python 3.8 或更高版本。推荐使用 Python 3.9 或 3.10。

```bash
# 检查 Python 版本
python --version

# 如果版本过低，请升级 Python
```

### Q3: 在 Windows 上安装遇到问题怎么办？

**A**: Windows 用户常见问题：

1. **缺少 Visual C++ 编译器**：
   - 安装 Microsoft Visual C++ Build Tools
   - 或安装 Visual Studio Community

2. **长路径问题**：
   - 启用 Windows 长路径支持
   - 或将项目移到较短的路径下

3. **权限问题**：
   - 以管理员身份运行命令提示符
   - 或使用 `--user` 参数安装

## ⚙️ 配置相关

### Q4: 如何获取 iTick API Key？

**A**: 获取步骤：

1. 访问 [iTick 官网](https://www.itick.com)
2. 注册账户并完成认证
3. 登录后进入开发者中心
4. 申请 API 密钥
5. 将密钥填入配置文件的 `itick.api_key` 字段

### Q5: 配置文件应该放在哪里？

**A**: 配置文件建议放置：

```
推荐方式：
config/config_local.yaml  # 本地配置，不提交到 Git

其他方式：
config/config.yaml        # 直接修改默认配置
~/.config/backtrader-itick/config.yaml  # 用户目录配置
```

### Q6: 如何设置多个通知渠道？

**A**: 可以同时启用多个通知方式：

```yaml
notification:
  enabled: true
  feishu:
    enabled: true
    webhook_url: "your_feishu_webhook"
  wechat:
    enabled: true
    webhook_url: "your_wechat_webhook"
```

### Q7: 配置修改后需要重启系统吗？

**A**: 是的，大部分配置修改后需要重启系统才能生效。部分配置可以通过 API 动态修改：

```bash
# 重启系统
python cli.py stop
python cli.py run

# 动态更新股票池（无需重启）
python cli.py update-pool --symbols "AAPL,MSFT,GOOGL"
```

## 🚀 运行相关

### Q8: 系统启动后没有任何输出是正常的吗？

**A**: 这取决于配置的日志级别和股票市场状态：

1. **检查日志级别**：确保设置为 `INFO` 或 `DEBUG`
2. **检查市场时间**：在非交易时间可能没有行情数据
3. **查看日志文件**：检查 `logs/main.log` 文件
4. **使用状态命令**：`python cli.py status`

### Q9: 系统突然停止运行怎么办？

**A**: 排查步骤：

1. **查看错误日志**：
   ```bash
   python cli.py logs --type error --lines 20
   ```

2. **检查系统资源**：
   ```bash
   python cli.py dashboard
   ```

3. **检查网络连接**：确保可以访问 iTick API

4. **重启系统**：
   ```bash
   python main.py
   ```

### Q10: 如何在后台运行系统？

**A**: 后台运行方法：

```bash
# 方式一：使用 nohup
nohup python main.py > output.log 2>&1 &

# 方式二：使用 screen
screen -S quant-trading
python main.py
# 按 Ctrl+A, D 分离会话

# 方式三：使用 systemd (Linux)
# 创建服务文件 /etc/systemd/system/quant-trading.service
sudo systemctl start quant-trading
sudo systemctl enable quant-trading
```

## 📊 策略相关

### Q11: 如何选择合适的策略？

**A**: 策略选择建议：

| 市场环境 | 推荐策略 | 说明 |
|---------|---------|------|
| 趋势市场 | MA_Crossover, Momentum | 跟踪趋势方向 |
| 震荡市场 | RSI_Strategy, BollingerBands | 高卖低买 |
| 突破行情 | Breakout, Donchian_Breakout | 捕捉突破机会 |
| 不确定 | Adaptive_MA_Crossover | 自适应调整 |

### Q12: 策略参数如何优化？

**A**: 参数优化方法：

1. **回测验证**：
   ```bash
   python cli.py backtest --start-date 2023-01-01 --end-date 2023-12-31
   ```

2. **逐步调整**：一次只调整一个参数

3. **A/B 测试**：同时运行不同参数的策略

4. **市场适应**：根据市场变化调整参数

### Q13: 可以同时运行多个策略吗？

**A**: 当前版本只支持单策略运行。多策略支持计划在后续版本中实现。

### Q14: 如何创建自定义策略？

**A**: 创建自定义策略步骤：

1. **继承基类**：
   ```python
   from src.strategies.base_strategy import BaseStrategy
   
   class MyStrategy(BaseStrategy):
       def next(self):
           # 实现策略逻辑
           pass
   ```

2. **注册策略**：在策略工厂中注册

3. **配置参数**：在配置文件中添加参数

详细教程请参考 [开发指南](development.md)。

## 📢 通知相关

### Q15: 为什么收不到通知？

**A**: 排查步骤：

1. **检查配置**：
   ```bash
   python cli.py config
   ```

2. **测试通知**：
   ```bash
   python cli.py test-notifications
   ```

3. **检查网络**：确保可以访问通知服务

4. **查看日志**：检查是否有错误信息

### Q16: 通知太频繁怎么办？

**A**: 调整通知频率：

```yaml
notification:
  frequency:
    mode: "batch"        # 改为批量模式
    batch_interval: 10   # 10分钟汇总一次
```

或调整信号过滤条件：

```yaml
# 在信号生成模块中调整
signal_filter:
  min_confidence: 0.8    # 提高置信度阈值
  min_interval_minutes: 60  # 增加信号间隔
```

### Q17: 如何自定义通知消息格式？

**A**: 修改通知模板，在 `src/notifications/notification_manager.py` 中：

```python
def format_signal_message(self, signal: TradeSignal) -> str:
    # 自定义消息格式
    return f"自定义格式: {signal.action} {signal.symbol}"
```

## 📈 数据相关

### Q18: 系统支持哪些股票市场？

**A**: 目前支持：
- **美股**：NYSE、NASDAQ、AMEX
- **港股**：HKEX

支持的市场以 iTick 提供的数据为准。

### Q19: 历史数据从哪里获取？

**A**: 历史数据来源：
1. **iTick API**：实时和历史数据
2. **本地存储**：系统自动保存历史数据
3. **手动导入**：可以导入外部数据

### Q20: 数据延迟有多大？

**A**: 数据延迟取决于：
- **iTick 数据源**：通常 < 1 秒
- **网络延迟**：10-100 毫秒
- **系统处理**：< 100 毫秒

总延迟通常在 1-2 秒内。

### Q21: 如何处理数据断线？

**A**: 系统具有自动重连机制：

1. **检测断线**：自动检测连接状态
2. **重试连接**：按配置的间隔重试
3. **通知用户**：发送断线通知
4. **数据补齐**：重连后获取缺失数据

## 🚀 性能相关

### Q22: 系统占用内存过多怎么办？

**A**: 内存优化方法：

1. **减少历史数据缓存**：
   ```yaml
   data:
     retention_hours: 12  # 减少保留时间
   ```

2. **减少监控股票数量**：限制股票池大小

3. **调整日志级别**：
   ```yaml
   logging:
     level: "WARNING"  # 减少日志输出
   ```

### Q23: CPU 使用率过高怎么办？

**A**: CPU 优化方法：

1. **增加更新间隔**：
   ```yaml
   data:
     update_interval: 300  # 5分钟更新一次
   ```

2. **简化策略逻辑**：使用计算量较小的策略

3. **减少技术指标计算**：只计算必要的指标

### Q24: 系统可以在树莓派上运行吗？

**A**: 可以，但需要注意：

1. **内存限制**：确保有足够的 RAM（建议 2GB+）
2. **性能调优**：减少监控股票数量
3. **网络稳定**：确保网络连接稳定
4. **散热处理**：长时间运行需要良好散热

## 🔍 其他问题

### Q25: 系统会自动下单吗？

**A**: **不会**。系统只生成交易信号并发送通知，不会进行任何自动交易。用户需要根据通知在券商平台手动下单。

### Q26: 数据安全如何保障？

**A**: 数据安全措施：

1. **本地存储**：所有数据存储在本地
2. **加密传输**：使用 HTTPS/WSS 连接
3. **敏感信息**：API 密钥等敏感信息加密存储
4. **访问控制**：限制系统访问权限

### Q27: 可以用于实盘交易吗？

**A**: 系统设计用于**信号生成和通知**，不直接进行实盘交易。建议：

1. **充分测试**：先进行充分的回测和模拟
2. **小资金试验**：用小额资金验证策略
3. **风险控制**：设置合理的止损止盈
4. **人工确认**：重要决策需要人工确认

### Q28: 如何获得技术支持？

**A**: 技术支持渠道：

1. **文档查阅**：首先查看相关文档
2. **GitHub Issues**：提交问题和建议
3. **社区讨论**：参与社区讨论
4. **邮件联系**：发送邮件到 support@example.com

### Q29: 系统开源吗？

**A**: 是的，系统采用 MIT 开源协议。您可以：

- 自由使用和修改代码
- 贡献代码和改进
- 创建自己的衍生版本
- 用于商业用途（需遵循许可证）

### Q30: 如何贡献代码？

**A**: 贡献步骤：

1. **Fork 项目**：在 GitHub 上 Fork 项目
2. **创建分支**：创建功能分支
3. **编写代码**：实现新功能或修复
4. **测试验证**：确保代码质量
5. **提交 PR**：创建 Pull Request

详细流程请参考 [贡献指南](contributing.md)。

---

## 🆘 还有问题？

如果您的问题在这里找不到答案，请：

1. 查看其他文档：[快速入门](quick_start.md) | [配置指南](configuration.md) | [API 文档](api.md)
2. 搜索 [GitHub Issues](https://github.com/your-org/backtrader-itick/issues)
3. 提交新的 [Issue](https://github.com/your-org/backtrader-itick/issues/new)
4. 发送邮件到：support@example.com

我们会尽快为您解答！