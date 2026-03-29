<template>
  <div class="bandtrade-card card">
    <div class="card-header">
      <div class="header-left">
        <div class="card-icon gradient-icon purple">
          <el-icon :size="20"><TrendCharts /></el-icon>
        </div>
        <div class="title-section">
          <div class="card-title">波段操作</div>
          <div class="card-subtitle">回调加仓与移动止损</div>
        </div>
      </div>
      <div class="header-actions">
        <el-switch v-model="config.enabled" @change="updateConfig" size="default" />
      </div>
    </div>
    
    <div class="config-tip" style="margin-bottom: 16px;">
      <span class="tip-icon">💡</span>
      <span>分层止盈配置已整合到策略配置页的"止盈止损"中，此处仅保留回调加仓和移动止损配置</span>
    </div>
    
    <div class="config-section">
      <div class="section-title">回调加仓</div>
      <div class="config-row">
        <span>启用</span>
        <el-switch v-model="config.callback_buy_enabled" @change="updateConfig" />
      </div>
      <div class="config-row">
        <span>回调阈值</span>
        <el-input-number v-model="config.callback_buy_threshold" :min="-10" :max="0" :step="0.5" size="small" @change="updateConfig" />
        <span>%</span>
      </div>
      <div class="config-row">
        <span>最大加仓次数</span>
        <el-input-number v-model="config.max_callback_buys" :min="0" :max="5" size="small" @change="updateConfig" />
      </div>
    </div>
    
    <div class="config-section">
      <div class="section-title">移动止损</div>
      <div class="config-row">
        <span>启用</span>
        <el-switch v-model="config.trailing_stop_enabled" @change="updateConfig" />
      </div>
      <div class="config-row">
        <span>触发阈值</span>
        <el-input-number v-model="config.trailing_stop_trigger" :min="1" :max="20" size="small" @change="updateConfig" />
        <span>%</span>
      </div>
      <div class="config-row">
        <span>止损距离</span>
        <el-input-number v-model="config.trailing_stop_distance" :min="0.5" :max="10" :step="0.5" size="small" @change="updateConfig" />
        <span>%</span>
      </div>
    </div>
    
    <div class="positions-section" v-if="Object.keys(positions).length > 0">
      <div class="section-title">当前波段仓位</div>
      <div class="positions-list">
        <div v-for="(pos, coin) in positions" :key="coin" class="position-item">
          <div class="pos-header">
            <span class="pos-coin">{{ coin }}</span>
            <el-button size="small" type="danger" text @click="removePosition(coin)">移除</el-button>
          </div>
          <div class="pos-details">
            <span>入场: ${{ formatPrice(pos.entry_price) }}</span>
            <span>数量: {{ pos.current_amount.toFixed(4) }}</span>
            <span>剩余: {{ pos.remaining_percent.toFixed(0) }}%</span>
          </div>
          <div class="pos-status">
            <el-tag v-if="pos.trailing_stop_activated" type="success" size="small">移动止损激活</el-tag>
            <el-tag v-if="pos.callback_buy_count > 0" type="info" size="small">加仓{{ pos.callback_buy_count }}次</el-tag>
            <el-tag v-if="pos.take_profit_executed.length > 0" type="warning" size="small">
              止盈{{ pos.take_profit_executed.length }}层
            </el-tag>
          </div>
        </div>
      </div>
    </div>
    
    <div class="add-position">
      <el-button size="small" type="primary" @click="showAddDialog = true">添加波段仓位</el-button>
    </div>
    
    <el-dialog v-model="showAddDialog" title="添加波段仓位" width="300px">
      <el-form>
        <el-form-item label="币种">
          <el-input v-model="newPosition.coin" placeholder="如: BTC" />
        </el-form-item>
        <el-form-item label="入场价格">
          <el-input-number v-model="newPosition.price" :min="0" :precision="4" style="width: 100%" />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="newPosition.amount" :min="0" :precision="4" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addPosition">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { TrendCharts } from '@element-plus/icons-vue'

interface BandConfig {
  enabled: boolean
  take_profit_levels: Array<{ trigger_percent: number; sell_percent: number }>
  callback_buy_enabled: boolean
  callback_buy_threshold: number
  max_callback_buys: number
  trailing_stop_enabled: boolean
  trailing_stop_trigger: number
  trailing_stop_distance: number
}

const config = reactive<BandConfig>({
  enabled: true,
  take_profit_levels: [
    { trigger_percent: 3, sell_percent: 30 },
    { trigger_percent: 5, sell_percent: 30 },
    { trigger_percent: 8, sell_percent: 40 }
  ],
  callback_buy_enabled: true,
  callback_buy_threshold: -3,
  max_callback_buys: 2,
  trailing_stop_enabled: true,
  trailing_stop_trigger: 5,
  trailing_stop_distance: 2
})

const positions = ref<Record<string, any>>({})
const showAddDialog = ref(false)
const newPosition = reactive({
  coin: '',
  price: 0,
  amount: 0
})

function formatPrice(price: number): string {
  if (price >= 1000) return price.toFixed(0)
  if (price >= 1) return price.toFixed(2)
  return price.toFixed(6)
}

async function fetchConfig() {
  try {
    const response = await fetch('/api/v1/services/bandtrade/config')
    if (response.ok) {
      const data = await response.json()
      Object.assign(config, data)
    }
  } catch (error) {
    console.error('Failed to fetch config:', error)
  }
}

async function fetchPositions() {
  try {
    const response = await fetch('/api/v1/services/bandtrade/positions')
    if (response.ok) {
      positions.value = await response.json()
    }
  } catch (error) {
    console.error('Failed to fetch positions:', error)
  }
}

async function updateConfig() {
  try {
    const response = await fetch('/api/v1/services/bandtrade/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    })
    if (response.ok) {
      ElMessage.success('配置已更新')
    }
  } catch (error) {
    ElMessage.error('更新失败')
  }
}

async function addPosition() {
  if (!newPosition.coin || newPosition.price <= 0) {
    ElMessage.warning('请填写完整信息')
    return
  }
  
  try {
    const response = await fetch(`/api/v1/services/bandtrade/position/${newPosition.coin.toUpperCase()}?entry_price=${newPosition.price}&amount=${newPosition.amount}`, {
      method: 'POST'
    })
    if (response.ok) {
      ElMessage.success('仓位已添加')
      showAddDialog.value = false
      newPosition.coin = ''
      newPosition.price = 0
      newPosition.amount = 0
      fetchPositions()
    }
  } catch (error) {
    ElMessage.error('添加失败')
  }
}

async function removePosition(coin: string) {
  try {
    const response = await fetch(`/api/v1/services/bandtrade/position/${coin}`, {
      method: 'DELETE'
    })
    if (response.ok) {
      ElMessage.success('仓位已移除')
      fetchPositions()
    }
  } catch (error) {
    ElMessage.error('移除失败')
  }
}

onMounted(() => {
  fetchConfig()
  fetchPositions()
})
</script>

<style lang="scss" scoped>
.bandtrade-card {
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
    margin-bottom: 24px;

    .section-title {
      font-size: 15px;
      font-weight: 600;
      margin-bottom: 16px;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 8px;

      &::before {
        content: '';
        width: 4px;
        height: 16px;
        background: $gradient-purple;
        border-radius: 2px;
      }
    }

    .levels-list {
      .level-item {
        display: flex;
        justify-content: space-between;
        padding: 12px 16px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        margin-bottom: 8px;
        font-size: 13px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all $transition-normal;

        &:hover {
          background: rgba(255, 255, 255, 0.1);
          box-shadow: $dark-shadow;
        }

        .level-name {
          font-weight: 600;
          color: #ffffff;
        }

        .level-trigger {
          color: $success-color;
          font-weight: 500;
        }

        .level-sell {
          color: $warning-color;
          font-weight: 500;
        }
      }
    }

    .config-row {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
      font-size: 14px;

      span:first-child {
        min-width: 110px;
        color: rgba(255, 255, 255, 0.7);
        font-weight: 500;
      }
    }
  }

  .positions-section {
    margin-top: 24px;
    padding-top: 24px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);

    .positions-list {
      .position-item {
        padding: 16px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        margin-bottom: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all $transition-normal;

        &:hover {
          background: rgba(255, 255, 255, 0.1);
          box-shadow: $dark-shadow;
        }

        .pos-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;

          .pos-coin {
            font-size: 18px;
            font-weight: 700;
            color: #ffffff;
          }
        }

        .pos-details {
          display: flex;
          gap: 20px;
          font-size: 14px;
          color: rgba(255, 255, 255, 0.7);
          margin-bottom: 12px;
          flex-wrap: wrap;
        }

        .pos-status {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }
      }
    }
  }

  .add-position {
    margin-top: 20px;
  }
}
</style>
