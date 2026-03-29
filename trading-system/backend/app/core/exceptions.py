"""
统一异常处理模块
标准化异常类和错误码
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ErrorCode(str, Enum):
    SUCCESS = "0"
    UNKNOWN_ERROR = "-1"
    NETWORK_ERROR = "-2"
    TIMEOUT_ERROR = "-3"
    CONNECTION_ERROR = "-4"
    RATE_LIMIT_ERROR = "-5"
    INVALID_PARAMETER = "400"
    UNAUTHORIZED = "401"
    FORBIDDEN = "403"
    NOT_FOUND = "404"
    TRADING_ERROR = "500"
    INSUFFICIENT_BALANCE = "501"
    POSITION_NOT_FOUND = "502"
    ORDER_REJECTED = "503"
    SIGNAL_DUPLICATED = "504"
    SIGNAL_COOLDOWN = "505"
    CONFIG_ERROR = "600"
    VALIDATION_ERROR = "601"


class TradingSystemError(Exception):
    """交易系统基础异常类"""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None,
        retry: bool = False
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        self.retry = retry
        self.timestamp = datetime.now()
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "code": self.code.value,
            "details": self.details,
            "retry": self.retry,
            "timestamp": self.timestamp.isoformat()
        }


class NetworkError(TradingSystemError):
    """网络相关错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.NETWORK_ERROR,
            details=details,
            retry=True
        )


class TimeoutError(TradingSystemError):
    """请求超时错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.TIMEOUT_ERROR,
            details=details,
            retry=True
        )


class RateLimitError(TradingSystemError):
    """频率限制错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, retry_after: int = 60):
        super().__init__(
            message=message,
            code=ErrorCode.RATE_LIMIT_ERROR,
            details={**(details or {}), "retry_after": retry_after},
            retry=True
        )


class TradingError(TradingSystemError):
    """交易执行错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.TRADING_ERROR,
            details=details,
            retry=False
        )


class InsufficientBalanceError(TradingError):
    """余额不足错误"""

    def __init__(self, required: float, available: float, coin: str = "USDT"):
        super().__init__(
            message=f"余额不足: 需要{required}{coin}, 可用{available}{coin}",
            details={"required": required, "available": available, "coin": coin}
        )


class PositionNotFoundError(TradingError):
    """持仓不存在错误"""

    def __init__(self, coin: str, position_type: str = "long"):
        super().__init__(
            message=f"未找到 {coin} 的 {position_type} 持仓",
            details={"coin": coin, "position_type": position_type}
        )


class OrderRejectedError(TradingError):
    """订单被拒绝错误"""

    def __init__(self, reason: str, order_data: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"订单被拒绝: {reason}",
            details={**(order_data or {}), "reject_reason": reason}
        )


class SignalDuplicateError(TradingSystemError):
    """信号重复错误"""

    def __init__(self, coin: str, signal_type: str, last_price: float, last_time: str):
        super().__init__(
            message=f"{coin} {signal_type} 信号重复，上次交易价格{last_price}@{last_time}",
            code=ErrorCode.SIGNAL_DUPLICATED,
            details={
                "coin": coin,
                "signal_type": signal_type,
                "last_price": last_price,
                "last_time": last_time
            },
            retry=False
        )


class SignalCooldownError(TradingSystemError):
    """信号冷却中错误"""

    def __init__(self, coin: str, signal_type: str, remaining_minutes: int):
        super().__init__(
            message=f"{coin} {signal_type} 信号冷却中，剩余{remaining_minutes}分钟",
            code=ErrorCode.SIGNAL_COOLDOWN,
            details={
                "coin": coin,
                "signal_type": signal_type,
                "remaining_minutes": remaining_minutes
            },
            retry=False
        )


class ConfigError(TradingSystemError):
    """配置错误"""

    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(
            message=f"配置错误: {message}",
            code=ErrorCode.CONFIG_ERROR,
            details={"config_key": config_key} if config_key else {},
            retry=False
        )


class ValidationError(TradingSystemError):
    """数据验证错误"""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        super().__init__(
            message=f"验证失败: {message}",
            code=ErrorCode.VALIDATION_ERROR,
            details={
                "field": field,
                "value": value
            },
            retry=False
        )


def is_retryable_error(error: Exception) -> bool:
    """判断错误是否可重试"""
    if isinstance(error, TradingSystemError):
        return error.retry
    if isinstance(error, (NetworkError, TimeoutError, RateLimitError)):
        return True
    return False


def format_error_response(error: Exception) -> Dict[str, Any]:
    """格式化错误响应"""
    if isinstance(error, TradingSystemError):
        return error.to_dict()

    return {
        "error": error.__class__.__name__,
        "message": str(error),
        "code": ErrorCode.UNKNOWN_ERROR.value,
        "details": {},
        "retry": False,
        "timestamp": datetime.now().isoformat()
    }