<template>
  <div class="grid-trading-card card">
    <div class="card-header">
      <span class="title">📊 网格交易策略</span>
      <el-tabs v-model="activeStrategy" size="small" class="strategy-tabs">
        <el-tab-pane label="基础网格" name="grid" />
        <el-tab-pane label="趋势追踪" name="trend" />
        <el-tab-pane label="智能网格" name="smartgrid" />
      </el-tabs>
    </div>
    
    <div class="card-content">
      <div v-if="activeStrategy === 'grid'" class="strategy-content">
        <div class="status-section">
          <div class="section-title">基础网格状态</div>
          <div v-if="Object.keys(gridStatus.grids || {}).length === 0" class="empty-state">
            暂无配置的网格
          </div>
          <div v-else class="grid-list">
            <div v-for="(grid, name) in gridStatus.grids" :key="name" class="grid-item">
              <div class="grid-header">
                <span class="grid-name">{{ name }}</span>
                <el-tag :type="grid.enabled ? 'success' : 'info'" size="small">
                  {{ grid.enabled ? '运行中' : '已停止' }}
                </el-tag>
              </div>
              <div class="grid-info">
                <span>币种: {{ grid.inst_id }}</span>
                <span>区间: ${{ grid.min_price }} - ${{ grid.max_price }}</span>
                <span>网格数: {{ grid.grid_num }}</span>
                <el-tag v-if="grid.enable_short" type="danger" size="small">双向做空</el-tag>
                <el-tag v-else type="success" size="small">单向做多</el-tag>
                <span>上次价格: {{ grid.last_trade_price ? '$' + grid.last_trade_price.toFixed(4) : '未交易' }}</span>
              </div>
              <el-button type="danger" size="small" @click="removeGrid(String(name))">移除</el-button>
            </div>
          </div>
        </div>
        
        <div class="add-section">
          <div class="section-title">添加新网格</div>
          <el-form :model="newGrid" inline size="small">
            <el-form-item label="名称">
              <el-input v-model="newGrid.name" placeholder="如: ETH网格" />
            </el-form-item>
            <el-form-item label="币种">
              <el-input v-model="newGrid.inst_id" placeholder="如: ETH-USDT" />
            </el-form-item>
            <el-form-item label="最低价">
              <el-input-number v-model="newGrid.min_price" :min="0" :precision="4" />
            </el-form-item>
            <el-form-item label="最高价">
              <el-input-number v-model="newGrid.max_price" :min="0" :precision="4" />
            </el-form-item>
            <el-form-item label="网格数">
              <el-input-number v-model="newGrid.grid_num" :min="5" :max="100" />
            </el-form-item>
            <el-form-item label="做空模式">
              <el-switch v-model="newGrid.enable_short" />
              <span class="hint-text">开启后将使用合约双向交易</span>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="addGrid">添加</el-button>
            </el-form-item>
          </el-form>
        </div>
        
        <div class="action-buttons">
          <el-button type="primary" @click="runGridCycle" :loading="loading">执行网格周期</el-button>
        </div>
      </div>
      
      <div v-if="activeStrategy === 'trend'" class="strategy-content">
        <div class="status-section">
          <div class="section-title">趋势追踪状态</div>
          <div class="trend-stats">
            <div class="stat-item">
              <span class="label">持仓数</span>
              <span class="value">{{ Object.keys(trendStatus.positions || {}).length }}</span>
            </div>
            <div class="stat-item">
              <span class="label">今日交易</span>
              <span class="value">{{ trendStatus.daily_stats?.trade_count || 0 }}</span>
            </div>
            <div class="stat-item">
              <span class="label">今日亏损</span>
              <span class="value" :class="{ 'loss': (trendStatus.daily_stats?.loss || 0) > 0 }">
                ${{ (trendStatus.daily_stats?.loss || 0).toFixed(2) }}
              </span>
            </div>
          </div>
          
          <div v-if="Object.keys(trendStatus.positions || {}).length > 0" class="positions-list">
            <div v-for="(pos, coin) in trendStatus.positions" :key="coin" class="position-item">
              <div class="pos-header">
                <span class="coin-name">{{ coin }}</span>
                <span class="entry-price">入场: ${{ pos.entry_price.toFixed(4) }}</span>
              </div>
              <div class="pos-info">
                <span>数量: {{ pos.amount.toFixed(4) }}</span>
                <span>止损: ${{ pos.stop_loss.toFixed(4) }}</span>
                <span>止盈: ${{ pos.take_profit.toFixed(4) }}</span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="action-buttons">
          <el-button type="primary" @click="runTrendCycle" :loading="loading">执行趋势周期</el-button>
        </div>
      </div>
      
      <div v-if="activeStrategy === 'smartgrid'" class="strategy-content">
        <div class="status-section">
          <div class="section-title">智能网格状态</div>
          <div class="sentiment-info">
            <span>舆情评分: {{ smartgridStatus.sentiment_score || 5 }}/10</span>
            <span>趋势: {{ smartgridStatus.sentiment_trend || 'neutral' }}</span>
          </div>
          
          <div class="settings-info">
            <span>止损: {{ smartgridStatus.settings?.stop_loss_percent || -10 }}%</span>
            <span>止盈: {{ smartgridStatus.settings?.take_profit_percent || 5 }}%</span>
            <span>最大持仓: {{ smartgridStatus.settings?.max_position_per_coin || 30 }}%</span>
          </div>
          
          <div v-if="Object.keys(smartgridStatus.grids || {}).length === 0" class="empty-state">
            暂无配置的智能网格
          </div>
          <div v-else class="grid-list">
            <div v-for="(grid, name) in smartgridStatus.grids" :key="name" class="grid-item">
              <div class="grid-header">
                <span class="grid-name">{{ name }}</span>
                <span class="grid-range">${{ grid.min_price?.toFixed(2) }} - ${{ grid.max_price?.toFixed(2) }}</span>
              </div>
              <div class="grid-info">
                <span>多仓: {{ grid.position?.toFixed(4) || 0 }} @${{ grid.avg_price?.toFixed(4) || 0 }}</span>
                <span>空仓: {{ grid.short_position?.toFixed(4) || 0 }} @${{ grid.short_avg_price?.toFixed(4) || 0 }}</span>
                <span>上次价格: {{ grid.last_trade_price ? '$' + grid.last_trade_price.toFixed(4) : '未交易' }}</span>
              </div>
              <el-button type="danger" size="small" @click="removeSmartgrid(String(name))">移除</el-button>
            </div>
          </div>
        </div>
        
        <div class="add-section">
          <div class="section-title">添加智能网格</div>
          <el-form :model="newSmartgrid" inline size="small">
            <el-form-item label="名称">
              <el-input v-model="newSmartgrid.name" placeholder="如: ETH智能" />
            </el-form-item>
            <el-form-item label="币种">
              <el-input v-model="newSmartgrid.inst_id" placeholder="如: ETH-USDT" />
            </el-form-item>
            <el-form-item label="最低价">
              <el-input-number v-model="newSmartgrid.min_price" :min="0" :precision="2" />
            </el-form-item>
            <el-form-item label="最高价">
              <el-input-number v-model="newSmartgrid.max_price" :min="0" :precision="2" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="addSmartgrid">添加</el-button>
            </el-form-item>
          </el-form>
        </div>
        
        <div class="action-buttons">
          <el-button type="primary" @click="runSmartgridCycle" :loading="loading">执行智能网格</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const activeStrategy = ref('grid')
const loading = ref(false)

const gridStatus = ref<any>({ grids: {} })
const trendStatus = ref<any>({ positions: {}, daily_stats: {} })
const smartgridStatus = ref<any>({ grids: {}, settings: {}, sentiment_score: 5, sentiment_trend: 'neutral' })

const newGrid = ref({
  name: '',
  inst_id: '',
  min_price: 0,
  max_price: 0,
  grid_num: 10,
  enable_short: false
})

const newSmartgrid = ref({
  name: '',
  inst_id: '',
  min_price: 0,
  max_price: 0
})

async function fetchGridStatus() {
  try {
    const response = await fetch('/api/v1/services/grid/status')
    if (response.ok) {
      gridStatus.value = await response.json()
    }
  } catch (error) {
    console.error('Failed to fetch grid status:', error)
  }
}

async function fetchTrendStatus() {
  try {
    const response = await fetch('/api/v1/services/trendstrategy/status')
    if (response.ok) {
      trendStatus.value = await response.json()
    }
  } catch (error) {
    console.error('Failed to fetch trend status:', error)
  }
}

async function fetchSmartgridStatus() {
  try {
    const response = await fetch('/api/v1/services/smartgrid/status')
    if (response.ok) {
      smartgridStatus.value = await response.json()
    }
  } catch (error) {
    console.error('Failed to fetch smartgrid status:', error)
  }
}

async function addGrid() {
  if (!newGrid.value.name || !newGrid.value.inst_id) {
    ElMessage.warning('请填写完整信息')
    return
  }
  loading.value = true
  try {
    const response = await fetch('/api/v1/services/grid/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: newGrid.value.name,
        inst_id: newGrid.value.inst_id,
        min_price: newGrid.value.min_price,
        max_price: newGrid.value.max_price,
        grid_num: newGrid.value.grid_num,
        enable_short: newGrid.value.enable_short
      })
    })
    if (response.ok) {
      ElMessage.success('网格添加成功')
      newGrid.value = { name: '', inst_id: '', min_price: 0, max_price: 0, grid_num: 10, enable_short: false }
      await fetchGridStatus()
    }
  } catch (error) {
    ElMessage.error('添加失败')
  } finally {
    loading.value = false
  }
}

async function removeGrid(name: string) {
  try {
    const response = await fetch(`/api/v1/services/grid/${name}`, { method: 'DELETE' })
    if (response.ok) {
      ElMessage.success('网格已移除')
      await fetchGridStatus()
    }
  } catch (error) {
    ElMessage.error('移除失败')
  }
}

async function runGridCycle() {
  loading.value = true
  try {
    const response = await fetch('/api/v1/services/grid/run', { method: 'POST' })
    if (response.ok) {
      await response.json()
      ElMessage.success('网格周期执行完成')
      await fetchGridStatus()
    }
  } catch (error) {
    ElMessage.error('执行失败')
  } finally {
    loading.value = false
  }
}

async function runTrendCycle() {
  loading.value = true
  try {
    const response = await fetch('/api/v1/services/trendstrategy/run', { method: 'POST' })
    if (response.ok) {
      ElMessage.success('趋势周期执行完成')
      await fetchTrendStatus()
    }
  } catch (error) {
    ElMessage.error('执行失败')
  } finally {
    loading.value = false
  }
}

async function addSmartgrid() {
  if (!newSmartgrid.value.name || !newSmartgrid.value.inst_id) {
    ElMessage.warning('请填写完整信息')
    return
  }
  loading.value = true
  try {
    const response = await fetch('/api/v1/services/smartgrid/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: newSmartgrid.value.name,
        inst_id: newSmartgrid.value.inst_id,
        min_price: newSmartgrid.value.min_price,
        max_price: newSmartgrid.value.max_price
      })
    })
    if (response.ok) {
      ElMessage.success('智能网格添加成功')
      newSmartgrid.value = { name: '', inst_id: '', min_price: 0, max_price: 0 }
      await fetchSmartgridStatus()
    }
  } catch (error) {
    ElMessage.error('添加失败')
  } finally {
    loading.value = false
  }
}

async function removeSmartgrid(name: string) {
  try {
    const response = await fetch(`/api/v1/services/smartgrid/${name}`, { method: 'DELETE' })
    if (response.ok) {
      ElMessage.success('智能网格已移除')
      await fetchSmartgridStatus()
    }
  } catch (error) {
    ElMessage.error('移除失败')
  }
}

async function runSmartgridCycle() {
  loading.value = true
  try {
    const response = await fetch('/api/v1/services/smartgrid/run', { method: 'POST' })
    if (response.ok) {
      ElMessage.success('智能网格周期执行完成')
      await fetchSmartgridStatus()
    }
  } catch (error) {
    ElMessage.error('执行失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchGridStatus()
  fetchTrendStatus()
  fetchSmartgridStatus()
})
</script>

<style lang="scss" scoped>
.grid-trading-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
    
    .title {
      font-size: 16px;
      font-weight: 600;
    }
    
    .strategy-tabs {
      max-width: 300px;
    }
  }
  
  .card-content {
    margin-top: 16px;
  }
  
  .strategy-content {
    .section-title {
      font-size: 13px;
      font-weight: 600;
      color: #ffffff;
      margin-bottom: 12px;
    }
  }

  .status-section {
    margin-bottom: 16px;
  }

  .empty-state {
    text-align: center;
    padding: 30px;
    color: rgba(255, 255, 255, 0.7);
  }

  .grid-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .grid-item {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);

    .grid-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;

      .grid-name {
        font-weight: 600;
        color: #ffffff;
      }

      .grid-range {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.7);
      }
    }

    .grid-info {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      font-size: 12px;
      color: rgba(255, 255, 255, 0.7);
      margin-bottom: 8px;
    }
  }

  .trend-stats {
    display: flex;
    gap: 16px;
    margin-bottom: 16px;

    .stat-item {
      display: flex;
      flex-direction: column;
      gap: 4px;

      .label {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.6);
      }

      .value {
        font-size: 16px;
        font-weight: 600;
        color: #ffffff;

        &.loss {
          color: #ff4d4f;
        }
      }
    }
  }

  .positions-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .position-item {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);

    .pos-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;

      .coin-name {
        font-weight: 600;
        color: #ffffff;
      }

      .entry-price {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.7);
      }
    }

    .pos-info {
      display: flex;
      gap: 12px;
      font-size: 12px;
      color: rgba(255, 255, 255, 0.7);
    }
  }

  .sentiment-info, .settings-info {
    display: flex;
    gap: 16px;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.6);
    margin-bottom: 12px;
  }

  .add-section {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 16px;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }
  
  .action-buttons {
    display: flex;
    gap: 12px;
  }

  .hint-text {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.5);
    margin-left: 8px;
  }
}
</style>
