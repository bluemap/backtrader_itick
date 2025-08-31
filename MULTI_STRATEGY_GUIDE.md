# 多策略量化交易系统使用指南

## 🚀 系统概述

多策略量化交易系统是原有单策略系统的升级版，支持同时运行多个不同的交易策略，每个策略可以独立配置股票池和资金分配。系统具备信号冲突解决、资金管理、性能监控等高级功能。

## 📋 核心特性

### ✅ 已实现功能

1. **多策略并行运行**
   - 支持同时运行多个策略
   - 独立的股票池配置
   - 独立的资金分配管理
   - 策略间信号冲突解决

2. **资金管理**
   - 按百分比或固定金额分配资金
   - 自动验证资金分配合理性
   - 支持最大投入金额限制

3. **信号冲突解决**
   - 最高置信度优先
   - 第一个信号优先
   - 信号组合模式

4. **性能监控**
   - 实时策略性能统计
   - 全局系统统计
   - 信号冲突统计

5. **多策略回测**
   - 并行回测支持
   - 策略对比分析
   - 投资建议生成

## 🔧 快速开始

### 1. 配置多策略

使用提供的多策略配置文件：

```bash
cp config/multi_strategy_config.yaml config/config.yaml
```

或者直接使用：

```bash
python main_multi_strategy.py
```

### 2. 配置文件结构

```yaml
# 多策略配置示例
strategies:
  # 策略1：布林带策略
  - name: "bollinger_aapl_msft"
    enabled: true
    type: "BollingerBands"
    
    # 策略特定的股票池
    stock_pool:
      symbols:
        - AAPL
        - MSFT
    
    # 资金分配
    capital_allocation:
      percentage: 40  # 占总资金的40%
      max_amount: 50000  # 最大投入金额
    
    # 策略参数
    parameters:
      bollinger_bands:
        period: 20
        std_dev: 2
        stop_loss_pct: 0.03
        take_profit_pct: 0.08
    
    # 风险控制
    risk_control:
      max_signals_per_day: 10
      max_position_per_stock: 0.15
      
    # 通知设置
    notification:
      enabled: true
      prefix: "[布林带]"

# 策略管理配置
strategy_management:
  total_capital: 100000
  execution_mode: "parallel"  # parallel: 并行执行
  
  # 策略冲突处理
  conflict_resolution:
    mode: "highest_confidence"  # highest_confidence, first_wins, combine_signals
    signal_weights:
      BollingerBands: 0.4
      RSI_Strategy: 0.3
      MACD_Crossover: 0.3
```

### 3. 运行系统

```bash
# 运行多策略系统
python main_multi_strategy.py

# 运行测试
python test_multi_strategy.py

# 单独回测
python -c "
from src.backtesting.multi_strategy_backtest import MultiStrategyBacktest
from src.core.config_manager import ConfigManager
from src.data.itick_provider import ItickDataProvider

config = ConfigManager('config/multi_strategy_config.yaml')
provider = ItickDataProvider(config)
backtest = MultiStrategyBacktest(config, provider)
result = backtest.run_multi_strategy_backtest(days=7)
print(result)
"
```

## 📊 系统监控

### 查看系统状态

```python
from main_multi_strategy import MultiStrategyQuantTradingSystem

system = MultiStrategyQuantTradingSystem("config/multi_strategy_config.yaml")
status = system.get_system_status()
print(f"运行状态: {status}")
```

### 性能统计

```python
# 获取策略性能
performance = system.strategy_manager.get_strategy_performance()

# 获取全局统计
global_stats = system.strategy_manager.get_global_statistics()
```

## 🎯 策略配置详解

### 支持的策略类型

- **BollingerBands**: 布林带策略
- **RSI_Strategy**: RSI超买超卖策略
- **MACD_Crossover**: MACD交叉策略
- **MA_Crossover**: 均线交叉策略
- **Momentum**: 动量策略

### 资金分配方式

1. **按百分比分配**
```yaml
capital_allocation:
  percentage: 40  # 占总资金40%
  max_amount: 50000  # 最大不超过5万
```

2. **固定金额分配**
```yaml
capital_allocation:
  amount: 30000  # 固定3万元
```

### 风险控制配置

```yaml
risk_control:
  max_signals_per_day: 10  # 每日最大信号数
  max_position_per_stock: 0.15  # 单股最大仓位15%
```

## ⚔️ 信号冲突解决

当多个策略对同一股票产生不同信号时，系统提供三种解决方式：

### 1. 最高置信度优先 (推荐)
```yaml
conflict_resolution:
  mode: "highest_confidence"
```
选择置信度最高的信号

### 2. 第一个信号优先
```yaml
conflict_resolution:
  mode: "first_wins"
```
按策略优先级选择

### 3. 信号组合
```yaml
conflict_resolution:
  mode: "combine_signals"
  signal_weights:
    BollingerBands: 0.4
    RSI_Strategy: 0.3
    MACD_Crossover: 0.3
```
按权重组合多个信号

## 📈 多策略回测

### 运行回测

```python
from src.backtesting.multi_strategy_backtest import MultiStrategyBacktest

# 创建回测管理器
backtest_manager = MultiStrategyBacktest(config_manager, data_provider)

# 运行回测
result = backtest_manager.run_multi_strategy_backtest(
    days=30,
    initial_cash=100000,
    parallel=True,
    save_results=True
)

# 查看结果
if result['status'] == 'success':
    print(f"整体收益: {result['overall_performance']['weighted_average_return_pct']:.2f}%")
    print(f"总交易数: {result['overall_performance']['total_trades']}")
    print(f"整体胜率: {result['overall_performance']['overall_win_rate']:.1f}%")
```

### 策略对比

```python
# 对比特定策略
comparison = backtest_manager.compare_strategies(
    strategy_names=['bollinger_aapl_msft', 'rsi_tech_stocks'],
    days=30
)
```

## 🔧 高级配置

### 通知配置

```yaml
notification:
  global_settings:
    summary_mode: true  # 汇总模式
    summary_interval: 300  # 5分钟汇总
    individual_notifications: true  # 单独通知
```

### 策略特定通知

```yaml
strategies:
  - name: "my_strategy"
    notification:
      enabled: true
      prefix: "[我的策略]"
```

### 数据缓存

```yaml
data:
  cache:
    enabled: true
    max_cache_size: 1000
    cache_dir: "data/cache"
```

## 📋 使用示例

### 示例1：保守投资组合

```yaml
strategies:
  - name: "conservative_bb"
    type: "BollingerBands"
    stock_pool:
      symbols: ["AAPL", "MSFT", "GOOGL"]
    capital_allocation:
      percentage: 60
    parameters:
      bollinger_bands:
        period: 30
        std_dev: 1.5
        stop_loss_pct: 0.02
        take_profit_pct: 0.05
        
  - name: "conservative_rsi"
    type: "RSI_Strategy"
    stock_pool:
      symbols: ["AAPL", "MSFT"]
    capital_allocation:
      percentage: 40
    parameters:
      rsi_strategy:
        period: 21
        oversold: 20
        overbought: 80
```

### 示例2：激进投资组合

```yaml
strategies:
  - name: "aggressive_momentum"
    type: "Momentum"
    stock_pool:
      symbols: ["TSLA", "NVDA", "AMD"]
    capital_allocation:
      percentage: 50
    parameters:
      momentum:
        period: 5
        threshold: 0.05
        
  - name: "aggressive_macd"
    type: "MACD_Crossover"
    stock_pool:
      symbols: ["TSLA", "NVDA"]
    capital_allocation:
      percentage: 50
    parameters:
      macd:
        fast_period: 8
        slow_period: 21
        signal_period: 5
```

## 🐛 故障排除

### 常见问题

1. **策略加载失败**
   - 检查策略名称是否正确
   - 确认策略参数格式
   - 查看日志文件

2. **资金分配超额**
   - 检查百分比总和不超过100%
   - 确认max_amount设置合理

3. **信号冲突过多**
   - 调整策略股票池避免重叠
   - 优化冲突解决配置

4. **回测失败**
   - 确认数据连接正常
   - 检查股票代码有效性
   - 查看错误日志

### 日志文件位置

- 系统日志: `logs/system.log`
- 策略日志: `logs/strategy_*.log`
- 回测结果: `backtest_results/multi_strategy_*.json`

## 📞 技术支持

如果遇到问题，请：

1. 检查日志文件
2. 运行测试脚本: `python test_multi_strategy.py`
3. 查看配置文件格式
4. 参考示例配置

## 🔮 未来规划

- [ ] 策略热重载
- [ ] 实时策略参数调整
- [ ] 更多冲突解决算法
- [ ] 策略组合优化
- [ ] 机器学习策略支持
- [ ] 图形化配置界面

---

**恭喜！您现在拥有了一个功能强大的多策略量化交易系统。祝您投资顺利！** 🎉