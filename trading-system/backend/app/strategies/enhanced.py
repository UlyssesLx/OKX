from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime
import json
import os
import aiofiles
from app.core.okx_client import OKXClient


@dataclass
class BearishCandleResult:
    is_bearish: bool
    drop_percent: float = 0.0
    rsi: float = 50.0
    volume_ratio: float = 1.0
    reason: str = ""
    consecutive_count: int = 0


@dataclass
class BullishCandleResult:
    is_bullish: bool
    rise_percent: float = 0.0
    rsi: float = 50.0
    volume_ratio: float = 1.0
    reason: str = ""
    consecutive_count: int = 0


@dataclass
class SidewaysResult:
    is_sideways: bool
    volatility: float = 0.0
    periods: int = 0
    reason: str = ""


@dataclass
class CrashReboundResult:
    is_crash_rebound: bool
    drop_24h: float = 0.0
    trend_score: int = 0
    rsi: float = 50.0
    reason: str = ""


class BearishCandleConfig:
    enabled: bool = True
    consecutive_count: int = 2
    min_trend_score: int = 6
    price_below_ma: bool = True
    rsi_enabled: bool = True
    rsi_period: int = 14
    rsi_oversold: int = 40
    volume_enabled: bool = True
    volume_ratio: float = 1.2
    candle_interval: str = "5m"


class SidewaysConfig:
    enabled: bool = True
    trend_score_min: int = 3
    trend_score_max: int = 5
    max_volatility: float = 0.5
    min_periods: int = 3


class CrashReboundConfig:
    enabled: bool = True
    min_drop_24h: float = 10.0  # 24h跌幅阈值 >= 10%（对齐示例项目）
    min_trend_score: int = 6    # 趋势评分 >= 6（对齐示例项目）
    min_rebound_percent: float = 2.0  # 最小反弹幅度 2%（对齐示例项目）
    rsi_check_enabled: bool = False   # 不检查RSI（对齐示例项目）
    rsi_oversold: int = 35
    volume_check_enabled: bool = False  # 不检查成交量（对齐示例项目）
    volume_multiplier: float = 2.0


BEARISH_CANDLE_CONFIG = BearishCandleConfig()
CRASH_REBOUND_CONFIG = CrashReboundConfig()


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    
    gains = 0.0
    losses = 0.0
    
    for i in range(len(prices) - period, len(prices)):
        change = prices[i] - prices[i - 1]
        if change > 0:
            gains += change
        else:
            losses -= change
    
    avg_gain = gains / period
    avg_loss = losses / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1 + rs))


async def check_consecutive_bearish_candles(
    client: OKXClient,
    inst_id: str,
    current_price: float,
    config: BearishCandleConfig = None
) -> BearishCandleResult:
    if config is None:
        config = BEARISH_CANDLE_CONFIG
    
    if not config.enabled:
        return BearishCandleResult(is_bearish=False, reason="阴线买入策略未启用")
    
    try:
        result = await client.get_candles(inst_id, bar=config.candle_interval, limit=50)
        candles = result.get("data", [])
        
        if not candles or len(candles) < 20:
            return BearishCandleResult(is_bearish=False, reason="K线数据不足")
        
        data = []
        for c in candles:
            data.append({
                "open": float(c[1]),
                "high": float(c[2]),
                "low": float(c[3]),
                "close": float(c[4]),
                "volume": float(c[5])
            })
        data.reverse()
        
        recent_candles = data[-config.consecutive_count:]
        is_all_bearish = all(c["close"] < c["open"] for c in recent_candles)
        
        prices = [d["close"] for d in data]
        ma5 = sum(prices[-5:]) / 5
        
        below_ma = current_price < ma5
        
        rsi_check = True
        rsi_value = 50.0
        if config.rsi_enabled:
            rsi_value = calculate_rsi(prices, config.rsi_period)
            rsi_check = rsi_value < config.rsi_oversold
        
        volume_check = True
        volume_ratio = 1.0
        if config.volume_enabled and len(recent_candles) >= 2:
            vol1 = recent_candles[0]["volume"]
            vol2 = recent_candles[1]["volume"]
            volume_ratio = vol2 / vol1 if vol1 > 0 else 1.0
            volume_check = volume_ratio >= config.volume_ratio
        
        if is_all_bearish and below_ma and rsi_check and volume_check:
            drop_percent = ((recent_candles[0]["open"] - recent_candles[-1]["close"]) / recent_candles[0]["open"] * 100)
            return BearishCandleResult(
                is_bearish=True,
                drop_percent=drop_percent,
                rsi=rsi_value,
                volume_ratio=volume_ratio,
                reason=f"连续{config.consecutive_count}根阴线，RSI{rsi_value:.1f}超卖，成交量{volume_ratio:.2f}x放量"
            )
        
        reasons = []
        if not is_all_bearish:
            reasons.append("非连续阴线")
        if not below_ma:
            reasons.append("价格未低于MA5")
        if not rsi_check:
            reasons.append(f"RSI未超卖({rsi_value:.1f})")
        if not volume_check:
            reasons.append(f"成交量未放量({volume_ratio:.2f}x)")
        
        return BearishCandleResult(
            is_bearish=False,
            rsi=rsi_value,
            volume_ratio=volume_ratio,
            reason=", ".join(reasons)
        )
    
    except Exception as e:
        return BearishCandleResult(is_bearish=False, reason=f"检查失败: {str(e)}")


async def check_consecutive_bullish_candles(
    client: OKXClient,
    inst_id: str,
    current_price: float,
    config: BearishCandleConfig = None
) -> BullishCandleResult:
    if config is None:
        config = BEARISH_CANDLE_CONFIG

    if not config.enabled:
        return BullishCandleResult(is_bullish=False, reason="阳线卖出策略未启用")

    try:
        result = await client.get_candles(inst_id, bar=config.candle_interval, limit=50)
        candles = result.get("data", [])

        if not candles or len(candles) < 20:
            return BullishCandleResult(is_bullish=False, reason="K线数据不足")

        data = []
        for c in candles:
            data.append({
                "open": float(c[1]),
                "high": float(c[2]),
                "low": float(c[3]),
                "close": float(c[4]),
                "volume": float(c[5])
            })
        data.reverse()

        recent_candles = data[-config.consecutive_count:]
        is_all_bullish = all(c["close"] > c["open"] for c in recent_candles)

        prices = [d["close"] for d in data]
        ma5 = sum(prices[-5:]) / 5

        above_ma = current_price > ma5

        rsi_check = True
        rsi_value = 50.0
        if config.rsi_enabled:
            rsi_value = calculate_rsi(prices, config.rsi_period)
            rsi_check = rsi_value > config.rsi_oversold

        volume_check = True
        volume_ratio = 1.0
        if config.volume_enabled and len(recent_candles) >= 2:
            vol1 = recent_candles[0]["volume"]
            vol2 = recent_candles[1]["volume"]
            volume_ratio = vol2 / vol1 if vol1 > 0 else 1.0
            volume_check = volume_ratio >= config.volume_ratio

        if is_all_bullish and above_ma and rsi_check and volume_check:
            rise_percent = ((recent_candles[-1]["close"] - recent_candles[0]["open"]) / recent_candles[0]["open"] * 100)
            return BullishCandleResult(
                is_bullish=True,
                rise_percent=rise_percent,
                rsi=rsi_value,
                volume_ratio=volume_ratio,
                reason=f"连续{config.consecutive_count}根阳线，RSI{rsi_value:.1f}超买，成交量{volume_ratio:.2f}x放量",
                consecutive_count=len(recent_candles)
            )

        reasons = []
        if not is_all_bullish:
            reasons.append("非连续阳线")
        if not above_ma:
            reasons.append("价格未高于MA5")
        if not rsi_check:
            reasons.append(f"RSI未超买({rsi_value:.1f})")
        if not volume_check:
            reasons.append(f"成交量未放量({volume_ratio:.2f}x)")

        return BullishCandleResult(
            is_bullish=False,
            rsi=rsi_value,
            volume_ratio=volume_ratio,
            reason=", ".join(reasons),
            consecutive_count=0
        )

    except Exception as e:
        return BullishCandleResult(is_bullish=False, reason=f"检查失败: {str(e)}")


class SidewaysManager:
    def __init__(self, data_file: str = "./data/sideways_status.json"):
        self.config = SidewaysConfig()
        self.data_file = data_file
        self.status: Dict[str, Dict] = {}
        self._load_status()
    
    def _load_status(self):
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.status = json.load(f)
            except Exception:
                pass
    
    async def _save_status(self):
        async with aiofiles.open(self.data_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(self.status, indent=2, ensure_ascii=False))
    
    async def check_sideways(
        self,
        client: OKXClient,
        inst_id: str,
        trend_score: int
    ) -> SidewaysResult:
        if not self.config.enabled:
            return SidewaysResult(is_sideways=False, reason="横盘检测未启用")
        
        if trend_score < self.config.trend_score_min or trend_score > self.config.trend_score_max:
            return SidewaysResult(
                is_sideways=False,
                reason=f"趋势评分{trend_score}不在横盘范围[{self.config.trend_score_min}-{self.config.trend_score_max}]"
            )
        
        try:
            result = await client.get_candles(inst_id, bar="1H", limit=10)
            candles = result.get("data", [])
            
            if not candles or len(candles) < 5:
                return SidewaysResult(is_sideways=False, reason="K线数据不足")
            
            prices = [float(c[4]) for c in candles]
            avg_price = sum(prices) / len(prices)
            
            max_price = max(prices)
            min_price = min(prices)
            volatility = ((max_price - min_price) / avg_price * 100) if avg_price > 0 else 0
            
            if volatility <= self.config.max_volatility:
                coin = inst_id.replace("-USDT", "")
                
                if coin not in self.status:
                    self.status[coin] = {"periods": 0, "since": None}
                
                self.status[coin]["periods"] += 1
                if self.status[coin]["since"] is None:
                    self.status[coin]["since"] = datetime.now().isoformat()
                
                await self._save_status()
                
                return SidewaysResult(
                    is_sideways=True,
                    volatility=volatility,
                    periods=self.status[coin]["periods"],
                    reason=f"波动率{volatility:.2f}%<={self.config.max_volatility}%，横盘{self.status[coin]['periods']}周期"
                )
            
            coin = inst_id.replace("-USDT", "")
            if coin in self.status:
                del self.status[coin]
                await self._save_status()
            
            return SidewaysResult(
                is_sideways=False,
                volatility=volatility,
                reason=f"波动率{volatility:.2f}%>{self.config.max_volatility}%"
            )
        
        except Exception as e:
            return SidewaysResult(is_sideways=False, reason=f"检查失败: {str(e)}")
    
    def is_paused(self, coin: str) -> bool:
        if coin in self.status:
            return self.status[coin].get("periods", 0) >= self.config.min_periods
        return False
    
    async def reset(self, coin: str):
        if coin in self.status:
            del self.status[coin]
            await self._save_status()
    
    async def reset_all(self):
        self.status.clear()
        await self._save_status()
    
    @property
    def status_summary(self) -> Dict:
        return {
            "enabled": self.config.enabled,
            "paused_coins": list(self.status.keys()),
            "details": self.status
        }


async def check_crash_rebound(
    client: OKXClient,
    inst_id: str,
    trend_score: int,
    config: CrashReboundConfig = None
) -> CrashReboundResult:
    if config is None:
        config = CRASH_REBOUND_CONFIG
    
    if not config.enabled:
        return CrashReboundResult(is_crash_rebound=False, reason="暴跌反弹策略未启用")
    
    try:
        ticker_result = await client.get_ticker(inst_id)
        ticker_data = ticker_result.get("data", [{}])[0]
        
        last_price = float(ticker_data.get("last", 0))
        open_price = float(ticker_data.get("open24h", last_price))
        drop_24h = ((open_price - last_price) / open_price * 100) if open_price > 0 else 0
        
        if drop_24h < config.min_drop_24h:
            return CrashReboundResult(
                is_crash_rebound=False,
                drop_24h=drop_24h,
                reason=f"24h跌幅{drop_24h:.1f}%<{config.min_drop_24h}%"
            )
        
        if trend_score < config.min_trend_score:
            return CrashReboundResult(
                is_crash_rebound=False,
                drop_24h=drop_24h,
                trend_score=trend_score,
                reason=f"趋势评分{trend_score}<{config.min_trend_score}"
            )
        
        rsi_value = 50.0
        if config.rsi_check_enabled:
            candles_result = await client.get_candles(inst_id, bar="1H", limit=20)
            candles = candles_result.get("data", [])
            
            if candles:
                prices = [float(c[4]) for c in candles]
                prices.reverse()
                rsi_value = calculate_rsi(prices, 14)
            
            if rsi_value > config.rsi_oversold:
                return CrashReboundResult(
                    is_crash_rebound=False,
                    drop_24h=drop_24h,
                    trend_score=trend_score,
                    rsi=rsi_value,
                    reason=f"RSI{rsi_value:.1f}>{config.rsi_oversold}，未超卖"
                )
        
        return CrashReboundResult(
            is_crash_rebound=True,
            drop_24h=drop_24h,
            trend_score=trend_score,
            rsi=rsi_value,
            reason=f"24h暴跌{drop_24h:.1f}%，趋势回升{trend_score}分"
        )
    
    except Exception as e:
        return CrashReboundResult(is_crash_rebound=False, reason=f"检查失败: {str(e)}")


class EmergencyStop:
    def __init__(self, flag_file: str = "./data/EMERGENCY_STOP.flag"):
        self.flag_file = flag_file
        os.makedirs(os.path.dirname(flag_file), exist_ok=True)
    
    def is_stopped(self) -> bool:
        return os.path.exists(self.flag_file)
    
    def stop(self, reason: str = "紧急停止") -> bool:
        try:
            with open(self.flag_file, 'w', encoding='utf-8') as f:
                f.write(f"{reason}\n")
                f.write(f"stopped_at: {datetime.now().isoformat()}\n")
            return True
        except Exception:
            return False
    
    def resume(self) -> bool:
        try:
            if os.path.exists(self.flag_file):
                os.remove(self.flag_file)
            return True
        except Exception:
            return False
    
    def get_stop_info(self) -> Optional[Dict[str, str]]:
        if not self.is_stopped():
            return None
        
        try:
            with open(self.flag_file, 'r', encoding='utf-8') as f:
                content = f.read()
            lines = content.strip().split('\n')
            reason = lines[0] if lines else "未知原因"
            stopped_at = None
            for line in lines[1:]:
                if line.startswith("stopped_at:"):
                    stopped_at = line.split(":", 1)[1].strip()
            return {"reason": reason, "stopped_at": stopped_at}
        except Exception:
            return {"reason": "紧急停止", "stopped_at": None}


sideways_manager = SidewaysManager()
emergency_stop = EmergencyStop()
