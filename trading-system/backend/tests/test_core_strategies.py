"""
OKX交易系统单元测试
测试核心策略逻辑
"""
import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.strategies.common_indicators import (
    calculate_ma,
    calculate_ema,
    calculate_rsi_simple,
    calculate_rsi,
    calculate_macd,
    calculate_bollinger,
    calculate_volatility,
    calculate_volume_ratio,
    calculate_technicals,
    MACDResult,
    BollingerBands,
    RSIResult
)


class TestMovingAverages:
    """测试移动平均线计算"""

    def test_calculate_ma_basic(self):
        prices = [10, 20, 30, 40, 50]
        assert calculate_ma(prices, 3) == 40.0

    def test_calculate_ma_insufficient_data(self):
        prices = [10, 20]
        assert calculate_ma(prices, 5) == 20.0

    def test_calculate_ma_empty(self):
        assert calculate_ma([], 5) == 0.0

    def test_calculate_ema_basic(self):
        prices = [10, 20, 30, 40, 50]
        result = calculate_ema(prices, 3)
        assert 30 < result < 50

    def test_calculate_ema_insufficient_data(self):
        prices = [10, 20]
        assert calculate_ema(prices, 5) == 20.0


class TestRSI:
    """测试RSI计算"""

    def test_rsi_simple_basic(self):
        prices = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28]
        result = calculate_rsi_simple(prices, 14)
        assert 0 <= result <= 100

    def test_rsi_with_winning_period(self):
        prices = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120, 122, 124, 126, 128]
        result = calculate_rsi_simple(prices, 14)
        assert result > 70

    def test_rsi_with_losing_period(self):
        prices = [100, 98, 96, 94, 92, 90, 88, 86, 84, 82, 80, 78, 76, 74, 72]
        result = calculate_rsi_simple(prices, 14)
        assert result < 30

    def test_rsi_insufficient_data(self):
        prices = [100, 102, 103]
        result = calculate_rsi_simple(prices, 14)
        assert result == 50.0

    def test_rsi_result_object(self):
        prices = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28]
        result = calculate_rsi(prices, 14)
        assert isinstance(result, RSIResult)
        assert 0 <= result.rsi <= 100
        assert result.avg_gain >= 0
        assert result.avg_loss >= 0


class TestMACD:
    """测试MACD计算"""

    def test_macd_basic(self):
        prices = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84,
                  46.08, 45.89, 46.03, 45.61, 46.28, 45.84, 46.15, 45.56, 46.24,
                  46.63, 46.11, 46.22, 45.73, 46.38, 45.93, 46.54, 46.93, 46.82, 47.24]
        result = calculate_macd(prices)
        assert isinstance(result, MACDResult)
        assert isinstance(result.macd, float)
        assert isinstance(result.signal, float)
        assert isinstance(result.histogram, float)

    def test_macd_insufficient_data(self):
        prices = [44.34, 44.09]
        result = calculate_macd(prices)
        assert result.macd == 0.0
        assert result.signal == 0.0


class TestBollingerBands:
    """测试布林带计算"""

    def test_bollinger_basic(self):
        prices = [112, 114, 115, 114, 113, 115, 118, 120, 119, 121, 122, 121, 120, 119, 118, 117, 116, 115, 114, 113]
        result = calculate_bollinger(prices, 20)
        assert isinstance(result, BollingerBands)
        assert result.upper > result.middle
        assert result.middle > result.lower

    def test_bollinger_insufficient_data(self):
        prices = [112, 114]
        result = calculate_bollinger(prices, 20)
        assert result.upper > result.lower

    def test_bollinger_empty(self):
        result = calculate_bollinger([], 20)
        assert result.upper == 0.0


class TestVolatility:
    """测试波动率计算"""

    def test_volatility_basic(self):
        prices = [100, 101, 102, 101, 100, 99, 100, 101, 102, 103]
        result = calculate_volatility(prices)
        assert result >= 0

    def test_volatility_insufficient_data(self):
        prices = [100]
        result = calculate_volatility(prices)
        assert result == 0.0


class TestVolumeRatio:
    """测试成交量比率计算"""

    def test_volume_ratio_basic(self):
        volumes = [1000, 1100, 1200, 1100, 1000, 900, 1000, 1100, 1200, 1100,
                   1000, 900, 1000, 1100, 1200, 1100, 1000, 900, 1000, 1100]
        result = calculate_volume_ratio(volumes, 20)
        assert 0 <= result <= 10

    def test_volume_ratio_insufficient_data(self):
        volumes = [1000, 1100]
        result = calculate_volume_ratio(volumes, 20)
        assert result == 1.0


class TestCalculateTechnicals:
    """测试综合技术指标计算"""

    def test_calculate_technicals_with_prices_only(self):
        prices = [112, 114, 115, 114, 113, 115, 118, 120, 119, 121, 122, 121, 120, 119, 118, 117, 116, 115, 114, 113]
        result = calculate_technicals(prices)
        assert "ma5" in result
        assert "ma10" in result
        assert "rsi" in result
        assert "macd" in result
        assert "bollinger" in result
        assert "volatility" in result

    def test_calculate_technicals_with_volumes(self):
        prices = [112, 114, 115, 114, 113, 115, 118, 120, 119, 121, 122, 121, 120, 119, 118, 117, 116, 115, 114, 113]
        volumes = [1000, 1100, 1200, 1100, 1000, 900, 1000, 1100, 1200, 1100,
                   1000, 900, 1000, 1100, 1200, 1100, 1000, 900, 1000, 1100]
        result = calculate_technicals(prices, volumes)
        assert "volume_ratio" in result
        assert "vol_ma5" in result


class TestSignalDeduplicator:
    """测试信号去重机制"""

    def test_signal_dedup_check_allowed(self):
        from app.services.signal_dedup import SignalDeduplicator, SignalType

        dedup = SignalDeduplicator()
        result = dedup.check_signal("BTC", SignalType.BUY)
        assert result.allowed == True
        assert result.status.value == "allowed"

    def test_signal_dedup_record_and_block(self):
        from app.services.signal_dedup import SignalDeduplicator, SignalType

        dedup = SignalDeduplicator()
        dedup.record_signal("BTC", SignalType.BUY, 50000, "Test", 7, 6)

        result = dedup.check_signal("BTC", SignalType.BUY)
        assert result.allowed == False
        assert result.status.value in ["blocked_cooldown", "blocked_duplicate"]

    def test_signal_dedup_different_signals(self):
        from app.services.signal_dedup import SignalDeduplicator, SignalType

        dedup = SignalDeduplicator()
        dedup.record_signal("BTC", SignalType.BUY, 50000, "Test", 7, 6)

        sell_result = dedup.check_signal("BTC", SignalType.SELL)
        assert sell_result.allowed == True

    def test_signal_dedup_force_clear(self):
        from app.services.signal_dedup import SignalDeduplicator, SignalType

        dedup = SignalDeduplicator()
        dedup.record_signal("BTC", SignalType.BUY, 50000, "Test", 7, 6)
        dedup.force_clear("BTC", SignalType.BUY)

        result = dedup.check_signal("BTC", SignalType.BUY)
        assert result.allowed == True


class TestExceptions:
    """测试异常类"""

    def test_trading_system_error(self):
        from app.core.exceptions import TradingSystemError, ErrorCode

        error = TradingSystemError("Test error", ErrorCode.TRADING_ERROR)
        assert error.message == "Test error"
        assert error.code == ErrorCode.TRADING_ERROR
        assert error.retry == False

    def test_insufficient_balance_error(self):
        from app.core.exceptions import InsufficientBalanceError

        error = InsufficientBalanceError(100, 50, "USDT")
        assert "余额不足" in error.message
        assert error.details["required"] == 100
        assert error.details["available"] == 50

    def test_signal_duplicate_error(self):
        from app.core.exceptions import SignalDuplicateError

        error = SignalDuplicateError("BTC", "buy", 50000, "12:00")
        assert "BTC" in error.message
        assert error.code.value == "504"

    def test_is_retryable_error(self):
        from app.core.exceptions import is_retryable_error, NetworkError, ValidationError

        assert is_retryable_error(NetworkError("network")) == True
        assert is_retryable_error(ValidationError("validation")) == False


class TestIndicators:
    """测试indicators.py中的函数"""

    def test_calculate_ma_from_indicators(self):
        from app.strategies.indicators import calculate_ma

        prices = [10, 20, 30, 40, 50]
        assert calculate_ma(prices, 3) == 40.0

    def test_calculate_rsi_from_indicators(self):
        from app.strategies.indicators import calculate_rsi

        prices = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28]
        result = calculate_rsi(prices, 14)
        assert 0 <= result <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])