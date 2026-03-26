<template>
  <div class="trades-history-card card">
    <div class="card-header">
      <span class="card-title">📋 交易记录</span>
      <div class="header-actions">
        <el-tag type="warning" size="small">模拟盘</el-tag>
        <el-button type="danger" size="small" @click="handleClear" :loading="clearing">
          清空记录
        </el-button>
        <el-button type="primary" size="small" @click="fetchData" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>
    
    <div class="trades-stats">
      <el-row :gutter="12">
        <el-col :span="4">
          <div class="stat-item">
            <div class="stat-label">初始资金</div>
            <div class="stat-value">${{ stats.initial_balance.toFixed(0) }}</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-item">
            <div class="stat-label">可用余额</div>
            <div class="stat-value">${{ stats.available_balance.toFixed(2) }}</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-item">
            <div class="stat-label">总交易</div>
            <div class="stat-value">{{ stats.total_trades }}</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-item">
            <div class="stat-label">胜/负</div>
            <div class="stat-value">{{ stats.win_count }}/{{ stats.loss_count }}</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-item">
            <div class="stat-label">胜率</div>
            <div class="stat-value" :class="stats.win_rate >= 50 ? 'positive' : 'negative'">
              {{ stats.win_rate.toFixed(1) }}%
            </div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-item">
            <div class="stat-label">总盈亏</div>
            <div class="stat-value" :class="stats.total_pnl >= 0 ? 'positive' : 'negative'">
              {{ stats.total_pnl >= 0 ? '+' : '' }}${{ stats.total_pnl.toFixed(2) }}
            </div>
          </div>
        </el-col>
      </el-row>
    </div>
    
    <div class="trades-table">
      <div class="table-header">
        <el-row :gutter="8">
          <el-col :span="3"><div class="th">时间</div></el-col>
          <el-col :span="2"><div class="th">币种</div></el-col>
          <el-col :span="2"><div class="th">操作</div></el-col>
          <el-col :span="2"><div class="th">策略</div></el-col>
          <el-col :span="1"><div class="th">杠杆</div></el-col>
          <el-col :span="2"><div class="th">价格</div></el-col>
          <el-col :span="2"><div class="th">数量</div></el-col>
          <el-col :span="2"><div class="th">金额</div></el-col>
          <el-col :span="2"><div class="th">盈亏</div></el-col>
          <el-col :span="6"><div class="th">原因</div></el-col>
        </el-row>
      </div>
      <div class="table-body" v-if="trades.length > 0">
        <div v-for="(row, index) in trades" :key="index" class="table-row">
          <el-row :gutter="8">
            <el-col :span="3"><div class="td">{{ formatDateTime(row.timestamp) }}</div></el-col>
            <el-col :span="2"><div class="td">{{ row.coin }}</div></el-col>
            <el-col :span="2">
              <div class="td">
                <el-tag :type="getActionType(row.action)" size="small">
                  {{ getActionLabel(row.action) }}
                </el-tag>
              </div>
            </el-col>
            <el-col :span="2">
              <div class="td">
                <el-tag :type="getStrategyType(row.strategy)" size="small" v-if="row.strategy">
                  {{ getStrategyLabel(row.strategy) }}
                </el-tag>
                <span v-else class="text-muted">-</span>
              </div>
            </el-col>
            <el-col :span="1">
              <div class="td">
                <el-tag v-if="row.is_swap" type="danger" size="small">
                  {{ row.leverage || 1 }}x
                </el-tag>
                <el-tag v-else type="info" size="small">
                  现货
                </el-tag>
              </div>
            </el-col>
            <el-col :span="2"><div class="td">${{ row.price.toFixed(4) }}</div></el-col>
            <el-col :span="2"><div class="td">{{ row.amount.toFixed(6) }}</div></el-col>
            <el-col :span="2"><div class="td">${{ row.usdt_value.toFixed(2) }}</div></el-col>
            <el-col :span="2">
              <div class="td" :class="row.pnl >= 0 ? 'positive' : 'negative'">
                {{ (row.action === 'sell' || row.action === 'buy_short') ? (row.pnl >= 0 ? '+' : '') + row.pnl_percent.toFixed(2) + '%' : '-' }}
              </div>
            </el-col>
            <el-col :span="6">
              <div class="td reason">
                <el-tooltip :content="row.reason" placement="top" :disabled="!row.reason || row.reason.length < 30">
                  <span>{{ row.reason }}</span>
                </el-tooltip>
              </div>
            </el-col>
          </el-row>
        </div>
      </div>
      <div class="empty-state" v-else>
        <el-empty description="暂无交易记录" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { tradingApi } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/format'

interface Trade {
  coin: string
  action: string
  price: number
  amount: number
  usdt_value: number
  pnl: number
  pnl_percent: number
  reason: string
  timestamp: string
  is_simulation: boolean
  leverage?: number
  strategy?: string
  is_swap?: boolean
}

interface Stats {
  total_pnl: number
  win_count: number
  loss_count: number
  total_trades: number
  win_rate: number
  position_count: number
  initial_balance: number
  available_balance: number
}

const loading = ref(false)
const clearing = ref(false)
const trades = ref<Trade[]>([])
const stats = ref<Stats>({
  total_pnl: 0,
  win_count: 0,
  loss_count: 0,
  total_trades: 0,
  win_rate: 0,
  position_count: 0,
  initial_balance: 1000,
  available_balance: 1000
})

// 获取操作类型标签样式
function getActionType(action: string): 'success' | 'danger' | 'warning' | 'primary' | 'info' {
  switch (action) {
    case 'buy':
      return 'success'
    case 'sell':
      return 'danger'
    case 'sell_short':
      return 'warning'
    case 'buy_short':
      return 'primary'
    default:
      return 'info'
  }
}

// 获取操作类型显示文本
function getActionLabel(action: string): string {
  switch (action) {
    case 'buy':
      return '开多'
    case 'sell':
      return '平多'
    case 'sell_short':
      return '开空'
    case 'buy_short':
      return '平空'
    default:
      return action
  }
}

// 获取策略类型标签样式
function getStrategyType(strategy: string): 'success' | 'danger' | 'warning' | 'primary' | 'info' {
  if (!strategy) return 'info'
  if (strategy.includes('短线') || strategy.includes('short_term')) return 'success'
  if (strategy.includes('抄底') || strategy.includes('追空') || strategy.includes('dip')) return 'warning'
  if (strategy.includes('阴线') || strategy.includes('阳线') || strategy.includes('bearish')) return 'primary'
  if (strategy.includes('暴跌') || strategy.includes('暴涨') || strategy.includes('crash')) return 'danger'
  return 'info'
}

// 获取策略显示文本
function getStrategyLabel(strategy: string): string {
  const strategyMap: Record<string, string> = {
    'short_term': '短线策略',
    '短线策略': '短线策略',
    'dip_buy': '严格抄底',
    '严格抄底': '严格抄底',
    'bearish_candle': '阴线买入',
    '阴线买入': '阴线买入',
    'crash_rebound': '暴跌反弹',
    '暴跌反弹': '暴跌反弹',
    'short_term_short': '短线做空',
    '短线做空': '短线做空',
    'short_dip': '严格追空',
    '严格追空': '严格追空',
    'short_bearish': '阳线做空',
    '阳线做空': '阳线做空',
    'short_crash': '暴涨做空',
    '暴涨做空': '暴涨做空'
  }
  return strategyMap[strategy] || strategy
}

async function fetchData() {
  loading.value = true
  try {
    const [tradesData, statsData] = await Promise.all([
      tradingApi.getSimulationTrades(100),
      tradingApi.getSimulationStats()
    ])
    trades.value = tradesData.trades.reverse()
    stats.value = statsData.stats
  } catch (error) {
    console.error('Failed to fetch simulation data:', error)
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

async function handleClear() {
  try {
    await ElMessageBox.confirm(
      '确定要清空所有模拟交易记录吗？这将重置账户余额和持仓。',
      '确认清空',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    clearing.value = true
    await tradingApi.clearSimulation()
    ElMessage.success('已清空模拟记录')
    await fetchData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('清空失败')
    }
  } finally {
    clearing.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style lang="scss" scoped>
.trades-history-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    .card-title {
      margin: 0;
      padding: 0;
      border: none;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }

  .trades-stats {
    margin-bottom: 16px;
    padding: 12px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.1);

    .stat-item {
      text-align: center;

      .stat-label {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.6);
        margin-bottom: 4px;
      }

      .stat-value {
        font-size: 14px;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.9);

        &.positive { color: #4caf50; }
        &.negative { color: #f44336; }
      }
    }
  }

  .trades-table {
    width: 100%;

    .table-header {
      background: rgba(255, 255, 255, 0.05);
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      padding: 10px 0;
      margin-bottom: 4px;

      .th {
        font-size: 13px;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.8);
        text-align: center;
        padding: 0 4px;
      }
    }

    .table-body {
      max-height: 400px;
      overflow-y: auto;

      .table-row {
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding: 8px 0;
        transition: background 0.2s;

        &:hover {
          background: rgba(255, 255, 255, 0.05);
        }

        .td {
          font-size: 13px;
          color: rgba(255, 255, 255, 0.9);
          text-align: center;
          padding: 4px;

          &.reason {
            text-align: left;
            color: rgba(255, 255, 255, 0.7);
            font-size: 12px;
            line-height: 1.4;
            word-break: break-all;
            white-space: normal;
          }

          &.positive { color: #4caf50; }
          &.negative { color: #f44336; }
        }
      }
    }

    .text-muted {
      color: rgba(255, 255, 255, 0.5);
      font-size: 12px;
    }

    .empty-state {
      padding: 40px 0;
    }
  }
}
</style>
