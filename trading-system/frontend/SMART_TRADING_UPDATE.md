# 智能交易功能更新说明

## 更新日期
2026-03-21

## 更新内容

### 1. 前端组件 - SmartTradingCard.vue

新增智能交易配置卡片，包含：

#### 金字塔加仓配置
- **启用开关**：控制是否启用金字塔加仓
- **最大层数**：最多加仓次数（1-5层）
- **亏损触发阈值**：亏损达到此值时可加仓（-20% 至 -3%）
- **每层下跌幅度**：每层相对首开仓价的跌幅（-20% 至 -5%）
- **最低趋势评分**：趋势评分达标才加仓（5-10分）
- **加仓金额**：第1层,第2层,第3层...（逗号分隔）
- **单币最大持仓**：单一币种最大持仓占比（5-50%）

#### 智能止损配置
- **启用开关**：控制是否启用智能止损
- **强上升趋势止损**：趋势评分≥8分时的止损线（-15% 至 -5%）
- **上升趋势止损**：趋势评分6-7分时的止损线（-10% 至 -4%）
- **默认止损线**：趋势评分≤5分时的止损线（-8% 至 -3%）
- **时间保护**：新建仓后保护时间（0-120分钟）

#### 动态止盈配置
- **启用开关**：控制是否启用动态止盈
- **极强趋势止盈**：趋势评分9-10分时的止盈线（5-20%）
- **强趋势止盈**：趋势评分7-8分时的止盈线（4-15%）
- **中等趋势止盈**：趋势评分5-6分时的止盈线（3-12%）
- **默认止盈线**：趋势评分≤4分时的止盈线（2-10%）
- **部分止盈比例**：盈利到50%时卖出的比例（10-50%）

#### 功能特性
- ✅ **恢复默认**：一键恢复为示例项目默认配置
- ✅ **保存配置**：保存配置到后端
- ✅ **实时加载**：自动加载当前配置
- ✅ **开关控制**：每个功能可独立启用/禁用

### 2. 后端API - 智能交易配置

#### 新增API端点

**获取智能交易配置**
```
GET /api/v1/config/smart-trading
```

**更新智能交易配置**
```
POST /api/v1/config/smart-trading
Content-Type: application/json
Body: { ...配置对象... }
```

#### 配置文件
- 文件路径：`smart_trading_config.json`
- 自动保存和加载
- 与 `config.py` 同步

#### 默认配置（与示例项目一致）

```json
{
  "pyramid_enabled": true,
  "pyramid_max_layers": 3,
  "pyramid_drop_threshold": -5.0,
  "pyramid_drop_per_layer": -10.0,
  "pyramid_min_trend_score": 6,
  "pyramid_layer_amounts": "25.0,15.0,10.0",
  "pyramid_max_position_percent": 15.0,
  "smart_stop_loss_enabled": true,
  "stop_loss_trend_8_plus": -8.0,
  "stop_loss_trend_6_7": -6.0,
  "stop_loss_trend_default": -5.0,
  "stop_loss_time_protection_minutes": 60,
  "dynamic_take_profit_enabled": true,
  "take_profit_trend_9_10": 8.0,
  "take_profit_trend_7_8": 6.0,
  "take_profit_trend_5_6": 4.0,
  "take_profit_trend_default": 3.0,
  "partial_take_profit_percent": 0.3
}
```

### 3. 开空逻辑完善

#### 修改文件
- `backend/app/services/trading_engine.py`

#### 新增功能
- ✅ **空单持仓检查**：开空前检查是否已有该币种空单
- ✅ **避免重复开空**：同一币种不会重复开空
- ✅ **与做多对称**：与多单持仓检查逻辑一致

#### 逻辑说明
```python
# 检查当前币种是否已有空单持仓
if dry_run:
    existing_short_position = None
    for short_pos in simulation_manager.get_short_positions():
        if short_pos["coin"] == coin:
            existing_short_position = short_pos
            break

    if existing_short_position:
        logger.info(f"  ⚠️ {coin} 已有空单持仓，跳过")
        continue
```

### 4. 配置文件更新

#### 修改文件
- `backend/app/core/config.py`

#### 新增配置项
```python
# 金字塔加仓配置
PYRAMID_ENABLED: bool = True
PYRAMID_MAX_LAYERS: int = 3
PYRAMID_DROP_THRESHOLD: float = -5.0
PYRAMID_DROP_PER_LAYER: float = -10.0
PYRAMID_MIN_TREND_SCORE: int = 6
PYRAMID_LAYER_AMOUNTS: str = "25.0,15.0,10.0"
PYRAMID_MAX_POSITION_PERCENT: float = 15.0

# 智能止损配置
SMART_STOP_LOSS_ENABLED: bool = True
STOP_LOSS_TREND_8_PLUS: float = -8.0
STOP_LOSS_TREND_6_7: float = -6.0
STOP_LOSS_TREND_DEFAULT: float = -5.0
STOP_LOSS_TIME_PROTECTION_MINUTES: int = 60

# 动态止盈配置
DYNAMIC_TAKE_PROFIT_ENABLED: bool = True
TAKE_PROFIT_TREND_9_10: float = 8.0
TAKE_PROFIT_TREND_7_8: float = 6.0
TAKE_PROFIT_TREND_5_6: float = 4.0
TAKE_PROFIT_TREND_DEFAULT: float = 3.0
PARTIAL_TAKE_PROFIT_PERCENT: float = 0.3
```

## 使用说明

### 1. 前端配置流程

1. **打开智能交易配置卡片**
   - 导航到前端页面
   - 找到"智能交易配置"卡片

2. **调整配置参数**
   - 展开对应功能区域
   - 修改参数值
   - 可使用开关启用/禁用功能

3. **保存配置**
   - 点击"保存配置"按钮
   - 配置将保存到后端

4. **恢复默认**
   - 如需恢复示例项目默认配置
   - 点击"恢复默认"按钮

### 2. 金字塔加仓工作原理

1. **触发条件**
   - 亏损达到 -5%
   - 趋势评分 ≥ 6分
   - 余额充足
   - 未达最大层数

2. **加仓价格**
   - 第1层：首次开仓价 × 0.9（下跌10%）
   - 第2层：首次开仓价 × 0.8（下跌20%）
   - 第3层：首次开仓价 × 0.7（下跌30%）

3. **加仓金额**
   - 递减式加仓，降低风险
   - 第1层：$25
   - 第2层：$15
   - 第3层：$10

### 3. 智能止损工作原理

1. **趋势评分分级**
   - 评分≥8：止损线-8%
   - 评分6-7：止损线-6%
   - 评分≤5：止损线-5%

2. **时间保护**
   - 新建仓后60分钟内不止损
   - 给币种时间回调

3. **趋势保护**
   - 评分≥8且亏损时，建议加仓而非止损

### 4. 动态止盈工作原理

1. **趋势评分分级**
   - 评分9-10：止盈线8%
   - 评分7-8：止盈线6%
   - 评分5-6：止盈线4%
   - 评分≤4：止盈线3%

2. **部分止盈**
   - 盈利达到目标50%时
   - 卖出30%持仓
   - 锁定部分利润

### 5. 开空逻辑

1. **开空条件**
   - 趋势评分≤4（看跌）
   - 价格处于高位
   - RSI超买
   - 未达最大空单数

2. **持仓检查**
   - 开空前检查是否已有空单
   - 避免重复开空
   - 与多单逻辑对称

## 文件清单

### 前端文件
- ✅ `frontend/src/components/SmartTradingCard.vue` - 新增

### 后端文件
- ✅ `backend/app/services/simulation_manager.py` - 更新
- ✅ `backend/app/services/trading_engine.py` - 更新
- ✅ `backend/app/core/config.py` - 更新
- ✅ `backend/app/api/services.py` - 更新
- ✅ `backend/SMART_TRADING_FEATURES.md` - 新增

## 注意事项

1. **配置同步**
   - 前端修改配置后需要点击保存
   - 后端会同时更新配置文件和环境变量

2. **生效时机**
   - 配置修改后立即生效
   - 下一轮交易周期使用新配置

3. **风险控制**
   - 所有功能都有参数限制
   - 建议先在模拟盘测试
   - 实盘使用前充分回测

4. **性能影响**
   - 配置加载不影响性能
   - 实时计算趋势评分
   - 金字塔加仓有频率限制

## 故障排查

### 配置未生效
1. 检查是否点击了"保存配置"
2. 查看后端日志是否有错误
3. 确认 `smart_trading_config.json` 文件存在

### 金字塔加仓未触发
1. 检查趋势评分是否达标（≥6分）
2. 确认亏损是否达到阈值（-5%）
3. 检查是否已达最大层数（3层）
4. 查看余额是否充足

### 智能止损未生效
1. 确认智能止损开关已开启
2. 检查是否在时间保护期内（60分钟）
3. 查看趋势评分是否对应正确止损线

### 动态止盈未生效
1. 确认动态止盈开关已开启
2. 检查盈利是否达到对应趋势评分的止盈线
3. 查看是否已部分止盈（部分止盈只触发一次）

## 联系支持

如有问题，请查看：
- `backend/SMART_TRADING_FEATURES.md` - 功能详细说明
- 后端日志 - 错误信息
- 浏览器控制台 - 前端错误

---

**版本**：v1.0
**更新日期**：2026-03-21
**作者**：Auto AI Assistant
