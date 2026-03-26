import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Balance, MarketEnvironment, TimeZoneInfo, TradeLog, Stats } from '@/types'
import { tradingApi } from '@/api'

export const useTradingStore = defineStore('trading', () => {
  const balance = ref<Balance>({
    total_equity: 0,
    available_usdt: 0,
    positions: {}
  })

  const marketEnvironment = ref<MarketEnvironment>({
    can_trade: true,
    score: 5,
    btc_score: 5,
    eth_score: 5,
    funding_score: 5,
    btc_change_24h: 0,
    eth_change_24h: 0,
    reason: ''
  })

  const timeZoneInfo = ref<TimeZoneInfo>({
    current_time_zone: '',
    intensity: 1,
    position_size: { min: 5, max: 10 },
    hold_time: { min: 15, max: 60 },
    daily_quota: 0.1,
    check_interval: 5
  })

  const tradeLogs = ref<TradeLog[]>([])
  const stats = ref<Stats>({
    total_trades: 0,
    buy_count: 0,
    sell_count: 0,
    win_rate: 0,
    avg_profit: 0,
    avg_loss: 0,
    total_profit: 0,
    total_loss: 0,
    net_profit: 0
  })

  const isConnected = ref(false)
  const lastUpdate = ref<Date | null>(null)

  const totalEquity = computed(() => balance.value.total_equity)
  const availableUsdt = computed(() => balance.value.available_usdt)
  const positions = computed(() => balance.value.positions)
  const positionCount = computed(() => Object.keys(balance.value.positions).length)

  const btcPrice = computed(() => {
    return marketEnvironment.value.btc_change_24h
  })

  const ethPrice = computed(() => {
    return marketEnvironment.value.eth_change_24h
  })

  const canTrade = computed(() => marketEnvironment.value.can_trade)
  const marketScore = computed(() => marketEnvironment.value.score)

  async function fetchBalance() {
    try {
      const data = await tradingApi.getBalance()
      balance.value = data
      lastUpdate.value = new Date()
    } catch (error) {
      console.error('Failed to fetch balance:', error)
    }
  }

  async function fetchMarketEnvironment() {
    try {
      const data = await tradingApi.getMarketEnvironment()
      marketEnvironment.value = data
    } catch (error) {
      console.error('Failed to fetch market environment:', error)
    }
  }

  async function fetchTimeZoneInfo() {
    try {
      const data = await tradingApi.getTimeZoneInfo()
      timeZoneInfo.value = data
    } catch (error) {
      console.error('Failed to fetch time zone info:', error)
    }
  }

  function updateFromWebSocket(message: any) {
    if (message.type === 'account') {
      const newPositions: Record<string, any> = {}

      for (const pos of message.data.positions) {
        // 构建 position key：模拟空单用 _short_sim 后缀，模拟多单用 _sim 后缀
        let key: string
        if (pos.is_simulation) {
          key = pos.is_short ? `${pos.coin}_short_sim` : `${pos.coin}_sim`
        } else {
          key = pos.coin
        }
        newPositions[key] = {
          amount: pos.amount,
          value: pos.value,
          avg_price: pos.avg_price,
          is_simulation: pos.is_simulation || false,
          is_short: pos.is_short || false,
          coin: pos.coin,
          leverage: pos.leverage || 1.0,
          is_swap: pos.is_swap || false
        }
      }

      balance.value = {
        total_equity: message.data.total_equity,
        available_usdt: message.data.available_usdt,
        positions: newPositions
      }
      lastUpdate.value = new Date(message.data.timestamp)
    } else if (message.type === 'market') {
      marketEnvironment.value.btc_change_24h = message.data.btc.change_24h
      marketEnvironment.value.eth_change_24h = message.data.eth.change_24h
    } else if (message.type === 'timezone') {
      timeZoneInfo.value = message.data
    }
  }

  function setConnected(connected: boolean) {
    isConnected.value = connected
  }

  return {
    balance,
    marketEnvironment,
    timeZoneInfo,
    tradeLogs,
    stats,
    isConnected,
    lastUpdate,
    totalEquity,
    availableUsdt,
    positions,
    positionCount,
    btcPrice,
    ethPrice,
    canTrade,
    marketScore,
    fetchBalance,
    fetchMarketEnvironment,
    fetchTimeZoneInfo,
    updateFromWebSocket,
    setConnected
  }
})
