<template>
  <div class="positions-card card">
    <div class="card-header">
      <div class="header-left">
        <div class="icon-wrapper gradient-icon green md">
          <el-icon :size="24"><Wallet /></el-icon>
        </div>
        <div class="title-info">
          <div class="card-title">持仓管理</div>
          <div class="card-subtitle">实时盈亏监控</div>
        </div>
      </div>
      <div class="header-actions">
        <span v-if="hasSimulationPositions" class="sim-tag">
          <el-icon><Warning /></el-icon>
          含模拟持仓
        </span>
        <el-button type="primary" size="small" @click="refreshPositions">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <div class="positions-list" v-if="positionList.length > 0">
      <div
        v-for="position in positionList"
        :key="position.coin"
        class="position-item"
        :class="{ 'simulation': position.is_simulation }"
      >
        <div class="position-header">
          <div class="coin-info">
            <div class="coin-icon gradient-icon blue sm">
              <el-icon><Coin /></el-icon>
            </div>
            <div class="coin-details">
              <div class="coin-name">{{ position.coin }}</div>
              <el-tag v-if="position.is_simulation" type="warning" size="small" effect="plain">
                模拟
              </el-tag>
              <el-tag v-else type="success" size="small" effect="plain">
                实盘
              </el-tag>
            </div>
          </div>
          <div
            class="pnl-badge"
            :class="position.pnlPercent >= 0 ? 'positive' : 'negative'"
          >
            <el-icon><CaretTop v-if="position.pnlPercent >= 0" /><CaretBottom v-else /></el-icon>
            {{ position.pnlPercent >= 0 ? '+' : '' }}{{ position.pnlPercent.toFixed(2) }}%
          </div>
        </div>

        <div class="position-details">
          <div class="detail-row">
            <span class="label">数量</span>
            <span class="value">{{ position.amount.toFixed(6) }}</span>
          </div>

          <div class="detail-row">
            <span class="label">现值</span>
            <span class="value">${{ position.currentValue.toFixed(2) }}</span>
          </div>

          <div class="detail-row">
            <span class="label">成本价</span>
            <span class="value">${{ position.avg_price.toFixed(4) }}</span>
          </div>

          <div class="detail-row">
            <span class="label">现价</span>
            <span class="value">${{ position.currentPrice.toFixed(4) }}</span>
          </div>

          <div class="detail-row">
            <span class="label">盈亏</span>
            <span
              class="value"
              :class="position.pnlValue >= 0 ? 'positive' : 'negative'"
            >
              {{ position.pnlValue >= 0 ? '+' : '' }}${{ position.pnlValue.toFixed(2) }}
            </span>
          </div>
        </div>

        <div class="position-actions">
          <el-button
            v-if="!position.is_simulation"
            type="danger"
            size="small"
            @click="handleSell(position.coin, position.amount)"
          >
            <el-icon><Sell /></el-icon>
            卖出
          </el-button>
          <span class="sim-position-tag" title="模拟持仓请在交易记录页面管理">
            <el-icon><Warning /></el-icon>
            模拟持仓
          </span>
        </div>
      </div>
    </div>

    <div class="empty-state" v-else>
      <el-empty description="暂无持仓" :image-size="100">
        <el-icon :size="80" color="#999"><Wallet /></el-icon>
      </el-empty>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { Refresh, Warning, Wallet, Coin, CaretTop, CaretBottom, Sell } from '@element-plus/icons-vue'
import type { Position } from '@/types'
import { tradingApi } from '@/api'
import { ElMessage } from 'element-plus'

interface Props {
  positions: Record<string, Position>
}

const props = defineProps<Props>()

const emit = defineEmits<{
  refresh: []
}>()

interface PositionItem extends Position {
  coin: string
  pnlPercent: number
  pnlValue: number
  currentPrice: number
  currentValue: number
}

const currentPrices = ref<Record<string, number>>({})
let priceInterval: number | null = null

async function fetchCurrentPrices() {
  const coins = Object.values(props.positions).map(p => p.coin || '').filter(c => c)
  if (coins.length === 0) {
    currentPrices.value = {}
    return
  }

  try {
    const tickers = await tradingApi.getTickers()
    const newPrices: Record<string, number> = {}
    for (const ticker of tickers) {
      const coin = (ticker.instId || ticker.inst_id).replace('-USDT', '')
      if (coins.includes(coin)) {
        const price = ticker.last || ticker.price
        newPrices[coin] = typeof price === 'string' ? parseFloat(price) : price
      }
    }
    currentPrices.value = newPrices
  } catch (error) {
    console.error('获取价格失败:', error)
  }
}

// 监听 positions 变化，自动刷新价格
watch(() => props.positions, () => {
  fetchCurrentPrices()
}, { deep: true })

const positionList = computed(() => {
  const list: PositionItem[] = []

  for (const [key, pos] of Object.entries(props.positions)) {
    const coin = pos.coin || key.replace('_sim', '')
    const currentPrice = currentPrices.value[coin] || pos.avg_price
    const currentValue = pos.amount * currentPrice
    const costValue = pos.amount * pos.avg_price
    const pnlPercent = pos.avg_price > 0
      ? ((currentPrice / pos.avg_price) - 1) * 100
      : 0
    const pnlValue = currentValue - costValue

    list.push({
      coin,
      ...pos,
      pnlPercent,
      pnlValue,
      currentPrice,
      currentValue
    })
  }

  return list
})

const hasSimulationPositions = computed(() => {
  return positionList.value.some(p => p.is_simulation)
})

async function refreshPositions() {
  await fetchCurrentPrices()
  emit('refresh')
}

async function handleSell(coin: string, amount: number) {
  try {
    const result = await tradingApi.placeOrder({
      inst_id: `${coin}-USDT`,
      side: 'sell',
      order_type: 'market',
      size: (amount * 0.995).toFixed(6)
    })

    ElMessage.success(`卖出订单已提交: ${result.order_id}`)
    refreshPositions()
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

onMounted(() => {
  fetchCurrentPrices()
  priceInterval = window.setInterval(fetchCurrentPrices, 3000)
})

onUnmounted(() => {
  if (priceInterval) {
    clearInterval(priceInterval)
  }
})
</script>

<style lang="scss" scoped>
.positions-card {
  height: 100%;
  display: flex;
  flex-direction: column;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 0;
    border: none;

    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;

      .icon-wrapper {
        width: 48px;
        height: 48px;
      }

      .title-info {
        .card-title {
          font-size: 16px;
          font-weight: 600;
          color: #ffffff;
          margin: 0;
          padding: 0;
          border: none;
        }

        .card-subtitle {
          font-size: 12px;
          color: rgba(255, 255, 255, 0.6);
          margin-top: 4px;
        }
      }
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 8px;

      .sim-tag {
        margin-right: 8px;
        background-color: #e6a23c;
        color: #fff;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;

        .el-icon {
          font-size: 14px;
          color: #fff;
        }
      }
    }
  }

  .positions-list {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 16px;
    overflow-y: auto;
    padding-right: 4px;

    .position-item {
      background: rgba(255, 255, 255, 0.05);
      border-radius: $border-radius-sm;
      padding: 16px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      transition: all $transition-normal;

      &:hover {
        border-color: rgba(102, 126, 234, 0.3);
        box-shadow: $dark-shadow;
      }

      &.simulation {
        border-color: rgba($warning-color, 0.3);
        background: rgba($warning-color, 0.02);
      }

      .position-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;

        .coin-info {
          display: flex;
          align-items: center;
          gap: 12px;

          .coin-details {
            display: flex;
            flex-direction: column;
            gap: 4px;
          }

          .coin-name {
            font-size: 16px;
            font-weight: 600;
            color: #ffffff;
          }
        }

        .pnl-badge {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 6px 12px;
          border-radius: 12px;
          font-size: 14px;
          font-weight: 600;

          &.positive {
            background: rgba($success-color, 0.1);
            color: $success-color;
          }

          &.negative {
            background: rgba($danger-color, 0.1);
            color: $danger-color;
          }
        }
      }

      .position-details {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
        margin-bottom: 12px;

        .detail-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 12px;
          background: rgba(0, 0, 0, 0.02);
          border-radius: $border-radius-xs;

          .label {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.6);
          }

          .value {
            font-size: 13px;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.8);

            &.positive {
              color: $success-color;
            }

            &.negative {
              color: $danger-color;
            }
          }
        }
      }

      .position-actions {
        display: flex;
        justify-content: flex-end;
        padding-top: 12px;
        border-top: 1px solid rgba(255, 255, 255, 0.1);

        .sim-position-tag {
          background-color: #e6a23c;
          color: #fff;
          font-weight: 500;
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 6px 12px;
          border-radius: 4px;
          font-size: 13px;
          white-space: nowrap;

          .el-icon {
            font-size: 14px;
            color: #fff;
            flex-shrink: 0;
          }
        }
      }
    }
  }

  .empty-state {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 300px;
  }
}
</style>
