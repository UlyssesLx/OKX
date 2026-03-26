"""
智能网格交易策略
根据市场舆情动态调整网格参数，带风险控制
"""
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
import json
import os

from app.core.okx_client import OKXClient


@dataclass
class SmartGridConfig:
    inst_id: str
    min_price: float
    max_price: float
    grid_num: int = 20
    investment: float = 40.0
    amount_per_grid: float = 0.01
    last_trade_price: Optional[float] = None
    last_order_time: Optional[float] = None
    enabled: bool = True
    position: float = 0.0
    avg_price: float = 0.0
    short_position: float = 0.0  # 空单持仓
    short_avg_price: float = 0.0  # 空单均价


@dataclass
class SmartGridSettings:
    max_position_per_coin: float = 30.0
    max_orders_per_coin: int = 2
    stop_loss_percent: float = -10.0
    take_profit_percent: float = 5.0
    min_order_interval: int = 300000


class SmartGridStrategy:
    def __init__(self, data_dir: str = "."):
        self.data_dir = data_dir
        self.log_file = os.path.join(data_dir, "smart_grid_state.json")
        self.settings = SmartGridSettings()
        self.grids: Dict[str, SmartGridConfig] = {}
        self.orders: Dict[str, List[Dict]] = {}
        self.sentiment_score: float = 5.0
        self.sentiment_trend: str = "neutral"
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.settings = SmartGridSettings(**data.get("settings", {}))
                self.grids = {k: SmartGridConfig(**v) for k, v in data.get("grids", {}).items()}
                self.orders = data.get("orders", {})
                self.sentiment_score = data.get("sentiment_score", 5.0)
                self.sentiment_trend = data.get("sentiment_trend", "neutral")
                logger.info(f"已加载智能网格: {len(self.grids)} 个配置")
            except Exception as e:
                logger.error(f"加载智能网格状态失败: {e}")

    def _save_state(self):
        try:
            data = {
                "settings": self.settings.__dict__,
                "grids": {
                k: {
                    **v.__dict__,
                    "grid_size": self.get_grid_size(v)
                }
                for k, v in self.grids.items()
            },
                "orders": self.orders,
                "sentiment_score": self.sentiment_score,
                "sentiment_trend": self.sentiment_trend
            }
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存智能网格状态失败: {e}")

    def add_grid(self, name: str, config: SmartGridConfig):
        self.grids[name] = config
        if name not in self.orders:
            self.orders[name] = []
        self._save_state()
        logger.info(f"添加智能网格: {name}")

    def remove_grid(self, name: str):
        if name in self.grids:
            del self.grids[name]
            if name in self.orders:
                del self.orders[name]
            self._save_state()
            logger.info(f"移除智能网格: {name}")

    def update_sentiment(self, score: float, trend: str):
        self.sentiment_score = score
        self.sentiment_trend = trend
        self._adjust_grids_by_sentiment()
        self._save_state()

    def _adjust_grids_by_sentiment(self):
        logger.info(f"\n📊 动态调整智能网格 (舆情: {self.sentiment_score}/10, {self.sentiment_trend})")

        for name, grid in self.grids.items():
            grid_range = grid.max_price - grid.min_price
            old_min, old_max = grid.min_price, grid.max_price

            if self.sentiment_score >= 8:
                if "ETH" in name:
                    grid.max_price = max(grid.max_price, 2400)
                    grid.investment = min(grid.investment * 1.2, 50)
                    logger.info(f"🟢 利好情绪: {name} 网格上限提升至 ${grid.max_price}")

            elif self.sentiment_score <= 3:
                if "ETH" in name:
                    grid.min_price = min(grid.min_price, 1600)
                    grid.investment = max(grid.investment * 0.8, 30)
                    logger.info(f"🔴 利空情绪: {name} 网格下限降低至 ${grid.min_price}")

            if self.sentiment_trend == "bullish" and "DOGE" in name:
                grid.max_price = max(grid.max_price, 0.12)
                logger.info(f"🚀 利好趋势: {name} 网格上限提升至 ${grid.max_price}")

    def get_grid_size(self, grid: SmartGridConfig) -> float:
        return (grid.max_price - grid.min_price) / grid.grid_num

    async def check_trigger(self, client: OKXClient, name: str) -> Optional[Dict[str, Any]]:
        grid = self.grids.get(name)
        if not grid or not grid.enabled:
            return None

        try:
            result = await client.get_ticker(grid.inst_id)
            if result.get("data") and len(result["data"]) > 0:
                current_price = float(result["data"][0]["last"])
            else:
                return None

            now = datetime.now().timestamp() * 1000

            if grid.last_order_time and (now - grid.last_order_time) < self.settings.min_order_interval:
                logger.debug(f"{name} 下单间隔太短，跳过")
                return None

            if grid.position >= self.settings.max_position_per_coin:
                logger.debug(f"{name} 持仓已达上限，停止买入")
                return None

            grid_size = self.get_grid_size(grid)
            grid_index = int((current_price - grid.min_price) / grid_size)
            grid_lower = grid.min_price + (grid_index * grid_size)
            grid_upper = grid_lower + grid_size
            half_grid = grid_size / 2

            if current_price < grid.min_price or current_price > grid.max_price:
                self._auto_adjust_grid(grid, current_price)
                return None

            trigger = None
            if grid.last_trade_price is None:
                grid.last_trade_price = current_price
                self._save_state()
                return None

            # 双向网格逻辑:做多+做空
            if current_price <= grid_lower + half_grid:
                # 价格触及下沿
                if grid.short_position > 0:
                    # 有空单,平空获利
                    pnl_percent = (grid.short_avg_price - current_price) / grid.short_avg_price * 100
                    trigger = {"action": "close_short", "price": current_price, "reason": f"网格下沿平空获利 ({pnl_percent:.2f}%)"}
                else:
                    # 无空单,开多
                    if grid.position > 0 and grid.avg_price > 0:
                        pnl_percent = (current_price - grid.avg_price) / grid.avg_price * 100
                        if pnl_percent <= self.settings.stop_loss_percent:
                            trigger = {"action": "stop_loss", "price": current_price, "reason": f"触发止损 ({pnl_percent:.2f}%)"}
                        elif pnl_percent >= self.settings.take_profit_percent:
                            trigger = {"action": "sell", "price": current_price, "reason": f"触发止盈 ({pnl_percent:.2f}%)"}
                        else:
                            trigger = {"action": "buy", "price": current_price, "reason": "网格下沿买入(加仓)"}
                    else:
                        trigger = {"action": "buy", "price": current_price, "reason": "网格下沿买入"}
            elif current_price >= grid_upper - half_grid:
                # 价格触及上沿
                if grid.position > 0:
                    # 有多单,平多获利
                    pnl_percent = (current_price - grid.avg_price) / grid.avg_price * 100
                    trigger = {"action": "sell", "price": current_price, "reason": f"网格上沿平多获利 ({pnl_percent:.2f}%)"}
                else:
                    # 无多单,开空
                    trigger = {"action": "open_short", "price": current_price, "reason": "网格上沿开空"}

            if trigger:
                logger.info(f"🎯 {name} 触发{trigger['action']}: ${current_price}")

            return trigger

        except Exception as e:
            logger.error(f"检查智能网格触发失败 {name}: {e}")
            return None

    def _auto_adjust_grid(self, grid: SmartGridConfig, current_price: float):
        grid_size = self.get_grid_size(grid)
        distance_to_min = current_price - grid.min_price
        distance_to_max = grid.max_price - current_price

        if distance_to_min < grid_size:
            new_min = grid.min_price - grid_size * 2
            new_max = grid.max_price - grid_size * 2
            logger.info(f"🎯 {grid.inst_id} 价格接近下限，自动下移网格: ${new_min:.2f} - ${new_max:.2f}")
            grid.min_price = new_min
            grid.max_price = new_max
        elif distance_to_max < grid_size:
            new_min = grid.min_price + grid_size * 2
            new_max = grid.max_price + grid_size * 2
            logger.info(f"🎯 {grid.inst_id} 价格接近上限，自动上移网格: ${new_min:.2f} - ${new_max:.2f}")
            grid.min_price = new_min
            grid.max_price = new_max

    async def execute_trade(self, client: OKXClient, name: str, trigger: Dict[str, Any]) -> bool:
        grid = self.grids.get(name)
        if not grid:
            return False

        try:
            action = trigger["action"]
            price = trigger["price"]
            amount = grid.amount_per_grid

            logger.info(f"执行{action}: {grid.inst_id} @ ${price} x {amount}")

            # 根据动作类型确定交易方向和模式
            if action in ["open_short", "close_short"]:
                # 做空交易,使用合约模式
                if action == "open_short":
                    side = "sell"
                else:  # close_short
                    side = "buy"
                td_mode = "cross"  # 全仓模式
                # 转换为合约交易对
                swap_inst_id = f"{grid.inst_id.split('-')[0]}-USDT-SWAP" if "-SWAP" not in grid.inst_id else grid.inst_id
            else:
                # 常规做多交易
                if action == "stop_loss":
                    action = "sell"
                side = "buy" if action == "buy" else "sell"
                td_mode = "cash"
                swap_inst_id = grid.inst_id

            result = await client.place_order(
                inst_id=swap_inst_id,
                side=side,
                ord_type="market",
                sz=str(amount),
                td_mode=td_mode
            )

            if result.get("code") == "0":
                ord_id = result["data"][0]["ordId"]
                grid.last_trade_price = price
                grid.last_order_time = datetime.now().timestamp() * 1000

                # 更新持仓
                original_action = trigger["action"]
                if original_action == "buy":
                    # 买入做多
                    total_cost = grid.position * grid.avg_price + amount * price
                    grid.position += amount
                    grid.avg_price = total_cost / grid.position if grid.position > 0 else 0
                elif original_action == "sell":
                    # 卖出平多
                    grid.position -= amount
                    if grid.position <= 0:
                        grid.position = 0
                        grid.avg_price = 0
                elif original_action == "open_short":
                    # 开空
                    total_value = grid.short_position * grid.short_avg_price + amount * price
                    grid.short_position += amount
                    grid.short_avg_price = total_value / grid.short_position if grid.short_position > 0 else 0
                elif original_action == "close_short":
                    # 平空
                    grid.short_position -= amount
                    if grid.short_position <= 0:
                        grid.short_position = 0
                        grid.short_avg_price = 0
                elif original_action == "stop_loss":
                    # 止损
                    grid.position -= amount
                    if grid.position <= 0:
                        grid.position = 0
                        grid.avg_price = 0

                self.orders[name].append({
                    "time": datetime.now().isoformat(),
                    "action": original_action,
                    "price": price,
                    "amount": amount,
                    "ord_id": ord_id
                })

                logger.info(f"✅ 智能网格交易成功: {original_action} {grid.inst_id} @ ${price}")
                self._save_state()
                return True
            else:
                logger.error(f"❌ 智能网格交易失败: {result.get('msg')}")
                return False

        except Exception as e:
            logger.error(f"执行智能网格交易失败 {name}: {e}")
            return False

    async def run_cycle(self, client: OKXClient) -> Dict[str, Any]:
        results = {}
        for name in self.grids:
            trigger = await self.check_trigger(client, name)
            if trigger:
                success = await self.execute_trade(client, name, trigger)
                results[name] = {"trigger": trigger, "success": success}
            else:
                results[name] = {"trigger": None}
        return results

    def get_status(self) -> Dict[str, Any]:
        return {
            "settings": self.settings.__dict__,
            "grids": {name: {
                **g.__dict__,
                "grid_size": self.get_grid_size(g)
            } for name, g in self.grids.items()},
            "sentiment_score": self.sentiment_score,
            "sentiment_trend": self.sentiment_trend
        }


smart_grid_strategy = SmartGridStrategy()
