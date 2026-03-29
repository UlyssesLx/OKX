from pydantic import BaseModel
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from loguru import logger
import json
import os
import random

from app.core.okx_client import OKXClient

BEIJING_TZ = timezone(timedelta(hours=8))


def get_timezone_position_size() -> Tuple[float, float, int, int]:
    """
    根据当前时区返回仓位比例范围
    返回: (ratio_min, ratio_max, hold_time_min, hold_time_max)
    参考币市麻雀战法时区配置
    """
    hour = datetime.now(BEIJING_TZ).hour

    # 6个时段配置（币市麻雀战法）
    if hour >= 0 and hour < 4:
        # 亚洲尾盘 - 低活跃: $5-8 (基于$15基础)
        return (0.33, 0.53, 30, 60)
    elif hour >= 4 and hour < 8:
        # 欧美交接 - 中低活跃: $8-10
        return (0.53, 0.67, 20, 40)
    elif hour >= 8 and hour < 12:
        # 亚洲早盘 - 高活跃: $12-15
        return (0.80, 1.00, 15, 60)
    elif hour >= 12 and hour < 16:
        # 亚洲午盘 - 中等活跃: $10-12
        return (0.67, 0.80, 20, 50)
    elif hour >= 16 and hour < 20:
        # 欧洲早盘 - 高活跃: $12-15
        return (0.80, 1.00, 15, 60)
    else:
        # 美国早盘 - 高活跃: $12-15
        return (0.80, 1.00, 10, 45)


def get_position_size_by_timezone(base_size: float, timezone_adjusted: bool = True) -> float:
    """
    根据时区获取调整后的仓位大小
    
    Args:
        base_size: 基础仓位大小
        timezone_adjusted: 是否启用时区调整
    
    Returns:
        调整后的仓位大小
    """
    if not timezone_adjusted:
        return base_size
    
    ratio_min, ratio_max, _, _ = get_timezone_position_size()
    # 在范围内随机选择，新仓用较低比例
    adjusted_size = round(random.uniform(base_size * ratio_min, base_size * ratio_max), 2)
    return adjusted_size


class ShortTermConfig(BaseModel):
    # 选股门槛 - 完全对齐 crypto-trading-bot-master/strategy-short-term.js
    min_trend_score: int = 6           # 趋势评分 >= 6分
    max_trend_score: int = 10          # 趋势评分 <= 10分
    rsi_min: int = 30                  # RSI >= 30
    rsi_max: int = 70                  # RSI <= 70
    min_volume_ratio: float = 0.8        # 成交量 >= 0.8x
    max_24h_change: float = 8.0         # 24h涨跌 <= +8%
    min_24h_change: float = -5.0        # 24h涨跌 >= -5%
    min_market_trend: int = 4           # 大盘趋势 >= 4分

    # 仓位管理 - 完全对齐 crypto-trading-bot-master/strategy-short-term.js
    position_size: float = 40.0        # 单笔金额 $40
    max_positions: int = 3              # 最大持仓3个
    max_position_percent: float = 15.0  # 单个币种最大占比15%
    
    # 时区感知配置
    timezone_adjusted_position: bool = True  # 是否启用时区感知调整仓位

    # 止盈止损 - 完全对齐 crypto-trading-bot-master/strategy-short-term.js
    stop_loss: float = -1.5             # 止损 -1.5%
    take_profit_1: float = 1.0          # 第一止盈 +1%
    take_profit_2: float = 2.0          # 第二止盈 +2%
    time_stop: int = 48                 # 时间止损 48小时

    # 交易频率控制 - 完全对齐 crypto-trading-bot-master/strategy-short-term.js
    min_trade_interval: int = 2        # 最小交易间隔2小时
    max_daily_trades: int = 5          # 每日最大交易5笔

    # 波动率筛选 - 完全对齐 crypto-trading-bot-master/strategy-short-term.js
    min_volatility: float = 0.3         # 最小波动率0.3%
    max_volatility: float = 5.0         # 最大波动率5%


class ShortTermShortConfig(BaseModel):
    # 选股门槛 - 做空策略（做多策略的镜像反向）
    min_bearish_score: int = 7          # 看跌评分 >= 7分（做空需要高看跌）
    max_bearish_score: int = 10        # 看跌评分 <= 10分
    min_trend_score: int = 0           # 趋势评分 >= 0分（做空不需要高趋势）
    max_trend_score: int = 4           # 趋势评分 <= 4分（低趋势才做空）
    rsi_min: int = 30                  # RSI >= 30（适中，与做多一致）
    rsi_max: int = 70                  # RSI <= 70（适中，与做多一致）
    min_volume_ratio: float = 0.8        # 成交量 >= 0.8x（与做多一致）
    max_24h_change: float = 5.0         # 24h涨跌 <= +5%（允许最大上涨+5%）
    min_24h_change: float = -8.0        # 24h涨跌 >= -8%（允许最大下跌-8%）
    max_market_trend: int = 4           # 大盘趋势 <= 4分（不能太高）

    # 仓位管理 - 与做多一致
    position_size: float = 40.0        # 单笔金额 $40
    max_positions: int = 3              # 最大持仓3个
    max_position_percent: float = 15.0  # 单个币种最大占比15%
    
    # 时区感知配置
    timezone_adjusted_position: bool = True  # 是否启用时区感知调整仓位

    # 止盈止损 - 与做多一致（价格反向）
    stop_loss: float = -1.5             # 止损 -1.5%（价格上涨触发）
    take_profit_1: float = 1.0          # 第一止盈 +1%（价格下跌）
    take_profit_2: float = 2.0          # 第二止盈 +2%（价格下跌）
    time_stop: int = 48                 # 时间止损 48小时

    # 交易频率控制 - 与做多一致
    min_trade_interval: int = 2        # 最小交易间隔2小时
    max_daily_trades: int = 5          # 每日最大交易5笔

    # 波动率筛选 - 与做多一致
    min_volatility: float = 0.3         # 最小波动率0.3%
    max_volatility: float = 5.0         # 最大波动率5%


@dataclass
class BuyConditionResult:
    passed: bool
    reason: str


@dataclass
class ExitResult:
    should_exit: bool
    action: Optional[str] = None
    reason: str = ""


@dataclass
class ShortTermPosition:
    coin: str
    entry_price: float
    amount: float
    entry_time: datetime
    partial_exit: bool = False


@dataclass
class ShortTermShortPosition:
    """做空持仓"""
    coin: str
    entry_price: float
    amount: float
    entry_time: datetime
    partial_exit: bool = False


@dataclass
class ShortTermTrade:
    time: str
    coin: str
    action: str
    price: float
    amount: float
    reason: str


def check_short_term_buy_condition(
    config: ShortTermConfig,
    trend_score: int,
    rsi: float,
    volume_ratio: float,
    price_change_24h: float,
    market_trend: int,
    volatility: float
) -> BuyConditionResult:
    if trend_score < config.min_trend_score or trend_score > config.max_trend_score:
        return BuyConditionResult(
            passed=False,
            reason=f"趋势评分{trend_score}分，需要{config.min_trend_score}-{config.max_trend_score}分"
        )

    if rsi < config.rsi_min or rsi > config.rsi_max:
        return BuyConditionResult(
            passed=False,
            reason=f"RSI {rsi}，需要{config.rsi_min}-{config.rsi_max}"
        )

    if volume_ratio < config.min_volume_ratio:
        return BuyConditionResult(
            passed=False,
            reason=f"成交量{volume_ratio}x，需要>={config.min_volume_ratio}x"
        )

    if price_change_24h < config.min_24h_change or price_change_24h > config.max_24h_change:
        return BuyConditionResult(
            passed=False,
            reason=f"24h涨跌{price_change_24h}%，需要{config.min_24h_change}% ~ {config.max_24h_change}%"
        )

    if market_trend < config.min_market_trend:
        return BuyConditionResult(
            passed=False,
            reason=f"大盘趋势{market_trend}分，需要>={config.min_market_trend}分"
        )

    if volatility < config.min_volatility or volatility > config.max_volatility:
        return BuyConditionResult(
            passed=False,
            reason=f"波动率{volatility}%，需要{config.min_volatility}% ~ {config.max_volatility}%"
        )

    return BuyConditionResult(passed=True, reason="满足所有短线买入条件")


def check_short_term_short_condition(
    config: ShortTermShortConfig,
    bearish_score: int,
    trend_score: int,
    rsi: float,
    volume_ratio: float,
    price_change_24h: float,
    market_trend: int,
    volatility: float
) -> BuyConditionResult:
    """
    做空条件检查（做多策略的镜像反向）

    核心思想：
    - 看跌评分高：7-10分（与做多的看涨评分6-10分镜像）
    - 趋势差：趋势评分 0-4分（做多要求 6-10分）
    - RSI适中：30-70（与做多一致）
    - 允许跌多涨少：24h涨跌 -8% ~ +5%（做多允许 -5% ~ +8%）
    - 成交量充足：与做多一致
    - 波动率：与做多一致
    - 大盘趋势上限：≤4分（不能太高，逆势做空风险大）

    24h涨跌逻辑说明：
    - 做多：允许24h下跌-5%（抄底），允许上涨+8%（追涨）
    - 做空：允许24h下跌-8%（更大的下跌容忍度），限制上涨+5%（限制追高）
    """
    # 看跌评分检查（与做多的看涨评分镜像）
    if bearish_score < config.min_bearish_score or bearish_score > config.max_bearish_score:
        return BuyConditionResult(
            passed=False,
            reason=f"看跌评分{bearish_score}分，做空需要{config.min_bearish_score}-{config.max_bearish_score}分"
        )

    if trend_score < config.min_trend_score or trend_score > config.max_trend_score:
        return BuyConditionResult(
            passed=False,
            reason=f"趋势评分{trend_score}分，做空需要{config.min_trend_score}-{config.max_trend_score}分"
        )

    if rsi < config.rsi_min or rsi > config.rsi_max:
        return BuyConditionResult(
            passed=False,
            reason=f"RSI {rsi}，做空需要{config.rsi_min}-{config.rsi_max}（超买）"
        )

    if volume_ratio < config.min_volume_ratio:
        return BuyConditionResult(
            passed=False,
            reason=f"成交量{volume_ratio}x，需要>={config.min_volume_ratio}x"
        )

    if price_change_24h < config.min_24h_change or price_change_24h > config.max_24h_change:
        return BuyConditionResult(
            passed=False,
            reason=f"24h涨跌{price_change_24h}%，需要{config.min_24h_change}% ~ {config.max_24h_change}%"
        )

    # 大盘趋势检查：做空时不能太高（逆势做空风险大）
    if market_trend > config.max_market_trend:
        return BuyConditionResult(
            passed=False,
            reason=f"大盘趋势{market_trend}分，做空需要≤{config.max_market_trend}分"
        )

    if volatility < config.min_volatility or volatility > config.max_volatility:
        return BuyConditionResult(
            passed=False,
            reason=f"波动率{volatility}%，需要{config.min_volatility}% ~ {config.max_volatility}%"
        )

    return BuyConditionResult(passed=True, reason="满足所有短线做空条件")


def check_short_term_exit(
    config: ShortTermConfig,
    entry_price: float,
    current_price: float,
    entry_time: datetime,
    trend_score: int = 5,
    smart_stop_loss_enabled: bool = True,
    stop_loss_trend_8_plus: float = 3.0,
    stop_loss_trend_6_7: float = 2.0,
    stop_loss_trend_default: float = 1.5,
    dynamic_take_profit_enabled: bool = True,
    take_profit_trend_9_10: float = 15.0,
    take_profit_trend_7_8: float = 10.0,
    take_profit_trend_5_6: float = 8.0,
    take_profit_trend_default: float = 6.0
) -> ExitResult:
    pnl = ((current_price - entry_price) / entry_price) * 100
    hours_since_entry = (datetime.now() - entry_time).total_seconds() / 3600

    if smart_stop_loss_enabled:
        if trend_score >= 8:
            effective_stop_loss = -stop_loss_trend_8_plus
        elif trend_score >= 6:
            effective_stop_loss = -stop_loss_trend_6_7
        else:
            effective_stop_loss = -stop_loss_trend_default
    else:
        effective_stop_loss = config.stop_loss

    if pnl <= effective_stop_loss:
        return ExitResult(
            should_exit=True,
            action="STOP_LOSS",
            reason=f"亏损{pnl:.2f}%，触发止损(趋势{trend_score}分)"
        )

    if dynamic_take_profit_enabled:
        if trend_score >= 9:
            effective_take_profit = take_profit_trend_9_10
        elif trend_score >= 7:
            effective_take_profit = take_profit_trend_7_8
        elif trend_score >= 5:
            effective_take_profit = take_profit_trend_5_6
        else:
            effective_take_profit = take_profit_trend_default
    else:
        effective_take_profit = config.take_profit_2

    if pnl >= effective_take_profit:
        return ExitResult(
            should_exit=True,
            action="TAKE_PROFIT",
            reason=f"盈利{pnl:.2f}%，清仓(趋势{trend_score}分)"
        )

    if hours_since_entry >= config.time_stop:
        return ExitResult(
            should_exit=True,
            action="TIME_STOP",
            reason=f"持仓{hours_since_entry:.1f}小时，时间止损"
        )

    return ExitResult(should_exit=False)


def check_short_term_short_exit(
    config: ShortTermShortConfig,
    entry_price: float,
    current_price: float,
    entry_time: datetime,
    trend_score: int = 5,
    smart_stop_loss_enabled: bool = True,
    stop_loss_trend_0_2: float = 3.0,
    stop_loss_trend_3_4: float = 2.0,
    stop_loss_trend_default: float = 1.5,
    dynamic_take_profit_enabled: bool = True,
    take_profit_trend_0_1: float = 15.0,
    take_profit_trend_2_3: float = 10.0,
    take_profit_trend_4: float = 8.0,
    take_profit_trend_default: float = 6.0
) -> ExitResult:
    pnl = ((entry_price - current_price) / entry_price) * 100
    hours_since_entry = (datetime.now() - entry_time).total_seconds() / 3600

    if smart_stop_loss_enabled:
        if trend_score <= 2:
            effective_stop_loss = -stop_loss_trend_0_2
        elif trend_score <= 4:
            effective_stop_loss = -stop_loss_trend_3_4
        else:
            effective_stop_loss = -stop_loss_trend_default
    else:
        effective_stop_loss = config.stop_loss

    if pnl <= effective_stop_loss:
        return ExitResult(
            should_exit=True,
            action="STOP_LOSS",
            reason=f"做空亏损{abs(pnl):.2f}%，触发止损(趋势{trend_score}分)"
        )

    if dynamic_take_profit_enabled:
        if trend_score <= 1:
            effective_take_profit = take_profit_trend_0_1
        elif trend_score <= 3:
            effective_take_profit = take_profit_trend_2_3
        elif trend_score == 4:
            effective_take_profit = take_profit_trend_4
        else:
            effective_take_profit = take_profit_trend_default
    else:
        effective_take_profit = config.take_profit_2

    if pnl >= effective_take_profit:
        return ExitResult(
            should_exit=True,
            action="TAKE_PROFIT",
            reason=f"做空盈利{pnl:.2f}%，清仓(趋势{trend_score}分)"
        )

    if hours_since_entry >= config.time_stop:
        return ExitResult(
            should_exit=True,
            action="TIME_STOP",
            reason=f"做空持仓{hours_since_entry:.1f}小时，时间止损"
        )

    return ExitResult(should_exit=False)


class ShortTermStats:
    def __init__(self, stats_file: str = "./data/short_term_stats.json"):
        self.stats_file = stats_file
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)
    
    def get_today_trade_count(self) -> int:
        today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
        
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                    if stats.get("date") == today:
                        return stats.get("trade_count", 0)
            except Exception:
                pass
        
        return 0
    
    def record_trade(self, coin: str, action: str, price: float, amount: float):
        today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
        
        stats = {"date": today, "trade_count": 0, "trades": []}
        
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                    if existing.get("date") == today:
                        stats = existing
            except Exception:
                pass
        
        stats["trade_count"] += 1
        stats["trades"].append({
            "time": datetime.now().isoformat(),
            "coin": coin,
            "action": action,
            "price": price,
            "amount": amount
        })
        
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)


short_term_config = ShortTermConfig()
short_term_short_config = ShortTermShortConfig()  # 做空配置
short_term_stats = ShortTermStats()


class ShortTermTradingStrategy:
    """短线高胜率交易策略完整实现"""

    def __init__(self, data_dir: str = "."):
        self.data_dir = data_dir
        self.config = short_term_config
        self.stats = short_term_stats
        self.positions: Dict[str, ShortTermPosition] = {}
        self.trades: List[ShortTermTrade] = []
        self.last_trade_time: Dict[str, datetime] = {}
        self.state_file = os.path.join(data_dir, "short_term_state.json")
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.positions = {
                        k: ShortTermPosition(
                            coin=v["coin"],
                            entry_price=v["entry_price"],
                            amount=v["amount"],
                            entry_time=datetime.fromisoformat(v["entry_time"]),
                            partial_exit=v.get("partial_exit", False)
                        )
                        for k, v in data.get("positions", {}).items()
                    }
                    self.trades = [
                        ShortTermTrade(**t)
                        for t in data.get("trades", [])
                    ]
                    self.last_trade_time = {
                        k: datetime.fromisoformat(v)
                        for k, v in data.get("last_trade_time", {}).items()
                    }
                    logger.info(f"已加载短线策略状态: {len(self.positions)}持仓, {len(self.trades)}交易")
            except Exception as e:
                logger.error(f"加载短线策略状态失败: {e}")

    def _save_state(self):
        try:
            data = {
                "positions": {
                    k: {
                        "coin": v.coin,
                        "entry_price": v.entry_price,
                        "amount": v.amount,
                        "entry_time": v.entry_time.isoformat(),
                        "partial_exit": v.partial_exit
                    }
                    for k, v in self.positions.items()
                },
                "trades": [
                    {
                        "time": t.time,
                        "coin": t.coin,
                        "action": t.action,
                        "price": t.price,
                        "amount": t.amount,
                        "reason": t.reason
                    }
                    for t in self.trades[-100:]
                ],
                "last_trade_time": {
                    k: v.isoformat()
                    for k, v in self.last_trade_time.items()
                }
            }
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存短线策略状态失败: {e}")

    def get_adjusted_position_size(self, base_size: float) -> float:
        """获取时区调整后的仓位大小"""
        return get_position_size_by_timezone(
            base_size, 
            self.config.timezone_adjusted_position
        )

    async def execute_buy(
        self,
        client: OKXClient,
        coin: str,
        amount: float,
        reason: str
    ) -> Dict[str, Any]:
        """执行买入"""
        try:
            # 应用时区感知调整仓位大小
            adjusted_amount = self.get_adjusted_position_size(amount)
            
            inst_id = f"{coin}-USDT"
            ticker = await client.get_ticker(inst_id)
            if not ticker or ticker.get("code") != "0":
                return {"success": False, "error": "无法获取价格"}

            price = float(ticker["data"][0]["last"])
            quantity = adjusted_amount / price

            if self.config.timezone_adjusted_position and adjusted_amount != amount:
                logger.info(f"🟢 执行买入: {coin} 基础${amount} → 时区调整后${adjusted_amount} @ ${price:.4f}")
            else:
                logger.info(f"🟢 执行买入: {coin} ${adjusted_amount} @ ${price:.4f}")

            result = await client.place_order(
                inst_id=inst_id,
                side="buy",
                ord_type="market",
                sz=str(quantity)
            )

            if result.get("code") == "0":
                ord_id = result["data"][0]["ordId"]
                logger.info(f"✅ 买入成功: {ord_id}")

                self.positions[coin] = ShortTermPosition(
                    coin=coin,
                    entry_price=price,
                    amount=quantity,
                    entry_time=datetime.now(BEIJING_TZ)
                )
                self.last_trade_time[coin] = datetime.now(BEIJING_TZ)

                self.trades.append(ShortTermTrade(
                    time=datetime.now().isoformat(),
                    coin=coin,
                    action="buy",
                    price=price,
                    amount=quantity,
                    reason=reason
                ))

                self.stats.record_trade(coin, "buy", price, adjusted_amount)
                self._save_state()

                return {"success": True, "order_id": ord_id, "price": price, "quantity": quantity, "adjusted_amount": adjusted_amount}
            else:
                logger.error(f"❌ 买入失败: {result.get('msg')}")
                return {"success": False, "error": result.get("msg")}

        except Exception as e:
            logger.error(f"执行买入失败: {e}")
            return {"success": False, "error": str(e)}

    async def execute_sell(
        self,
        client: OKXClient,
        coin: str,
        amount: Optional[float] = None,
        reason: str = ""
    ) -> Dict[str, Any]:
        """执行卖出"""
        try:
            if coin not in self.positions:
                return {"success": False, "error": "没有持仓"}

            position = self.positions[coin]
            sell_amount = amount if amount else position.amount
            inst_id = f"{coin}-USDT"

            ticker = await client.get_ticker(inst_id)
            if not ticker or ticker.get("code") != "0":
                return {"success": False, "error": "无法获取价格"}

            price = float(ticker["data"][0]["last"])
            pnl = ((price - position.entry_price) / position.entry_price) * 100

            logger.info(f"🔴 执行卖出: {coin} {sell_amount:.6f} @ ${price:.4f} (PnL: {pnl:.2f}%)")

            result = await client.place_order(
                inst_id=inst_id,
                side="sell",
                ord_type="market",
                sz=str(sell_amount)
            )

            if result.get("code") == "0":
                ord_id = result["data"][0]["ordId"]
                logger.info(f"✅ 卖出成功: {ord_id}")

                self.trades.append(ShortTermTrade(
                    time=datetime.now().isoformat(),
                    coin=coin,
                    action="sell",
                    price=price,
                    amount=sell_amount,
                    reason=reason or f"{pnl:.2f}%盈亏"
                ))

                if sell_amount >= position.amount * 0.95:
                    del self.positions[coin]
                else:
                    position.amount -= sell_amount
                    position.partial_exit = True

                self.stats.record_trade(coin, "sell", price, sell_amount * price)
                self._save_state()

                return {"success": True, "order_id": ord_id, "price": price, "pnl": pnl}
            else:
                logger.error(f"❌ 卖出失败: {result.get('msg')}")
                return {"success": False, "error": result.get("msg")}

        except Exception as e:
            logger.error(f"执行卖出失败: {e}")
            return {"success": False, "error": str(e)}

    async def check_and_exit_positions(self, client: OKXClient) -> List[Dict[str, Any]]:
        """检查并执行退出逻辑"""
        exits = []
        
        try:
            from app.services.trading_engine import trading_engine
            te_config = trading_engine.config
        except ImportError:
            te_config = None

        for coin, position in list(self.positions.items()):
            try:
                inst_id = f"{coin}-USDT"
                ticker = await client.get_ticker(inst_id)
                if not ticker or ticker.get("code") != "0":
                    continue

                current_price = float(ticker["data"][0]["last"])
                
                trend_score = 5
                if te_config:
                    try:
                        from app.services.coordinator import coordinator
                        trend_data = coordinator.get_trend_score(coin)
                        if trend_data:
                            trend_score = trend_data.get("score", 5)
                    except Exception:
                        pass
                
                if te_config:
                    exit_result = check_short_term_exit(
                        self.config,
                        position.entry_price,
                        current_price,
                        position.entry_time,
                        trend_score=trend_score,
                        smart_stop_loss_enabled=te_config.long_smart_stop_loss_enabled,
                        stop_loss_trend_8_plus=te_config.long_stop_loss_trend_8_plus,
                        stop_loss_trend_6_7=te_config.long_stop_loss_trend_6_7,
                        stop_loss_trend_default=te_config.long_stop_loss_trend_default,
                        dynamic_take_profit_enabled=te_config.long_dynamic_take_profit_enabled,
                        take_profit_trend_9_10=te_config.long_take_profit_trend_9_10,
                        take_profit_trend_7_8=te_config.long_take_profit_trend_7_8,
                        take_profit_trend_5_6=te_config.long_take_profit_trend_5_6,
                        take_profit_trend_default=te_config.long_take_profit_trend_default
                    )
                else:
                    exit_result = check_short_term_exit(
                        self.config,
                        position.entry_price,
                        current_price,
                        position.entry_time
                    )

                if exit_result.should_exit:
                    action = exit_result.action
                    sell_amount = position.amount

                    if action == "TAKE_PROFIT_1" and not position.partial_exit:
                        sell_amount = position.amount * 0.5

                    logger.info(f"🎯 {coin} {exit_result.reason}")

                    result = await self.execute_sell(
                        client,
                        coin,
                        sell_amount,
                        exit_result.reason
                    )

                    exits.append({
                        "coin": coin,
                        "action": action,
                        "result": result
                    })

            except Exception as e:
                logger.error(f"检查退出逻辑失败 {coin}: {e}")

        return exits

    async def run_cycle(self, client: OKXClient) -> Dict[str, Any]:
        """执行一轮策略循环"""
        results = {
            "exits": [],
            "trades": 0,
            "errors": []
        }

        daily_count = self.stats.get_today_trade_count()
        if daily_count >= self.config.max_daily_trades:
            logger.info(f"今日交易已达上限: {daily_count}/{self.config.max_daily_trades}")
            return results

        results["exits"] = await self.check_and_exit_positions(client)

        return results

    def get_status(self) -> Dict[str, Any]:
        """获取策略状态"""
        daily_count = self.stats.get_today_trade_count()
        return {
            "positions": {
                k: {
                    "coin": v.coin,
                    "entry_price": v.entry_price,
                    "amount": v.amount,
                    "entry_time": v.entry_time.isoformat(),
                    "partial_exit": v.partial_exit
                }
                for k, v in self.positions.items()
            },
            "daily_trades": daily_count,
            "max_daily_trades": self.config.max_daily_trades,
            "total_trades": len(self.trades),
            "config": self.config.model_dump()
        }


short_term_strategy = ShortTermTradingStrategy()
