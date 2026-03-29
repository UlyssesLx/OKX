"""
统一日志配置模块
标准化日志格式和级别
"""
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from loguru import logger
from functools import wraps
import time


class LogFormat:
    """日志格式常量"""

    DETAILED = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"
    SIMPLE = "{time:HH:mm:ss} | {level: <8} | {message}"
    TRADING = "{time:HH:mm:ss.SSS} | {extra[coin]} | {level: <5} | {message}"
    ERROR = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line}\n{exception}"


class LogLevel:
    """日志级别"""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    SUCCESS = 25
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class LoggerConfig:
    """日志配置"""

    _configured = False
    _log_dir: Optional[Path] = None

    @classmethod
    def setup(
        cls,
        log_dir: Optional[str] = None,
        level: str = "INFO",
        rotation: str = "00:00",
        retention: str = "30 days",
        format_string: str = LogFormat.DETAILED,
        enable_console: bool = True
    ):
        """配置日志系统"""
        if cls._configured:
            return

        logger.remove()

        log_level = getattr(logging, level.upper(), logging.INFO)

        if enable_console:
            logger.add(
                sys.stdout,
                level=log_level,
                format=format_string,
                colorize=True
            )

        if log_dir:
            cls._log_dir = Path(log_dir)
            cls._log_dir.mkdir(parents=True, exist_ok=True)

            today = datetime.now().strftime("%Y-%m-%d")
            log_file = cls._log_dir / f"trading_{today}.log"

            logger.add(
                log_file,
                level=log_level,
                format=format_string,
                rotation=rotation,
                retention=retention,
                compression="zip",
                encoding="utf-8"
            )

            error_file = cls._log_dir / f"error_{today}.log"
            logger.add(
                error_file,
                level=logging.ERROR,
                format=LogFormat.ERROR,
                rotation=rotation,
                retention=retention,
                compression="zip",
                encoding="utf-8"
            )

        cls._configured = True

    @classmethod
    def get_log_dir(cls) -> Optional[Path]:
        return cls._log_dir


def setup_logging(
    log_dir: Optional[str] = None,
    level: str = "INFO"
):
    """设置日志的便捷函数"""
    LoggerConfig.setup(log_dir=log_dir, level=level)


class TradingLogger:
    """交易专用日志记录器"""

    def __init__(self, coin: str = ""):
        self.coin = coin
        self.logger = logger

    def _add_context(self, message: str) -> str:
        if self.coin:
            return f"[{self.coin}] {message}"
        return message

    def info(self, message: str, **kwargs):
        self.logger.info(self._add_context(message), **kwargs)

    def success(self, message: str, **kwargs):
        self.logger.success(self._add_context(message), **kwargs)

    def warning(self, message: str, **kwargs):
        self.logger.warning(self._add_context(message), **kwargs)

    def error(self, message: str, **kwargs):
        self.logger.error(self._add_context(message), **kwargs)

    def debug(self, message: str, **kwargs):
        self.logger.debug(self._add_context(message), **kwargs)

    def signal(self, action: str, price: float, reason: str, **kwargs):
        """记录交易信号"""
        self.logger.info(
            f"📢 信号: {action} @ {price:.4f} | 原因: {reason}",
            **kwargs
        )

    def order(self, action: str, coin: str, amount: float, price: float, order_id: str = "", **kwargs):
        """记录订单"""
        self.logger.info(
            f"📝 订单: {action} {amount} {coin} @ {price:.4f} | ID: {order_id}",
            **kwargs
        )

    def trade(self, action: str, coin: str, amount: float, price: float, pnl: float = 0, **kwargs):
        """记录成交"""
        pnl_str = f" | PnL: {pnl:+.2f}" if pnl != 0 else ""
        self.logger.success(
            f"✅ 成交: {action} {amount} {coin} @ {price:.4f}{pnl_str}",
            **kwargs
        )

    def position(self, coin: str, side: str, amount: float, entry_price: float, current_price: float, **kwargs):
        """记录持仓状态"""
        pnl_pct = (current_price - entry_price) / entry_price * 100 if entry_price > 0 else 0
        self.logger.info(
            f"💼 持仓: {side} {amount} {coin} @ 入场:{entry_price:.4f} 当前:{current_price:.4f} ({pnl_pct:+.2f}%)",
            **kwargs
        )


def log_execution_time(func):
    """记录函数执行时间的装饰器"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.debug(f"⏱️ {func.__name__} 执行耗时: {elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"⏱️ {func.__name__} 执行失败: {elapsed:.3f}s | 错误: {str(e)}")
            raise

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.debug(f"⏱️ {func.__name__} 执行耗时: {elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"⏱️ {func.__name__} 执行失败: {elapsed:.3f}s | 错误: {str(e)}")
            raise

    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def log_signal(func):
    """记录信号的装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        if result:
            coin = kwargs.get('coin', args[0] if args else 'UNKNOWN')
            action = kwargs.get('action', 'UNKNOWN')
            price = kwargs.get('price', 0)
            logger.info(f"📢 信号触发: {action} {coin} @ {price}")
        return result
    return wrapper


trading_logger = TradingLogger()