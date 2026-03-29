"""
信号去重机制模块
避免同一周期重复交易
"""
from typing import Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio


class SignalType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    SHORT = "short"
    COVER = "cover"


class DedupStatus(str, Enum):
    ALLOWED = "allowed"
    BLOCKED_COOLDOWN = "blocked_cooldown"
    BLOCKED_DUPLICATE = "blocked_duplicate"
    BLOCKED_PENDING = "blocked_pending"


@dataclass
class SignalRecord:
    coin: str
    signal_type: SignalType
    price: float
    timestamp: datetime
    reason: str
    trend_score: int
    resonance_score: int


@dataclass
class DedupResult:
    allowed: bool
    status: DedupStatus
    reason: str
    cooldown_remaining: int = 0


class SignalDeduplicator:
    """
    信号去重器
    追踪最近交易信号，防止同一币种在同一周期内重复交易
    """
    _instance: Optional['SignalDeduplicator'] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._records: Dict[str, SignalRecord] = {}
        self._pending_signals: Dict[str, datetime] = {}
        self._cooldowns: Dict[str, datetime] = {}
        self._settings: Dict[str, int] = {
            "buy_cooldown_minutes": 30,
            "sell_cooldown_minutes": 15,
            "short_cooldown_minutes": 20,
            "cover_cooldown_minutes": 15,
            "pending_timeout_minutes": 5,
        }

    def update_settings(self, settings: Dict[str, int]):
        """更新去重设置"""
        self._settings.update(settings)

    def _get_cooldown_minutes(self, signal_type: SignalType) -> int:
        mapping = {
            SignalType.BUY: "buy_cooldown_minutes",
            SignalType.SELL: "sell_cooldown_minutes",
            SignalType.SHORT: "short_cooldown_minutes",
            SignalType.COVER: "cover_cooldown_minutes",
        }
        return self._settings.get(mapping.get(signal_type, "buy_cooldown_minutes"), 30)

    def _make_key(self, coin: str, signal_type: SignalType) -> str:
        return f"{coin}_{signal_type.value}"

    def _is_in_cooldown(self, key: str) -> bool:
        if key not in self._cooldowns:
            return False
        cooldown_end = self._cooldowns[key]
        return datetime.now() < cooldown_end

    def _get_cooldown_remaining(self, key: str) -> int:
        if key not in self._cooldowns:
            return 0
        remaining = self._cooldowns[key] - datetime.now()
        return max(0, int(remaining.total_seconds() / 60))

    def _is_pending(self, coin: str) -> bool:
        if coin not in self._pending_signals:
            return False
        pending_until = self._pending_signals[coin]
        return datetime.now() < pending_until

    def check_signal(self, coin: str, signal_type: SignalType) -> DedupResult:
        """
        检查信号是否允许
        """
        key = self._make_key(coin, signal_type)

        if self._is_pending(coin):
            return DedupResult(
                allowed=False,
                status=DedupStatus.BLOCKED_PENDING,
                reason=f"{coin} 存在待处理订单"
            )

        if self._is_in_cooldown(key):
            remaining = self._get_cooldown_remaining(key)
            return DedupResult(
                allowed=False,
                status=DedupStatus.BLOCKED_COOLDOWN,
                reason=f"{coin} {signal_type.value} 冷却中，剩余{remaining}分钟",
                cooldown_remaining=remaining
            )

        if key in self._records:
            last_record = self._records[key]
            return DedupResult(
                allowed=False,
                status=DedupStatus.BLOCKED_DUPLICATE,
                reason=f"{coin} {signal_type.value} 已交易({last_record.price:.4f}@{last_record.timestamp.strftime('%H:%M')})"
            )

        return DedupResult(
            allowed=True,
            status=DedupStatus.ALLOWED,
            reason="信号允许"
        )

    def record_signal(
        self,
        coin: str,
        signal_type: SignalType,
        price: float,
        reason: str,
        trend_score: int = 0,
        resonance_score: int = 0
    ):
        """记录已执行的信号"""
        key = self._make_key(coin, signal_type)
        self._records[key] = SignalRecord(
            coin=coin,
            signal_type=signal_type,
            price=price,
            timestamp=datetime.now(),
            reason=reason,
            trend_score=trend_score,
            resonance_score=resonance_score
        )

        cooldown_minutes = self._get_cooldown_minutes(signal_type)
        self._cooldowns[key] = datetime.now() + timedelta(minutes=cooldown_minutes)

    def set_pending(self, coin: str, timeout_minutes: int = None):
        """设置待处理状态"""
        if timeout_minutes is None:
            timeout_minutes = self._settings.get("pending_timeout_minutes", 5)
        self._pending_signals[coin] = datetime.now() + timedelta(minutes=timeout_minutes)

    def clear_pending(self, coin: str):
        """清除待处理状态"""
        if coin in self._pending_signals:
            del self._pending_signals[coin]

    def get_last_signal(self, coin: str, signal_type: SignalType) -> Optional[SignalRecord]:
        """获取最近一次信号记录"""
        key = self._make_key(coin, signal_type)
        return self._records.get(key)

    def get_all_records(self) -> Dict[str, SignalRecord]:
        """获取所有信号记录"""
        return self._records.copy()

    def clear_expired(self):
        """清理过期记录"""
        now = datetime.now()
        expired_keys = []

        for key, record in self._records.items():
            age = now - record.timestamp
            if age > timedelta(hours=24):
                expired_keys.append(key)

        for key in expired_keys:
            del self._records[key]

        expired_pending = []
        for coin, pending_until in self._pending_signals.items():
            if now > pending_until:
                expired_pending.append(coin)

        for coin in expired_pending:
            del self._pending_signals[coin]

    def force_clear(self, coin: str, signal_type: SignalType = None):
        """强制清除指定币种的记录"""
        if signal_type:
            key = self._make_key(coin, signal_type)
            if key in self._records:
                del self._records[key]
            if key in self._cooldowns:
                del self._cooldowns[key]
        else:
            keys_to_remove = [k for k in self._records if k.startswith(f"{coin}_")]
            for key in keys_to_remove:
                del self._records[key]
            if coin in self._pending_signals:
                del self._pending_signals[coin]


signal_dedup = SignalDeduplicator()


def get_signal_dedup() -> SignalDeduplicator:
    return signal_dedup