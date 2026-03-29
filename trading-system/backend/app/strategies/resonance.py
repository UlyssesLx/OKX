from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from app.core.okx_client import OKXClient
from app.strategies.common_indicators import (
    calculate_rsi_simple,
    calculate_ma,
    calculate_volatility,
    calculate_volume_ratio
)


@dataclass
class MarketEnvironment:
    can_trade: bool
    score: int
    btc_score: int
    eth_score: int
    funding_score: int
    btc_change_24h: float
    eth_change_24h: float
    reason: str


@dataclass
class CapitalFlow:
    has_inflow: bool
    score: int
    volume_ratio: float
    volume_score: int
    oi_score: int
    reason: str


@dataclass
class ResonanceResult:
    can_buy: bool
    total_score: int
    sentiment_score: int
    technical_score: int
    capital_flow_score: int
    market_env_score: int
    trend_score: int = 0
    reason: str = ""


@dataclass
class TechnicalValidation:
    """技术面验证结果"""
    passed: bool
    score: int
    pass_count: int
    total_checks: int
    checks: Dict[str, bool]
    reason: str


def validate_technical_indicators_resonance(
    sentiment_score: int,
    rsi: float,
    volume_ratio: float,
    current_price: float,
    ma5: float,
    volatility: float,
    min_pass_count: int = 2,
    trend_score_threshold: int = 5,
    rsi_min: float = 30.0,
    rsi_max: float = 80.0,
    volume_ratio_min: float = 0.8,
    ma5_tolerance: float = 0.98,
    volatility_min: float = 0.2
) -> TechnicalValidation:
    """
    技术面综合验证 - 与示例项目对齐
    检查5项指标，通过至少min_pass_count项即可
    """
    checks = {
        "trend_score": sentiment_score >= trend_score_threshold,
        "rsi_valid": rsi_min <= rsi <= rsi_max,
        "volume_valid": volume_ratio > volume_ratio_min,
        "price_above_ma5": current_price > ma5 * ma5_tolerance if ma5 > 0 else True,
        "volatility_valid": volatility >= volatility_min
    }
    
    pass_count = sum(checks.values())
    technical_score = round((pass_count / 5) * 10)
    
    passed = pass_count >= min_pass_count or technical_score >= 5
    
    return TechnicalValidation(
        passed=passed,
        score=technical_score,
        pass_count=pass_count,
        total_checks=5,
        checks=checks,
        reason=f"技术面{pass_count}/5项通过，评分{technical_score}/10"
    )


async def check_market_environment(client: OKXClient) -> MarketEnvironment:
    try:
        btc_ticker = await client.get_ticker("BTC-USDT")
        eth_ticker = await client.get_ticker("ETH-USDT")
        btc_funding = await client.get_funding_rate("BTC-USDT-SWAP")
        
        btc_data = btc_ticker.get("data", [{}])[0] if btc_ticker.get("data") else {}
        eth_data = eth_ticker.get("data", [{}])[0] if eth_ticker.get("data") else {}
        funding_data = btc_funding.get("data", [{}])[0] if btc_funding.get("data") else {}
        
        if not btc_data or not eth_data:
            return MarketEnvironment(
                can_trade=True,
                score=5,
                btc_score=5,
                eth_score=5,
                funding_score=5,
                btc_change_24h=0.0,
                eth_change_24h=0.0,
                reason="数据获取失败，默认允许交易"
            )
        
        btc_last = float(btc_data.get("last", 0))
        btc_open = float(btc_data.get("open24h", btc_last))
        btc_change_24h = ((btc_last - btc_open) / btc_open * 100) if btc_open > 0 else 0
        
        eth_last = float(eth_data.get("last", 0))
        eth_open = float(eth_data.get("open24h", eth_last))
        eth_change_24h = ((eth_last - eth_open) / eth_open * 100) if eth_open > 0 else 0
        
        btc_candles = await client.get_candles("BTC-USDT", bar="1H", limit=20)
        btc_score = 5
        if btc_candles and btc_candles.get("data"):
            candles = btc_candles["data"]
            if len(candles) >= 10:
                closes = [float(c[4]) for c in reversed(candles)]
                ma5 = sum(closes[-5:]) / 5
                ma10 = sum(closes[-10:]) / 10
                price = closes[-1]
                
                if price > ma5 and ma5 > ma10:
                    btc_score = 8
                elif price > ma5:
                    btc_score = 6
                elif price < ma5 and ma5 < ma10:
                    btc_score = 2
                elif price < ma5:
                    btc_score = 4
        
        eth_candles = await client.get_candles("ETH-USDT", bar="1H", limit=20)
        eth_score = 5
        if eth_candles and eth_candles.get("data"):
            candles = eth_candles["data"]
            if len(candles) >= 10:
                closes = [float(c[4]) for c in reversed(candles)]
                ma5 = sum(closes[-5:]) / 5
                ma10 = sum(closes[-10:]) / 10
                price = closes[-1]
                
                if price > ma5 and ma5 > ma10:
                    eth_score = 8
                elif price > ma5:
                    eth_score = 6
                elif price < ma5 and ma5 < ma10:
                    eth_score = 2
                elif price < ma5:
                    eth_score = 4
        
        funding_score = 5
        if funding_data:
            funding_rate = float(funding_data.get("fundingRate", 0))
            if funding_rate < -0.0001:
                funding_score = 8
            elif funding_rate < 0:
                funding_score = 7
            elif funding_rate < 0.0001:
                funding_score = 5
            else:
                funding_score = 3
        
        market_score = round((btc_score + eth_score + funding_score) / 3)
        can_trade = market_score >= 4
        
        return MarketEnvironment(
            can_trade=can_trade,
            score=market_score,
            btc_score=btc_score,
            eth_score=eth_score,
            funding_score=funding_score,
            btc_change_24h=btc_change_24h,
            eth_change_24h=eth_change_24h,
            reason=f"大盘环境{'良好' if can_trade else '差'}({market_score}/10): BTC{btc_score}分, ETH{eth_score}分, 资金{funding_score}分"
        )
    except Exception as e:
        return MarketEnvironment(
            can_trade=True,
            score=5,
            btc_score=5,
            eth_score=5,
            funding_score=5,
            btc_change_24h=0.0,
            eth_change_24h=0.0,
            reason=f"检测失败，默认允许: {str(e)}"
        )


async def check_capital_flow(client: OKXClient, coin: str, min_score: int = 5) -> CapitalFlow:
    try:
        inst_id = f"{coin}-USDT"
        swap_inst_id = f"{coin}-USDT-SWAP"
        
        spot_ticker = await client.get_ticker(inst_id)
        swap_ticker = await client.get_ticker(swap_inst_id)
        open_interest = await client.get_open_interest(swap_inst_id)
        candles_1h = await client.get_candles(inst_id, bar='1H', limit=24)
        
        spot_data = spot_ticker.get("data", [{}])[0] if spot_ticker.get("data") else {}
        oi_data = open_interest.get("data", [{}])[0] if open_interest.get("data") else {}
        candle_data = candles_1h.get("data", []) if candles_1h.get("data") else []
        
        if not spot_data:
            return CapitalFlow(
                has_inflow=False,
                score=5,
                volume_ratio=1.0,
                volume_score=5,
                oi_score=5,
                reason="数据获取失败"
            )
        
        vol_24h = float(spot_data.get("vol24h", 0))
        avg_vol_per_hour = vol_24h / 24 if vol_24h > 0 else 1
        
        current_hour_vol = 0
        if candle_data and len(candle_data) >= 1:
            current_hour_vol = float(candle_data[0][5]) if candle_data[0][5] else 0
        
        volume_ratio = current_hour_vol / avg_vol_per_hour if avg_vol_per_hour > 0 else 1.0
        
        spot_last = float(spot_data.get("last", 0))
        spot_open = float(spot_data.get("open24h", spot_last))
        change_24h = ((spot_last - spot_open) / spot_open * 100) if spot_open > 0 else 0
        
        oi_score = 5
        if oi_data:
            oi_usd = float(oi_data.get("oiUsd", 0))
            if oi_usd > 500000000:
                oi_score = 8
            elif oi_usd > 100000000:
                oi_score = 7
            elif oi_usd > 50000000:
                oi_score = 6
            else:
                oi_score = 4
        
        volume_score = 5
        if volume_ratio > 3:
            volume_score = 9
        elif volume_ratio > 2:
            volume_score = 8
        elif volume_ratio > 1.5:
            volume_score = 7
        elif volume_ratio > 1.2:
            volume_score = 6
        elif volume_ratio > 0.8:
            volume_score = 5
        else:
            volume_score = 4
        
        flow_score = round((volume_score + oi_score) / 2)
        has_inflow = flow_score >= min_score and change_24h > -5
        
        return CapitalFlow(
            has_inflow=has_inflow,
            score=flow_score,
            volume_ratio=volume_ratio,
            volume_score=volume_score,
            oi_score=oi_score,
            reason=f"量比{volume_ratio:.2f}x, 持仓{oi_score}分, 评分{flow_score}, 24h涨跌{change_24h:.2f}%"
        )
    except Exception as e:
        return CapitalFlow(
            has_inflow=False,
            score=5,
            volume_ratio=1.0,
            volume_score=5,
            oi_score=5,
            reason=f"检测失败: {str(e)}"
        )


async def calculate_resonance_score(
    client: OKXClient,
    coin: str,
    sentiment_score: int,
    current_price: float,
    weights: Optional[Dict[str, float]] = None,
    min_capital_flow_score: int = 5,
    market_env: Optional[MarketEnvironment] = None,
    rsi: Optional[float] = None,
    volume_ratio: Optional[float] = None,
    ma5: Optional[float] = None,
    volatility: Optional[float] = None,
    technical_config: Optional[Dict[str, Any]] = None
) -> ResonanceResult:
    if weights is None:
        weights = {
            "sentiment": 0.30,
            "technical": 0.25,
            "capital_flow": 0.25,
            "market_env": 0.20
        }
    
    tech_min_pass_count = 2
    tech_trend_threshold = 5
    tech_rsi_min = 30.0
    tech_rsi_max = 80.0
    tech_volume_min = 0.8
    tech_ma5_tolerance = 0.98
    tech_volatility_min = 0.2
    
    if technical_config:
        tech_min_pass_count = technical_config.get("min_pass_count", 2)
        tech_trend_threshold = technical_config.get("trend_score_threshold", 5)
        tech_rsi_min = technical_config.get("rsi_min", 30.0)
        tech_rsi_max = technical_config.get("rsi_max", 80.0)
        tech_volume_min = technical_config.get("volume_ratio_min", 0.8)
        tech_ma5_tolerance = technical_config.get("ma5_tolerance", 0.98)
        tech_volatility_min = technical_config.get("volatility_min", 0.2)

    if market_env is None:
        market_env = await check_market_environment(client)
    capital_flow = await check_capital_flow(client, coin, min_capital_flow_score)
    
    if rsi is None or volume_ratio is None or ma5 is None or volatility is None:
        try:
            candles_result = await client.get_candles(f"{coin}-USDT", bar="5m", limit=50)
            if candles_result and candles_result.get("data"):
                candles = candles_result["data"]
                prices = [float(c[4]) for c in reversed(candles)]
                volumes = [float(c[5]) for c in reversed(candles)]

                rsi = calculate_rsi_simple(prices, 14) if len(prices) >= 15 else 50
                ma5 = calculate_ma(prices, 5) if len(prices) >= 5 else current_price
                volume_ratio = calculate_volume_ratio(volumes, 20) if len(volumes) >= 20 else 1.0
                volatility = calculate_volatility(prices) if len(prices) >= 2 else 1.0
            else:
                rsi = 50
                volume_ratio = 1.0
                ma5 = current_price
                volatility = 1.0
        except Exception as e:
            rsi = 50
            volume_ratio = 1.0
            ma5 = current_price
            volatility = 1.0
    
    technical = validate_technical_indicators_resonance(
        sentiment_score=sentiment_score,
        rsi=rsi,
        volume_ratio=volume_ratio,
        current_price=current_price,
        ma5=ma5,
        volatility=volatility,
        min_pass_count=tech_min_pass_count,
        trend_score_threshold=tech_trend_threshold,
        rsi_min=tech_rsi_min,
        rsi_max=tech_rsi_max,
        volume_ratio_min=tech_volume_min,
        ma5_tolerance=tech_ma5_tolerance,
        volatility_min=tech_volatility_min
    )
    
    technical_score = technical.score
    
    total_score = round(
        sentiment_score * weights.get("sentiment", 0.30) +
        technical_score * weights.get("technical", 0.25) +
        capital_flow.score * weights.get("capital_flow", 0.25) +
        market_env.score * weights.get("market_env", 0.20)
    )
    
    can_buy = (
        total_score >= 6 and
        market_env.can_trade and
        (technical.passed or technical.score >= 5) and
        (capital_flow.has_inflow or capital_flow.score >= 4)
    )
    
    reasons = []
    if total_score < 6:
        reasons.append(f"共振分数{total_score}<6")
    if not market_env.can_trade:
        reasons.append(f"大盘环境不佳(BTC={market_env.btc_score}分,ETH={market_env.eth_score}分,资金费率={market_env.funding_score}分,综合={market_env.score}分<4)")
    if not technical.passed and technical.score < 5:
        reasons.append(f"技术面不佳({technical.reason})")
    if not capital_flow.has_inflow and capital_flow.score < 4:
        reasons.append(f"资金流向不佳(评分{capital_flow.score}<4且24h涨跌<-5%)")
    
    return ResonanceResult(
        can_buy=can_buy,
        total_score=total_score,
        sentiment_score=sentiment_score,
        technical_score=technical_score,
        capital_flow_score=capital_flow.score,
        market_env_score=market_env.score,
        trend_score=sentiment_score,
        reason="; ".join(reasons) if reasons else "多维度共振通过"
    )


def calculate_position_size(resonance_score: int, base_size: float) -> Dict[str, Any]:
    if resonance_score >= 9:
        size = base_size * 1.25
        reason = f"共振极强({resonance_score}分)，重仓${size:.0f}"
    elif resonance_score >= 8:
        size = base_size
        reason = f"共振强({resonance_score}分)，标准仓${size:.0f}"
    elif resonance_score >= 7:
        size = base_size * 0.78
        reason = f"共振良好({resonance_score}分)，基础仓${size:.0f}"
    elif resonance_score >= 6:
        size = base_size * 0.625
        reason = f"共振一般({resonance_score}分)，轻仓${size:.0f}"
    elif resonance_score >= 5:
        size = base_size * 0.47
        reason = f"共振较弱({resonance_score}分)，试探仓${size:.0f}"
    else:
        size = 0
        reason = f"共振不足({resonance_score}分)，不建仓"
    
    return {"size": size, "reason": reason}
