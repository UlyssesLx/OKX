<template>
  <div class="positions-detail-card card">
    <div class="card-header">
      <span class="card-title">💰 持仓详情</span>
      <el-button type="primary" size="small" @click="fetchData">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>
    
    <div class="positions-summary">
      <el-row :gutter="16">
        <el-col :span="3">
          <div class="summary-item">
            <div class="summary-label">总持仓</div>
            <div class="summary-value">${{ totalPositionValue.toFixed(2) }}</div>
          </div>
        </el-col>
        <el-col :span="3">
          <div class="summary-item">
            <div class="summary-label">持仓数</div>
            <div class="summary-value">{{ positionCount }}</div>
          </div>
        </el-col>
        <el-col :span="3">
          <div class="summary-item">
            <div class="summary-label">总盈亏</div>
            <div class="summary-value" :class="totalPnl >= 0 ? 'positive' : 'negative'">
              ${{ totalPnl >= 0 ? '+' : '' }}{{ totalPnl.toFixed(2) }}
            </div>
          </div>
        </el-col>
        <el-col :span="3">
          <div class="summary-item">
            <div class="summary-label">模拟余额</div>
            <div class="summary-value">${{ simulationAvailableBalance.toFixed(2) }}</div>
          </div>
        </el-col>
        <el-col :span="3">
          <div class="summary-item">
            <div class="summary-label">模拟盈亏</div>
            <div class="summary-value" :class="simulationPnl >= 0 ? 'positive' : 'negative'">
              ${{ simulationPnl >= 0 ? '+' : '' }}{{ simulationPnl.toFixed(2) }}
            </div>
          </div>
        </el-col>
        <el-col :span="3">
          <div class="summary-item">
            <div class="summary-label">模拟胜率</div>
            <div class="summary-value">{{ simulationWinRate.toFixed(1) }}%</div>
          </div>
        </el-col>
        <el-col :span="3">
          <div class="summary-item">
            <div class="summary-label">盈亏比</div>
            <div class="summary-value" :class="totalPnlPercent >= 0 ? 'positive' : 'negative'">
              {{ totalPnlPercent >= 0 ? '+' : '' }}{{ totalPnlPercent.toFixed(2) }}%
            </div>
          </div>
        </el-col>
        <el-col :span="3">
          <div class="summary-item">
            <div class="summary-label">初始资金</div>
            <div class="summary-value">${{ simulationInitialBalance.toFixed(0) }}</div>
          </div>
        </el-col>
      </el-row>
    </div>
    
    <div class="positions-table">
      <el-table
        :data="positionList"
        style="width: 100%"
        :header-cell-style="{ background: 'rgba(255,255,255,0.05)', color: '#fff' }"
        :cell-style="{ color: 'rgba(255,255,255,0.9)' }"
        size="small"
      >
        <el-table-column prop="coin" label="币种" min-width="80">
          <template #default="{ row }">
            {{ row.coin }}
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" min-width="70">
          <template #default="{ row }">
            <el-tag :type="row.isSimulation ? 'warning' : 'success'" size="small">
              {{ row.isSimulation ? '模拟' : '实盘' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="direction" label="方向" min-width="70">
          <template #default="{ row }">
            <el-tag :type="row.isShort ? 'danger' : 'primary'" size="small">
              {{ row.isShort ? '空单' : '多单' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="leverage" label="杠杆" min-width="60">
          <template #default="{ row }">
            <span v-if="row.isSwap" class="leverage-tag">{{ row.leverage }}x</span>
            <span v-else class="leverage-tag spot">现货</span>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="数量" min-width="120">
          <template #default="{ row }">
            {{ row.amount.toFixed(6) }}
          </template>
        </el-table-column>
        <el-table-column prop="currentPrice" label="现价" min-width="100">
          <template #default="{ row }">
            ${{ row.currentPrice.toFixed(4) }}
          </template>
        </el-table-column>
        <el-table-column prop="avgPrice" label="成本价" min-width="100">
          <template #default="{ row }">
            ${{ row.avgPrice.toFixed(4) }}
          </template>
        </el-table-column>
        <el-table-column prop="currentValue" label="现值" min-width="100">
          <template #default="{ row }">
            ${{ row.currentValue.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="pnlPercent" label="盈亏比" min-width="90">
          <template #default="{ row }">
            <span :class="row.pnlPercent >= 0 ? 'positive' : 'negative'">
              {{ row.pnlPercent >= 0 ? '+' : '' }}{{ row.pnlPercent.toFixed(2) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="pnlValue" label="盈亏额" min-width="100">
          <template #default="{ row }">
            <span :class="row.pnlValue >= 0 ? 'positive' : 'negative'">
              ${{ row.pnlValue >= 0 ? '+' : '' }}{{ row.pnlValue.toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="80" fixed="right">
          <template #default="{ row }">
            <el-button 
              type="danger" 
              size="small"
              @click="handleSell(row.coin, row.amount, row.isSimulation, row.isShort)"
            >
              {{ row.isShort ? '平仓' : '卖出' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watch, onUnmounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useTradingStore } from '@/stores/trading'
import { tradingApi } from '@/api'
import { ElMessage } from 'element-plus'

const tradingStore = useTradingStore()

const positions = computed(() => tradingStore.positions)

interface PositionItem {
  coin: string
  amount: number
  value: number
  avgPrice: number
  currentPrice: number
  currentValue: number
  pnlPercent: number
  pnlValue: number
  isSimulation: boolean
  isShort: boolean
  leverage: number
  isSwap: boolean
}

const currentPrices = ref<Record<string, number>>({})
let priceInterval: number | null = null

async function fetchCurrentPrices(coins: string[]) {
  const uniqueCoins = [...new Set(coins)]
  if (uniqueCoins.length === 0) {
    currentPrices.value = {}
    return
  }

  try {
    const tickers = await tradingApi.getTickers()
    const newPrices: Record<string, number> = {}
    for (const ticker of tickers) {
      const coin = (ticker.instId || ticker.inst_id).replace('-USDT', '')
      if (uniqueCoins.includes(coin)) {
        const price = ticker.last || ticker.price
        newPrices[coin] = typeof price === 'string' ? parseFloat(price) : price
      }
    }
    currentPrices.value = newPrices
  } catch (error) {
    console.error('获取价格失败:', error)
  }
}

const positionList = computed(() => {
  const list: PositionItem[] = []

  for (const [key, pos] of Object.entries(positions.value)) {
    const coin = pos.coin || key.replace('_sim', '').replace('_short', '')
    const isSimulation = pos.is_simulation || false
    const isShort = pos.is_short || false
    const leverage = pos.leverage || 1.0
    const isSwap = pos.is_swap || false
    const currentPrice = currentPrices.value[coin] || pos.avg_price
    const currentValue = pos.amount * currentPrice
    const costValue = pos.amount * pos.avg_price
    let pnlPercent = 0
    let pnlValue = 0
    
    if (pos.avg_price > 0) {
      if (isShort) {
        pnlPercent = ((pos.avg_price / currentPrice) - 1) * 100
        pnlValue = costValue - currentValue
      } else {
        pnlPercent = ((currentPrice / pos.avg_price) - 1) * 100
        pnlValue = currentValue - costValue
      }
    }

    list.push({
      coin,
      amount: pos.amount,
      value: pos.value,
      avgPrice: pos.avg_price,
      currentPrice,
      currentValue,
      pnlPercent,
      pnlValue,
      isSimulation,
      isShort,
      leverage,
      isSwap
    })
  }

  return list
})

// 监听 positions 变化，自动刷新价格
watch(() => positions.value, (newPositions) => {
  const coins = Object.values(newPositions).map(p => (p as any).coin || '').filter(c => c)
  if (coins.length > 0) {
    fetchCurrentPrices(coins)
  }
}, { deep: true, immediate: true })

const totalPositionValue = computed(() => {
  return positionList.value.reduce((sum, p) => sum + p.currentValue, 0)
})

const positionCount = computed(() => positionList.value.length)

const totalPnl = computed(() => {
  return positionList.value.reduce((sum, p) => sum + p.pnlValue, 0)
})

const totalPnlPercent = computed(() => {
  const totalCost = positionList.value.reduce((sum, p) => sum + (p.amount * p.avgPrice), 0)
  return totalCost > 0 ? (totalPnl.value / totalCost) * 100 : 0
})

const simulationPnl = ref(0)
const simulationWinRate = ref(0)
const simulationInitialBalance = ref(1000)
const simulationAvailableBalance = ref(1000)

async function fetchSimulationStats() {
  try {
    const data = await tradingApi.getSimulationStats()
    simulationWinRate.value = data.stats.win_rate
    simulationPnl.value = data.stats.total_pnl
    simulationInitialBalance.value = data.stats.initial_balance
    simulationAvailableBalance.value = data.stats.available_balance
  } catch (error) {
    console.error('Failed to fetch simulation stats:', error)
  }
}

onMounted(() => {
  fetchSimulationStats()
  // 定期刷新价格和模拟统计
  priceInterval = window.setInterval(async () => {
    const coins = Object.values(positions.value).map(p => (p as any).coin || '').filter(c => c)
    if (coins.length > 0) {
      await fetchCurrentPrices(coins)
    }
    await fetchSimulationStats()
  }, 3000)
})

onUnmounted(() => {
  if (priceInterval) {
    clearInterval(priceInterval)
  }
})

async function fetchData() {
  await tradingStore.fetchBalance()
  await fetchSimulationStats()

  const coins = Object.values(positions.value).map(p => (p as any).coin || '').filter(c => c)
  if (coins.length > 0) {
    await fetchCurrentPrices(coins)
  }
}

async function handleSell(coin: string, amount: number, isSimulation: boolean, isShort: boolean = false) {
  if (isSimulation) {
    ElMessage.warning('模拟持仓请通过交易记录页面清空')
    return
  }

  try {
    const result = await tradingApi.placeOrder({
      inst_id: `${coin}-USDT`,
      side: isShort ? 'buy' : 'sell',
      order_type: 'market',
      size: (amount * 0.995).toFixed(6),
      use_swap: false
    })

    ElMessage.success(`${isShort ? '平仓' : '卖出'}订单已提交: ${result.order_id}`)
    fetchData()
  } catch (error: any) {
    let errorMsg = '卖出失败'
    if (error?.response?.data?.detail) {
      if (typeof error.response.data.detail === 'object') {
        errorMsg = `${error.response.data.detail.message || '卖出失败'} (错误码: ${error.response.data.detail.code})`
      } else {
        errorMsg = error.response.data.detail
      }
    } else if (error?.message) {
      errorMsg = error.message
    }
    ElMessage.error(errorMsg)
  }
}
</script>

<style lang="scss" scoped>
.positions-detail-card {
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
  }

  .positions-summary {
    margin-bottom: 16px;
    padding: 12px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.1);

    .summary-item {
      text-align: center;

      .summary-label {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.6);
        margin-bottom: 4px;
      }

      .summary-value {
        font-size: 16px;
        font-weight: 600;
        color: #ffffff;

        &.positive { color: #4caf50; }
        &.negative { color: #f44336; }
      }
    }
  }

  .positions-table {
    width: 100%;
    overflow-x: auto;

    :deep(.el-table) {
      background: transparent;
      width: 100% !important;

      .el-table__header-wrapper,
      .el-table__body-wrapper {
        width: 100% !important;
      }

      .el-table__header {
        width: 100% !important;

        .el-table__cell {
          background: rgba(255, 255, 255, 0.08);
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          padding: 10px 8px;
          font-weight: 600;
          text-align: center;

          .cell {
            padding: 0 4px;
            white-space: nowrap;
          }
        }
      }

      .el-table__body {
        width: 100% !important;

        .el-table__cell {
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          padding: 10px 8px;
          text-align: center;

          .cell {
            padding: 0 4px;
            white-space: nowrap;
          }
        }
      }

      tr {
        background: transparent;

        &:hover > td {
          background: rgba(255, 255, 255, 0.1);
        }
      }

      colgroup {
        display: none;
      }

      .leverage-tag {
        display: inline-block;
        padding: 2px 8px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;

        &.spot {
          background: rgba(144, 147, 153, 0.5);
        }
      }
    }
  }
}
</style>
