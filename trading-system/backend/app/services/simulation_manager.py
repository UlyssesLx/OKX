"""
模拟持仓管理器
管理模拟盘的持仓、止盈止损和收益统计
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
from loguru import logger

BEIJING_TZ = timezone(timedelta(hours=8))

# 获取数据目录 - 优先使用相对于backend目录的data目录
def get_data_dir() -> str:
    # 尝试多个可能的数据目录路径
    possible_paths = [
        Path(__file__).parent.parent.parent / "data",  # backend/data (优先)
        Path("./data"),
        Path(os.getcwd()) / "data",
    ]
    
    for path in possible_paths:
        exists = path.exists()
        has_positions = (path / "simulated_positions.json").exists() if exists else False
        if exists and has_positions:
            return str(path)
    
    backend_data = Path(__file__).parent.parent.parent / "data"
    backend_data.mkdir(parents=True, exist_ok=True)
    return str(backend_data)


@dataclass
class SimulatedPosition:
    coin: str
    entry_price: float
    amount: float
    usdt_value: float
    entry_time: str
    stop_loss_percent: float = -1.0
    take_profit_percent: float = 5.0
    highest_price: float = 0.0
    trailing_activated: bool = False
    trailing_stop_price: float = 0.0
    is_short: bool = False  # 是否为空单持仓
    leverage: float = 1.0  # 杠杆倍数
    is_swap: bool = False  # 是否为合约模式（True=合约，False=现货）
    pyramid_layers: int = 0  # 已加仓层数（0-3）
    pyramid_base_price: float = 0.0  # 基准价格（用于计算加仓点）
    pyramid_layer_prices: list = None  # 各层加仓价格记录
    partial_profit_taken: bool = False  # 是否已部分止盈
    trend_score: float = 5.0  # 趋势评分（用于智能止损）
    over_position_exemption_start: Optional[str] = None  # 超仓豁免期开始时间
    small_profit_reduced: bool = False  # 是否已执行小盈减仓
    over_position_reduced: bool = False  # 是否已执行超仓减仓
    trend_reversal_reduced: bool = False  # 是否已执行趋势变盘减仓
    trend_history: list = None  # 趋势评分历史（用于趋势变盘检测）


@dataclass
class SimulatedTrade:
    coin: str
    action: str
    price: float
    amount: float
    usdt_value: float
    pnl: float = 0.0
    pnl_percent: float = 0.0
    reason: str = ""
    timestamp: str = ""
    leverage: float = 1.0
    strategy: str = ""  # 策略名称
    is_swap: bool = False  # 是否为合约模式


class SimulationManager:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, data_dir: str = None):
        if self._initialized:
            return
        self._initialized = True
        
        self.data_dir = data_dir if data_dir else get_data_dir()
        self.positions_file = os.path.join(self.data_dir, "simulated_positions.json")
        self.trades_file = os.path.join(self.data_dir, "simulated_trades.json")
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.positions: Dict[str, SimulatedPosition] = {}
        self.trades: List[SimulatedTrade] = []
        self.total_pnl: float = 0.0
        self.win_count: int = 0
        self.loss_count: int = 0
        self.short_positions: Dict[str, SimulatedPosition] = {}
        
        self.initial_balance: float = 1000.0
        self.available_balance: float = 1000.0
        
        self._load_data()
    
    def _load_data(self):
        try:
            if os.path.exists(self.positions_file):
                with open(self.positions_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        logger.warning(f"持仓文件为空，使用默认值")
                        self._save_positions()
                        return
                    data = json.loads(content)
                    self.positions = {}
                    for k, v in data.get("positions", {}).items():
                        if "pyramid_layer_prices" not in v:
                            v["pyramid_layer_prices"] = []
                        if "partial_profit_taken" not in v:
                            v["partial_profit_taken"] = False
                        if "trend_score" not in v:
                            v["trend_score"] = 5.0
                        if "pyramid_base_price" not in v:
                            v["pyramid_base_price"] = 0.0
                        if "leverage" not in v:
                            v["leverage"] = 1.0
                        if "trend_history" not in v:
                            v["trend_history"] = []
                        self.positions[k] = SimulatedPosition(**v)
                    self.short_positions = {}
                    for k, v in data.get("short_positions", {}).items():
                        if "leverage" not in v:
                            v["leverage"] = 1.0
                        if "trend_history" not in v:
                            v["trend_history"] = []
                        self.short_positions[k] = SimulatedPosition(**v)
                    self.total_pnl = data.get("total_pnl", 0.0)
                    self.win_count = data.get("win_count", 0)
                    self.loss_count = data.get("loss_count", 0)
                    self.initial_balance = data.get("initial_balance", 1000.0)
                    self.available_balance = data.get("available_balance", 1000.0)
                    
                    total_position_value = sum(p.usdt_value for p in self.positions.values())
                    total_short_value = sum(p.usdt_value for p in self.short_positions.values())
                    expected_available = self.initial_balance - total_position_value - total_short_value + self.total_pnl
                    if abs(self.available_balance - expected_available) > 0.01:
                        logger.warning(f"余额不一致，自动修正: {self.available_balance:.2f} -> {expected_available:.2f}")
                        self.available_balance = expected_available
                        self._save_positions()
        except json.JSONDecodeError as e:
            logger.error(f"持仓文件JSON格式错误: {e}，将重置文件")
            self._save_positions()
        except Exception as e:
            logger.error(f"加载模拟持仓失败: {e}")
        
        try:
            if os.path.exists(self.trades_file):
                with open(self.trades_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        logger.warning(f"交易记录文件为空，跳过加载")
                        return
                    data = json.loads(content)
                    self.trades = [SimulatedTrade(**t) for t in data]
        except json.JSONDecodeError as e:
            logger.error(f"交易记录文件JSON格式错误: {e}")
        except Exception as e:
            logger.error(f"加载模拟交易记录失败: {e}")
    
    def _save_positions(self):
        try:
            data = {
                "positions": {
                    k: {
                        "coin": v.coin,
                        "entry_price": v.entry_price,
                        "amount": v.amount,
                        "usdt_value": v.usdt_value,
                        "entry_time": v.entry_time,
                        "stop_loss_percent": v.stop_loss_percent,
                        "take_profit_percent": v.take_profit_percent,
                        "highest_price": v.highest_price,
                        "trailing_activated": v.trailing_activated,
                        "trailing_stop_price": v.trailing_stop_price,
                        "is_short": v.is_short,
                        "pyramid_layers": v.pyramid_layers,
                        "pyramid_base_price": v.pyramid_base_price,
                        "pyramid_layer_prices": v.pyramid_layer_prices,
                        "partial_profit_taken": v.partial_profit_taken,
                        "trend_score": v.trend_score,
                        "leverage": v.leverage,
                        "is_swap": v.is_swap if hasattr(v, 'is_swap') else False
                    } for k, v in self.positions.items()
                },
                "short_positions": {
                    k: {
                        "coin": v.coin,
                        "entry_price": v.entry_price,
                        "amount": v.amount,
                        "usdt_value": v.usdt_value,
                        "entry_time": v.entry_time,
                        "stop_loss_percent": v.stop_loss_percent,
                        "take_profit_percent": v.take_profit_percent,
                        "highest_price": v.highest_price,
                        "trailing_activated": v.trailing_activated,
                        "trailing_stop_price": v.trailing_stop_price,
                        "is_short": v.is_short,
                        "leverage": v.leverage,
                        "is_swap": v.is_swap if hasattr(v, 'is_swap') else False
                    } for k, v in self.short_positions.items()
                },
                "total_pnl": self.total_pnl,
                "win_count": self.win_count,
                "loss_count": self.loss_count,
                "initial_balance": self.initial_balance,
                "available_balance": self.available_balance
            }
            with open(self.positions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存模拟持仓失败: {e}")
    
    def _save_trades(self):
        try:
            data = [
                {
                    "coin": t.coin,
                    "action": t.action,
                    "price": t.price,
                    "amount": t.amount,
                    "usdt_value": t.usdt_value,
                    "pnl": t.pnl,
                    "pnl_percent": t.pnl_percent,
                    "reason": t.reason,
                    "timestamp": t.timestamp,
                    "leverage": t.leverage,
                    "strategy": t.strategy,
                    "is_swap": t.is_swap if hasattr(t, 'is_swap') else False
                } for t in self.trades
            ]
            with open(self.trades_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存模拟交易记录失败: {e}")
    
    def buy(self, coin: str, price: float, usdt_value: float, 
            stop_loss_percent: float = -1.0, take_profit_percent: float = 5.0,
            reason: str = "", leverage: float = 1.0, strategy: str = "",
            is_swap: bool = False) -> bool:
        if usdt_value > self.available_balance:
            return False
        
        amount = usdt_value / price
        self.available_balance -= usdt_value
        
        if coin in self.positions:
            pos = self.positions[coin]
            total_amount = pos.amount + amount
            total_value = pos.usdt_value + usdt_value
            avg_price = total_value / total_amount

            pos.entry_price = avg_price
            pos.amount = total_amount
            pos.usdt_value = total_value
        else:
            self.positions[coin] = SimulatedPosition(
                coin=coin,
                entry_price=price,
                amount=amount,
                usdt_value=usdt_value,
                entry_time=datetime.now(BEIJING_TZ).isoformat(),
                stop_loss_percent=stop_loss_percent,
                take_profit_percent=take_profit_percent,
                highest_price=price,
                pyramid_base_price=price,
                pyramid_layer_prices=[],
                leverage=leverage,
                is_swap=is_swap,
                trend_history=[]
            )
        
        trade = SimulatedTrade(
            coin=coin,
            action="buy",
            price=price,
            amount=amount,
            usdt_value=usdt_value,
            reason=reason,
            timestamp=datetime.now(BEIJING_TZ).isoformat(),
            leverage=leverage,
            strategy=strategy,
            is_swap=is_swap
        )
        self.trades.append(trade)

        self._save_positions()
        self._save_trades()

        return True

    def sell_short(self, coin: str, price: float, usdt_value: float,
                 stop_loss_percent: float = 1.0, take_profit_percent: float = -3.0,
                 reason: str = "", leverage: float = 1.0, strategy: str = "",
                 is_swap: bool = False) -> bool:
        """做空方法"""
        if usdt_value > self.available_balance:
            return False

        amount = usdt_value / price
        self.available_balance -= usdt_value

        if coin in self.short_positions:
            pos = self.short_positions[coin]
            total_amount = pos.amount + amount
            total_value = pos.usdt_value + usdt_value
            avg_price = total_value / total_amount

            pos.entry_price = avg_price
            pos.amount = total_amount
            pos.usdt_value = total_value
        else:
            self.short_positions[coin] = SimulatedPosition(
                coin=coin,
                entry_price=price,
                amount=amount,
                usdt_value=usdt_value,
                entry_time=datetime.now(BEIJING_TZ).isoformat(),
                stop_loss_percent=stop_loss_percent,
                take_profit_percent=take_profit_percent,
                highest_price=price,
                is_short=True,
                leverage=leverage,
                is_swap=is_swap,
                trend_history=[]
            )

        trade = SimulatedTrade(
            coin=coin,
            action="sell_short",
            price=price,
            amount=amount,
            usdt_value=usdt_value,
            reason=reason,
            timestamp=datetime.now(BEIJING_TZ).isoformat(),
            leverage=leverage,
            strategy=strategy,
            is_swap=is_swap
        )
        self.trades.append(trade)

        self._save_positions()
        self._save_trades()

        return True

    def sell(self, coin: str, price: float, sell_percent: float = 1.0,
             reason: str = "") -> Optional[SimulatedTrade]:
        if coin not in self.positions:
            return None

        pos = self.positions[coin]
        sell_amount = pos.amount * sell_percent
        sell_value = sell_amount * price

        # 盈亏计算（考虑杠杆）
        leverage = pos.leverage if hasattr(pos, 'leverage') and pos.leverage else 1.0
        is_swap = pos.is_swap if hasattr(pos, 'is_swap') else False
        pnl = (price - pos.entry_price) * sell_amount * leverage
        pnl_percent = (price - pos.entry_price) / pos.entry_price * 100 * leverage

        self.total_pnl += pnl
        self.available_balance += sell_value
        if pnl >= 0:
            self.win_count += 1
        else:
            self.loss_count += 1

        trade = SimulatedTrade(
            coin=coin,
            action="sell",
            price=price,
            amount=sell_amount,
            usdt_value=sell_value,
            pnl=pnl,
            pnl_percent=pnl_percent,
            reason=reason,
            timestamp=datetime.now(BEIJING_TZ).isoformat(),
            leverage=leverage,
            is_swap=is_swap
        )
        self.trades.append(trade)

        if sell_percent >= 1.0:
            # 清仓时重置金字塔层级（如果配置启用）
            if "止损" in reason or "stop" in reason.lower():
                # 这里可以添加重置金字塔层级的逻辑
                # 由于持仓被删除，新买入时会重新初始化
                pass
            del self.positions[coin]
        else:
            pos.amount -= sell_amount
            pos.usdt_value -= sell_value
            # 如果是部分止盈（sell_percent < 1），标记已部分止盈
            if sell_percent < 1.0:
                pos.partial_profit_taken = True

        self._save_positions()
        self._save_trades()
        return trade
    
    def update_price(self, coin: str, current_price: float):
        if coin not in self.positions:
            return

        pos = self.positions[coin]
        leverage = pos.leverage if hasattr(pos, 'leverage') and pos.leverage else 1.0

        # 激活移动止损条件：盈利达到3%（考虑杠杆）
        pnl_percent = (current_price - pos.entry_price) / pos.entry_price * 100 * leverage

        if pnl_percent >= 3:
            pos.trailing_activated = True

        # 更新最高价
        if current_price > pos.highest_price:
            pos.highest_price = current_price

        # 如果已激活移动止损，更新移动止损价格
        if pos.trailing_activated:
            # 移动止损价格 = 最高价 * 0.98（回调2%触发）
            new_trailing_stop = pos.highest_price * 0.98
            # 止损价格只能上移，不能下移
            if new_trailing_stop > pos.trailing_stop_price:
                pos.trailing_stop_price = new_trailing_stop

        self._save_positions()
    
    def check_sell_signals(self, coin: str, current_price: float, trend_score: float = 5.0, 
                           trading_config=None, volatility: float = 0.0, turnover_24h: float = 0.0) -> Dict:
        """
        检查卖出信号
        trading_config: 交易引擎配置，用于与实盘保持一致
        volatility: 波动率，用于动态止损止盈计算
        turnover_24h: 24h成交额，用于动态止损止盈计算
        """
        from app.core.config import settings

        if coin not in self.positions:
            return {"should_sell": False, "reason": "", "sell_percent": 0}

        pos = self.positions[coin]
        pos.trend_score = trend_score
        if not hasattr(pos, 'trend_history') or pos.trend_history is None:
            pos.trend_history = []
        pos.trend_history.append(trend_score)
        if len(pos.trend_history) > 10:
            pos.trend_history = pos.trend_history[-10:]

        leverage = pos.leverage if hasattr(pos, 'leverage') and pos.leverage else 1.0
        pnl_percent = (current_price - pos.entry_price) / pos.entry_price * 100 * leverage

        entry_time = datetime.fromisoformat(pos.entry_time)
        holding_time_minutes = (datetime.now(BEIJING_TZ) - entry_time).total_seconds() / 60

        # 持仓时间保护：刚加仓后禁止止损/平仓（对齐 ai_trading_bot.js）
        pyramid_add_time = getattr(pos, 'pyramid_add_time', None)
        time_protection_minutes = getattr(trading_config, 'stop_loss_time_protection_minutes', 60) if trading_config else 60
        if pyramid_add_time:
            pyramid_holding_minutes = (datetime.now(BEIJING_TZ) - pyramid_add_time).total_seconds() / 60
            if pyramid_holding_minutes < time_protection_minutes:
                return {
                    "should_sell": False,
                    "reason": f"做多金字塔加仓后{pyramid_holding_minutes:.1f}分钟，时间保护未到期 ({time_protection_minutes}分钟)，禁止平仓",
                    "sell_percent": 0
                }

        if trading_config and trading_config.dynamic_bands_enabled:
            volatility_factor = min(2.0, max(0.5, volatility / 3)) if volatility > 0 else 1.0
            if turnover_24h > 1000000000:
                market_cap_factor = 1.2
            elif turnover_24h > 100000000:
                market_cap_factor = 1.0
            else:
                market_cap_factor = 0.6

            if trading_config.long_dynamic_take_profit_enabled:
                if trend_score >= 9:
                    base_take_profit = getattr(trading_config, 'long_take_profit_trend_9_10', 15.0)
                elif trend_score >= 7:
                    base_take_profit = getattr(trading_config, 'long_take_profit_trend_7_8', 10.0)
                elif trend_score >= 5:
                    base_take_profit = getattr(trading_config, 'long_take_profit_trend_5_6', 8.0)
                else:
                    base_take_profit = getattr(trading_config, 'long_take_profit_trend_default', 6.0)
            else:
                base_take_profit = 6.0

            if getattr(trading_config, 'long_smart_stop_loss_enabled', False):
                if trend_score >= 8:
                    base_stop_loss = -abs(getattr(trading_config, 'long_stop_loss_trend_8_plus', 3.0))
                elif trend_score >= 6:
                    base_stop_loss = -abs(getattr(trading_config, 'long_stop_loss_trend_6_7', 2.0))
                else:
                    base_stop_loss = -abs(getattr(trading_config, 'long_stop_loss_trend_default', 1.5))
            else:
                base_stop_loss = -3.0

            trend_factor = 1.2 if trend_score >= 8 else (1.0 if trend_score >= 6 else 0.8)
            dynamic_stop_loss = base_stop_loss * volatility_factor * market_cap_factor * trend_factor
            dynamic_take_profit = base_take_profit * volatility_factor * market_cap_factor * trend_factor

            if getattr(trading_config, 'time_decay_enabled', False):
                hours_held = holding_time_minutes / 60
                time_decay_factor = getattr(trading_config, 'time_decay_factor', 0.1)
                time_decay_max_stop = getattr(trading_config, 'time_decay_max_stop', -8.0)
                time_decay = hours_held * time_decay_factor
                dynamic_stop_loss = max(dynamic_stop_loss - time_decay, time_decay_max_stop)

            max_stop_loss = getattr(trading_config, 'max_stop_loss', -5.0)
            min_stop_loss = getattr(trading_config, 'min_stop_loss', -1.0)
            min_take_profit = getattr(trading_config, 'min_take_profit', 2.0)
            max_take_profit = getattr(trading_config, 'max_take_profit', 15.0)
            dynamic_stop_loss = max(max_stop_loss, min(min_stop_loss, dynamic_stop_loss))
            dynamic_take_profit = max(min_take_profit, min(max_take_profit, dynamic_take_profit))

            if pnl_percent <= dynamic_stop_loss:
                pyramid_on_stop_loss_trend_score = getattr(trading_config, 'pyramid_on_stop_loss_trend_score', 8) if trading_config else 8
                pyramid_max_layers = getattr(trading_config, 'smart_pyramid_max_layers', 3) if trading_config else 3
                if holding_time_minutes < settings.STOP_LOSS_TIME_PROTECTION_MINUTES:
                    return {
                        "should_sell": False,
                        "reason": f"刚买入{holding_time_minutes:.0f}分钟，亏损{pnl_percent:.2f}%可能是正常回调，暂不止损",
                        "sell_percent": 0
                    }
                elif trend_score >= pyramid_on_stop_loss_trend_score and pos.pyramid_layers < pyramid_max_layers:
                    return {
                        "should_sell": False,
                        "reason": f"亏损{pnl_percent:.2f}%但趋势评分{trend_score}/10强劲，建议金字塔加仓",
                        "sell_percent": 0,
                        "suggest_pyramid": True
                    }
                else:
                    return {
                        "should_sell": True,
                        "sell_percent": 1.0,
                        "reason": f"动态止损触发！亏损{pnl_percent:.2f}% <= {dynamic_stop_loss:.2f}%"
                    }

            if pnl_percent >= dynamic_take_profit:
                return {
                    "should_sell": True,
                    "sell_percent": 1.0,
                    "reason": f"动态止盈触发！盈利{pnl_percent:.2f}% >= {dynamic_take_profit:.2f}%"
                }

            if pnl_percent >= dynamic_take_profit * 0.5 and not pos.partial_profit_taken:
                return {
                    "should_sell": True,
                    "sell_percent": settings.PARTIAL_TAKE_PROFIT_PERCENT,
                    "reason": f"部分止盈: 盈利{pnl_percent:.2f}% >= {dynamic_take_profit * 0.5:.2f}%"
                }

        else:
            long_smart_stop_loss_enabled = getattr(trading_config, 'long_smart_stop_loss_enabled', True) if trading_config else True
            if long_smart_stop_loss_enabled:
                if trend_score >= 8:
                    smart_stop_loss = -abs(getattr(trading_config, 'long_stop_loss_trend_8_plus', 3.0))
                elif trend_score >= 6:
                    smart_stop_loss = -abs(getattr(trading_config, 'long_stop_loss_trend_6_7', 2.0))
                else:
                    smart_stop_loss = -abs(getattr(trading_config, 'long_stop_loss_trend_default', 1.5))
            else:
                smart_stop_loss = pos.stop_loss_percent

            if pnl_percent <= smart_stop_loss:
                pyramid_on_stop_loss_enabled = getattr(trading_config, 'pyramid_on_stop_loss_enabled', settings.PYRAMID_ON_STOP_LOSS_ENABLED) if trading_config else settings.PYRAMID_ON_STOP_LOSS_ENABLED
                pyramid_on_stop_loss_trend_score = getattr(trading_config, 'pyramid_on_stop_loss_trend_score', settings.PYRAMID_ON_STOP_LOSS_TREND_SCORE) if trading_config else settings.PYRAMID_ON_STOP_LOSS_TREND_SCORE
                pyramid_on_stop_loss_max_position_percent = getattr(trading_config, 'pyramid_on_stop_loss_max_position_percent', settings.PYRAMID_ON_STOP_LOSS_MAX_POSITION_PERCENT) if trading_config else settings.PYRAMID_ON_STOP_LOSS_MAX_POSITION_PERCENT
                pyramid_on_stop_loss_min_cash = getattr(trading_config, 'pyramid_on_stop_loss_min_cash', settings.PYRAMID_ON_STOP_LOSS_MIN_CASH) if trading_config else settings.PYRAMID_ON_STOP_LOSS_MIN_CASH
                pyramid_max_layers = getattr(trading_config, 'smart_pyramid_max_layers', settings.PYRAMID_MAX_LAYERS) if trading_config else settings.PYRAMID_MAX_LAYERS

                if holding_time_minutes < 60:
                    return {
                        "should_sell": False,
                        "reason": f"刚买入{holding_time_minutes:.0f}分钟，亏损{pnl_percent:.2f}%可能是正常回调，暂不止损",
                        "sell_percent": 0
                    }
                elif (pyramid_on_stop_loss_enabled and
                      trend_score >= pyramid_on_stop_loss_trend_score and
                      pos.pyramid_layers < pyramid_max_layers):
                    position_percent = (pos.usdt_value / self.initial_balance * 100) if self.initial_balance > 0 else 0
                    if (position_percent < pyramid_on_stop_loss_max_position_percent and
                        self.available_balance >= pyramid_on_stop_loss_min_cash):
                        return {
                            "should_sell": False,
                            "reason": f"触发智能止损但趋势评分{trend_score}/10强劲，建议金字塔加仓",
                            "sell_percent": 0,
                            "suggest_pyramid": True,
                            "pyramid_reason": f"智能止损拦截加仓：亏损{pnl_percent:.2f}%但趋势强劲"
                        }
                    else:
                        return {
                            "should_sell": True,
                            "sell_percent": 1.0,
                            "reason": f"触发智能止损！亏损{pnl_percent:.2f}% (止损线{smart_stop_loss}%)，趋势评分{trend_score}/10"
                        }
                else:
                    return {
                        "should_sell": True,
                        "sell_percent": 1.0,
                        "reason": f"触发智能止损！亏损{pnl_percent:.2f}% (止损线{smart_stop_loss}%)，趋势评分{trend_score}/10"
                    }

            if pnl_percent <= pos.stop_loss_percent:
                pyramid_on_stop_loss_enabled = getattr(trading_config, 'pyramid_on_stop_loss_enabled', settings.PYRAMID_ON_STOP_LOSS_ENABLED) if trading_config else settings.PYRAMID_ON_STOP_LOSS_ENABLED
                pyramid_on_stop_loss_trend_score = getattr(trading_config, 'pyramid_on_stop_loss_trend_score', settings.PYRAMID_ON_STOP_LOSS_TREND_SCORE) if trading_config else settings.PYRAMID_ON_STOP_LOSS_TREND_SCORE
                pyramid_on_stop_loss_max_position_percent = getattr(trading_config, 'pyramid_on_stop_loss_max_position_percent', settings.PYRAMID_ON_STOP_LOSS_MAX_POSITION_PERCENT) if trading_config else settings.PYRAMID_ON_STOP_LOSS_MAX_POSITION_PERCENT
                pyramid_on_stop_loss_min_cash = getattr(trading_config, 'pyramid_on_stop_loss_min_cash', settings.PYRAMID_ON_STOP_LOSS_MIN_CASH) if trading_config else settings.PYRAMID_ON_STOP_LOSS_MIN_CASH
                pyramid_max_layers = getattr(trading_config, 'smart_pyramid_max_layers', settings.PYRAMID_MAX_LAYERS) if trading_config else settings.PYRAMID_MAX_LAYERS

                if (pyramid_on_stop_loss_enabled and
                    trend_score >= pyramid_on_stop_loss_trend_score and
                    pos.pyramid_layers < pyramid_max_layers):
                    total_position_value = sum(p.usdt_value for p in self.positions.values())
                    position_percent = (pos.usdt_value / self.initial_balance * 100) if self.initial_balance > 0 else 0
                    if (position_percent < pyramid_on_stop_loss_max_position_percent and
                        self.available_balance >= pyramid_on_stop_loss_min_cash):
                        return {
                            "should_sell": False,
                            "reason": f"触发固定止损但趋势评分{trend_score}/10强劲，建议金字塔加仓而非卖出",
                            "sell_percent": 0,
                            "suggest_pyramid": True,
                            "pyramid_reason": f"止损拦截加仓：亏损{pnl_percent:.2f}%但趋势强劲"
                        }
                return {
                    "should_sell": True,
                    "sell_percent": 1.0,
                    "reason": f"固定止损: 亏损{abs(pnl_percent):.2f}% <= {abs(pos.stop_loss_percent)}%"
                }

            long_dynamic_take_profit_enabled = getattr(trading_config, 'long_dynamic_take_profit_enabled', True) if trading_config else True
            if long_dynamic_take_profit_enabled:
                if trend_score >= 9:
                    dynamic_take_profit = getattr(trading_config, 'long_take_profit_trend_9_10', 15.0)
                elif trend_score >= 7:
                    dynamic_take_profit = getattr(trading_config, 'long_take_profit_trend_7_8', 10.0)
                elif trend_score >= 5:
                    dynamic_take_profit = getattr(trading_config, 'long_take_profit_trend_5_6', 8.0)
                else:
                    dynamic_take_profit = getattr(trading_config, 'long_take_profit_trend_default', 6.0)
            else:
                dynamic_take_profit = abs(pos.take_profit_percent)
                if trend_score >= 9:
                    dynamic_take_profit = 15.0
                elif trend_score >= 7:
                    dynamic_take_profit = 10.0
                elif trend_score >= 5:
                    dynamic_take_profit = 8.0

            pos.take_profit_percent = dynamic_take_profit

            if pnl_percent >= dynamic_take_profit:
                return {
                    "should_sell": True,
                    "sell_percent": 1.0,
                    "reason": f"触发动态止盈！盈利{pnl_percent:.2f}% >= 止盈线{dynamic_take_profit}% (趋势评分{trend_score}/10)"
                }

            if pnl_percent >= dynamic_take_profit * 0.5 and not pos.partial_profit_taken:
                return {
                    "should_sell": True,
                    "sell_percent": settings.PARTIAL_TAKE_PROFIT_PERCENT,
                    "reason": f"部分止盈: 盈利{pnl_percent:.2f}% >= {dynamic_take_profit * 0.5:.2f}%"
                }

        # 计算仓位占比
        position_percent = (pos.usdt_value / self.initial_balance * 100) if self.initial_balance > 0 else 0
        
        # 1. 小盈减仓：盈利≥止盈线50%且仓位>15%
        if (trading_config and getattr(trading_config, 'long_small_profit_reduce_enabled', True) and
            not pos.small_profit_reduced and pnl_percent > 0):
            long_dynamic_take_profit_enabled = getattr(trading_config, 'long_dynamic_take_profit_enabled', False)
            if long_dynamic_take_profit_enabled:
                if trend_score >= 9:
                    dynamic_take_profit = getattr(trading_config, 'long_take_profit_trend_9_10', 15.0)
                elif trend_score >= 7:
                    dynamic_take_profit = getattr(trading_config, 'long_take_profit_trend_7_8', 10.0)
                elif trend_score >= 5:
                    dynamic_take_profit = getattr(trading_config, 'long_take_profit_trend_5_6', 8.0)
                else:
                    dynamic_take_profit = getattr(trading_config, 'long_take_profit_trend_default', 6.0)
            else:
                dynamic_take_profit = abs(pos.take_profit_percent)
            
            threshold_percent = getattr(trading_config, 'long_small_profit_reduce_threshold_percent', 50.0)
            position_threshold = getattr(trading_config, 'long_small_profit_reduce_position_threshold', 15.0)
            reduce_ratio = getattr(trading_config, 'long_small_profit_reduce_ratio', 50.0)
            
            if pnl_percent >= dynamic_take_profit * (threshold_percent / 100) and position_percent > position_threshold:
                pos.small_profit_reduced = True
                return {
                    "should_sell": True,
                    "sell_percent": reduce_ratio / 100,
                    "reason": f"小盈减仓！盈利{pnl_percent:.2f}%≥{dynamic_take_profit * (threshold_percent / 100):.2f}%({threshold_percent:.0f}%止盈线)且仓位{position_percent:.1f}%>{position_threshold}%",
                    "is_small_profit_reduce": True
                }
        
        # 2. 超仓减仓：仓位>30%强制减仓
        if (trading_config and getattr(trading_config, 'over_position_reduce_enabled', True) and
            not pos.over_position_reduced):
            over_threshold = getattr(trading_config, 'over_position_reduce_threshold', 30.0)
            target_percent = getattr(trading_config, 'over_position_reduce_target', 20.0)
            
            if position_percent > over_threshold:
                # 检查智能豁免期
                exemption_enabled = getattr(trading_config, 'over_position_exemption_enabled', True)
                if exemption_enabled and pos.over_position_exemption_start:
                    exemption_start = datetime.fromisoformat(pos.over_position_exemption_start)
                    elapsed_minutes = (datetime.now(BEIJING_TZ) - exemption_start).total_seconds() / 60
                    
                    # 根据盈亏确定豁免时长
                    if pnl_percent < getattr(trading_config, 'exemption_loss_high_threshold', -1.0):
                        exemption_minutes = getattr(trading_config, 'exemption_loss_high_minutes', 60)
                    elif pnl_percent < getattr(trading_config, 'exemption_loss_medium_threshold', 0.0):
                        exemption_minutes = getattr(trading_config, 'exemption_loss_medium_minutes', 45)
                    else:
                        exemption_minutes = getattr(trading_config, 'exemption_profit_minutes', 30)
                    
                    if elapsed_minutes < exemption_minutes:
                        return {
                            "should_sell": False,
                            "reason": f"超仓但豁免期内({elapsed_minutes:.0f}/{exemption_minutes}分钟)，盈亏{pnl_percent:.2f}%，继续持有",
                            "sell_percent": 0,
                            "is_exemption": True
                        }
                
                # 计算减仓比例
                reduce_percent = min(over_threshold - target_percent, (position_percent - target_percent))
                actual_reduce_ratio = reduce_percent / position_percent
                pos.over_position_reduced = True
                
                return {
                    "should_sell": True,
                    "sell_percent": actual_reduce_ratio,
                    "reason": f"超仓减仓！仓位{position_percent:.1f}%>{over_threshold}%，减仓至{target_percent}%",
                    "is_over_position_reduce": True
                }
        
        # 3. 趋势变盘减仓：检测趋势反转快速清仓
        if (trading_config and getattr(trading_config, 'trend_reversal_reduce_enabled', True) and
            not pos.trend_reversal_reduced and pnl_percent > 0):
            reversal_from = getattr(trading_config, 'trend_reversal_from_score', 8)
            reversal_to = getattr(trading_config, 'trend_reversal_to_score', 5)
            reversal_min_periods = getattr(trading_config, 'trend_reversal_min_periods', 3)
            reversal_reduce_percent = getattr(trading_config, 'trend_reversal_reduce_percent', 50.0)
            
            # 检查趋势是否从高分降至低分（需要维护趋势历史，这里简化处理）
            if hasattr(pos, 'trend_history'):
                high_count = sum(1 for ts in pos.trend_history if ts >= reversal_from)
                low_count = sum(1 for ts in pos.trend_history if ts <= reversal_to)
                
                if high_count >= reversal_min_periods and trend_score <= reversal_to:
                    pos.trend_reversal_reduced = True
                    return {
                        "should_sell": True,
                        "sell_percent": reversal_reduce_percent / 100,
                        "reason": f"趋势变盘减仓！趋势从{reversal_from}+分降至{reversal_to}分以下，快速保护利润",
                        "is_trend_reversal": True
                    }
        
        if pos.trailing_activated and current_price <= pos.trailing_stop_price:
            return {
                "should_sell": True,
                "sell_percent": 1.0,
                "reason": f"移动止损触发: 价格{current_price} <= 止损价{pos.trailing_stop_price:.4f}"
            }

        return {
            "should_sell": False,
            "reason": "",
            "sell_percent": 0
        }

    def get_short_positions(self) -> List[Dict]:
        """获取空单持仓列表"""
        return [
            {
                "coin": pos.coin,
                "amount": pos.amount,
                "entry_price": pos.entry_price,
                "usdt_value": pos.usdt_value,
                "entry_time": pos.entry_time,
                "stop_loss_percent": pos.stop_loss_percent,
                "take_profit_percent": pos.take_profit_percent,
                "is_simulation": True,
                "leverage": pos.leverage,
                "is_swap": pos.is_swap if hasattr(pos, 'is_swap') else False
            } for pos in self.short_positions.values()
        ]

    def check_short_cover_signals(self, coin: str, current_price: float, 
                                   trading_config=None, volatility: float = 0.0, 
                                   turnover_24h: float = 0.0, trend_score: float = 5.0,
                                   pyramid_time_protection_minutes: int = 60) -> Dict:
        """
        检查空单平仓信号
        trading_config: 交易引擎配置，用于与实盘保持一致
        volatility: 波动率，用于动态止损止盈计算
        turnover_24h: 24h成交额，用于动态止损止盈计算
        trend_score: 趋势评分
        """
        from app.core.config import settings

        if coin not in self.short_positions:
            return {"should_cover": False, "reason": ""}

        pos = self.short_positions[coin]

        leverage = pos.leverage if hasattr(pos, 'leverage') and pos.leverage else 1.0
        pnl_percent = (pos.entry_price - current_price) / pos.entry_price * 100 * leverage

        # 持仓时间保护：刚加仓后禁止止损/平仓（对齐 ai_trading_bot.js）
        pyramid_add_time = getattr(pos, 'pyramid_add_time', None)
        time_protection_minutes = pyramid_time_protection_minutes
        if pyramid_add_time:
            from datetime import datetime, timezone, timedelta
            BEIJING_TZ = timezone(timedelta(hours=8))
            holding_minutes = (datetime.now(BEIJING_TZ) - pyramid_add_time).total_seconds() / 60
            logger.info(f"[时间保护检查] {coin} 做空金字塔加仓时间: {pyramid_add_time}, 已持仓: {holding_minutes:.1f}分钟, 保护期: {time_protection_minutes}分钟")
            if holding_minutes < time_protection_minutes:
                logger.info(f"[时间保护生效] {coin} 做空金字塔加仓后{holding_minutes:.1f}分钟，时间保护未到期({time_protection_minutes}分钟)，禁止平仓")
                return {
                    "should_cover": False,
                    "reason": f"做空金字塔加仓后{holding_minutes:.1f}分钟，时间保护未到期({time_protection_minutes}分钟)，禁止平仓"
                }
        else:
            logger.debug(f"[时间保护检查] {coin} 无金字塔加仓时间记录，跳过时间保护")

        if getattr(trading_config, 'dynamic_bands_enabled', False):
            volatility_factor = min(2.0, max(0.5, volatility / 3)) if volatility > 0 else 1.0
            if turnover_24h > 1000000000:
                market_cap_factor = 1.2
            elif turnover_24h > 100000000:
                market_cap_factor = 1.0
            else:
                market_cap_factor = 0.6

            base_stop_loss = getattr(trading_config, 'short_stop_loss_percent', 1.5)
            base_take_profit = getattr(trading_config, 'short_take_profit_percent', 3.0)
            trend_factor = 1.2 if trend_score <= 3 else (1.0 if trend_score <= 5 else 0.8)
            dynamic_stop_loss = base_stop_loss * volatility_factor * market_cap_factor * trend_factor
            dynamic_take_profit = base_take_profit * volatility_factor * market_cap_factor * trend_factor

            dynamic_stop_loss = max(1.0, min(8.0, dynamic_stop_loss))
            dynamic_take_profit = max(2.0, min(15.0, dynamic_take_profit))

            if pnl_percent <= -dynamic_stop_loss:
                return {
                    "should_cover": True,
                    "cover_percent": 1.0,
                    "reason": f"空单动态止损: 亏损{-pnl_percent:.2f}% >= {dynamic_stop_loss:.2f}%"
                }

            if pnl_percent >= dynamic_take_profit:
                return {
                    "should_cover": True,
                    "cover_percent": 1.0,
                    "reason": f"空单动态止盈: 盈利{pnl_percent:.2f}% >= {dynamic_take_profit:.2f}%"
                }

            if pnl_percent >= dynamic_take_profit * 0.5:
                return {
                    "should_cover": True,
                    "cover_percent": 0.5,
                    "reason": f"空单部分止盈: 盈利{pnl_percent:.2f}% >= {dynamic_take_profit * 0.5:.2f}%"
                }

        else:
            short_smart_stop_loss_enabled = getattr(trading_config, 'short_smart_stop_loss_enabled', True) if trading_config else True
            if short_smart_stop_loss_enabled:
                if trend_score <= 2:
                    short_stop_loss = abs(getattr(trading_config, 'short_stop_loss_trend_0_2', 3.0))
                elif trend_score <= 4:
                    short_stop_loss = abs(getattr(trading_config, 'short_stop_loss_trend_3_4', 2.0))
                else:
                    short_stop_loss = abs(getattr(trading_config, 'short_stop_loss_trend_default', 1.5))
            else:
                short_stop_loss = abs(pos.stop_loss_percent)

            if pnl_percent <= -short_stop_loss:
                return {
                    "should_cover": True,
                    "cover_percent": 1.0,
                    "reason": f"空单止损: 亏损{-pnl_percent:.2f}% >= {short_stop_loss:.2f}%"
                }

            short_dynamic_take_profit_enabled = getattr(trading_config, 'short_dynamic_take_profit_enabled', True) if trading_config else True
            if short_dynamic_take_profit_enabled:
                if trend_score <= 1:
                    short_take_profit = getattr(trading_config, 'short_take_profit_trend_0_1', 15.0)
                elif trend_score <= 3:
                    short_take_profit = getattr(trading_config, 'short_take_profit_trend_2_3', 10.0)
                elif trend_score == 4:
                    short_take_profit = getattr(trading_config, 'short_take_profit_trend_4', 8.0)
                else:
                    short_take_profit = getattr(trading_config, 'short_take_profit_trend_default', 6.0)
            else:
                short_take_profit = abs(pos.take_profit_percent)

            if pnl_percent >= short_take_profit:
                return {
                    "should_cover": True,
                    "cover_percent": 1.0,
                    "reason": f"空单止盈: 盈利{pnl_percent:.2f}% >= {short_take_profit:.2f}%"
                }

            if pnl_percent >= short_take_profit * 0.5:
                return {
                    "should_cover": True,
                    "cover_percent": 0.5,
                    "reason": f"空单部分止盈: 盈利{pnl_percent:.2f}% >= {short_take_profit * 0.5:.2f}%"
                }

        return {"should_cover": False, "reason": ""}

    def cover_short(self, coin: str, price: float, cover_percent: float = 1.0,
                   reason: str = "") -> Optional[SimulatedTrade]:
        """平空单"""
        if coin not in self.short_positions:
            return None

        pos = self.short_positions[coin]
        cover_amount = pos.amount * cover_percent
        cover_value = cover_amount * price

        # 空单盈亏计算（考虑杠杆）
        leverage = pos.leverage if hasattr(pos, 'leverage') and pos.leverage else 1.0
        pnl = (pos.entry_price - price) * cover_amount * leverage
        pnl_percent = (pos.entry_price - price) / pos.entry_price * 100 * leverage

        self.total_pnl += pnl
        self.available_balance += pos.usdt_value * cover_percent + pnl

        if pnl >= 0:
            self.win_count += 1
        else:
            self.loss_count += 1

        trade = SimulatedTrade(
            coin=coin,
            action="buy_short",  # 平空单
            price=price,
            amount=cover_amount,
            usdt_value=cover_value,
            pnl=pnl,
            pnl_percent=pnl_percent,
            reason=reason,
            timestamp=datetime.now(BEIJING_TZ).isoformat(),
            leverage=leverage
        )
        self.trades.append(trade)

        if cover_percent >= 1.0:
            del self.short_positions[coin]
        else:
            pos.amount -= cover_amount
            pos.usdt_value -= pos.usdt_value * cover_percent

        self._save_positions()
        self._save_trades()
        return trade

    def get_positions(self) -> List[Dict]:
        if not self.positions:
            self._load_data()
        
        result = [
            {
                "coin": pos.coin,
                "amount": pos.amount,
                "entry_price": pos.entry_price,
                "usdt_value": pos.usdt_value,
                "entry_time": pos.entry_time,
                "stop_loss_percent": pos.stop_loss_percent,
                "take_profit_percent": pos.take_profit_percent,
                "highest_price": pos.highest_price,
                "pyramid_layers": pos.pyramid_layers,
                "pyramid_base_price": pos.pyramid_base_price,
                "is_simulation": True,
                "leverage": pos.leverage,
                "is_swap": pos.is_swap if hasattr(pos, 'is_swap') else False
            } for pos in self.positions.values()
        ]
        return result
    
    def get_stats(self) -> Dict:
        total_trades = self.win_count + self.loss_count
        win_rate = self.win_count / total_trades * 100 if total_trades > 0 else 0

        return {
            "total_pnl": self.total_pnl,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "position_count": len(self.positions),
            "short_position_count": len(self.short_positions),
            "initial_balance": self.initial_balance,
            "available_balance": self.available_balance
        }
    
    def get_recent_trades(self, limit: int = 50) -> List[Dict]:
        return [
            {
                "coin": t.coin,
                "action": t.action,
                "price": t.price,
                "amount": t.amount,
                "usdt_value": t.usdt_value,
                "pnl": t.pnl,
                "pnl_percent": t.pnl_percent,
                "reason": t.reason,
                "timestamp": t.timestamp,
                "is_simulation": True,
                "leverage": t.leverage,
                "strategy": t.strategy,
                "is_swap": t.is_swap if hasattr(t, 'is_swap') else False
            } for t in self.trades[-limit:]
        ]
    
    def clear_all(self):
        self.positions.clear()
        self.short_positions.clear()
        self.trades.clear()
        self.total_pnl = 0.0
        self.win_count = 0
        self.loss_count = 0
        self.available_balance = self.initial_balance
        self._save_positions()
        self._save_trades()

        # 同时清空交易统计中的日交易记录
        from app.services.trade_stats import trade_stats
        trade_stats.trade_log.trades.clear()
        trade_stats.trade_log.daily_volume = 0.0
        trade_stats.trade_log.daily_trade_count = 0
        trade_stats.trade_log.last_buy_time.clear()
        trade_stats._save_trade_log()
        
        # 清空 trading_engine 的日交易计数
        from app.services.trading_engine import trading_engine
        trading_engine.daily_trade_count.clear()
    
    def reset_balance(self, initial_balance: float = 1000.0):
        self.initial_balance = initial_balance
        self.available_balance = initial_balance
        self._save_positions()

    def calculate_pyramid_buy_amount(self, coin: str, current_price: float, trend_score: float,
                                      base_amount: float = None, timezone_ratio: tuple = None) -> Dict:
        """
        计算金字塔加仓金额
        返回: {"should_add": bool, "amount": float, "layer": int, "reason": str}
        
        Args:
            coin: 币种
            current_price: 当前价格
            trend_score: 趋势评分
            base_amount: 基础金额（可选，默认使用 settings.PYRAMID_BASE_AMOUNT）
            timezone_ratio: 时区比例元组 (ratio_min, ratio_max)（可选）
        """
        from app.core.config import settings
        import random

        if not settings.PYRAMID_ENABLED:
            return {"should_add": False, "amount": 0, "layer": 0, "reason": "金字塔加仓未启用"}

        if coin not in self.positions:
            return {"should_add": False, "amount": 0, "layer": 0, "reason": "无持仓"}

        pos = self.positions[coin]

        # 1. 检查是否已达最大加仓层数
        if pos.pyramid_layers >= settings.PYRAMID_MAX_LAYERS:
            return {"should_add": False, "amount": 0, "layer": 0, "reason": f"已达最大加仓层数({settings.PYRAMID_MAX_LAYERS}层)"}

        # 2. 计算当前盈亏
        pnl_percent = (current_price - pos.entry_price) / pos.entry_price * 100

        # 3. 只有亏损达到设定阈值以上才考虑加仓
        if pnl_percent > settings.PYRAMID_DROP_THRESHOLD:
            return {"should_add": False, "amount": 0, "layer": 0, "reason": f"亏损不足{abs(settings.PYRAMID_DROP_THRESHOLD)}%({pnl_percent:.2f}%)，不符合加仓条件"}

        # 4. 趋势评分必须达标
        if trend_score < settings.PYRAMID_MIN_TREND_SCORE:
            return {"should_add": False, "amount": 0, "layer": 0, "reason": f"趋势评分{trend_score}/10不足{settings.PYRAMID_MIN_TREND_SCORE}分，风险较大"}

        # 5. 计算加仓价格条件（金字塔：每层比基准价格下跌设定百分比）
        # 基准价格：首次开仓价
        base_price = pos.pyramid_base_price if pos.pyramid_base_price > 0 else pos.entry_price
        layer_target_percent = settings.PYRAMID_DROP_PER_LAYER * (pos.pyramid_layers + 1)  # 第1层-10%，第2层-20%，第3层-30%
        layer_target_price = base_price * (1 + layer_target_percent / 100)

        # 检查是否达到该层加仓价格
        if current_price > layer_target_price:
            return {
                "should_add": False,
                "amount": 0,
                "layer": 0,
                "reason": f"当前价格${current_price:.4f} > 第{pos.pyramid_layers+1}层加仓价${layer_target_price:.4f}"
            }

        # 6. 计算该层加仓金额（基础金额 × 时区比例 × 层比例）
        layer_ratios = [float(x) for x in settings.PYRAMID_LAYER_RATIOS.split(",")]
        layer_ratio = layer_ratios[min(pos.pyramid_layers, len(layer_ratios) - 1)]
        
        # 使用传入的基础金额或默认配置
        pyramid_base = base_amount if base_amount is not None else settings.PYRAMID_BASE_AMOUNT
        
        # 应用时区感知（如果提供了时区比例）
        if timezone_ratio and len(timezone_ratio) >= 2:
            ratio_min, ratio_max = timezone_ratio[0], timezone_ratio[1]
            # 金字塔加仓使用比例范围的较高值（更激进）
            tz_ratio = random.uniform(ratio_min, ratio_max)
            add_amount = pyramid_base * tz_ratio * layer_ratio
        else:
            add_amount = pyramid_base * layer_ratio

        # 7. 检查可用余额
        if add_amount > self.available_balance:
            return {"should_add": False, "amount": 0, "layer": 0, "reason": f"余额不足（需要${add_amount:.2f}）"}

        # 8. 检查持仓占比（单一币种不超过设定比例）
        total_value = pos.usdt_value
        if total_value + add_amount > self.initial_balance * (settings.PYRAMID_MAX_POSITION_PERCENT / 100):
            return {"should_add": False, "amount": 0, "layer": 0, "reason": f"持仓占比已达{settings.PYRAMID_MAX_POSITION_PERCENT}%上限"}

        return {
            "should_add": True,
            "amount": add_amount,
            "layer": pos.pyramid_layers + 1,
            "reason": f"第{pos.pyramid_layers+1}层金字塔加仓：亏损{pnl_percent:.2f}%，趋势{trend_score}/10良好"
        }

    def pyramid_add(self, coin: str, price: float, usdt_value: float, layer: int, reason: str = "") -> bool:
        """
        执行金字塔加仓
        """
        if coin not in self.positions:
            return False

        if usdt_value > self.available_balance:
            return False

        pos = self.positions[coin]
        amount = usdt_value / price
        self.available_balance -= usdt_value

        # 更新持仓信息
        total_amount = pos.amount + amount
        total_value = pos.usdt_value + usdt_value
        avg_price = total_value / total_amount

        pos.entry_price = avg_price
        pos.amount = total_amount
        pos.usdt_value = total_value
        pos.pyramid_layers = layer
        pos.pyramid_layer_prices.append(price)
        
        # 记录加仓时间，用于时间保护（对齐 ai_trading_bot.js）
        pos.pyramid_add_time = datetime.now(BEIJING_TZ)

        # 记录交易
        trade = SimulatedTrade(
            coin=coin,
            action="buy",
            price=price,
            amount=amount,
            usdt_value=usdt_value,
            reason=f"金字塔加仓第{layer}层 - {reason}",
            timestamp=datetime.now(BEIJING_TZ).isoformat(),
            leverage=pos.leverage if hasattr(pos, 'leverage') else 1.0,
            is_swap=pos.is_swap if hasattr(pos, 'is_swap') else False
        )
        self.trades.append(trade)

        self._save_positions()
        self._save_trades()

        return True

    def reset_pyramid_layers(self, coin: str) -> bool:
        """
        重置指定币种的金字塔层级
        在止损后调用，以便下次买入时重新计算
        """
        if coin not in self.positions:
            return False
        
        pos = self.positions[coin]
        pos.pyramid_layers = 0
        pos.pyramid_layer_prices = []
        pos.pyramid_base_price = 0.0
        
        self._save_positions()
        return True

    def calculate_short_pyramid_add_amount(self, coin: str, current_price: float, trend_score: float = 5.0,
                                          config = None, base_amount: float = None, timezone_ratio: tuple = None) -> Dict:
        """
        计算做空金字塔加仓条件（价格向上涨时加仓摊薄成本）
        做空金字塔逻辑：价格上涨时分层加仓
        
        Args:
            coin: 币种
            current_price: 当前价格
            trend_score: 趋势评分
            config: 配置对象（可选）
            base_amount: 基础金额（可选，默认使用配置值）
            timezone_ratio: 时区比例元组 (ratio_min, ratio_max)（可选）
        """
        from app.core.config import settings
        import random

        if coin not in self.short_positions:
            return {"should_add": False, "amount": 0, "layer": 0, "reason": "无做空持仓"}

        pos = self.short_positions[coin]

        if not hasattr(pos, 'short_pyramid_layers'):
            pos.short_pyramid_layers = 0
            pos.short_pyramid_layer_prices = []
            pos.short_pyramid_base_price = pos.entry_price

        if not hasattr(settings, 'PYRAMID_MAX_LAYERS'):
            settings.PYRAMID_MAX_LAYERS = 5
        if not hasattr(settings, 'PYRAMID_DROP_THRESHOLD'):
            settings.PYRAMID_DROP_THRESHOLD = -3.0
        if not hasattr(settings, 'PYRAMID_MIN_TREND_SCORE'):
            settings.PYRAMID_MIN_TREND_SCORE = 7
        if not hasattr(settings, 'PYRAMID_DROP_PER_LAYER'):
            settings.PYRAMID_DROP_PER_LAYER = 3
        if not hasattr(settings, 'PYRAMID_BASE_AMOUNT'):
            settings.PYRAMID_BASE_AMOUNT = 10
        if not hasattr(settings, 'PYRAMID_LAYER_RATIOS'):
            settings.PYRAMID_LAYER_RATIOS = "1.0,0.6,0.35,0.2"
        if not hasattr(settings, 'PYRAMID_MAX_POSITION_PERCENT'):
            settings.PYRAMID_MAX_POSITION_PERCENT = 30

        max_layers = getattr(settings, 'PYRAMID_MAX_LAYERS', 5)
        profit_threshold = getattr(settings, 'PYRAMID_DROP_THRESHOLD', -3.0)
        max_trend_score = getattr(settings, 'PYRAMID_MIN_TREND_SCORE', 7)
        drop_per_layer = getattr(settings, 'PYRAMID_DROP_PER_LAYER', 3)
        default_base_amount = getattr(settings, 'PYRAMID_BASE_AMOUNT', 10)
        layer_ratios = getattr(settings, 'PYRAMID_LAYER_RATIOS', "1.0,0.6,0.35,0.2")
        max_position_percent = getattr(settings, 'PYRAMID_MAX_POSITION_PERCENT', 30)

        if config:
            max_layers = getattr(config, 'short_pyramid_max_layers', max_layers)
            profit_threshold = getattr(config, 'short_pyramid_drop_threshold', getattr(config, 'short_pyramid_profit_threshold', profit_threshold))
            max_trend_score = getattr(config, 'short_pyramid_max_trend_score', max_trend_score)
            layer_ratios = getattr(config, 'short_pyramid_layer_ratios', layer_ratios)
            # 使用传入的基础金额或配置值
            if base_amount is None:
                base_amount = getattr(config, 'short_pyramid_base_amount', default_base_amount)
        else:
            # 使用传入的基础金额或默认值
            if base_amount is None:
                base_amount = default_base_amount

        if pos.short_pyramid_layers >= max_layers:
            return {"should_add": False, "amount": 0, "layer": 0, "reason": f"已达做空最大加仓层数({max_layers}层)"}

        leverage = pos.leverage if hasattr(pos, 'leverage') and pos.leverage else 1.0
        pnl_percent = (pos.entry_price - current_price) / pos.entry_price * 100 * leverage

        if pnl_percent < abs(profit_threshold):
            return {"should_add": False, "amount": 0, "layer": 0, "reason": f"做空盈利不足{abs(profit_threshold)}%({pnl_percent:.2f}%)，不符合加仓条件"}

        if trend_score > max_trend_score:
            return {"should_add": False, "amount": 0, "layer": 0, "reason": f"做空趋势评分{trend_score}/10过高({trend_score}>{max_trend_score})，上涨趋势过强"}

        base_price = pos.short_pyramid_base_price if hasattr(pos, 'short_pyramid_base_price') and pos.short_pyramid_base_price > 0 else pos.entry_price
        layer_target_percent = drop_per_layer * (pos.short_pyramid_layers + 1)
        layer_target_price = base_price * (1 + layer_target_percent / 100)

        if current_price < layer_target_price:
            return {
                "should_add": False,
                "amount": 0,
                "layer": 0,
                "reason": f"当前做空价格${current_price:.4f} < 第{pos.short_pyramid_layers+1}层加仓触发价${layer_target_price:.4f}"
            }

        ratios = [float(x) for x in layer_ratios.split(",")]
        layer_ratio = ratios[min(pos.short_pyramid_layers, len(ratios) - 1)]
        
        # 应用时区感知（如果提供了时区比例）
        if timezone_ratio and len(timezone_ratio) >= 2:
            ratio_min, ratio_max = timezone_ratio[0], timezone_ratio[1]
            # 金字塔加仓使用比例范围的较高值（更激进）
            tz_ratio = random.uniform(ratio_min, ratio_max)
            add_amount = base_amount * tz_ratio * layer_ratio
        else:
            add_amount = base_amount * layer_ratio

        if add_amount > self.available_balance:
            return {"should_add": False, "amount": 0, "layer": 0, "reason": f"做空余额不足（需要${add_amount:.2f}）"}

        total_value = pos.usdt_value
        if total_value + add_amount > self.initial_balance * (max_position_percent / 100):
            return {"should_add": False, "amount": 0, "layer": 0, "reason": f"做空持仓占比已达{max_position_percent}%上限"}

        return {
            "should_add": True,
            "amount": add_amount,
            "layer": pos.short_pyramid_layers + 1,
            "reason": f"第{pos.short_pyramid_layers+1}层做空金字塔加仓：价格上涨触发，趋势{trend_score}/10"
        }

    def short_pyramid_add(self, coin: str, price: float, usdt_value: float, layer: int, reason: str = "") -> bool:
        """
        执行做空金字塔加仓
        """
        if coin not in self.short_positions:
            return False

        if usdt_value > self.available_balance:
            return False

        pos = self.short_positions[coin]
        amount = usdt_value / price
        self.available_balance -= usdt_value

        total_amount = pos.amount + amount
        total_value = pos.usdt_value + usdt_value
        avg_price = total_value / total_amount

        pos.entry_price = avg_price
        pos.amount = total_amount
        pos.usdt_value = total_value
        
        if not hasattr(pos, 'short_pyramid_layers'):
            pos.short_pyramid_layers = 0
            pos.short_pyramid_layer_prices = []
        pos.short_pyramid_layers = layer
        pos.short_pyramid_layer_prices.append(price)
        pos.short_pyramid_base_price = getattr(pos, 'short_pyramid_base_price', pos.entry_price)
        
        # 记录加仓时间，用于时间保护（对齐 ai_trading_bot.js）
        pos.pyramid_add_time = datetime.now(BEIJING_TZ)

        trade = SimulatedTrade(
            coin=coin,
            action="sell_short",
            price=price,
            amount=amount,
            usdt_value=usdt_value,
            reason=f"做空金字塔加仓第{layer}层 - {reason}",
            timestamp=datetime.now(BEIJING_TZ).isoformat(),
            leverage=pos.leverage if hasattr(pos, 'leverage') else 1.0,
            is_swap=pos.is_swap if hasattr(pos, 'is_swap') else False
        )
        self.trades.append(trade)

        self._save_positions()
        self._save_trades()

        return True

    def reset_short_pyramid_layers(self, coin: str) -> bool:
        """
        重置指定币种的做空金字塔层级
        在平空后调用，以便下次做空时重新计算
        """
        if coin not in self.short_positions:
            return False
        
        pos = self.short_positions[coin]
        pos.short_pyramid_layers = 0
        pos.short_pyramid_layer_prices = []
        pos.short_pyramid_base_price = 0.0
        
        self._save_positions()
        return True


simulation_manager = SimulationManager()
