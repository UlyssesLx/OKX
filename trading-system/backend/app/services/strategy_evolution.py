"""
策略自迭代模块 v3.0
整合AI策略顾问和规则迭代，支持止盈止损参数优化
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from loguru import logger

from app.services.ai_strategy_advisor import ai_strategy_advisor, AISuggestion


class EvolutionConfig(BaseModel):
    min_trades_for_review: int = 10
    consecutive_loss_threshold: int = 3
    win_rate_high: float = 0.70
    win_rate_low: float = 0.40
    pause_after_losses_hours: int = 24
    pause_on_loss_enabled: bool = True
    ai_evolution_enabled: bool = False
    ai_evolution_auto_apply: bool = False
    ai_evolution_min_trades: int = 10
    ai_evolution_interval_hours: int = 24
    ai_evolution_confidence_threshold: float = 0.7


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


class AISuggestionRecord(BaseModel):
    timestamp: str
    side: str
    suggestion: Dict[str, Any]
    confidence: float
    analysis: str
    reason: str
    applied: bool = False
    applied_at: Optional[str] = None


class EvolutionIteration(BaseModel):
    version: str
    date: str
    trigger: str
    side: str
    changes: List[str]
    params_before: Dict[str, Any]
    params_after: Dict[str, Any]
    performance: Dict[str, Any]
    source: str = "rule"


class EvolutionLog(BaseModel):
    version: str = "3.0.0"
    iterations: List[EvolutionIteration] = []
    current_params: LongShortParams = LongShortParams()
    performance: PerformanceStats = PerformanceStats()
    long_performance: SidePerformance = SidePerformance()
    short_performance: SidePerformance = SidePerformance()
    pause_on_loss_enabled: bool = True
    ai_evolution_enabled: bool = False
    ai_evolution_auto_apply: bool = False
    last_ai_analysis: Optional[str] = None
    pending_suggestions: List[AISuggestionRecord] = []


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
                self.config.pause_on_loss_enabled = self.log.pause_on_loss_enabled
                self.config.ai_evolution_enabled = self.log.ai_evolution_enabled
                self.config.ai_evolution_auto_apply = self.log.ai_evolution_auto_apply
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
            "profit_loss_ratio": profit_factor,
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
            if self.config.pause_on_loss_enabled:
                adjustments.append(f"{'做多' if side == 'long' else '做空'}连续亏损{performance['consecutive_losses']}笔，暂停交易")
            else:
                adjustments.append(f"{'做多' if side == 'long' else '做空'}连续亏损{performance['consecutive_losses']}笔")
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

    async def ai_analyze(self, trades: List, current_params: Dict[str, Any], side: str = "long") -> Optional[AISuggestion]:
        """使用AI分析交易数据并给出建议"""
        if not self.config.ai_evolution_enabled:
            logger.info("AI策略迭代未启用")
            return None
        
        if self.log.last_ai_analysis:
            last_time = datetime.fromisoformat(self.log.last_ai_analysis)
            elapsed = datetime.utcnow() - last_time
            if elapsed.total_seconds() < self.config.ai_evolution_interval_hours * 3600:
                remaining = self.config.ai_evolution_interval_hours * 3600 - elapsed.total_seconds()
                logger.info(f"AI分析间隔未到，还需等待 {remaining/60:.0f} 分钟")
                return None
        
        performance = self.analyze_performance(trades, side)
        if not performance or performance["total_trades"] < self.config.ai_evolution_min_trades:
            logger.info(f"交易数据不足（{performance['total_trades'] if performance else 0}笔），跳过AI分析")
            return None
        
        logger.info(f"开始AI策略分析（{side}方向）...")
        suggestion = await ai_strategy_advisor.analyze_performance(
            trades=trades,
            performance=performance,
            current_params=current_params,
            side=side
        )
        
        if suggestion:
            self.log.last_ai_analysis = datetime.utcnow().isoformat()
            
            if suggestion.confidence >= self.config.ai_evolution_confidence_threshold:
                if self.config.ai_evolution_auto_apply:
                    logger.info(f"AI建议置信度{suggestion.confidence:.2f}，自动应用")
                    await self._apply_ai_suggestion(suggestion, side)
                else:
                    logger.info(f"AI建议置信度{suggestion.confidence:.2f}，保存待确认")
                    self._save_pending_suggestion(suggestion, side)
            else:
                logger.info(f"AI建议置信度{suggestion.confidence:.2f}低于阈值{self.config.ai_evolution_confidence_threshold}，忽略")
            
            self._save_log()
        
        return suggestion

    def _save_pending_suggestion(self, suggestion: AISuggestion, side: str):
        """保存待确认的AI建议"""
        record = AISuggestionRecord(
            timestamp=datetime.utcnow().isoformat(),
            side=side,
            suggestion=suggestion.model_dump(),
            confidence=suggestion.confidence,
            analysis=suggestion.analysis,
            reason=suggestion.reason,
            applied=False
        )
        self.log.pending_suggestions.append(record)
        logger.info(f"AI建议已保存，等待确认")

    async def _apply_ai_suggestion(self, suggestion: AISuggestion, side: str):
        """应用AI建议到交易配置"""
        try:
            from app.services.trading_engine import trading_engine
            
            config = trading_engine.config
            prefix = "long" if side == "long" else "short"
            
            changes = []
            
            if suggestion.stop_loss_suggestion:
                sl = suggestion.stop_loss_suggestion
                if sl.enabled is not None:
                    setattr(config, f"{prefix}_smart_stop_loss_enabled", sl.enabled)
                    changes.append(f"智能止损启用: {sl.enabled}")
                if side == "long":
                    if sl.trend_8_plus is not None:
                        setattr(config, f"{prefix}_stop_loss_trend_8_plus", sl.trend_8_plus)
                        changes.append(f"趋势≥8分止损: {sl.trend_8_plus}%")
                    if sl.trend_6_7 is not None:
                        setattr(config, f"{prefix}_stop_loss_trend_6_7", sl.trend_6_7)
                        changes.append(f"趋势6-7分止损: {sl.trend_6_7}%")
                else:
                    if sl.trend_0_2 is not None:
                        setattr(config, f"{prefix}_stop_loss_trend_0_2", sl.trend_0_2)
                        changes.append(f"趋势0-2分止损: {sl.trend_0_2}%")
                    if sl.trend_3_4 is not None:
                        setattr(config, f"{prefix}_stop_loss_trend_3_4", sl.trend_3_4)
                        changes.append(f"趋势3-4分止损: {sl.trend_3_4}%")
                if sl.trend_default is not None:
                    setattr(config, f"{prefix}_stop_loss_trend_default", sl.trend_default)
                    changes.append(f"默认止损: {sl.trend_default}%")
            
            if suggestion.take_profit_suggestion:
                tp = suggestion.take_profit_suggestion
                if tp.enabled is not None:
                    setattr(config, f"{prefix}_dynamic_take_profit_enabled", tp.enabled)
                    changes.append(f"动态止盈启用: {tp.enabled}")
                if side == "long":
                    if tp.trend_9_10 is not None:
                        setattr(config, f"{prefix}_take_profit_trend_9_10", tp.trend_9_10)
                        changes.append(f"趋势9-10分止盈: {tp.trend_9_10}%")
                    if tp.trend_7_8 is not None:
                        setattr(config, f"{prefix}_take_profit_trend_7_8", tp.trend_7_8)
                        changes.append(f"趋势7-8分止盈: {tp.trend_7_8}%")
                    if tp.trend_5_6 is not None:
                        setattr(config, f"{prefix}_take_profit_trend_5_6", tp.trend_5_6)
                        changes.append(f"趋势5-6分止盈: {tp.trend_5_6}%")
                else:
                    if tp.trend_0_1 is not None:
                        setattr(config, f"{prefix}_take_profit_trend_0_1", tp.trend_0_1)
                        changes.append(f"趋势0-1分止盈: {tp.trend_0_1}%")
                    if tp.trend_2_3 is not None:
                        setattr(config, f"{prefix}_take_profit_trend_2_3", tp.trend_2_3)
                        changes.append(f"趋势2-3分止盈: {tp.trend_2_3}%")
                    if tp.trend_4 is not None:
                        setattr(config, f"{prefix}_take_profit_trend_4", tp.trend_4)
                        changes.append(f"趋势4分止盈: {tp.trend_4}%")
                if tp.trend_default is not None:
                    setattr(config, f"{prefix}_take_profit_trend_default", tp.trend_default)
                    changes.append(f"默认止盈: {tp.trend_default}%")
            
            if suggestion.band_trade_suggestion:
                bt = suggestion.band_trade_suggestion
                if bt.enabled is not None:
                    setattr(config, f"{prefix}_band_trade_enabled", bt.enabled)
                    changes.append(f"分层减仓启用: {bt.enabled}")
                if bt.reduce_at is not None:
                    setattr(config, f"{prefix}_band_trade_reduce_at", bt.reduce_at)
                    changes.append(f"第一档减仓点: {bt.reduce_at}%")
                if bt.reduce_percent is not None:
                    setattr(config, f"{prefix}_band_trade_reduce_percent", bt.reduce_percent)
                    changes.append(f"第一档减仓比例: {bt.reduce_percent}%")
                if bt.second_reduce_at is not None:
                    setattr(config, f"{prefix}_band_trade_second_reduce_at", bt.second_reduce_at)
                    changes.append(f"第二档减仓点: {bt.second_reduce_at}%")
                if bt.second_reduce_percent is not None:
                    setattr(config, f"{prefix}_band_trade_second_reduce_percent", bt.second_reduce_percent)
                    changes.append(f"第二档减仓比例: {bt.second_reduce_percent}%")
                if bt.final_reduce_at is not None:
                    setattr(config, f"{prefix}_band_trade_final_reduce_at", bt.final_reduce_at)
                    changes.append(f"最终止盈点: {bt.final_reduce_at}%")
            
            if suggestion.small_profit_suggestion:
                sp = suggestion.small_profit_suggestion
                if sp.enabled is not None:
                    setattr(config, f"{prefix}_small_profit_reduce_enabled", sp.enabled)
                    changes.append(f"小盈减仓启用: {sp.enabled}")
                if sp.threshold_percent is not None:
                    setattr(config, f"{prefix}_small_profit_reduce_threshold_percent", sp.threshold_percent)
                    changes.append(f"触发阈值: {sp.threshold_percent}%")
                if sp.position_threshold is not None:
                    setattr(config, f"{prefix}_small_profit_reduce_position_threshold", sp.position_threshold)
                    changes.append(f"仓位阈值: {sp.position_threshold}%")
                if sp.reduce_ratio is not None:
                    setattr(config, f"{prefix}_small_profit_reduce_ratio", sp.reduce_ratio)
                    changes.append(f"减仓比例: {sp.reduce_ratio}%")
            
            iteration = EvolutionIteration(
                version=f"3.0.{len(self.log.iterations) + 1}",
                date=datetime.utcnow().isoformat(),
                trigger=f"AI策略分析（{side}方向）",
                side=side,
                changes=changes,
                params_before={},
                params_after=suggestion.model_dump(),
                performance={},
                source="ai"
            )
            self.log.iterations.append(iteration)
            
            logger.info(f"AI建议已应用: {len(changes)}项调整")
            for change in changes:
                logger.info(f"  • {change}")
            
        except Exception as e:
            logger.error(f"应用AI建议失败: {e}")

    async def apply_pending_suggestion(self, suggestion_id: str) -> bool:
        """应用待确认的AI建议"""
        for i, record in enumerate(self.log.pending_suggestions):
            if record.timestamp == suggestion_id and not record.applied:
                suggestion = AISuggestion(**record.suggestion)
                await self._apply_ai_suggestion(suggestion, record.side)
                self.log.pending_suggestions[i].applied = True
                self.log.pending_suggestions[i].applied_at = datetime.utcnow().isoformat()
                self._save_log()
                return True
        return False

    def get_pending_suggestions(self) -> List[AISuggestionRecord]:
        """获取待确认的AI建议"""
        return [s for s in self.log.pending_suggestions if not s.applied]

    async def evolve(self, trades: List[Dict]) -> Dict[str, Any]:
        logger.info("\n=== 策略自迭代分析 ===")
        
        if trades and len(trades) > 0:
            first_trade = trades[0]
            if not isinstance(first_trade, dict):
                logger.error(f"警告: trades 不是字典列表，而是 {type(first_trade)}, 尝试转换为字典")
                trades = [
                    {
                        "action": getattr(t, 'action', 'unknown'),
                        "pnl": getattr(t, 'pnl', 0),
                        "coin": getattr(t, 'coin', 'unknown'),
                        "time": getattr(t, 'time', ''),
                        "side": getattr(t, 'side', 'long')
                    }
                    for t in trades
                ]
        
        if self.log.performance.paused and self.log.performance.pause_until:
            if not self.config.pause_on_loss_enabled:
                logger.info("✅ 亏损暂停已禁用，清除暂停状态")
                self.log.performance.paused = False
                self.log.performance.pause_until = None
                self._save_log()
            else:
                pause_until = datetime.fromisoformat(self.log.performance.pause_until)
                if datetime.utcnow() < pause_until:
                    remaining = (pause_until - datetime.utcnow()).total_seconds() / 60
                    logger.info(f"⏸️ 策略暂停中，还剩 {remaining:.0f} 分钟")
                    return {"paused": True, "remaining": remaining}
                else:
                    logger.info("✅ 暂停期结束，恢复交易")
                    self.log.performance.paused = False
                    self.log.performance.pause_until = None
                    self._save_log()

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
                if self.config.pause_on_loss_enabled:
                    self.log.performance.paused = True
                    self.log.performance.pause_until = (
                        datetime.utcnow() + timedelta(hours=self.config.pause_after_losses_hours)
                    ).isoformat()
                    logger.info(f"\n⏸️ 做多触发暂停机制：连续{long_perf['consecutive_losses']}笔亏损")
                else:
                    logger.info(f"\n⚠️ 做多连续{long_perf['consecutive_losses']}笔亏损（暂停功能未启用）")

            if long_adj:
                iteration = EvolutionIteration(
                    version=f"3.0.{len(self.log.iterations) + 1}",
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
                    },
                    source="rule"
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
                if self.config.pause_on_loss_enabled:
                    self.log.performance.paused = True
                    self.log.performance.pause_until = (
                        datetime.utcnow() + timedelta(hours=self.config.pause_after_losses_hours)
                    ).isoformat()
                    logger.info(f"\n⏸️ 做空触发暂停机制：连续{short_perf['consecutive_losses']}笔亏损")
                else:
                    logger.info(f"\n⚠️ 做空连续{short_perf['consecutive_losses']}笔亏损（暂停功能未启用）")

            if short_adj:
                iteration = EvolutionIteration(
                    version=f"3.0.{len(self.log.iterations) + 1}",
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
                    },
                    source="rule"
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
                "stop_loss": te.config.long_stop_loss_trend_8_plus,
                "take_profit": te.config.long_take_profit_trend_9_10,
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
            "ai_evolution_enabled": self.log.ai_evolution_enabled,
            "ai_evolution_auto_apply": self.log.ai_evolution_auto_apply,
            "last_ai_analysis": self.log.last_ai_analysis,
            "pending_suggestions_count": len([s for s in self.log.pending_suggestions if not s.applied]),
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

    def update_ai_config(self, enabled: bool = None, auto_apply: bool = None, 
                         min_trades: int = None, interval_hours: int = None,
                         confidence_threshold: float = None):
        """更新AI迭代配置"""
        if enabled is not None:
            self.config.ai_evolution_enabled = enabled
            self.log.ai_evolution_enabled = enabled
        if auto_apply is not None:
            self.config.ai_evolution_auto_apply = auto_apply
            self.log.ai_evolution_auto_apply = auto_apply
        if min_trades is not None:
            self.config.ai_evolution_min_trades = min_trades
        if interval_hours is not None:
            self.config.ai_evolution_interval_hours = interval_hours
        if confidence_threshold is not None:
            self.config.ai_evolution_confidence_threshold = confidence_threshold
        
        self._save_log()
        logger.info(f"AI迭代配置已更新: enabled={self.config.ai_evolution_enabled}, auto_apply={self.config.ai_evolution_auto_apply}")


strategy_evolution = StrategyEvolution(data_dir=str(Path(__file__).parent.parent.parent / "data"))
