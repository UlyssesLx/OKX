"""
v4.2 核心功能模块
包含：时区感知、买入金额递减、智能超仓豁免、动态波段计算
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from loguru import logger

BEIJING_TZ = timezone(timedelta(hours=8))


@dataclass
class TimeZoneConfig:
    """时区配置"""
    name: str  # 时段名称
    intensity: int  # 活跃强度 1-5
    position_min: float  # 最小仓位
    position_max: float  # 最大仓位
    hold_time_min: int  # 最小持仓时间（分钟）
    hold_time_max: int  # 最大持仓时间（分钟）
    daily_quota: float  # 日目标占比
    check_interval: int  # 检查频率（分钟）


class TimeZoneManager:
    """时区感知管理器"""

    # 6个时段配置（币市麻雀战法）
    TIME_ZONES = {
        "00:00-04:00": TimeZoneConfig(
            name="亚洲尾盘",
            intensity=1,
            position_min=5,
            position_max=8,
            hold_time_min=30,
            hold_time_max=60,
            daily_quota=0.10,
            check_interval=5
        ),
        "04:00-08:00": TimeZoneConfig(
            name="欧美交接",
            intensity=2,
            position_min=8,
            position_max=10,
            hold_time_min=20,
            hold_time_max=40,
            daily_quota=0.15,
            check_interval=5
        ),
        "08:00-12:00": TimeZoneConfig(
            name="亚洲早盘",
            intensity=5,
            position_min=12,
            position_max=15,
            hold_time_min=15,
            hold_time_max=60,
            daily_quota=0.30,
            check_interval=2
        ),
        "12:00-16:00": TimeZoneConfig(
            name="亚洲午盘",
            intensity=3,
            position_min=10,
            position_max=12,
            hold_time_min=20,
            hold_time_max=50,
            daily_quota=0.20,
            check_interval=5
        ),
        "16:00-20:00": TimeZoneConfig(
            name="欧洲早盘",
            intensity=5,
            position_min=12,
            position_max=15,
            hold_time_min=15,
            hold_time_max=60,
            daily_quota=0.30,
            check_interval=2
        ),
        "20:00-24:00": TimeZoneConfig(
            name="美国早盘",
            intensity=5,
            position_min=12,
            position_max=15,
            hold_time_min=10,
            hold_time_max=45,
            daily_quota=0.40,
            check_interval=2
        ),
    }

    @staticmethod
    def get_current_timezone_key() -> str:
        """获取当前时段的键值"""
        hour = datetime.now(BEIJING_TZ).hour

        if hour >= 0 and hour < 4:
            return "00:00-04:00"
        elif hour >= 4 and hour < 8:
            return "04:00-08:00"
        elif hour >= 8 and hour < 12:
            return "08:00-12:00"
        elif hour >= 12 and hour < 16:
            return "12:00-16:00"
        elif hour >= 16 and hour < 20:
            return "16:00-20:00"
        else:
            return "20:00-24:00"

    @staticmethod
    def get_current_config() -> TimeZoneConfig:
        """获取当前时段的配置"""
        key = TimeZoneManager.get_current_timezone_key()
        return TimeZoneManager.TIME_ZONES[key]

    @staticmethod
    def print_timezone_info():
        """打印时区信息"""
        config = TimeZoneManager.get_current_config()
        intensity = '⭐' * config.intensity

        logger.info("")
        logger.info("=" * 60)
        logger.info("🐦 币市麻雀战法 v4.2 - 时区感知")
        logger.info("=" * 60)
        logger.info(f"⏰ 当前时段: {TimeZoneManager.get_current_timezone_key()}")
        logger.info(f"📊 活跃强度: {intensity}")
        logger.info(f"💰 建议仓位: ${config.position_min}-${config.position_max}")
        logger.info(f"⏱️ 持仓时间: {config.hold_time_min}-{config.hold_time_max}分钟")
        logger.info(f"🎯 日目标占比: {int(config.daily_quota * 100)}%")
        logger.info(f"🔄 检查频率: {config.check_interval}分钟")
        logger.info("")


class DecreasingBuyManager:
    """买入金额递减管理器"""

    DEFAULT_FACTORS = [1.0, 0.6, 0.35, 0.2]  # 第1次100%，第2次60%，第3次35%，第4次及以后20%

    @staticmethod
    def calculate_amount(
        coin: str,
        base_amount: float,
        today_trades: List[Dict],
        factors: Optional[List[float]] = None
    ) -> float:
        """
        计算递减买入金额

        Args:
            coin: 币种名称
            base_amount: 基础金额
            today_trades: 今日交易列表
            factors: 递减系数列表

        Returns:
            调整后的金额
        """
        if factors is None:
            factors = DecreasingBuyManager.DEFAULT_FACTORS

        # 统计今日该币种的买入次数
        buy_count = sum(
            1 for t in today_trades
            if t.get('coin') == coin and t.get('action') == 'buy'
        )

        # 获取递减系数
        level = min(buy_count, len(factors) - 1)
        factor = factors[level]

        adjusted_amount = base_amount * factor

        if buy_count > 0:
            logger.info(f"  📉 {coin} 今日第{buy_count + 1}次买入，金额递减至{factor*100:.0f}%: ${adjusted_amount:.2f} USDT")

        return adjusted_amount


class ExemptionManager:
    """智能超仓豁免期管理器"""

    @staticmethod
    def calculate_exemption_minutes(unrealized_pnl_percent: float) -> int:
        """
        计算智能超仓豁免期（单位：分钟）
        根据当前盈亏状态返回豁免时长

        Args:
            unrealized_pnl_percent: 未实现盈亏百分比

        Returns:
            豁免分钟数
        """
        if unrealized_pnl_percent < -1:
            return 60  # 亏损>1%，60分钟
        elif unrealized_pnl_percent < 0:
            return 45  # 亏损0-1%，45分钟
        else:
            return 30  # 已盈利，30分钟

    @staticmethod
    def is_in_exemption_period(
        coin: str,
        unrealized_pnl_percent: float,
        last_buy_time: Optional[datetime],
        current_time: Optional[datetime] = None
    ) -> bool:
        """
        检查是否在超仓豁免期内

        Args:
            coin: 币种名称
            unrealized_pnl_percent: 未实现盈亏百分比
            last_buy_time: 最后买入时间
            current_time: 当前时间（可选，默认为当前时间）

        Returns:
            是否在豁免期内
        """
        if not last_buy_time:
            return False

        exemption_minutes = ExemptionManager.calculate_exemption_minutes(unrealized_pnl_percent)
        if exemption_minutes <= 0:
            return False

        if current_time is None:
            current_time = datetime.now(BEIJING_TZ)

        diff_minutes = (current_time - last_buy_time).total_seconds() / 60

        if diff_minutes < exemption_minutes:
            logger.info(f"  ⏳ {coin} 超仓豁免期内：{diff_minutes:.1f}/{exemption_minutes}分钟，盈亏{unrealized_pnl_percent:.2f}%")
            return True

        return False


class DynamicBandsCalculator:
    """动态波段计算器"""

    @staticmethod
    def calculate(
        coin: str,
        change_24h: float,
        volatility: float,
        turnover_24h: float,
        trend_score: int,
        base_stop_loss: float = -3.0,
        base_take_profit: float = 6.0
    ) -> Dict[str, any]:
        """
        动态波段计算
        根据波动率、市值、趋势动态调整止损止盈

        Args:
            coin: 币种名称
            change_24h: 24小时涨跌幅
            volatility: 波动率
            turnover_24h: 24小时成交额
            trend_score: 趋势评分
            base_stop_loss: 基础止损百分比
            base_take_profit: 基础止盈百分比

        Returns:
            包含止损止盈和计算因子的字典
        """
        # 计算波动系数 (0.5 ~ 2.0)
        volatility_factor = min(2.0, max(0.5, volatility / 3))

        # 市值系数 (0.6 ~ 1.2) - 基于成交额估算
        if turnover_24h > 1000000000:
            market_cap_factor = 1.2  # 大市值
            market_cap_level = "large"
        elif turnover_24h > 100000000:
            market_cap_factor = 1.0  # 中市值
            market_cap_level = "medium"
        else:
            market_cap_factor = 0.6  # 小市值
            market_cap_level = "small"

        # 趋势系数 (0.8 ~ 1.2)
        trend_factor = 1.2 if trend_score >= 8 else (1.0 if trend_score >= 6 else 0.8)

        # 计算动态值
        dynamic_stop_loss = base_stop_loss * volatility_factor * market_cap_factor * trend_factor
        dynamic_take_profit = base_take_profit * volatility_factor * market_cap_factor * trend_factor

        # 限制范围
        dynamic_stop_loss = max(-8.0, min(-1.0, dynamic_stop_loss))
        dynamic_take_profit = max(2.0, min(15.0, dynamic_take_profit))

        logger.info(f"  📊 {coin} 动态波段计算:")
        logger.info(f"     波动率: {volatility:.2f}%, 24h涨跌: {change_24h:.2f}%")
        logger.info(f"     市值级别: {market_cap_level}, 波动系数: {volatility_factor:.2f}")
        logger.info(f"     市值系数: {market_cap_factor:.2f}, 趋势系数: {trend_factor:.2f}")
        logger.info(f"     动态止损: {dynamic_stop_loss:.2f}%, 动态止盈: {dynamic_take_profit:.2f}%")

        return {
            "stop_loss": dynamic_stop_loss,
            "take_profit": dynamic_take_profit,
            "volatility": volatility,
            "market_cap_level": market_cap_level,
            "factors": {
                "volatility_factor": volatility_factor,
                "market_cap_factor": market_cap_factor,
                "trend_factor": trend_factor
            }
        }


# 导出全局实例
timezone_manager = TimeZoneManager()
decreasing_buy_manager = DecreasingBuyManager()
exemption_manager = ExemptionManager()
dynamic_bands_calculator = DynamicBandsCalculator()
