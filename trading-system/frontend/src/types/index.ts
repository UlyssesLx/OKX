export interface Balance {
  total_equity: number
  available_usdt: number
  positions: Record<string, Position>
}

export interface Position {
  amount: number
  value: number
  avg_price: number
  is_simulation?: boolean
  is_short?: boolean
  coin?: string
  leverage?: number
  is_swap?: boolean
}

export interface Ticker {
  symbol: string
  inst_id: string
  instId: string
  price: number
  last: number
  change_24h: number
  volume_24h: number
  high_24h: number
  low_24h: number
}

export interface TrendAnalysis {
  symbol: string
  score: number
  trend: 'bullish' | 'bearish' | 'neutral'
  volatility: number
  recent_change: number
  signals: string[]
  indicators: Record<string, any>
}

export interface MarketEnvironment {
  can_trade: boolean
  score: number
  btc_score: number
  eth_score: number
  funding_score: number
  btc_change_24h: number
  eth_change_24h: number
  reason: string
}

export interface Resonance {
  can_buy: boolean
  total_score: number
  sentiment_score: number
  technical_score: number
  capital_flow_score: number
  market_env_score: number
  reason: string
}

export interface TimeZoneInfo {
  current_time_zone: string
  intensity: number
  position_size: {
    min: number
    max: number
  }
  hold_time: {
    min: number
    max: number
  }
  daily_quota: number
  check_interval: number
}

export interface Order {
  order_id: string
  inst_id: string
  side: 'buy' | 'sell'
  order_type: 'market' | 'limit'
  size: string
  price?: string
  status: string
  created_at: string
}

export interface TradeLog {
  time: string
  coin: string
  action: 'buy' | 'sell'
  price: number
  amount: number
  reason: string
}

export interface Stats {
  total_trades: number
  buy_count: number
  sell_count: number
  win_rate: number
  avg_profit: number
  avg_loss: number
  total_profit: number
  total_loss: number
  net_profit: number
}

export interface SystemStatus {
  status: string
  version: string
  trading_mode: string
  current_time: string
  time_zone_info: TimeZoneInfo
  daily_stats: Stats
}

export interface WebSocketMessage {
  type: 'account' | 'market' | 'timezone' | 'trade' | 'ping' | 'pong' | 'subscribed'
  data?: any
  channel?: string
}
