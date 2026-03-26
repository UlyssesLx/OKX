# 参数配置对齐文档

## 版本信息
- 对齐日期: 2026-03-21 (最终版本)
- 对齐目标: crypto-trading-bot-master (ai_trading_bot.js)
- 当前版本: trading-system v4.4

## 核心交易参数对比

| 参数名 | crypto-trading-bot-master | trading-system | 对齐状态 |
|--------|--------------------------|----------------|----------|
| 单笔交易金额 | 32 USDT | 32 USDT | ✅ 已对齐 |
| 单币种最大持仓 | 35% | 35% | ✅ 已对齐 |
| 每日最大交易次数 | 9999 (无限制) | 9999 | ✅ 已对齐 |
| 每日最大交易量 | 1000 USDT | 1000 USDT | ✅ 已对齐 |
| 最小现金保留 | 30% | 30% | ✅ 已对齐 |
| 基础止损 | -1.0% | -1.0% | ✅ 已对齐 |
| 基础止盈 | 5% | 5% | ✅ 已对齐 |
| 买入冷却期 | 30分钟 | 30分钟 | ✅ 已对齐 |
| 舆情买入阈值 | 7 | 7 | ✅ 已对齐 |
| 舆情卖出阈值 | 3 | 3 | ✅ 已对齐 |

## 波段操作参数对比

| 参数名 | crypto-trading-bot-master | trading-system | 对齐状态 |
|--------|--------------------------|----------------|----------|
| 波段操作 | enabled | enabled | ✅ 已对齐 |
| 首次止盈 | +1.5% 减30% | +1.5% 减30% | ✅ 已对齐 |
| 二次止盈 | +3% 减50% | +3% 减50% | ✅ 已对齐 |
| 最终止盈 | +6% 清仓 | +6% 清仓 | ✅ 已对齐 |
| 回调买回 | -2% | -2% | ✅ 已对齐 |

## 分层冷却期参数对比

| 参数名 | crypto-trading-bot-master | trading-system | 对齐状态 |
|--------|--------------------------|----------------|----------|
| 分层冷却 | enabled | enabled | ✅ 已对齐 |
| 趋势10分冷却 | 15分钟 | 15分钟 | ✅ 已对齐 |
| 趋势8-9分冷却 | 20分钟 | 20分钟 | ✅ 已对齐 |
| 趋势6-7分冷却 | 30分钟 | 30分钟 | ✅ 已对齐 |

## 波动率筛选参数对比

| 参数名 | crypto-trading-bot-master | trading-system | 对齐状态 |
|--------|--------------------------|----------------|----------|
| 波动率筛选 | enabled | enabled | ✅ 已对齐 |
| 最小波动率 | 0.5% | 0.5% | ✅ 已对齐 |
| 优选波动率 | 1.5% | 1.5% | ✅ 已对齐 |

## 智能超仓豁免期参数对比

| 参数名 | crypto-trading-bot-master | trading-system | 对齐状态 |
|--------|--------------------------|----------------|----------|
| 超仓豁免 | enabled | enabled | ✅ 已对齐 |
| 亏损>1%豁免 | 60分钟 | 60分钟 | ✅ 已对齐 |
| 亏损0-1%豁免 | 45分钟 | 45分钟 | ✅ 已对齐 |
| 已盈利豁免 | 30分钟 | 30分钟 | ✅ 已对齐 |

## 抄底策略参数对比

| 参数名 | crypto-trading-bot-master | trading-system | 对齐状态 |
|--------|--------------------------|----------------|----------|
| 抄底策略 | enabled | enabled | ✅ 已对齐 |
| 最小趋势评分 | 7 | 7 | ✅ 已对齐 |
| 最小BTC趋势 | 6 | 6 | ✅ 已对齐 |

## 短线策略参数对比

| 参数名 | crypto-trading-bot-master | trading-system | 对齐状态 |
|--------|--------------------------|----------------|----------|
| MIN_TREND_SCORE | 6 | 6 | ✅ 已对齐 |
| MAX_TREND_SCORE | 10 | 10 | ✅ 已对齐 |
| RSI_MIN | 30 | 30 | ✅ 已对齐 |
| RSI_MAX | 70 | 70 | ✅ 已对齐 |
| MIN_VOLUME_RATIO | 0.8 | 0.8 | ✅ 已对齐 |
| MAX_24H_CHANGE | 8% | 8% | ✅ 已对齐 |
| MIN_24H_CHANGE | -5% | -5% | ✅ 已对齐 |
| POSITION_SIZE | 40 USDT | 40 USDT | ✅ 已对齐 |
| MAX_POSITIONS | 3 | 3 | ✅ 已对齐 |
| STOP_LOSS | -1.5% | -1.5% | ✅ 已对齐 |
| TAKE_PROFIT_1 | 1.0% | 1.0% | ✅ 已对齐 |
| TAKE_PROFIT_2 | 2.0% | 2.0% | ✅ 已对齐 |
| TIME_STOP | 48h | 48h | ✅ 已对齐 |
| MIN_VOLATILITY | 0.3 | 0.3 | ✅ 已对齐 |
| MAX_VOLATILITY | 5.0 | 5.0 | ✅ 已对齐 |

## 麻雀战法参数对比

| 参数名 | crypto-trading-bot-master | trading-system | 对齐状态 |
|--------|--------------------------|----------------|----------|
| base_capital | 287 | 287 | ✅ 已对齐 |
| daily_target | 9 | 9 | ✅ 已对齐 |
| weekly_target | 21 | 21 | ✅ 已对齐 |
| 时区配置 | 6个时段 | 6个时段 | ✅ 已对齐 |
| 止盈层级 | 3层 | 3层 | ✅ 已对齐 |
| 止损软线 | 0.3% | 0.3% | ✅ 已对齐 |
| 止损硬线 | 0.5% | 0.5% | ✅ 已对齐 |
| 时间止损 | 120分钟 | 120分钟 | ✅ 已对齐 |
| 最大持仓 | 3 | 3 | ✅ 已对齐 |
| 单币种最大 | 15 USDT | 15 USDT | ✅ 已对齐 |
| 总仓位限制 | 20% | 20% | ✅ 已对齐 |

## v4.4 新增参数（与crypto-trading-bot-master对齐）

### 时间衰减止损
| 参数名 | crypto-trading-bot-master | trading-system | 对齐状态 |
|--------|--------------------------|----------------|----------|
| timeDecayEnabled | - | true | ✅ 已实现 |
| timeDecayFactor | 0.1 | 0.1 | ✅ 已对齐 |
| maxStopLoss | -5% | -5% | ✅ 已对齐 |
| minStopLoss | -1% | -1% | ✅ 已对齐 |

### 分批止盈（波段操作）
| 参数名 | crypto-trading-bot-master | trading-system | 对齐状态 |
|--------|--------------------------|----------------|----------|
| tieredTakeProfitEnabled | - | true | ✅ 已实现 |
| takeProfitTier1Percent | 1.5% | 1.5% | ✅ 已对齐 |
| takeProfitTier1Ratio | 0.3 | 0.3 | ✅ 已对齐 |
| takeProfitTier2Percent | 3% | 3% | ✅ 已对齐 |
| takeProfitTier2Ratio | 0.5 | 0.5 | ✅ 已对齐 |
| takeProfitTier3Percent | 6% | 6% | ✅ 已对齐 |
| takeProfitTier3Ratio | 1.0 | 1.0 | ✅ 已对齐 |

### 舆情触发交易
| 参数名 | crypto-trading-bot-master | trading-system | 对齐状态 |
|--------|--------------------------|----------------|----------|
| sentimentTriggerEnabled | - | true | ✅ 已实现 |
| sentimentBuyThreshold | 7 | 7 | ✅ 已对齐 |
| sentimentSellThreshold | 3 | 3 | ✅ 已对齐 |
| sentimentMinVolumeSurge | 2.0 | 2.0 | ✅ 已对齐 |

## 风控参数对比

| 参数名 | crypto-trading-bot-master | trading-system | 对齐状态 |
|--------|--------------------------|----------------|----------|
| 单币种最大持仓 | 35% | 35% | ✅ 已对齐 |
| 最小现金保留 | 30% | 30% | ✅ 已对齐 |
| 超仓豁免 | 支持 | 支持 | ✅ 已对齐 |
| 分层冷却 | 支持 | 支持 | ✅ 已对齐 |
| 趋势变盘 | 支持 | 支持 | ✅ 已对齐 |
| 时间衰减 | 支持 | 支持 | ✅ 已对齐 |

## trading-system独有参数

以下参数为trading-system增强功能，crypto-trading-bot-master中不存在：

| 参数名 | 默认值 | 说明 |
|--------|--------|------|
| dynamic_bands_enabled | false | 动态止盈止损 |
| trend_reversal_enabled | true | 趋势变盘减仓 |
| take_profit_limit_order_enabled | true | 止盈限价单 |
| pyramid_enabled | true | 金字塔加仓 |
| timezone_aware_enabled | true | 时区感知交易 |
| database_url | sqlite | 数据库支持 |
| redis_url | 可选 | 缓存支持 |

## 配置文件结构

### crypto-trading-bot-master
```
trading-config.json          # 主配置
okx_data/config.json        # API配置
okx_data/.env.example       # 环境变量
okx_data/strategy-short-term.js  # 短线配置
okx_data/config-sparrow.js  # 麻雀战法配置
okx_data/ai_trading_bot.js  # 主交易配置
```

### trading-system
```
backend/settings.json                # 系统设置
backend/.env.example                # 环境变量
backend/app/core/config.py          # 核心配置
backend/app/services/trading_engine.py  # 交易引擎配置
backend/app/strategies/short_term.py  # 短线策略配置
backend/app/strategies/sparrow_config.py  # 麻雀战法配置
```

## API接口对比

### 配置管理API

| API端点 | 功能 | 对齐状态 |
|---------|------|----------|
| GET /api/v1/trading/risk-config | 获取风控配置 | ✅ 已实现 |
| POST /api/v1/trading/risk-config | 更新风控配置 | ✅ 已实现 |
| GET /api/v1/trading/long-config | 获取多单配置 | ✅ 已实现 |
| POST /api/v1/trading/long-config | 更新多单配置 | ✅ 已实现 |
| GET /api/v1/trading/short-config | 获取空单配置 | ✅ 已实现 |
| POST /api/v1/trading/short-config | 更新空单配置 | ✅ 已实现 |

## 总结

### ✅ 已对齐的参数
- 所有核心交易参数（100%对齐）
- 所有波段操作参数（100%对齐）
- 所有短线策略参数（100%对齐）
- 所有麻雀战法参数（100%对齐）
- 所有风控参数（100%对齐）
- v4.4新增的3组参数（时间衰减、分批止盈、舆情触发）

### 🚀 trading-system优势
- 配置热更新支持
- 统一配置管理
- 更丰富的风控功能
- 动态止盈止损
- 数据库持久化
- 前端可视化配置
- 多策略独立配置
- 更完善的参数验证

### 📊 参数一致性
- **完全一致**: 100%
- **trading-system新增**: 10+个高级功能
- **配置管理**: 更现代化、更易用

## 更新日志

### v4.4 (2026-03-21) - 最终版本
- ✅ 对齐核心交易参数与crypto-trading-bot-master的ai_trading_bot.js
- ✅ 修正单笔交易金额为32 USDT
- ✅ 修正单币种最大持仓为35%
- ✅ 修正每日最大交易次数为9999（无限制）
- ✅ 修正基础止损为-1.0%
- ✅ 修正基础止盈为5%
- ✅ 修正分批止盈参数（1.5%/3%/6%）
- ✅ 修正舆情买入阈值为7
- ✅ 添加时间衰减止损配置
- ✅ 添加波动率筛选配置
- ✅ 添加抄底策略配置
- ✅ 更新settings.json默认值
- ✅ 更新API接口暴露新参数

### v4.3 (2026-03-20)
- ✅ 添加分层冷却期配置
- ✅ 添加趋势变盘减仓配置
- ✅ 添加止盈限价单配置

### v4.2 (2026-03-19)
- ✅ 添加时区感知配置
- ✅ 添加买入金额递减配置
- ✅ 添加超仓豁免期配置

## 注意事项

### 策略参数分离

trading-system采用策略独立配置架构：
- **TradingConfig**: 通用交易引擎配置（与crypto-bot的ai_trading_bot.js对齐）
- **SparrowConfig**: 麻雀战法专用配置（与crypto-bot的config-sparrow.js对齐）
- **ShortTermConfig**: 短线策略专用配置（与crypto-bot的strategy-short-term.js对齐）
- **GridConfig**: 网格交易专用配置
- **TrendConfig**: 趋势策略专用配置

各策略参数互不干扰，根据策略类型自动选择对应配置。
