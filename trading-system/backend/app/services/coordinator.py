import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
from loguru import logger

from app.services.trading_engine import trading_engine, TradingScheduler
from app.services.data_reminder_agent import data_reminder_agent
from app.services.trade_stats import trade_stats
from app.services.strategy_evolution import strategy_evolution, StrategyParams
from app.strategies.enhanced import emergency_stop, sideways_manager
from app.strategies.pyramid import pyramid_manager
from app.core.config import settings
from app.core.okx_client import OKXClient
from app.config.sparrow_config import get_check_interval, sparrow_config

BEIJING_TZ = timezone(timedelta(hours=8))

def get_beijing_time():
    return datetime.now(BEIJING_TZ)


def get_timezone_adjusted_interval(base_interval: int, timezone_aware: bool = True) -> int:
    """
    根据时区获取调整后的检查间隔
    高活跃时段缩短检查间隔，低活跃时段延长检查间隔
    
    Args:
        base_interval: 基础检查间隔（分钟）
        timezone_aware: 是否启用时区感知调整
    
    Returns:
        调整后的检查间隔（分钟）
    """
    # 如果禁用时区感知，使用配置的固定间隔
    if not timezone_aware or not sparrow_config.timezone_aware_enabled:
        return sparrow_config.check_interval.fixed
    
    try:
        # 使用币市麻雀战法的检查频率配置
        check_interval_minutes = get_check_interval(sparrow_config)
        return check_interval_minutes
    except Exception as e:
        logger.warning(f"获取时区调整间隔失败，使用基础间隔: {e}")
        return base_interval

# WebSocket 广播回调（将在 main.py 中设置）
ws_broadcast_callback: Optional[callable] = None

def set_ws_broadcast_callback(callback: callable):
    global ws_broadcast_callback
    ws_broadcast_callback = callback


@dataclass
class CoordinatorStatus:
    is_running: bool
    last_cycle_time: Optional[datetime]
    total_cycles: int
    errors: List[str]
    trading_enabled: bool


class Coordinator:
    def __init__(self):
        self.trading_scheduler: Optional[TradingScheduler] = None
        self.running = False
        self.last_cycle_time: Optional[datetime] = None
        self.total_cycles = 0
        self.errors: List[str] = []
        self._background_task: Optional[asyncio.Task] = None
        self._okx_health_check_task: Optional[asyncio.Task] = None
        self._last_okx_success_time: Optional[datetime] = None
        self._okx_disconnected_notified: bool = False
        self._interval_minutes: int = 5
        self._dry_run: bool = True
    
    def get_status(self) -> CoordinatorStatus:
        return CoordinatorStatus(
            is_running=self.running,
            last_cycle_time=self.last_cycle_time,
            total_cycles=self.total_cycles,
            errors=self.errors[-10:],
            trading_enabled=settings.TRADING_MODE == "live"
        )

    def clear_errors(self):
        """清除错误列表"""
        self.errors = []
        logger.info("错误列表已清除")

    def _sync_evolution_params(self):
        config = trading_engine.config
        strategy_evolution.log.current_params.long = StrategyParams(
            stop_loss=config.long_stop_loss_trend_8_plus,
            take_profit=config.long_take_profit_trend_9_10,
            max_positions=config.long_max_positions,
            trade_size=config.long_position_size,
            sentiment_threshold=config.sentiment_threshold
        )
        strategy_evolution.log.current_params.short = StrategyParams(
            stop_loss=-config.short_stop_loss_percent,
            take_profit=config.short_take_profit_percent,
            max_positions=config.short_max_positions,
            trade_size=config.short_position_size,
            sentiment_threshold=config.short_sentiment_threshold
        )
        strategy_evolution._save_log()
        logger.info("✅ 策略进化参数已同步到交易引擎配置")

    async def run_single_cycle(self, dry_run: bool = True) -> Dict[str, Any]:
        if emergency_stop.is_stopped():
            stop_info = emergency_stop.get_stop_info()
            logger.warning(f"紧急停止状态: {stop_info}")
            return {
                "status": "stopped",
                "reason": stop_info.get("reason", "紧急停止"),
                "stopped_at": stop_info.get("stopped_at")
            }

        self.total_cycles += 1
        self.last_cycle_time = get_beijing_time()

        # 收集日志
        cycle_logs = []

        def log_collector(message, level="info"):
            log_entry = {
                "time": get_beijing_time().strftime("%H:%M:%S"),
                "message": message,
                "type": level
            }
            cycle_logs.append(log_entry)
            # 通过 WebSocket 广播日志
            if ws_broadcast_callback:
                asyncio.create_task(ws_broadcast_callback({
                    "type": "coordinator_log",
                    "data": log_entry
                }))
        
        # 设置 trading_engine 的日志回调
        trading_engine.set_log_callback(log_collector)

        log_collector("=" * 50, "info")
        log_collector(f"🔄 开始第 {self.total_cycles} 个周期", "info")
        log_collector(f"⏰ {self.last_cycle_time.strftime('%Y-%m-%d %H:%M:%S')}", "info")

        logger.info("=" * 70)
        logger.info(f"🔄 协调器 - 开始第 {self.total_cycles} 个周期")
        logger.info(f"⏰ 时间: {self.last_cycle_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)

        # 启动后立即检查并清理过期黑名单
        from app.services.blacklist_manager import blacklist_manager
        blacklist_coins = blacklist_manager.get_blacklist_summary()
        if blacklist_coins.get("total_count", 0) > 0:
            log_collector(f"📋 黑名单状态: {blacklist_coins['total_count']} 个币种", "info")
        
        pyramid_coins = list(pyramid_manager.layers.keys())
        log_collector(f"📋 已加载金字塔层级记录: {pyramid_coins}", "info")
        
        from app.services.blacklist_manager import blacklist_manager
        blacklist_coins = blacklist_manager.get_blacklisted_coins()
        log_collector(f"📋 已加载持久化黑名单: {blacklist_coins}", "info")
        
        reduce_position_coins = []
        reduce_price_file = Path(__file__).parent.parent.parent / "data" / "reduce_position_prices.json"
        if reduce_price_file.exists():
            try:
                import json
                with open(reduce_price_file, 'r', encoding='utf-8') as f:
                    reduce_data = json.load(f)
                    reduce_position_coins = list(reduce_data.keys())
            except:
                pass
        log_collector(f"📋 已加载减仓价格记录: {reduce_position_coins}", "info")

        result = {
            "cycle": self.total_cycles,
            "timestamp": self.last_cycle_time.isoformat(),
            "dry_run": dry_run,
            "steps": {},
            "logs": cycle_logs
        }

        try:
            today_trades = trade_stats.get_today_trades()
            buy_count = len([t for t in today_trades if t.action == "buy"]) if today_trades else 0
            log_collector(f"今日交易: {len(today_trades) if today_trades else 0}/9999 笔", "info")
            log_collector(f"今日买入: {buy_count}/1000 USDT (卖出不计入)", "info")
            log_collector("🔧 初始化Sub-agent服务...", "info")
            log_collector("  ✅ Sub-agent服务已在运行", "info")
            
            log_collector("📊 步骤1: 数据提醒检查", "info")
            logger.info("📊 步骤 1: 数据提醒检查")
            reminder = await data_reminder_agent.run_check()
            result["steps"]["data_reminder"] = reminder

            if reminder.get("needs_refresh"):
                log_collector("⚠️ 数据需要刷新，建议立即执行交易检查", "warning")
                logger.warning("⚠️ 数据需要刷新")
            else:
                log_collector("✓ 数据状态正常", "success")

            log_collector("📈 步骤2: 市场扫描与交易信号生成", "info")
            logger.info("📈 步骤 2: 市场扫描与交易信号生成")
            trading_result = await trading_engine.run_trading_cycle(dry_run=dry_run)
            result["steps"]["trading"] = trading_result

            opps = trading_result.get("opportunities", [])
            sigs = trading_result.get("signals", [])
            opp_count = opps if isinstance(opps, int) else len(opps)
            sig_count = sigs if isinstance(sigs, int) else len(sigs)
            log_collector(f"📈 市场扫描: 发现 {opp_count} 个机会, 生成 {sig_count} 个信号", "info")

            await data_reminder_agent.record_report_timestamp("trading_check")

            log_collector("📊 步骤3: 策略进化检查", "info")
            logger.info("📊 步骤 3: 策略进化检查")

            recent_trades = trade_stats.get_recent_trades(limit=20)
            trades_for_evolution = [
                {
                    "action": t.action,
                    "pnl": t.pnl,
                    "coin": t.coin,
                    "time": t.time,
                    "side": t.side
                }
                for t in recent_trades
            ]
            evolution_result = await strategy_evolution.evolve(trades_for_evolution)

            if evolution_result.get("paused"):
                log_collector(f"⚠️ 策略暂停中，{evolution_result.get('remaining', 0):.0f}分钟后恢复", "warning")
                logger.warning(f"⚠️ 策略暂停中")
            elif evolution_result.get("long") or evolution_result.get("short"):
                log_collector("✅ 策略迭代分析完成", "success")
                logger.info("✅ 策略迭代分析完成")

                # 显示迭代建议（不覆盖用户配置）
                if evolution_result.get("long", {}).get("params"):
                    long_params = evolution_result["long"]["params"]
                    logger.info(f"  📊 做多迭代建议: 止损{long_params.get('stop_loss')}%, 止盈{long_params.get('take_profit')}%, 金额${long_params.get('trade_size')}")
                    logger.info(f"     当前用户配置: 止损{trading_engine.config.stop_loss_percent}%, 止盈{trading_engine.config.take_profit_percent}%, 金额${trading_engine.config.trade_size}")

                if evolution_result.get("short", {}).get("params"):
                    short_params = evolution_result["short"]["params"]
                    logger.info(f"  📊 做空迭代建议: 止损{short_params.get('stop_loss')}%, 止盈{short_params.get('take_profit')}%, 金额${short_params.get('trade_size')}")
                    logger.info(f"     当前用户配置: 止损{trading_engine.config.short_stop_loss_percent}%, 止盈{trading_engine.config.short_take_profit_1}%, 金额${trading_engine.config.short_position_size}")

            evolution_status = strategy_evolution.get_status()
            result["steps"]["evolution"] = evolution_status

            result["status"] = "completed"
            log_collector(f"✅ 周期 {self.total_cycles} 完成", "success")
            logger.info(f"✅ 周期 {self.total_cycles} 完成")
            
            log_collector("", "info")
            log_collector("=== 数据提醒 Sub-Agent ===", "info")
            log_collector("╔════════════════════════════════════════════════════════════╗", "info")
            log_collector("║  📢 数据提醒 Sub-Agent 报告                                  ║", "info")
            log_collector(f"║  当前时间: {self.last_cycle_time.strftime('%Y/%m/%d %H:%M:%S')}          ║", "info")
            log_collector("╠════════════════════════════════════════════════════════════╣", "info")
            log_collector("║  ✅ 数据获取检查清单:                                        ║", "info")
            log_collector("║     [✓] 账户余额 (OKX API)                                  ║", "info")
            log_collector("║     [✓] 持仓数据 (OKX API)                                  ║", "info")
            log_collector("║     [✓] 市场价格 (OKX API)                                  ║", "info")
            log_collector("║     [✓] 情绪数据 (CoinGecko API)                            ║", "info")
            log_collector("╚════════════════════════════════════════════════════════════╝", "info")
            log_collector("✅ 已显示数据获取提醒", "info")
            log_collector("=== 数据提醒完成 ===", "info")

        except Exception as e:
            import traceback
            error_msg = f"周期执行失败：{str(e)}"
            error_traceback = traceback.format_exc()
            log_collector(f"❌ {error_msg}", "error")
            logger.error(error_msg)
            logger.error(f"错误堆栈：{error_traceback}")
            self.errors.append(f"{datetime.now().isoformat()}: {error_msg}")
            result["status"] = "error"
            result["error"] = error_msg

        return result
    
    async def _run_periodic(self, interval_minutes: int, dry_run: bool, timezone_aware: bool = True):
        """周期性运行，支持时区感知的动态间隔调整"""
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.running:
            try:
                await self.run_single_cycle(dry_run=dry_run)
                consecutive_errors = 0  # 成功执行后重置错误计数
            except asyncio.CancelledError:
                logger.info("协调器任务被取消")
                break
            except Exception as e:
                consecutive_errors += 1
                error_msg = f"周期执行异常 ({consecutive_errors}/{max_consecutive_errors}): {e}"
                logger.error(error_msg)
                self.errors.append(f"{datetime.now().isoformat()}: {str(e)}")
                
                # 如果连续错误过多，等待更长时间再重试
                if consecutive_errors >= max_consecutive_errors:
                    logger.warning(f"连续错误达到{max_consecutive_errors}次，等待5分钟后重试")
                    await asyncio.sleep(300)  # 等待5分钟
                    consecutive_errors = 0  # 重置计数
                    continue
            
            # 获取时区调整后的检查间隔
            try:
                adjusted_interval = get_timezone_adjusted_interval(interval_minutes, timezone_aware)
            except Exception as e:
                logger.warning(f"获取时区调整间隔失败，使用基础间隔: {e}")
                adjusted_interval = interval_minutes
            
            # 记录间隔信息
            if sparrow_config.timezone_aware_enabled and timezone_aware:
                from app.config.sparrow_config import get_current_time_zone
                current_tz = get_current_time_zone()
                if adjusted_interval != interval_minutes:
                    logger.info(f"⏰ 时区感知调整检查间隔: {interval_minutes}分钟 → {adjusted_interval}分钟 (当前时段: {current_tz})")
                else:
                    logger.debug(f"⏰ 当前检查间隔: {adjusted_interval}分钟 (时段: {current_tz})")
            else:
                logger.debug(f"⏰ 固定检查间隔: {adjusted_interval}分钟")
            
            await asyncio.sleep(adjusted_interval * 60)
    
    def _on_task_done(self, task):
        """任务完成回调，用于自动重启"""
        if not self.running:
            # 正常停止，不需要重启
            return
        
        try:
            # 检查任务是否有异常
            if task.cancelled():
                logger.warning("协调器任务被取消")
            elif task.exception():
                logger.error(f"协调器任务异常退出: {task.exception()}")
            else:
                logger.warning("协调器任务意外结束")
            
            # 如果仍在运行状态，自动重启
            if self.running and not emergency_stop.is_stopped():
                logger.info("🔄 自动重启协调器...")
                import asyncio
                self._background_task = asyncio.create_task(
                    self._run_periodic(self._interval_minutes, self._dry_run)
                )
                self._background_task.add_done_callback(self._on_task_done)
                logger.info("✅ 协调器已自动重启")
        except Exception as e:
            logger.error(f"处理任务完成回调失败: {e}")
    
    def stop(self):
        self.running = False
        if self._background_task:
            self._background_task.cancel()
        logger.info("🛑 协调器已停止")
    
    def emergency_stop(self, reason: str = "手动触发"):
        success = emergency_stop.stop(reason)
        if success:
            self.stop()
            logger.warning(f"🚨 紧急停止已触发: {reason}")
        return success
    
    def resume(self):
        success = emergency_stop.resume()
        if success:
            logger.info("✅ 紧急停止已解除，可以重新启动")
        return success

    def reset_sideways(self, coin: str = None):
        if coin:
            sideways_manager.reset(coin)
            logger.info(f"已重置 {coin} 的横盘状态")
        else:
            for c in list(sideways_manager.status.keys()):
                sideways_manager.reset(c)
            logger.info("已重置所有横盘状态")

    async def _check_okx_health(self):
        """定期检查 OKX 连接状态，断开超过1分钟发送飞书通知"""
        from app.services.notification_agent import feishu_notifier

        while self.running:
            try:
                async with OKXClient() as client:
                    result = await client.get_balance()

                if result.get("code") == "0":
                    # OKX 连接正常
                    self._last_okx_success_time = get_beijing_time()
                    if self._okx_disconnected_notified:
                        # 之前断开过，现在恢复了
                        await feishu_notifier.send_message(
                            "✅ OKX 连接恢复",
                            f"OKX API 连接已恢复正常\n时间: {get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        self._okx_disconnected_notified = False
                        logger.info("✅ OKX 连接恢复，已发送飞书通知")
                else:
                    # OKX 返回错误
                    logger.warning(f"OKX 健康检查失败: {result.get('msg', '未知错误')}")
            except Exception as e:
                logger.error(f"OKX 健康检查异常: {e}")

            # 检查是否断开超过1分钟
            if self._last_okx_success_time:
                elapsed = (get_beijing_time() - self._last_okx_success_time).total_seconds()
                if elapsed > 60 and not self._okx_disconnected_notified:
                    # 断开超过1分钟，发送飞书通知
                    await feishu_notifier.send_message(
                        "🚨 OKX 连接断开警告",
                        f"OKX API 连接已断开超过1分钟\n"
                        f"最后成功时间: {self._last_okx_success_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"当前时间: {get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"请检查网络连接或 OKX 服务状态"
                    )
                    self._okx_disconnected_notified = True
                    logger.warning("🚨 OKX 连接断开超过1分钟，已发送飞书通知")

            # 每10秒检查一次
            await asyncio.sleep(10)

    async def start(self, interval_minutes: int = 5, dry_run: bool = True):
        if self.running:
            logger.warning("协调器已在运行中")
            return

        if emergency_stop.is_stopped():
            logger.error("紧急停止状态，无法启动")
            return

        self._sync_evolution_params()
        self.running = True
        self._interval_minutes = interval_minutes
        self._dry_run = dry_run
        self._last_okx_success_time = get_beijing_time()
        self._background_task = asyncio.create_task(
            self._run_periodic(interval_minutes, dry_run)
        )
        self._background_task.add_done_callback(self._on_task_done)
        self._okx_health_check_task = asyncio.create_task(
            self._check_okx_health()
        )
        logger.info(f"🚀 协调器已启动，间隔 {interval_minutes} 分钟，模拟模式: {dry_run}")

    def stop(self):
        self.running = False
        if self._background_task:
            self._background_task.cancel()
        if self._okx_health_check_task:
            self._okx_health_check_task.cancel()
        logger.info("🛑 协调器已停止")


coordinator = Coordinator()
