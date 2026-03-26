"""
统一持仓管理
集中管理所有持仓的止盈止损
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
import json
import os
from loguru import logger


@dataclass
class PositionProfitConfig:
    """止盈止损配置 - 废弃，改用 trading_engine.TradingConfig 统一管理"""
    stop_loss_percent: float = -1.0
    take_profit_percent: float = 5.0
    trailing_stop_enabled: bool = True
    trailing_stop_trigger: float = 3.0
    trailing_stop_distance: float = 1.5
    time_stop_hours: float = 48.0  # 时间止损（小时）
    dynamic_bands_enabled: bool = False  # 启用动态止盈止损


@dataclass
class Position:
    """持仓信息"""
    coin: str
    entry_price: float
    amount: float
    stop_loss: float
    take_profit: float
    trailing_stop_price: Optional[float] = None
    trailing_activated: bool = False
    highest_price: float = 0.0
    entry_time: str = ""
    layers: int = 1
    total_invested: float = 0.0


@dataclass
class TakeProfitAction:
    """止盈动作"""
    coin: str
    sell_percent: float
    current_price: float
    reason: str


class PositionManager:
    """
    统一持仓管理器
    所有交易策略共享同一个持仓管理器
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, data_dir: str = "./data"):
        if self._initialized:
            return
        self._initialized = True

        self.data_dir = data_dir
        self.data_file = os.path.join(data_dir, "positions.json")
        os.makedirs(data_dir, exist_ok=True)

        # 配置从 trading_engine 读取，不再维护独立配置
        self.config = PositionProfitConfig()  # 保留字段以兼容旧代码，但实际值从 trading_engine 获取
        self.positions: Dict[str, Position] = {}
        self._load_positions()

    def _get_config(self) -> PositionProfitConfig:
        """从 trading_engine 获取配置（统一配置源）"""
        try:
            from app.services.trading_engine import trading_engine
            return PositionProfitConfig(
                stop_loss_percent=trading_engine.config.stop_loss_percent,
                take_profit_percent=trading_engine.config.take_profit_percent,
                time_stop_hours=trading_engine.config.time_stop_hours,
                dynamic_bands_enabled=trading_engine.config.dynamic_bands_enabled
            )
        except:
            # 如果 trading_engine 未初始化，返回默认配置
            return self.config

    def _load_positions(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.positions = {
                        k: Position(**v) for k, v in data.items()
                    }
            except Exception:
                self.positions = {}

    def _save_positions(self):
        try:
            data = {
                k: {
                    "coin": v.coin,
                    "entry_price": v.entry_price,
                    "amount": v.amount,
                    "stop_loss": v.stop_loss,
                    "take_profit": v.take_profit,
                    "trailing_stop_price": v.trailing_stop_price,
                    "trailing_activated": v.trailing_activated,
                    "highest_price": v.highest_price,
                    "entry_time": v.entry_time,
                    "layers": v.layers,
                    "total_invested": v.total_invested
                } for k, v in self.positions.items()
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            pass

    def add_position(self, coin: str, entry_price: float, amount: float,
                     stop_loss: float = None, take_profit: float = None,
                     layers: int = 1, total_invested: float = 0.0):
        """添加持仓"""
        config = self._get_config()
        if stop_loss is None:
            stop_loss = entry_price * (1 + config.stop_loss_percent / 100)
        if take_profit is None:
            take_profit = entry_price * (1 + config.take_profit_percent / 100)

        self.positions[coin] = Position(
            coin=coin,
            entry_price=entry_price,
            amount=amount,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop_price=None,
            trailing_activated=False,
            highest_price=entry_price,
            entry_time=datetime.now().isoformat(),
            layers=layers,
            total_invested=total_invested
        )
        self._save_positions()
        return self.positions[coin]

    def update_position(self, coin: str, current_price: float) -> Dict:
        """更新持仓状态，返回需要执行的操作"""
        if coin not in self.positions:
            return {}

        config = self._get_config()
        pos = self.positions[coin]

        # 更新最高价
        if current_price > pos.highest_price:
            pos.highest_price = current_price

            # 触发移动止损
            if config.trailing_stop_enabled and not pos.trailing_activated:
                price_change = (current_price - pos.entry_price) / pos.entry_price * 100
                if price_change >= config.trailing_stop_trigger:
                    pos.trailing_activated = True
                    pos.trailing_stop_price = current_price * (1 - config.trailing_stop_distance / 100)

        # 检查移动止损
        if pos.trailing_activated and pos.trailing_stop_price:
            if current_price <= pos.trailing_stop_price:
                return {
                    "action": "sell",
                    "reason": f"移动止损 @{pos.trailing_stop_price:.4f}",
                    "sell_percent": 100
                }

        # 检查固定止损
        if current_price <= pos.stop_loss:
            return {
                "action": "sell",
                "reason": f"止损 @{pos.stop_loss:.4f} ({config.stop_loss_percent}%)",
                "sell_percent": 100
            }

        # 检查止盈
        if current_price >= pos.take_profit:
            return {
                "action": "sell",
                "reason": f"止盈 @{pos.take_profit:.4f} ({config.take_profit_percent}%)",
                "sell_percent": 100
            }

        # 检查时间止损
        time_stop_result = self.check_time_stop(coin)
        if time_stop_result:
            return time_stop_result

        return {}

    async def calculate_dynamic_bands(self, coin: str, current_price: float) -> Optional[Dict[str, float]]:
        """
        计算动态止盈止损
        基于市场波动率、市值、趋势动态调整
        """
        config = self._get_config()
        if not config.dynamic_bands_enabled:
            return None

        try:
            from app.core.okx_client import OKXClient
            okx_client = OKXClient()

            # 获取24h K线数据计算波动率
            candles_response = await okx_client.get_candles(f"{coin}-USDT", "1H", limit=24)
            if not candles_response or len(candles_response) < 10:
                return {
                    "stop_loss_percent": self.config.stop_loss_percent,
                    "take_profit_percent": self.config.take_profit_percent
                }

            # 提取收盘价
            prices = [float(candle[4]) for candle in candles_response]
            if len(prices) < 10:
                return {
                    "stop_loss_percent": self.config.stop_loss_percent,
                    "take_profit_percent": self.config.take_profit_percent
                }

            # 计算24h波动率（标准差/平均值）
            avg_price = sum(prices) / len(prices)
            variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
            volatility = (variance ** 0.5) / avg_price * 100  # 波动率百分比

            # 获取24h涨跌幅
            ticker_response = await okx_client.get_ticker(f"{coin}-USDT")
            change_24h = 0.0
            vol_24h = 0.0
            if ticker_response:
                change_24h = float(ticker_response.get("change24h", 0))
                vol_24h = float(ticker_response.get("vol24h", 0))

            # 估算市值等级
            market_cap_level = (
                "large" if vol_24h > 1000000000 else
                "medium" if vol_24h > 100000000 else
                "small"
            )

            # 计算波动系数 (0.5 ~ 2.0)
            volatility_factor = min(2.0, max(0.5, volatility / 3))

            # 市值系数 (0.6 ~ 1.2)
            market_cap_factor = (
                1.2 if market_cap_level == "large" else
                1.0 if market_cap_level == "medium" else
                0.6
            )

            # 趋势系数 (0.8 ~ 1.2)
            trend_factor = (
                1.2 if abs(change_24h) > 10 else
                1.0 if abs(change_24h) > 5 else
                0.8
            )

            # 基础值：止损-3%，止盈+6%
            base_stop_loss = -3.0
            base_take_profit = 6.0

            # 计算动态止损止盈
            dynamic_stop_loss = base_stop_loss * volatility_factor * market_cap_factor * trend_factor
            dynamic_take_profit = base_take_profit * volatility_factor * market_cap_factor * trend_factor

            # 限制范围
            dynamic_stop_loss = min(-0.5, max(-5.0, dynamic_stop_loss))
            dynamic_take_profit = min(15.0, max(3.0, dynamic_take_profit))

            logger.info(
                f"📊 动态波段 [{coin}]: 波动率={volatility:.2f}%, 24h涨跌={change_24h:.2f}%, "
                f"市值等级={market_cap_level}, "
                f"止损={dynamic_stop_loss:.2f}%, 止盈={dynamic_take_profit:.2f}%"
            )

            return {
                "stop_loss_percent": dynamic_stop_loss,
                "take_profit_percent": dynamic_take_profit,
                "volatility": volatility,
                "change_24h": change_24h,
                "market_cap_level": market_cap_level,
                "volatility_factor": volatility_factor,
                "market_cap_factor": market_cap_factor,
                "trend_factor": trend_factor
            }

        except Exception as e:
            logger.error(f"计算动态波段失败: {e}")
            return {
                "stop_loss_percent": self.config.stop_loss_percent,
                "take_profit_percent": self.config.take_profit_percent
            }

    def remove_position(self, coin: str):
        """移除持仓"""
        if coin in self.positions:
            del self.positions[coin]
            self._save_positions()

    def get_position(self, coin: str) -> Optional[Position]:
        """获取持仓"""
        return self.positions.get(coin)

    def get_all_positions(self) -> Dict[str, Position]:
        """获取所有持仓"""
        return self.positions

    def update_config(self, config: Dict):
        """
        更新配置 - 废弃方法
        配置应通过 trading_engine 更新，position_manager 从 trading_engine 读取
        此方法保留仅为兼容性，已不再实际更新配置
        """
        logger.warning("⚠️ PositionManager.update_config 已废弃，请使用 trading_engine.config 更新配置")
        try:
            from app.services.trading_engine import trading_engine
            if "stop_loss_percent" in config:
                trading_engine.config.stop_loss_percent = config["stop_loss_percent"]
            if "take_profit_percent" in config:
                trading_engine.config.take_profit_percent = config["take_profit_percent"]
            if "time_stop_hours" in config:
                trading_engine.config.time_stop_hours = config["time_stop_hours"]
            if "dynamic_bands_enabled" in config:
                trading_engine.config.dynamic_bands_enabled = config["dynamic_bands_enabled"]
        except Exception as e:
            logger.error(f"更新配置失败: {e}")

    def get_config(self) -> Dict:
        """获取当前配置 - 从 trading_engine 读取"""
        config = self._get_config()
        return {
            "stop_loss_percent": config.stop_loss_percent,
            "take_profit_percent": config.take_profit_percent,
            "trailing_stop_enabled": config.trailing_stop_enabled,
            "trailing_stop_trigger": config.trailing_stop_trigger,
            "trailing_stop_distance": config.trailing_stop_distance,
            "time_stop_hours": config.time_stop_hours,
            "dynamic_bands_enabled": config.dynamic_bands_enabled
        }

    def check_time_stop(self, coin: str) -> Optional[Dict[str, Any]]:
        """检查时间止损"""
        if coin not in self.positions:
            return None

        config = self._get_config()
        pos = self.positions[coin]
        if not pos.entry_time:
            return None

        try:
            entry_dt = datetime.fromisoformat(pos.entry_time)
            now = datetime.now()
            hours_since_entry = (now - entry_dt).total_seconds() / 3600

            if hours_since_entry >= config.time_stop_hours:
                return {
                    "action": "sell",
                    "reason": f"时间止损：持仓{hours_since_entry:.1f}小时",
                    "sell_percent": 100,
                    "hours_held": hours_since_entry,
                    "time_limit": config.time_stop_hours
                }
        except Exception as e:
            logger.error(f"检查时间止损失败: {e}")

        return None

    def calculate_time_decay_stop_loss(self, coin: str, current_price: float) -> Optional[Dict[str, Any]]:
        """
        计算时间衰减止损（来自crypto-trading-bot-master）
        持仓时间越长，止损线越收紧
        """
        if coin not in self.positions:
            return None

        try:
            from app.services.trading_engine import trading_engine
            config = trading_engine.config

            if not config.time_decay_enabled:
                return None

            pos = self.positions[coin]
            if not pos.entry_time:
                return None

            entry_dt = datetime.fromisoformat(pos.entry_time)
            now = datetime.now()
            hours_since_entry = (now - entry_dt).total_seconds() / 3600

            # 计算衰减量：每小时收紧 time_decay_factor
            decay_amount = hours_since_entry * config.time_decay_factor

            # 基础止损（使用初始止损线）
            initial_stop_loss = abs(config.stop_loss_percent)
            current_stop_loss = max(config.max_stop_loss,
                                     min(config.min_stop_loss, -(initial_stop_loss - decay_amount)))

            return {
                "action": "adjust_stop_loss",
                "stop_loss_percent": current_stop_loss,
                "initial_stop_loss": initial_stop_loss,
                "hours_held": hours_since_entry,
                "decay_amount": decay_amount,
                "reason": f"时间衰减：持仓{hours_since_entry:.1f}小时，止损收紧至{current_stop_loss:.2f}%"
            }
        except Exception as e:
            logger.error(f"计算时间衰减止损失败: {e}")
            return None

    def check_tiered_take_profit(self, coin: str, current_price: float) -> Optional[Dict[str, Any]]:
        """
        检查分批止盈（来自crypto-trading-bot-master）
        三层止盈：5%/10%/15%，分别卖出30%/30%/40%
        """
        if coin not in self.positions:
            return None

        try:
            from app.services.trading_engine import trading_engine
            config = trading_engine.config

            if not config.tiered_take_profit_enabled:
                return None

            pos = self.positions[coin]
            pnl_percent = (current_price - pos.entry_price) / pos.entry_price * 100

            # 检查第三层止盈（15%）
            if pnl_percent >= config.take_profit_tier3_percent:
                return {
                    "action": "sell",
                    "reason": f"第三层止盈：盈利{pnl_percent:.2f}% >= {config.take_profit_tier3_percent}%",
                    "sell_percent": config.take_profit_tier3_ratio * 100,
                    "tier": 3,
                    "pnl_percent": pnl_percent
                }

            # 检查第二层止盈（10%）
            elif pnl_percent >= config.take_profit_tier2_percent:
                return {
                    "action": "sell",
                    "reason": f"第二层止盈：盈利{pnl_percent:.2f}% >= {config.take_profit_tier2_percent}%",
                    "sell_percent": config.take_profit_tier2_ratio * 100,
                    "tier": 2,
                    "pnl_percent": pnl_percent
                }

            # 检查第一层止盈（5%）
            elif pnl_percent >= config.take_profit_tier1_percent:
                return {
                    "action": "sell",
                    "reason": f"第一层止盈：盈利{pnl_percent:.2f}% >= {config.take_profit_tier1_percent}%",
                    "sell_percent": config.take_profit_tier1_ratio * 100,
                    "tier": 1,
                    "pnl_percent": pnl_percent
                }

        except Exception as e:
            logger.error(f"检查分批止盈失败: {e}")

        return None

    def reset(self, coin: str = None):
        """重置持仓"""
        if coin:
            self.remove_position(coin)
        else:
            self.positions.clear()
            self._save_positions()


# 全局单例
position_manager = PositionManager()