<template>
  <div class="market-scan-card card">
    <div class="card-header">
      <div class="header-left">
        <div class="card-icon gradient-icon green">
          <el-icon :size="20"><Search /></el-icon>
        </div>
        <div class="title-section">
          <div class="card-title">市场扫描</div>
          <div class="card-subtitle">发现交易机会</div>
        </div>
      </div>
      <div class="header-actions">
        <el-button type="primary" size="default" @click="scanMarket" :loading="loading">
          <el-icon style="margin-right: 6px"><Search /></el-icon>
          开始扫描
        </el-button>
      </div>
    </div>

    <div class="card-content">
      <div v-if="loading" class="loading-state">
        <div class="loading-icon">
          <el-icon class="is-loading" :size="48"><Loading /></el-icon>
        </div>
        <span class="loading-text">正在扫描市场...</span>
        <span class="loading-hint">分析所有币种的交易机会</span>
      </div>

      <div v-else-if="opportunities.length === 0" class="empty-state">
        <div class="empty-icon">
          <el-icon :size="64"><Search /></el-icon>
        </div>
        <span class="empty-text">暂无交易机会</span>
        <span class="empty-hint">点击扫描按钮查找机会</span>
      </div>

      <div v-else class="opportunities-list">
        <div class="list-header">
          <div class="header-info">
            <div class="opportunity-count">发现 {{ opportunities.length }} 个机会</div>
            <div class="scan-time">{{ scanTime }}</div>
          </div>
        </div>

        <el-table :data="opportunities" style="width: 100%" size="default" max-height="400">
          <el-table-column prop="coin" label="币种" width="90">
            <template #default="{ row }">
              <div class="coin-cell">
                <div class="coin-icon-wrapper gradient-icon blue sm">
                  <el-icon :size="14"><Coin /></el-icon>
                </div>
                <span class="coin-name">{{ row.coin }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="price" label="价格" width="110">
            <template #default="{ row }">
              <span class="price-value">${{ formatPrice(row.price) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="change_24h" label="24h涨跌" width="100">
            <template #default="{ row }">
              <span :class="row.change_24h >= 0 ? 'positive' : 'negative'" class="change-badge">
                {{ row.change_24h >= 0 ? '+' : '' }}{{ row.change_24h.toFixed(2) }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="trend_score" label="趋势" width="80">
            <template #default="{ row }">
              <el-tag :type="getTrendTagType(row.trend_score)" size="small" effect="plain">
                {{ row.trend_score }}分
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="resonance_score" label="共振" width="80">
            <template #default="{ row }">
              <el-tag :type="getResonanceTagType(row.resonance_score)" size="small" effect="plain">
                {{ row.resonance_score }}分
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="signal_type" label="信号类型" width="110">
            <template #default="{ row }">
              <el-tag :type="getSignalTagType(row.signal_type)" size="small" effect="light">
                {{ getSignalLabel(row.signal_type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="reason" label="原因" min-width="160">
            <template #default="{ row }">
              <span class="reason-text">{{ row.reason }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, Search, Coin } from '@element-plus/icons-vue'

interface Opportunity {
  coin: string
  price: number
  change_24h: number
  trend_score: number
  resonance_score: number
  signal_type: string
  reason: string
}

const opportunities = ref<Opportunity[]>([])
const loading = ref(false)
const scanTime = ref('')

function formatPrice(price: number): string {
  if (price >= 1000) return price.toFixed(2)
  if (price >= 1) return price.toFixed(4)
  return price.toFixed(6)
}

function getTrendTagType(score: number): 'success' | 'warning' | 'info' | 'primary' | 'danger' {
  if (score >= 8) return 'success'
  if (score >= 6) return 'warning'
  return 'info'
}

function getResonanceTagType(score: number): 'success' | 'warning' | 'info' | 'primary' | 'danger' {
  if (score >= 8) return 'success'
  if (score >= 6) return 'warning'
  return 'info'
}

function getSignalTagType(type: string): 'success' | 'warning' | 'info' | 'primary' | 'danger' {
  switch (type) {
    case 'bearish_candle': return 'warning'
    case 'crash_rebound': return 'danger'
    default: return 'primary'
  }
}

function getSignalLabel(type: string): string {
  switch (type) {
    case 'bearish_candle': return '阴线买入'
    case 'crash_rebound': return '暴跌反弹'
    default: return '常规信号'
  }
}

async function scanMarket() {
  loading.value = true
  try {
    const response = await fetch('/api/v1/services/trading/scan')
    if (response.ok) {
      const data = await response.json()
      opportunities.value = data.opportunities || []
      scanTime.value = new Date().toLocaleTimeString()
      ElMessage.success(`扫描完成，发现 ${opportunities.value.length} 个机会`)
    }
  } catch (error) {
    ElMessage.error('扫描失败')
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.market-scan-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;

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

  .card-content {
    flex: 1;
    margin-top: 20px;
    overflow: auto;
    min-height: 0;
  }

  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 30px;

    .loading-icon {
      color: $primary-color;
      margin-bottom: 20px;
    }

    .loading-text {
      font-size: 16px;
      font-weight: 500;
      color: rgba(255, 255, 255, 0.7);
      margin-bottom: 8px;
    }

    .loading-hint {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.6);
    }
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 30px;

    .empty-icon {
      color: rgba(255, 255, 255, 0.5);
      margin-bottom: 16px;
      opacity: 0.5;
    }

    .empty-text {
      font-size: 16px;
      font-weight: 500;
      color: rgba(255, 255, 255, 0.7);
      margin-bottom: 8px;
    }

    .empty-hint {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.6);
    }
  }

  .opportunities-list {
    .list-header {
      margin-bottom: 16px;

      .header-info {
        display: flex;
        justify-content: space-between;
        align-items: center;

        .opportunity-count {
          font-size: 15px;
          font-weight: 600;
          color: #ffffff;
        }

        .scan-time {
          font-size: 13px;
          color: rgba(255, 255, 255, 0.7);
        }
      }
    }

    .coin-cell {
      display: flex;
      align-items: center;
      gap: 8px;

      .coin-name {
        font-weight: 600;
        font-size: 14px;
        color: $primary-color;
      }
    }

    .price-value {
      font-weight: 500;
      color: #ffffff;
    }

    .change-badge {
      padding: 4px 10px;
      border-radius: 6px;
      font-weight: 600;
      font-size: 13px;
      display: inline-block;

      &.positive {
        background: rgba($success-color, 0.1);
        color: $success-color;
      }

      &.negative {
        background: rgba($danger-color, 0.1);
        color: $danger-color;
      }
    }

    .reason-text {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.7);
    }
  }
}
</style>
