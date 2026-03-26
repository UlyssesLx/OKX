<template>
  <div class="evolution-card card">
    <div class="card-header">
      <span class="title">🧬 策略自迭代</span>
      <el-tag :type="status.is_paused ? 'warning' : 'success'" size="small">
        {{ status.is_paused ? '暂停中' : '运行中' }}
      </el-tag>
    </div>

    <div class="card-content">
      <div class="status-info">
        <div class="info-row">
          <span class="label">版本:</span>
          <span class="value">{{ status.version }}</span>
        </div>
        <div class="info-row">
          <span class="label">迭代次数:</span>
          <span class="value">{{ status.iterations_count }}</span>
        </div>
        <div class="info-row">
          <span class="label">总交易:</span>
          <span class="value">{{ status.total_trades }}</span>
        </div>
        <div class="info-row">
          <span class="label">胜/负:</span>
          <span class="value">{{ status.wins || 0 }} / {{ status.losses || 0 }}</span>
        </div>
        <div class="info-row">
          <span class="label">连续亏损:</span>
          <span class="value" :class="{ 'warning': status.consecutive_losses >= 3 }">
            {{ status.consecutive_losses || 0 }}
          </span>
        </div>
      </div>

      <div class="params-section">
        <div class="section-title">📈 做多参数</div>
        <div class="params-grid">
          <div class="param-item">
            <span class="param-label">止损</span>
            <span class="param-value">{{ status.long?.params?.stop_loss || -5.0 }}%</span>
          </div>
          <div class="param-item">
            <span class="param-label">止盈</span>
            <span class="param-value">{{ status.long?.params?.take_profit || 10.0 }}%</span>
          </div>
          <div class="param-item">
            <span class="param-label">最大持仓</span>
            <span class="param-value">{{ status.long?.params?.max_positions || 5 }}</span>
          </div>
          <div class="param-item">
            <span class="param-label">单笔金额</span>
            <span class="param-value">${{ status.long?.params?.trade_size || 60 }}</span>
          </div>
        </div>
      </div>

      <div class="params-section">
        <div class="section-title">📉 做空参数</div>
        <div class="params-grid">
          <div class="param-item">
            <span class="param-label">止损</span>
            <span class="param-value">{{ status.short?.params?.stop_loss || -3.0 }}%</span>
          </div>
          <div class="param-item">
            <span class="param-label">止盈</span>
            <span class="param-value">{{ status.short?.params?.take_profit || 6.0 }}%</span>
          </div>
          <div class="param-item">
            <span class="param-label">最大持仓</span>
            <span class="param-value">{{ status.short?.params?.max_positions || 1 }}</span>
          </div>
          <div class="param-item">
            <span class="param-label">单笔金额</span>
            <span class="param-value">${{ status.short?.params?.trade_size || 40 }}</span>
          </div>
        </div>
      </div>

      <div class="sentiment-section">
        <div class="section-title">📰 舆情阈值</div>
        <div class="sentiment-cards">
          <div class="sentiment-card long">
            <div class="sentiment-icon">📈</div>
            <div class="sentiment-info">
              <div class="sentiment-label">做多买入</div>
              <div class="sentiment-value">>= {{ status.long?.params?.sentiment_threshold || 7 }}</div>
            </div>
          </div>
          <div class="sentiment-card short">
            <div class="sentiment-icon">📉</div>
            <div class="sentiment-info">
              <div class="sentiment-label">做空卖出</div>
              <div class="sentiment-value">>= {{ status.short?.params?.sentiment_threshold || 7 }}</div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="status.is_paused" class="paused-notice">
        <el-icon><WarningFilled /></el-icon>
        <span>策略已暂停 {{ formatPauseTime(status.pause_until) }}</span>
      </div>

      <el-button type="primary" size="small" @click="showHistory = true" class="history-btn">
        📜 查看进化历史
      </el-button>

      <el-button type="primary" size="small" @click="refreshStatus" :loading="loading" class="refresh-btn">
        🔄 刷新状态
      </el-button>

      <el-button type="warning" size="small" @click="showConfig = true" class="config-btn">
        ⚙️ 进化配置
      </el-button>
    </div>

    <!-- 进化配置对话框 -->
    <el-dialog v-model="showConfig" title="⚙️ 策略进化配置" width="600px">
      <div class="config-form">
        <div class="form-item">
          <div class="form-label">复盘交易数量</div>
          <div class="form-desc">达到指定交易笔数后进行复盘</div>
          <el-input-number v-model="evoConfig.min_trades_for_review" :min="5" :max="50" :step="5" />
        </div>
        <div class="form-item">
          <div class="form-label">连续亏损阈值</div>
          <div class="form-desc">连续亏损达到此数值时触发调整/暂停</div>
          <el-input-number v-model="evoConfig.consecutive_loss_threshold" :min="2" :max="10" />
        </div>
        <div class="form-item">
          <div class="form-label">高胜率阈值</div>
          <div class="form-desc">胜率高于此值时放宽策略</div>
          <el-slider v-model="evoConfig.win_rate_high" :min="0.5" :max="0.9" :step="0.05" :format-tooltip="(v: number) => (v * 100).toFixed(0) + '%'" />
          <span class="slider-value">{{ (evoConfig.win_rate_high * 100).toFixed(0) }}%</span>
        </div>
        <div class="form-item">
          <div class="form-label">低胜率阈值</div>
          <div class="form-desc">胜率低于此值时收紧策略</div>
          <el-slider v-model="evoConfig.win_rate_low" :min="0.2" :max="0.5" :step="0.05" :format-tooltip="(v: number) => (v * 100).toFixed(0) + '%'" />
          <span class="slider-value">{{ (evoConfig.win_rate_low * 100).toFixed(0) }}%</span>
        </div>
        <div class="form-item">
          <div class="form-label">暂停时长（小时）</div>
          <div class="form-desc">连续亏损触发暂停的小时数</div>
          <el-input-number v-model="evoConfig.pause_after_losses_hours" :min="1" :max="72" :step="1" />
        </div>
      </div>
      <template #footer>
        <el-button @click="showConfig = false">取消</el-button>
        <el-button type="primary" @click="saveConfig" :loading="configSaving">保存配置</el-button>
      </template>
    </el-dialog>

    <!-- 进化历史对话框 -->
    <el-dialog v-model="showHistory" title="📜 策略进化历史" width="80%" top="5vh">
      <div v-if="historyLoading" class="loading-container">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载中...</span>
      </div>
      <div v-else-if="history.iterations.length === 0" class="empty-container">
        <el-empty description="暂无进化记录" />
      </div>
      <div v-else class="history-container">
        <el-timeline>
          <el-timeline-item
            v-for="(item, index) in history.iterations"
            :key="index"
            :timestamp="formatDate(item.date)"
            placement="top"
            :type="index === 0 ? 'primary' : 'info'"
            :size="index === 0 ? 'large' : 'normal'"
          >
            <el-card class="history-item">
              <div class="history-header">
                <el-tag size="small">{{ item.version }}</el-tag>
                <el-tag type="success" size="small">{{ item.trigger }}</el-tag>
              </div>
              <div class="history-changes">
                <div class="changes-title">调整内容:</div>
                <ul>
                  <li v-for="(change, i) in item.changes" :key="i">{{ change }}</li>
                </ul>
              </div>
              <div class="history-params">
                <div class="params-compare">
                  <div class="params-group params-before">
                    <div class="group-title">调整前:</div>
                    <div class="param-row">止损: {{ item.params_before.stop_loss }}%</div>
                    <div class="param-row">止盈: {{ item.params_before.take_profit }}%</div>
                    <div class="param-row">多单: {{ item.params_before.max_positions }}</div>
                    <div class="param-row">空单: {{ item.params_before.short_max_positions || 1 }}</div>
                    <div class="param-row">金额: ${{ item.params_before.trade_size }}</div>
                  </div>
                  <div class="params-arrow">→</div>
                  <div class="params-group params-after">
                    <div class="group-title">调整后:</div>
                    <div class="param-row">止损: {{ item.params_after.stop_loss }}%</div>
                    <div class="param-row">止盈: {{ item.params_after.take_profit }}%</div>
                    <div class="param-row">多单: {{ item.params_after.max_positions }}</div>
                    <div class="param-row">空单: {{ item.params_after.short_max_positions || 1 }}</div>
                    <div class="param-row">金额: ${{ item.params_after.trade_size }}</div>
                  </div>
                </div>
              </div>
              <div class="history-performance">
                <div class="perf-title">表现数据:</div>
                <div class="perf-grid">
                  <div class="perf-item">
                    <span class="perf-label">胜率:</span>
                    <span class="perf-value">{{ (item.performance.win_rate * 100).toFixed(0) }}%</span>
                  </div>
                  <div class="perf-item">
                    <span class="perf-label">平均盈利:</span>
                    <span class="perf-value positive">+{{ item.performance.avg_profit.toFixed(2) }}%</span>
                  </div>
                  <div class="perf-item">
                    <span class="perf-label">平均亏损:</span>
                    <span class="perf-value negative">-{{ item.performance.avg_loss.toFixed(2) }}%</span>
                  </div>
                  <div class="perf-item">
                    <span class="perf-label">盈亏比:</span>
                    <span class="perf-value">{{ item.performance.profit_factor.toFixed(2) }}</span>
                  </div>
                </div>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { WarningFilled, Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const status = ref<any>({
  version: '2.1.0',
  is_paused: false,
  pause_until: null,
  long: {
    params: {
      stop_loss: -5.0,
      take_profit: 10.0,
      max_positions: 5,
      trade_size: 60,
      sentiment_threshold: 7
    },
    performance: null
  },
  short: {
    params: {
      stop_loss: -3.0,
      take_profit: 6.0,
      max_positions: 1,
      trade_size: 40,
      sentiment_threshold: 7
    },
    performance: null
  },
  iterations_count: 0,
  total_trades: 0,
  wins: 0,
  losses: 0,
  consecutive_losses: 0,
  last_trade_time: null
})

const loading = ref(false)
const historyLoading = ref(false)
const showHistory = ref(false)
const showConfig = ref(false)
const configSaving = ref(false)
const history = ref<any>({
  version: '2.1.0',
  total_iterations: 0,
  iterations: []
})

const evoConfig = ref({
  min_trades_for_review: 10,
  consecutive_loss_threshold: 3,
  win_rate_high: 0.70,
  win_rate_low: 0.40,
  pause_after_losses_hours: 24
})

let pollInterval: number | null = null

async function fetchStatus() {
  try {
    const response = await fetch('/api/v1/services/evolution/status')
    if (response.ok) {
      const data = await response.json()
      status.value = {
        ...status.value,
        ...data,
        long: data.long || status.value.long,
        short: data.short || status.value.short
      }
    }
  } catch (error) {
    console.error('Failed to fetch strategy evolution status:', error)
  }
}

async function fetchHistory() {
  historyLoading.value = true
  try {
    const response = await fetch('/api/v1/services/evolution/history?limit=50')
    if (response.ok) {
      const data = await response.json()
      history.value = data
    }
  } catch (error) {
    console.error('Failed to fetch strategy evolution history:', error)
  }
  historyLoading.value = false
}

async function fetchConfig() {
  try {
    const response = await fetch('/api/v1/services/evolution/config')
    if (response.ok) {
      const data = await response.json()
      evoConfig.value = data
    }
  } catch (error) {
    console.error('Failed to fetch evolution config:', error)
  }
}

async function saveConfig() {
  configSaving.value = true
  try {
    const response = await fetch('/api/v1/services/evolution/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(evoConfig.value)
    })
    if (response.ok) {
      ElMessage.success('配置已保存')
      showConfig.value = false
    }
  } catch (error) {
    console.error('Failed to save evolution config:', error)
    ElMessage.error('保存失败')
  }
  configSaving.value = false
}

function formatPauseTime(isoString: string | null): string {
  if (!isoString) return ''
  try {
    const pauseUntil = new Date(isoString)
    const now = new Date()
    const remaining = Math.max(0, Math.floor((pauseUntil.getTime() - now.getTime()) / 60000))
    return `还剩 ${remaining} 分钟`
  } catch {
    return ''
  }
}

function formatDate(isoString: string): string {
  try {
    const date = new Date(isoString)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return isoString
  }
}

async function refreshStatus() {
  loading.value = true
  await fetchStatus()
  loading.value = false
}

// 监听 showHistory 变化，打开时加载历史记录
watch(showHistory, (newVal) => {
  if (newVal) {
    fetchHistory()
  }
})

watch(showConfig, (newVal) => {
  if (newVal) {
    fetchConfig()
  }
})

onMounted(() => {
  fetchStatus()
  pollInterval = window.setInterval(fetchStatus, 30000)
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>

<style lang="scss" scoped>
.evolution-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .title {
      font-size: 16px;
      font-weight: 600;
    }
  }

  .card-content {
    margin-top: 16px;
  }

  .status-info {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 16px;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  .info-row {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);

    &:last-child {
      border-bottom: none;
    }

    .label {
      color: rgba(255, 255, 255, 0.7);
    }

    .value {
      font-weight: 500;
      color: #ffffff;

      &.warning {
        color: #ff4d4f;
      }
    }
  }

  .params-section {
    margin-bottom: 16px;
  }

  .section-title {
    font-size: 13px;
    font-weight: 600;
    color: #ffffff;
    margin-bottom: 12px;
  }

  .params-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }

  .param-item {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 6px;
    padding: 10px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  .param-label {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.7);
  }

  .param-value {
    font-size: 14px;
    font-weight: 600;
    color: $primary-color;
  }

  .paused-notice {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(255, 77, 79, 0.1);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 16px;
    color: #ff4d4f;
    font-size: 13px;
  }

  .history-btn {
    width: 100%;
    margin-bottom: 8px;
  }

  .refresh-btn {
    width: 100%;
    margin-left: 0px;
  }

  .config-btn {
    width: 100%;
    margin-top: 8px;
    margin-left: 0px;
  }

  :deep(.history-btn) {
    background: linear-gradient(135deg, #5a6ab8, #6b7dc4) !important;
    border: none !important;
    color: #ffffff !important;
    box-shadow: 0 2px 6px rgba(90, 106, 184, 0.3) !important;

    &:hover {
      background: linear-gradient(135deg, #6b7dc4, #7a8ed4) !important;
    }
  }

  :deep(.refresh-btn) {
    background: linear-gradient(135deg, #4a9e8e, #5bb8a6) !important;
    border: none !important;
    color: #ffffff !important;
    box-shadow: 0 2px 6px rgba(75, 158, 142, 0.3) !important;

    &:hover {
      background: linear-gradient(135deg, #5bb8a6, #6cc8b8) !important;
    }
  }

  :deep(.config-btn) {
    background: linear-gradient(135deg, #c48835, #d49a40) !important;
    border: none !important;
    color: #ffffff !important;
    box-shadow: 0 2px 6px rgba(196, 136, 53, 0.3) !important;

    &:hover {
      background: linear-gradient(135deg, #d49a40, #e0aa50) !important;
    }
  }

  .config-form {
    .form-item {
      margin-bottom: 20px;

      .form-label {
        font-size: 14px;
        font-weight: 500;
        color: #ffffff;
        margin-bottom: 4px;
      }

      .form-desc {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.6);
        margin-bottom: 8px;
      }

      .slider-value {
        display: inline-block;
        margin-left: 12px;
        font-size: 14px;
        color: $primary-color;
        font-weight: 500;
      }
    }
  }

  .sentiment-section {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 12px;
    margin-top: 12px;
    margin-bottom: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);

    .section-title {
      font-size: 13px;
      font-weight: 600;
      color: #ffffff;
      margin-bottom: 10px;
    }

    .sentiment-cards {
      display: flex;
      gap: 10px;
    }

    .sentiment-card {
      flex: 1;
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      border-radius: 8px;

      &.long {
        background: linear-gradient(135deg, rgba(82, 196, 26, 0.15), rgba(82, 196, 26, 0.05));
        border: 1px solid rgba(82, 196, 26, 0.3);
        .sentiment-icon { color: $success-color; }
        .sentiment-value { color: $success-color; }
      }

      &.short {
        background: linear-gradient(135deg, rgba(255, 77, 79, 0.15), rgba(255, 77, 79, 0.05));
        border: 1px solid rgba(255, 77, 79, 0.3);
        .sentiment-icon { color: $danger-color; }
        .sentiment-value { color: $danger-color; }
      }

      .sentiment-icon {
        font-size: 20px;
      }

      .sentiment-info {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }

      .sentiment-label {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.7);
      }

      .sentiment-value {
        font-size: 16px;
        font-weight: 600;
      }
    }
  }

  // 进化历史对话框样式
  .loading-container,
  .empty-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 200px;
    gap: 12px;
    color: rgba(255, 255, 255, 0.8);
  }

  .history-container {
    max-height: 60vh;
    overflow-y: auto;
    padding-right: 10px;

    &::-webkit-scrollbar {
      width: 6px;
    }

    &::-webkit-scrollbar-track {
      background: rgba(255, 255, 255, 0.1);
      border-radius: 3px;
    }

    &::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.3);
      border-radius: 3px;

      &:hover {
        background: rgba(255, 255, 255, 0.5);
      }
    }
  }

  .history-item {
    margin-bottom: 12px;

    .history-header {
      display: flex;
      gap: 8px;
      margin-bottom: 12px;
      align-items: center;
    }

    .history-changes {
      margin-bottom: 12px;

      .changes-title {
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 6px;
        color: #ffffff;
      }

      ul {
        margin: 0;
        padding-left: 20px;
        list-style-type: disc;

        li {
          font-size: 13px;
          color: rgba(255, 255, 255, 0.9);
          margin-bottom: 4px;
          line-height: 1.5;
        }
      }
    }

    .history-params {
      margin-bottom: 12px;

      .params-compare {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        gap: 16px;
        align-items: center;
      }

      .params-group {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 6px;
        padding: 10px;

        .group-title {
          font-size: 12px;
          font-weight: 600;
          margin-bottom: 8px;
          color: #ffffff;
        }

        .param-row {
          font-size: 12px;
          color: rgba(255, 255, 255, 0.9);
          margin-bottom: 4px;

          &:last-child {
            margin-bottom: 0;
          }
        }

        &.params-after {
          background: rgba(103, 194, 58, 0.1);
        }
      }

      .params-arrow {
        font-size: 18px;
        color: $primary-color;
        font-weight: 600;
      }
    }

    .history-performance {
      .perf-title {
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 8px;
        color: #ffffff;
      }

      .perf-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
      }

      .perf-item {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 4px;
        padding: 8px;
        text-align: center;

        .perf-label {
          font-size: 11px;
          color: rgba(255, 255, 255, 0.7);
          display: block;
          margin-bottom: 4px;
        }

        .perf-value {
          font-size: 13px;
          font-weight: 600;
          color: #ffffff;

          &.positive {
            color: #67c23a;
          }

          &.negative {
            color: #f56c6c;
          }
        }
      }
    }
  }
}
</style>
