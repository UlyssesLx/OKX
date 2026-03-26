"""
策略自迭代模块 v2.0
自动分析交易表现，优化策略参数（多空独立迭代）
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from loguru import logger


class EvolutionConfig(BaseModel):
    min_trades_for_review: int = 10
    consecutive_loss_threshold: int = 3
    win_rate_high: float = 0.70
    win_rate_low: float = 0.40
    pause_after_losses_hours: int = 24


class StrategyParams(BaseModel):
    stop_loss: float = -5.0
    take_profit: float = 10.0
    max_positions: int = 3
    trade_size: float = 60.0
    sentiment_threshold: int = 7


class LongShortParams(BaseModel):
    long: StrategyParams = StrategyParams()
    short: StrategyParams = StrategyParams(
        stop_loss=-3.0,
        take_profit=6.0,
        max_positions=1,
        sentiment_threshold=3
    )


class PerformanceStats(BaseModel):
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    consecutive_losses: int = 0
    last_trade_time: Optional[str] = None
    paused: bool = False
    pause_until: Optional[str] = None


class SidePerformance(BaseModel):
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    consecutive_losses: int = 0
    win_rate: float = 0.0
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0


class EvolutionIteration(BaseModel):
    version: str
    date: str
    trigger: str
    side: str
    changes: List[str]
    params_before: Dict[str, Any]
    params_after: Dict[str, Any]
    performance: Dict[str, Any]


class EvolutionLog(BaseModel):
    version: str = "2.1.0"
    iterations: List[EvolutionIteration] = []
    current_params: LongShortParams = LongShortParams()
    performance: PerformanceStats = PerformanceStats()
    long_performance: SidePerformance = SidePerformance()
    short_performance: SidePerformance = SidePerformance()


class StrategyEvolution:
    def __init__(self, data_dir: str = "."):
        self.data_dir = Path(data_dir)
        self.log_file = self.data_dir / "strategy_evolution.json"
        self.config = EvolutionConfig()
        self.adjustment_range = {
            "long": {
                "stop_loss": {"min": -5.0, "max": -3.0},
                "take_profit": {"min": 7.0, "max": 15.0},
                "max_positions": {"min": 3, "max": 7},
                "trade_size": {"min": 40.0, "max": 100.0},
                "sentiment_threshold": {"min": 6, "max": 8}
            },
            "short": {
                "stop_loss": {"min": -1.5, "max": -3.0},
                "take_profit": {"min": 3.0, "max": 8.0},
                "max_positions": {"min": 1, "max": 3},
                "trade_size": {"min": 20.0, "max": 60.0},
                "sentiment_threshold": {"min": 6, "max": 8}
            }
        }
        self._load_log()

    def _load_log(self):
        if self.log_file.exists():
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.log = EvolutionLog(**data)
            except Exception as e:
                logger.error(f"Failed to load evolution log: {e}")
                self.log = EvolutionLog()
        else:
            self.log = EvolutionLog()

    def _save_log(self):
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(self.log.model_dump(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save evolution log: {e}")

    def _get_trade_value(self, trade, key: str, default=None):
        """安全获取交易记录字段，支持Dict和BaseModel"""
        if isinstance(trade, dict):
            return trade.get(key, default)
        elif hasattr(trade, key):
            return getattr(trade, key, default)
        return default

    def analyze_performance(self, trades: List, side: str = "long") -> Optional[Dict[str, Any]]:
        if not trades:
            return None

        side_trades = [t for t in trades if self._get_trade_value(t, "side", "long") == side and self._get_trade_value(t, "action") == "sell"]

        if not side_trades:
            return None

        wins = 0
        losses = 0
        total_profit = 0.0
        total_loss = 0.0
        consecutive_losses = 0
        temp_consecutive = 0

        for t in side_trades:
            pnl = self._get_trade_value(t, "pnl", 0)
            if pnl > 0:
                wins += 1
                total_profit += pnl
                temp_consecutive = 0
            elif pnl < 0:
                losses += 1
                total_loss += abs(pnl)
                temp_consecutive += 1
                consecutive_losses = max(consecutive_losses, temp_consecutive)

        total = wins + losses
        win_rate = wins / total if total > 0 else 0
        avg_profit = total_profit / wins if wins > 0 else 0
        avg_loss = total_loss / losses if losses > 0 else 0
        profit_factor = avg_profit / avg_loss if avg_loss > 0 else 0

        return {
            "side": side,
            "total_trades": len(side_trades),
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "avg_profit": avg_profit,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "consecutive_losses": consecutive_losses
        }

    def generate_adjustments(self, performance: Dict, current_params: StrategyParams, side: str = "long") -> tuple[List[str], StrategyParams]:
        adjustments = []
        new_params = current_params.model_copy()
        side_range = self.adjustment_range.get(side, self.adjustment_range["long"])

        if performance["win_rate"] >= self.config.win_rate_high:
            adjustments.append(f"{'做多' if side == 'long' else '做空'}胜率优秀({performance['win_rate']*100:.1f}%)，放宽止盈")
            new_params.take_profit = min(
                side_range["take_profit"]["max"],
                current_params.take_profit + 1.0
            )
            new_params.max_positions = min(
                side_range["max_positions"]["max"],
                current_params.max_positions + 1
            )

        if performance["win_rate"] <= self.config.win_rate_low and performance["total_trades"] >= 5:
            adjustments.append(f"{'做多' if side == 'long' else '做空'}胜率偏低({performance['win_rate']*100:.1f}%)，收紧止损")
            new_params.stop_loss = max(
                side_range["stop_loss"]["max"],
                current_params.stop_loss + 0.5
            )
            new_params.trade_size = max(
                side_range["trade_size"]["min"],
                current_params.trade_size - 5.0
            )
            new_params.sentiment_threshold = min(
                side_range["sentiment_threshold"]["max"],
                current_params.sentiment_threshold + 1
            )

        if performance["consecutive_losses"] >= self.config.consecutive_loss_threshold:
            adjustments.append(f"{'做多' if side == 'long' else '做空'}连续亏损{performance['consecutive_losses']}笔，暂停交易")
            new_params.stop_loss = side_range["stop_loss"]["max"]
            new_params.trade_size = side_range["trade_size"]["min"]
            new_params.sentiment_threshold = side_range["sentiment_threshold"]["max"]

        if performance["profit_factor"] < 1.5 and performance["total_trades"] >= 5:
            adjustments.append(f"{'做多' if side == 'long' else '做空'}盈亏比偏低({performance['profit_factor']:.2f})，优化止盈止损比")
            new_params.take_profit = min(
                side_range["take_profit"]["max"],
                current_params.take_profit + 0.5
            )

        return adjustments, new_params

    async def evolve(self, trades: List[Dict]) -> Dict[str, Any]:
        logger.info("\n=== 策略自迭代分析 ===")

        if self.log.performance.paused and self.log.performance.pause_until:
            pause_until = datetime.fromisoformat(self.log.performance.pause_until)
            if datetime.utcnow() < pause_until:
                remaining = (pause_until - datetime.utcnow()).total_seconds() / 60
                logger.info(f"⏸️ 策略暂停中，还剩 {remaining:.0f} 分钟")
                return {"paused": True, "remaining": remaining}
            else:
                logger.info("✅ 暂停期结束，恢复交易")
                self.log.performance.paused = False
                self.log.performance.pause_until = None

        result = {
            "paused": False,
            "long": {"params": self.log.current_params.long.model_dump()},
            "short": {"params": self.log.current_params.short.model_dump()}
        }

        long_trades = [t for t in trades if self._get_trade_value(t, "side", "long") == "long"]
        short_trades = [t for t in trades if self._get_trade_value(t, "side") == "short"]

        long_perf = self.analyze_performance(long_trades, "long") if long_trades else None
        short_perf = self.analyze_performance(short_trades, "short") if short_trades else None

        if long_perf and long_perf["total_trades"] >= 3:
            logger.info(f"\n📈 做多最近{long_perf['total_trades']}笔交易表现:")
            logger.info(f"  胜率: {long_perf['win_rate']*100:.1f}% ({long_perf['wins']}胜/{long_perf['losses']}负)")
            logger.info(f"  平均盈利: +{long_perf['avg_profit']:.2f}%")
            logger.info(f"  平均亏损: -{long_perf['avg_loss']:.2f}%")
            logger.info(f"  盈亏比: {long_perf['profit_factor']:.2f}")
            logger.info(f"  连续亏损: {long_perf['consecutive_losses']}笔")

            long_adj, new_long_params = self.generate_adjustments(long_perf, self.log.current_params.long, "long")

            if long_perf["consecutive_losses"] >= self.config.consecutive_loss_threshold:
                self.log.performance.paused = True
                self.log.performance.pause_until = (
                    datetime.utcnow() + timedelta(hours=self.config.pause_after_losses_hours)
                ).isoformat()
                logger.info(f"\n⏸️ 做多触发暂停机制：连续{long_perf['consecutive_losses']}笔亏损")

            if long_adj:
                iteration = EvolutionIteration(
                    version=f"1.0.{len(self.log.iterations) + 1}",
                    date=datetime.utcnow().isoformat(),
                    trigger=f"做多{long_perf['total_trades']}笔交易完成复盘",
                    side="long",
                    changes=long_adj,
                    params_before=self.log.current_params.long.model_dump(),
                    params_after=new_long_params.model_dump(),
                    performance={
                        "win_rate": long_perf["win_rate"],
                        "avg_profit": long_perf["avg_profit"],
                        "avg_loss": long_perf["avg_loss"],
                        "profit_factor": long_perf["profit_factor"]
                    }
                )
                self.log.iterations.append(iteration)
                self.log.current_params.long = new_long_params
                logger.info("\n🔄 做多策略自动调整:")
                for a in long_adj:
                    logger.info(f"  • {a}")

            self.log.long_performance = SidePerformance(**long_perf)
            result["long"]["params"] = self.log.current_params.long.model_dump()
            result["long"]["adjustments"] = long_adj

        if short_perf and short_perf["total_trades"] >= 3:
            logger.info(f"\n📉 做空最近{short_perf['total_trades']}笔交易表现:")
            logger.info(f"  胜率: {short_perf['win_rate']*100:.1f}% ({short_perf['wins']}胜/{short_perf['losses']}负)")
            logger.info(f"  平均盈利: +{short_perf['avg_profit']:.2f}%")
            logger.info(f"  平均亏损: -{short_perf['avg_loss']:.2f}%")
            logger.info(f"  盈亏比: {short_perf['profit_factor']:.2f}")
            logger.info(f"  连续亏损: {short_perf['consecutive_losses']}笔")

            short_adj, new_short_params = self.generate_adjustments(short_perf, self.log.current_params.short, "short")

            if short_perf["consecutive_losses"] >= self.config.consecutive_loss_threshold:
                self.log.performance.paused = True
                self.log.performance.pause_until = (
                    datetime.utcnow() + timedelta(hours=self.config.pause_after_losses_hours)
                ).isoformat()
                logger.info(f"\n⏸️ 做空触发暂停机制：连续{short_perf['consecutive_losses']}笔亏损")

            if short_adj:
                iteration = EvolutionIteration(
                    version=f"1.0.{len(self.log.iterations) + 1}",
                    date=datetime.utcnow().isoformat(),
                    trigger=f"做空{short_perf['total_trades']}笔交易完成复盘",
                    side="short",
                    changes=short_adj,
                    params_before=self.log.current_params.short.model_dump(),
                    params_after=new_short_params.model_dump(),
                    performance={
                        "win_rate": short_perf["win_rate"],
                        "avg_profit": short_perf["avg_profit"],
                        "avg_loss": short_perf["avg_loss"],
                        "profit_factor": short_perf["profit_factor"]
                    }
                )
                self.log.iterations.append(iteration)
                self.log.current_params.short = new_short_params
                logger.info("\n🔄 做空策略自动调整:")
                for a in short_adj:
                    logger.info(f"  • {a}")

            self.log.short_performance = SidePerformance(**short_perf)
            result["short"]["params"] = self.log.current_params.short.model_dump()
            result["short"]["adjustments"] = short_adj

        if not long_perf and not short_perf:
            logger.info("📊 交易数据不足，跳过迭代分析")

        total_trades = (long_perf["total_trades"] if long_perf else 0) + (short_perf["total_trades"] if short_perf else 0)
        total_wins = (long_perf["wins"] if long_perf else 0) + (short_perf["wins"] if short_perf else 0)
        total_losses = (long_perf["losses"] if long_perf else 0) + (short_perf["losses"] if short_perf else 0)

        self.log.performance.total_trades = total_trades
        self.log.performance.wins = total_wins
        self.log.performance.losses = total_losses
        self.log.performance.consecutive_losses = max(
            long_perf["consecutive_losses"] if long_perf else 0,
            short_perf["consecutive_losses"] if short_perf else 0
        )
        self.log.performance.last_trade_time = datetime.utcnow().isoformat()

        self._save_log()

        result["performance"] = {
            "total_trades": total_trades,
            "wins": total_wins,
            "losses": total_losses,
            "consecutive_losses": self.log.performance.consecutive_losses
        }

        return result

    def get_current_params(self) -> LongShortParams:
        return self.log.current_params

    def is_paused(self) -> bool:
        if self.log.performance.paused and self.log.performance.pause_until:
            pause_until = datetime.fromisoformat(self.log.performance.pause_until)
            if datetime.utcnow() < pause_until:
                return True
            else:
                self.log.performance.paused = False
                self.log.performance.pause_until = None
                self._save_log()
        return False

    def get_status(self) -> Dict[str, Any]:
        try:
            from app.services.trading_engine import trading_engine as te
            long_params = {
                "stop_loss": te.config.stop_loss_trend_8_plus,
                "take_profit": te.config.take_profit_trend_9_10,
                "max_positions": te.config.long_max_positions,
                "trade_size": te.config.long_position_size,
                "sentiment_threshold": te.config.sentiment_threshold
            }
            short_params = {
                "stop_loss": -te.config.short_stop_loss_percent,
                "take_profit": te.config.short_take_profit_percent,
                "max_positions": te.config.short_max_positions,
                "trade_size": te.config.short_position_size,
                "sentiment_threshold": te.config.short_sentiment_threshold
            }
        except (ImportError, AttributeError):
            long_params = self.log.current_params.long.model_dump()
            short_params = self.log.current_params.short.model_dump()

        return {
            "version": self.log.version,
            "is_paused": self.is_paused(),
            "pause_until": self.log.performance.pause_until,
            "long": {
                "params": long_params,
                "performance": self.log.long_performance.model_dump() if self.log.long_performance else None
            },
            "short": {
                "params": short_params,
                "performance": self.log.short_performance.model_dump() if self.log.short_performance else None
            },
            "iterations_count": len(self.log.iterations),
            "total_trades": self.log.performance.total_trades,
            "wins": self.log.performance.wins,
            "losses": self.log.performance.losses,
            "consecutive_losses": self.log.performance.consecutive_losses,
            "last_trade_time": self.log.performance.last_trade_time
        }


strategy_evolution = StrategyEvolution()