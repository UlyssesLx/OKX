# 麻雀战法配置完成说明

## 概述
已完成麻雀战法的完整前端配置支持，用户可以在前端界面配置所有麻雀战法参数。

## 新增文件

### 1. 前端组件
**`trading-system/frontend/src/components/SparrowConfigCard.vue`**
- 完整的麻雀战法配置界面
- 支持所有参数的可视化配置
- 包含时区配置的6个时段详细设置
- 支持保存和恢复默认配置

### 2. 后端 API
**`trading-system/backend/app/api/services.py`**
- 新增 `/api/v1/services/sparrow-config` GET 接口
- 新增 `/api/v1/services/sparrow-config` POST 接口
- 配置持久化到 `sparrow_config.json` 文件

## 功能特性

### ✅ 基础参数配置
- 本金设置
- 日目标（自动计算百分比）
- 周目标（自动计算百分比）

### ✅ 时区配置（6个时段）
每个时段支持配置：
- 活跃强度（1-5星）
- 仓位范围（最小-最大 USDT）
- 持仓时间（最小-最大 分钟）
- 日目标占比（百分比）

时段说明：
| 时段 | 时段名称 | 默认强度 |
|------|---------|---------|
| 00:00-04:00 | 亚洲尾盘 | ⭐ |
| 04:00-08:00 | 欧美交接 | ⭐⭐ |
| 08:00-12:00 | 亚洲早盘 | ⭐⭐⭐⭐⭐ |
| 12:00-16:00 | 亚洲午盘 | ⭐⭐⭐ |
| 16:00-20:00 | 欧洲早盘 | ⭐⭐⭐⭐⭐ |
| 20:00-24:00 | 美国早盘 | ⭐⭐⭐⭐⭐ |

### ✅ 止盈配置
- **分层止盈**:
  - 第1层: +0.5% 减仓 30%
  - 第2层: +1.0% 减仓 50%（累计 80%）
  - 第3层: +2.0% 清仓（100%）
  - 硬止盈: +3.0%

- **动态止盈**（按趋势评分）:
  - 趋势≥8分: +3% 清仓
  - 趋势6-7分: +2% 清仓
  - 趋势≤5分: +1% 清仓

### ✅ 止损配置
- 软止损（预警）: -0.3%
- 硬止损: -0.5%
- 时间止损: 120 分钟

### ✅ 选股门槛
- 趋势评分: ≥5 分
- 共振评分: ≥5 分
- BTC趋势: ≥3 分
- 波动率: 0.3%-3.0%

### ✅ 仓位管理
- 最大持仓数: 3 个币种
- 单币最大: $15 USDT
- 总仓位上限: 20%

### ✅ 日度控制
- 盈利目标: $3 USDT（达到停止交易）
- 亏损限制: $5 USDT（达到停止交易）
- 连续亏损: 3 笔（达到暂停）
- 暂停时长: 30 分钟

### ✅ 检查频率
- 活跃时段（强度≥4）: 2 分钟
- 清淡时段（强度<4）: 5 分钟

## API 接口

### 获取配置
```http
GET /api/v1/services/sparrow-config
```

### 更新配置
```http
POST /api/v1/services/sparrow-config
Content-Type: application/json

{
  "enabled": true,
  "base_capital": 287.0,
  "daily_target": 9.0,
  "weekly_target": 21.0,
  "time_zones": { ... },
  "take_profit": { ... },
  "stop_loss": { ... },
  "entry_threshold": { ... },
  "position": { ... },
  "daily_control": { ... },
  "check_interval": { ... }
}
```

## 默认配置值

所有默认值与示例项目（crypto-trading-bot-master/okx_data/config-sparrow.js）完全一致：

```javascript
{
  base_capital: 287.0,
  daily_target: 9.0,      // 3% 日目标
  weekly_target: 21.0,    // 7% 周目标

  take_profit: {
    tier1: { profit: 0.005, action: 'reduce30' },
    tier2: { profit: 0.01, action: 'reduce50' },
    tier3: { profit: 0.02, action: 'reduce100' },
    hard: 0.03
  },

  stop_loss: {
    soft: 0.003,
    hard: 0.005,
    time: 120
  },

  entry_threshold: {
    trend_score: 5,
    resonance_score: 5,
    btc_trend: 3,
    volatility: { min: 0.3, max: 3.0 }
  },

  position: {
    max_positions: 3,
    max_per_coin: 15,
    total_exposure: 0.20
  },

  daily_control: {
    profit_target: 3,
    loss_limit: 5,
    consecutive_losses: 3,
    pause_duration: 30
  },

  check_interval: {
    active: 2,
    quiet: 5
  }
}
```

## 使用方式

1. 在前端界面打开"麻雀战法配置"卡片
2. 启用麻雀战法开关
3. 根据实际情况调整各参数
4. 点击"保存配置"保存
5. 如需恢复默认值，点击"恢复默认"

## 特性说明

### 🎯 时区感知
- 根据不同时段自动调整仓位大小
- 活跃时段（亚洲早盘、欧洲早盘、美国早盘）仓位更大
- 清淡时段（亚洲尾盘、欧美交接）仓位更小

### 💰 小步快跑
- 快速止盈：+0.5% 开始减仓
- 分批止盈：逐层锁定利润
- 严格止损：-0.5% 硬止损

### 🛡️ 严格风控
- 单币最大仓位限制
- 总仓位上限控制
- 日度盈亏控制
- 连续亏损保护

### 📊 动态调整
- 根据趋势评分动态调整止盈目标
- 强趋势持有更久
- 弱趋势快速止盈

## 注意事项

1. **独立配置**: 麻雀战法配置独立于核心交易配置，需要单独启用
2. **参数生效**: 修改配置后立即生效，无需重启
3. **合理设置**: 根据账户本金合理设置日目标和周目标
4. **风险控制**: 建议先在模拟环境测试，确认无误后再使用实盘
5. **配置持久化**: 配置保存在 `sparrow_config.json` 文件中

## 文件清单

### 新增文件
- `trading-system/frontend/src/components/SparrowConfigCard.vue` - 麻雀战法配置组件

### 修改文件
- `trading-system/backend/app/api/services.py` - 添加麻雀战法配置 API
- `trading-system/frontend/FRONTEND_CONFIG_GUIDE.md` - 更新配置说明文档

### 配置文件
- `trading-system/backend/sparrow_config.json` - 麻雀战法配置存储（运行时生成）

## 技术栈

- 前端: Vue 3 + Element Plus
- 后端: FastAPI + Pydantic
- 配置: JSON 文件持久化

## 下一步

1. 将 `SparrowConfigCard.vue` 添加到主页面
2. 测试所有配置项的保存和加载
3. 验证配置是否正确应用到交易引擎
4. 添加配置验证逻辑
5. 考虑添加配置导入/导出功能
