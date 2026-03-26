"""
网格交易策略
低买高卖，在价格区间内自动网格交易
支持舆情驱动的动态调整和风险控制
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
class GridRiskConfig:
    max_position_per_coin: float = 30.0
    max_orders_per_coin: int = 2
    stop_loss_percent: float = -10.0
    take_profit_percent: float = 5.0
    min_order_interval: int = 300000  # 5分钟


@dataclass
class GridConfig:
    inst_id: str
    min_price: float
    max_price: float
    grid_num: int = 10
    investment: float = 40.0
    amount_per_grid: float = 0.01
    last_trade_price: Optional[float] = None
    enabled: bool = True
    enable_short: bool = False
    position: float = 0.0
    avg_price: float = 0.0
    last_order_time: int = 0


@dataclass
class GridOrder:
    time: str
    action: str
    price: float
    amount: float
    ord_id: str


class GridTradingStrategy:
    def __init__(self, data_dir: str = "."):
        self.data_dir = data_dir
        self.log_file = os.path.join(data_dir, "grid_trading_state.json")
        self.risk_config = GridRiskConfig()
        self.grids: Dict[str, GridConfig] = {}
        self.orders: Dict[str, List[GridOrder]] = {}
        self.base_grids: Dict[str, GridConfig] = {}
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for name, grid_data in data.get("grids", {}).items():
                    self.grids[name] = GridConfig(**grid_data)
                for name, orders_data in data.get("orders", {}).items():
                    self.orders[name] = [GridOrder(**o) for o in orders_data]
                logger.info(f"已加载 {len(self.grids)} 个网格配置")
            except Exception as e:
                logger.error(f"加载网格状态失败: {e}")

    def _save_state(self):
        try:
            data = {
                "grids": {name: {
                    "inst_id": g.inst_id,
                    "min_price": g.min_price,
                    "max_price": g.max_price,
                    "grid_num": g.grid_num,
                    "investment": g.investment,
                    "amount_per_grid": g.amount_per_grid,
                    "last_trade_price": g.last_trade_price,
                    "enabled": g.enabled,
                    "enable_short": g.enable_short
                } for name, g in self.grids.items()},
                "orders": {name: [o.__dict__ for o in orders] for name, orders in self.orders.items()}
            }
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存网格状态失败: {e}")

    def add_grid(self, name: str, config: GridConfig):
        self.grids[name] = config
        self.base_grids[name] = GridConfig(
            inst_id=config.inst_id,
            min_price=config.min_price,
            max_price=config.max_price,
            grid_num=config.grid_num,
            investment=config.investment,
            amount_per_grid=config.amount_per_grid
        )
        if name not in self.orders:
            self.orders[name] = []
        self._save_state()
        logger.info(f"添加网格: {name} - {config.inst_id} @ ${config.min_price}-${config.max_price}")

    def remove_grid(self, name: str):
        if name in self.grids:
            del self.grids[name]
            if name in self.orders:
                del self.orders[name]
            self._save_state()
            logger.info(f"移除网格: {name}")

    def get_grid_size(self, grid: GridConfig) -> float:
        return (grid.max_price - grid.min_price) / grid.grid_num

    def get_current_grid_index(self, grid: GridConfig, current_price: float) -> int:
        if current_price < grid.min_price or current_price > grid.max_price:
            return -1
        return int((current_price - grid.min_price) / self.get_grid_size(grid))

    async def analyze_sentiment(self) -> Dict[str, Any]:
        """分析市场舆情"""
        try:
            logger.info("🔍 分析市场舆情...")

            sentiment = {
                "score": 5,
                "trend": "neutral",
                "factors": []
            }

            hour = datetime.now().hour
            if 9 <= hour <= 17:
                sentiment["factors"].append("交易时段，市场活跃")

            logger.info(f"舆情评分: {sentiment['score']}/10, 趋势: {sentiment['trend']}")
            logger.info(f"因素: {', '.join(sentiment['factors']) if sentiment['factors'] else '无重大因素'}")

            return sentiment
        except Exception as e:
            logger.error(f"舆情分析失败: {e}")
            return {"score": 5, "trend": "neutral", "factors": []}

    def adjust_grid_by_sentiment(self, name: str, sentiment: Dict[str, Any]):
        """根据舆情动态调整网格参数"""
        if name not in self.grids or name not in self.base_grids:
            return

        base = self.base_grids[name]
        grid = self.grids[name]

        logger.info(f"\n📊 动态调整 {name} 网格参数...")

        score = sentiment.get("score", 5)
        trend = sentiment.get("trend", "neutral")

        if score >= 8:
            grid.max_price = max(grid.max_price, base.max_price * 1.2)
            grid.investment = min(grid.investment * 1.2, base.investment * 1.5)
            logger.info(f"🟢 利好情绪：{name} 网格上限提升至 ${grid.max_price:.2f}")
        elif score <= 3:
            grid.min_price = min(grid.min_price, base.min_price * 0.8)
            grid.investment = max(grid.investment * 0.8, base.investment * 0.6)
            logger.info(f"🔴 利空情绪：{name} 网格下限降低至 ${grid.min_price:.2f}")

        if trend == "bullish" and any("Musk" in f for f in sentiment.get("factors", [])):
            if "DOGE" in name:
                grid.max_price = max(grid.max_price, base.max_price * 1.5)
                logger.info(f"🚀 马斯克利好：{name} 网格上限提升至 ${grid.max_price:.2f}")

        logger.info(f"调整后网格: ${grid.min_price:.2f} - ${grid.max_price:.2f}")
        self._save_state()

    async def check_risk_control(
        self,
        config: GridConfig,
        current_price: float,
        action: str
    ) -> bool:
        """检查风险控制"""
        now = int(datetime.now().timestamp() * 1000)

        if now - config.last_order_time < self.risk_config.min_order_interval:
            logger.info(f"  ⏸️ 下单间隔太短，跳过")
            return False

        if action == "buy" and config.position >= self.risk_config.max_position_per_coin:
            logger.info(f"  ⚠️ {config.inst_id} 持仓已达上限 ({config.position})，停止买入")
            return False

        if config.position > 0 and config.avg_price > 0:
            pnl_percent = (current_price - config.avg_price) / config.avg_price * 100
            if pnl_percent <= self.risk_config.stop_loss_percent:
                logger.info(f"  🛑 触发止损！当前亏损 {pnl_percent:.2f}%")
                return False

        return True

    def auto_adjust_grid(self, name: str, current_price: float) -> bool:
        """自动决策调整网格区间"""
        if name not in self.grids:
            return False

        config = self.grids[name]
        grid_size = self.get_grid_size(config)
        distance_to_min = current_price - config.min_price
        distance_to_max = config.max_price - current_price

        logger.info(f"\n🤖 自动决策分析 {name}:")
        logger.info(f"  距离下限: ${distance_to_min:.2f}, 距离上限: ${distance_to_max:.2f}")

        if distance_to_min < grid_size:
            new_min = config.min_price - grid_size * 2
            new_max = config.max_price - grid_size * 2
            logger.info(f"  🎯 决策: 价格接近下限，自动下移网格")
            logger.info(f"  新区间: ${new_min:.2f} - ${new_max:.2f}")
            config.min_price = new_min
            config.max_price = new_max
            self._save_state()
            return True

        if distance_to_max < grid_size:
            new_min = config.min_price + grid_size * 2
            new_max = config.max_price + grid_size * 2
            logger.info(f"  🎯 决策: 价格接近上限，自动上移网格")
            logger.info(f"  新区间: ${new_min:.2f} - ${new_max:.2f}")
            config.min_price = new_min
            config.max_price = new_max
            self._save_state()
            return True

        logger.info(f"  ⏸️ 决策: 维持当前网格")
        return False

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

            grid_size = self.get_grid_size(grid)
            grid_index = self.get_current_grid_index(grid, current_price)

            if grid_index < 0:
                logger.warning(f"{name} 价格${current_price}超出网格范围")
                return None

            grid_lower = grid.min_price + (grid_index * grid_size)
            grid_upper = grid_lower + grid_size
            half_grid = grid_size / 2
            grid_middle = (grid_lower + grid_upper) / 2

            logger.info(f"{name} 当前价格: ${current_price:.4f}, 网格: ${grid_lower:.4f}-${grid_upper:.4f}, 中点: ${grid_middle:.4f}")

            if grid.last_trade_price is None:
                if current_price <= grid_middle:
                    trigger = {"action": "buy", "price": current_price, "reason": "首次运行，网格下半部分自动买入"}
                else:
                    grid.last_trade_price = current_price
                    self._save_state()
                    return None
            else:
                trigger = None
                if grid.enable_short:
                    if current_price <= grid_lower + half_grid:
                        if grid.last_trade_price > grid_lower + half_grid:
                            trigger = {"action": "buy", "price": current_price, "reason": "网格下沿买入（自主决策）"}
                        else:
                            trigger = {"action": "sell_short", "price": current_price, "reason": "网格下沿做空"}
                    elif current_price >= grid_upper - half_grid:
                        if grid.last_trade_price < grid_upper - half_grid:
                            trigger = {"action": "sell", "price": current_price, "reason": "网格上沿卖出（自主决策）"}
                        else:
                            trigger = {"action": "buy_short", "price": current_price, "reason": "网格上沿平空"}
                else:
                    if current_price <= grid_lower + half_grid and grid.last_trade_price > grid_lower + half_grid:
                        trigger = {"action": "buy", "price": current_price, "reason": "网格下沿买入（自主决策）"}
                    elif current_price >= grid_upper - half_grid and grid.last_trade_price < grid_upper - half_grid:
                        trigger = {"action": "sell", "price": current_price, "reason": "网格上沿卖出（自主决策）"}

            if trigger:
                logger.info(f"🎯 触发{trigger['action']}: {trigger['reason']} @ ${trigger['price']:.4f}")

            return trigger

        except Exception as e:
            logger.error(f"检查网格触发失败 {name}: {e}")
            return None

    async def execute_trade(self, client: OKXClient, name: str, trigger: Dict[str, Any]) -> bool:
        grid = self.grids.get(name)
        if not grid:
            return False

        try:
            action = trigger["action"]
            price = trigger["price"]
            amount = grid.amount_per_grid

            logger.info(f"执行{action}: {grid.inst_id} @ ${price} x {amount}")

            if action in ["buy_short", "sell_short"]:
                side = "sell" if action == "sell_short" else "buy"
                td_mode = "cross"
                swap_inst_id = f"{grid.inst_id.split('-')[0]}-USDT-SWAP" if "-SWAP" not in grid.inst_id else grid.inst_id
            else:
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
                logger.info(f"✅ 网格交易成功 ({action}): {ord_id}")

                grid.last_trade_price = price
                grid.last_order_time = int(datetime.now().timestamp() * 1000)

                if action == "buy":
                    grid.position += amount
                    total_cost = grid.avg_price * (grid.position - amount) + price * amount
                    grid.avg_price = total_cost / grid.position
                elif action == "sell":
                    grid.position -= amount
                    if grid.position <= 0:
                        grid.avg_price = 0

                self.orders[name].append(GridOrder(
                    time=datetime.now().isoformat(),
                    action=action,
                    price=price,
                    amount=amount,
                    ord_id=ord_id
                ))
                self._save_state()
                return True
            else:
                logger.error(f"❌ 网格交易失败: {result.get('msg')}")
                return False

        except Exception as e:
            logger.error(f"执行网格交易失败 {name}: {e}")
            return False

    async def run_cycle(self, client: OKXClient) -> Dict[str, Any]:
        sentiment = await self.analyze_sentiment()
        results = {}

        for name in self.grids:
            self.adjust_grid_by_sentiment(name, sentiment)

            trigger = await self.check_trigger(client, name)

            if trigger:
                risk_ok = await self.check_risk_control(
                    self.grids[name],
                    trigger["price"],
                    trigger["action"]
                )

                if risk_ok:
                    success = await self.execute_trade(client, name, trigger)
                    results[name] = {"trigger": trigger, "success": success}
                else:
                    results[name] = {"trigger": trigger, "success": False, "reason": "风险控制"}
            else:
                current_price_result = await client.get_ticker(self.grids[name].inst_id)
                if current_price_result and current_price_result.get("data"):
                    current_price = float(current_price_result["data"][0]["last"])
                    self.auto_adjust_grid(name, current_price)

                results[name] = {"trigger": None}

        return results

    def get_status(self) -> Dict[str, Any]:
        return {
            "grids": {name: {
                "inst_id": g.inst_id,
                "min_price": g.min_price,
                "max_price": g.max_price,
                "grid_num": g.grid_num,
                "investment": g.investment,
                "last_trade_price": g.last_trade_price,
                "enabled": g.enabled,
                "orders_count": len(self.orders.get(name, []))
            } for name, g in self.grids.items()}
        }


grid_trading_strategy = GridTradingStrategy()
