"""
趋势追踪交易策略
顺势而为，截断亏损，让利润奔跑
"""
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from loguru import logger
import json
import os

from app.core.okx_client import OKXClient
from app.strategies.indicators import calculate_rsi, calculate_macd
from app.services.position_manager import position_manager

BEIJING_TZ = timezone(timedelta(hours=8))


@dataclass
class TrendStrategyConfig:
    trade_size: float = 10.0
    max_positions: int = 2
    max_total_position: float = 60.0
    entry_lookback: int = 20
    min_rsi: float = 50.0
    max_rsi: float = 80.0
    volume_multiplier: float = 1.5
    trailing_stop: bool = True
    trailing_stop_percent: float = 3.0
    max_daily_trades: int = 5
    max_daily_loss: float = 20.0
    cooldown_minutes: int = 30
    watch_list: List[str] = None

    def __post_init__(self):
        if self.watch_list is None:
            self.watch_list = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "DOGE-USDT", "XRP-USDT"]
        self._sync_from_position_manager()

    def _sync_from_position_manager(self):
        pm_config = position_manager.get_config()
        self._stop_loss_percent = pm_config.get("stop_loss_percent", -2.0)
        self._take_profit_percent = pm_config.get("take_profit_percent", 5.0)

    @property
    def stop_loss_percent(self) -> float:
        return self._stop_loss_percent

    @property
    def take_profit_percent(self) -> float:
        return self._take_profit_percent


@dataclass
class TrendPosition:
    coin: str
    entry_price: float
    amount: float
    stop_loss: float
    take_profit: float
    trailing_stop_price: float
    entry_time: str


@dataclass
class TrendTrade:
    coin: str
    action: str
    price: float
    amount: float
    pnl: float
    time: str


class TrendTradingStrategy:
    def __init__(self, data_dir: str = "."):
        self.data_dir = data_dir
        self.log_file = os.path.join(data_dir, "trend_trading_state.json")
        self.config = TrendStrategyConfig()
        self.positions: Dict[str, TrendPosition] = {}
        self.trades: List[TrendTrade] = []
        self.daily_stats = {
            "date": datetime.now(BEIJING_TZ).strftime("%Y-%m-%d"),
            "trade_count": 0,
            "loss": 0.0
        }
        self.last_buy_time: Dict[str, datetime] = {}
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.config = TrendStrategyConfig(**data.get("config", {}))
                self.positions = {k: TrendPosition(**v) for k, v in data.get("positions", {}).items()}
                self.trades = [TrendTrade(**t) for t in data.get("trades", [])[-100:]]
                self.daily_stats = data.get("daily_stats", self.daily_stats)
                self.last_buy_time = {k: datetime.fromisoformat(v) for k, v in data.get("last_buy_time", {}).items()}
                logger.info(f"已加载趋势交易状态: {len(self.positions)}持仓, {len(self.trades)}交易记录")
            except Exception as e:
                logger.error(f"加载趋势交易状态失败: {e}")

    def _save_state(self):
        try:
            data = {
                "config": self.config.__dict__,
                "positions": {k: v.__dict__ for k, v in self.positions.items()},
                "trades": [t.__dict__ for t in self.trades[-100:]],
                "daily_stats": self.daily_stats,
                "last_buy_time": {k: v.isoformat() for k, v in self.last_buy_time.items()}
            }
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存趋势交易状态失败: {e}")

    def _reset_daily_stats_if_needed(self):
        today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
        if self.daily_stats["date"] != today:
            self.daily_stats = {
                "date": today,
                "trade_count": 0,
                "loss": 0.0
            }

    async def get_candles(self, client: OKXClient, inst_id: str, bar: str = "1H", limit: int = 30) -> Optional[List[Dict]]:
        try:
            result = await client.get_candles(inst_id, bar=bar, limit=limit)
            if result.get("data"):
                candles = []
                for c in result["data"]:
                    candles.append({
                        "timestamp": int(c[0]),
                        "open": float(c[1]),
                        "high": float(c[2]),
                        "low": float(c[3]),
                        "close": float(c[4]),
                        "volume": float(c[5])
                    })
                return list(reversed(candles))
            return None
        except Exception as e:
            logger.error(f"获取K线失败 {inst_id}: {e}")
            return None

    def calculate_indicators(self, candles: List[Dict]) -> Optional[Dict[str, Any]]:
        if not candles or len(candles) < 20:
            return None

        closes = [c["close"] for c in candles]
        volumes = [c["volume"] for c in candles]
        current = closes[-1]
        current_volume = volumes[-1]

        high_20 = max(candles[-20:])["high"]

        avg_volume_20 = sum(volumes[-20:]) / 20

        rsi = calculate_rsi(closes, 14)
        macd = calculate_macd(closes)

        return {
            "current": current,
            "high_20": high_20,
            "rsi": rsi,
            "macd": macd,
            "current_volume": current_volume,
            "avg_volume_20": avg_volume_20,
            "volume_ratio": current_volume / avg_volume_20 if avg_volume_20 > 0 else 1,
            "trend": "bullish" if current > high_20 * 0.98 else "bearish"
        }

    async def check_entry_signal(self, client: OKXClient, inst_id: str) -> Optional[Dict[str, Any]]:
        candles = await self.get_candles(client, inst_id, bar="1H", limit=30)
        if not candles:
            return None

        indicators = self.calculate_indicators(candles)
        if not indicators:
            return None

        current = indicators["current"]
        rsi = indicators["rsi"]
        volume_ratio = indicators["volume_ratio"]
        trend = indicators["trend"]
        high_20 = indicators["high_20"]

        if trend == "bullish" and rsi < self.config.max_rsi and rsi > self.config.min_rsi:
            if volume_ratio >= self.config.volume_multiplier:
                if current > high_20 * 0.98:
                    return {
                        "signal": "buy",
                        "price": current,
                        "rsi": rsi,
                        "volume_ratio": volume_ratio,
                        "reason": f"突破{self.config.entry_lookback}周期高点，RSI={rsi:.1f}，成交量放量{volume_ratio:.1f}倍"
                    }

        return None

    def check_exit_signal(self, position: TrendPosition, current_price: float, indicators: Dict) -> Optional[Dict[str, Any]]:
        pnl_percent = (current_price - position.entry_price) / position.entry_price * 100

        if current_price <= position.stop_loss:
            return {"action": "sell", "reason": f"触发固定止损 @{position.stop_loss:.4f} ({pnl_percent:.2f}%)"}

        if self.config.trailing_stop and pnl_percent >= 3:
            new_trailing = current_price * (1 - self.config.trailing_stop_percent / 100)
            if new_trailing > position.trailing_stop_price:
                position.trailing_stop_price = new_trailing
                logger.info(f"更新移动止损: ${new_trailing:.4f} (回撤{self.config.trailing_stop_percent}%)")

            if current_price <= position.trailing_stop_price:
                drawdown = (current_price - position.entry_price) / position.entry_price * 100
                return {
                    "action": "sell",
                    "reason": f"触发移动止损 @{position.trailing_stop_price:.4f} (从高点回撤{drawdown:.2f}%)"
                }

        if current_price >= position.take_profit:
            return {"action": "sell", "reason": f"触发固定止盈 @{position.take_profit:.4f} ({pnl_percent:.2f}%)"}

        return None

    async def execute_trade(self, client: OKXClient, inst_id: str, action: str, price: float, amount: float) -> bool:
        try:
            side = "buy" if action == "buy" else "sell"
            result = await client.place_order(
                inst_id=inst_id,
                side=side,
                ord_type="market",
                sz=str(amount)
            )

            if result.get("code") == "0":
                ord_id = result["data"][0]["ordId"]
                logger.info(f"✅ 趋势交易{'买入' if action == 'buy' else '卖出'}成功: {ord_id}")
                return True
            else:
                logger.error(f"❌ 趋势交易失败: {result.get('msg')}")
                return False
        except Exception as e:
            logger.error(f"执行趋势交易失败: {e}")
            return False

    async def run_cycle(self, client: OKXClient) -> Dict[str, Any]:
        self._reset_daily_stats_if_needed()

        results = {"signals": [], "exits": [], "errors": []}

        for inst_id in self.config.watch_list:
            try:
                if inst_id in self.positions:
                    position = self.positions[inst_id]
                    candles = await self.get_candles(client, inst_id)
                    if candles:
                        indicators = self.calculate_indicators(candles)
                        current_price = indicators["current"]
                        exit_signal = self.check_exit_signal(position, current_price, indicators)

                        if exit_signal:
                            amount = position.amount
                            success = await self.execute_trade(client, inst_id, "sell", current_price, amount)
                            if success:
                                pnl = (current_price - position.entry_price) * amount
                                self.trades.append(TrendTrade(
                                    coin=inst_id,
                                    action="sell",
                                    price=current_price,
                                    amount=amount,
                                    pnl=pnl,
                                    time=datetime.now().isoformat()
                                ))
                                if pnl < 0:
                                    self.daily_stats["loss"] += abs(pnl)
                                del self.positions[inst_id]
                                results["exits"].append({"coin": inst_id, **exit_signal, "pnl": pnl})
                else:
                    if self.daily_stats["trade_count"] >= self.config.max_daily_trades:
                        continue

                    if self.daily_stats["loss"] >= self.config.max_daily_loss:
                        logger.warning("每日亏损已达上限，停止开仓")
                        continue

                    last_buy = self.last_buy_time.get(inst_id)
                    if last_buy and (datetime.now() - last_buy).total_seconds() < self.config.cooldown_minutes * 60:
                        continue

                    signal = await self.check_entry_signal(client, inst_id)
                    if signal:
                        amount = self.config.trade_size / signal["price"]
                        success = await self.execute_trade(client, inst_id, "buy", signal["price"], amount)
                        if success:
                            stop_loss = signal["price"] * (1 + self.config.stop_loss_percent / 100)
                            take_profit = signal["price"] * (1 + self.config.take_profit_percent / 100)
                            trailing_stop = signal["price"] * (1 - self.config.trailing_stop_percent / 100)

                            self.positions[inst_id] = TrendPosition(
                                coin=inst_id,
                                entry_price=signal["price"],
                                amount=amount,
                                stop_loss=stop_loss,
                                take_profit=take_profit,
                                trailing_stop_price=trailing_stop,
                                entry_time=datetime.now().isoformat()
                            )
                            self.last_buy_time[inst_id] = datetime.now()
                            self.daily_stats["trade_count"] += 1
                            results["signals"].append({"coin": inst_id, **signal})

            except Exception as e:
                logger.error(f"处理 {inst_id} 时出错: {e}")
                results["errors"].append({"coin": inst_id, "error": str(e)})

        self._save_state()
        return results

    def get_status(self) -> Dict[str, Any]:
        return {
            "positions": {k: v.__dict__ for k, v in self.positions.items()},
            "daily_stats": self.daily_stats,
            "config": self.config.__dict__,
            "trade_count": len(self.trades)
        }


trend_trading_strategy = TrendTradingStrategy()
