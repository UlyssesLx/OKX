<template>
  <div class="trade-stats-card card">
    <div class="card-header">
      <span class="card-title">📊 交易统计</span>
      <div class="header-actions">
        <el-radio-group v-model="statsMode" size="small">
          <el-radio-button value="real">实盘</el-radio-button>
          <el-radio-button value="simulation">模拟盘</el-radio-button>
          <el-radio-button value="all">全部</el-radio-button>
        </el-radio-group>
        <el-button size="small" @click="fetchStats" :loading="loading">刷新</el-button>
      </div>
    </div>

    <div v-if="stats" class="stats-content">
      <div class="summary-grid">
        <div class="summary-item">
          <span class="label">总交易</span>
          <span class="value">{{ stats.summary.total_trades }}</span>
        </div>
        <div class="summary-item">
          <span class="label">买入</span>
          <span class="value">{{ stats.summary.buy_count }}</span>
        </div>
        <div class="summary-item">
          <span class="label">卖出</span>
          <span class="value">{{ stats.summary.sell_count }}</span>
        </div>
        <div class="summary-item">
          <span class="label">胜率</span>
          <span class="value" :class="stats.summary.win_rate >= 50 ? 'positive' : 'negative'">
            {{ stats.summary.win_rate }}%
          </span>
        </div>
      </div>

      <div class="profit-section">
        <div class="profit-item">
          <span class="label">平均盈利</span>
          <span class="value positive">+{{ stats.summary.avg_profit }}%</span>
        </div>
        <div class="profit-item">
          <span class="label">平均亏损</span>
          <span class="value negative">-{{ stats.summary.avg_loss }}%</span>
        </div>
        <div class="profit-item">
          <span class="label">盈亏比</span>
          <span class="value">{{ stats.summary.profit_loss_ratio }}</span>
        </div>
      </div>

      <div class="total-section">
        <div class="total-item">
          <span class="label">总盈利</span>
          <span class="value positive">+{{ stats.summary.total_profit }}%</span>
        </div>
        <div class="total-item">
          <span class="label">总亏损</span>
          <span class="value negative">-{{ stats.summary.total_loss }}%</span>
        </div>
        <div class="total-item highlight">
          <span class="label">净盈亏</span>
          <span class="value" :class="Number(stats.summary.net_profit) >= 0 ? 'positive' : 'negative'">
            {{ Number(stats.summary.net_profit) >= 0 ? '+' : '' }}{{ stats.summary.net_profit }}%
          </span>
        </div>
      </div>

      <!-- 模拟盘额外信息 -->
      <div v-if="statsMode === 'simulation' || statsMode === 'all'" class="simulation-section">
        <div class="section-title">💰 模拟盘资金</div>
        <div class="simulation-stats">
          <div class="sim-item">
            <span class="label">初始资金</span>
            <span class="value">${{ simulationStats.initial_balance.toFixed(2) }}</span>
          </div>
          <div class="sim-item">
            <span class="label">可用资金</span>
            <span class="value">${{ simulationStats.available_balance.toFixed(2) }}</span>
          </div>
          <div class="sim-item">
            <span class="label">持仓盈亏</span>
            <span class="value" :class="simulationStats.total_pnl >= 0 ? 'positive' : 'negative'">
              {{ simulationStats.total_pnl >= 0 ? '+' : '' }}${{ simulationStats.total_pnl.toFixed(2) }}
            </span>
          </div>
          <div class="sim-item">
            <span class="label">总收益率</span>
            <span class="value" :class="simulationReturn >= 0 ? 'positive' : 'negative'">
              {{ simulationReturn >= 0 ? '+' : '' }}{{ simulationReturn.toFixed(2) }}%
            </span>
          </div>
        </div>
      </div>

      <div class="today-section" v-if="stats.today">
        <div class="section-title">📅 今日交易</div>
        <div class="today-stats">
          <span>交易 {{ stats.today.trades }} 笔</span>
          <span>买入 {{ stats.today.buys }} 次</span>
          <span>卖出 {{ stats.today.sells }} 次</span>
          <span>金额 ${{ stats.today.volume }}</span>
        </div>
      </div>

      <div class="coin-stats" v-if="stats.coin_stats && Object.keys(stats.coin_stats).length > 0">
        <div class="section-title">💰 币种表现</div>
        <div class="coin-list">
          <div v-for="(stat, coin) in stats.coin_stats" :key="coin" class="coin-item">
            <span class="coin-name">{{ coin }}</span>
            <span class="coin-detail">买{{ stat.buys }}/卖{{ stat.sells }}</span>
            <span class="coin-result" :class="stat.profit > stat.loss ? 'positive' : 'negative'">
              {{ stat.profit }}胜/{{ stat.loss }}负
            </span>
          </div>
        </div>
      </div>

      <div class="charts-section">
        <div class="chart-card">
          <div class="chart-title">📈 资产趋势</div>
          <div class="chart-container" ref="equityChartRef"></div>
        </div>
        <div class="chart-card">
          <div class="chart-title">🥧 交易统计</div>
          <div class="chart-container" ref="tradesChartRef"></div>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <span>暂无交易数据</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { tradingApi } from '@/api'

function getBeijingDate(): string {
  const now = new Date()
  const beijingTime = new Date(now.getTime() + (now.getTimezoneOffset() * 60000) + (8 * 3600000))
  return beijingTime.toISOString().split('T')[0]
}

interface StatsData {
  summary: {
    total_trades: number
    buy_count: number
    sell_count: number
    win_rate: number
    avg_profit: string | number
    avg_loss: string | number
    profit_loss_ratio: string | number
    total_profit: string | number
    total_loss: string | number
    net_profit: string | number
  }
  today: {
    date: string
    trades: number
    buys: number
    sells: number
    volume: string | number
  }
  coin_stats: Record<string, { buys: number; sells: number; profit: number; loss: number }>
}

interface SimulationStats {
  total_pnl: number
  win_count: number
  loss_count: number
  total_trades: number
  win_rate: number
  position_count: number
  initial_balance: number
  available_balance: number
}

const stats = ref<StatsData | null>(null)
const simulationStats = ref<SimulationStats>({
  total_pnl: 0,
  win_count: 0,
  loss_count: 0,
  total_trades: 0,
  win_rate: 0,
  position_count: 0,
  initial_balance: 1000,
  available_balance: 1000
})
const loading = ref(false)
const statsMode = ref<'real' | 'simulation' | 'all'>('real')

const equityChartRef = ref<HTMLElement>()
const tradesChartRef = ref<HTMLElement>()
let equityChart: echarts.ECharts | null = null
let tradesChart: echarts.ECharts | null = null

// 计算模拟盘收益率
const simulationReturn = computed(() => {
  if (simulationStats.value.initial_balance === 0) return 0
  return (simulationStats.value.total_pnl / simulationStats.value.initial_balance) * 100
})

async function fetchStats() {
  loading.value = true
  try {
    // 获取实盘统计
    const response = await fetch('/api/v1/services/stats')
    let realStats = null
    if (response.ok) {
      realStats = await response.json()
    }

    // 获取模拟盘统计和交易记录
    const [simResponse, simTradesResponse] = await Promise.all([
      tradingApi.getSimulationStats(),
      tradingApi.getSimulationTrades(200)
    ])
    simulationStats.value = simResponse.stats

    // 合并模拟盘数据
    const simData = {
      ...simResponse,
      trades: simTradesResponse.trades
    }

    // 根据模式合并数据
    if (statsMode.value === 'real') {
      stats.value = realStats
    } else if (statsMode.value === 'simulation') {
      // 构建模拟盘统计
      stats.value = buildSimulationStats(simData)
    } else {
      // 合并全部
      stats.value = mergeStats(realStats, simData)
    }

    // 更新图表
    updateCharts()
  } catch (error) {
    console.error('Failed to fetch stats:', error)
  } finally {
    loading.value = false
  }
}

function buildSimulationStats(simData: any): StatsData {
  const trades = simData.trades || []
  const buyTrades = trades.filter((t: any) => t.action === 'buy')
  const sellTrades = trades.filter((t: any) => t.action === 'sell')
  const winTrades = sellTrades.filter((t: any) => (t.pnl || 0) > 0)
  const lossTrades = sellTrades.filter((t: any) => (t.pnl || 0) <= 0)

  // 计算今日数据（使用北京时间）
  const today = getBeijingDate()
  const todayTrades = trades.filter((t: any) => t.timestamp?.startsWith(today))
  const todayVolume = todayTrades.reduce((sum: number, t: any) => sum + (t.usdt_value || 0), 0)

  // 计算币种统计
  const coinStats: Record<string, { buys: number; sells: number; profit: number; loss: number }> = {}
  for (const t of trades) {
    if (!coinStats[t.coin]) {
      coinStats[t.coin] = { buys: 0, sells: 0, profit: 0, loss: 0 }
    }
    if (t.action === 'buy') {
      coinStats[t.coin].buys++
    } else {
      coinStats[t.coin].sells++
      if ((t.pnl || 0) > 0) {
        coinStats[t.coin].profit++
      } else if ((t.pnl || 0) < 0) {
        coinStats[t.coin].loss++
      }
    }
  }

  return {
    summary: {
      total_trades: trades.length,
      buy_count: buyTrades.length,
      sell_count: sellTrades.length,
      win_rate: sellTrades.length > 0 ? Math.round((winTrades.length / sellTrades.length) * 100) : 0,
      avg_profit: winTrades.length > 0 ? parseFloat((winTrades.reduce((s: number, t: any) => s + (t.pnl_percent || 0), 0) / winTrades.length).toFixed(2)) : 0,
      avg_loss: lossTrades.length > 0 ? parseFloat((Math.abs(lossTrades.reduce((s: number, t: any) => s + (t.pnl_percent || 0), 0)) / lossTrades.length).toFixed(2)) : 0,
      profit_loss_ratio: lossTrades.length > 0 ? parseFloat((winTrades.length / lossTrades.length).toFixed(2)) : 0,
      total_profit: parseFloat(winTrades.reduce((s: number, t: any) => s + (t.pnl_percent || 0), 0).toFixed(2)),
      total_loss: parseFloat(Math.abs(lossTrades.reduce((s: number, t: any) => s + (t.pnl_percent || 0), 0)).toFixed(2)),
      net_profit: parseFloat((simData.stats.total_pnl / simData.stats.initial_balance * 100).toFixed(2))
    },
    today: {
      date: today,
      trades: todayTrades.length,
      buys: todayTrades.filter((t: any) => t.action === 'buy').length,
      sells: todayTrades.filter((t: any) => t.action === 'sell').length,
      volume: parseFloat(todayVolume.toFixed(2))
    },
    coin_stats: coinStats
  }
}

function mergeStats(realStats: StatsData | null, simData: any): StatsData {
  const simStats = buildSimulationStats(simData)

  if (!realStats) return simStats

  return {
    summary: {
      total_trades: realStats.summary.total_trades + simStats.summary.total_trades,
      buy_count: realStats.summary.buy_count + simStats.summary.buy_count,
      sell_count: realStats.summary.sell_count + simStats.summary.sell_count,
      win_rate: Math.round((realStats.summary.win_rate + simStats.summary.win_rate) / 2),
      avg_profit: ((Number(realStats.summary.avg_profit) + Number(simStats.summary.avg_profit)) / 2),
      avg_loss: ((Number(realStats.summary.avg_loss) + Number(simStats.summary.avg_loss)) / 2),
      profit_loss_ratio: ((Number(realStats.summary.profit_loss_ratio) + Number(simStats.summary.profit_loss_ratio)) / 2),
      total_profit: Number(realStats.summary.total_profit) + Number(simStats.summary.total_profit),
      total_loss: Number(realStats.summary.total_loss) + Number(simStats.summary.total_loss),
      net_profit: Number(realStats.summary.net_profit) + Number(simStats.summary.net_profit)
    },
    today: {
      date: realStats.today.date,
      trades: realStats.today.trades + simStats.today.trades,
      buys: realStats.today.buys + simStats.today.buys,
      sells: realStats.today.sells + simStats.today.sells,
      volume: Number(realStats.today.volume) + Number(simStats.today.volume)
    },
    coin_stats: { ...realStats.coin_stats, ...simStats.coin_stats }
  }
}

function updateCharts() {
  if (!stats.value) return

  if (equityChart) {
    equityChart.setOption({
      series: [{
        data: generateEquityData()
      }]
    })
  }

  if (tradesChart) {
    tradesChart.setOption({
      series: [{
        data: [
          { value: stats.value.summary.buy_count, name: '买入' },
          { value: stats.value.summary.sell_count, name: '卖出' }
        ]
      }]
    })
  }
}

function generateEquityData() {
  // 根据模式生成不同的资产曲线数据
  const baseValue = statsMode.value === 'simulation' ? simulationStats.value.initial_balance : 287
  const netProfit = Number(stats.value?.summary.net_profit || 0)
  const currentValue = statsMode.value === 'simulation'
    ? simulationStats.value.initial_balance + simulationStats.value.total_pnl
    : baseValue * (1 + netProfit / 100)

  // 生成7天的模拟数据
  const data = []
  for (let i = 0; i < 7; i++) {
    const progress = i / 6
    data.push(baseValue + (currentValue - baseValue) * progress)
  }
  return data
}

function initCharts() {
  if (equityChartRef.value) {
    equityChart = echarts.init(equityChartRef.value)
    equityChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
        axisLabel: { color: 'rgba(255,255,255,0.7)' }
      },
      yAxis: {
        type: 'value',
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
        axisLabel: { color: 'rgba(255,255,255,0.7)' },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } }
      },
      series: [{
        data: generateEquityData(),
        type: 'line',
        smooth: true,
        lineStyle: { color: '#667eea', width: 3 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(102, 126, 234, 0.3)' },
            { offset: 1, color: 'rgba(102, 126, 234, 0)' }
          ])
        }
      }]
    })
  }

  if (tradesChartRef.value) {
    tradesChart = echarts.init(tradesChartRef.value)
    tradesChart.setOption({
      tooltip: { trigger: 'item' },
      legend: {
        top: '5%',
        left: 'center',
        textStyle: { color: 'rgba(255,255,255,0.7)' }
      },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 20,
            fontWeight: 'bold',
            color: '#ffffff'
          }
        },
        labelLine: { show: false },
        data: [
          { value: stats.value?.summary.buy_count || 0, name: '买入', itemStyle: { color: '#67c23a' } },
          { value: stats.value?.summary.sell_count || 0, name: '卖出', itemStyle: { color: '#f56c6c' } }
        ]
      }]
    })
  }
}

// 监听模式变化
watch(statsMode, () => {
  fetchStats()
})

onMounted(() => {
  fetchStats()
  initCharts()
})

onUnmounted(() => {
  if (equityChart) {
    equityChart.dispose()
  }
  if (tradesChart) {
    tradesChart.dispose()
  }
})
</script>

<style lang="scss" scoped>
.trade-stats-card {
  height: 100%;
  display: flex;
  flex-direction: column;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .header-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }
  }

  .stats-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 20px;
    overflow-y: auto;

    .summary-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;

      .summary-item {
        background: rgba(255, 255, 255, 0.05);
        border-radius: $border-radius-sm;
        padding: 16px;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.1);

        .label {
          display: block;
          font-size: 12px;
          color: rgba(255, 255, 255, 0.7);
          margin-bottom: 8px;
        }

        .value {
          font-size: 24px;
          font-weight: 700;
          color: #ffffff;

          &.positive {
            color: $success-color;
          }

          &.negative {
            color: $danger-color;
          }
        }
      }
    }

    .profit-section,
    .total-section {
      display: flex;
      justify-content: space-around;
      padding: 16px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: $border-radius-sm;
      border: 1px solid rgba(255, 255, 255, 0.1);

      .profit-item,
      .total-item {
        text-align: center;

        .label {
          display: block;
          font-size: 12px;
          color: rgba(255, 255, 255, 0.7);
          margin-bottom: 8px;
        }

        .value {
          font-size: 18px;
          font-weight: 600;
          color: #ffffff;

          &.positive {
            color: $success-color;
          }

          &.negative {
            color: $danger-color;
          }
        }

        &.highlight {
          .value {
            font-size: 24px;
          }
        }
      }
    }

    .simulation-section {
      background: rgba(255, 193, 7, 0.1);
      border: 1px solid rgba(255, 193, 7, 0.3);
      border-radius: $border-radius-sm;
      padding: 16px;

      .section-title {
        font-size: 14px;
        font-weight: 600;
        color: #e6a23c;
        margin-bottom: 12px;
      }

      .simulation-stats {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;

        .sim-item {
          text-align: center;

          .label {
            display: block;
            font-size: 12px;
            color: rgba(255, 255, 255, 0.7);
            margin-bottom: 4px;
          }

          .value {
            font-size: 16px;
            font-weight: 600;
            color: #ffffff;

            &.positive {
              color: $success-color;
            }

            &.negative {
              color: $danger-color;
            }
          }
        }
      }
    }

    .today-section,
    .coin-stats {
      background: rgba(255, 255, 255, 0.05);
      border-radius: $border-radius-sm;
      padding: 16px;
      border: 1px solid rgba(255, 255, 255, 0.1);

      .section-title {
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 12px;
        color: #ffffff;
      }

      .today-stats {
        display: flex;
        justify-content: space-around;
        flex-wrap: wrap;
        gap: 12px;

        span {
          font-size: 14px;
          color: rgba(255, 255, 255, 0.8);
        }
      }

      .coin-list {
        display: flex;
        flex-direction: column;
        gap: 8px;

        .coin-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 12px;
          background: rgba(255, 255, 255, 0.05);
          border-radius: $border-radius-sm;
          border: 1px solid rgba(255, 255, 255, 0.1);

          .coin-name {
            font-weight: 600;
            min-width: 60px;
            color: #ffffff;
          }

          .coin-detail {
            color: rgba(255, 255, 255, 0.7);
          }

          .coin-result {
            font-weight: 600;
            color: #ffffff;

            &.positive {
              color: $success-color;
            }

            &.negative {
              color: $danger-color;
            }
          }
        }
      }
    }

    .charts-section {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 20px;

      .chart-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: $border-radius-sm;
        padding: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);

        .chart-title {
          font-size: 14px;
          font-weight: 600;
          margin-bottom: 12px;
          color: #ffffff;
        }

        .chart-container {
          height: 200px;
        }
      }
    }
  }

  .empty-state {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(255, 255, 255, 0.7);
  }
}
</style>
