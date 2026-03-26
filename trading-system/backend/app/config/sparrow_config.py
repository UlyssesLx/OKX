"""
币市麻雀战法策略配置 v4.1
时区感知 + 小步快跑 + 严格风控
"""
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class TimeZoneConfig:
    intensity: int
    position_size: Dict[str, int]
    hold_time: Dict[str, int]
    daily_quota: float


@dataclass
class TakeProfitConfig:
    tier1: Dict[str, Any]
    tier2: Dict[str, Any]
    tier3: Dict[str, Any]
    hard: float
    dynamic: Dict[str, Dict[str, Any]]


@dataclass
class StopLossConfig:
    soft: float
    hard: float
    time: int


@dataclass
class EntryThresholdConfig:
    trend_score: int
    resonance_score: int
    btc_trend: int
    volatility: Dict[str, float]


@dataclass
class PositionConfig:
    max_positions: int
    max_per_coin: float
    total_exposure: float


@dataclass
class DailyControlConfig:
    profit_target: float
    loss_limit: float
    consecutive_losses: int
    pause_duration: int


@dataclass
class CheckIntervalConfig:
    active: int      # 高活跃时段检查间隔（分钟）
    quiet: int       # 低活跃时段检查间隔（分钟）
    fixed: int       # 禁用时区感知时的固定检查间隔（分钟）


@dataclass
class ResonanceWeightsConfig:
    sentiment: float
    technical: float
    capital_flow: float
    market_env: float


@dataclass
class BlacklistConfig:
    stop_loss_duration: int
    strong_trend_unlock: bool
    strong_trend_threshold: int
    medium_trend_duration: int
    medium_trend_threshold: int
    manual_ban: bool
    stablecoin_ban: bool
    stablecoins: list


class SparrowConfig:
    """币市麻雀战法配置类"""

    def __init__(self):
        self.version = "4.1-sparrow"
        self.base_capital = 287
        self.daily_target = 9
        self.weekly_target = 21

        # 时区配置 (GMT+8 北京时间)
        self.time_zones = {
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
        }

        # 止盈止损配置
        self.take_profit = TakeProfitConfig(
            tier1={"profit": 0.005, "action": "reduce30"},
            tier2={"profit": 0.01, "action": "reduce50"},
            tier3={"profit": 0.02, "action": "reduce100"},
            hard=0.03,
            dynamic={
                "trend8plus": {"profit": 0.03, "action": "reduce100"},
                "trend6to7": {"profit": 0.02, "action": "reduce100"},
                "trend5minus": {"profit": 0.01, "action": "reduce100"}
            }
        )

        self.stop_loss = StopLossConfig(
            soft=0.003,
            hard=0.005,
            time=120
        )

        # 选股门槛
        self.entry_threshold = EntryThresholdConfig(
            trend_score=5,
            resonance_score=5,
            btc_trend=3,
            volatility={"min": 0.3, "max": 3.0}
        )

        # 仓位管理
        self.position = PositionConfig(
            max_positions=3,
            max_per_coin=15,
            total_exposure=0.20
        )

        # 日度控制
        self.daily_control = DailyControlConfig(
            profit_target=3,
            loss_limit=5,
            consecutive_losses=3,
            pause_duration=30
        )

        # 检查频率
        self.check_interval = CheckIntervalConfig(
            active=2,      # 高活跃时段：2分钟
            quiet=5,       # 低活跃时段：5分钟
            fixed=5        # 禁用时区感知时：固定5分钟
        )

        # 时区感知配置
        self.timezone_aware_enabled = True  # 是否启用时区感知功能

        # 共振权重
        self.resonance_weights = ResonanceWeightsConfig(
            sentiment=0.30,
            technical=0.30,
            capital_flow=0.25,
            market_env=0.15
        )

        # 黑名单配置
        self.blacklist = BlacklistConfig(
            stop_loss_duration=2 * 60 * 60 * 1000,
            strong_trend_unlock=True,
            strong_trend_threshold=8,
            medium_trend_duration=30 * 60 * 1000,
            medium_trend_threshold=6,
            manual_ban=True,
            stablecoin_ban=True,
            stablecoins=["USDC", "USDT", "USDG", "USDE", "DAI", "TUSD", "PAXG", "XAUT"]
        )


sparrow_config = SparrowConfig()


def get_current_time_zone() -> str:
    """获取当前时段"""
    from datetime import datetime, timezone, timedelta

    beijing_tz = timezone(timedelta(hours=8))
    now = datetime.now(beijing_tz)
    hour = now.hour

    # 定义时段范围（按小时排序）
    time_ranges = [
        (0, 4, "00:00-04:00"),
        (4, 8, "04:00-08:00"),
        (8, 12, "08:00-12:00"),
        (12, 16, "12:00-16:00"),
        (16, 20, "16:00-20:00"),
        (20, 24, "20:00-24:00"),
    ]

    for start, end, time_range in time_ranges:
        if start <= hour < end:
            return time_range

    return "00:00-04:00"


def get_time_zone_config(config: SparrowConfig) -> TimeZoneConfig:
    """获取当前时段配置"""
    current_tz = get_current_time_zone()
    return config.time_zones.get(current_tz, config.time_zones["00:00-04:00"])


def get_check_interval(config: SparrowConfig) -> int:
    """获取检查频率"""
    tz_config = get_time_zone_config(config)
    if tz_config.intensity >= 4:
        return config.check_interval.active
    else:
        return config.check_interval.quiet
