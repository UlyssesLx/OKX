"""
Sub-agent服务架构
管理各个子服务（舆情、数据提醒等）的协调工作
"""
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from loguru import logger
import asyncio
import json
import os

from app.core.okx_client import OKXClient

BEIJING_TZ = timezone(timedelta(hours=8))


@dataclass
class Reminder:
    """数据提醒"""
    time: str
    coin: str
    type: str  # "price_above", "price_below", "volume_spike"
    threshold: float
    triggered: bool = False


@dataclass
class SubAgentStatus:
    """子Agent状态"""
    name: str
    enabled: bool
    last_run: Optional[str]
    run_count: int
    error_count: int


class SubAgentService:
    """Sub-agent服务基类"""

    def __init__(self, name: str, data_dir: str = "."):
        self.name = name
        self.data_dir = data_dir
        self.enabled = True
        self.last_run: Optional[str] = None
        self.run_count = 0
        self.error_count = 0

    async def run(self, client: OKXClient) -> Dict[str, Any]:
        """运行子Agent"""
        raise NotImplementedError

    def get_status(self) -> SubAgentStatus:
        """获取状态"""
        return SubAgentStatus(
            name=self.name,
            enabled=self.enabled,
            last_run=self.last_run,
            run_count=self.run_count,
            error_count=self.error_count
        )


class DataReminderAgent(SubAgentService):
    """数据提醒Agent"""

    def __init__(self, data_dir: str = "."):
        super().__init__("data_reminder", data_dir)
        self.reminders_file = os.path.join(data_dir, "data_reminders.json")
        self.reminders: List[Reminder] = []
        self._load_reminders()

    def _load_reminders(self):
        """加载提醒列表"""
        if os.path.exists(self.reminders_file):
            try:
                with open(self.reminders_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.reminders = [Reminder(**r) for r in data]
            except Exception as e:
                logger.error(f"加载提醒列表失败: {e}")

    def _save_reminders(self):
        """保存提醒列表"""
        try:
            os.makedirs(os.path.dirname(self.reminders_file), exist_ok=True)
            data = [
                {
                    "time": r.time,
                    "coin": r.coin,
                    "type": r.type,
                    "threshold": r.threshold,
                    "triggered": r.triggered
                }
                for r in self.reminders
            ]
            with open(self.reminders_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存提醒列表失败: {e}")

    def add_reminder(self, coin: str, type: str, threshold: float) -> str:
        """添加提醒"""
        reminder = Reminder(
            time=datetime.now().isoformat(),
            coin=coin,
            type=type,
            threshold=threshold,
            triggered=False
        )
        self.reminders.append(reminder)
        self._save_reminders()
        logger.info(f"添加提醒: {coin} {type} {threshold}")
        return reminder.time

    def remove_reminder(self, time: str):
        """移除提醒"""
        self.reminders = [r for r in self.reminders if r.time != time]
        self._save_reminders()

    def get_reminders(self) -> List[Dict[str, Any]]:
        """获取提醒列表"""
        return [
            {
                "time": r.time,
                "coin": r.coin,
                "type": r.type,
                "threshold": r.threshold,
                "triggered": r.triggered
            }
            for r in self.reminders
        ]

    async def check_reminders(self, client: OKXClient) -> List[Dict[str, Any]]:
        """检查提醒"""
        triggered = []

        for reminder in self.reminders:
            if reminder.triggered:
                continue

            try:
                inst_id = f"{reminder.coin}-USDT"
                ticker = await client.get_ticker(inst_id)
                if not ticker or ticker.get("code") != "0":
                    continue

                current_price = float(ticker["data"][0]["last"])
                should_trigger = False

                if reminder.type == "price_above" and current_price >= reminder.threshold:
                    should_trigger = True
                elif reminder.type == "price_below" and current_price <= reminder.threshold:
                    should_trigger = True

                if should_trigger:
                    reminder.triggered = True
                    triggered.append({
                        "coin": reminder.coin,
                        "type": reminder.type,
                        "threshold": reminder.threshold,
                        "current_price": current_price,
                        "time": datetime.now().isoformat()
                    })
                    logger.info(f"🔔 提醒触发: {reminder.coin} {reminder.type} {reminder.threshold} @ {current_price}")

            except Exception as e:
                logger.error(f"检查提醒失败 {reminder.coin}: {e}")

        self._save_reminders()
        return triggered

    async def run(self, client: OKXClient) -> Dict[str, Any]:
        """运行提醒Agent"""
        self.last_run = datetime.now().isoformat()
        self.run_count += 1

        try:
            triggered = await self.check_reminders(client)
            return {"status": "success", "triggered": triggered, "count": len(triggered)}
        except Exception as e:
            self.error_count += 1
            logger.error(f"数据提醒Agent运行失败: {e}")
            return {"status": "error", "error": str(e)}


class MarketSentimentAgent(SubAgentService):
    """市场舆情Agent"""

    def __init__(self, data_dir: str = "."):
        super().__init__("market_sentiment", data_dir)
        self.sentiment_file = os.path.join(data_dir, "market_sentiment.json")

    async def analyze_sentiment(self) -> Dict[str, Any]:
        """分析市场舆情"""
        try:
            hour = datetime.now(BEIJING_TZ).hour
            factors = []

            if 9 <= hour <= 17:
                factors.append("交易时段，市场活跃")

            sentiment = {
                "score": 5,
                "trend": "neutral",
                "factors": factors,
                "timestamp": datetime.now().isoformat()
            }

            logger.info(f"舆情分析: 评分{sentiment['score']}/10, 趋势{sentiment['trend']}")
            return sentiment
        except Exception as e:
            logger.error(f"舆情分析失败: {e}")
            return {"score": 5, "trend": "neutral", "factors": [], "timestamp": datetime.now().isoformat()}

    async def run(self, client: OKXClient) -> Dict[str, Any]:
        """运行舆情Agent"""
        self.last_run = datetime.now().isoformat()
        self.run_count += 1

        try:
            sentiment = await self.analyze_sentiment()

            os.makedirs(os.path.dirname(self.sentiment_file), exist_ok=True)
            with open(self.sentiment_file, 'w', encoding='utf-8') as f:
                json.dump(sentiment, f, indent=2, ensure_ascii=False)

            return {"status": "success", "sentiment": sentiment}
        except Exception as e:
            self.error_count += 1
            logger.error(f"舆情Agent运行失败: {e}")
            return {"status": "error", "error": str(e)}


class SubAgentCoordinator:
    """Sub-agent协调器"""

    def __init__(self, data_dir: str = "."):
        self.data_dir = data_dir
        self.agents: Dict[str, SubAgentService] = {}
        self._initialize_agents()

    def _initialize_agents(self):
        """初始化子Agent"""
        self.agents = {
            "data_reminder": DataReminderAgent(self.data_dir),
            "market_sentiment": MarketSentimentAgent(self.data_dir)
        }

    async def run_all(self, client: OKXClient) -> Dict[str, Any]:
        """运行所有子Agent"""
        results = {}

        for name, agent in self.agents.items():
            if agent.enabled:
                result = await agent.run(client)
                results[name] = result

        return results

    def get_all_status(self) -> Dict[str, SubAgentStatus]:
        """获取所有Agent状态"""
        return {name: agent.get_status() for name, agent in self.agents.items()}

    def enable_agent(self, name: str):
        """启用Agent"""
        if name in self.agents:
            self.agents[name].enabled = True
            logger.info(f"已启用Agent: {name}")

    def disable_agent(self, name: str):
        """禁用Agent"""
        if name in self.agents:
            self.agents[name].enabled = False
            logger.info(f"已禁用Agent: {name}")


sub_agent_coordinator = SubAgentCoordinator()
