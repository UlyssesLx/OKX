"""
公共指标计算模块
统一所有技术指标计算，消除代码重复
"""
from typing import List, Optional, Tuple
from dataclasses import dataclass
import numpy as np


@dataclass
class MACDResult:
    macd: float
    signal: float
    histogram: float
    prev_histogram: float


@dataclass
class BollingerBands:
    upper: float
    middle: float
    lower: float


@dataclass
class RSIResult:
    rsi: float
    avg_gain: float
    avg_loss: float


def calculate_ma(prices: List[float], period: int) -> float:
    if not prices:
        return 0.0
    if len(prices) < period:
        return prices[-1]
    return sum(prices[-period:]) / period


def calculate_ema(prices: List[float], period: int) -> float:
    if not prices:
        return 0.0
    if len(prices) < period:
        return prices[-1]

    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period

    for i in range(period, len(prices)):
        ema = prices[i] * k + ema * (1 - k)

    return ema


def calculate_rsi(prices: List[float], period: int = 14) -> RSIResult:
    if len(prices) < period + 1:
        return RSIResult(rsi=50.0, avg_gain=0.0, avg_loss=0.0)

    gains = []
    losses = []

    for i in range(len(prices) - period, len(prices)):
        change = prices[i] - prices[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(-change)

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return RSIResult(rsi=100.0, avg_gain=avg_gain, avg_loss=avg_loss)

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return RSIResult(rsi=rsi, avg_gain=avg_gain, avg_loss=avg_loss)


def calculate_rsi_simple(prices: List[float], period: int = 14) -> float:
    """简单的RSI计算，仅返回RSI值"""
    return calculate_rsi(prices, period).rsi


def calculate_macd(
    prices: List[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> MACDResult:
    if len(prices) < slow:
        return MACDResult(macd=0.0, signal=0.0, histogram=0.0, prev_histogram=0.0)

    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    macd_line = ema_fast - ema_slow

    macd_series = []
    for i in range(slow, len(prices)):
        fast_ema = calculate_ema(prices[:i + 1], fast)
        slow_ema = calculate_ema(prices[:i + 1], slow)
        macd_series.append(fast_ema - slow_ema)

    signal_line = calculate_ema(macd_series, signal) if len(macd_series) >= signal else 0.0
    histogram = macd_line - signal_line

    prev_histogram = 0.0
    if len(macd_series) > 1:
        prev_signal = calculate_ema(macd_series[:-1], signal) if len(macd_series[:-1]) >= signal else signal_line
        prev_histogram = macd_series[-2] - prev_signal if len(macd_series) >= 2 else histogram

    return MACDResult(
        macd=macd_line,
        signal=signal_line,
        histogram=histogram,
        prev_histogram=prev_histogram
    )


def calculate_bollinger(prices: List[float], period: int = 20) -> BollingerBands:
    if not prices:
        return BollingerBands(upper=0.0, middle=0.0, lower=0.0)

    if len(prices) < period:
        price = prices[-1]
        return BollingerBands(
            upper=price * 1.02,
            middle=price,
            lower=price * 0.98
        )

    slice_prices = prices[-period:]
    middle = sum(slice_prices) / period
    variance = sum((p - middle) ** 2 for p in slice_prices) / period
    std_dev = variance ** 0.5

    return BollingerBands(
        upper=middle + 2 * std_dev,
        middle=middle,
        lower=middle - 2 * std_dev
    )


def calculate_volatility(prices: List[float]) -> float:
    if len(prices) < 2:
        return 0.0

    changes = []
    for i in range(1, len(prices)):
        changes.append((prices[i] - prices[i - 1]) / prices[i - 1] * 100)

    if not changes:
        return 0.0

    mean = sum(changes) / len(changes)
    variance = sum((c - mean) ** 2 for c in changes) / len(changes)
    std_volatility = variance ** 0.5

    max_price = max(prices)
    min_price = min(prices)
    avg_price = sum(prices) / len(prices)
    range_volatility = ((max_price - min_price) / avg_price) * 100 if avg_price > 0 else 0.0

    return (std_volatility + range_volatility) / 2


def calculate_volume_ratio(volumes: List[float], period: int = 20) -> float:
    if len(volumes) < period:
        return 1.0

    avg_vol = sum(volumes[-period:]) / period
    current_vol = volumes[-1] if volumes else 1

    return current_vol / avg_vol if avg_vol > 0 else 1.0


def calculate_technicals(
    prices: List[float],
    volumes: Optional[List[float]] = None,
    period: int = 14
) -> dict:
    """
    计算所有主要技术指标
    返回包含所有指标的字典
    """
    result = {
        "ma5": calculate_ma(prices, 5) if len(prices) >= 5 else prices[-1] if prices else 0.0,
        "ma10": calculate_ma(prices, 10) if len(prices) >= 10 else prices[-1] if prices else 0.0,
        "ma20": calculate_ma(prices, 20) if len(prices) >= 20 else prices[-1] if prices else 0.0,
        "rsi": calculate_rsi_simple(prices, period),
        "macd": calculate_macd(prices),
        "bollinger": calculate_bollinger(prices),
        "volatility": calculate_volatility(prices),
    }

    if volumes:
        result["volume_ratio"] = calculate_volume_ratio(volumes)
        result["vol_ma5"] = calculate_ma(volumes, 5) if len(volumes) >= 5 else sum(volumes) / len(volumes) if volumes else 0.0
        result["vol_ma10"] = calculate_ma(volumes, 10) if len(volumes) >= 10 else sum(volumes) / len(volumes) if volumes else 0.0

    return result