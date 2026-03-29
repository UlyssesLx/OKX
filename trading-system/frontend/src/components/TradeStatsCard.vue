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
          <span class="label">开仓</span>
          <span class="value">{{ stats.summary.open_count || 0 }}</span>
        </div>
        <div class="summary-item">
          <span class="label">平仓</span>
          <span class="value">{{ stats.summary.close_count || 0 }}</span>
        </div>
        <div class="summary-item">
          <span class="label">胜率</span>
          <span class="value" :class="stats.summary.win_rate >= 50 ? 'positive' : 'negative'">
            {{ stats.summary.win_rate }}%
          </span>
        </div>
      </div>

      <div class="direction-stats">
        <div class="direction-item long">
          <div class="direction-title">📈 做多</div>
          <div class="direction-detail">
            <span class="stat-text">开多 {{ stats.summary.open_long || 0 }} / 平多 {{ stats.summary.close_long || 0 }}</span>
            <span class="result" :class="stats.summary.long_profit >= 0 ? 'positive' : 'negative'">
              {{ stats.summary.long_profit >= 0 ? '+' : '' }}{{ stats.summary.long_profit || 0 }}%
            </span>
          </div>
        </div>
        <div class="direction-item short">
          <div class="direction-title">📉 做空</div>
          <div class="direction-detail">
            <span class="stat-text">开空 {{ stats.summary.open_short || 0 }} / 平空 {{ stats.summary.close_short || 0 }}</span>
            <span class="result" :class="stats.summary.short_profit >= 0 ? 'positive' : 'negative'">
              {{ stats.summary.short_profit >= 0 ? '+' : '' }}{{ stats.summary.short_profit || 0 }}%
            </span>
          </div>
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
          <span>开仓 {{ stats.today.opens || 0 }} 次</span>
          <span>平仓 {{ stats.today.closes || 0 }} 次</span>
          <span>金额 ${{ stats.today.volume }}</span>
        </div>
        <div class="today-detail">
          <span class="detail-item long">开多 {{ stats.today.open_long || 0 }}</span>
          <span class="detail-item long">平多 {{ stats.today.close_long || 0 }}</span>
          <span class="detail-item short">开空 {{ stats.today.open_short || 0 }}</span>
          <span class="detail-item short">平空 {{ stats.today.close_short || 0 }}</span>
        </div>
      </div>

      <div class="coin-stats" v-if="stats.coin_stats && Object.keys(stats.coin_stats).length > 0">
        <div class="section-title">💰 币种表现</div>
        <div class="coin-list">
          <div v-for="(stat, coin) in stats.coin_stats" :key="coin" class="coin-item">
            <span class="coin-name">{{ coin }}</span>
            <div class="coin-detail-row">
              <span class="detail-badge open">开仓 {{ (stat.open_long || 0) + (stat.open_short || 0) }}</span>
              <span class="detail-badge close">平仓 {{ (stat.close_long || 0) + (stat.close_short || 0) }}</span>
            </div>
            <div class="coin-direction-row">
              <span class="direction-badge long">开多 {{ stat.open_long || 0 }}</span>
              <span class="direction-badge long">平多 {{ stat.close_long || 0 }}</span>
              <span class="direction-badge short">开空 {{ stat.open_short || 0 }}</span>
              <span class="direction-badge short">平空 {{ stat.close_short || 0 }}</span>
            </div>
            <div class="coin-winrate-row">
              <span class="winrate-item long" :class="getWinRateClass(stat.long_win, stat.long_loss_count)">
                做多胜率: {{ calcWinRate(stat.long_win, stat.long_loss_count) }}%
              </span>
              <span class="winrate-item short" :class="getWinRateClass(stat.short_win, stat.short_loss_count)">
                做空胜率: {{ calcWinRate(stat.short_win, stat.short_loss_count) }}%
              </span>
              <span class="winrate-item total" :class="getWinRateClass(stat.profit, stat.loss)">
                总胜率: {{ calcWinRate(stat.profit, stat.loss) }}%
              </span>
            </div>
            <div class="coin-result-row">
              <span class="result-item positive">
                <span>盈利次数: {{ stat.profit || 0 }}</span>
              </span>
              <span class="result-item negative">
                <span>亏损次数: {{ stat.loss || 0 }}</span>
              </span>
            </div>
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
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
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
    open_count: number
    close_count: number
    open_long: number
    close_long: number
    open_short: number
    close_short: number
    buy_count: number
    sell_count: number
    win_rate: number
    avg_profit: string | number
    avg_loss: string | number
    profit_loss_ratio: string | number
    total_profit: string | number
    total_loss: string | number
    net_profit: string | number
    long_profit: number
    short_profit: number
    [key: string]: any
  }
  today: {
    date: string
    trades: number
    opens: number
    closes: number
    open_long: number
    close_long: number
    open_short: number
    close_short: number
    buys: number
    sells: number
    volume: string | number
    [key: string]: any
  }
  coin_stats: Record<string, any>
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

function calcWinRate(wins: number, losses: number): number {
  const total = (wins || 0) + (losses || 0)
  if (total === 0) return 0
  return Math.round(((wins || 0) / total) * 100)
}

function getWinRateClass(wins: number, losses: number): string {
  const winRate = calcWinRate(wins, losses)
  if (winRate >= 60) return 'positive'
  if (winRate >= 40) return 'neutral'
  return 'negative'
}

async function fetchStats() {
  loading.value = true
  try {
    // 获取实盘统计（is_simulation=false）
    const response = await fetch('/api/v1/services/stats?is_simulation=false')
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

    // 保存交易历史用于图表
    tradesHistory.value = simTradesResponse.trades || []

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
  
  // 分类统计
  const openLong = trades.filter((t: any) => t.action === 'buy')
  const closeLong = trades.filter((t: any) => t.action === 'sell')
  const openShort = trades.filter((t: any) => t.action === 'sell_short')
  const closeShort = trades.filter((t: any) => t.action === 'buy_short')
  
  const allClose = [...closeLong, ...closeShort]
  const winTrades = allClose.filter((t: any) => (t.pnl || 0) > 0)
  const lossTrades = allClose.filter((t: any) => (t.pnl || 0) <= 0)
  
  // 计算做多做空盈亏
  const longPnL = closeLong.reduce((sum: number, t: any) => sum + (t.pnl_percent || 0), 0)
  const shortPnL = closeShort.reduce((sum: number, t: any) => sum + (t.pnl_percent || 0), 0)
  
  // 计算今日数据（使用北京时间）
  const today = getBeijingDate()
  const todayTrades = trades.filter((t: any) => t.timestamp?.startsWith(today))
  const todayVolume = todayTrades.reduce((sum: number, t: any) => sum + (t.usdt_value || 0), 0)
  const todayOpens = todayTrades.filter((t: any) => t.action === 'buy' || t.action === 'sell_short').length
  const todayCloses = todayTrades.filter((t: any) => t.action === 'sell' || t.action === 'buy_short').length
  const todayOpenLong = todayTrades.filter((t: any) => t.action === 'buy').length
  const todayCloseLong = todayTrades.filter((t: any) => t.action === 'sell').length
  const todayOpenShort = todayTrades.filter((t: any) => t.action === 'sell_short').length
  const todayCloseShort = todayTrades.filter((t: any) => t.action === 'buy_short').length
  
  // 计算币种统计
  const coinStats: Record<string, { 
    buys: number; sells: number; 
    open_long: number; close_long: number;
    open_short: number; close_short: number;
    profit: number; loss: number;
    long_profit: number; short_profit: number;
    long_win: number; long_loss: number;
    short_win: number; short_loss: number;
    long_win_rate: number; short_win_rate: number; total_win_rate: number;
  }> = {}
  
  for (const t of trades) {
    if (!coinStats[t.coin]) {
      coinStats[t.coin] = { 
        buys: 0, sells: 0,
        open_long: 0, close_long: 0,
        open_short: 0, close_short: 0,
        profit: 0, loss: 0,
        long_profit: 0, short_profit: 0,
        long_win: 0, long_loss: 0,
        short_win: 0, short_loss: 0,
        long_win_rate: 0, short_win_rate: 0, total_win_rate: 0
      }
    }
    
    if (t.action === 'buy') {
      coinStats[t.coin].buys++
      coinStats[t.coin].open_long++
    } else if (t.action === 'sell') {
      coinStats[t.coin].sells++
      coinStats[t.coin].close_long++
      const pnl = t.pnl_percent || 0
      coinStats[t.coin].long_profit += pnl
      if (pnl > 0) {
        coinStats[t.coin].profit++
        coinStats[t.coin].long_win++
      } else if (pnl < 0) {
        coinStats[t.coin].loss++
        coinStats[t.coin].long_loss++
      }
    } else if (t.action === 'sell_short') {
      coinStats[t.coin].sells++
      coinStats[t.coin].open_short++
    } else if (t.action === 'buy_short') {
      coinStats[t.coin].buys++
      coinStats[t.coin].close_short++
      const pnl = t.pnl_percent || 0
      coinStats[t.coin].short_profit += pnl
      if (pnl > 0) {
        coinStats[t.coin].profit++
        coinStats[t.coin].short_win++
      } else if (pnl < 0) {
        coinStats[t.coin].loss++
        coinStats[t.coin].short_loss++
      }
    }
  }
  
  // 计算各币种的胜率
  for (const coin in coinStats) {
    const stat = coinStats[coin]
    const longCloseCount = stat.long_win + stat.long_loss
    const shortCloseCount = stat.short_win + stat.short_loss
    const totalCloseCount = longCloseCount + shortCloseCount
    
    stat.long_win_rate = longCloseCount > 0 ? Math.round((stat.long_win / longCloseCount) * 100) : 0
    stat.short_win_rate = shortCloseCount > 0 ? Math.round((stat.short_win / shortCloseCount) * 100) : 0
    stat.total_win_rate = totalCloseCount > 0 ? Math.round(((stat.long_win + stat.short_win) / totalCloseCount) * 100) : 0
    
    // 保留两位小数
    stat.long_profit = parseFloat(stat.long_profit.toFixed(2))
    stat.short_profit = parseFloat(stat.short_profit.toFixed(2))
  }

  return {
    summary: {
      total_trades: trades.length,
      open_count: openLong.length + openShort.length,
      close_count: closeLong.length + closeShort.length,
      open_long: openLong.length,
      close_long: closeLong.length,
      open_short: openShort.length,
      close_short: closeShort.length,
      long_profit: parseFloat(longPnL.toFixed(2)),
      short_profit: parseFloat(shortPnL.toFixed(2)),
      buy_count: openLong.length + closeShort.length, // 买入 = 开多 + 平空
      sell_count: closeLong.length + openShort.length, // 卖出 = 平多 + 开空
      win_rate: allClose.length > 0 ? Math.round((winTrades.length / allClose.length) * 100) : 0,
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
      opens: todayOpens,
      closes: todayCloses,
      open_long: todayOpenLong,
      close_long: todayCloseLong,
      open_short: todayOpenShort,
      close_short: todayCloseShort,
      buys: todayOpenLong + todayCloseShort,
      sells: todayCloseLong + todayOpenShort,
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
      open_count: (realStats.summary.open_count || 0) + (simStats.summary.open_count || 0),
      close_count: (realStats.summary.close_count || 0) + (simStats.summary.close_count || 0),
      open_long: (realStats.summary.open_long || 0) + (simStats.summary.open_long || 0),
      close_long: (realStats.summary.close_long || 0) + (simStats.summary.close_long || 0),
      open_short: (realStats.summary.open_short || 0) + (simStats.summary.open_short || 0),
      close_short: (realStats.summary.close_short || 0) + (simStats.summary.close_short || 0),
      buy_count: realStats.summary.buy_count + simStats.summary.buy_count,
      sell_count: realStats.summary.sell_count + simStats.summary.sell_count,
      win_rate: Math.round((realStats.summary.win_rate + simStats.summary.win_rate) / 2),
      avg_profit: ((Number(realStats.summary.avg_profit) + Number(simStats.summary.avg_profit)) / 2),
      avg_loss: ((Number(realStats.summary.avg_loss) + Number(simStats.summary.avg_loss)) / 2),
      profit_loss_ratio: ((Number(realStats.summary.profit_loss_ratio) + Number(simStats.summary.profit_loss_ratio)) / 2),
      total_profit: Number(realStats.summary.total_profit) + Number(simStats.summary.total_profit),
      total_loss: Number(realStats.summary.total_loss) + Number(simStats.summary.total_loss),
      net_profit: Number(realStats.summary.net_profit) + Number(simStats.summary.net_profit),
      long_profit: (realStats.summary.long_profit || 0) + (simStats.summary.long_profit || 0),
      short_profit: (realStats.summary.short_profit || 0) + (simStats.summary.short_profit || 0)
    },
    today: {
      date: realStats.today.date,
      trades: realStats.today.trades + simStats.today.trades,
      opens: (realStats.today.opens || 0) + (simStats.today.opens || 0),
      closes: (realStats.today.closes || 0) + (simStats.today.closes || 0),
      open_long: (realStats.today.open_long || 0) + (simStats.today.open_long || 0),
      close_long: (realStats.today.close_long || 0) + (simStats.today.close_long || 0),
      open_short: (realStats.today.open_short || 0) + (simStats.today.open_short || 0),
      close_short: (realStats.today.close_short || 0) + (simStats.today.close_short || 0),
      buys: (realStats.today.buys || 0) + (simStats.today.buys || 0),
      sells: (realStats.today.sells || 0) + (simStats.today.sells || 0),
      volume: Number(realStats.today.volume) + Number(simStats.today.volume)
    },
    coin_stats: { ...realStats.coin_stats, ...simStats.coin_stats }
  }
}

function updateCharts() {
  if (!stats.value) {
    console.log('updateCharts: stats is null')
    return
  }

  console.log('updateCharts:', {
    open_count: stats.value.summary.open_count,
    close_count: stats.value.summary.close_count,
    equityData: generateEquityData()
  })

  if (equityChart) {
    equityChart.setOption({
      xAxis: {
        data: generateTimeLabels()
      },
      series: [{
        data: generateEquityData()
      }]
    })
    equityChart.resize()
  }

  if (tradesChart) {
    const openCount = stats.value.summary.open_count || 0
    const closeCount = stats.value.summary.close_count || 0
    tradesChart.setOption({
      series: [{
        data: [
          { value: openCount, name: '开仓', itemStyle: { color: '#67c23a' } },
          { value: closeCount, name: '平仓', itemStyle: { color: '#f56c6c' } }
        ]
      }]
    })
    tradesChart.resize()
  }
}

// 存储交易历史用于图表
const tradesHistory = ref<any[]>([])

function generateEquityData() {
  // 根据模式生成不同的资产曲线数据
  const baseValue = statsMode.value === 'simulation' ? simulationStats.value.initial_balance : 287
  const netProfit = Number(stats.value?.summary.net_profit || 0)
  const currentValue = statsMode.value === 'simulation'
    ? simulationStats.value.initial_balance + simulationStats.value.total_pnl
    : baseValue * (1 + netProfit / 100)

  // 生成7天的模拟数据，保留两位小数
  const data = []
  for (let i = 0; i < 7; i++) {
    const progress = i / 6
    const value = baseValue + (currentValue - baseValue) * progress
    data.push(parseFloat(value.toFixed(2)))
  }
  return data
}

function generateTimeLabels() {
  // 生成最近7天的日期标签
  const labels = []
  const today = new Date()
  for (let i = 6; i >= 0; i--) {
    const date = new Date(today)
    date.setDate(date.getDate() - i)
    const month = (date.getMonth() + 1).toString().padStart(2, '0')
    const day = date.getDate().toString().padStart(2, '0')
    labels.push(`${month}-${day}`)
  }
  return labels
}

function initCharts() {
  if (equityChartRef.value) {
    equityChart = echarts.init(equityChartRef.value)
    equityChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: generateTimeLabels(),
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
    // 强制调整大小以确保正确渲染
    equityChart.resize()
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
          { value: stats.value?.summary.open_count || 0, name: '开仓', itemStyle: { color: '#67c23a' } },
          { value: stats.value?.summary.close_count || 0, name: '平仓', itemStyle: { color: '#f56c6c' } }
        ]
      }]
    })
    // 强制调整大小以确保正确渲染
    tradesChart.resize()
  }
}

// 监听模式变化
watch(statsMode, () => {
  fetchStats()
})

onMounted(async () => {
  await fetchStats()
  // 等待DOM更新完成
  await nextTick()
  initCharts()
  // 确保图表数据更新
  updateCharts()
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
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.03) 100%);
        border-radius: $border-radius-sm;
        padding: 16px;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all 0.3s ease;

        &:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }

        .label {
          display: block;
          font-size: 12px;
          color: rgba(255, 255, 255, 0.7);
          margin-bottom: 8px;
          font-weight: 500;
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

    .direction-stats {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;

      .direction-item {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.03) 100%);
        border-radius: $border-radius-sm;
        padding: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all 0.3s ease;

        &:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }

        &.long {
          border-left: 3px solid $success-color;
        }

        &.short {
          border-left: 3px solid $danger-color;
        }

        .direction-title {
          font-size: 14px;
          font-weight: 600;
          margin-bottom: 12px;
          color: rgba(255, 255, 255, 0.9);
        }

        .direction-detail {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;

            .stat-text {
              font-size: 13px;
              color: rgba(255, 255, 255, 0.8);
            }

            span {
              font-size: 13px;
              color: rgba(255, 255, 255, 0.7);
            }

          .result {
            font-weight: 600;
            font-size: 14px;

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

      .today-detail {
        display: flex;
        justify-content: center;
        gap: 16px;
        margin-top: 10px;
        padding-top: 10px;
        border-top: 1px solid rgba(255, 255, 255, 0.1);

        .detail-item {
          font-size: 12px;
          padding: 4px 10px;
          border-radius: 4px;
          background: rgba(255, 255, 255, 0.05);

          &.long {
            color: $success-color;
            border-left: 2px solid $success-color;
          }

          &.short {
            color: $danger-color;
            border-left: 2px solid $danger-color;
          }
        }
      }

      .coin-list {
        display: flex;
        flex-direction: column;
        gap: 10px;

        .coin-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.03) 100%);
          border-radius: $border-radius-sm;
          border: 1px solid rgba(255, 255, 255, 0.1);
          transition: all 0.3s ease;

          &:hover {
            transform: translateX(4px);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          }

          .coin-name {
            font-weight: 700;
            min-width: 60px;
            color: #ffffff;
            font-size: 14px;
          }

          .coin-detail-row {
            display: flex;
            gap: 12px;
            align-items: center;

            .detail-badge {
              font-size: 12px;
              color: rgba(255, 255, 255, 0.9);
              padding: 2px 8px;
              border-radius: 4px;
              font-weight: 500;

              &.open {
                background: rgba(103, 194, 58, 0.15);
                border: 1px solid rgba(103, 194, 58, 0.3);
              }

              &.close {
                background: rgba(245, 108, 108, 0.15);
                border: 1px solid rgba(245, 108, 108, 0.3);
              }
            }
          }

          .coin-direction-row {
            display: flex;
            gap: 8px;
            align-items: center;
            margin: 6px 0;

            .direction-badge {
              font-size: 11px;
              padding: 3px 8px;
              border-radius: 4px;
              background: rgba(255, 255, 255, 0.05);
              font-weight: 500;

              &.long {
                color: $success-color;
                border-left: 2px solid $success-color;
              }

              &.short {
                color: $danger-color;
                border-left: 2px solid $danger-color;
              }
            }
          }

          .coin-winrate-row {
            display: flex;
            gap: 8px;
            align-items: center;
            margin: 4px 0;

            .winrate-item {
              font-weight: 600;
              font-size: 11px;
              padding: 3px 8px;
              border-radius: 4px;
              background: rgba(255, 255, 255, 0.05);

              &.long {
                border-left: 2px solid $success-color;
              }

              &.short {
                border-left: 2px solid $danger-color;
              }

              &.total {
                border-left: 2px solid #409eff;
              }

              &.positive {
                color: $success-color;
                background: rgba(103, 194, 58, 0.15);
              }

              &.neutral {
                color: #e6a23c;
                background: rgba(230, 162, 60, 0.15);
              }

              &.negative {
                color: $danger-color;
                background: rgba(245, 108, 108, 0.15);
              }
            }
          }

          .coin-result-row {
            display: flex;
            gap: 12px;
            align-items: center;

            .result-item {
              font-weight: 600;
              font-size: 12px;
              padding: 4px 8px;
              border-radius: 4px;
              background: rgba(255, 255, 255, 0.05);

              span {
                display: inline-block;
              }

              &.positive {
                color: $success-color;
                background: rgba(103, 194, 58, 0.15);
              }

              &.negative {
                color: $danger-color;
                background: rgba(245, 108, 108, 0.15);
              }
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
