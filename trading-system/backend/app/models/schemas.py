from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class PositionStatus(str, Enum):
    HOLDING = "holding"
    CLOSED = "closed"


class BalanceResponse(BaseModel):
    total_equity: float
    available_usdt: float
    positions: Dict[str, Any]


class TickerResponse(BaseModel):
    symbol: str
    inst_id: str
    price: float
    change_24h: float
    volume_24h: float
    high_24h: float
    low_24h: float


class TrendAnalysisResponse(BaseModel):
    symbol: str
    score: int
    trend: str
    volatility: float
    recent_change: float
    signals: List[str]
    indicators: Dict[str, Any]


class OrderRequest(BaseModel):
    inst_id: str
    side: OrderSide
    order_type: OrderType
    size: str
    price: Optional[str] = None
    use_swap: bool = False
    pos_side: Optional[str] = None
    leverage: Optional[int] = None


class OrderResponse(BaseModel):
    order_id: str
    inst_id: str
    side: str
    order_type: str
    size: str
    price: Optional[str]
    status: str
    created_at: datetime


class PositionResponse(BaseModel):
    coin: str
    amount: float
    value: float
    avg_price: float
    current_price: float
    pnl_percent: float
    pnl_value: float


class TradeLogResponse(BaseModel):
    time: datetime
    coin: str
    action: str
    price: float
    amount: float
    reason: str


class StatsResponse(BaseModel):
    total_trades: int
    buy_count: int
    sell_count: int
    win_rate: float
    avg_profit: float
    avg_loss: float
    total_profit: float
    total_loss: float
    net_profit: float


class MarketEnvironmentResponse(BaseModel):
    can_trade: bool
    score: int
    btc_score: int
    eth_score: int
    funding_score: int
    btc_change_24h: float
    eth_change_24h: float
    reason: str


class ResonanceResponse(BaseModel):
    can_buy: bool
    total_score: int
    sentiment_score: int
    technical_score: int
    capital_flow_score: int
    market_env_score: int
    reason: str


class DecisionResponse(BaseModel):
    action: str
    reason: str
    amount: Optional[float] = None
    usdt_amount: Optional[float] = None
    resonance_score: Optional[int] = None


class TimeZoneInfoResponse(BaseModel):
    current_time_zone: str
    intensity: int
    position_size: Dict[str, float]
    hold_time: Dict[str, int]
    daily_quota: float
    check_interval: int


class SystemStatusResponse(BaseModel):
    status: str
    version: str
    trading_mode: str
    current_time: datetime
    time_zone_info: TimeZoneInfoResponse
    daily_stats: StatsResponse


class TradingSignalResponse(BaseModel):
    time: str
    coin: str
    type: str
    price: float
    reason: str
    urgency: str


class TradingAgentConfigResponse(BaseModel):
    enabled: bool
    auto_execute: bool
    max_trade_amount: float
    max_daily_trades: int
    today_trade_count: int
