"""
回测API接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio

from app.core.okx_client import OKXClient
from app.services.backtest_engine import run_backtest, BacktestEngine
from app.services.trading_engine import TradingConfig

router = APIRouter(prefix="/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    coins: List[str]
    start_date: str
    end_date: str
    initial_balance: float = 1000.0
    position_size: float = 40.0
    leverage: float = 1.0
    enable_short: bool = False
    bar: str = "1H"
    
    long_min_bullish_score: int = 7
    long_bullish_gap: int = 2
    long_min_trend_score: int = 6
    long_max_trend_score: int = 10
    long_rsi_min: float = 30.0
    long_rsi_max: float = 70.0
    long_min_volume_ratio: float = 0.8
    long_max_pullback_percent: float = 8.0
    long_min_pullback_percent: float = -5.0
    long_stop_loss_percent: float = -1.5
    long_take_profit_percent: float = 3.0
    long_max_positions: int = 3
    
    short_min_bearish_score: int = 7
    short_min_trend_score: int = 3
    short_max_trend_score: int = 5
    short_rsi_min: float = 70.0
    short_rsi_max: float = 85.0
    short_min_volume_ratio: float = 1.2
    short_min_pullback_percent: float = 3.0
    short_max_pullback_percent: float = 10.0
    short_stop_loss_percent: float = 1.5
    short_take_profit_percent: float = 3.0
    short_max_positions: int = 3
    short_max_btc_trend: int = 5
    short_max_eth_trend: int = 5


class BacktestResponse(BaseModel):
    success: bool
    message: str
    result: Optional[Dict[str, Any]] = None


async def fetch_historical_candles(inst_id: str, bar: str, start_ts: int, end_ts: int) -> List[List]:
    """获取历史K线数据"""
    all_candles = []
    current_end = end_ts
    limit = 300
    
    async with OKXClient() as client:
        while current_end > start_ts:
            try:
                result = await client._request('GET', '/api/v5/market/candles', params={
                    'instId': inst_id,
                    'bar': bar,
                    'before': str(current_end),
                    'limit': str(limit)
                })
                
                if result.get('code') != '0':
                    break
                
                candles = result.get('data', [])
                if not candles:
                    break
                
                for c in candles:
                    ts = int(c[0])
                    if start_ts <= ts <= end_ts:
                        all_candles.append(c)
                
                if len(candles) < limit:
                    break
                
                oldest_ts = int(candles[-1][0])
                if oldest_ts >= current_end:
                    break
                
                current_end = oldest_ts - 1
                
            except Exception as e:
                print(f"Error fetching candles for {inst_id}: {e}")
                break
    
    all_candles.sort(key=lambda x: int(x[0]))
    return all_candles


@router.post("/run", response_model=BacktestResponse)
async def run_backtest_api(request: BacktestRequest):
    """执行回测"""
    try:
        start_dt = datetime.strptime(request.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(request.end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
        
        start_ts = int(start_dt.timestamp() * 1000)
        end_ts = int(end_dt.timestamp() * 1000)
        
        if end_dt > datetime.now():
            return BacktestResponse(
                success=False,
                message="结束日期不能超过当前日期"
            )
        
        if (end_dt - start_dt).days > 90:
            return BacktestResponse(
                success=False,
                message="回测时间范围不能超过90天"
            )
        
        config = TradingConfig(
            long_min_bullish_score=request.long_min_bullish_score,
            long_bullish_gap=request.long_bullish_gap,
            long_min_trend_score=request.long_min_trend_score,
            long_max_trend_score=request.long_max_trend_score,
            long_rsi_min=request.long_rsi_min,
            long_rsi_max=request.long_rsi_max,
            long_min_volume_ratio=request.long_min_volume_ratio,
            long_max_pullback_percent=request.long_max_pullback_percent,
            long_min_pullback_percent=request.long_min_pullback_percent,
            long_stop_loss_percent=request.long_stop_loss_percent,
            long_take_profit_percent=request.long_take_profit_percent,
            long_max_positions=request.long_max_positions,
            short_min_bearish_score=request.short_min_bearish_score,
            short_min_trend_score=request.short_min_trend_score,
            short_max_trend_score=request.short_max_trend_score,
            short_rsi_min=request.short_rsi_min,
            short_rsi_max=request.short_rsi_max,
            short_min_volume_ratio=request.short_min_volume_ratio,
            short_min_pullback_percent=request.short_min_pullback_percent,
            short_max_pullback_percent=request.short_max_pullback_percent,
            short_stop_loss_percent=request.short_stop_loss_percent,
            short_take_profit_percent=request.short_take_profit_percent,
            short_max_positions=request.short_max_positions,
            short_max_btc_trend=request.short_max_btc_trend,
            short_max_eth_trend=request.short_max_eth_trend,
            enable_short=request.enable_short
        )
        
        candles_data = {}
        
        tasks = []
        for coin in request.coins:
            inst_id = f"{coin}-USDT"
            tasks.append(fetch_historical_candles(inst_id, request.bar, start_ts, end_ts))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, coin in enumerate(request.coins):
            if isinstance(results[i], Exception):
                print(f"Error fetching {coin}: {results[i]}")
                continue
            if results[i] and len(results[i]) >= 50:
                candles_data[coin] = results[i]
        
        if not candles_data:
            return BacktestResponse(
                success=False,
                message="无法获取足够的历史数据，请检查币种名称和日期范围"
            )
        
        btc_candles = None
        eth_candles = None
        
        if "BTC" in candles_data:
            btc_candles = candles_data["BTC"]
        else:
            btc_result = await fetch_historical_candles("BTC-USDT", request.bar, start_ts, end_ts)
            if btc_result and len(btc_result) >= 50:
                btc_candles = btc_result
        
        if "ETH" in candles_data:
            eth_candles = candles_data["ETH"]
        else:
            eth_result = await fetch_historical_candles("ETH-USDT", request.bar, start_ts, end_ts)
            if eth_result and len(eth_result) >= 50:
                eth_candles = eth_result
        
        result = await run_backtest(
            candles_data=candles_data,
            config=config,
            initial_balance=request.initial_balance,
            position_size=request.position_size,
            leverage=request.leverage,
            enable_short=request.enable_short,
            btc_candles=btc_candles,
            eth_candles=eth_candles
        )
        
        return BacktestResponse(
            success=True,
            message=f"回测完成，共{result.total_trades}笔交易",
            result={
                "start_time": result.start_time,
                "end_time": result.end_time,
                "initial_balance": result.initial_balance,
                "final_balance": round(result.final_balance, 2),
                "total_pnl": round(result.total_pnl, 2),
                "total_pnl_percent": round(result.total_pnl_percent, 2),
                "total_trades": result.total_trades,
                "win_trades": result.win_trades,
                "loss_trades": result.loss_trades,
                "win_rate": round(result.win_rate, 2),
                "max_drawdown": round(result.max_drawdown, 2),
                "max_drawdown_percent": round(result.max_drawdown_percent, 2),
                "sharpe_ratio": round(result.sharpe_ratio, 3),
                "profit_factor": round(result.profit_factor, 3),
                "avg_profit": round(result.avg_profit, 2),
                "avg_loss": round(result.avg_loss, 2),
                "max_consecutive_wins": result.max_consecutive_wins,
                "max_consecutive_losses": result.max_consecutive_losses,
                "trades": result.trades[:100],
                "daily_pnl": result.daily_pnl
            }
        )
        
    except ValueError as e:
        return BacktestResponse(
            success=False,
            message=f"日期格式错误: {str(e)}"
        )
    except Exception as e:
        return BacktestResponse(
            success=False,
            message=f"回测执行失败: {str(e)}"
        )


@router.get("/coins")
async def get_popular_coins():
    """获取热门币种列表"""
    return {
        "coins": [
            "BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "DOT", "LINK", "MATIC",
            "UNI", "ATOM", "LTC", "ETC", "FIL", "ARB", "OP", "APT", "SUI", "SEI",
            "TIA", "INJ", "NEAR", "ICP", "VET", "HBAR", "FTM", "SAND", "MANA", "AAVE"
        ]
    }


@router.get("/default-config")
async def get_default_config():
    """获取默认回测配置"""
    return {
        "long_min_bullish_score": 7,
        "long_bullish_gap": 2,
        "long_min_trend_score": 6,
        "long_max_trend_score": 10,
        "long_rsi_min": 30.0,
        "long_rsi_max": 70.0,
        "long_min_volume_ratio": 0.8,
        "long_max_pullback_percent": 8.0,
        "long_min_pullback_percent": -5.0,
        "long_stop_loss_percent": -1.5,
        "long_take_profit_percent": 3.0,
        "long_max_positions": 3,
        "short_min_bearish_score": 7,
        "short_min_trend_score": 3,
        "short_max_trend_score": 5,
        "short_rsi_min": 70.0,
        "short_rsi_max": 85.0,
        "short_min_volume_ratio": 1.2,
        "short_min_pullback_percent": 3.0,
        "short_max_pullback_percent": 10.0,
        "short_stop_loss_percent": 1.5,
        "short_take_profit_percent": 3.0,
        "short_max_positions": 3,
        "short_max_btc_trend": 5,
        "short_max_eth_trend": 5
    }
