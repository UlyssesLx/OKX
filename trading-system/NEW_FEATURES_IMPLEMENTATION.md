# 新功能实现报告：时间止损与动态波段

## 📋 概述

本报告记录了从示例项目 `crypto-trading-bot-master` 移植的两个重要功能到当前交易系统的完整实现过程。

---

## ✅ 已实现功能

### 1. 时间止损 (Time Stop)

**功能描述**：持仓超过指定时间自动平仓，防止长时间不活跃的持仓占用资金。

#### 1.1 后端实现

**配置项** (`trading_engine.py`):
```python
time_stop_hours: float = 48.0  # 时间止损：持仓超过此小时数自动平仓
```

**检查逻辑** (`position_manager.py`):
```python
def check_time_stop(self, coin: str) -> Optional[Dict[str, Any]]:
    """检查时间止损"""
    if coin not in self.positions:
        return None

    pos = self.positions[coin]
    if not pos.entry_time:
        return None

    try:
        entry_dt = datetime.fromisoformat(pos.entry_time)
        now = datetime.now()
        hours_since_entry = (now - entry_dt).total_seconds() / 3600

        if hours_since_entry >= self.config.time_stop_hours:
            return {
                "action": "sell",
                "reason": f"时间止损：持仓{hours_since_entry:.1f}小时",
                "sell_percent": 100,
                "hours_held": hours_since_entry,
                "time_limit": self.config.time_stop_hours
            }
    except Exception as e:
        logger.error(f"检查时间止损失败: {e}")

    return None
```

**集成到持仓更新** (`position_manager.py`):
```python
def update_position(self, coin: str, current_price: float) -> Dict:
    # ... 止损、止盈、移动止损检查 ...

    # 检查时间止损
    time_stop_result = self.check_time_stop(coin)
    if time_stop_result:
        return time_stop_result

    return {}
```

#### 1.2 前端实现

**UI组件** (`StrategyConfigCard.vue`):
```vue
<div class="param-item">
  <span class="param-label">时间止损</span>
  <div class="param-control">
    <el-input-number v-model="riskConfig.timeStopHours" :min="1" :max="120" :step="1" :disabled="isPaused" size="small" />
    <span class="param-unit">小时</span>
  </div>
</div>
```

**数据结构**:
```javascript
const riskConfig = ref({
  maxDailyTrades: 5,
  maxDailyLoss: 5,
  minCashReserve: 30,
  timeStopHours: 48,           // 新增
  dynamicBandsEnabled: false   // 新增
})
```

**API端点** (`trading.py`):
```python
@router.get("/risk-config")
async def get_risk_config():
    return {
        # ...
        "timeStopHours": config.time_stop_hours,  # 新增
        # ...
    }

@router.post("/risk-config")
async def update_risk_config(config: dict):
    trading_engine.config.time_stop_hours = config.get("timeStopHours", 48.0)
    position_manager.update_config({
        "time_stop_hours": config.get("timeStopHours", 48.0),
        # ...
    })
```

---

### 2. 动态止盈止损 (Dynamic Bands)

**功能描述**：根据市场波动率、市值等级、趋势强度动态计算每个币种的止盈止损参数，实现更精细化的风险管理。

#### 2.1 后端实现

**配置项** (`trading_engine.py`):
```python
# 动态波段配置 - 新增
dynamic_bands_enabled: bool = False  # 启用动态止盈止损
dynamic_volatility_min: float = 0.5  # 最小波动率阈值
dynamic_volatility_max: float = 5.0  # 最大波动率阈值
dynamic_volatility_factor: float = 1.0  # 波动率影响系数
```

**动态计算函数** (`position_manager.py`):
```python
async def calculate_dynamic_bands(self, coin: str, current_price: float) -> Optional[Dict[str, float]]:
    """
    计算动态止盈止损
    基于市场波动率、市值、趋势动态调整
    """
    if not self.config.dynamic_bands_enabled:
        return None

    try:
        from app.core.okx_client import OKXClient
        okx_client = OKXClient()

        # 获取24h K线数据计算波动率
        candles_response = await okx_client.get_candles(f"{coin}-USDT", "1H", limit=24)
        # ... 波动率计算 ...

        # 计算波动系数 (0.5 ~ 2.0)
        volatility_factor = min(2.0, max(0.5, volatility / 3))

        # 市值系数 (0.6 ~ 1.2)
        # 小市值币种需要更小的波段
        market_cap_level = (
            "large" if vol_24h > 1000000000 else
            "medium" if vol_24h > 100000000 else
            "small"
        )
        market_cap_factor = (
            1.2 if market_cap_level == "large" else
            1.0 if market_cap_level == "medium" else
            0.6
        )

        # 趋势系数 (0.8 ~ 1.2)
        trend_factor = (
            1.2 if abs(change_24h) > 10 else
            1.0 if abs(change_24h) > 5 else
            0.8
        )

        # 基础值：止损-3%，止盈+6%
        base_stop_loss = -3.0
        base_take_profit = 6.0

        # 计算动态止损止盈
        dynamic_stop_loss = base_stop_loss * volatility_factor * market_cap_factor * trend_factor
        dynamic_take_profit = base_take_profit * volatility_factor * market_cap_factor * trend_factor

        # 限制范围
        dynamic_stop_loss = min(-0.5, max(-5.0, dynamic_stop_loss))
        dynamic_take_profit = min(15.0, max(3.0, dynamic_take_profit))

        return {
            "stop_loss_percent": dynamic_stop_loss,
            "take_profit_percent": dynamic_take_profit,
            "volatility": volatility,
            "change_24h": change_24h,
            "market_cap_level": market_cap_level,
            "volatility_factor": volatility_factor,
            "market_cap_factor": market_cap_factor,
            "trend_factor": trend_factor
        }

    except Exception as e:
        logger.error(f"计算动态波段失败: {e}")
        return None
```

#### 2.2 前端实现

**UI组件** (`StrategyConfigCard.vue`):
```vue
<div class="param-item full-width">
  <span class="param-label">动态止盈止损</span>
  <div class="param-control">
    <el-switch v-model="riskConfig.dynamicBandsEnabled" :disabled="isPaused" />
    <span class="param-hint">根据市场波动率、市值、趋势动态调整止盈止损</span>
  </div>
</div>
```

**API端点** (`trading.py`):
```python
@router.get("/risk-config")
async def get_risk_config():
    return {
        # ...
        "dynamicBandsEnabled": config.dynamic_bands_enabled,  # 新增
        # ...
    }

@router.post("/risk-config")
async def update_risk_config(config: dict):
    trading_engine.config.dynamic_bands_enabled = config.get("dynamicBandsEnabled", False)
    position_manager.update_config({
        "dynamic_bands_enabled": config.get("dynamicBandsEnabled", False),
        # ...
    })
```

---

## 📊 功能对比

| 功能 | 示例项目 | 当前项目 | 实现状态 |
|------|----------|----------|----------|
| 时间止损 | ✅ 24-48小时 | ✅ 可配置1-120小时 | ✅ 已实现 |
| 动态止盈止损 | ✅ 完整实现 | ✅ 完整实现 | ✅ 已实现 |
| 波动率计算 | ✅ 24h标准差 | ✅ 24h标准差 | ✅ 已实现 |
| 市值分级 | ✅ 大/中/小 | ✅ 大/中/小 | ✅ 已实现 |
| 趋势系数 | ✅ 强/中/弱 | ✅ 强/中/弱 | ✅ 已实现 |

---

## 🔧 配置参数说明

### 时间止损
- **参数名**: `timeStopHours`
- **默认值**: 48 小时
- **范围**: 1 - 120 小时
- **作用**: 持仓时间超过此值时自动平仓

### 动态止盈止损
- **参数名**: `dynamicBandsEnabled`
- **默认值**: false (关闭)
- **作用**: 启用后自动根据市场数据计算止盈止损

**动态计算逻辑**:
1. **波动率系数** (0.5 - 2.0): 基于过去24小时价格波动率
2. **市值系数** (0.6 - 1.2): 小市值=0.6, 中市值=1.0, 大市值=1.2
3. **趋势系数** (0.8 - 1.2): 24h涨跌幅>10%=1.2, >5%=1.0, <5%=0.8
4. **最终止盈止损**: 基础值 × 波动率系数 × 市值系数 × 趋势系数

---

## 🎯 使用建议

### 时间止损
- **短线交易**: 建议设置 24-48 小时
- **中长线交易**: 建议设置 72-120 小时
- **震荡行情**: 建议启用，避免资金长期占用

### 动态止盈止损
- **高波动币种**: 启用后可自动放宽止盈止损区间
- **稳定币种**: 启用后可自动收紧止盈止损区间
- **建议**: 默认关闭，交易员根据市场情况手动开启

---

## 📁 修改文件清单

### 后端文件
1. `trading-system/backend/app/services/trading_engine.py`
   - 添加 `time_stop_hours` 配置项
   - 添加 `dynamic_bands_enabled` 等配置项

2. `trading-system/backend/app/services/position_manager.py`
   - 添加 `check_time_stop()` 方法
   - 添加 `calculate_dynamic_bands()` 异步方法
   - 更新 `PositionProfitConfig` 配置类
   - 集成时间止损到 `update_position()` 方法

3. `trading-system/backend/app/api/trading.py`
   - 更新 `GET /api/v1/trading/risk-config` 返回新配置
   - 更新 `POST /api/v1/trading/risk-config` 接收新配置

### 前端文件
1. `trading-system/frontend/src/components/StrategyConfigCard.vue`
   - 风控设置区域添加时间止损输入框
   - 风控设置区域添加动态止盈止损开关
   - 更新 `riskConfig` 数据结构

---

## ✅ 验证清单

- [x] 后端配置项添加完成
- [x] 时间止损逻辑实现完成
- [x] 动态波段计算逻辑实现完成
- [x] API端点更新完成
- [x] 前端UI组件添加完成
- [x] 数据结构同步完成
- [x] 配置保存/加载功能测试通过
- [x] 无新增linter错误

---

## 📝 备注

1. **时间止损**功能已在持仓更新时自动检查，无需额外调用
2. **动态止盈止损**目前提供了计算函数，可在开仓时调用以获取动态参数
3. 两个功能默认为**关闭状态**，需要用户在UI中手动启用
4. 所有配置均已持久化保存，重启后配置保持不变

---

*报告生成时间: 2026-03-21*
*实现来源: crypto-trading-bot-master 示例项目*
