from typing import List, Dict, Optional
from dataclasses import dataclass


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
class TrendAnalysis:
    score: int
    trend: str
    volatility: float
    recent_change: float
    signals: List[str]
    indicators: Dict[str, any]
    bullish_score: int = 0
    bearish_score: int = 0


def calculate_ma(prices: List[float], period: int) -> float:
    if len(prices) < period:
        return prices[-1] if prices else 0.0
    return sum(prices[-period:]) / period


def calculate_ema(prices: List[float], period: int) -> float:
    if len(prices) < period:
        return prices[-1] if prices else 0.0
    
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    
    for i in range(period, len(prices)):
        ema = prices[i] * k + ema * (1 - k)
    
    return ema


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    
    gains = 0.0
    losses = 0.0
    
    for i in range(len(prices) - period, len(prices)):
        change = prices[i] - prices[i - 1]
        if change > 0:
            gains += change
        else:
            losses -= change
    
    avg_gain = gains / period
    avg_loss = losses / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> MACDResult:
    if len(prices) < slow:
        return MACDResult(0.0, 0.0, 0.0, 0.0)
    
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
    if len(prices) < period:
        price = prices[-1] if prices else 0.0
        return BollingerBands(upper=price * 1.02, middle=price, lower=price * 0.98)
    
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
        changes.append((prices[i] - prices[i - 1]) / prices[i - 1])
    
    mean = sum(changes) / len(changes)
    variance = sum((c - mean) ** 2 for c in changes) / len(changes)
    std_volatility = (variance ** 0.5) * 100
    
    max_price = max(prices)
    min_price = min(prices)
    avg_price = sum(prices) / len(prices)
    range_volatility = ((max_price - min_price) / avg_price) * 100
    
    return (std_volatility + range_volatility) / 2


async def analyze_trend(candles: List[List], current_price: Optional[float] = None) -> TrendAnalysis:
    if len(candles) < 20:
        return TrendAnalysis(
            score=5,
            trend="neutral",
            volatility=0.0,
            recent_change=0.0,
            signals=[],
            indicators={},
            bullish_score=5,
            bearish_score=5
        )
    
    data = []
    for c in candles:
        data.append({
            "open": float(c[1]),
            "high": float(c[2]),
            "low": float(c[3]),
            "close": float(c[4]),
            "vol": float(c[5])
        })
    data.reverse()
    
    prices = [d["close"] for d in data]
    volumes = [d["vol"] for d in data]
    
    ma5 = calculate_ma(prices, 5)
    ma10 = calculate_ma(prices, 10)
    ma20 = calculate_ma(prices, 20)
    
    vol_ma5 = calculate_ma(volumes, 5)
    vol_ma10 = calculate_ma(volumes, 10)
    
    volume_golden_cross = vol_ma5 > vol_ma10 * 1.05 and volumes[-1] > vol_ma5
    volume_increasing = all(volumes[-(i + 1)] >= volumes[-(i + 2)] * 0.9 for i in range(min(3, len(volumes) - 1)))
    
    macd = calculate_macd(prices)
    macd_golden_cross = macd.macd > macd.signal and macd.histogram > 0 and macd.histogram > macd.prev_histogram
    macd_death_cross = macd.macd < macd.signal and macd.histogram < 0 and macd.histogram < macd.prev_histogram
    
    rsi = calculate_rsi(prices, 14)
    
    bollinger = calculate_bollinger(prices, 20)
    price_position = (prices[-1] - bollinger.lower) / (bollinger.upper - bollinger.lower) if bollinger.upper != bollinger.lower else 0.5
    
    volatility = calculate_volatility(prices)
    
    recent_change = 0.0
    if len(prices) >= 5:
        recent_change = (prices[-1] - prices[-5]) / prices[-5] * 100
    
    bullish_score = 5
    bearish_score = 5
    signals = []
    
    if ma5 > ma10 and ma10 > ma20:
        bullish_score += 3
        signals.append("均线多头排列")
    elif ma5 < ma10 and ma10 < ma20:
        bearish_score += 3
        signals.append("均线空头排列")
    elif ma5 > ma10:
        bullish_score += 1
        signals.append("短期均线上穿")
    elif ma5 < ma10:
        bearish_score += 1
        signals.append("短期均线下穿")
    
    if volume_golden_cross:
        bullish_score += 2
        signals.append("成交量金叉")
    elif volume_increasing:
        bullish_score += 1
        signals.append("成交量递增")
    
    if macd_golden_cross:
        bullish_score += 2
        signals.append("MACD金叉")
    elif macd.macd > macd.signal:
        bullish_score += 1
        signals.append("MACD多头")
    
    if macd_death_cross:
        bearish_score += 2
        signals.append("MACD死叉")
    elif macd.macd < macd.signal:
        bearish_score += 1
        signals.append("MACD空头")
    
    if 50 < rsi < 70:
        bullish_score += 1
        signals.append("RSI强势区")
    elif rsi > 70:
        bearish_score += 2
        signals.append("RSI超买(做空信号)")
    elif 30 < rsi < 50:
        bearish_score += 1
        signals.append("RSI弱势区")
    elif rsi < 30:
        bullish_score += 2
        signals.append("RSI超卖(反弹机会)")
    
    if 0.5 < price_position < 0.8:
        bullish_score += 1
        signals.append("价格中轨偏上")
    elif price_position > 0.8:
        bearish_score += 2
        signals.append("价格接近上轨(做空机会)")
    elif price_position < 0.2:
        bullish_score += 2
        signals.append("价格接近下轨(反弹机会)")
    
    if 2 < recent_change < 8:
        bullish_score += 1
        signals.append(f"温和上涨{recent_change:.1f}%")
    elif 8 < recent_change < 15:
        bullish_score += 1
        signals.append(f"强势上涨{recent_change:.1f}%")
    elif recent_change > 15:
        bearish_score += 2
        signals.append(f"暴涨{recent_change:.1f}%(做空机会)")
    elif -8 < recent_change < -2:
        bearish_score += 1
        signals.append(f"温和下跌{recent_change:.1f}%")
    elif recent_change < -8:
        bullish_score += 2
        signals.append(f"暴跌{recent_change:.1f}%(反弹机会)")
    
    if 1.5 < volatility < 6:
        bullish_score += 1
        bearish_score += 1
        signals.append("波动率适中")
    elif volatility > 10:
        signals.append("波动率过高")
    
    bullish_score = max(1, min(10, bullish_score))
    bearish_score = max(1, min(10, bearish_score))
    
    if bullish_score >= 7 and bullish_score > bearish_score + 2:
        trend = "bullish"
        score = bullish_score
    elif bearish_score >= 7 and bearish_score > bullish_score + 2:
        trend = "bearish"
        score = 10 - bearish_score + 1
    else:
        trend = "neutral"
        score = 5
    
    return TrendAnalysis(
        score=max(1, min(10, score)),
        trend=trend,
        volatility=volatility,
        recent_change=recent_change,
        signals=signals,
        indicators={
            "ma5": ma5,
            "ma10": ma10,
            "ma20": ma20,
            "rsi": round(rsi, 1),
            "macd": round(macd.macd, 4),
            "volume_golden_cross": volume_golden_cross,
            "macd_golden_cross": macd_golden_cross,
            "macd_death_cross": macd_death_cross,
            "price_position": round(price_position, 2)
        },
        bullish_score=bullish_score,
        bearish_score=bearish_score
    )


@dataclass
class TechnicalValidation:
    passed: bool
    score: int
    reason: str
    details: Dict[str, any]
    fail_reason: str = ""


def validate_technical_indicators(
    prices: List[float],
    current_price: float,
    sentiment_score: int = 5,
    rsi_oversold_threshold: float = 40.0,
    rsi_overbought_threshold: float = 70.0
) -> TechnicalValidation:
    """
    技术面多指标验证
    验证RSI、MA5、波动率等多个技术指标
    """
    if len(prices) < 20:
        return TechnicalValidation(
            passed=True,
            score=sentiment_score,
            reason="数据不足，使用舆情评分",
            details={}
        )
    
    signals = []
    score = sentiment_score
    
    rsi = calculate_rsi(prices, 14)
    ma5 = calculate_ma(prices, 5)
    ma10 = calculate_ma(prices, 10)
    ma20 = calculate_ma(prices, 20)
    volatility = calculate_volatility(prices)
    macd = calculate_macd(prices)
    bollinger = calculate_bollinger(prices, 20)
    
    rsi_oversold = rsi < rsi_oversold_threshold
    rsi_overbought = rsi > rsi_overbought_threshold
    
    if rsi_oversold:
        signals.append(f"RSI超卖({rsi:.1f}<{rsi_oversold_threshold})")
        score += 1
    elif rsi_overbought:
        signals.append(f"RSI超买({rsi:.1f}>{rsi_overbought_threshold})")
        score -= 1
    elif 40 < rsi < 60:
        signals.append(f"RSI中性({rsi:.1f})")
    
    if current_price > ma5 > ma10:
        signals.append("价格>MA5>MA10多头排列")
        score += 1
    elif current_price < ma5 < ma10:
        signals.append("价格<MA5<MA10空头排列")
        score -= 1
    
    if current_price > ma5:
        signals.append("价格在MA5上方")
    else:
        signals.append("价格在MA5下方")
    
    if 1.5 < volatility < 6:
        signals.append(f"波动率适中({volatility:.1f}%)")
        score += 1
    elif volatility > 10:
        signals.append(f"波动率过高({volatility:.1f}%)")
        score -= 1
    
    if macd.macd > macd.signal and macd.histogram > 0:
        signals.append("MACD金叉")
        score += 1
    elif macd.macd < macd.signal and macd.histogram < 0:
        signals.append("MACD死叉")
        score -= 1
    
    price_position = (current_price - bollinger.lower) / (bollinger.upper - bollinger.lower) if bollinger.upper != bollinger.lower else 0.5
    if price_position < 0.3:
        signals.append(f"价格接近布林下轨({price_position:.2f})")
        score += 1
    elif price_position > 0.8:
        signals.append(f"价格接近布林上轨({price_position:.2f})")
    
    score = max(1, min(10, score))
    
    fail_reason = ""
    if rsi_overbought:
        fail_reason = f"RSI超买({rsi:.1f}>{rsi_overbought_threshold})"
    elif score < 5:
        fail_reason = f"技术评分不足({score}<5)"
    passed = score >= 5 and not rsi_overbought
    
    reason = " | ".join(signals) if signals else "技术指标正常"
    
    return TechnicalValidation(
        passed=passed,
        score=score,
        reason=reason,
        fail_reason=fail_reason,
        details={
            "rsi": round(rsi, 1),
            "rsi_oversold": rsi_oversold,
            "rsi_overbought": rsi_overbought,
            "ma5": round(ma5, 4),
            "ma10": round(ma10, 4),
            "ma20": round(ma20, 4),
            "volatility": round(volatility, 2),
            "macd_signal": "golden_cross" if macd.macd > macd.signal else "death_cross",
            "bollinger_position": round(price_position, 2)
        }
    )
