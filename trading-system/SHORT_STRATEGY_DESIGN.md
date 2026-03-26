# 做空策略设计文档

## 核心思想

做空策略是做多策略（短线高胜率策略）的**镜像反向**实现。两者参数结构完全一致，但方向相反。

## 策略对比表

### 做多 vs 做空核心参数对比

| 参数维度 | 做多（Long） | 做空（Short） | 差异说明 |
|---------|-------------|---------------|---------|
| **趋势评分** | 6-10分（高趋势） | 0-4分（低趋势） | 镜像反向 |
| **RSI范围** | 30-70（适中） | 70-90（超买） | 做空要求超买 |
| **成交量** | ≥ 0.8x | ≥ 0.8x | 一致 |
| **24h涨跌** | -5% ~ +8% | +2% ~ +8% | 做空要求正在上涨 |
| **波动率** | 0.3% ~ 5% | 0.3% ~ 5% | 一致 |
| **大盘趋势** | ≥ 4分 | ≥ 0分 | 做空时不限制 |
| **单笔金额** | $40 | $40 | 一致 |
| **最大持仓** | 3个 | 3个 | 一致 |
| **单币种占比** | 15% | 15% | 一致 |
| **止损** | -1.5% | -1.5% | 一致（价格反方向） |
| **第一止盈** | +1.0% | +1.0% | 一致（价格反方向） |
| **第二止盈** | +2.0% | +2.0% | 一致（价格反方向） |
| **时间止损** | 48小时 | 48小时 | 一致 |
| **交易间隔** | 2小时 | 2小时 | 一致 |
| **每日交易** | 5笔 | 5笔 | 一致 |

## 做空策略逻辑

### 买入（开空仓）条件

```python
def check_short_term_short_condition(config, trend_score, rsi, volume_ratio,
                                     price_change_24h, market_trend, volatility):
    # 1. 趋势评分：0-4分（低趋势）
    if trend_score < 0 or trend_score > 4:
        return False, f"趋势评分{trend_score}分，做空需要0-4分"

    # 2. RSI：70-90（超买区域）
    if rsi < 70 or rsi > 90:
        return False, f"RSI {rsi}，做空需要70-90（超买）"

    # 3. 成交量：≥ 0.8x
    if volume_ratio < 0.8:
        return False, f"成交量{volume_ratio}x，需要≥ 0.8x"

    # 4. 24h涨跌：+2% ~ +8%（要求正在上涨）
    if price_change_24h < 2.0 or price_change_24h > 8.0:
        return False, f"24h涨幅{price_change_24h}%，做空需要2% ~ 8%（正在上涨）"

    # 5. 波动率：0.3% ~ 5%
    if volatility < 0.3 or volatility > 5.0:
        return False, f"波动率{volatility}%，需要0.3% ~ 5%"

    # 5. 大盘趋势：不限制（可做空）
    # if market_trend < 0:
    #     return False, f"大盘趋势{market_trend}分，需要≥ 0分"

    return True, "满足所有短线做空条件"
```

### 退出（平空仓）条件

```python
def check_short_term_short_exit(config, entry_price, current_price, entry_time):
    # 注意：做空时，价格上涨=亏损，价格下跌=盈利
    pnl = ((entry_price - current_price) / entry_price) * 100  # 价格下跌=盈利
    hours = (datetime.now() - entry_time).total_seconds() / 3600

    # 1. 止损：价格上涨1.5%（做空亏损）
    if pnl <= -1.5:
        return True, "STOP_LOSS", f"做空亏损{abs(pnl):.2f}%，触发止损"

    # 2. 第一止盈：价格下跌1%（做空盈利50%平仓）
    if pnl >= 1.0 and pnl < 2.0:
        return True, "TAKE_PROFIT_1", f"做空盈利{pnl:.2f}%，减仓50%"

    # 3. 第二止盈：价格下跌2%（做空盈利100%平仓）
    if pnl >= 2.0:
        return True, "TAKE_PROFIT_2", f"做空盈利{pnl:.2f}%，清仓"

    # 4. 时间止损：48小时强制平仓
    if hours >= 48:
        return True, "TIME_STOP", f"做空持仓{hours:.1f}小时，时间止损"

    return False, "", ""
```

## 策略特点

### 做多策略特点
- **高胜率优先**：严格的6指标选股
- **快速进出**：第一止盈1%，第二止盈2%
- **严格止损**：-1.5%止损
- **趋势跟随**：要求趋势评分6-10分
- **适中RSI**：RSI 30-70区间
- **大盘配合**：大盘趋势≥4分

### 做空策略特点
- **逆势操作**：在低趋势时做空
- **超买捕捉**：RSI 70-90（超买区域）
- **快速平仓**：与做多一致
- **严格风控**：与做多一致
- **独立判断**：不依赖大盘趋势
- **镜像参数**：所有参数结构与做多一致

## 实现要点

### 1. 后端实现 (`short_term.py`)

```python
# 配置类
class ShortTermShortConfig(BaseModel):
    min_trend_score: int = 0
    max_trend_score: int = 4
    rsi_min: int = 70
    rsi_max: int = 90
    min_volume_ratio: float = 0.8
    max_24h_change: float = 8.0
    min_24h_change: float = -5.0
    min_market_trend: int = 0
    # ... 其他参数与做多一致

# 数据类
@dataclass
class ShortTermShortPosition:
    coin: str
    entry_price: float
    amount: float
    entry_time: datetime
    partial_exit: bool = False

# 检查函数
def check_short_term_short_condition(...) -> BuyConditionResult
def check_short_term_short_exit(...) -> ExitResult

# 配置实例
short_term_short_config = ShortTermShortConfig()
```

### 2. 前端实现 (`StrategyConfigCard.vue`)

```javascript
// 做空配置
const shortConfig = ref({
  enableShort: true,

  // 选币门槛（镜像反向）
  minTrendScore: 0,
  maxTrendScore: 4,
  minVolumeRatio: 0.8,
  minVolatility: 0.3,
  maxVolatility: 5.0,
  rsiOversoldThreshold: 70,  // 超买下限
  rsiOverboughtThreshold: 90, // 超买上限
  minChange24h: 2,          // 至少上涨2%
  maxChange24h: 8,          // 最多上涨8%
  minMarketTrend: 0,

  // 交易配置（与做多一致）
  positionRatio: 1.0,
  maxPositions: 3,
  maxPositionPercent: 15,
  stopLossPercent: 1.5,
  takeProfitPercent1: 1.0,
  takeProfitPercent2: 2.0,
  tradeSize: 40,
  minTradeInterval: 120,
  maxDailyTrades: 5,
  timeStop: 48
})
```

## 交易示例

### 做多示例
```
情景：BTC趋势8分，RSI=45，成交量1.2x
操作：买入 $40
止损价：$100 * (1 - 1.5%) = $98.5
第一止盈：$100 * (1 + 1.0%) = $101（减仓50%）
第二止盈：$100 * (1 + 2.0%) = $102（清仓）
```

### 做空示例
```
情景：ETH趋势3分，RSI=75，成交量0.9x
操作：做空 $40（开空仓）
止损价：$100 * (1 + 1.5%) = $101.5（价格上涨触发）
第一止盈：$100 * (1 - 1.0%) = $99（减仓50%）
第二止盈：$100 * (1 - 2.0%) = $98（清仓）
```

## 注意事项

### 1. PnL计算差异
- **做多**：`pnl = (current - entry) / entry * 100`
- **做空**：`pnl = (entry - current) / entry * 100`

### 2. 止盈止损方向
- **做多**：价格上涨=盈利，价格下跌=亏损
- **做空**：价格下跌=盈利，价格上涨=亏损

### 3. 大盘趋势影响
- **做多**：要求大盘趋势≥4分
- **做空**：不限制大盘趋势（做空可独立运行）

### 4. 风险提示
- 做空风险高于做多（理论上亏损无限）
- 建议做空仓位不超过总仓位的30%
- 做空应严格设置止损
- 做空适合有经验的交易者

## 与示例项目对比

| 功能 | 示例项目 | 当前项目 | 状态 |
|------|---------|---------|------|
| 做多策略 | ✅ 短线高胜率 | ✅ 已对齐 | 完全一致 |
| 做空策略 | ❌ 未实现 | ✅ 已设计 | 新增功能 |
| 做多参数 | ✅ 严格参数 | ✅ 已对齐 | 完全一致 |
| 做空参数 | ❌ 未实现 | ✅ 镜像设计 | 新增功能 |

## 后续优化建议

1. **做空独立黑名单**：做多和做空使用不同的黑名单
2. **做空情绪指标**：增加市场恐惧贪婪指数判断
3. **做空加仓策略**：亏损时的反向加仓
4. **做空对冲策略**：做多和做空同时持仓的风险控制
5. **做空回测模块**：验证做空策略的有效性

## 总结

做空策略完全基于做多策略的镜像反向设计，保持了：
- ✅ 参数结构一致性
- ✅ 交易逻辑对称性
- ✅ 风控标准统一性
- ✅ 代码复用性

这样设计的好处：
1. 易于理解和维护
2. 参数调优可以相互参考
3. 代码逻辑清晰对称
4. 风险控制统一标准
