# 更新日志 v4.2

## 发布日期：2026-03-21

## 概述

v4.2 版本补充了从原始 `ai_trading_bot.js` 项目缺失的核心功能，实现了完整的币市麻雀战法交易逻辑。本次更新专注于四大核心功能：时区感知、买入金额递减、智能超仓豁免和动态波段计算。

## 新增功能

### 1. 时区感知功能 ✨

**问题描述：**
原系统有时区配置但仅用于日志显示，未真正影响交易策略。

**解决方案：**
- 实现了完整的时区感知逻辑，6个时段动态调整交易参数
- 时区配置真正应用到仓位大小、持仓时间、检查频率等

**技术实现：**
- `backend/app/strategies/v42_features.py` - `TimeZoneManager` 类
- `backend/app/services/trading_engine.py` - `_get_timezone_position_size()` 方法

**影响范围：**
- 00:00-04:00：亚洲尾盘，活跃强度1星，仓位 $5-$8
- 04:00-08:00：欧美交接，活跃强度2星，仓位 $8-$10
- 08:00-12:00：亚洲早盘，活跃强度5星，仓位 $12-$15
- 12:00-16:00：亚洲午盘，活跃强度3星，仓位 $10-$12
- 16:00-20:00：欧洲早盘，活跃强度5星，仓位 $12-$15
- 20:00-24:00：美国早盘，活跃强度5星，仓位 $12-$15

### 2. 买入金额递减功能 📉

**问题描述：**
原系统缺失买入金额递减逻辑，可能导致同一币种过度集中持仓。

**解决方案：**
- 实现买入金额递减，同币种多次买入时金额逐步减少
- 递减比例：100% → 60% → 35% → 20%

**技术实现：**
- `backend/app/strategies/v42_features.py` - `DecreasingBuyManager` 类
- `backend/app/services/trading_engine.py` - `_calculate_decreasing_buy_amount()` 方法

**影响范围：**
- 降低单一币种持仓风险
- 控制仓位增长速度
- 提高资金利用率

### 3. 智能超仓豁免功能 ⏳

**问题描述：**
原系统缺失超仓豁免逻辑，可能在正常交易中误判为超仓。

**解决方案：**
- 根据当前盈亏状态给予不同时长的豁免期
- 豁免期间不会因超仓而阻止买入

**技术实现：**
- `backend/app/strategies/v42_features.py` - `ExemptionManager` 类
- `backend/app/services/trading_engine.py` - `_calculate_exemption_minutes()` 和 `_is_in_exemption_period()` 方法

**影响范围：**
- 亏损 > 1%：豁免 60 分钟
- 亏损 0-1%：豁免 45 分钟
- 已盈利：豁免 30 分钟

### 4. 动态波段计算功能 📊

**问题描述：**
原系统使用固定的止损止盈参数，无法适应不同市场环境。

**解决方案：**
- 根据波动率、市值、趋势动态调整止损止盈
- 提高策略适应性和盈利潜力

**技术实现：**
- `backend/app/strategies/v42_features.py` - `DynamicBandsCalculator` 类
- `backend/app/services/trading_engine.py` - `_calculate_dynamic_bands()` 方法

**影响范围：**
- 波动系数：0.5 ~ 2.0（波动率越高系数越大）
- 市值系数：0.6 ~ 1.2（小市值系数更小）
- 趋势系数：0.8 ~ 1.2（强趋势系数更大）
- 止损范围：-8% ~ -1%
- 止盈范围：2% ~ 15%

## 改进功能

### 1. 策略配置界面增强

**变更内容：**
- 新增 "v4.2 核心功能" 配置区域
- 4个开关：时区感知、买入金额递减、智能超仓豁免、动态波段计算

**技术实现：**
- `frontend/src/components/StrategyConfigCard.vue` - 新增 v42-features-section

### 2. API 端点扩展

**新增端点：**
```
GET  /api/v1/v42-features    # 获取 v4.2 功能配置
POST /api/v1/v42-features    # 更新 v4.2 功能配置
```

**技术实现：**
- `backend/app/api/services.py` - 新增 v4.2 功能 API

### 3. 配置文件管理

**新增文件：**
- `data/v42_features.json` - v4.2 功能配置持久化

**默认配置：**
```json
{
  "timezone_aware": true,
  "timezone_adjusted_position": true,
  "decreasing_buy_enabled": true,
  "decreasing_buy_factors": [1.0, 0.6, 0.35, 0.2],
  "over_position_exemption_enabled": true,
  "exemption_loss_high": 60,
  "exemption_loss_medium": 45,
  "exemption_profit": 30,
  "dynamic_bands_enabled": true
}
```

## 新增文件

### 后端文件

1. `backend/app/strategies/v42_features.py` - v4.2 核心功能模块
2. `backend/app/strategies/test_v42_features.py` - 功能测试套件

### 文档文件

1. `V42_FEATURES_SUMMARY.md` - v4.2 功能实现总结
2. `CHANGELOG_v42.md` - 本更新日志

### 配置文件

1. `data/v42_features.json` - v4.2 功能配置（运行时生成）

## 修改文件

### 后端文件

1. `backend/app/services/trading_engine.py`
   - 新增 `TradingConfig` 参数
   - 新增 5 个方法实现 v4.2 功能
   - 更新 `generate_signals()` 和 `run_trading_cycle()` 方法

2. `backend/app/api/services.py`
   - 新增 v4.2 功能配置 API 端点
   - 新增配置加载和保存函数

### 前端文件

1. `frontend/src/components/StrategyConfigCard.vue`
   - 新增 v42-features-section 配置区域
   - 新增 v42Features 数据模型
   - 新增加载、保存、重置方法

## 与原始项目对比

| 功能 | 原始项目 | v4.1 | v4.2 | 状态 |
|------|---------|-------|-------|------|
| 时区感知 | ✅ | ⚠️ 仅显示 | ✅ 完整实现 | ✅ 一致 |
| 买入金额递减 | ✅ | ❌ 缺失 | ✅ 完整实现 | ✅ 一致 |
| 智能超仓豁免 | ✅ | ❌ 缺失 | ✅ 完整实现 | ✅ 一致 |
| 动态波段计算 | ✅ | ❌ 缺失 | ✅ 完整实现 | ✅ 一致 |
| 波段操作 | ✅ | ✅ 已有 | ✅ 已有 | ✅ 一致 |
| 分层冷却期 | ✅ | ✅ 已有 | ✅ 已有 | ✅ 一致 |
| 做空功能 | ❌ | ✅ 新增 | ✅ 新增 | ✅ 增强 |

## 测试

### 功能测试

1. ✅ 时区感知功能测试
   - 不同时段仓位大小正确调整
   - 检查频率动态变化

2. ✅ 买入金额递减测试
   - 同币种多次买入金额递减
   - 递减比例正确

3. ✅ 智能超仓豁免测试
   - 不同盈亏状态豁免期正确
   - 豁免期内不阻止买入

4. ✅ 动态波段计算测试
   - 不同波动率/市值/趋势的参数调整正确
   - 止损止盈在合理范围内

### 集成测试

1. ✅ 前后端配置同步
2. ✅ 配置持久化
3. ✅ API 端点响应
4. ✅ 交易引擎集成

### 性能测试

1. ✅ 时区感知对交易频率的影响评估
2. ✅ 买入金额递减对风险控制的改善验证
3. ✅ 动态波段与固定参数的对比分析

## 向后兼容性

### 配置兼容性

- ✅ 所有 v4.2 功能默认启用
- ✅ 配置文件持久化，重启后保持设置
- ✅ 旧版本配置文件自动迁移

### API 兼容性

- ✅ 新增端点不影响现有 API
- ✅ 前端向后兼容，旧版本可正常运行

### 数据兼容性

- ✅ 持久化状态格式不变
- ✅ 交易日志格式兼容
- ✅ 黑名单数据格式兼容

## 升级指南

### 从 v4.1 升级到 v4.2

**步骤：**

1. **更新代码**
   ```bash
   git pull origin main
   ```

2. **更新依赖**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **启动后端**
   ```bash
   python main.py
   ```

4. **启动前端**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. **验证功能**
   - 打开策略配置页面
   - 确认 "v4.2 核心功能" 区域显示正常
   - 测试各功能开关

**注意事项：**
- 首次启动会自动创建 `data/v42_features.json` 配置文件
- 所有功能默认启用，可根据需要关闭
- 建议先在模拟模式测试

## 已知问题

### 限制

1. 时区感知仅支持北京时间（UTC+8）
2. 买入金额递减递减层级固定为 4 层
3. 超仓豁免期时长不可自定义

### 计划改进

1. 支持自定义时区配置
2. 支持自定义递减系数和层级
3. 根据币种特性动态调整豁免期
4. 引入更多动态波段因子

## 贡献者

- AI Agent - 主要开发和实现
- 原始项目 `ai_trading_bot.js` - 核心策略逻辑参考

## 许可证

与主项目保持一致

## 支持

如有问题或建议，请提交 Issue 或 Pull Request。
