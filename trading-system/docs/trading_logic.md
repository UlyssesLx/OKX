# 交易逻辑文档

## 概述

本文档描述OKX加密货币自动交易系统的完整交易逻辑，包括买入、卖出、做空、平空等核心交易决策流程。

---

## 一、核心交易组件

### 1.1 主要文件结构

```
backend/app/
├── services/
│   ├── simulation_manager.py  # 模拟持仓管理、止盈止损信号检查
│   ├── trading_engine.py      # 核心交易引擎、信号生成、市场扫描
│   ├── trade_stats.py         # 交易统计
│   └── coordinator.py         # 交易协调器
├── strategies/
│   ├── indicators.py          # 技术指标分析
│   ├── resonance.py           # 共振分析
│   └── enhanced.py            # 增强策略（横盘检测、紧急停止等）
└── api/
    └── services.py            # API服务、配置同步
```

---

## 二、交易信号检查逻辑

### 2.1 做多持仓检查 - `check_sell_signals()`

#### 2.1.1 动态止盈止损模式 (`dynamic_bands_enabled=True`)

```python
# 动态止盈计算
if trading_config.dynamic_take_profit_enabled:
    if trend_score >= take_profit_score_tier1:  # 9分
        base_take_profit = take_profit_trend_9_10  # 15%
    elif trend_score >= take_profit_score_tier2:  # 7分
        base_take_profit = take_profit_trend_7_8  # 10%
    elif trend_score >= take_profit_score_tier3:  # 5分
        base_take_profit = take_profit_trend_5_6  # 8%
    else:
        base_take_profit = take_profit_trend_default  # 6%
else:
    base_take_profit = 6.0

# 动态止损计算（智能止损）
if trading_config.smart_stop_loss_enabled:
    if trend_score >= stop_loss_score_tier1:  # 8分
        base_stop_loss = stop_loss_trend_8_plus  # -3%
    elif trend_score >= stop_loss_score_tier2:  # 6分
        base_stop_loss = stop_loss_trend_6_7  # -2%
    else:
        base_stop_loss = stop_loss_trend_default  # -1.5%
else:
    base_stop_loss = -3.0

# 波动率因子和市场容量因子
volatility_factor = min(2.0, max(0.5, volatility / 3))
if turnover_24h > 1B:
    market_cap_factor = 1.2
elif turnover_24h > 100M:
    market_cap_factor = 1.0
else:
    market_cap_factor = 0.6

# 趋势因子
trend_factor = 1.2 if trend_score >= 8 else (1.0 if trend_score >= 6 else 0.8)

# 最终动态波段
dynamic_stop_loss = base_stop_loss * volatility_factor * market_cap_factor * trend_factor
dynamic_take_profit = base_take_profit * volatility_factor * market_cap_factor * trend_factor

# 时间衰减止损
if time_decay_enabled:
    hours_held = holding_time_minutes / 60
    time_decay = hours_held * time_decay_factor  # 每小时收紧0.1%
    dynamic_stop_loss = max(dynamic_stop_loss - time_decay, time_decay_max_stop)  # 不超过-8%

# 限制范围
dynamic_stop_loss = max(max_stop_loss, min(min_stop_loss, dynamic_stop_loss))  # -5% ~ -1%
dynamic_take_profit = max(min_take_profit, min(max_take_profit, dynamic_take_profit))  # 2% ~ 15%
```

#### 2.1.2 非动态模式 - 智能止损止盈

**止损拦截加仓逻辑**:
```python
# 条件1: 触发止损但趋势强劲 → 优先加仓
if pnl_percent <= smart_stop_loss:
    if pyramid_on_stop_loss_enabled and trend_score >= pyramid_on_stop_loss_trend_score:
        if pos.pyramid_layers < pyramid_max_layers:
            # 仓位占比检查
            position_percent = pos.usdt_value / initial_balance * 100
            if position_percent < pyramid_on_stop_loss_max_position_percent:
                return {"suggest_pyramid": True}  # 建议金字塔加仓
    # 否则执行止损卖出
```

**固定止损检查**:
```python
# 固定止损
if pnl_percent <= pos.stop_loss_percent:
    return {"should_sell": True, "sell_percent": 1.0}
```

**动态止盈**:
```python
if dynamic_take_profit_enabled:
    if trend_score >= take_profit_score_tier1:
        dynamic_take_profit = take_profit_trend_9_10
    # ... 趋势档位计算
    if pnl_percent >= dynamic_take_profit:
        return {"should_sell": True, "sell_percent": 1.0}
    if pnl_percent >= dynamic_take_profit * 0.5 and not partial_profit_taken:
        return {"should_sell": True, "sell_percent": 0.5}  # 部分止盈50%
```

#### 2.1.3 减仓策略

**1. 小盈减仓** (`small_profit_reduce_enabled`)
```python
# 条件: 盈利≥止盈线50% 且 仓位>15%
if pnl_percent >= dynamic_take_profit * 0.5 and position_percent > 15%:
    return {"should_sell": True, "sell_percent": 0.5}  # 卖出50%
```

**2. 超仓减仓** (`over_position_reduce_enabled`)
```python
# 条件: 仓位>30%
if position_percent > 30%:
    # 智能豁免期检查
    if over_position_exemption_enabled and exemption_start:
        elapsed = (now - exemption_start).minutes
        # 亏损>1%: 豁免60分钟; 亏损0-1%: 豁免45分钟; 盈利: 豁免30分钟
        if elapsed < exemption_minutes:
            return {"is_exemption": True}  # 豁免期内，继续持有
    # 执行减仓至20%
```

**3. 趋势变盘减仓** (`trend_reversal_reduce_enabled`)
```python
# 条件: 趋势从8+分降至5分以下
if trend_history >= 3次高分 and current_trend <= 5:
    return {"should_sell": True, "sell_percent": 0.5}
```

**4. 移动止损** (Trailing Stop)
```python
# 激活条件: 盈利≥3% (考虑杠杆)
if pnl_percent >= 3%:
    trailing_activated = True

# 移动止损: 最高价 * 0.98，回调2%触发
if trailing_activated:
    trailing_stop_price = highest_price * 0.98
    if current_price <= trailing_stop_price:
        return {"should_sell": True, "sell_percent": 1.0}
```

---

### 2.2 做空持仓检查 - `check_short_cover_signals()`

#### 2.2.1 动态模式

```python
if dynamic_bands_enabled:
    volatility_factor = min(2.0, max(0.5, volatility / 3))
    market_cap_factor = 1.2 / 1.0 / 0.6  # 根据成交额

    base_stop_loss = short_stop_loss_percent  # 做空止损1.5%
    base_take_profit = short_take_profit_percent  # 做空止盈3.0%

    # 做空逻辑：趋势越低（接近0），trend_factor越大
    trend_factor = 1.2 if trend_score <= 3 else (1.0 if trend_score <= 5 else 0.8)

    dynamic_stop_loss = base_stop_loss * volatility_factor * market_cap_factor * trend_factor
    dynamic_take_profit = base_take_profit * volatility_factor * market_cap_factor * trend_factor

    # 范围限制
    dynamic_stop_loss = max(1.0, min(8.0, dynamic_stop_loss))
    dynamic_take_profit = max(2.0, min(15.0, dynamic_take_profit))

    # 做空盈亏计算：(入场价 - 当前价) / 入场价 * 杠杆
    pnl_percent = (entry_price - current_price) / entry_price * 100 * leverage

    if pnl_percent <= -dynamic_stop_loss:  # 亏损超过止损线
        return {"should_cover": True, "cover_percent": 1.0}
    if pnl_percent >= dynamic_take_profit:  # 盈利达到止盈线
        return {"should_cover": True, "cover_percent": 1.0}
    if pnl_percent >= dynamic_take_profit * 0.5:
        return {"should_cover": True, "cover_percent": 0.5}  # 部分平仓
```

#### 2.2.2 非动态模式

```python
# 智能止损（做空）
if smart_stop_loss_enabled:
    # 做空止损逻辑与做多对称，但方向相反
    if trend_score <= (10 - stop_loss_score_tier2):  # trend_score <= 4
        short_stop_loss = stop_loss_trend_6_7  # 2%
    elif trend_score <= (10 - stop_loss_score_tier1):  # trend_score <= 2
        short_stop_loss = stop_loss_trend_8_plus  # 3%
    else:
        short_stop_loss = stop_loss_trend_default  # 1.5%

# 动态止盈（做空）
if dynamic_take_profit_enabled:
    if trend_score >= take_profit_score_tier1:  # 9分
        short_take_profit = take_profit_trend_9_10
    # ... 趋势档位计算
```

---

## 三、买入信号生成逻辑

### 3.1 市场扫描流程 (`scan_market`)

```
1. 获取所有USDT交易对行情
2. 按24h成交额排序，取前20名
3. 过滤稳定币和低价币
4. 获取趋势分析数据
5. 检查横盘状态
```

### 3.2 三层买入策略

#### 第一层：短线高胜率策略 (`_check_low_buy_conditions`)

```python
# 条件全部满足才通过
1. 趋势评分: 6 <= score <= 10
2. RSI: 30 <= rsi <= 70
3. 24h涨跌: -5% <= change <= +8%
4. 成交量比: ratio >= 0.8x
```

#### 第二层：严格抄底策略 (`_check_strict_dip_buy`)

```python
# 当短线策略不通过时Fallback
1. 趋势评分 >= 7分
2. BTC趋势 >= 6分
3. ETH趋势 >= 5分
4. RSI < 35 (超卖)
5. 成交量 > 2倍平均
6. 连续3根阴线后第4根收阳
7. 价格 < MA5 且 < MA10
```

#### 第三层：特殊信号Fallback

```python
# 当短线和严格抄底都不通过时，且 bullish_score < 7
1. 阴线买入: 连续阴线后反弹
2. 暴跌反弹: 24h暴跌>-10%后趋势回升
```

### 3.3 做空信号

#### 短线做空 (`_check_short_term`)

```python
1. bearish_score >= 7 (看跌评分)
2. bearish_score > bullish_score + 2 (领先看涨2分)
3. RSI: 30 <= rsi <= 70
4. 24h涨跌: -8% <= change <= +5%
5. 成交量比: ratio >= 0.8x
```

#### 严格做空 (`_check_short_dip`)

```python
# 与严格抄底对称
1. 趋势评分 <= 4分
2. BTC趋势 <= 4分
3. ETH趋势 <= 4分
4. RSI > 65 (超买)
5. 成交量 > 2倍平均
6. 连续3根阳线后第4根收阴
```

---

## 四、配置优先级

### 4.1 配置来源

| 配置项 | 来源 | 说明 |
|--------|------|------|
| 交易引擎配置 | `trading_engine.config` (TradingConfig dataclass) | 核心默认配置 |
| 前端智能配置 | `smart_trading_config.json` | 通过API同步 |
| 系统配置 | `settings.py` | 环境变量配置 |

### 4.2 配置同步流程

```python
# 1. 前端修改智能交易配置
POST /api/v1/services/config/smart-trading

# 2. services.py 保存到文件
save_smart_trading_config_file(config)

# 3. 同步到 trading_engine.config
update_smart_trading_config():
    for key, attr in key_attr_map.items():
        setattr(trading_engine.config, attr, config[key])

# 4. 同步到 settings.py
settings.SMART_STOP_LOSS_ENABLED = config["smart_stop_loss_enabled"]
```

### 4.3 simulation_manager配置获取优先级

```python
# 优先使用 trading_config，否则降级到 settings
if trading_config:
    smart_stop_loss_enabled = getattr(trading_config, 'smart_stop_loss_enabled', settings.SMART_STOP_LOSS_ENABLED)
else:
    smart_stop_loss_enabled = settings.SMART_STOP_LOSS_ENABLED
```

---

## 五、关键配置参数

### 5.1 止盈止损配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `stop_loss_trend_8_plus` | -3.0% | 趋势8+分止损 |
| `stop_loss_trend_6_7` | -2.0% | 趋势6-7分止损 |
| `stop_loss_trend_default` | -1.5% | 默认止损 |
| `take_profit_trend_9_10` | 15.0% | 趋势9-10分止盈 |
| `take_profit_trend_7_8` | 10.0% | 趋势7-8分止盈 |
| `take_profit_trend_5_6` | 8.0% | 趋势5-6分止盈 |
| `take_profit_trend_default` | 6.0% | 默认止盈 |

### 5.2 金字塔加仓配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `smart_pyramid_max_layers` | 3 | 最大加仓层数 |
| `smart_pyramid_drop_threshold` | -5.0% | 加仓亏损阈值 |
| `smart_pyramid_drop_per_layer` | -10.0% | 每层下跌幅度 |
| `smart_pyramid_base_amount` | 25.0 | 基础加仓金额 |

### 5.3 风控配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_position_percent` | 35% | 单币种最大仓位 |
| `long_max_positions` | 3 | 最大持仓数 |
| `short_max_positions` | 3 | 最大空单数 |
| `min_cash_reserve` | 30 | 最小现金保留 |
| `time_decay_factor` | 0.1 | 时间衰减因子 |

---

## 六、发现的问题与改进建议

### 6.1 配置不一致问题

**问题**: `settings.py` 中的默认止盈值与 `TradingConfig` 中不一致

| 配置项 | settings.py | TradingConfig |
|--------|-------------|---------------|
| `TAKE_PROFIT_TREND_9_10` | 8.0% | 15.0% |
| `TAKE_PROFIT_TREND_7_8` | 6.0% | 10.0% |
| `TAKE_PROFIT_TREND_5_6` | 4.0% | 8.0% |
| `TAKE_PROFIT_TREND_DEFAULT` | 3.0% | 6.0% |

**建议**: 统一使用 `TradingConfig` 的值作为标准

### 6.2 空单止损逻辑问题

**位置**: `check_short_cover_signals()` 非动态模式

**问题**: 使用 `trend_score <= (10 - score_tier)` 的反向计算方式，与做多逻辑不一致

**当前逻辑**:
```python
if trend_score <= (10 - short_stop_loss_score_tier2):  # <= 4
    short_stop_loss = stop_loss_trend_6_7
elif trend_score <= (10 - short_stop_loss_score_tier1):  # <= 2
    short_stop_loss = stop_loss_trend_8_plus
```

**建议**: 统一使用正向的 `trend_score >= tier` 逻辑风格

### 6.3 缺失的 trend_history 追踪

**问题**: `check_sell_signals()` 中趋势变盘减仓依赖 `pos.trend_history`，但该字段未在持仓创建时初始化

**建议**: 在 `SimulatedPosition` 创建时初始化 `trend_history` 列表

---

## 七、执行流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    run_trading_cycle()                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    scan_market()                             │
│  1. 获取候选币种 (按成交额排序)                               │
│  2. 趋势分析                                                 │
│  3. 三层买入筛选                                             │
│  4. 生成 opportunities                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  generate_signals()                          │
│  1. 共振评分计算                                             │
│  2. 买入/做空信号生成                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   execute_signal()                           │
│  1. 买入/做空执行                                            │
│  2. 更新持仓                                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              check_simulation_positions()                    │
│  1. 遍历持仓检查止盈止损                                     │
│  2. 执行金字塔加仓                                           │
│  3. 执行减仓逻辑                                             │
│  4. 执行移动止损                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               check_short_positions()                        │
│  1. 遍历空单检查平仓信号                                     │
│  2. 执行平空操作                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 八、状态标记说明

### SimulatedPosition 状态字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `pyramid_layers` | int | 已加仓层数 (0-3) |
| `partial_profit_taken` | bool | 是否已部分止盈 |
| `trailing_activated` | bool | 移动止损是否激活 |
| `small_profit_reduced` | bool | 是否已小盈减仓 |
| `over_position_reduced` | bool | 是否已超仓减仓 |
| `trend_reversal_reduced` | bool | 是否已趋势变盘减仓 |
| `over_position_exemption_start` | str | 豁免期开始时间 |

---

## 九、注意事项

1. **杠杆计算**: 所有盈亏百分比都需乘以 `leverage`
2. **持仓时间保护**: 新建仓60分钟内不执行止损（除非极端行情）
3. **金字塔加仓**: 只有亏损状态才能加仓，盈利后不可加仓
4. **时区感知**: 不同交易时段仓位比例动态调整
5. **配置生效**: 修改配置后需重启或重新同步才能完全生效

---

*文档生成时间: 2026-03-23*
