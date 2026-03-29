from pydantic import BaseModel
from typing import Dict, List
from datetime import datetime, timezone, timedelta
from enum import Enum

BEIJING_TZ = timezone(timedelta(hours=8))


class TimeZoneType(str, Enum):
    ASIA_LATE = "00:00-04:00"
    EUROPE_AMERICA_TRANSITION = "04:00-08:00"
    ASIA_EARLY = "08:00-12:00"
    ASIA_MIDDAY = "12:00-16:00"
    EUROPE_EARLY = "16:00-20:00"
    AMERICA_EARLY = "20:00-24:00"


class TimeZoneConfig(BaseModel):
    intensity: int
    position_size: Dict[str, float]
    hold_time: Dict[str, int]
    daily_quota: float


class TakeProfitTier(BaseModel):
    profit: float
    action: str


class DynamicTakeProfitTier(BaseModel):
    profit: float
    action: str


class TakeProfitConfig(BaseModel):
    tier1: TakeProfitTier
    tier2: TakeProfitTier
    tier3: TakeProfitTier
    hard: float
    dynamic: Dict[str, DynamicTakeProfitTier]


class StopLossConfig(BaseModel):
    soft: float
    hard: float
    time: int


class EntryThreshold(BaseModel):
    trend_score: int
    resonance_score: int
    btc_trend: int
    volatility: Dict[str, float]


class PositionConfig(BaseModel):
    max_positions: int
    max_per_coin: float
    total_exposure: float


class DailyControlConfig(BaseModel):
    profit_target: float
    loss_limit: float
    consecutive_losses: int
    pause_duration: int


class CheckIntervalConfig(BaseModel):
    active: int = 5
    quiet: int = 15
    fixed: int = 10  # 固定检查间隔


class BuyConditionsConfig(BaseModel):
    sentiment_threshold: int = 7
    long_min_trend_score: int = 5
    long_rsi_min: float = 30.0
    long_rsi_max: float = 70.0
    long_min_volume_ratio: float = 0.8
    long_max_pullback_percent: float = 8.0
    long_min_pullback_percent: float = -15.0


class CooldownConfig(BaseModel):
    tiered_cooldown_enabled: bool = True
    cooldown_trend_10: int = 15
    cooldown_trend_8_9: int = 20
    cooldown_trend_6_7: int = 30


class DecreasingBuyConfig(BaseModel):
    decreasing_buy_enabled: bool = True
    factor_1: float = 1.0
    factor_2: float = 0.6
    factor_3: float = 0.35
    factor_4: float = 0.2


class PullbackConfig(BaseModel):
    pullback_buy_threshold: float = 0.97


class CashReserveConfig(BaseModel):
    min_cash_reserve: float = 30.0


class ExemptionConfig(BaseModel):
    over_position_exemption_enabled: bool = True
    exemption_loss_high: int = 60
    exemption_loss_medium: int = 45
    exemption_profit: int = 30


class VolatilityFilterConfig(BaseModel):
    volatility_filter_enabled: bool = True
    volatility_min: float = 0.5
    volatility_preferred: float = 1.5


class ResonanceWeights(BaseModel):
    sentiment: float
    technical: float
    capital_flow: float
    market_env: float


class TechnicalValidationConfig(BaseModel):
    enabled: bool = True
    min_pass_count: int = 2
    trend_score_threshold: int = 5
    rsi_min: float = 30.0
    rsi_max: float = 80.0
    volume_ratio_min: float = 0.8
    ma5_tolerance: float = 0.98
    volatility_min: float = 0.2


class BlacklistConfig(BaseModel):
    stop_loss_duration: int
    strong_trend_unlock: bool
    strong_trend_threshold: int
    medium_trend_duration: int
    medium_trend_threshold: int
    manual_ban: bool
    stablecoin_ban: bool
    stablecoins: List[str]


class SparrowConfig(BaseModel):
    version: str = "4.1-sparrow"
    base_capital: float = 287.0
    daily_target: float = 9.0
    weekly_target: float = 21.0
    
    time_zones: Dict[str, TimeZoneConfig]
    take_profit: TakeProfitConfig
    stop_loss: StopLossConfig
    entry_threshold: EntryThreshold
    position: PositionConfig
    daily_control: DailyControlConfig
    check_interval: CheckIntervalConfig
    resonance_weights: ResonanceWeights
    blacklist: BlacklistConfig
    buy_conditions: BuyConditionsConfig = BuyConditionsConfig()
    cooldown: CooldownConfig = CooldownConfig()
    decreasing_buy: DecreasingBuyConfig = DecreasingBuyConfig()
    pullback: PullbackConfig = PullbackConfig()
    cash_reserve: CashReserveConfig = CashReserveConfig()
    exemption: ExemptionConfig = ExemptionConfig()
    volatility: VolatilityFilterConfig = VolatilityFilterConfig()
    technical_validation: TechnicalValidationConfig = TechnicalValidationConfig()


def get_default_config() -> SparrowConfig:
    return SparrowConfig(
        time_zones={
            "00:00-04:00": TimeZoneConfig(
                intensity=1,
                position_size={"min": 5, "max": 8},
                hold_time={"min": 30, "max": 60},
                daily_quota=0.10
            ),
            "04:00-08:00": TimeZoneConfig(
                intensity=2,
                position_size={"min": 8, "max": 10},
                hold_time={"min": 20, "max": 40},
                daily_quota=0.15
            ),
            "08:00-12:00": TimeZoneConfig(
                intensity=5,
                position_size={"min": 12, "max": 15},
                hold_time={"min": 15, "max": 60},
                daily_quota=0.30
            ),
            "12:00-16:00": TimeZoneConfig(
                intensity=3,
                position_size={"min": 10, "max": 12},
                hold_time={"min": 20, "max": 50},
                daily_quota=0.20
            ),
            "16:00-20:00": TimeZoneConfig(
                intensity=5,
                position_size={"min": 12, "max": 15},
                hold_time={"min": 15, "max": 60},
                daily_quota=0.30
            ),
            "20:00-24:00": TimeZoneConfig(
                intensity=5,
                position_size={"min": 12, "max": 15},
                hold_time={"min": 10, "max": 45},
                daily_quota=0.40
            )
        },
        take_profit=TakeProfitConfig(
            tier1=TakeProfitTier(profit=0.005, action="reduce30"),
            tier2=TakeProfitTier(profit=0.01, action="reduce50"),
            tier3=TakeProfitTier(profit=0.02, action="reduce100"),
            hard=0.03,
            dynamic={
                "trend8plus": {"profit": 0.03, "action": "reduce100"},
                "trend6to7": {"profit": 0.02, "action": "reduce100"},
                "trend5minus": {"profit": 0.01, "action": "reduce100"}
            }
        ),
        stop_loss=StopLossConfig(
            soft=0.003,
            hard=0.005,
            time=120
        ),
        entry_threshold=EntryThreshold(
            trend_score=5,
            resonance_score=5,
            btc_trend=3,
            volatility={"min": 0.3, "max": 3.0}
        ),
        position=PositionConfig(
            max_positions=3,
            max_per_coin=15,
            total_exposure=0.20
        ),
        daily_control=DailyControlConfig(
            profit_target=3,
            loss_limit=5,
            consecutive_losses=3,
            pause_duration=30
        ),
        check_interval=CheckIntervalConfig(
            active=2,
            quiet=5,
            fixed=10
        ),
        resonance_weights=ResonanceWeights(
            sentiment=0.30,
            technical=0.30,
            capital_flow=0.25,
            market_env=0.15
        ),
        blacklist=BlacklistConfig(
            stop_loss_duration=2 * 60 * 60 * 1000,
            strong_trend_unlock=True,
            strong_trend_threshold=8,
            medium_trend_duration=30 * 60 * 1000,
            medium_trend_threshold=6,
            manual_ban=True,
            stablecoin_ban=True,
            stablecoins=["USDC", "USDT", "USDG", "USDE", "DAI", "TUSD", "PAXG", "XAUT"]
        )
    )


def get_current_time_zone() -> str:
    now = datetime.now(BEIJING_TZ)
    hour = now.hour
    
    if 0 <= hour < 4:
        return "00:00-04:00"
    elif 4 <= hour < 8:
        return "04:00-08:00"
    elif 8 <= hour < 12:
        return "08:00-12:00"
    elif 12 <= hour < 16:
        return "12:00-16:00"
    elif 16 <= hour < 20:
        return "16:00-20:00"
    else:
        return "20:00-24:00"


def get_time_zone_config(config: SparrowConfig) -> TimeZoneConfig:
    time_zone = get_current_time_zone()
    return config.time_zones[time_zone]


def get_check_interval(config: SparrowConfig) -> int:
    tz_config = get_time_zone_config(config)
    if tz_config.intensity >= 4:
        return config.check_interval.active
    return config.check_interval.quiet


def get_position_size_by_time_zone(config: SparrowConfig) -> Dict[str, float]:
    tz_config = get_time_zone_config(config)
    return tz_config.position_size


sparrow_config = get_default_config()
