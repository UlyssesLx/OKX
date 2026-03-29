from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    OKX_API_KEY: str = ""
    OKX_SECRET_KEY: str = ""
    OKX_PASSPHRASE: str = ""
    OKX_BASE_URL: str = "https://www.okx.com"

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/trading.db"
    REDIS_URL: Optional[str] = None

    LOG_LEVEL: str = "ERROR"
    TRADING_MODE: str = "simulation"

    # 金字塔加仓配置
    PYRAMID_ENABLED: bool = True  # 是否启用金字塔加仓
    PYRAMID_MAX_LAYERS: int = 3  # 最大加仓层数
    PYRAMID_DROP_THRESHOLD: float = -5.0  # 触发加仓的亏损阈值（%）
    PYRAMID_DROP_PER_LAYER: float = -10.0  # 每层加仓需要的下跌幅度（%）
    PYRAMID_MIN_TREND_SCORE: int = 6  # 金字塔加仓最低趋势评分
    PYRAMID_BASE_AMOUNT: float = 25.0  # 金字塔加仓基础金额（$）
    PYRAMID_LAYER_RATIOS: str = "1.0,0.6,0.35"  # 各层加仓比例（逗号分隔）
    PYRAMID_MAX_POSITION_PERCENT: float = 15.0  # 单一币种最大持仓占比（%）

    # 智能止损配置（与示例项目对齐）
    SMART_STOP_LOSS_ENABLED: bool = True  # 是否启用智能止损
    STOP_LOSS_TREND_8_PLUS: float = -3.0  # 趋势评分8+时的止损线（放宽至-3%，允许加仓）
    STOP_LOSS_TREND_6_7: float = -2.0  # 趋势评分6-7时的止损线
    STOP_LOSS_TREND_DEFAULT: float = -1.5  # 默认止损线
    STOP_LOSS_TIME_PROTECTION_MINUTES: int = 60  # 新建仓保护时间（分钟）

    # 止损拦截加仓配置（新增）
    PYRAMID_ON_STOP_LOSS_ENABLED: bool = True  # 是否在止损时优先加仓
    PYRAMID_ON_STOP_LOSS_TREND_SCORE: int = 8  # 止损时加仓的最低趋势评分
    PYRAMID_ON_STOP_LOSS_MAX_POSITION_PERCENT: float = 15.0  # 止损时加仓的最大仓位占比
    PYRAMID_ON_STOP_LOSS_MIN_CASH: float = 25.0  # 止损时加仓的最低可用资金

    # 动态止盈配置（与TradingConfig保持一致）
    DYNAMIC_TAKE_PROFIT_ENABLED: bool = True  # 是否启用动态止盈
    TAKE_PROFIT_TREND_9_10: float = 15.0  # 趋势评分9-10时的止盈线
    TAKE_PROFIT_TREND_7_8: float = 10.0  # 趋势评分7-8时的止盈线
    TAKE_PROFIT_TREND_5_6: float = 8.0  # 趋势评分5-6时的止盈线
    TAKE_PROFIT_TREND_DEFAULT: float = 6.0  # 默认止盈线
    PARTIAL_TAKE_PROFIT_PERCENT: float = 0.5  # 部分止盈比例（50%）

    # 外部数据源配置
    TWITTER_CONSUMER_KEY: str = ""  # Twitter API Consumer Key
    TWITTER_CONSUMER_SECRET: str = ""  # Twitter API Consumer Secret
    TWITTER_ACCESS_TOKEN: str = ""  # Twitter API Access Token
    TWITTER_ACCESS_TOKEN_SECRET: str = ""  # Twitter API Access Token Secret
    LUNARCRUSH_API_KEY: str = ""  # LunarCrush API Key
    ENABLE_RSS_MONITOR: bool = True  # 是否启用RSS监控
    ENABLE_TWITTER_MONITOR: bool = False  # 是否启用Twitter监控
    ENABLE_LUNARCRUSH_MONITOR: bool = False  # 是否启用LunarCrush监控

    # 飞书配置
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""
    FEISHU_CHAT_ID: str = ""
    FEISHU_NOTIFICATION_ENABLED: bool = True  # 是否启用飞书通知

    # 情绪融合配置
    SENTIMENT_FUSION_ENABLED: bool = False  # 是否启用情绪融合
    SENTIMENT_FUSION_MODE: str = "free"  # 情绪融合模式

    # LM Studio配置（AI策略迭代）
    LM_STUDIO_URL: str = "http://10.10.6.15:1234"
    LM_STUDIO_MODEL: str = "local-model"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
