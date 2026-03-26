from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set, List
import asyncio
import json
from datetime import datetime
from loguru import logger

from app.core.okx_client import OKXClient
from app.strategies import (
    get_current_time_zone,
    get_time_zone_config,
    sparrow_config
)
from app.services.simulation_manager import simulation_manager

router = APIRouter(tags=["websocket"])

# 全局OKX客户端实例
_okx_client: OKXClient | None = None

async def get_okx_client() -> OKXClient:
    global _okx_client
    if _okx_client is None or (_okx_client._client and _okx_client._client.is_closed):
        _okx_client = OKXClient()
    return _okx_client


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.connection_subscriptions: Dict[WebSocket, Set[str]] = {}
        self.last_broadcast_data: Dict[str, dict] = {}
        self.broadcast_lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_subscriptions[websocket] = {"account", "market", "timezone"}
        logger.info(f"WebSocket connected, total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        self.connection_subscriptions.pop(websocket, None)
        logger.info(f"WebSocket disconnected, total: {len(self.active_connections)}")

    async def subscribe(self, websocket: WebSocket, channels: List[str]):
        """订阅特定频道"""
        if websocket in self.connection_subscriptions:
            valid_channels = [ch for ch in channels if ch in ["account", "market", "timezone"]]
            self.connection_subscriptions[websocket].update(valid_channels)
            logger.info(f"WebSocket subscribed to: {valid_channels}")

    async def unsubscribe(self, websocket: WebSocket, channels: List[str]):
        """取消订阅特定频道"""
        if websocket in self.connection_subscriptions:
            for ch in channels:
                self.connection_subscriptions[websocket].discard(ch)
            logger.info(f"WebSocket unsubscribed from: {channels}")

    async def broadcast(self, message: dict, channel: str = None):
        """增量更新：只向订阅了该频道的连接发送数据"""
        async with self.broadcast_lock:
            # 缓存最新数据用于增量更新判断
            msg_type = message.get("type", "")
            if msg_type:
                self.last_broadcast_data[msg_type] = message

            for connection in self.active_connections:
                try:
                    # 如果指定了频道，检查连接是否订阅了该频道
                    if channel and connection in self.connection_subscriptions:
                        if channel not in self.connection_subscriptions[connection]:
                            continue

                    # 如果没有指定频道，发送给所有连接
                    await connection.send_json(message)
                except Exception as e:
                    err_msg = str(e).lower()
                    if "asgi" in err_msg or "close" in err_msg or "completed" in err_msg:
                        self.disconnect(connection)
                    else:
                        logger.error(f"Broadcast error: {e}")


manager = ConnectionManager()


async def fetch_account_data():
    client = await get_okx_client()
    result = await client.get_balance()
    
    if result.get("code") != "0":
        return None
    
    data = result.get("data", [{}])[0]
    details = data.get("details", [])
    
    total_equity = float(data.get("totalEq", 0))
    available_usdt = 0.0
    positions = []
    
    for d in details:
        if d.get("ccy") == "USDT":
            available_usdt = float(d.get("availBal", 0))
        if float(d.get("eqUsd", 0)) > 0.5 and d.get("ccy") != "USDT":
            positions.append({
                "coin": d.get("ccy"),
                "amount": float(d.get("spotBal", 0) or d.get("eq", 0)),
                "value": float(d.get("eqUsd", 0)),
                "avg_price": float(d.get("openAvgPx", 0) or d.get("accAvgPx", 0)),
                "is_simulation": False
            })
    
    sim_positions = simulation_manager.get_positions()
    for pos in sim_positions:
        positions.append({
            "coin": pos["coin"],
            "amount": pos["amount"],
            "value": pos["usdt_value"],
            "avg_price": pos["entry_price"],
            "is_simulation": True,
            "is_short": False,
            "leverage": pos.get("leverage", 1.0),
            "is_swap": pos.get("is_swap", False)
        })
    
    # 获取模拟空单持仓
    sim_short_positions = simulation_manager.get_short_positions()
    for pos in sim_short_positions:
        positions.append({
            "coin": pos["coin"],
            "amount": pos["amount"],
            "value": pos["usdt_value"],
            "avg_price": pos["entry_price"],
            "is_simulation": True,
            "is_short": True,
            "leverage": pos.get("leverage", 1.0),
            "is_swap": pos.get("is_swap", False)
        })
    
    return {
        "type": "account",
        "data": {
            "total_equity": total_equity,
            "available_usdt": available_usdt,
            "positions": positions,
            "timestamp": datetime.now().isoformat()
        }
    }


async def fetch_market_data():
    client = await get_okx_client()
    btc_ticker = await client.get_ticker("BTC-USDT")
    eth_ticker = await client.get_ticker("ETH-USDT")
    
    btc_data = btc_ticker.get("data", [{}])[0] if btc_ticker.get("data") else {}
    eth_data = eth_ticker.get("data", [{}])[0] if eth_ticker.get("data") else {}
    
    btc_price = float(btc_data.get("last", 0))
    eth_price = float(eth_data.get("last", 0))
    
    btc_open = float(btc_data.get("open24h", btc_price))
    eth_open = float(eth_data.get("open24h", eth_price))
    
    btc_change = ((btc_price - btc_open) / btc_open * 100) if btc_open > 0 else 0
    eth_change = ((eth_price - eth_open) / eth_open * 100) if eth_open > 0 else 0
    
    return {
        "type": "market",
        "data": {
            "btc": {
                "price": btc_price,
                "change_24h": btc_change
            },
            "eth": {
                "price": eth_price,
                "change_24h": eth_change
            },
            "timestamp": datetime.now().isoformat()
        }
    }


async def fetch_time_zone_info():
    current_tz = get_current_time_zone()
    tz_config = get_time_zone_config(sparrow_config)
    
    return {
        "type": "timezone",
        "data": {
            "current_time_zone": current_tz,
            "intensity": tz_config.intensity,
            "position_size": tz_config.position_size,
            "hold_time": tz_config.hold_time,
            "daily_quota": tz_config.daily_quota,
            "timestamp": datetime.now().isoformat()
        }
    }


async def data_stream(websocket: WebSocket):
    try:
        while True:
            try:
                # 并行获取所有数据
                account_task = asyncio.create_task(fetch_account_data())
                market_task = asyncio.create_task(fetch_market_data())
                tz_task = asyncio.create_task(fetch_time_zone_info())

                account_data, market_data, tz_info = await asyncio.gather(
                    account_task, market_task, tz_task,
                    return_exceptions=True
                )

                # 按频道发送数据
                if account_data and not isinstance(account_data, Exception):
                    await manager.broadcast(account_data, "account")

                if market_data and not isinstance(market_data, Exception):
                    await manager.broadcast(market_data, "market")

                if tz_info and not isinstance(tz_info, Exception):
                    await manager.broadcast(tz_info, "timezone")

                await asyncio.sleep(5)
            except Exception as e:
                err_msg = str(e).lower()
                if "asgi" in err_msg or "send" in err_msg or "close" in err_msg or "completed" in err_msg:
                    break
                logger.error(f"Data stream error: {e}")
                await asyncio.sleep(5)
    except Exception as e:
        logger.error(f"Data stream ended: {e}")


@router.websocket("/ws/trading")
async def websocket_trading(websocket: WebSocket):
    await manager.connect(websocket)
    stream_task = None

    try:
        # 启动数据流
        stream_task = asyncio.create_task(data_stream(websocket))

        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)

                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

                elif message.get("type") == "subscribe":
                    channels = message.get("channels", [])
                    if isinstance(channels, list):
                        await manager.subscribe(websocket, channels)
                    await websocket.send_json({
                        "type": "subscribed",
                        "channels": channels
                    })

                elif message.get("type") == "unsubscribe":
                    channels = message.get("channels", [])
                    if isinstance(channels, list):
                        await manager.unsubscribe(websocket, channels)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "channels": channels
                    })

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {data}")

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if stream_task:
            stream_task.cancel()
            try:
                await stream_task
            except asyncio.CancelledError:
                pass
        manager.disconnect(websocket)
