import axios from 'axios'
import type {
  Balance,
  Ticker,
  TrendAnalysis,
  MarketEnvironment,
  Resonance,
  TimeZoneInfo,
  Order
} from '@/types'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const tradingApi = {
  async getBalance(): Promise<Balance> {
    const response = await api.get('/trading/balance')
    return response.data
  },

  async getTicker(instId: string): Promise<Ticker> {
    const response = await api.get(`/trading/ticker/${instId}`)
    return response.data
  },

  async getTickers(instType: string = 'SPOT'): Promise<Ticker[]> {
    const response = await api.get('/trading/tickers', { params: { inst_type: instType } })
    return response.data
  },

  async getTrendAnalysis(instId: string): Promise<TrendAnalysis> {
    const response = await api.get(`/trading/trend/${instId}`)
    return response.data
  },

  async getMarketEnvironment(): Promise<MarketEnvironment> {
    const response = await api.get('/trading/market-environment')
    return response.data
  },

  async getResonance(coin: string, sentimentScore: number = 7): Promise<Resonance> {
    const response = await api.get(`/trading/resonance/${coin}`, {
      params: { sentiment_score: sentimentScore }
    })
    return response.data
  },

  async getTimeZoneInfo(): Promise<TimeZoneInfo> {
    const response = await api.get('/trading/time-zone')
    return response.data
  },

  async placeOrder(order: {
    inst_id: string
    side: 'buy' | 'sell'
    order_type: 'market' | 'limit'
    size: string
    price?: string
    use_swap?: boolean
    pos_side?: 'long' | 'short'
    leverage?: number
  }): Promise<Order> {
    const response = await api.post('/trading/order', order)
    return response.data
  },

  async cancelOrder(instId: string, orderId: string): Promise<{ success: boolean }> {
    const response = await api.delete(`/trading/order/${instId}/${orderId}`)
    return response.data
  },

  async getSimulationStats(): Promise<{
    positions: any[]
    stats: {
      total_pnl: number
      win_count: number
      loss_count: number
      total_trades: number
      win_rate: number
      position_count: number
      initial_balance: number
      available_balance: number
    }
  }> {
    const response = await api.get('/trading/simulation/positions')
    return response.data
  },

  async getSimulationTrades(limit: number = 50): Promise<{
    trades: Array<{
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
    }>
  }> {
    const response = await api.get('/trading/simulation/trades', { params: { limit } })
    return response.data
  },

  async clearSimulation(): Promise<{ success: boolean }> {
    const response = await api.delete('/trading/simulation/clear')
    return response.data
  }
}

export default api
