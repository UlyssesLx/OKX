<template>
  <div class="sparrow-config-card card">
    <div class="card-header">
      <div class="header-left">
        <div class="card-icon gradient-icon green">
          <el-icon :size="20"><Guide /></el-icon>
        </div>
        <div class="title-section">
          <div class="card-title">麻雀战法配置</div>
          <div class="card-subtitle">时区感知 + 小步快跑 + 严格风控</div>
        </div>
      </div>
      <div class="header-actions">
        <el-switch v-model="config.enabled" @change="updateConfig" size="default" />
      </div>
    </div>

    <!-- 基础参数 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">📊 基础参数</div>
      <div class="config-grid">
        <div class="param-item">
          <span class="param-label">本金</span>
          <div class="param-control">
            <el-input-number v-model="config.base_capital" :min="100" :max="10000" size="small" />
            <span class="param-unit">USDT</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">日目标</span>
          <div class="param-control">
            <el-input-number v-model="config.daily_target" :min="1" :max="50" size="small" />
            <span class="param-unit">USDT</span>
            <span class="param-hint">{{ ((config.daily_target / config.base_capital) * 100).toFixed(1) }}%</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">周目标</span>
          <div class="param-control">
            <el-input-number v-model="config.weekly_target" :min="5" :max="200" size="small" />
            <span class="param-unit">USDT</span>
            <span class="param-hint">{{ ((config.weekly_target / config.base_capital) * 100).toFixed(1) }}%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 时区配置 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">🌍 时区配置</div>
      <div class="timezone-config">
        <div v-for="(tz, key) in config.time_zones" :key="key" class="timezone-item">
          <div class="timezone-header">
            <span class="timezone-name">{{ getTimeZoneName(key) }}</span>
            <div class="intensity-indicator">
              <span
                v-for="i in 5"
                :key="i"
                class="star"
                :class="{ active: i <= tz.intensity }"
              >⭐</span>
            </div>
          </div>
          <div class="timezone-params">
            <div class="param-row">
              <span class="label">仓位范围</span>
              <div class="control-group">
                <el-input-number v-model="tz.position_size.min" :min="5" :max="20" size="small" @change="updateConfig" />
                <span>-</span>
                <el-input-number v-model="tz.position_size.max" :min="10" :max="30" size="small" @change="updateConfig" />
                <span class="unit">USDT</span>
              </div>
            </div>
            <div class="param-row">
              <span class="label">持仓时间</span>
              <div class="control-group">
                <el-input-number v-model="tz.hold_time.min" :min="5" :max="30" size="small" @change="updateConfig" />
                <span>-</span>
                <el-input-number v-model="tz.hold_time.max" :min="10" :max="120" size="small" @change="updateConfig" />
                <span class="unit">分钟</span>
              </div>
            </div>
            <div class="param-row">
              <span class="label">日目标占比</span>
              <div class="control-group">
                <el-slider v-model="tz.daily_quota" :min="0.05" :max="0.50" :step="0.05" :format-tooltip="(v) => `${(v * 100).toFixed(0)}%`" @change="updateConfig" style="width: 150px" />
                <span class="unit">{{ (tz.daily_quota * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 止盈配置 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">💰 止盈配置</div>
      <div class="config-grid">
        <div class="param-item">
          <span class="param-label">第1层止盈</span>
          <div class="param-control">
            <el-input-number v-model="config.take_profit.tier1.profit" :min="0.002" :max="0.02" :step="0.001" :precision="3" size="small" @change="updateConfig" />
            <span class="param-unit">{{ (config.take_profit.tier1.profit * 100).toFixed(2) }}%</span>
            <span class="param-hint">{{ getReducePercent(config.take_profit.tier1.action) }}</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">第2层止盈</span>
          <div class="param-control">
            <el-input-number v-model="config.take_profit.tier2.profit" :min="0.005" :max="0.03" :step="0.001" :precision="3" size="small" @change="updateConfig" />
            <span class="param-unit">{{ (config.take_profit.tier2.profit * 100).toFixed(2) }}%</span>
            <span class="param-hint">{{ getReducePercent(config.take_profit.tier2.action) }}</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">第3层止盈</span>
          <div class="param-control">
            <el-input-number v-model="config.take_profit.tier3.profit" :min="0.01" :max="0.05" :step="0.001" :precision="3" size="small" @change="updateConfig" />
            <span class="param-unit">{{ (config.take_profit.tier3.profit * 100).toFixed(2) }}%</span>
            <span class="param-hint">{{ getReducePercent(config.take_profit.tier3.action) }}</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">硬止盈上限</span>
          <div class="param-control">
            <el-input-number v-model="config.take_profit.hard" :min="0.01" :max="0.10" :step="0.005" :precision="3" size="small" @change="updateConfig" />
            <span class="param-unit">{{ (config.take_profit.hard * 100).toFixed(2) }}%</span>
          </div>
        </div>
      </div>

      <!-- 动态止盈 -->
      <div class="sub-section">
        <div class="sub-section-title">动态止盈（按趋势评分）</div>
        <div class="config-grid">
          <div class="param-item">
            <span class="param-label">趋势≥8分</span>
            <div class="param-control">
              <el-input-number v-model="config.take_profit.dynamic.trend8plus.profit" :min="0.01" :max="0.10" :step="0.005" :precision="3" size="small" @change="updateConfig" />
              <span class="param-unit">{{ (config.take_profit.dynamic.trend8plus.profit * 100).toFixed(2) }}%</span>
            </div>
          </div>
          <div class="param-item">
            <span class="param-label">趋势6-7分</span>
            <div class="param-control">
              <el-input-number v-model="config.take_profit.dynamic.trend6to7.profit" :min="0.01" :max="0.08" :step="0.005" :precision="3" size="small" @change="updateConfig" />
              <span class="param-unit">{{ (config.take_profit.dynamic.trend6to7.profit * 100).toFixed(2) }}%</span>
            </div>
          </div>
          <div class="param-item">
            <span class="param-label">趋势≤5分</span>
            <div class="param-control">
              <el-input-number v-model="config.take_profit.dynamic.trend5minus.profit" :min="0.005" :max="0.05" :step="0.005" :precision="3" size="small" @change="updateConfig" />
              <span class="param-unit">{{ (config.take_profit.dynamic.trend5minus.profit * 100).toFixed(2) }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 止损配置 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">🛡️ 止损配置</div>
      <div class="config-grid">
        <div class="param-item">
        
          <span class="param-label">软止损（预警）</span>
          <div class="param-control">
            <el-input-number v-model="config.stop_loss.soft" :min="0.001" :max="0.01" :step="0.001" :precision="3" size="small" @change="updateConfig" />
            <span class="param-unit">{{ (config.stop_loss.soft * 100).toFixed(2) }}%</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">硬止损</span>
          <div class="param-control">
            <el-input-number v-model="config.stop_loss.hard" :min="0.002" :max="0.02" :step="0.001" :precision="3" size="small" @change="updateConfig" />
            <span class="param-unit">{{ (config.stop_loss.hard * 100).toFixed(2) }}%</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">时间止损</span>
          <div class="param-control">
            <el-input-number v-model="config.stop_loss.time" :min="30" :max="300" :step="10" size="small" @change="updateConfig" />
            <span class="param-unit">分钟</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 选股门槛 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">🎯 选股门槛</div>
      <div class="config-grid">
        <div class="param-item">
          <span class="param-label">趋势评分</span>
          <div class="param-control">
            <el-input-number v-model="config.entry_threshold.trend_score" :min="3" :max="10" size="small" @change="updateConfig" />
            <span class="param-unit">/10</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">共振评分</span>
          <div class="param-control">
            <el-input-number v-model="config.entry_threshold.resonance_score" :min="3" :max="10" size="small" @change="updateConfig" />
            <span class="param-unit">/10</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">BTC趋势</span>
          <div class="param-control">
            <el-input-number v-model="config.entry_threshold.btc_trend" :min="1" :max="10" size="small" @change="updateConfig" />
            <span class="param-unit">/10</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">波动率范围</span>
          <div class="param-control">
            <el-input-number v-model="config.entry_threshold.volatility.min" :min="0.1" :max="1" :step="0.1" :precision="1" size="small" @change="updateConfig" />
            <span>-</span>
            <el-input-number v-model="config.entry_threshold.volatility.max" :min="2" :max="10" :step="0.5" :precision="1" size="small" @change="updateConfig" />
            <span class="param-unit">%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 仓位管理 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">📦 仓位管理</div>
      <div class="config-grid">
        <div class="param-item">
          <span class="param-label">最大多单数</span>
          <div class="param-control">
            <el-input-number v-model="config.position.max_positions" :min="1" :max="5" size="small" @change="updateConfig" />
            <span class="param-unit">币种</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">最大空单数</span>
          <div class="param-control">
            <el-input-number v-model="config.short_decreasing.short_max_positions" :min="1" :max="5" size="small" @change="updateConfig" />
            <span class="param-unit">币种</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">单币最大</span>
          <div class="param-control">
            <el-input-number v-model="config.position.max_per_coin" :min="5" :max="50" size="small" @change="updateConfig" />
            <span class="param-unit">USDT</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">总仓位上限</span>
          <div class="param-control">
            <el-slider v-model="config.position.total_exposure" :min="0.10" :max="0.50" :step="0.05" :format-tooltip="(v) => `${(v * 100).toFixed(0)}%`" @change="updateConfig" style="width: 150px" />
            <span class="param-unit">{{ (config.position.total_exposure * 100).toFixed(0) }}%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 日度控制 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">📅 日度控制</div>
      <div class="config-grid">
        <div class="param-item">
          <span class="param-label">盈利目标</span>
          <div class="param-control">
            <el-input-number v-model="config.daily_control.profit_target" :min="1" :max="20" size="small" @change="updateConfig" />
            <span class="param-unit">USDT</span>
            <span class="param-hint">达到停止交易</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">亏损限制</span>
          <div class="param-control">
            <el-input-number v-model="config.daily_control.loss_limit" :min="3" :max="30" size="small" @change="updateConfig" />
            <span class="param-unit">USDT</span>
            <span class="param-hint">达到停止交易</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">连续亏损</span>
          <div class="param-control">
            <el-input-number v-model="config.daily_control.consecutive_losses" :min="2" :max="10" size="small" @change="updateConfig" />
            <span class="param-unit">笔</span>
            <span class="param-hint">达到暂停</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">暂停时长</span>
          <div class="param-control">
            <el-input-number v-model="config.daily_control.pause_duration" :min="10" :max="120" size="small" @change="updateConfig" />
            <span class="param-unit">分钟</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 检查频率 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">⏱️ 检查频率</div>
      <div class="config-grid">
        <div class="param-item">
          <span class="param-label">活跃时段</span>
          <div class="param-control">
            <el-input-number v-model="config.check_interval.active" :min="1" :max="5" size="small" @change="updateConfig" />
            <span class="param-unit">分钟</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">清淡时段</span>
          <div class="param-control">
            <el-input-number v-model="config.check_interval.quiet" :min="3" :max="10" size="small" @change="updateConfig" />
            <span class="param-unit">分钟</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 买入条件配置 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">📈 买入条件</div>
      <div class="config-grid">
        <div class="param-item">
          <span class="param-label">舆情门槛</span>
          <div class="param-control">
            <el-input-number v-model="config.buy_conditions.sentiment_threshold" :min="1" :max="10" size="small" @change="updateConfig" />
            <span class="param-unit">/10</span>
            <span class="param-hint">≥此分才买入</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">最小趋势评分</span>
          <div class="param-control">
            <el-input-number v-model="config.buy_conditions.long_min_trend_score" :min="1" :max="10" size="small" @change="updateConfig" />
            <span class="param-unit">/10</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">RSI超卖下限</span>
          <div class="param-control">
            <el-input-number v-model="config.buy_conditions.long_rsi_oversold_min" :min="10" :max="40" size="small" @change="updateConfig" />
            <span class="param-unit">≥ 此值</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">RSI超卖上限</span>
          <div class="param-control">
            <el-input-number v-model="config.buy_conditions.long_rsi_oversold_max" :min="30" :max="60" size="small" @change="updateConfig" />
            <span class="param-unit">≤ 此值超卖</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">最小量比</span>
          <div class="param-control">
            <el-input-number v-model="config.buy_conditions.long_min_volume_ratio" :min="0.5" :max="3" :step="0.1" :precision="1" size="small" @change="updateConfig" />
            <span class="param-unit">x</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">最大回调%</span>
          <div class="param-control">
            <el-input-number v-model="config.buy_conditions.long_max_pullback_percent" :min="1" :max="20" size="small" @change="updateConfig" />
            <span class="param-unit">%</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">最小回调%</span>
          <div class="param-control">
            <el-input-number v-model="config.buy_conditions.long_min_pullback_percent" :min="-30" :max="-5" size="small" @change="updateConfig" />
            <span class="param-unit">%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 冷却期配置 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">⏳ 冷却期配置</div>
      <div class="config-grid">
        <div class="param-item">
          <span class="param-label">启用分层冷却期</span>
          <div class="param-control">
            <el-switch v-model="config.cooldown.tiered_cooldown_enabled" @change="updateConfig" />
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">趋势10分冷却</span>
          <div class="param-control">
            <el-input-number v-model="config.cooldown.cooldown_trend_10" :min="5" :max="30" size="small" @change="updateConfig" />
            <span class="param-unit">分钟</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">趋势8-9分冷却</span>
          <div class="param-control">
            <el-input-number v-model="config.cooldown.cooldown_trend_8_9" :min="10" :max="45" size="small" @change="updateConfig" />
            <span class="param-unit">分钟</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">趋势6-7分冷却</span>
          <div class="param-control">
            <el-input-number v-model="config.cooldown.cooldown_trend_6_7" :min="15" :max="60" size="small" @change="updateConfig" />
            <span class="param-unit">分钟</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 买入金额递减 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">📉 买入金额递减</div>
      <div class="config-grid">
        <div class="param-item">
          <span class="param-label">启用递减</span>
          <div class="param-control">
            <el-switch v-model="config.decreasing_buy.decreasing_buy_enabled" @change="updateConfig" />
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">第1次买入</span>
          <div class="param-control">
            <el-input-number v-model="config.decreasing_buy.factor_1" :min="0.1" :max="1" :step="0.1" :precision="1" size="small" @change="updateConfig" />
            <span class="param-unit">x 基础金额</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">第2次买入</span>
          <div class="param-control">
            <el-input-number v-model="config.decreasing_buy.factor_2" :min="0.1" :max="1" :step="0.1" :precision="1" size="small" @change="updateConfig" />
            <span class="param-unit">x 基础金额</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">第3次买入</span>
          <div class="param-control">
            <el-input-number v-model="config.decreasing_buy.factor_3" :min="0.1" :max="1" :step="0.1" :precision="1" size="small" @change="updateConfig" />
            <span class="param-unit">x 基础金额</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">第4次+买入</span>
          <div class="param-control">
            <el-input-number v-model="config.decreasing_buy.factor_4" :min="0.1" :max="1" :step="0.1" :precision="1" size="small" @change="updateConfig" />
            <span class="param-unit">x 基础金额</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 回调加仓配置 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">🔄 回调加仓</div>
      <div class="config-grid">
        <div class="param-item">
          <span class="param-label">回调阈值</span>
          <div class="param-control">
            <el-input-number v-model="config.pullback.pullback_buy_threshold" :min="0.90" :max="0.99" :step="0.01" :precision="2" size="small" @change="updateConfig" />
            <span class="param-unit">x 减仓价</span>
            <span class="param-hint">97%=回调3%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 现金保留 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">💰 现金保留</div>
      <div class="config-grid">
        <div class="param-item">
          <span class="param-label">最小现金保留</span>
          <div class="param-control">
            <el-input-number v-model="config.cash_reserve.min_cash_reserve" :min="10" :max="50" size="small" @change="updateConfig" />
            <span class="param-unit">%</span>
            <span class="param-hint">强制保留</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 超仓豁免期 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">🛡️ 超仓豁免期</div>
      <div class="config-grid">
        <div class="param-item">
          <span class="param-label">启用豁免期</span>
          <div class="param-control">
            <el-switch v-model="config.exemption.over_position_exemption_enabled" @change="updateConfig" />
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">亏损>1%豁免</span>
          <div class="param-control">
            <el-input-number v-model="config.exemption.exemption_loss_high" :min="30" :max="120" size="small" @change="updateConfig" />
            <span class="param-unit">分钟</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">亏损0-1%豁免</span>
          <div class="param-control">
            <el-input-number v-model="config.exemption.exemption_loss_medium" :min="20" :max="90" size="small" @change="updateConfig" />
            <span class="param-unit">分钟</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">已盈利豁免</span>
          <div class="param-control">
            <el-input-number v-model="config.exemption.exemption_profit" :min="10" :max="60" size="small" @change="updateConfig" />
            <span class="param-unit">分钟</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 波动率筛选 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">📊 波动率筛选</div>
      <div class="config-grid">
        <div class="param-item">
          <span class="param-label">启用筛选</span>
          <div class="param-control">
            <el-switch v-model="config.volatility.volatility_filter_enabled" @change="updateConfig" />
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">最小波动率</span>
          <div class="param-control">
            <el-input-number v-model="config.volatility.volatility_min" :min="0.1" :max="2" :step="0.1" :precision="1" size="small" @change="updateConfig" />
            <span class="param-unit">%</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">优选波动率</span>
          <div class="param-control">
            <el-input-number v-model="config.volatility.volatility_preferred" :min="0.5" :max="5" :step="0.5" :precision="1" size="small" @change="updateConfig" />
            <span class="param-unit">%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 做空条件配置 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">📉 做空条件</div>
      <div class="config-grid">
        <div class="param-item">
          <span class="param-label">最小看跌评分</span>
          <div class="param-control">
            <el-input-number v-model="config.short_conditions.short_min_bearish_score" :min="5" :max="10" size="small" @change="updateConfig" />
            <span class="param-unit">/10</span>
            <span class="param-hint">≥此值看跌</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">趋势评分下限</span>
          <div class="param-control">
            <el-input-number v-model="config.short_conditions.short_min_trend_score" :min="0" :max="4" size="small" @change="updateConfig" />
            <span class="param-unit">/10</span>
            <span class="param-hint">≥此值考虑做空</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">趋势评分上限</span>
          <div class="param-control">
            <el-input-number v-model="config.short_conditions.short_max_trend_score" :min="1" :max="6" size="small" @change="updateConfig" />
            <span class="param-unit">/10</span>
            <span class="param-hint">≤此值可做空</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">BTC趋势上限</span>
          <div class="param-control">
            <el-input-number v-model="config.short_conditions.short_max_btc_trend" :min="1" :max="6" size="small" @change="updateConfig" />
            <span class="param-unit">/10</span>
            <span class="param-hint">大盘弱势</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">ETH趋势上限</span>
          <div class="param-control">
            <el-input-number v-model="config.short_conditions.short_max_eth_trend" :min="1" :max="6" size="small" @change="updateConfig" />
            <span class="param-unit">/10</span>
            <span class="param-hint">大盘弱势</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">最小24h涨幅</span>
          <div class="param-control">
            <el-input-number v-model="config.short_conditions.short_min_change_24h" :min="1" :max="10" size="small" @change="updateConfig" />
            <span class="param-unit">%</span>
            <span class="param-hint">高位</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">最大24h涨幅</span>
          <div class="param-control">
            <el-input-number v-model="config.short_conditions.short_max_change_24h" :min="10" :max="30" size="small" @change="updateConfig" />
            <span class="param-unit">%</span>
            <span class="param-hint">不追空</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">RSI超买下限</span>
          <div class="param-control">
            <el-input-number v-model="config.short_conditions.short_rsi_overbought_min" :min="50" :max="80" size="small" @change="updateConfig" />
            <span class="param-unit">≥ 此值超买</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">RSI超买上限</span>
          <div class="param-control">
            <el-input-number v-model="config.short_conditions.short_rsi_overbought_max" :min="60" :max="95" size="small" @change="updateConfig" />
            <span class="param-unit">≤ 此值</span>
            <span class="param-hint">避免反转</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">最小量比</span>
          <div class="param-control">
            <el-input-number v-model="config.short_conditions.short_min_volume_ratio" :min="0.5" :max="3" :step="0.1" :precision="1" size="small" @change="updateConfig" />
            <span class="param-unit">x</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">舆情做空阈值</span>
          <div class="param-control">
            <el-input-number v-model="config.short_conditions.short_sentiment_threshold" :min="1" :max="5" size="small" @change="updateConfig" />
            <span class="param-unit">/10</span>
            <span class="param-hint">< 此值做空</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 做空冷却期配置 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">⏳ 做空冷却期</div>
      <div class="config-grid">
        <div class="param-item">
          <span class="param-label">趋势1分冷却</span>
          <div class="param-control">
            <el-input-number v-model="config.short_cooldown.short_cooldown_trend_1" :min="5" :max="30" size="small" @change="updateConfig" />
            <span class="param-unit">分钟</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">趋势2-3分冷却</span>
          <div class="param-control">
            <el-input-number v-model="config.short_cooldown.short_cooldown_trend_2_3" :min="10" :max="45" size="small" @change="updateConfig" />
            <span class="param-unit">分钟</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">趋势4分冷却</span>
          <div class="param-control">
            <el-input-number v-model="config.short_cooldown.short_cooldown_trend_4" :min="15" :max="60" size="small" @change="updateConfig" />
            <span class="param-unit">分钟</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 做空金额递减 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">📉 做空金额递减</div>
      <div class="config-grid">
        <div class="param-item">
          <span class="param-label">启用递减</span>
          <div class="param-control">
            <el-switch v-model="config.short_decreasing.short_decreasing_buy_enabled" @change="updateConfig" />
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">仓位比例</span>
          <div class="param-control">
            <el-input-number v-model="config.short_decreasing.short_position_ratio" :min="0.5" :max="1.5" :step="0.1" :precision="1" size="small" @change="updateConfig" />
            <span class="param-unit">x 基础金额</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 做空止损止盈 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">🎯 做空止损止盈</div>
      <div class="config-grid">
        <div class="param-item">
          <span class="param-label">止损百分比</span>
          <div class="param-control">
            <el-input-number v-model="config.short_risk.short_stop_loss_percent" :min="1" :max="5" :step="0.5" :precision="1" size="small" @change="updateConfig" />
            <span class="param-unit">%</span>
            <span class="param-hint">价格上涨</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">止盈百分比</span>
          <div class="param-control">
            <el-input-number v-model="config.short_risk.short_take_profit_percent" :min="1" :max="10" :step="0.5" :precision="1" size="small" @change="updateConfig" />
            <span class="param-unit">%</span>
            <span class="param-hint">价格下跌</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">反弹加空阈值</span>
          <div class="param-control">
            <el-input-number v-model="config.short_risk.short_pullback_threshold" :min="1.01" :max="1.10" :step="0.01" :precision="2" size="small" @change="updateConfig" />
            <span class="param-unit">x 减空价</span>
            <span class="param-hint">103%=反弹3%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 做空豁免期 -->
    <div class="config-section" v-if="config.enabled">
      <div class="section-title">🛡️ 做空豁免期</div>
      <div class="config-grid">
        <div class="param-item">
          <span class="param-label">启用豁免期</span>
          <div class="param-control">
            <el-switch v-model="config.short_exemption.short_exemption_enabled" @change="updateConfig" />
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">亏损>1%豁免</span>
          <div class="param-control">
            <el-input-number v-model="config.short_exemption.short_exemption_loss_high" :min="30" :max="120" size="small" @change="updateConfig" />
            <span class="param-unit">分钟</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">亏损0-1%豁免</span>
          <div class="param-control">
            <el-input-number v-model="config.short_exemption.short_exemption_loss_medium" :min="20" :max="90" size="small" @change="updateConfig" />
            <span class="param-unit">分钟</span>
          </div>
        </div>
        <div class="param-item">
          <span class="param-label">已盈利豁免</span>
          <div class="param-control">
            <el-input-number v-model="config.short_exemption.short_exemption_profit" :min="10" :max="60" size="small" @change="updateConfig" />
            <span class="param-unit">分钟</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部按钮 -->
    <div class="actions">
      <el-button type="primary" @click="saveConfig" :disabled="!config.enabled">
        保存配置
      </el-button>
      <el-button @click="resetConfig">
        恢复默认
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Guide } from '@element-plus/icons-vue'

const DEFAULT_CONFIG = {
  enabled: false,
  base_capital: 287.0,
  daily_target: 9.0,
  weekly_target: 21.0,
  time_zones: {
    '00:00-04:00': {
      intensity: 1,
      position_size: { min: 5, max: 8 },
      hold_time: { min: 30, max: 60 },
      daily_quota: 0.10
    },
    '04:00-08:00': {
      intensity: 2,
      position_size: { min: 8, max: 10 },
      hold_time: { min: 20, max: 40 },
      daily_quota: 0.15
    },
    '08:00-12:00': {
      intensity: 5,
      position_size: { min: 12, max: 15 },
      hold_time: { min: 15, max: 60 },
      daily_quota: 0.30
    },
    '12:00-16:00': {
      intensity: 3,
      position_size: { min: 10, max: 12 },
      hold_time: { min: 20, max: 50 },
      daily_quota: 0.20
    },
    '16:00-20:00': {
      intensity: 5,
      position_size: { min: 12, max: 15 },
      hold_time: { min: 15, max: 60 },
      daily_quota: 0.30
    },
    '20:00-24:00': {
      intensity: 5,
      position_size: { min: 12, max: 15 },
      hold_time: { min: 10, max: 45 },
      daily_quota: 0.40
    }
  },
  take_profit: {
    tier1: { profit: 0.005, action: 'reduce30' },
    tier2: { profit: 0.01, action: 'reduce50' },
    tier3: { profit: 0.02, action: 'reduce100' },
    hard: 0.03,
    dynamic: {
      trend8plus: { profit: 0.03, action: 'reduce100' },
      trend6to7: { profit: 0.02, action: 'reduce100' },
      trend5minus: { profit: 0.01, action: 'reduce100' }
    }
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
  },
  buy_conditions: {
    sentiment_threshold: 7,
    long_min_trend_score: 5,
    long_rsi_oversold_min: 20,
    long_rsi_oversold_max: 40,
    long_min_volume_ratio: 1.2,
    long_max_pullback_percent: 8,
    long_min_pullback_percent: -15
  },
  cooldown: {
    tiered_cooldown_enabled: true,
    cooldown_trend_10: 15,
    cooldown_trend_8_9: 20,
    cooldown_trend_6_7: 30
  },
  decreasing_buy: {
    decreasing_buy_enabled: true,
    factor_1: 1.0,
    factor_2: 0.6,
    factor_3: 0.35,
    factor_4: 0.2
  },
  pullback: {
    pullback_buy_threshold: 0.97
  },
  cash_reserve: {
    min_cash_reserve: 30
  },
  exemption: {
    over_position_exemption_enabled: true,
    exemption_loss_high: 60,
    exemption_loss_medium: 45,
    exemption_profit: 30
  },
  volatility: {
    volatility_filter_enabled: true,
    volatility_min: 0.5,
    volatility_preferred: 1.5
  },
  short_conditions: {
    short_min_bearish_score: 7,
    short_min_trend_score: 0,
    short_max_trend_score: 4,
    short_max_btc_trend: 4,
    short_max_eth_trend: 4,
    short_min_change_24h: 3,
    short_max_change_24h: 15,
    short_rsi_overbought_min: 60,
    short_rsi_overbought_max: 80,
    short_min_volume_ratio: 1.2,
    short_sentiment_threshold: 3
  },
  short_cooldown: {
    short_cooldown_trend_1: 15,
    short_cooldown_trend_2_3: 20,
    short_cooldown_trend_4: 30
  },
  short_decreasing: {
    short_decreasing_buy_enabled: true,
    short_position_ratio: 0.8,
    short_max_positions: 1
  },
  short_risk: {
    short_stop_loss_percent: 2.0,
    short_take_profit_percent: 3.0,
    short_pullback_threshold: 1.03
  },
  short_exemption: {
    short_exemption_enabled: true,
    short_exemption_loss_high: 60,
    short_exemption_loss_medium: 45,
    short_exemption_profit: 30
  }
}

const config = reactive(JSON.parse(JSON.stringify(DEFAULT_CONFIG)))

function getTimeZoneName(key: string | number): string {
  const keyStr = String(key)
  const names: Record<string, string> = {
    '00:00-04:00': '亚洲尾盘',
    '04:00-08:00': '欧美交接',
    '08:00-12:00': '亚洲早盘',
    '12:00-16:00': '亚洲午盘',
    '16:00-20:00': '欧洲早盘',
    '20:00-24:00': '美国早盘'
  }
  return names[keyStr] || keyStr
}

function getReducePercent(action: string): string {
  const match = action.match(/reduce(\d+)/)
  if (match) {
    return `卖${match[1]}%`
  }
  return action
}

async function updateConfig() {
  // 实时更新（防抖）
  // 实际应用中可能需要添加防抖逻辑
}

async function saveConfig() {
  try {
    const response = await fetch('/api/v1/services/sparrow-config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    })
    if (response.ok) {
      ElMessage.success('麻雀战法配置已保存')
    } else {
      ElMessage.error('保存失败')
    }
  } catch (error) {
    console.error('Failed to save config:', error)
    ElMessage.error('保存失败')
  }
}

async function resetConfig() {
  Object.assign(config, JSON.parse(JSON.stringify(DEFAULT_CONFIG)))
  await saveConfig()
  ElMessage.success('已恢复默认配置')
}

async function loadConfig() {
  try {
    const response = await fetch('/api/v1/services/sparrow-config')
    if (response.ok) {
      const data = await response.json()
      if (data) {
        Object.assign(config, data)
      }
    }
  } catch (error) {
    console.error('Failed to load config:', error)
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style lang="scss" scoped>
.sparrow-config-card {
  .card-header {
    padding-bottom: 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);

    .header-left {
      display: flex;
      align-items: center;
      gap: 16px;

      .title-section {
        .card-title {
          font-size: 18px;
          font-weight: 600;
          margin-bottom: 4px;
        }

        .card-subtitle {
          font-size: 13px;
          color: rgba(255, 255, 255, 0.6);
        }
      }
    }
  }

  .config-section {
    margin-bottom: 32px;

    &:last-child {
      margin-bottom: 0;
    }

    .section-title {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 16px;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 10px;

      &::before {
        content: '';
        width: 4px;
        height: 16px;
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        border-radius: 2px;
      }
    }

    .config-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;

      .param-item {
        padding: 14px 16px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all $transition-normal;

        &:hover {
          background: rgba(255, 255, 255, 0.1);
          box-shadow: $dark-shadow;
        }

        .param-label {
          display: block;
          font-size: 13px;
          font-weight: 600;
          color: #ffffff;
          margin-bottom: 12px;
        }

        .param-control {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;

          .param-unit {
            font-size: 13px;
            color: rgba(255, 255, 255, 0.7);
            font-weight: 500;
            min-width: 40px;
          }

          .param-hint {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.5);
          }
        }
      }
    }

    .sub-section {
      margin-top: 20px;
      padding: 16px;
      background: rgba(102, 126, 234, 0.1);
      border-radius: 10px;

      .sub-section-title {
        font-size: 14px;
        font-weight: 600;
        color: #ffffff;
        margin-bottom: 12px;
      }
    }
  }

  .timezone-config {
    display: flex;
    flex-direction: column;
    gap: 16px;

    .timezone-item {
      padding: 16px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 10px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      transition: all $transition-normal;

      &:hover {
        background: #fff;
        box-shadow: $shadow-sm;
      }

      .timezone-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;

        .timezone-name {
          font-size: 15px;
          font-weight: 600;
          color: #ffffff;
        }

        .intensity-indicator {
          display: flex;
          gap: 2px;

          .star {
            opacity: 0.3;
            font-size: 14px;

            &.active {
              opacity: 1;
            }
          }
        }
      }

      .timezone-params {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;

        .param-row {
          display: flex;
          align-items: center;
          gap: 8px;

          .label {
            font-size: 13px;
            color: rgba(255, 255, 255, 0.7);
            font-weight: 500;
            min-width: 60px;
          }

          .control-group {
            display: flex;
            align-items: center;
            gap: 6px;
            flex: 1;

            .unit {
              font-size: 12px;
              color: rgba(255, 255, 255, 0.5);
              min-width: 35px;
            }
          }
        }
      }
    }
  }

  .actions {
    display: flex;
    gap: 12px;
    justify-content: flex-end;
    padding-top: 20px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    margin-top: 20px;
  }
}
</style>
