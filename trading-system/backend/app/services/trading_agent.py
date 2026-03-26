"""
交易Agent - Trading Agent
专门负责执行买卖交易操作，接收交易信号并执行
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from loguru import logger
import json
import os

from app.core.okx_client import OKXClient

BEIJING_TZ = timezone(timedelta(hours=8))


@dataclass
class TradingSignal:
    time: str
    coin: str
    type: str  # "BUY" or "SELL"
    price: float
    reason: str
    urgency: str = "normal"  # "high" or "normal"


@dataclass
class TradeRecord:
    time: str
    coin: str
    action: str
    price: float
    amount: float
    reason: str
    order_id: str
    status: str


class TradingAgent:
    """交易Agent类"""

    def __init__(self, data_dir: str = "."):
        self.data_dir = data_dir
        self.config_file = os.path.join(data_dir, "trading_agent_config.json")
        self.signals_file = os.path.join(data_dir, "trading_signals.json")
        self.trades_file = os.path.join(data_dir, "trading_agent_trades.json")

        # 默认配置
        self.enabled = True
        self.auto_execute = False
        self.max_trade_amount = 25.0
        self.max_daily_trades = 10
        self.today_trade_count = 0
        self.last_trade_date = None

        self.signals: List[TradingSignal] = []
        self.trades: List[TradeRecord] = []

        self._load_config()
        self._load_signals()
        self._load_trades()

    def _load_config(self):
        """加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.enabled = config.get("enabled", True)
                    self.auto_execute = config.get("auto_execute", False)
                    self.max_trade_amount = config.get("max_trade_amount", 25.0)
                    self.max_daily_trades = config.get("max_daily_trades", 10)
                    self.today_trade_count = config.get("today_trade_count", 0)
                    self.last_trade_date = config.get("last_trade_date")
            except Exception as e:
                logger.error(f"加载交易Agent配置失败: {e}")

    def _save_config(self):
        """保存配置"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            config = {
                "enabled": self.enabled,
                "auto_execute": self.auto_execute,
                "max_trade_amount": self.max_trade_amount,
                "max_daily_trades": self.max_daily_trades,
                "today_trade_count": self.today_trade_count,
                "last_trade_date": self.last_trade_date
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存交易Agent配置失败: {e}")

    def _load_signals(self):
        """加载交易信号"""
        if os.path.exists(self.signals_file):
            try:
                with open(self.signals_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.signals = [TradingSignal(**s) for s in data]
            except Exception as e:
                logger.error(f"加载交易信号失败: {e}")

    def _save_signals(self):
        """保存交易信号"""
        try:
            os.makedirs(os.path.dirname(self.signals_file), exist_ok=True)
            data = [
                {
                    "time": s.time,
                    "coin": s.coin,
                    "type": s.type,
                    "price": s.price,
                    "reason": s.reason,
                    "urgency": s.urgency
                }
                for s in self.signals
            ]
            with open(self.signals_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存交易信号失败: {e}")

    def _load_trades(self):
        """加载交易记录"""
        if os.path.exists(self.trades_file):
            try:
                with open(self.trades_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.trades = [TradeRecord(**t) for t in data]
            except Exception as e:
                logger.error(f"加载交易记录失败: {e}")

    def _save_trades(self):
        """保存交易记录"""
        try:
            os.makedirs(os.path.dirname(self.trades_file), exist_ok=True)
            data = [
                {
                    "time": t.time,
                    "coin": t.coin,
                    "action": t.action,
                    "price": t.price,
                    "amount": t.amount,
                    "reason": t.reason,
                    "order_id": t.order_id,
                    "status": t.status
                }
                for t in self.trades[-100:]
            ]
            with open(self.trades_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存交易记录失败: {e}")

    def _reset_daily_count_if_needed(self):
        """重置每日计数（如果需要）"""
        today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
        if self.last_trade_date != today:
            self.today_trade_count = 0
            self.last_trade_date = today
            self._save_config()

    def get_today_trade_count(self) -> int:
        """获取今日交易次数"""
        self._reset_daily_count_if_needed()
        return self.today_trade_count

    def load_signals(self) -> List[Dict[str, Any]]:
        """加载交易信号"""
        self._load_signals()
        return [
            {
                "time": s.time,
                "coin": s.coin,
                "type": s.type,
                "price": s.price,
                "reason": s.reason,
                "urgency": s.urgency
            }
            for s in self.signals
        ]

    def add_signal(self, signal: Dict[str, Any]):
        """添加交易信号"""
        self.signals.append(TradingSignal(
            time=datetime.now().isoformat(),
            coin=signal.get("coin"),
            type=signal.get("type", "BUY"),
            price=signal.get("price", 0),
            reason=signal.get("reason", ""),
            urgency=signal.get("urgency", "normal")
        ))
        self._save_signals()
        logger.info(f"添加交易信号: {signal['coin']} {signal['type']}")

    def clear_signals(self):
        """清空所有信号"""
        self.signals = []
        self._save_signals()
        logger.info("已清空所有交易信号")

    async def execute_buy(self, client: OKXClient, signal: TradingSignal) -> Dict[str, Any]:
        """执行买入"""
        try:
            logger.info(f"\n🟢 执行买入: {signal.coin}")
            logger.info(f"   金额: ${self.max_trade_amount}")
            logger.info(f"   原因: {signal.reason}")

            inst_id = f"{signal.coin}-USDT"
            ticker = await client.get_ticker(inst_id)
            if not ticker or ticker.get("code") != "0":
                return {"success": False, "error": "无法获取价格"}

            price = float(ticker["data"][0]["last"])
            quantity = self.max_trade_amount / price

            balance = await client.get_balance()
            if not balance or balance.get("code") != "0":
                return {"success": False, "error": "无法获取余额"}

            usdt_available = 0.0
            for detail in balance.get("data", [{}])[0].get("details", []):
                if detail.get("ccy") == "USDT":
                    usdt_available = float(detail.get("availBal", 0))
                    break

            if usdt_available < self.max_trade_amount:
                return {"success": False, "error": "余额不足"}

            result = await client.place_order(
                inst_id=inst_id,
                side="buy",
                ord_type="market",
                sz=str(quantity)
            )

            if result.get("code") == "0":
                ord_id = result["data"][0]["ordId"]
                logger.info(f"✅ 买入成功: {ord_id}")

                self.trades.append(TradeRecord(
                    time=datetime.now().isoformat(),
                    coin=signal.coin,
                    action="buy",
                    price=price,
                    amount=quantity,
                    reason=signal.reason,
                    order_id=ord_id,
                    status="completed"
                ))

                self.today_trade_count += 1
                self._save_config()
                self._save_trades()

                return {
                    "success": True,
                    "coin": signal.coin,
                    "price": price,
                    "quantity": quantity,
                    "amount": self.max_trade_amount,
                    "order_id": ord_id
                }
            else:
                logger.error(f"❌ 买入失败: {result.get('msg')}")
                return {"success": False, "error": result.get("msg")}

        except Exception as e:
            logger.error(f"执行买入失败: {e}")
            return {"success": False, "error": str(e)}

    async def execute_sell(self, client: OKXClient, signal: TradingSignal) -> Dict[str, Any]:
        """执行卖出"""
        try:
            logger.info(f"\n🔴 执行卖出: {signal.coin}")
            logger.info(f"   原因: {signal.reason}")

            inst_id = f"{signal.coin}-USDT"

            positions = await client.get_positions()
            if not positions or positions.get("code") != "0":
                return {"success": False, "error": "无法获取持仓"}

            position = None
            for pos in positions.get("data", []):
                if pos.get("instId") == inst_id and float(pos.get("pos", 0)) != 0:
                    position = pos
                    break

            if not position:
                return {"success": False, "error": "没有持仓"}

            amount = abs(float(position.get("pos", 0)))

            result = await client.place_order(
                inst_id=inst_id,
                side="sell",
                ord_type="market",
                sz=str(amount)
            )

            if result.get("code") == "0":
                ord_id = result["data"][0]["ordId"]
                logger.info(f"✅ 卖出成功: {ord_id}")

                ticker = await client.get_ticker(inst_id)
                price = float(ticker["data"][0]["last"]) if ticker and ticker.get("code") == "0" else 0

                self.trades.append(TradeRecord(
                    time=datetime.now().isoformat(),
                    coin=signal.coin,
                    action="sell",
                    price=price,
                    amount=amount,
                    reason=signal.reason,
                    order_id=ord_id,
                    status="completed"
                ))

                self._save_trades()

                return {
                    "success": True,
                    "coin": signal.coin,
                    "price": price,
                    "quantity": amount,
                    "amount": price * amount,
                    "order_id": ord_id
                }
            else:
                logger.error(f"❌ 卖出失败: {result.get('msg')}")
                return {"success": False, "error": result.get("msg")}

        except Exception as e:
            logger.error(f"执行卖出失败: {e}")
            return {"success": False, "error": str(e)}

    async def execute_signal(self, index: int) -> Dict[str, Any]:
        """执行指定索引的信号"""
        self._reset_daily_count_if_needed()

        if not self.enabled:
            return {"success": False, "error": "交易Agent已禁用"}

        if index < 0 or index >= len(self.signals):
            return {"success": False, "error": "信号索引无效"}

        if self.today_trade_count >= self.max_daily_trades:
            return {"success": False, "error": "已达到每日最大交易次数限制"}

        signal = self.signals[index]
        async with OKXClient() as client:
            if signal.type == "BUY":
                result = await self.execute_buy(client, signal)
            else:
                result = await self.execute_sell(client, signal)

            if result.get("success"):
                self.signals.pop(index)
                self._save_signals()

            return result

    async def execute_all_signals(self) -> List[Dict[str, Any]]:
        """执行所有待处理信号"""
        self._reset_daily_count_if_needed()

        if not self.enabled:
            return [{"success": False, "error": "交易Agent已禁用"}]

        if not self.signals:
            return []

        results = []
        async with OKXClient() as client:
            for signal in self.signals[:]:
                if self.today_trade_count >= self.max_daily_trades:
                    break

                if signal.type == "BUY":
                    result = await self.execute_buy(client, signal)
                else:
                    result = await self.execute_sell(client, signal)

                results.append(result)

                if result.get("success"):
                    self.signals.remove(signal)

            self._save_signals()

        return results

    def get_recent_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近的交易记录"""
        trades = self.trades[-limit:]
        return [
            {
                "time": t.time,
                "coin": t.coin,
                "action": t.action,
                "price": t.price,
                "amount": t.amount,
                "reason": t.reason,
                "order_id": t.order_id,
                "status": t.status
            }
            for t in trades
        ]

    def get_status(self) -> Dict[str, Any]:
        """获取Agent状态"""
        return {
            "enabled": self.enabled,
            "auto_execute": self.auto_execute,
            "max_trade_amount": self.max_trade_amount,
            "max_daily_trades": self.max_daily_trades,
            "today_trade_count": self.get_today_trade_count(),
            "pending_signals": len(self.signals),
            "total_trades": len(self.trades)
        }


trading_agent = TradingAgent()
