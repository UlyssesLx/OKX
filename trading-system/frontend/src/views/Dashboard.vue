<template>
  <div class="dashboard">
    <div class="top-bar">
      <div class="system-brand">
        <span class="brand-icon">🐦</span>
        <span class="brand-name">币市麻雀战法</span>
        <span class="brand-version">v4.2</span>
      </div>
      <div class="system-status">
        <div class="status-indicator" :class="isConnected ? 'running' : 'paused'"></div>
        <span class="status-text">{{ isConnected ? '系统运行中' : '未连接' }}</span>
      </div>
      <div class="balance-info">
        <span class="label">总资产:</span>
        <span class="value positive">${{ totalEquity.toFixed(2) }}</span>
      </div>
    </div>

    <div class="nav-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="nav-tab"
        :class="{ active: activeNav === tab.key }"
        @click="activeNav = tab.key"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        <span class="tab-text">{{ tab.label }}</span>
      </button>
    </div>

    <div class="content-area">
      <div v-show="activeNav === 'overview'" class="config-panel">
        <div class="panel-header">
          <h2 class="panel-title">📊 市场概览</h2>
          <p class="panel-desc">实时监控市场状态和持仓情况</p>
        </div>

        <div class="stats-grid">
          <StatsCard title="总资产" :value="`$${totalEquity.toFixed(2)}`" icon="💰" :trend="totalEquity > 300 ? 'up' : 'down'" />
          <StatsCard title="可用USDT" :value="`$${availableUsdt.toFixed(2)}`" icon="💵" :trend="availableUsdt > 50 ? 'up' : 'neutral'" />
          <StatsCard title="持仓数量" :value="positionCount.toString()" icon="📊" :trend="positionCount > 0 ? 'up' : 'neutral'" />
          <StatsCard title="大盘评分" :value="`${marketScore}/10`" icon="📈" :trend="marketScore >= 6 ? 'up' : marketScore >= 4 ? 'neutral' : 'down'" />
        </div>

        <div class="content-grid">
          <div class="left-column">
            <TimeZoneCard :timeZoneInfo="timeZoneInfo" />
            <MarketEnvironmentCard :environment="marketEnvironment" />
          </div>
          <div class="right-column">
            <PositionsCard :positions="positions" />
          </div>
        </div>
      </div>

      <div v-show="activeNav === 'positions'" class="config-panel">
        <div class="panel-header">
          <h2 class="panel-title">💰 持仓详情</h2>
          <p class="panel-desc">查看所有持仓的详细信息和盈亏状态</p>
        </div>
        <PositionsDetailCard />
      </div>

      <div v-show="activeNav === 'trades'" class="config-panel">
        <div class="panel-header">
          <h2 class="panel-title">📋 交易记录</h2>
          <p class="panel-desc">查看所有历史交易和操作日志</p>
        </div>
        <TradesHistoryCard />
      </div>

      <div v-show="activeNav === 'sentiment'" class="config-panel">
        <div class="panel-header">
          <h2 class="panel-title">🌡️ 市场情绪</h2>
          <p class="panel-desc">实时监控市场情绪和资金流向</p>
        </div>
        <SentimentCard />
      </div>

      <div v-show="activeNav === 'stats'" class="config-panel">
        <div class="panel-header">
          <h2 class="panel-title">📈 交易统计</h2>
          <p class="panel-desc">交易数据统计和分析报表</p>
        </div>
        <TradeStatsCard />
      </div>

      <div v-show="activeNav === 'strategy'" class="config-panel full-width">
        <StrategyConfigCard />
      </div>

      <div v-show="activeNav === 'auto'" class="config-panel">
        <div class="panel-header">
          <h2 class="panel-title">🤖 自动交易</h2>
          <p class="panel-desc">交易协调和自动执行控制</p>
        </div>
        <CoordinatorCard />
        <div class="bottom-cards">
          <StrategyEvolutionCard />
          <div class="vertical-cards">
            <MarketScanCard />
            <EmergencyStopCard />
          </div>
        </div>
      </div>

      <div v-show="activeNav === 'monitor'" class="config-panel">
        <div class="panel-header">
          <h2 class="panel-title">🔍 状态监控</h2>
          <p class="panel-desc">系统状态监控和黑名单管理</p>
        </div>
        <div class="content-grid">
          <div class="left-wide">
            <BlacklistCard />
          </div>
          <div class="right-narrow">
            <SidewaysStatusCard />
          </div>
        </div>
      </div>

      <div v-show="activeNav === 'grid'" class="config-panel">
        <div class="panel-header">
          <h2 class="panel-title">🔲 网格交易</h2>
          <p class="panel-desc">网格交易策略配置和状态</p>
        </div>
        <GridTradingCard />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useTradingStore } from '@/stores/trading'
import StatsCard from '@/components/StatsCard.vue'
import TimeZoneCard from '@/components/TimeZoneCard.vue'
import MarketEnvironmentCard from '@/components/MarketEnvironmentCard.vue'
import PositionsCard from '@/components/PositionsCard.vue'
import SentimentCard from '@/components/SentimentCard.vue'
import TradeStatsCard from '@/components/TradeStatsCard.vue'
import StrategyConfigCard from '@/components/StrategyConfigCard.vue'
import CoordinatorCard from '@/components/CoordinatorCard.vue'
import EmergencyStopCard from '@/components/EmergencyStopCard.vue'
import MarketScanCard from '@/components/MarketScanCard.vue'
import SidewaysStatusCard from '@/components/SidewaysStatusCard.vue'
import BlacklistCard from '@/components/BlacklistCard.vue'
import StrategyEvolutionCard from '@/components/StrategyEvolutionCard.vue'
import GridTradingCard from '@/components/GridTradingCard.vue'
import PositionsDetailCard from '@/components/PositionsDetailCard.vue'
import TradesHistoryCard from '@/components/TradesHistoryCard.vue'
import { useWebSocket } from '@/composables/useWebSocket'

const tradingStore = useTradingStore()

const totalEquity = computed(() => tradingStore.totalEquity)
const availableUsdt = computed(() => tradingStore.availableUsdt)
const positionCount = computed(() => tradingStore.positionCount)
const marketScore = computed(() => tradingStore.marketScore)
const positions = computed(() => tradingStore.positions)
const marketEnvironment = computed(() => tradingStore.marketEnvironment)
const timeZoneInfo = computed(() => tradingStore.timeZoneInfo)
const isConnected = computed(() => tradingStore.isConnected)

const activeNav = ref('overview')

const tabs = [
  { key: 'overview', label: '市场概览', icon: '📊' },
  { key: 'positions', label: '持仓详情', icon: '💰' },
  { key: 'trades', label: '交易记录', icon: '📋' },
  { key: 'sentiment', label: '市场情绪', icon: '🌡️' },
  { key: 'stats', label: '交易统计', icon: '📈' },
  { key: 'strategy', label: '策略配置', icon: '⚙️' },
  { key: 'auto', label: '自动交易', icon: '🤖' },
  { key: 'monitor', label: '状态监控', icon: '🔍' },
  { key: 'grid', label: '网格交易', icon: '🔲' }
]

const { connect, disconnect } = useWebSocket()

onMounted(async () => {
  await tradingStore.fetchBalance()
  await tradingStore.fetchMarketEnvironment()
  await tradingStore.fetchTimeZoneInfo()
  connect()
})

onUnmounted(() => {
  disconnect()
})
</script>

<style lang="scss" scoped>
* {
  box-sizing: border-box;
}

.dashboard {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  color: #fff;
  display: flex;
  flex-direction: column;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 32px;
  background: rgba(0, 0, 0, 0.4);
  border-bottom: 1px solid rgba(255, 255, 255, 0.15);

  .system-brand {
    display: flex;
    align-items: center;
    gap: 10px;

    .brand-icon {
      font-size: 24px;
    }

    .brand-name {
      font-size: 18px;
      font-weight: 700;
      background: linear-gradient(135deg, #667eea, #764ba2);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }

    .brand-version {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.5);
      background: rgba(255, 255, 255, 0.1);
      padding: 3px 7px;
      border-radius: 6px;
    }
  }

  .system-status {
    display: flex;
    align-items: center;
    gap: 10px;

    .status-indicator {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: #4caf50;
      box-shadow: 0 0 8px rgba(76, 175, 80, 0.6);
      animation: pulse 2s infinite;

      &.paused {
        background: #f44336;
        box-shadow: 0 0 8px rgba(244, 67, 54, 0.6);
        animation: none;
      }
    }

    .status-text {
      font-size: 14px;
      font-weight: 500;
      color: #ffffff;
    }
  }

  .balance-info {
    font-size: 14px;

    .label {
      color: rgba(255, 255, 255, 0.7);
      margin-right: 8px;
    }

    .value {
      font-weight: 600;
      color: #ffffff;

      &.positive {
        color: #4caf50;
        text-shadow: 0 0 10px rgba(76, 175, 80, 0.4);
      }

      &.negative {
        color: #f44336;
        text-shadow: 0 0 10px rgba(244, 67, 54, 0.4);
      }
    }
  }
}

.nav-tabs {
  display: flex;
  gap: 8px;
  padding: 20px 32px;
  overflow-x: auto;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(0, 0, 0, 0.2);

  &::-webkit-scrollbar {
    height: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.3);
    border-radius: 2px;
  }
}

.nav-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 12px;
  color: rgba(255, 255, 255, 0.75);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;

  .tab-icon {
    font-size: 16px;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.12);
    color: #ffffff;
  }

  &.active {
    background: linear-gradient(135deg, #667eea, #764ba2);
    border-color: #667eea;
    color: #ffffff;
    box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
  }
}

.content-area {
  flex: 1;
  padding: 32px;
}

.config-panel {
  &.full-width {
    margin: -32px;
    padding: 32px;
  }

  .panel-header {
    margin-bottom: 24px;

    .panel-title {
      font-size: 24px;
      font-weight: 700;
      margin: 0 0 8px;
      color: #ffffff;
    }

    .panel-desc {
      color: rgba(255, 255, 255, 0.6);
      margin: 0;
      font-size: 14px;
    }
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;

  @media (max-width: 1200px) {
    grid-template-columns: repeat(2, 1fr);
  }

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 20px;
  align-items: start;

  @media (max-width: 1024px) {
    grid-template-columns: 1fr;
  }

  .left-column, .right-column, .left-wide, .right-narrow {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }
}

.bottom-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-top: 24px;

  @media (max-width: 1024px) {
    grid-template-columns: 1fr;
  }
}

.vertical-cards {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: stretch;
  gap: 20px;
  height: 100%;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}
</style>
