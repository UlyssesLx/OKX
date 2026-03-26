from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
from loguru import logger
from pathlib import Path
import json

from app.core.okx_client import OKXClient
from app.strategies import (
    analyze_trend,
    check_market_environment,
    calculate_resonance_score,
    get_current_time_zone,
    get_time_zone_config,
    get_check_interval,
    sparrow_config
)
from app.models import (
    BalanceResponse,
    TickerResponse,
    TrendAnalysisResponse,
    OrderRequest,
    OrderResponse,
    MarketEnvironmentResponse,
    ResonanceResponse,
    TimeZoneInfoResponse
)
from app.services.simulation_manager import simulation_manager

router = APIRouter(prefix="/api/v1/trading", tags=["trading"])


async def get_client() -> OKXClient:
    return OKXClient()


@router.get("/balance", response_model=BalanceResponse)
async def get_balance():
    async with OKXClient() as client:
        result = await client.get_balance()
        
        if result.get("code") != "0":
            raise HTTPException(status_code=400, detail=result.get("msg", "获取余额失败"))
        
        data = result.get("data", [{}])[0]
        details = data.get("details", [])
        
        total_equity = float(data.get("totalEq", 0))
        available_usdt = 0.0
        positions = {}
        
        for d in details:
            if d.get("ccy") == "USDT":
                available_usdt = float(d.get("availBal", 0))
            if float(d.get("eqUsd", 0)) > 0.5 and d.get("ccy") != "USDT":
                coin = d.get("ccy")
                positions[coin] = {
                    "amount": float(d.get("spotBal", 0) or d.get("eq", 0)),
                    "value": float(d.get("eqUsd", 0)),
                    "avg_price": float(d.get("openAvgPx", 0) or d.get("accAvgPx", 0)),
                    "is_simulation": False,
                    "coin": coin
                }
        
        sim_positions = simulation_manager.get_positions()
        for pos in sim_positions:
            coin = pos["coin"]
            sim_key = f"{coin}_sim"
            positions[sim_key] = {
                "amount": pos["amount"],
                "value": pos["usdt_value"],
                "avg_price": pos["entry_price"],
                "is_simulation": True,
                "coin": coin,
                "is_short": False,
                "leverage": pos.get("leverage", 1.0),
                "is_swap": pos.get("is_swap", False)
            }
        
        sim_short_positions = simulation_manager.get_short_positions()
        for pos in sim_short_positions:
            coin = pos["coin"]
            sim_key = f"{coin}_short_sim"
            positions[sim_key] = {
                "amount": pos["amount"],
                "value": pos["usdt_value"],
                "avg_price": pos["entry_price"],
                "is_simulation": True,
                "coin": coin,
                "is_short": True,
                "leverage": pos.get("leverage", 1.0),
                "is_swap": pos.get("is_swap", False)
            }
        
        return BalanceResponse(
            total_equity=total_equity,
            available_usdt=available_usdt,
            positions=positions
        )


@router.get("/ticker/{inst_id}", response_model=TickerResponse)
async def get_ticker(inst_id: str):
    async with OKXClient() as client:
        result = await client.get_ticker(inst_id)
        
        if result.get("code") != "0":
            raise HTTPException(status_code=400, detail=result.get("msg", "获取行情失败"))
        
        data = result.get("data", [{}])[0]
        
        last_price = float(data.get("last", 0))
        open_price = float(data.get("open24h", last_price))
        change_24h = ((last_price - open_price) / open_price * 100) if open_price > 0 else 0
        
        return TickerResponse(
            symbol=inst_id.replace("-USDT", ""),
            inst_id=inst_id,
            price=last_price,
            change_24h=change_24h,
            volume_24h=float(data.get("vol24h", 0)),
            high_24h=float(data.get("high24h", 0)),
            low_24h=float(data.get("low24h", 0))
        )


@router.get("/tickers", response_model=List[TickerResponse])
async def get_tickers(inst_type: str = "SPOT"):
    async with OKXClient() as client:
        result = await client.get_tickers(inst_type)
        
        if result.get("code") != "0":
            raise HTTPException(status_code=400, detail=result.get("msg", "获取行情失败"))
        
        tickers = []
        for data in result.get("data", []):
            if not data.get("instId", "").endswith("-USDT"):
                continue
            
            last_price = float(data.get("last", 0))
            open_price = float(data.get("open24h", last_price))
            change_24h = ((last_price - open_price) / open_price * 100) if open_price > 0 else 0
            
            tickers.append(TickerResponse(
                symbol=data.get("instId", "").replace("-USDT", ""),
                inst_id=data.get("instId", ""),
                price=last_price,
                change_24h=change_24h,
                volume_24h=float(data.get("vol24h", 0)),
                high_24h=float(data.get("high24h", 0)),
                low_24h=float(data.get("low24h", 0))
            ))
        
        return tickers


@router.get("/trend/{inst_id}", response_model=TrendAnalysisResponse)
async def get_trend_analysis(inst_id: str):
    async with OKXClient() as client:
        candles_result = await client.get_candles(inst_id, "5m", 50)
        
        if candles_result.get("code") != "0":
            raise HTTPException(status_code=400, detail=candles_result.get("msg", "获取K线失败"))
        
        candles = candles_result.get("data", [])
        analysis = await analyze_trend(candles)
        
        return TrendAnalysisResponse(
            symbol=inst_id.replace("-USDT", ""),
            score=analysis.score,
            trend=analysis.trend,
            volatility=analysis.volatility,
            recent_change=analysis.recent_change,
            signals=analysis.signals,
            indicators=analysis.indicators
        )


@router.get("/market-environment", response_model=MarketEnvironmentResponse)
async def get_market_environment():
    async with OKXClient() as client:
        env = await check_market_environment(client)
        
        return MarketEnvironmentResponse(
            can_trade=env.can_trade,
            score=env.score,
            btc_score=env.btc_score,
            eth_score=env.eth_score,
            funding_score=env.funding_score,
            btc_change_24h=env.btc_change_24h,
            eth_change_24h=env.eth_change_24h,
            reason=env.reason
        )


@router.get("/resonance/{coin}", response_model=ResonanceResponse)
async def get_resonance(coin: str, sentiment_score: int = 7):
    async with OKXClient() as client:
        ticker_result = await client.get_ticker(f"{coin}-USDT")
        
        if ticker_result.get("code") != "0":
            raise HTTPException(status_code=400, detail=ticker_result.get("msg", "获取行情失败"))
        
        current_price = float(ticker_result.get("data", [{}])[0].get("last", 0))
        
        resonance = await calculate_resonance_score(client, coin, sentiment_score, current_price)
        
        return ResonanceResponse(
            can_buy=resonance.can_buy,
            total_score=resonance.total_score,
            sentiment_score=resonance.sentiment_score,
            technical_score=resonance.technical_score,
            capital_flow_score=resonance.capital_flow_score,
            market_env_score=resonance.market_env_score,
            reason=resonance.reason
        )


@router.get("/time-zone", response_model=TimeZoneInfoResponse)
async def get_time_zone_info():
    current_tz = get_current_time_zone()
    tz_config = get_time_zone_config(sparrow_config)
    check_interval = get_check_interval(sparrow_config)
    
    return TimeZoneInfoResponse(
        current_time_zone=current_tz,
        intensity=tz_config.intensity,
        position_size=tz_config.position_size,
        hold_time=tz_config.hold_time,
        daily_quota=tz_config.daily_quota,
        check_interval=check_interval
    )


@router.post("/order", response_model=OrderResponse)
async def place_order(request: OrderRequest):
    async with OKXClient() as client:
        if request.use_swap:
            result = await client.place_order(
                inst_id=request.inst_id,
                side=request.side.value,
                ord_type=request.order_type.value,
                sz=request.size,
                td_mode="cross",
                pos_side=request.pos_side,
                px=request.price
            )
        else:
            result = await client.place_order(
                inst_id=request.inst_id,
                side=request.side.value,
                order_type=request.order_type.value,
                size=request.size,
                price=request.price
            )

        if result.get("code") != "0":
            error_msg = result.get("msg", "下单失败")
            error_code = result.get("code", "")
            logger.error(f"下单失败: {error_msg}, 错误码: {error_code}, 请求: {request}")
            raise HTTPException(
                status_code=400,
                detail={
                    "message": error_msg,
                    "code": error_code,
                    "request": request.model_dump()
                }
            )

        data = result.get("data", [{}])[0]

        return OrderResponse(
            order_id=data.get("ordId", ""),
            inst_id=request.inst_id,
            side=request.side.value,
            order_type=request.order_type.value,
            size=request.size,
            price=request.price,
            status="pending",
            created_at=datetime.now()
        )


@router.delete("/order/{inst_id}/{order_id}")
async def cancel_order(inst_id: str, order_id: str):
    async with OKXClient() as client:
        result = await client.cancel_order(inst_id, order_id)
        
        if result.get("code") != "0":
            raise HTTPException(status_code=400, detail=result.get("msg", "撤单失败"))
        
        return {"success": True, "order_id": order_id}


@router.get("/simulation/positions")
async def get_simulation_positions():
    positions = simulation_manager.get_positions()
    stats = simulation_manager.get_stats()
    return {
        "positions": positions,
        "stats": stats
    }


@router.get("/simulation/trades")
async def get_simulation_trades(limit: int = 50):
    trades = simulation_manager.get_recent_trades(limit)
    return {"trades": trades}


@router.delete("/simulation/clear")
async def clear_simulation():
    simulation_manager.clear_all()
    return {"success": True}


@router.get("/long-config")
async def get_long_config():
    """获取多单配置"""
    from app.services.trading_engine import trading_engine
    config = trading_engine.config

    return {
        "minBullishScore": config.long_min_bullish_score,
        "sentimentThreshold": config.sentiment_threshold,
        "minCapitalFlowScore": config.min_capital_flow_score,
        "minTrendScore": config.long_min_trend_score,
        "maxTrendScore": config.long_max_trend_score,
        "rsiMin": config.long_rsi_min,
        "rsiMax": config.long_rsi_max,
        "rsiRange": [config.long_rsi_min, config.long_rsi_max],
        "minVolumeRatio": config.long_min_volume_ratio,
        "minChange24h": config.long_min_pullback_percent,
        "maxChange24h": config.long_max_pullback_percent,
        "changeRange": [config.long_min_pullback_percent, config.long_max_pullback_percent],
        "minMarketTrend": config.long_min_market_trend,
        "tradeSize": config.long_position_size,
        "shortTermTradeSize": config.short_term_trade_size,
        "positionRatio": config.long_position_ratio,
        "maxPositions": config.long_max_positions,
        "maxPositionPercent": config.long_max_position_percent,
        "stopLossPercent": config.long_stop_loss_percent,
        "takeProfit1": config.long_take_profit_1,
        "takeProfit2": config.long_take_profit_2,
        "timeStop": config.long_time_stop,
        "minTradeInterval": config.long_min_trade_interval,
        "maxDailyTrades": config.long_max_daily_trades,
        "minVolatility": config.long_min_volatility,
        "maxVolatility": config.long_max_volatility,
        "volatilityRange": [config.long_min_volatility, config.long_max_volatility],
        "trendWeakThreshold": config.trend_weak_threshold,
        "sidewaysMinScore": config.sideways_min_score,
        "sidewaysMaxScore": config.sideways_max_score,
        "pyramidEnabled": config.smart_pyramid_enabled,
        "pyramidMaxLayers": config.smart_pyramid_max_layers,
        "pyramidProfitThreshold": config.smart_pyramid_drop_threshold,
        "pyramidDropPerLayer": config.smart_pyramid_drop_per_layer,
        "pyramidMaxTrendScore": config.smart_pyramid_min_trend_score,
        "pyramidLayerRatios": config.smart_pyramid_layer_ratios,
        "pyramidBaseAmount": config.smart_pyramid_base_amount,
        "minCashReserve": config.smart_pyramid_min_cash,
        "pyramidOnStopLossEnabled": config.pyramid_on_stop_loss_enabled,
        "pyramidOnStopLossTrendScore": config.pyramid_on_stop_loss_trend_score,
        "pyramidOnStopLossMaxPositionPercent": config.pyramid_on_stop_loss_max_position_percent,
        "pyramidOnStopLossMinCash": config.pyramid_on_stop_loss_min_cash
    }


@router.post("/long-config")
async def update_long_config(config: dict):
    """更新多单配置"""
    from app.services.trading_engine import trading_engine

    trading_engine.config.long_min_bullish_score = config.get("minBullishScore", 5)
    trading_engine.config.sentiment_threshold = config.get("sentimentThreshold", 7)
    trading_engine.config.min_capital_flow_score = config.get("minCapitalFlowScore", 5)
    trading_engine.config.long_min_trend_score = config.get("minTrendScore", 6)
    trading_engine.config.long_max_trend_score = config.get("maxTrendScore", 10)
    trading_engine.config.long_rsi_min = config.get("rsiMin", 30.0)
    trading_engine.config.long_rsi_max = config.get("rsiMax", 70.0)
    trading_engine.config.long_min_volume_ratio = config.get("minVolumeRatio", 0.8)
    trading_engine.config.long_min_pullback_percent = config.get("minChange24h", -5.0)
    trading_engine.config.long_max_pullback_percent = config.get("maxChange24h", 8.0)
    trading_engine.config.long_min_market_trend = config.get("minMarketTrend", 4)
    trading_engine.config.long_position_size = config.get("tradeSize", 40.0)
    trading_engine.config.short_term_trade_size = config.get("shortTermTradeSize", 40.0)
    trading_engine.config.long_position_ratio = config.get("positionRatio", 1.0)
    trading_engine.config.long_max_positions = config.get("maxPositions", 3)
    trading_engine.config.long_max_position_percent = config.get("maxPositionPercent", 15.0)
    trading_engine.config.long_stop_loss_percent = config.get("stopLossPercent", 1.5)
    trading_engine.config.long_take_profit_1 = config.get("takeProfit1", 1.0)
    trading_engine.config.long_take_profit_2 = config.get("takeProfit2", 2.0)
    trading_engine.config.long_time_stop = config.get("timeStop", 48)
    trading_engine.config.long_min_trade_interval = config.get("minTradeInterval", 120)
    trading_engine.config.long_max_daily_trades = config.get("maxDailyTrades", 5)
    trading_engine.config.long_min_volatility = config.get("minVolatility", 0.3)
    trading_engine.config.long_max_volatility = config.get("maxVolatility", 5.0)
    trading_engine.config.trend_weak_threshold = config.get("trendWeakThreshold", 3)
    trading_engine.config.sideways_min_score = config.get("sidewaysMinScore", 3)
    trading_engine.config.sideways_max_score = config.get("sidewaysMaxScore", 5)
    # 金字塔加仓配置
    trading_engine.config.smart_pyramid_enabled = config.get("pyramidEnabled", True)
    trading_engine.config.smart_pyramid_max_layers = config.get("pyramidMaxLayers", 3)
    trading_engine.config.smart_pyramid_drop_threshold = config.get("pyramidProfitThreshold", -5.0)
    trading_engine.config.smart_pyramid_drop_per_layer = config.get("pyramidDropPerLayer", -10.0)
    trading_engine.config.smart_pyramid_min_trend_score = config.get("pyramidMaxTrendScore", 6)
    trading_engine.config.smart_pyramid_layer_ratios = config.get("pyramidLayerRatios", "1.0,0.6,0.35")
    trading_engine.config.smart_pyramid_base_amount = config.get("pyramidBaseAmount", 25.0)
    trading_engine.config.smart_pyramid_min_cash = config.get("minCashReserve", 15.0)
    # 止损拦截加仓配置
    trading_engine.config.pyramid_on_stop_loss_enabled = config.get("pyramidOnStopLossEnabled", True)
    trading_engine.config.pyramid_on_stop_loss_trend_score = config.get("pyramidOnStopLossTrendScore", 8)
    trading_engine.config.pyramid_on_stop_loss_max_position_percent = config.get("pyramidOnStopLossMaxPositionPercent", 15.0)
    trading_engine.config.pyramid_on_stop_loss_min_cash = config.get("pyramidOnStopLossMinCash", 25.0)

    # 保存配置到文件
    _save_long_config(config)
    
    logger.info(f"多单配置已更新并保存: {config}")

    return {"success": True, "config": config}


def _save_long_config(config: dict):
    """保存多单配置到文件"""
    config_file = Path("data/long_config.json")
    config_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"保存多单配置失败: {e}")


def _load_long_config() -> dict:
    """从文件加载多单配置"""
    config_file = Path("data/long_config.json")
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载多单配置失败: {e}")
    return {}


@router.get("/dip-buy-config")
async def get_dip_buy_config():
    """获取严格抄底配置"""
    from app.services.trading_engine import trading_engine
    config = trading_engine.config

    return {
        "enabled": config.dip_buy_enabled,
        "minTrendScore": config.dip_buy_min_trend_score,
        "minBtcTrend": config.dip_buy_min_btc_trend,
        "minEthTrend": config.dip_buy_min_eth_trend,
        "rsiThreshold": config.dip_buy_rsi_threshold,
        "volumeMultiplier": config.dip_buy_volume_multiplier,
        "minConsecutiveBearish": config.dip_buy_min_consecutive_bearish,
        "requireBullishReversal": config.dip_buy_require_bullish_reversal,
        "priceBelowMa5": config.dip_buy_price_below_ma5,
        "priceBelowMa10": config.dip_buy_price_below_ma10
    }


@router.post("/dip-buy-config")
async def update_dip_buy_config(config: dict):
    """更新严格抄底配置"""
    from app.services.trading_engine import trading_engine

    # 更新配置 - 完全对齐 ai_trading_bot.js 的 dipBuy 配置
    trading_engine.config.dip_buy_enabled = config.get("enabled", True)
    trading_engine.config.dip_buy_min_trend_score = config.get("minTrendScore", 7)
    trading_engine.config.dip_buy_min_btc_trend = config.get("minBtcTrend", 6)
    trading_engine.config.dip_buy_min_eth_trend = config.get("minEthTrend", 5)
    trading_engine.config.dip_buy_rsi_threshold = config.get("rsiThreshold", 35.0)
    trading_engine.config.dip_buy_volume_multiplier = config.get("volumeMultiplier", 2.0)
    trading_engine.config.dip_buy_min_consecutive_bearish = config.get("minConsecutiveBearish", 3)
    trading_engine.config.dip_buy_require_bullish_reversal = config.get("requireBullishReversal", True)
    trading_engine.config.dip_buy_price_below_ma5 = config.get("priceBelowMa5", True)
    trading_engine.config.dip_buy_price_below_ma10 = config.get("priceBelowMa10", True)

    logger.info(f"严格抄底配置已更新: {config}")

    return {"success": True, "config": config}


@router.get("/bearish-candle-config")
async def get_bearish_candle_config():
    """获取阴线买入配置"""
    from app.services.trading_engine import trading_engine
    return {
        "enabled": trading_engine.config.bearish_candle_enabled,
        "consecutiveCount": trading_engine.config.bearish_candle_consecutive_count,
        "minTrendScore": trading_engine.config.bearish_candle_min_trend_score,
        "priceBelowMa": trading_engine.config.bearish_candle_price_below_ma,
        "rsiEnabled": trading_engine.config.bearish_candle_rsi_enabled,
        "rsiOversold": trading_engine.config.bearish_candle_rsi_oversold,
        "volumeEnabled": trading_engine.config.bearish_candle_volume_enabled,
        "volumeRatio": trading_engine.config.bearish_candle_volume_ratio,
        "candleInterval": trading_engine.config.bearish_candle_interval
    }


@router.post("/bearish-candle-config")
async def update_bearish_candle_config(config: dict):
    """更新阴线买入配置"""
    from app.services.trading_engine import trading_engine

    trading_engine.config.bearish_candle_enabled = config.get("enabled", True)
    trading_engine.config.bearish_candle_consecutive_count = config.get("consecutiveCount", 2)
    trading_engine.config.bearish_candle_min_trend_score = config.get("minTrendScore", 6)
    trading_engine.config.bearish_candle_price_below_ma = config.get("priceBelowMa", True)
    trading_engine.config.bearish_candle_rsi_enabled = config.get("rsiEnabled", True)
    trading_engine.config.bearish_candle_rsi_oversold = config.get("rsiOversold", 40)
    trading_engine.config.bearish_candle_volume_enabled = config.get("volumeEnabled", True)
    trading_engine.config.bearish_candle_volume_ratio = config.get("volumeRatio", 1.2)
    trading_engine.config.bearish_candle_interval = config.get("candleInterval", "5m")

    logger.info(f"阴线买入配置已更新: {config}")

    return {"success": True, "config": config}


@router.get("/crash-rebound-config")
async def get_crash_rebound_config():
    """获取暴跌反弹配置"""
    from app.services.trading_engine import trading_engine
    return {
        "enabled": trading_engine.config.crash_rebound_enabled,
        "minDrop24h": trading_engine.config.crash_rebound_threshold,
        "minTrendScore": trading_engine.config.crash_rebound_min_trend_score,
        "minReboundPercent": trading_engine.config.crash_rebound_min_rebound_percent
    }


@router.post("/crash-rebound-config")
async def update_crash_rebound_config(config: dict):
    """更新暴跌反弹配置"""
    from app.services.trading_engine import trading_engine

    trading_engine.config.crash_rebound_enabled = config.get("enabled", True)
    trading_engine.config.crash_rebound_threshold = config.get("minDrop24h", -10.0)
    trading_engine.config.crash_rebound_min_trend_score = config.get("minTrendScore", 6)
    trading_engine.config.crash_rebound_min_rebound_percent = config.get("minReboundPercent", 2.0)

    logger.info(f"暴跌反弹配置已更新: {config}")

    return {"success": True, "config": config}


@router.get("/decision/{inst_id}")
async def make_single_coin_decision(inst_id: str):
    """
    单币种决策分析 - 对齐示例项目的 makeDecision 函数
    集成阴线买入和暴跌反弹策略
    """
    from app.services.trading_engine import trading_engine
    from app.strategies.enhanced import (
        check_consecutive_bearish_candles,
        check_crash_rebound,
        BEARISH_CANDLE_CONFIG,
        CRASH_REBOUND_CONFIG
    )
    from app.core.okx_client import OKXClient

    client = OKXClient()

    try:
        # 获取币种信息
        ticker = await client.get_ticker(inst_id)
        if not ticker:
            return {"error": f"无法获取 {inst_id} 行情数据"}

        current_price = ticker.get("last", 0)
        change_24h = ticker.get("change24h", 0) * 100

        # 获取趋势评分
        trend_data = await analyze_trend(inst_id)
        trend_score = trend_data.get("score", 5)

        # 获取RSI
        rsi = trend_data.get("rsi", 50)

        # 获取成交量比
        volume_ratio = ticker.get("volumeRatio", 1.0)

        # 获取大盘环境
        market_env = await check_market_environment()
        btc_trend = market_env.btc_score if market_env else 5
        eth_trend = getattr(market_env, 'eth_score', 5) if market_env else 5

        decision = {
            "instId": inst_id,
            "currentPrice": current_price,
            "change24h": change_24h,
            "trendScore": trend_score,
            "rsi": rsi,
            "volumeRatio": volume_ratio,
            "btcTrend": btc_trend,
            "ethTrend": eth_trend,
            "action": "hold",
            "reason": "",
            "signals": []
        }

        # 1. 检查短线策略条件
        short_term_passed = (
            trend_score >= trading_engine.config.long_min_trend_score and
            trend_score <= trading_engine.config.long_max_trend_score and
            rsi >= trading_engine.config.long_rsi_min and
            rsi <= trading_engine.config.long_rsi_max and
            volume_ratio >= trading_engine.config.long_min_volume_ratio and
            change_24h >= trading_engine.config.long_min_pullback_percent and
            change_24h <= trading_engine.config.long_max_pullback_percent
        )

        if short_term_passed:
            decision["action"] = "buy"
            decision["reason"] = f"短线策略通过：趋势{trend_score}分，RSI{rsi:.1f}，成交量{volume_ratio:.2f}x"
            decision["signals"].append("short_term")
            return decision

        # 2. 检查严格抄底策略
        if trading_engine.config.dip_buy_enabled:
            # 检查连续阴线
            bearish_result = await check_consecutive_bearish_candles(client, inst_id, current_price)

            # 获取MA指标
            indicators = trend_data.get("indicators", {})
            ma5 = indicators.get("ma5", 0)
            ma10 = indicators.get("ma10", 0)

            dip_buy_passed = (
                trend_score >= trading_engine.config.dip_buy_min_trend_score and
                btc_trend >= trading_engine.config.dip_buy_min_btc_trend and
                eth_trend >= trading_engine.config.dip_buy_min_eth_trend and
                rsi < trading_engine.config.dip_buy_rsi_threshold and
                volume_ratio > trading_engine.config.dip_buy_volume_multiplier and
                (bearish_result.is_bearish or not trading_engine.config.dip_buy_require_bullish_reversal) and
                (not trading_engine.config.dip_buy_price_below_ma5 or current_price < ma5) and
                (not trading_engine.config.dip_buy_price_below_ma10 or current_price < ma10)
            )

            if dip_buy_passed:
                decision["action"] = "buy"
                decision["reason"] = f"严格抄底：趋势{trend_score}分，BTC{btc_trend}分，ETH{eth_trend}分，RSI{rsi:.1f}，成交量{volume_ratio:.2f}x"
                decision["signals"].append("dip_buy")
                return decision

        # 3. 检查阴线买入策略（对齐示例项目：舆情不达标时的特殊买入信号）
        if BEARISH_CANDLE_CONFIG.enabled:
            bearish_check = await check_consecutive_bearish_candles(client, inst_id, current_price)
            if bearish_check.is_bearish and trend_score >= BEARISH_CANDLE_CONFIG.min_trend_score:
                decision["action"] = "buy"
                decision["reason"] = f"阴线买入：连续阴线后反弹，趋势{trend_score}/10"
                decision["signals"].append("bearish_candle")
                return decision

        # 4. 检查暴跌反弹策略（对齐示例项目）
        if CRASH_REBOUND_CONFIG.enabled:
            crash_check = await check_crash_rebound(client, inst_id, trend_score)
            if crash_check.is_crash_rebound:
                decision["action"] = "buy"
                decision["reason"] = f"暴跌反弹：24h跌幅{abs(change_24h):.2f}%，趋势回升至{trend_score}分"
                decision["signals"].append("crash_rebound")
                return decision

        # 没有触发任何买入信号
        decision["reason"] = f"无买入信号：趋势{trend_score}分，RSI{rsi:.1f}，24h涨跌{change_24h:.2f}%"
        return decision

    except Exception as e:
        logger.error(f"单币决策分析失败: {e}")
        return {"error": str(e)}


@router.get("/short-config")
async def get_short_config():
    """获取做空配置"""
    from app.services.trading_engine import trading_engine
    config = trading_engine.config

    from pathlib import Path
    import json
    settings_file = Path("settings.json")
    enable_short = True
    if settings_file.exists():
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)
                enable_short = settings.get("shortConfig", {}).get("enableShort", True)
        except Exception as e:
            logger.warning(f"加载 settings.json 失败: {e}")

    return {
        "enableShort": enable_short,
        "minBearishScore": config.short_min_bearish_score,
        "sentimentThreshold": config.sentiment_threshold,
        "minCapitalFlowScore": config.min_capital_flow_score,
        "minTrendScore": config.short_min_trend_score,
        "maxTrendScore": config.short_max_trend_score,
        "rsiMin": config.short_rsi_min,
        "rsiMax": config.short_rsi_max,
        "rsiRange": [config.short_rsi_min, config.short_rsi_max],
        "minVolumeRatio": config.short_min_volume_ratio,
        "changeRange": [config.short_min_pullback_percent, config.short_max_pullback_percent],
        "minPullbackPercent": config.short_min_pullback_percent,
        "maxPullbackPercent": config.short_max_pullback_percent,
        "maxMarketTrend": config.short_max_market_trend,
        "tradeSize": config.short_position_size,
        "shortTermTradeSize": config.short_term_trade_size,
        "positionRatio": config.short_position_ratio,
        "maxPositions": config.short_max_positions,
        "maxPositionPercent": config.short_max_position_percent,
        "stopLossPercent": config.short_stop_loss_percent,
        "takeProfit1": config.short_take_profit_1,
        "takeProfit2": config.short_take_profit_2,
        "timeStop": config.short_time_stop,
        "minTradeInterval": config.short_min_trade_interval,
        "maxDailyTrades": config.short_max_daily_trades,
        "minVolatility": config.short_min_volatility,
        "maxVolatility": config.short_max_volatility,
        "volatilityRange": [config.short_min_volatility, config.short_max_volatility],
        "decreasingBuyEnabled": config.short_decreasing_buy_enabled,
        "cooldownTrend1": config.short_cooldown_trend_1,
        "cooldownTrend2_3": config.short_cooldown_trend_2_3,
        "cooldownTrend4": config.short_cooldown_trend_4,
        "rallyThreshold": config.short_rally_threshold,
        "takeProfitPercent": config.short_take_profit_percent,
        "pyramidEnabled": config.short_pyramid_enabled,
        "pyramidMaxLayers": config.short_pyramid_max_layers,
        "pyramidProfitThreshold": config.short_pyramid_drop_threshold,
        "pyramidMaxTrendScore": config.short_pyramid_max_trend_score,
        "pyramidLayerRatios": config.short_pyramid_layer_ratios,
        "pyramidBaseAmount": config.short_pyramid_base_amount,
        "exemptionEnabled": config.short_exemption_enabled,
        "exemptionLossHigh": config.short_exemption_loss_high,
        "exemptionLossMedium": config.short_exemption_loss_medium,
        "exemptionProfit": config.short_exemption_profit,
        "minCashReserve": config.short_min_cash_reserve
    }


@router.post("/short-config")
async def update_short_config(config: dict):
    """更新做空配置"""
    from app.services.trading_engine import trading_engine
    from pathlib import Path
    import json

    trading_engine.config.short_min_bearish_score = config.get("minBearishScore", 7)
    trading_engine.config.sentiment_threshold = config.get("sentimentThreshold", 7)
    trading_engine.config.min_capital_flow_score = config.get("minCapitalFlowScore", 5)
    trading_engine.config.short_min_trend_score = config.get("minTrendScore", 0)
    trading_engine.config.short_max_trend_score = config.get("maxTrendScore", 4)
    trading_engine.config.short_rsi_min = config.get("rsiMin", 60.0)
    trading_engine.config.short_rsi_max = config.get("rsiMax", 80.0)
    trading_engine.config.short_min_volume_ratio = config.get("minVolumeRatio", 0.8)
    trading_engine.config.short_min_pullback_percent = config.get("minPullbackPercent", -8.0)
    trading_engine.config.short_max_pullback_percent = config.get("maxPullbackPercent", 5.0)
    trading_engine.config.short_max_market_trend = config.get("maxMarketTrend", 4)
    trading_engine.config.short_position_size = config.get("tradeSize", 40.0)
    trading_engine.config.short_term_trade_size = config.get("shortTermTradeSize", 40.0)
    trading_engine.config.short_position_ratio = config.get("positionRatio", 1.0)
    trading_engine.config.short_max_positions = config.get("maxPositions", 3)
    trading_engine.config.short_max_position_percent = config.get("maxPositionPercent", 15.0)
    trading_engine.config.short_stop_loss_percent = config.get("stopLossPercent", 1.5)
    trading_engine.config.short_take_profit_1 = config.get("takeProfit1", 1.0)
    trading_engine.config.short_take_profit_2 = config.get("takeProfit2", 2.0)
    trading_engine.config.short_time_stop = config.get("timeStop", 48)
    trading_engine.config.short_min_trade_interval = config.get("minTradeInterval", 120)
    trading_engine.config.short_max_daily_trades = config.get("maxDailyTrades", 5)
    trading_engine.config.short_min_volatility = config.get("minVolatility", 0.3)
    trading_engine.config.short_max_volatility = config.get("maxVolatility", 5.0)
    trading_engine.config.short_decreasing_buy_enabled = config.get("decreasingBuyEnabled", True)
    trading_engine.config.short_cooldown_trend_1 = config.get("cooldownTrend1", 15)
    trading_engine.config.short_cooldown_trend_2_3 = config.get("cooldownTrend2_3", 20)
    trading_engine.config.short_cooldown_trend_4 = config.get("cooldownTrend4", 30)
    trading_engine.config.short_rally_threshold = config.get("rallyThreshold", 1.03)
    trading_engine.config.short_take_profit_percent = config.get("takeProfitPercent", 3.0)
    trading_engine.config.short_pyramid_enabled = config.get("pyramidEnabled", True)
    trading_engine.config.short_pyramid_max_layers = config.get("pyramidMaxLayers", 3)
    trading_engine.config.short_pyramid_profit_threshold = config.get("pyramidProfitThreshold", -3.0)
    trading_engine.config.short_pyramid_max_trend_score = config.get("pyramidMaxTrendScore", 4)
    trading_engine.config.short_pyramid_layer_ratios = config.get("pyramidLayerRatios", "1.0,0.6,0.35,0.2")
    trading_engine.config.short_pyramid_base_amount = config.get("pyramidBaseAmount", 25.0)
    trading_engine.config.short_exemption_enabled = config.get("exemptionEnabled", True)
    trading_engine.config.short_exemption_loss_high = config.get("exemptionLossHigh", 60)
    trading_engine.config.short_exemption_loss_medium = config.get("exemptionLossMedium", 45)
    trading_engine.config.short_exemption_profit = config.get("exemptionProfit", 30)
    trading_engine.config.short_min_cash_reserve = config.get("minCashReserve", 30)

    settings_file = Path("settings.json")
    settings = {}
    if settings_file.exists():
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except Exception as e:
            logger.warning(f"加载 settings.json 失败: {e}")
    
    settings["shortConfig"] = config
    
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

    logger.info(f"做空配置已更新: {config}")

    return {"success": True, "config": config}


@router.get("/short-dip-config")
async def get_short_dip_config():
    """获取严格追空配置"""
    from app.services.trading_engine import trading_engine
    config = trading_engine.config

    return {
        "enabled": config.short_dip_enabled,
        "maxTrendScore": config.short_dip_max_trend_score,
        "maxBtcTrend": config.short_dip_max_btc_trend,
        "maxEthTrend": config.short_dip_max_eth_trend,
        "rsiThreshold": config.short_dip_rsi_threshold,
        "volumeMultiplier": config.short_dip_volume_multiplier,
        "minConsecutiveBullish": config.short_dip_min_consecutive_bullish,
        "requireBearishReversal": config.short_dip_require_bearish_reversal,
        "priceAboveMa5": config.short_dip_price_above_ma5,
        "priceAboveMa10": config.short_dip_price_above_ma10
    }


@router.post("/short-dip-config")
async def update_short_dip_config(config: dict):
    """更新严格追空配置"""
    from app.services.trading_engine import trading_engine

    trading_engine.config.short_dip_enabled = config.get("enabled", True)
    trading_engine.config.short_dip_max_trend_score = config.get("maxTrendScore", 4)
    trading_engine.config.short_dip_max_btc_trend = config.get("maxBtcTrend", 4)
    trading_engine.config.short_dip_max_eth_trend = config.get("maxEthTrend", 4)
    trading_engine.config.short_dip_rsi_threshold = config.get("rsiThreshold", 65.0)
    trading_engine.config.short_dip_volume_multiplier = config.get("volumeMultiplier", 2.0)
    trading_engine.config.short_dip_min_consecutive_bullish = config.get("minConsecutiveBullish", 3)
    trading_engine.config.short_dip_require_bearish_reversal = config.get("requireBearishReversal", True)
    trading_engine.config.short_dip_price_above_ma5 = config.get("priceAboveMa5", True)
    trading_engine.config.short_dip_price_above_ma10 = config.get("priceAboveMa10", True)

    logger.info(f"严格追空配置已更新: {config}")

    return {"success": True, "config": config}


@router.get("/short-bearish-config")
async def get_short_bearish_config():
    """获取阳线做空配置"""
    from app.services.trading_engine import trading_engine
    config = trading_engine.config

    return {
        "enabled": config.short_bearish_enabled,
        "consecutiveCount": config.short_bearish_consecutive_count,
        "maxTrendScore": config.short_bearish_max_trend_score,
        "priceAboveMa": config.short_bearish_price_above_ma,
        "rsiEnabled": config.short_bearish_rsi_enabled,
        "rsiPeriod": config.short_bearish_rsi_period,
        "rsiOverbought": config.short_bearish_rsi_overbought,
        "volumeEnabled": config.short_bearish_volume_enabled,
        "volumeRatio": config.short_bearish_volume_ratio,
        "candleInterval": config.short_bearish_candle_interval
    }


@router.post("/short-bearish-config")
async def update_short_bearish_config(config: dict):
    """更新阳线做空配置"""
    from app.services.trading_engine import trading_engine

    trading_engine.config.short_bearish_enabled = config.get("enabled", True)
    trading_engine.config.short_bearish_consecutive_count = config.get("consecutiveCount", 2)
    trading_engine.config.short_bearish_max_trend_score = config.get("maxTrendScore", 4)
    trading_engine.config.short_bearish_price_above_ma = config.get("priceAboveMa", True)
    trading_engine.config.short_bearish_rsi_enabled = config.get("rsiEnabled", True)
    trading_engine.config.short_bearish_rsi_period = config.get("rsiPeriod", 14)
    trading_engine.config.short_bearish_rsi_overbought = config.get("rsiOverbought", 70.0)
    trading_engine.config.short_bearish_volume_enabled = config.get("volumeEnabled", True)
    trading_engine.config.short_bearish_volume_ratio = config.get("volumeRatio", 1.2)
    trading_engine.config.short_bearish_candle_interval = config.get("candleInterval", "5m")

    logger.info(f"阳线做空配置已更新: {config}")

    return {"success": True, "config": config}


@router.get("/short-crash-config")
async def get_short_crash_config():
    """获取暴涨做空配置"""
    from app.services.trading_engine import trading_engine
    config = trading_engine.config

    return {
        "enabled": config.short_crash_enabled,
        "minRise24h": config.short_crash_min_rise_24h,
        "maxTrendScore": config.short_crash_max_trend_score,
        "minPullbackPercent": config.short_crash_min_pullback_percent,
        "rsiCheckEnabled": config.short_crash_rsi_check_enabled,
        "volumeCheckEnabled": config.short_crash_volume_check_enabled
    }


@router.post("/short-crash-config")
async def update_short_crash_config(config: dict):
    """更新暴涨做空配置"""
    from app.services.trading_engine import trading_engine

    trading_engine.config.short_crash_enabled = config.get("enabled", True)
    trading_engine.config.short_crash_min_rise_24h = config.get("minRise24h", 10.0)
    trading_engine.config.short_crash_max_trend_score = config.get("maxTrendScore", 4)
    trading_engine.config.short_crash_min_pullback_percent = config.get("minPullbackPercent", 2.0)
    trading_engine.config.short_crash_rsi_check_enabled = config.get("rsiCheckEnabled", False)
    trading_engine.config.short_crash_volume_check_enabled = config.get("volumeCheckEnabled", False)

    logger.info(f"暴涨做空配置已更新: {config}")

    return {"success": True, "config": config}


@router.get("/short-bearish-candle-config")
async def get_short_bearish_candle_config():
    """获取做空阳线卖出配置"""
    from app.services.trading_engine import trading_engine
    config = trading_engine.config

    return {
        "enabled": config.short_bearish_enabled,
        "consecutiveCount": config.short_bearish_consecutive_count,
        "maxTrendScore": config.short_bearish_max_trend_score,
        "rsiOverbought": config.short_bearish_rsi_overbought,
        "priceAboveMa": config.short_bearish_price_above_ma,
        "rsiEnabled": config.short_bearish_rsi_enabled,
        "volumeEnabled": config.short_bearish_volume_enabled,
        "volumeRatio": config.short_bearish_volume_ratio,
        "candleInterval": config.short_bearish_candle_interval
    }


@router.post("/short-bearish-candle-config")
async def update_short_bearish_candle_config(config: dict):
    """更新做空阳线卖出配置"""
    from app.services.trading_engine import trading_engine

    trading_engine.config.short_bearish_enabled = config.get("enabled", True)
    trading_engine.config.short_bearish_consecutive_count = config.get("consecutiveCount", 2)
    trading_engine.config.short_bearish_max_trend_score = config.get("maxTrendScore", 4)
    trading_engine.config.short_bearish_rsi_overbought = config.get("rsiOverbought", 60)
    trading_engine.config.short_bearish_price_above_ma = config.get("priceAboveMa", True)
    trading_engine.config.short_bearish_rsi_enabled = config.get("rsiEnabled", True)
    trading_engine.config.short_bearish_volume_enabled = config.get("volumeEnabled", True)
    trading_engine.config.short_bearish_volume_ratio = config.get("volumeRatio", 1.2)
    trading_engine.config.short_bearish_candle_interval = config.get("candleInterval", "5m")

    logger.info(f"做空阳线卖出配置已更新: {config}")

    return {"success": True, "config": config}


# 风控配置 API
# ==================== 交易Agent API ====================

@router.get("/agent/config")
async def get_trading_agent_config():
    """获取交易Agent配置"""
    from app.services.trading_agent import trading_agent
    return {
        "enabled": trading_agent.enabled,
        "autoExecute": trading_agent.auto_execute,
        "maxTradeAmount": trading_agent.max_trade_amount,
        "maxDailyTrades": trading_agent.max_daily_trades,
        "todayTradeCount": trading_agent.get_today_trade_count()
    }


@router.post("/agent/config")
async def update_trading_agent_config(config: dict):
    """更新交易Agent配置"""
    from app.services.trading_agent import trading_agent

    trading_agent.enabled = config.get("enabled", True)
    trading_agent.auto_execute = config.get("autoExecute", False)
    trading_agent.max_trade_amount = config.get("maxTradeAmount", 25)
    trading_agent.max_daily_trades = config.get("maxDailyTrades", 10)

    logger.info(f"交易Agent配置已更新: {config}")
    return {"success": True, "config": config}


@router.get("/agent/signals")
async def get_pending_signals():
    """获取待处理交易信号"""
    from app.services.trading_agent import trading_agent
    signals = trading_agent.load_signals()
    return {"signals": signals}


@router.post("/agent/signals")
async def add_trading_signal(signal: dict):
    """添加交易信号"""
    from app.services.trading_agent import trading_agent
    trading_agent.add_signal(signal)
    return {"success": True}


@router.delete("/agent/signals")
async def clear_signals():
    """清空所有信号"""
    from app.services.trading_agent import trading_agent
    trading_agent.clear_signals()
    return {"success": True}


@router.post("/agent/execute/{index}")
async def execute_signal(index: int):
    """执行指定索引的信号"""
    from app.services.trading_agent import trading_agent
    result = await trading_agent.execute_signal(index)
    return result


@router.post("/agent/execute-all")
async def execute_all_signals():
    """执行所有待处理信号"""
    from app.services.trading_agent import trading_agent
    results = await trading_agent.execute_all_signals()
    return {"results": results}


@router.get("/agent/trades")
async def get_agent_trades(limit: int = 50):
    """获取交易Agent的交易记录"""
    from app.services.trading_agent import trading_agent
    trades = trading_agent.get_recent_trades(limit)
    return {"trades": trades}


@router.get("/risk-config")
async def get_risk_config():
    """获取风控配置"""
    from app.services.trading_engine import trading_engine
    config = trading_engine.config

    return {
        # 核心配置
        "maxPositionPercent": config.max_position_percent,
        "maxDailyTrades": config.max_daily_trades,
        "maxDailyVolume": config.max_daily_volume,
        "stopLossPercent": config.stop_loss_percent,
        "takeProfitPercent": config.take_profit_percent,
        "sentimentThreshold": config.sentiment_threshold,
        "sentimentSellThreshold": config.sentiment_sell_threshold,
        "minCashReserve": config.min_cash_reserve,
        "tradeSize": config.trade_size,
        "buyCooldownMinutes": config.buy_cooldown_minutes,
        # 检查频率配置
        "checkIntervalHighIntensity": config.check_interval_high_intensity,
        "checkIntervalLowIntensity": config.check_interval_low_intensity,
        "checkIntensityThreshold": config.check_intensity_threshold,
        # 波段操作配置
        "bandTradeEnabled": config.band_trade_enabled,
        "bandTradeReduceAt": config.band_trade_reduce_at,
        "bandTradeSecondReduceAt": config.band_trade_second_reduce_at,
        "bandTradeFinalReduceAt": config.band_trade_final_reduce_at,
        "bandTradeReducePercent": config.band_trade_reduce_percent,
        "bandTradeSecondReducePercent": config.band_trade_second_reduce_percent,
        "bandTradeBuyBackAt": config.band_trade_buy_back_at,
        # 分层冷却期配置
        "tieredCooldownEnabled": config.tiered_cooldown_enabled,
        "cooldownTrend10": config.cooldown_trend_10,
        "cooldownTrend8_9": config.cooldown_trend_8_9,
        "cooldownTrend6_7": config.cooldown_trend_6_7,
        "cooldownScoreTier1": config.cooldown_score_tier1,
        "cooldownScoreTier2": config.cooldown_score_tier2,
        "cooldownScoreTier3": config.cooldown_score_tier3,
        # 止盈止损评分阈值配置
        "takeProfitScoreTier1": config.take_profit_score_tier1,
        "takeProfitScoreTier2": config.take_profit_score_tier2,
        "takeProfitScoreTier3": config.take_profit_score_tier3,
        "stopLossScoreTier1": config.stop_loss_score_tier1,
        "stopLossScoreTier2": config.stop_loss_score_tier2,
        "positionPercentScoreTier1": config.position_percent_score_tier1,
        "positionPercentScoreTier2": config.position_percent_score_tier2,
        "positionPercentScoreTier3": config.position_percent_score_tier3,
        # 波动率筛选配置
        "volatilityFilterEnabled": config.volatility_filter_enabled,
        "volatilityMin": config.volatility_min,
        "volatilityPreferred": config.volatility_preferred,
        "cooldownHighVolatility": config.cooldown_high_volatility,
        "cooldownLowVolatility": config.cooldown_low_volatility,
        "cooldownHighVolatilityMultiplier": config.cooldown_high_volatility_multiplier,
        "cooldownLowVolatilityMultiplier": config.cooldown_low_volatility_multiplier,
        # 趋势变盘减仓配置
        "trendReversalEnabled": config.trend_reversal_enabled,
        "trendReversalFromScore": config.trend_reversal_from_score,
        "trendReversalToScore": config.trend_reversal_to_score,
        "trendReversalMinPeriods": config.trend_reversal_min_periods,
        "trendReversalReducePercent": config.trend_reversal_reduce_percent,
        # 止盈限价单配置
        "takeProfitLimitOrderEnabled": config.take_profit_limit_order_enabled,
        "takeProfitLimitOrderAutoCancel": config.take_profit_limit_order_auto_cancel,
        # 时间衰减止损配置
        "timeDecayEnabled": config.time_decay_enabled,
        "timeDecayFactor": config.time_decay_factor,
        "maxStopLoss": config.max_stop_loss,
        "minStopLoss": config.min_stop_loss,
        "maxTakeProfit": config.max_take_profit,
        "minTakeProfit": config.min_take_profit,
        "timeDecayMaxStop": config.time_decay_max_stop,
        # 分批止盈配置（波段操作）
        "tieredTakeProfitEnabled": config.tiered_take_profit_enabled,
        "takeProfitTier1Percent": config.take_profit_tier1_percent,
        "takeProfitTier1Ratio": config.take_profit_tier1_ratio,
        "takeProfitTier2Percent": config.take_profit_tier2_percent,
        "takeProfitTier2Ratio": config.take_profit_tier2_ratio,
        "takeProfitTier3Percent": config.take_profit_tier3_percent,
        "takeProfitTier3Ratio": config.take_profit_tier3_ratio,
        # 舆情触发交易配置
        "sentimentTriggerEnabled": config.sentiment_trigger_enabled,
        "sentimentBuyThreshold": config.sentiment_buy_threshold,
        "sentimentSellThreshold": config.sentiment_sell_threshold,
        "sentimentMinVolumeSurge": config.sentiment_min_volume_surge,
        "sentimentTrendWeight": config.sentiment_trend_weight,
        "sentimentNewsWeight": config.sentiment_news_weight,
        # 其他配置
        "timeStopHours": config.time_stop_hours,
        "dynamicBandsEnabled": config.dynamic_bands_enabled,
        "overPositionExemptionEnabled": config.over_position_exemption_enabled,
        "exemptionLossHigh": config.exemption_loss_high,
        "exemptionLossMedium": config.exemption_loss_medium,
        "exemptionProfit": config.exemption_profit,
        # 回调加仓条件
        "pullbackBuyEnabled": config.pullback_buy_enabled,
        "pullbackBuyThreshold": config.pullback_buy_threshold,
        # 实时盈亏验证
        "pnlCheckEnabled": config.pnl_check_enabled,
        "pnlCheckThreshold": config.pnl_check_threshold,
        "pnlCheckAdjustScore": config.pnl_check_adjust_score,
        # 黑名单趋势反转检查
        "blacklistTrendCheckEnabled": config.blacklist_trend_check_enabled,
        "blacklistTrendThreshold": config.blacklist_trend_threshold,
        "blacklistTrendCount": config.blacklist_trend_count,
        "blacklistHighThreshold": config.blacklist_high_threshold,
        # 买入金额递减
        "decreasingTradeSizeEnabled": config.decreasing_trade_size_enabled,
        "decreasingFactors": config.decreasing_factors,
        # 止盈单管理
        "takeProfitOrderEnabled": config.take_profit_order_enabled,
        "takeProfitOrderPartial": config.take_profit_order_partial,
        "takeProfitAdjustOnBadSentiment": config.take_profit_adjust_on_bad_sentiment,
        "takeProfitBadSentimentThreshold": config.take_profit_bad_sentiment_threshold,
        # 黄金稳定币特殊处理
        "goldStablecoinSpecialHandling": config.gold_stablecoin_special_handling,
        "goldStablecoinList": config.gold_stablecoin_list,
        "goldStablecoinTakeProfit": config.gold_stablecoin_take_profit,
        # 智能超仓豁免期配置
        "overPositionExemptionEnabled": config.over_position_exemption_enabled,
        "exemptionLossHighMinutes": config.exemption_loss_high,
        "exemptionLossMediumMinutes": config.exemption_loss_medium,
        "exemptionProfitMinutes": config.exemption_profit,
        # 多空互斥决策配置
        "mutualExclusiveEnabled": config.mutual_exclusive_enabled,
        "mutualExclusiveMinScore": config.mutual_exclusive_min_score,
        "mutualExclusiveScoreDiff": config.mutual_exclusive_score_diff
    }


@router.post("/risk-config")
async def update_risk_config(config: dict):
    """更新风控配置 - 统一配置到 trading_engine"""
    from app.services.trading_engine import trading_engine

    # 核心配置
    trading_engine.config.max_position_percent = config.get("maxPositionPercent", 35.0)
    trading_engine.config.max_daily_trades = config.get("maxDailyTrades", 9999)
    trading_engine.config.max_daily_volume = config.get("maxDailyVolume", 1000.0)
    trading_engine.config.stop_loss_percent = config.get("stopLossPercent", -1.0)
    trading_engine.config.take_profit_percent = config.get("takeProfitPercent", 5.0)
    trading_engine.config.sentiment_threshold = config.get("sentimentThreshold", 7)
    trading_engine.config.sentiment_sell_threshold = config.get("sentimentSellThreshold", 3)
    trading_engine.config.min_cash_reserve = config.get("minCashReserve", 30.0)
    trading_engine.config.trade_size = config.get("tradeSize", 32.0)
    trading_engine.config.buy_cooldown_minutes = config.get("buyCooldownMinutes", 30)

    # 检查频率配置
    trading_engine.config.check_interval_high_intensity = config.get("checkIntervalHighIntensity", 2)
    trading_engine.config.check_interval_low_intensity = config.get("checkIntervalLowIntensity", 5)
    trading_engine.config.check_intensity_threshold = config.get("checkIntensityThreshold", 4)

    # 波段操作配置
    trading_engine.config.band_trade_enabled = config.get("bandTradeEnabled", True)
    trading_engine.config.band_trade_reduce_at = config.get("bandTradeReduceAt", 1.5)
    trading_engine.config.band_trade_second_reduce_at = config.get("bandTradeSecondReduceAt", 3.0)
    trading_engine.config.band_trade_final_reduce_at = config.get("bandTradeFinalReduceAt", 6.0)
    trading_engine.config.band_trade_reduce_percent = config.get("bandTradeReducePercent", 30.0)
    trading_engine.config.band_trade_second_reduce_percent = config.get("bandTradeSecondReducePercent", 50.0)
    trading_engine.config.band_trade_buy_back_at = config.get("bandTradeBuyBackAt", -2.0)

    # 分层冷却期配置
    trading_engine.config.tiered_cooldown_enabled = config.get("tieredCooldownEnabled", True)
    trading_engine.config.cooldown_trend_10 = config.get("cooldownTrend10", 15)
    trading_engine.config.cooldown_trend_8_9 = config.get("cooldownTrend8_9", 20)
    trading_engine.config.cooldown_trend_6_7 = config.get("cooldownTrend6_7", 30)
    trading_engine.config.cooldown_score_tier1 = config.get("cooldownScoreTier1", 10)
    trading_engine.config.cooldown_score_tier2 = config.get("cooldownScoreTier2", 8)
    trading_engine.config.cooldown_score_tier3 = config.get("cooldownScoreTier3", 6)

    # 止盈止损评分阈值配置
    trading_engine.config.take_profit_score_tier1 = config.get("takeProfitScoreTier1", 9)
    trading_engine.config.take_profit_score_tier2 = config.get("takeProfitScoreTier2", 7)
    trading_engine.config.take_profit_score_tier3 = config.get("takeProfitScoreTier3", 5)
    trading_engine.config.stop_loss_score_tier1 = config.get("stopLossScoreTier1", 8)
    trading_engine.config.stop_loss_score_tier2 = config.get("stopLossScoreTier2", 6)
    trading_engine.config.position_percent_score_tier1 = config.get("positionPercentScoreTier1", 10)
    trading_engine.config.position_percent_score_tier2 = config.get("positionPercentScoreTier2", 8)
    trading_engine.config.position_percent_score_tier3 = config.get("positionPercentScoreTier3", 6)

    # 波动率筛选配置
    trading_engine.config.volatility_filter_enabled = config.get("volatilityFilterEnabled", True)
    trading_engine.config.volatility_min = config.get("volatilityMin", 0.5)
    trading_engine.config.volatility_preferred = config.get("volatilityPreferred", 1.5)
    trading_engine.config.cooldown_high_volatility = config.get("cooldownHighVolatility", 5.0)
    trading_engine.config.cooldown_low_volatility = config.get("cooldownLowVolatility", 2.0)
    trading_engine.config.cooldown_high_volatility_multiplier = config.get("cooldownHighVolatilityMultiplier", 0.7)
    trading_engine.config.cooldown_low_volatility_multiplier = config.get("cooldownLowVolatilityMultiplier", 1.3)

    # 趋势变盘减仓配置
    trading_engine.config.trend_reversal_enabled = config.get("trendReversalEnabled", True)
    trading_engine.config.trend_reversal_from_score = config.get("trendReversalFromScore", 8)
    trading_engine.config.trend_reversal_to_score = config.get("trendReversalToScore", 5)
    trading_engine.config.trend_reversal_min_periods = config.get("trendReversalMinPeriods", 3)
    trading_engine.config.trend_reversal_reduce_percent = config.get("trendReversalReducePercent", 0.5)

    # 止盈限价单配置
    trading_engine.config.take_profit_limit_order_enabled = config.get("takeProfitLimitOrderEnabled", True)
    trading_engine.config.take_profit_limit_order_auto_cancel = config.get("takeProfitLimitOrderAutoCancel", True)

    # 时间衰减止损配置
    trading_engine.config.time_decay_enabled = config.get("timeDecayEnabled", True)
    trading_engine.config.time_decay_factor = config.get("timeDecayFactor", 0.1)
    trading_engine.config.max_stop_loss = config.get("maxStopLoss", -5.0)
    trading_engine.config.min_stop_loss = config.get("minStopLoss", -1.0)
    trading_engine.config.max_take_profit = config.get("maxTakeProfit", 15.0)
    trading_engine.config.min_take_profit = config.get("minTakeProfit", 2.0)
    trading_engine.config.time_decay_max_stop = config.get("timeDecayMaxStop", -8.0)

    # 分批止盈配置（波段操作）
    trading_engine.config.tiered_take_profit_enabled = config.get("tieredTakeProfitEnabled", True)
    trading_engine.config.take_profit_tier1_percent = config.get("takeProfitTier1Percent", 1.5)
    trading_engine.config.take_profit_tier1_ratio = config.get("takeProfitTier1Ratio", 0.3)
    trading_engine.config.take_profit_tier2_percent = config.get("takeProfitTier2Percent", 3.0)
    trading_engine.config.take_profit_tier2_ratio = config.get("takeProfitTier2Ratio", 0.5)
    trading_engine.config.take_profit_tier3_percent = config.get("takeProfitTier3Percent", 6.0)
    trading_engine.config.take_profit_tier3_ratio = config.get("takeProfitTier3Ratio", 1.0)

    # 舆情触发交易配置
    trading_engine.config.sentiment_trigger_enabled = config.get("sentimentTriggerEnabled", True)
    trading_engine.config.sentiment_buy_threshold = config.get("sentimentBuyThreshold", 7)
    trading_engine.config.sentiment_sell_threshold = config.get("sentimentSellThreshold", 3)
    trading_engine.config.sentiment_min_volume_surge = config.get("sentimentMinVolumeSurge", 2.0)
    trading_engine.config.sentiment_trend_weight = config.get("sentimentTrendWeight", 0.6)
    trading_engine.config.sentiment_news_weight = config.get("sentimentNewsWeight", 0.4)

    # 其他配置
    trading_engine.config.time_stop_hours = config.get("timeStopHours", 48.0)
    trading_engine.config.dynamic_bands_enabled = config.get("dynamicBandsEnabled", False)

    # 回调加仓条件
    trading_engine.config.pullback_buy_enabled = config.get("pullbackBuyEnabled", True)
    trading_engine.config.pullback_buy_threshold = config.get("pullbackBuyThreshold", 0.97)

    # 实时盈亏验证
    trading_engine.config.pnl_check_enabled = config.get("pnlCheckEnabled", True)
    trading_engine.config.pnl_check_threshold = config.get("pnlCheckThreshold", -1.0)
    trading_engine.config.pnl_check_adjust_score = config.get("pnlCheckAdjustScore", True)

    # 黑名单趋势反转检查
    trading_engine.config.blacklist_trend_check_enabled = config.get("blacklistTrendCheckEnabled", True)
    trading_engine.config.blacklist_trend_threshold = config.get("blacklistTrendThreshold", 8)
    trading_engine.config.blacklist_trend_count = config.get("blacklistTrendCount", 2)
    trading_engine.config.blacklist_high_threshold = config.get("blacklistHighThreshold", 9)

    # 买入金额递减
    trading_engine.config.decreasing_trade_size_enabled = config.get("decreasingTradeSizeEnabled", True)
    trading_engine.config.decreasing_factors = config.get("decreasingFactors", "1.0,0.6,0.35,0.2")

    # 止盈单管理
    trading_engine.config.take_profit_order_enabled = config.get("takeProfitOrderEnabled", True)
    trading_engine.config.take_profit_order_partial = config.get("takeProfitOrderPartial", 0.5)
    trading_engine.config.take_profit_adjust_on_bad_sentiment = config.get("takeProfitAdjustOnBadSentiment", True)
    trading_engine.config.take_profit_bad_sentiment_threshold = config.get("takeProfitBadSentimentThreshold", 3)

    # 黄金稳定币特殊处理
    trading_engine.config.gold_stablecoin_special_handling = config.get("goldStablecoinSpecialHandling", True)
    trading_engine.config.gold_stablecoin_list = config.get("goldStablecoinList", "XAUT,PAXG")
    trading_engine.config.gold_stablecoin_take_profit = config.get("goldStablecoinTakeProfit", 0.2)

    # 智能超仓豁免期配置
    trading_engine.config.over_position_exemption_enabled = config.get("overPositionExemptionEnabled", True)
    trading_engine.config.exemption_loss_high = config.get("exemptionLossHighMinutes", 60)
    trading_engine.config.exemption_loss_medium = config.get("exemptionLossMediumMinutes", 45)
    trading_engine.config.exemption_profit = config.get("exemptionProfitMinutes", 30)

    # 多空互斥决策配置
    trading_engine.config.mutual_exclusive_enabled = config.get("mutualExclusiveEnabled", True)
    trading_engine.config.mutual_exclusive_min_score = config.get("mutualExclusiveMinScore", 60.0)
    trading_engine.config.mutual_exclusive_score_diff = config.get("mutualExclusiveScoreDiff", 15.0)

    # 保存到持久化文件
    trading_engine._save_persistent_state()

    logger.info(f"风控配置已更新: {config}")

    return {"success": True, "config": config}
