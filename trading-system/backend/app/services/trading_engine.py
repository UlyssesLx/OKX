import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
import json
import os
import random
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

from app.core.okx_client import OKXClient
from app.strategies.indicators import analyze_trend, validate_technical_indicators
from app.strategies.resonance import check_market_environment, calculate_resonance_score, check_capital_flow
from app.strategies.enhanced import (
    check_consecutive_bearish_candles,
    check_consecutive_bullish_candles,
    sideways_manager,
    emergency_stop
)
from app.strategies.pyramid import PyramidManager, PyramidConfig

BEIJING_TZ = timezone(timedelta(hours=8))
from app.services.blacklist_manager import blacklist_manager
from app.services.trade_stats import trade_stats, TradeRecord
from app.services.simulation_manager import simulation_manager
from app.services.notification_agent import feishu_notifier
from app.services.sentiment_service import sentiment_service
from app.services.signal_dedup import signal_dedup, SignalType, DedupStatus
from app.core.logger import TradingLogger, log_execution_time
from app.services.strategy_evolution import strategy_evolution


@dataclass
class TradingSignal:
    coin: str
    action: str
    price: float
    amount: float
    reason: str
    trend_score: int
    resonance_score: int
    signal_type: str
    timestamp: datetime
    strategy: str = ""
    side: str = "long"


@dataclass
class TradingConfig:
    # 核心配置（与crypto-trading-bot-master ai_trading_bot.js完全对齐）
    max_position_percent: float = 35.0  # 单币种最大仓位35%
    max_daily_trades: int = 9999  # 每日最大交易次数（已取消限制，满足条件即可交易）
    max_daily_volume: float = 1000.0  # 每日最大交易量$1000
    stop_loss_percent: float = -1.0  # 短线策略止损-1%
    take_profit_percent: float = 5.0  # 止盈线+5%（短线策略第二止盈位）
    sentiment_threshold: int = 7  # 舆情买入阈值(>7分买入)
    sentiment_sell_threshold: int = 3  # 舆情卖出阈值(<3分卖出)
    short_sentiment_threshold: int = 3  # 舆情做空阈值(<=3分做空)
    min_cash_reserve: float = 30.0  # 最小现金保留30%
    trade_size: float = 32.0  # 单笔交易金额$32（普通策略）
    short_term_trade_size: float = 40.0  # 单笔交易金额$40（短线策略）
    buy_cooldown_minutes: int = 30  # 默认买入冷却期30分钟
    trend_weak_threshold: int = 3  # 趋势转弱阈值（<=此值卖出）
    sideways_min_score: int = 3  # 横盘趋势评分下限
    sideways_max_score: int = 5  # 横盘趋势评分上限

    # 分层冷却期配置
    tiered_cooldown_enabled: bool = True  # 启用分层冷却期
    cooldown_trend_10: int = 15  # 趋势10分：冷却期15分钟
    cooldown_trend_8_9: int = 20  # 趋势8-9分：冷却期20分钟
    cooldown_trend_6_7: int = 30  # 趋势6-7分：冷却期30分钟
    cooldown_score_tier1: int = 10  # 冷却期第一档评分阈值
    cooldown_score_tier2: int = 8  # 冷却期第二档评分阈值
    cooldown_score_tier3: int = 6  # 冷却期第三档评分阈值

    # 波动率筛选配置
    volatility_filter_enabled: bool = True  # 启用波动率筛选
    volatility_min: float = 0.5  # 最小波动率0.5%
    volatility_preferred: float = 1.5  # 优选波动率1.5%
    cooldown_high_volatility: float = 5.0  # 高波动阈值（缩短冷却期）
    cooldown_low_volatility: float = 2.0  # 低波动阈值（延长冷却期）
    cooldown_high_volatility_multiplier: float = 0.7  # 高波动冷却期缩短比例
    cooldown_low_volatility_multiplier: float = 1.3  # 低波动冷却期延长比例

    # 回调加仓阈值
    pullback_buy_threshold: float = 0.97  # 回调加仓阈值：减仓后价格需≤减仓价的97%
    pullback_buy_enabled: bool = True  # 启用回调加仓检查
    
    # 实时盈亏验证 - 防止追高
    pnl_check_enabled: bool = True  # 启用实时盈亏验证
    pnl_check_threshold: float = -1.0  # 亏损阈值（<-1%禁止买入）
    pnl_check_adjust_score: bool = True  # 亏损时降低趋势评分
    
    # 黑名单趋势反转检查
    blacklist_trend_check_enabled: bool = True  # 启用黑名单趋势检查
    blacklist_trend_threshold: int = 8  # 趋势评分阈值（≥8分）
    blacklist_trend_count: int = 2  # 连续次数（2次）
    blacklist_high_threshold: int = 9  # 高分阈值（单次≥9分立即解除）
    
    # 买入金额递减
    decreasing_trade_size_enabled: bool = True  # 启用买入金额递减
    decreasing_factors: str = "1.0,0.6,0.35,0.2"  # 递减比例：第1次100%，第2次60%，第3次35%，第4次及以后20%
    
    # 止盈单管理
    take_profit_order_enabled: bool = True  # 启用止盈单
    take_profit_order_partial: float = 0.5  # 止盈单仓位比例（50%）
    take_profit_adjust_on_bad_sentiment: bool = True  # 舆情极差时收紧止盈
    take_profit_bad_sentiment_threshold: int = 3  # 舆情≤3分时收紧止盈
    
    # 黄金稳定币特殊处理
    gold_stablecoin_special_handling: bool = True  # 启用黄金稳定币特殊处理
    gold_stablecoin_list: str = "XAUT,PAXG"  # 黄金稳定币列表
    gold_stablecoin_take_profit: float = 0.2  # 黄金稳定币止盈目标0.2%

    # 智能超仓豁免期配置（单位：分钟）
    over_position_exemption_enabled: bool = True  # 启用智能豁免期
    exemption_loss_high: int = 60  # 亏损>1%，豁免60分钟
    exemption_loss_medium: int = 45  # 亏损0-1%，豁免45分钟
    exemption_profit: int = 30  # 已盈利，豁免30分钟

    # 抄底策略配置 - 完全对齐 ai_trading_bot.js 的 dipBuy 配置
    dip_buy_enabled: bool = True  # 启用优化抄底策略
    dip_buy_min_trend_score: int = 7  # 趋势评分≥7分
    dip_buy_min_btc_trend: int = 6  # BTC趋势≥6分
    dip_buy_min_eth_trend: int = 5  # ETH趋势≥5分
    dip_buy_rsi_threshold: float = 35.0  # RSI<35（超卖）
    dip_buy_volume_multiplier: float = 2.0  # 成交量>2倍平均
    dip_buy_min_consecutive_bearish: int = 3  # 连续3根阴线
    dip_buy_require_bullish_reversal: bool = True  # 需要第4根收阳
    dip_buy_price_below_ma5: bool = True  # 价格<MA5
    dip_buy_price_below_ma10: bool = True  # 价格<MA10
    
    # 阴线买入配置 - 对齐 strategy-enhanced.js 的 BEARISH_CANDLE_CONFIG
    bearish_candle_enabled: bool = True  # 启用阴线买入
    bearish_candle_consecutive_count: int = 2  # 连续阴线数量
    bearish_candle_min_trend_score: int = 6  # 最小趋势评分
    bearish_candle_price_below_ma: bool = True  # 价格需低于MA
    bearish_candle_rsi_enabled: bool = True  # RSI验证
    bearish_candle_rsi_oversold: int = 40  # RSI超卖阈值
    bearish_candle_volume_enabled: bool = True  # 成交量验证
    bearish_candle_volume_ratio: float = 1.2  # 成交量比例
    bullish_fallback_threshold: int = 7  # 买入Fallback阈值（bullish_score < 此值才检查阴线买入）
    bearish_candle_interval: str = '5m'  # K线周期
    
    # 暴跌反弹策略配置 - 对齐 strategy-enhanced.js 的 CRASH_REBOUND_CONFIG
    crash_rebound_enabled: bool = True  # 启用暴跌反弹策略
    crash_rebound_threshold: float = -10.0  # 24h跌幅阈值 -10%
    crash_rebound_min_trend_score: int = 6  # 反弹时趋势评分>=6分
    crash_rebound_min_rebound_percent: float = 2.0  # 最小反弹幅度 2%
    crash_rebound_rsi_check_enabled: bool = False  # RSI检查开关
    crash_rebound_rsi_threshold: float = 30.0  # RSI超卖阈值
    crash_rebound_volume_check_enabled: bool = False  # 成交量检查开关
    crash_rebound_volume_ratio: float = 1.5  # 成交量放大阈值

    # 短线策略参数 - 完全对齐示例项目 indicators.py 趋势判断逻辑
    long_min_bullish_score: int = 7  # 买入最小看涨评分（>=7看涨，对齐示例项目）
    long_bullish_gap: int = 2  # 看涨评分需领先看跌评分2分以上（对齐示例项目）
    long_min_trend_score: int = 6  # 趋势评分下限 >= 6分（对齐最新版示例项目）
    long_max_trend_score: int = 10  # 趋势评分上限 <= 10分
    long_rsi_min: float = 30.0  # RSI下限 >= 30（对齐最新版示例项目）
    long_rsi_max: float = 70.0  # RSI上限 <= 70（对齐最新版示例项目）
    long_min_volume_ratio: float = 0.8  # 成交量 >= 0.8x（对齐最新版示例项目）
    long_max_pullback_percent: float = 8.0  # 24h涨跌上限 <= +8%（对齐最新版示例项目）
    long_min_pullback_percent: float = -5.0  # 24h涨跌下限 >= -5%（对齐最新版示例项目）
    long_min_market_trend: int = 4  # 大盘趋势 >= 4分（对齐最新版示例项目）
    long_position_size: float = 40.0  # 单笔金额 $40（对齐最新版示例项目）
    long_position_ratio: float = 1.0  # 买入仓位比例
    long_max_positions: int = 3  # 最大持仓3个
    long_max_position_percent: float = 15.0  # 单个币种最大占比15%（对齐最新版示例项目）
    long_stop_loss_percent: float = 1.5  # 止损 -1.5%（对齐最新版示例项目）
    long_take_profit_percent: float = 3.0  # 止盈 +3%
    long_take_profit_1: float = 1.0  # 第一止盈 +1%（对齐最新版示例项目）
    long_take_profit_2: float = 2.0  # 第二止盈 +2%（对齐最新版示例项目）
    long_time_stop: int = 48  # 时间止损 48小时（对齐最新版示例项目）
    long_min_trade_interval: int = 120  # 同一币种最小交易间隔2小时（分钟，对齐最新版示例项目）
    long_max_daily_trades: int = 5  # 每日最大交易笔数（对齐最新版示例项目）
    long_min_volatility: float = 0.3  # 最小波动率0.3%（对齐最新版示例项目）
    long_max_volatility: float = 5.0  # 最大波动率5%（对齐最新版示例项目）

    # 止损拦截加仓配置（与示例项目对齐）
    pyramid_on_stop_loss_enabled: bool = True  # 是否在止损时优先加仓
    pyramid_on_stop_loss_trend_score: int = 8  # 止损时加仓的最低趋势评分
    pyramid_on_stop_loss_max_position_percent: float = 15.0  # 止损时加仓的最大仓位占比
    pyramid_on_stop_loss_min_cash: float = 25.0  # 止损时加仓的最低可用资金

    # 短线策略配置 - 完全对齐 short_term.py 的 ShortTermConfig
    short_term_min_trend_score: int = 6  # 趋势评分 >= 6分（与ShortTermConfig一致）
    short_term_max_trend_score: int = 10  # 趋势评分 <= 10分
    short_term_rsi_min: float = 30.0  # RSI >= 30（与ShortTermConfig一致）
    short_term_rsi_max: float = 70.0  # RSI <= 70（与ShortTermConfig一致）
    short_term_min_volume_ratio: float = 0.8  # 成交量 >= 0.8x（与ShortTermConfig一致）
    short_term_max_24h_change: float = 8.0  # 24h涨跌幅 <= +8%（与ShortTermConfig一致）
    short_term_min_24h_change: float = -5.0  # 24h涨跌幅 >= -5%（与ShortTermConfig一致）
    short_term_position_size: float = 40.0  # 单笔金额 $40
    short_term_max_positions: int = 3  # 最大持仓3个
    short_term_stop_loss: float = -1.5  # 止损 -1.5%（与ShortTermConfig一致）
    short_term_take_profit_1: float = 1.0  # 止盈1 +1%（与ShortTermConfig一致）
    short_term_take_profit_2: float = 2.0  # 止盈2 +2%（与ShortTermConfig一致）
    short_term_time_stop: int = 48  # 时间止损 48小时（与ShortTermConfig一致）

    # 做空相关参数（与开多逻辑对称）
    short_min_bearish_score: int = 7  # 做空最小看跌评分（>=7看跌，对应做多min_bullish_score）
    short_bearish_gap: int = 2  # 看跌评分需领先看涨评分2分以上（与做多long_bullish_gap对称）
    short_min_trend_score: int = 0  # 做空趋势评分下限
    short_max_trend_score: int = 4  # 做空趋势评分上限（<=4表示下跌趋势）
    short_max_btc_trend: int = 4  # BTC趋势上限
    short_max_eth_trend: int = 4  # ETH趋势上限
    short_rsi_min: float = 30.0  # 做空RSI下限（适中，与做多一致）
    short_rsi_max: float = 70.0  # 做空RSI上限（适中，与做多一致）
    short_min_volume_ratio: float = 0.8  # 做空最小量比（与做多一致）
    short_min_pullback_percent: float = -8.0  # 做空24h涨跌下限（对应做多min_pullback_percent）
    short_max_pullback_percent: float = 5.0  # 做空24h涨跌上限（对应做多max_pullback_percent）
    short_max_market_trend: int = 4  # 做空大盘趋势上限（<=4表示大盘弱势，对应做多min_market_trend）
    short_position_size: float = 40.0  # 做空单笔金额 $40
    short_position_ratio: float = 1.0  # 做空仓位比例
    short_max_positions: int = 3  # 最大空单持仓数
    short_max_position_percent: float = 15.0  # 做空单币最大占比15%
    short_stop_loss_percent: float = 1.5  # 做空止损百分比（价格上涨触发）
    short_take_profit_1: float = 1.0  # 做空第一止盈 +1%
    short_take_profit_2: float = 2.0  # 做空第二止盈 +2%
    short_time_stop: int = 48  # 做空时间止损 48小时
    short_min_trade_interval: int = 120  # 做空最小交易间隔 2小时（分钟）
    short_max_daily_trades: int = 5  # 做空每日最大交易数
    short_min_volatility: float = 0.3  # 做空最小波动率0.3%
    short_max_volatility: float = 5.0  # 做空最大波动率5%

    # 做空递减买入配置
    short_decreasing_buy_enabled: bool = True  # 启用做空递减买入
    short_cooldown_trend_1: int = 15  # 趋势评分1的冷却期（分钟）
    short_cooldown_trend_2_3: int = 20  # 趋势评分2-3的冷却期（分钟）
    short_cooldown_trend_4: int = 30  # 趋势评分4的冷却期（分钟）
    short_cooldown_score_tier1: int = 9  # 做空冷却期第一档评分阈值
    short_cooldown_score_tier2: int = 7  # 做空冷却期第二档评分阈值
    short_rally_enabled: bool = True  # 启用做空上涨拦截
    short_rally_threshold: float = 1.03  # 做空上涨阈值（与做多对称）
    short_take_profit_percent: float = 3.0  # 做空止盈百分比

    # 做空金字塔加仓配置（与做多金字塔对称）
    short_pyramid_enabled: bool = True  # 启用做空金字塔加仓
    short_pyramid_max_layers: int = 3  # 做空金字塔最大层数
    short_pyramid_drop_threshold: float = -3.0  # 做空亏损触发阈值（价格上涨时触发，与做多对称）
    short_pyramid_max_trend_score: int = 4  # 做空趋势评分上限（超过则禁止加仓）
    short_pyramid_layer_ratios: str = "1.0,0.6,0.35,0.2"  # 做空金字塔每层比例
    short_pyramid_base_amount: float = 25.0  # 做空金字塔加仓基础金额

    # 做空豁免期配置
    short_exemption_enabled: bool = True  # 启用做空豁免期
    short_exemption_loss_high: int = 60  # 亏损>1%，豁免60分钟
    short_exemption_loss_medium: int = 45  # 亏损0-1%，豁免45分钟
    short_exemption_profit: int = 30  # 已盈利，豁免30分钟
    short_min_cash_reserve: float = 30.0  # 做空最小现金保留30%

    # 做空止损补仓配置（与做多对称）
    short_pyramid_on_stop_loss_enabled: bool = True  # 是否在止损时优先加仓
    short_pyramid_on_stop_loss_trend_score: int = 8  # 止损时加仓的最低趋势评分
    short_pyramid_on_stop_loss_max_position_percent: float = 15.0  # 止损时加仓的最大仓位占比
    short_pyramid_on_stop_loss_min_cash: float = 25.0  # 止损时加仓的最低可用资金

    # 做空60分钟持仓保护配置（与做多对称）
    short_stop_loss_time_protection_enabled: bool = True  # 启用持仓时间保护
    short_stop_loss_time_protection_minutes: int = 60  # 最短持仓时间（分钟）

    # 做空超仓豁免配置（与做多对称）
    short_over_position_exemption_enabled: bool = True  # 启用超仓豁免
    short_over_position_exemption_loss_high: int = 60  # 亏损>1%，豁免60分钟
    short_over_position_exemption_loss_medium: int = 45  # 亏损0-1%，豁免45分钟
    short_over_position_exemption_profit: int = 30  # 已盈利，豁免30分钟

    # 严格追空策略参数（与严格抄底对称）
    short_dip_enabled: bool = True  # 启用严格追空
    short_dip_max_trend_score: int = 4  # 趋势评分上限 <= 4分
    short_dip_max_btc_trend: int = 4  # BTC趋势上限
    short_dip_max_eth_trend: int = 4  # ETH趋势上限
    short_dip_rsi_threshold: float = 65.0  # RSI超买阈值 > 65
    short_dip_volume_multiplier: float = 2.0  # 成交量倍数 > 2倍
    short_dip_min_consecutive_bullish: int = 3  # 连续阳线数 >= 3根
    short_dip_require_bearish_reversal: bool = True  # 需要收阴确认
    short_dip_price_above_ma5: bool = True  # 价格高于MA5
    short_dip_price_above_ma10: bool = True  # 价格高于MA10

    # 阳线做空策略参数（与阴线买入对称）
    short_bearish_enabled: bool = True  # 启用阳线做空
    short_bearish_consecutive_count: int = 2  # 连续阳线数量
    short_bearish_max_trend_score: int = 4  # 趋势评分上限
    short_bearish_price_above_ma: bool = True  # 价格需高于MA5
    short_bearish_rsi_enabled: bool = True  # 启用RSI验证
    short_bearish_rsi_period: int = 14  # RSI周期
    short_bearish_rsi_overbought: float = 70.0  # RSI超买阈值
    short_bearish_volume_enabled: bool = True  # 启用成交量验证
    short_bearish_volume_ratio: float = 1.2  # 成交量倍数
    short_bearish_candle_interval: str = '5m'  # K线周期
    short_bearish_fallback_threshold: int = 7  # 阳线做空Fallback阈值

    # 暴涨做空策略参数（与暴跌反弹对称）
    short_crash_enabled: bool = True  # 启用暴涨做空
    short_crash_min_rise_24h: float = 10.0  # 24h涨幅阈值 >= 10%
    short_crash_max_trend_score: int = 4  # 趋势评分上限
    short_crash_min_pullback_percent: float = 2.0  # 最小回调幅度 2%
    short_crash_rsi_check_enabled: bool = False  # 不检查RSI
    short_crash_rsi_threshold: float = 70.0  # RSI超买阈值
    short_crash_volume_check_enabled: bool = False  # 不检查成交量
    short_crash_volume_ratio: float = 1.2  # 成交量放大阈值

    # 时区感知配置
    timezone_aware_enabled: bool = True  # 启用时区感知
    timezone_adjusted_position: bool = True  # 时区调整仓位大小

    # 时间止损配置（短线策略）
    time_stop_hours: float = 48.0  # 时间止损：持仓超过此小时数自动平仓

    # 动态波段配置
    dynamic_bands_enabled: bool = False  # 启用动态止盈止损
    dynamic_volatility_min: float = 0.5  # 最小波动率阈值
    dynamic_volatility_max: float = 5.0  # 最大波动率阈值
    dynamic_volatility_factor: float = 1.0  # 波动率影响系数

    # 多空互斥决策配置
    mutual_exclusive_enabled: bool = True  # 启用多空互斥决策
    mutual_exclusive_min_score: float = 60.0  # 最低开仓评分阈值
    mutual_exclusive_score_diff: float = 15.0  # 多空分差阈值

    # 趋势变盘减仓配置
    trend_reversal_enabled: bool = True  # 启用趋势变盘减仓
    trend_reversal_from_score: int = 8  # 原始高分阈值（≥8分）
    trend_reversal_to_score: int = 5  # 降至低分阈值（≤5分）
    trend_reversal_min_periods: int = 3  # 持续周期数
    trend_reversal_reduce_percent: float = 0.5  # 减仓比例50%

    # 止盈限价单配置
    take_profit_limit_order_enabled: bool = True  # 启用止盈限价单
    take_profit_limit_order_auto_cancel: bool = True  # 卖出时自动撤销止盈单

    # 时间衰减止损配置（来自crypto-trading-bot-master）
    time_decay_enabled: bool = True  # 启用时间衰减止损
    time_decay_factor: float = 0.1  # 每小时收紧止损线（百分比）
    max_stop_loss: float = -5.0  # 最大止损（收紧到）
    min_stop_loss: float = -1.0  # 最小止损（不会低于此值）
    max_take_profit: float = 15.0  # 最大止盈
    min_take_profit: float = 2.0  # 最小止盈
    time_decay_max_stop: float = -8.0  # 时间衰减最大止损限制

    # 舆情触发交易配置（来自crypto-trading-bot-master）
    sentiment_trigger_enabled: bool = True  # 启用舆情触发交易
    sentiment_buy_threshold: int = 7  # 舆情买入阈值（与sentiment_threshold一致）
    sentiment_sell_threshold: int = 3  # 舆情卖出阈值
    sentiment_min_volume_surge: float = 2.0  # 舆情触发最小放量倍数
    sentiment_trend_weight: float = 0.6  # 趋势评分权重
    sentiment_news_weight: float = 0.4  # 新闻舆情权重

    # 买入金额递减配置
    decreasing_buy_enabled: bool = True  # 启用买入金额递减
    decreasing_buy_factors: List[float] = None  # 递减系数：[1.0, 0.6, 0.35, 0.2]
    max_decrease_levels: int = 4  # 递减层级

    # 风控配置
    max_daily_loss: float = 50.0  # 每日最大亏损限制（$50）

    # 检查频率配置
    check_interval_high_intensity: int = 2  # 高强度检查频率（分钟）
    check_interval_low_intensity: int = 5  # 低强度检查频率（分钟）
    check_intensity_threshold: int = 4  # 强度阈值

    # 共振分析配置 - 对齐 ai_trading_bot.js
    min_capital_flow_score: int = 4  # 资金流向最低评分（对齐 ai_trading_bot.js: capitalFlow.score >= 4）
    resonance_min_total_score: int = 6  # 共振总分门槛
    resonance_sentiment_weight: float = 0.30  # 舆情评分权重 30%
    resonance_technical_weight: float = 0.25  # 技术面权重 25%
    resonance_capital_flow_weight: float = 0.25  # 资金流向权重 25%
    resonance_market_env_weight: float = 0.20  # 大盘环境权重 20%
    
    # 技术面验证参数配置 - 共振策略专用
    technical_validation_enabled: bool = True  # 启用技术面验证
    technical_min_pass_count: int = 2  # 技术面验证最少通过项数（2/5）
    technical_trend_score_threshold: int = 5  # 趋势评分阈值
    technical_rsi_min: float = 30.0  # RSI 下限
    technical_rsi_max: float = 80.0  # RSI 上限
    technical_volume_ratio_min: float = 0.8  # 量比最小值
    technical_ma5_tolerance: float = 0.98  # MA5 容差
    technical_volatility_min: float = 0.2  # 波动率最小值

    # 日交易量限制
    daily_volume_limit_enabled: bool = True  # 启用日交易量限制
    max_daily_volume: float = 1000.0  # 每日最大交易量$1000

    # 连续加仓限制 - 根据趋势动态调整
    consecutive_add_position_enabled: bool = True  # 启用连续加仓限制
    max_position_percent_trend_10: float = 40.0  # 趋势10分最大仓位40%
    max_position_percent_trend_8_9: float = 30.0  # 趋势8-9分最大仓位30%
    max_position_percent_trend_6_7: float = 20.0  # 趋势6-7分最大仓位20%
    max_position_percent_trend_default: float = 10.0  # 默认最大仓位10%
    position_percent_score_tier1: int = 10  # 持仓第一档评分阈值
    position_percent_score_tier2: int = 8  # 持仓第二档评分阈值
    position_percent_score_tier3: int = 6  # 持仓第三档评分阈值

    # 舆情综合验证 - 评分≥8但24h跌>5%则降分
    sentiment_consistency_check_enabled: bool = True  # 启用舆情一致性检查
    sentiment_high_score_threshold: int = 8  # 高分阈值
    price_drop_threshold: float = -5.0  # 价格下跌阈值
    sentiment_adjustment: int = -2  # 评分调整幅度

    # 超仓减仓 - 仓位>30%强制减仓
    over_position_reduce_enabled: bool = True  # 启用超仓减仓
    over_position_reduce_threshold: float = 30.0  # 超仓阈值（30%）
    over_position_reduce_target: float = 20.0  # 减仓目标（20%）

    # 智能豁免期 - 超仓但豁免期内持有
    over_position_exemption_enabled: bool = True  # 启用智能豁免期
    exemption_loss_high_minutes: int = 60  # 亏损>1%，豁免60分钟
    exemption_loss_medium_minutes: int = 45  # 亏损0-1%，豁免45分钟
    exemption_profit_minutes: int = 30  # 已盈利，豁免30分钟
    exemption_loss_high_threshold: float = -1.0  # 高亏损阈值
    exemption_loss_medium_threshold: float = 0.0  # 中等亏损阈值

    # 趋势变盘减仓 - 检测趋势反转快速清仓
    trend_reversal_reduce_enabled: bool = True  # 启用趋势变盘减仓
    trend_reversal_from_score: int = 8  # 原始高分阈值（≥8分）
    trend_reversal_to_score: int = 5  # 降至低分阈值（≤5分）
    trend_reversal_min_periods: int = 3  # 持续周期数
    trend_reversal_reduce_percent: float = 50.0  # 减仓比例（50%）

    # 止损后重置金字塔层级
    reset_pyramid_on_stop_loss: bool = True  # 止损后重置金字塔层级

    # ========== 多空分别的止盈止损配置 ==========
    # 做多智能止损（趋势档位）
    long_smart_stop_loss_enabled: bool = True  # 启用做多智能止损
    long_stop_loss_trend_8_plus: float = -3.0  # 趋势≥8分止损
    long_stop_loss_trend_6_7: float = -2.0  # 趋势6-7分止损
    long_stop_loss_trend_default: float = -1.5  # 默认止损

    # 做多动态止盈（趋势档位）
    long_dynamic_take_profit_enabled: bool = True  # 启用做多动态止盈
    long_take_profit_trend_9_10: float = 15.0  # 趋势9-10分止盈
    long_take_profit_trend_7_8: float = 10.0  # 趋势7-8分止盈
    long_take_profit_trend_5_6: float = 8.0  # 趋势5-6分止盈
    long_take_profit_trend_default: float = 6.0  # 默认止盈

    # 做多分层减仓止盈（波段操作）
    long_band_trade_enabled: bool = True  # 启用做多分层减仓
    long_band_trade_reduce_at: float = 1.5  # 第一档减仓点
    long_band_trade_reduce_percent: float = 30.0  # 第一档减仓比例
    long_band_trade_second_reduce_at: float = 3.0  # 第二档减仓点
    long_band_trade_second_reduce_percent: float = 50.0  # 第二档减仓比例
    long_band_trade_final_reduce_at: float = 6.0  # 最终止盈点

    # 做多小盈减仓
    long_small_profit_reduce_enabled: bool = True  # 启用做多小盈减仓
    long_small_profit_reduce_threshold_percent: float = 50.0  # 止盈线百分比
    long_small_profit_reduce_position_threshold: float = 15.0  # 仓位阈值
    long_small_profit_reduce_ratio: float = 50.0  # 减仓比例

    # 做多止盈限价单
    long_take_profit_limit_order_enabled: bool = True  # 启用做多止盈限价单
    long_take_profit_order_partial: float = 0.5  # 止盈仓位比例

    # 做空智能止损（趋势档位）
    short_smart_stop_loss_enabled: bool = True  # 启用做空智能止损
    short_stop_loss_trend_0_2: float = -3.0  # 趋势0-2分止损（强下跌趋势放宽止损）
    short_stop_loss_trend_3_4: float = -2.0  # 趋势3-4分止损
    short_stop_loss_trend_default: float = -1.5  # 默认止损

    # 做空动态止盈（趋势档位）
    short_dynamic_take_profit_enabled: bool = True  # 启用做空动态止盈
    short_take_profit_trend_0_1: float = 15.0  # 趋势0-1分止盈（强下跌）
    short_take_profit_trend_2_3: float = 10.0  # 趋势2-3分止盈
    short_take_profit_trend_4: float = 8.0  # 趋势4分止盈
    short_take_profit_trend_default: float = 6.0  # 默认止盈

    # 做空分层减仓止盈（波段操作）
    short_band_trade_enabled: bool = True  # 启用做空分层减仓
    short_band_trade_reduce_at: float = 1.5  # 第一档减仓点
    short_band_trade_reduce_percent: float = 30.0  # 第一档减仓比例
    short_band_trade_second_reduce_at: float = 3.0  # 第二档减仓点
    short_band_trade_second_reduce_percent: float = 50.0  # 第二档减仓比例
    short_band_trade_final_reduce_at: float = 6.0  # 最终止盈点

    # 做空小盈减仓
    short_small_profit_reduce_enabled: bool = True  # 启用做空小盈减仓
    short_small_profit_reduce_threshold_percent: float = 50.0  # 止盈线百分比
    short_small_profit_reduce_position_threshold: float = 15.0  # 仓位阈值
    short_small_profit_reduce_ratio: float = 50.0  # 减仓比例

    # 做空止盈限价单
    short_take_profit_limit_order_enabled: bool = True  # 启用做空止盈限价单
    short_take_profit_order_partial: float = 0.5  # 止盈仓位比例

    # ========== AI策略迭代配置 ==========
    ai_evolution_enabled: bool = False  # 启用AI策略迭代
    ai_evolution_auto_apply: bool = False  # 自动应用AI建议
    ai_evolution_min_trades: int = 10  # 最少交易数才触发AI分析
    ai_evolution_interval_hours: int = 24  # AI分析间隔（小时）
    ai_evolution_confidence_threshold: float = 0.7  # AI建议置信度阈值

    # 做空开关
    enable_short: bool = True  # 是否启用做空

    # 合约配置
    use_swap: bool = False  # 是否使用合约交易（False=现货，True=合约）
    long_leverage: int = 3  # 做多杠杆倍数
    short_leverage: int = 3  # 做空杠杆倍数

    # ========== 智能交易配置（来自前端 smart_trading_config）==========
    # 金字塔加仓配置
    smart_pyramid_enabled: bool = True  # 启用金字塔加仓
    smart_pyramid_max_layers: int = 3  # 最大层数
    smart_pyramid_drop_threshold: float = -5.0  # 亏损触发阈值
    smart_pyramid_drop_per_layer: float = -10.0  # 每层下跌幅度
    smart_pyramid_base_amount: float = 25.0  # 基础金额
    smart_pyramid_layer_ratios: str = "1.0,0.6,0.35"  # 各层比例
    smart_pyramid_max_position_percent: float = 15.0  # 最大仓位占比
    smart_pyramid_min_trend_score: int = 6  # 金字塔补仓最低趋势评分
    smart_pyramid_min_cash: float = 15.0  # 金字塔补仓最低资金

    # 飞书通知配置
    feishu_notification_enabled: bool = False  # 启用飞书通知
    feishu_chat_id: str = ""  # 飞书群组ID（可选，App ID/Secret 从环境变量读取）

    # 情绪融合配置 - 对齐 ai_trading_bot.js
    sentiment_fusion_enabled: bool = False  # 启用情绪融合（推荐使用免费方案）
    sentiment_fusion_mode: str = "free"  # 模式: "free"(CoinGecko+Fear&Greed) 或 "news"(CoinGecko+新闻)
    sentiment_coingecko_weight: float = 0.3  # CoinGecko情绪权重（30%）
    sentiment_fear_greed_weight: float = 0.3  # Fear & Greed权重（30%，免费）
    sentiment_news_weight: float = 0.2  # 新闻情绪权重（20%，可选）
    sentiment_technical_weight: float = 0.4  # 技术面权重（40%）
    sentiment_cache_duration: int = 300  # 情绪数据缓存时间（秒，5分钟）
    sentiment_bearish_alert_threshold: int = 3  # 极度看跌阈值（<=3分警告）
    sentiment_fetch_timeout: float = 5.0  # 获取情绪数据超时（秒）
    sentiment_fallback_on_error: bool = True  # 获取失败时使用纯技术面评分

    def __post_init__(self):
        if not hasattr(self, 'decreasing_buy_factors') or self.decreasing_buy_factors is None:
            object.__setattr__(self, 'decreasing_buy_factors', [1.0, 0.6, 0.35, 0.2])


@dataclass
class ScanFilterConfig:
    """市场扫描过滤配置"""
    max_coins: int = 20
    min_turnover_24h: float = 1000000
    min_price: float = 0.01
    only_usdt_pairs: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_coins": self.max_coins,
            "min_turnover_24h": self.min_turnover_24h,
            "min_price": self.min_price,
            "only_usdt_pairs": self.only_usdt_pairs
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScanFilterConfig":
        return cls(
            max_coins=data.get("max_coins", 20),
            min_turnover_24h=data.get("min_turnover_24h", 1000000),
            min_price=data.get("min_price", 0.01),
            only_usdt_pairs=data.get("only_usdt_pairs", True)
        )


class TradingEngine:
    def __init__(self, config: TradingConfig = None):
        self.config = config or TradingConfig()
        self.scan_filter_config = ScanFilterConfig()  # 扫描过滤配置
        self.pyramid_manager = PyramidManager(PyramidConfig())
        self.last_trade_time: Dict[str, datetime] = {}  # 按币种记录最后交易时间（分层冷却期）
        self.daily_trade_count: Dict[str, int] = {}
        self.daily_pnl: Dict[str, float] = {}  # 每日盈亏记录
        self.pending_orders: List[Dict] = []
        self.position_entry_times: Dict[str, datetime] = {}  # 持仓入场时间记录
        self.short_position_entry_times: Dict[str, datetime] = {}  # 做空持仓入场时间记录

        # 趋势历史记录（用于趋势变盘检测）
        self.trend_history: Dict[str, List[int]] = {}

        # 止盈限价单记录
        self.take_profit_orders: Dict[str, Dict] = {}  # {coin: {orderId, amount, costPrice, takeProfitPercent}}

        # 减仓价格记录（用于回调加仓条件检查）
        self.reduce_position_prices: Dict[str, Dict] = {}  # {coin: {price, time, reason}}

        self.running = False
        self._data_dir = "./data"
        self._log_callback: Optional[Callable] = None
        self._market_env_cache = None  # 市场环境缓存
        self._market_env_cache_time = None  # 缓存时间
        os.makedirs(self._data_dir, exist_ok=True)
        self._load_persistent_state()

        # 加载保存的策略配置
        self._load_saved_configs()

        # 初始化飞书通知（从环境变量读取凭证）
        feishu_app_id = os.getenv("FEISHU_APP_ID", "")
        feishu_app_secret = os.getenv("FEISHU_APP_SECRET", "")
        feishu_chat_id = os.getenv("FEISHU_CHAT_ID", "")
        feishu_webhook_url = os.getenv("FEISHU_WEBHOOK_URL", "")
        feishu_enabled = os.getenv("FEISHU_NOTIFICATION_ENABLED", "true").lower() == "true"
        
        # 优先使用 Webhook 方式，如果没有则使用 App ID/Secret 方式
        if feishu_webhook_url:
            feishu_notifier.configure(
                enabled=feishu_enabled,
                webhook_url=feishu_webhook_url
            )
            logger.info(f"飞书通知已配置（Webhook方式）: enabled={feishu_enabled}")
        elif feishu_app_id and feishu_app_secret:
            feishu_notifier.configure(
                app_id=feishu_app_id,
                app_secret=feishu_app_secret,
                enabled=feishu_enabled,
                chat_id=feishu_chat_id
            )
            logger.info(f"飞书通知已配置（OAuth方式）: enabled={feishu_enabled}, chat_id={feishu_chat_id}")
        else:
            logger.warning("飞书通知未配置：请设置 FEISHU_WEBHOOK_URL 或 FEISHU_APP_ID/FEISHU_APP_SECRET")

    def _get_state_file(self):
        """获取状态文件路径"""
        from pathlib import Path
        data_dir = Path(__file__).parent.parent.parent / "data"
        data_dir.mkdir(exist_ok=True)
        return data_dir / "trading_state.json"

    def _get_timezone_position_size(self) -> tuple:
        """
        根据当前时区返回仓位比例范围
        返回: (ratio_min, ratio_max, hold_time_min, hold_time_max)
        参考示例项目 config-sparrow.js: 基础仓位 $15
        """
        if not self.config.timezone_aware_enabled:
            return (1.0, 1.0, 15, 60)

        hour = datetime.now(BEIJING_TZ).hour

        # 6个时段配置（币市麻雀战法）- 比例基于示例项目 $15 基础
        if hour >= 0 and hour < 4:
            # 亚洲尾盘 - 低活跃
            return (0.33, 0.53, 30, 60)  # 5-8/15
        elif hour >= 4 and hour < 8:
            # 欧美交接 - 中低活跃
            return (0.53, 0.67, 20, 40)  # 8-10/15
        elif hour >= 8 and hour < 12:
            # 亚洲早盘 - 高活跃
            return (0.80, 1.00, 15, 60)  # 12-15/15
        elif hour >= 12 and hour < 16:
            # 亚洲午盘 - 中等活跃
            return (0.67, 0.80, 20, 50)  # 10-12/15
        elif hour >= 16 and hour < 20:
            # 欧洲早盘 - 高活跃
            return (0.80, 1.00, 15, 60)  # 12-15/15
        else:
            # 美国早盘 - 高活跃
            return (0.80, 1.00, 10, 45)  # 12-15/15

    def _load_saved_configs(self):
        """加载保存的策略配置"""
        try:
            from pathlib import Path
            
            # 加载智能交易配置（从smart_trading_config.json）
            smart_config_file = Path("smart_trading_config.json")
            if smart_config_file.exists():
                with open(smart_config_file, "r", encoding="utf-8") as f:
                    smart_config = json.load(f)
                    # 金字塔加仓配置
                    self.config.smart_pyramid_enabled = smart_config.get("pyramid_enabled", self.config.smart_pyramid_enabled)
                    self.config.smart_pyramid_max_layers = smart_config.get("pyramid_max_layers", self.config.smart_pyramid_max_layers)
                    self.config.smart_pyramid_drop_threshold = smart_config.get("pyramid_drop_threshold", self.config.smart_pyramid_drop_threshold)
                    self.config.smart_pyramid_drop_per_layer = smart_config.get("pyramid_drop_per_layer", self.config.smart_pyramid_drop_per_layer)
                    self.config.smart_pyramid_base_amount = smart_config.get("pyramid_base_amount", self.config.smart_pyramid_base_amount)
                    self.config.smart_pyramid_layer_ratios = smart_config.get("pyramid_layer_ratios", self.config.smart_pyramid_layer_ratios)
                    self.config.smart_pyramid_max_position_percent = smart_config.get("pyramid_max_position_percent", self.config.smart_pyramid_max_position_percent)
                    self.config.smart_pyramid_min_trend_score = smart_config.get("smart_pyramid_min_trend_score", self.config.smart_pyramid_min_trend_score)
                    self.config.smart_pyramid_min_cash = smart_config.get("smart_pyramid_min_cash", self.config.smart_pyramid_min_cash)
                    # 止损拦截加仓配置
                    self.config.pyramid_on_stop_loss_enabled = smart_config.get("pyramid_on_stop_loss_enabled", self.config.pyramid_on_stop_loss_enabled)
                    self.config.pyramid_on_stop_loss_trend_score = smart_config.get("pyramid_on_stop_loss_trend_score", self.config.pyramid_on_stop_loss_trend_score)
                    self.config.pyramid_on_stop_loss_max_position_percent = smart_config.get("pyramid_on_stop_loss_max_position_percent", self.config.pyramid_on_stop_loss_max_position_percent)
                    self.config.pyramid_on_stop_loss_min_cash = smart_config.get("pyramid_on_stop_loss_min_cash", self.config.pyramid_on_stop_loss_min_cash)
                    # 超仓减仓配置
                    self.config.over_position_reduce_enabled = smart_config.get("over_position_reduce_enabled", self.config.over_position_reduce_enabled)
                    self.config.over_position_reduce_threshold = smart_config.get("over_position_reduce_threshold", self.config.over_position_reduce_threshold)
                    self.config.over_position_reduce_target = smart_config.get("over_position_reduce_target", self.config.over_position_reduce_target)
                    # 智能豁免期配置
                    self.config.over_position_exemption_enabled = smart_config.get("over_position_exemption_enabled", self.config.over_position_exemption_enabled)
                    self.config.exemption_loss_high_minutes = smart_config.get("exemption_loss_high_minutes", self.config.exemption_loss_high_minutes)
                    self.config.exemption_loss_medium_minutes = smart_config.get("exemption_loss_medium_minutes", self.config.exemption_loss_medium_minutes)
                    self.config.exemption_profit_minutes = smart_config.get("exemption_profit_minutes", self.config.exemption_profit_minutes)
                    # 做多智能止损配置（新字段）
                    self.config.long_smart_stop_loss_enabled = smart_config.get("long_smart_stop_loss_enabled", smart_config.get("smart_stop_loss_enabled", self.config.long_smart_stop_loss_enabled))
                    self.config.long_stop_loss_trend_8_plus = smart_config.get("long_stop_loss_trend_8_plus", smart_config.get("stop_loss_trend_8_plus", self.config.long_stop_loss_trend_8_plus))
                    self.config.long_stop_loss_trend_6_7 = smart_config.get("long_stop_loss_trend_6_7", smart_config.get("stop_loss_trend_6_7", self.config.long_stop_loss_trend_6_7))
                    self.config.long_stop_loss_trend_default = smart_config.get("long_stop_loss_trend_default", smart_config.get("stop_loss_trend_default", self.config.long_stop_loss_trend_default))
                    # 做多动态止盈配置（新字段）
                    self.config.long_dynamic_take_profit_enabled = smart_config.get("long_dynamic_take_profit_enabled", smart_config.get("dynamic_take_profit_enabled", self.config.long_dynamic_take_profit_enabled))
                    self.config.long_take_profit_trend_9_10 = smart_config.get("long_take_profit_trend_9_10", smart_config.get("take_profit_trend_9_10", self.config.long_take_profit_trend_9_10))
                    self.config.long_take_profit_trend_7_8 = smart_config.get("long_take_profit_trend_7_8", smart_config.get("take_profit_trend_7_8", self.config.long_take_profit_trend_7_8))
                    self.config.long_take_profit_trend_5_6 = smart_config.get("long_take_profit_trend_5_6", smart_config.get("take_profit_trend_5_6", self.config.long_take_profit_trend_5_6))
                    self.config.long_take_profit_trend_default = smart_config.get("long_take_profit_trend_default", smart_config.get("take_profit_trend_default", self.config.long_take_profit_trend_default))
                    # 时间衰减止损
                    self.config.time_decay_enabled = smart_config.get("time_decay_enabled", self.config.time_decay_enabled)
                    self.config.time_decay_factor = smart_config.get("time_decay_factor", self.config.time_decay_factor)
                    # 做多小盈减仓（新字段）
                    self.config.long_small_profit_reduce_enabled = smart_config.get("long_small_profit_reduce_enabled", smart_config.get("small_profit_reduce_enabled", self.config.long_small_profit_reduce_enabled))
                    self.config.long_small_profit_reduce_threshold_percent = smart_config.get("long_small_profit_reduce_threshold_percent", smart_config.get("small_profit_reduce_threshold_percent", self.config.long_small_profit_reduce_threshold_percent))
                    self.config.long_small_profit_reduce_position_threshold = smart_config.get("long_small_profit_reduce_position_threshold", smart_config.get("small_profit_reduce_position_threshold", self.config.long_small_profit_reduce_position_threshold))
                    # 做多分层减仓止盈（新字段）
                    self.config.long_band_trade_enabled = smart_config.get("long_band_trade_enabled", smart_config.get("band_trade_enabled", self.config.long_band_trade_enabled))
                    self.config.long_band_trade_reduce_at = smart_config.get("long_band_trade_reduce_at", smart_config.get("band_trade_reduce_at", self.config.long_band_trade_reduce_at))
                    self.config.long_band_trade_second_reduce_at = smart_config.get("long_band_trade_second_reduce_at", smart_config.get("band_trade_second_reduce_at", self.config.long_band_trade_second_reduce_at))
                    self.config.long_band_trade_final_reduce_at = smart_config.get("long_band_trade_final_reduce_at", smart_config.get("band_trade_final_reduce_at", self.config.long_band_trade_final_reduce_at))
                    self.config.long_band_trade_reduce_percent = smart_config.get("long_band_trade_reduce_percent", smart_config.get("band_trade_reduce_percent", self.config.long_band_trade_reduce_percent))
                    self.config.long_band_trade_second_reduce_percent = smart_config.get("long_band_trade_second_reduce_percent", smart_config.get("band_trade_second_reduce_percent", self.config.long_band_trade_second_reduce_percent))
                    # 技术面验证配置
                    self.config.technical_validation_enabled = smart_config.get("technical_validation_enabled", self.config.technical_validation_enabled)
                    self.config.technical_min_pass_count = smart_config.get("technical_min_pass_count", self.config.technical_min_pass_count)
                    self.config.technical_trend_score_threshold = smart_config.get("technical_trend_score_threshold", self.config.technical_trend_score_threshold)
                    self.config.technical_rsi_min = smart_config.get("technical_rsi_min", self.config.technical_rsi_min)
                    self.config.technical_rsi_max = smart_config.get("technical_rsi_max", self.config.technical_rsi_max)
                    self.config.technical_volume_ratio_min = smart_config.get("technical_volume_ratio_min", self.config.technical_volume_ratio_min)
                    self.config.technical_ma5_tolerance = smart_config.get("technical_ma5_tolerance", self.config.technical_ma5_tolerance)
                    self.config.technical_volatility_min = smart_config.get("technical_volatility_min", self.config.technical_volatility_min)
                    # 情绪融合配置
                    self.config.sentiment_fusion_enabled = smart_config.get("sentiment_fusion_enabled", self.config.sentiment_fusion_enabled)
                    self.config.sentiment_fusion_mode = smart_config.get("sentiment_fusion_mode", self.config.sentiment_fusion_mode)

            # 加载多单配置
            long_config_file = Path("data/long_config.json")
            if long_config_file.exists():
                with open(long_config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.config.long_min_bullish_score = config.get("minBullishScore", self.config.long_min_bullish_score)
                    self.config.long_min_trend_score = config.get("minTrendScore", self.config.long_min_trend_score)
                    self.config.long_max_trend_score = config.get("maxTrendScore", self.config.long_max_trend_score)
                    self.config.long_rsi_min = config.get("rsiMin", self.config.long_rsi_min)
                    self.config.long_rsi_max = config.get("rsiMax", self.config.long_rsi_max)
                    self.config.long_min_volume_ratio = config.get("minVolumeRatio", self.config.long_min_volume_ratio)
                    self.config.long_min_pullback_percent = config.get("minChange24h", self.config.long_min_pullback_percent)
                    self.config.long_max_pullback_percent = config.get("maxChange24h", self.config.long_max_pullback_percent)
                    self.config.long_min_market_trend = config.get("minMarketTrend", self.config.long_min_market_trend)
                    self.config.long_position_size = config.get("tradeSize", self.config.long_position_size)
                    self.config.long_position_ratio = config.get("positionRatio", self.config.long_position_ratio)
                    self.config.long_max_positions = config.get("maxPositions", self.config.long_max_positions)
                    self.config.long_max_position_percent = config.get("maxPositionPercent", self.config.long_max_position_percent)
                    self.config.long_stop_loss_percent = config.get("stopLossPercent", self.config.long_stop_loss_percent)
                    self.config.long_take_profit_1 = config.get("takeProfit1", self.config.long_take_profit_1)
                    self.config.long_take_profit_2 = config.get("takeProfit2", self.config.long_take_profit_2)
                    self.config.long_time_stop = config.get("timeStop", self.config.long_time_stop)
                    self.config.long_min_trade_interval = config.get("minTradeInterval", self.config.long_min_trade_interval)
                    self.config.long_max_daily_trades = config.get("maxDailyTrades", self.config.long_max_daily_trades)
                    self.config.long_min_volatility = config.get("minVolatility", self.config.long_min_volatility)
                    self.config.long_max_volatility = config.get("maxVolatility", self.config.long_max_volatility)
            
            # 加载空单配置 (从settings.json)
            settings_file = Path("settings.json")
            if settings_file.exists():
                with open(settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    # 加载 useSwap 配置
                    if "useSwap" in settings:
                        self.config.use_swap = settings["useSwap"]
                    if "longLeverage" in settings:
                        self.config.long_leverage = settings["longLeverage"]
                    if "shortLeverage" in settings:
                        self.config.short_leverage = settings["shortLeverage"]
                    
                    if "shortConfig" in settings:
                        sc = settings["shortConfig"]
                        self.config.short_min_bearish_score = sc.get("minBearishScore", self.config.short_min_bearish_score)
                        self.config.short_bearish_gap = sc.get("bearishGap", self.config.short_bearish_gap)
                        self.config.short_sentiment_threshold = sc.get("sentimentThreshold", self.config.short_sentiment_threshold)
                        self.config.short_min_trend_score = sc.get("minTrendScore", self.config.short_min_trend_score)
                        self.config.short_max_trend_score = sc.get("maxTrendScore", self.config.short_max_trend_score)
                        self.config.short_rsi_min = sc.get("rsiMin", self.config.short_rsi_min)
                        self.config.short_rsi_max = sc.get("rsiMax", self.config.short_rsi_max)
                        self.config.short_min_volume_ratio = sc.get("minVolumeRatio", self.config.short_min_volume_ratio)
                        self.config.short_min_pullback_percent = sc.get("changeRange", [self.config.short_min_pullback_percent, 5])[0]
                        self.config.short_max_pullback_percent = sc.get("changeRange", [-8, self.config.short_max_pullback_percent])[1]
                        self.config.short_max_market_trend = sc.get("maxMarketTrend", self.config.short_max_market_trend)
                        self.config.short_position_size = sc.get("tradeSize", self.config.short_position_size)
                        self.config.short_term_trade_size = sc.get("shortTermTradeSize", self.config.short_term_trade_size)
                        self.config.short_position_ratio = sc.get("positionRatio", self.config.short_position_ratio)
                        self.config.short_max_positions = sc.get("maxPositions", self.config.short_max_positions)
                        self.config.short_max_position_percent = sc.get("maxPositionPercent", self.config.short_max_position_percent)
                        self.config.short_stop_loss_percent = sc.get("stopLossPercent", self.config.short_stop_loss_percent)
                        self.config.short_take_profit_1 = sc.get("takeProfit1", self.config.short_take_profit_1)
                        self.config.short_take_profit_2 = sc.get("takeProfit2", self.config.short_take_profit_2)
                        self.config.short_take_profit_percent = sc.get("takeProfitPercent", self.config.short_take_profit_percent)
                        self.config.short_time_stop = sc.get("timeStop", self.config.short_time_stop)
                        self.config.short_min_trade_interval = sc.get("minTradeInterval", self.config.short_min_trade_interval)
                        self.config.short_max_daily_trades = sc.get("maxDailyTrades", self.config.short_max_daily_trades)
                        self.config.short_decreasing_buy_enabled = sc.get("decreasingBuyEnabled", self.config.short_decreasing_buy_enabled)
                        self.config.short_cooldown_trend_1 = sc.get("cooldownTrend1", self.config.short_cooldown_trend_1)
                        self.config.short_cooldown_trend_2_3 = sc.get("cooldownTrend2_3", self.config.short_cooldown_trend_2_3)
                        self.config.short_cooldown_trend_4 = sc.get("cooldownTrend4", self.config.short_cooldown_trend_4)
                        self.config.short_rally_enabled = sc.get("rallyEnabled", self.config.short_rally_enabled)
                        self.config.short_rally_threshold = sc.get("rallyThreshold", self.config.short_rally_threshold)
                        self.config.short_exemption_enabled = sc.get("exemptionEnabled", self.config.short_exemption_enabled)
                        self.config.short_exemption_loss_high = sc.get("exemptionLossHigh", self.config.short_exemption_loss_high)
                        self.config.short_exemption_loss_medium = sc.get("exemptionLossMedium", self.config.short_exemption_loss_medium)
                        self.config.short_exemption_profit = sc.get("exemptionProfit", self.config.short_exemption_profit)
                        self.config.short_min_cash_reserve = sc.get("minCashReserve", self.config.short_min_cash_reserve)
                        
        except Exception as e:
            logger.error(f"加载保存的配置失败: {e}")
        
        # 同步策略迭代参数（仅作为参考，不覆盖用户配置）
        self._log_evolution_params()
    
    def _log_evolution_params(self):
        """记录策略迭代参数（仅作为参考，不覆盖用户配置）"""
        try:
            params = strategy_evolution.get_current_params()
            
            # 只记录迭代参数，不覆盖用户配置
            long_params = params.long
            short_params = params.short
            
            logger.info(f"📊 策略迭代建议参数（仅供参考）:")
            logger.info(f"  做多建议: 止损={long_params.stop_loss}%, 止盈={long_params.take_profit}%, 金额=${long_params.trade_size}")
            logger.info(f"  做空建议: 止损={short_params.stop_loss}%, 止盈={short_params.take_profit}%, 金额=${short_params.trade_size}")
            logger.info(f"  当前用户配置: 止损={self.config.stop_loss_percent}%, 止盈={self.config.take_profit_percent}%, 金额=${self.config.trade_size}")
                
        except Exception as e:
            logger.warning(f"获取策略迭代参数失败: {e}")

    def _calculate_decreasing_buy_amount(self, coin: str, base_amount: float) -> float:
        """
        计算递减买入金额
        同一币种多次买入，金额递减以控制仓位增长
        """
        if not self.config.decreasing_buy_enabled:
            return base_amount

        # 统计今日该币种的买入次数
        today_trades = trade_stats.get_today_trades()
        buy_count = sum(1 for t in today_trades if t.coin == coin and t.action == "buy")

        # 获取递减系数
        factors = self.config.decreasing_buy_factors
        level = min(buy_count, len(factors) - 1)
        factor = factors[level]

        adjusted_amount = base_amount * factor

        if buy_count > 0:
            logger.info(f"  📉 {coin} 今日第{buy_count + 1}次买入，金额递减至{factor*100:.0f}%: ${adjusted_amount:.2f} USDT")

        return adjusted_amount

    def _calculate_exemption_minutes(self, unrealized_pnl_percent: float) -> int:
        """
        计算智能超仓豁免期（单位：分钟）
        根据当前盈亏状态返回豁免时长
        """
        if not self.config.over_position_exemption_enabled:
            return 0

        if unrealized_pnl_percent < -1:
            return self.config.exemption_loss_high  # 亏损>1%，60分钟
        elif unrealized_pnl_percent < 0:
            return self.config.exemption_loss_medium  # 亏损0-1%，45分钟
        else:
            return self.config.exemption_profit  # 已盈利，30分钟

    def _is_in_exemption_period(self, coin: str, unrealized_pnl_percent: float) -> bool:
        """
        检查是否在超仓豁免期内
        """
        if not self.config.over_position_exemption_enabled:
            return False

        last_buy_time = self.last_trade_time.get(coin)
        if not last_buy_time:
            return False

        exemption_minutes = self._calculate_exemption_minutes(unrealized_pnl_percent)
        elapsed = (datetime.now(BEIJING_TZ) - last_buy_time).total_seconds() / 60

        if elapsed < exemption_minutes:
            logger.info(f"  ⏳ {coin} 超仓豁免期内：{elapsed:.1f}/{exemption_minutes}分钟，盈亏{unrealized_pnl_percent:.2f}%")
            return True

        return False

    def _check_trend_reversal(self, coin: str, current_trend_score: int) -> Dict[str, Any]:
        """
        检测趋势变盘 - 当趋势从高分降至低分并横盘时，建议减仓
        返回: {should_reduce: bool, reduce_percent: float, reason: str}
        """
        if not self.config.trend_reversal_enabled:
            return {"should_reduce": False}

        # 初始化趋势历史
        if coin not in self.trend_history:
            self.trend_history[coin] = []

        # 添加当前评分
        self.trend_history[coin].append(current_trend_score)

        # 只保留最近10个评分
        if len(self.trend_history[coin]) > 10:
            self.trend_history[coin].pop(0)

        scores = self.trend_history[coin]

        # 检查是否曾经高分
        had_high_trend = any(s >= self.config.trend_reversal_from_score for s in scores)

        # 检查最近是否持续低分
        recent_scores = scores[-self.config.trend_reversal_min_periods:]
        recent_low_trend = all(s <= self.config.trend_reversal_to_score for s in recent_scores)

        # 检查是否横盘（趋势评分在配置范围内）
        is_sideways = all(self.config.sideways_min_score <= s <= self.config.sideways_max_score for s in recent_scores)

        if had_high_trend and recent_low_trend and is_sideways:
            logger.info(f"  🔄 趋势变盘：{coin} 从高分(≥{self.config.trend_reversal_from_score})降至低分(≤{self.config.trend_reversal_to_score})并横盘{self.config.trend_reversal_min_periods}周期，减仓{self.config.trend_reversal_reduce_percent*100:.0f}%")
            return {
                "should_reduce": True,
                "reduce_percent": self.config.trend_reversal_reduce_percent,
                "reason": f"趋势变盘：从高分降至低分并横盘"
            }

        return {"should_reduce": False}

    async def _place_take_profit_limit_order(self, coin: str, amount: float, cost_price: float, take_profit_percent: float) -> Optional[Dict]:
        """
        下达止盈限价单
        """
        if not self.config.take_profit_limit_order_enabled:
            return None

        try:
            async with OKXClient() as client:
                take_profit_price = cost_price * (1 + take_profit_percent / 100)
                inst_id = f"{coin}-USDT"

                order_data = {
                    "instId": inst_id,
                    "tdMode": "cash",
                    "side": "sell",
                    "ordType": "limit",
                    "sz": str(round(amount, 6)),
                    "px": str(round(take_profit_price, 6))
                }

                result = await client.place_order(order_data)

                if result.get("code") == "0":
                    order_id = result["data"][0]["ordId"]
                    # 记录止盈限价单
                    self.take_profit_orders[coin] = {
                        "order_id": order_id,
                        "amount": amount,
                        "cost_price": cost_price,
                        "take_profit_percent": take_profit_percent,
                        "take_profit_price": take_profit_price,
                        "created_at": datetime.now(BEIJING_TZ).isoformat()
                    }
                    logger.info(f"  ✅ 止盈限价单已下达: {coin} {amount:.6f} @ ${take_profit_price:.6f} (订单ID: {order_id})")
                    self._log(f"  ✅ 止盈限价单已下达: {coin} @ ${take_profit_price:.6f}")
                    return result["data"][0]
                else:
                    logger.error(f"  ❌ 止盈限价单失败: {result.get('msg')}")
                    return None
        except Exception as e:
            logger.error(f"  ❌ 下达止盈限价单异常: {e}")
            return None

    async def _cancel_take_profit_limit_order(self, coin: str) -> bool:
        """
        撤销止盈限价单
        """
        if coin not in self.take_profit_orders:
            return False

        try:
            async with OKXClient() as client:
                order_id = self.take_profit_orders[coin]["order_id"]
                inst_id = f"{coin}-USDT"

                result = await client.cancel_order(inst_id, order_id)

                if result.get("code") == "0":
                    logger.info(f"  ✅ 止盈限价单已撤销: {coin} (订单ID: {order_id})")
                    self._log(f"  ✅ 止盈限价单已撤销: {coin}")
                    del self.take_profit_orders[coin]
                    return True
                else:
                    logger.error(f"  ❌ 撤销止盈限价单失败: {result.get('msg')}")
                    return False
        except Exception as e:
            logger.error(f"  ❌ 撤销止盈限价单异常: {e}")
            return False

    async def _check_take_profit_limit_order_status(self, coin: str) -> Optional[Dict]:
        """
        检查止盈限价单状态
        """
        if coin not in self.take_profit_orders:
            return None

        try:
            async with OKXClient() as client:
                order_id = self.take_profit_orders[coin]["order_id"]
                inst_id = f"{coin}-USDT"

                result = await client.get_order(inst_id, order_id)

                if result.get("code") == "0" and result.get("data"):
                    order = result["data"][0]
                    state = order.get("state")

                    # 如果订单已成交或已撤销，从记录中移除
                    if state == "filled":
                        logger.info(f"  ✅ 止盈限价单已成交: {coin} (订单ID: {order_id})")
                        del self.take_profit_orders[coin]
                        return {"status": "filled", "order": order}
                    elif state == "cancelled":
                        logger.info(f"  ℹ️ 止盈限价单已撤销: {coin} (订单ID: {order_id})")
                        del self.take_profit_orders[coin]
                        return {"status": "cancelled", "order": order}

                    return {"status": state, "order": order}
        except Exception as e:
            logger.error(f"  ❌ 检查止盈限价单状态异常: {e}")

        return None

    def _update_trend_history(self, coin: str, trend_score: int) -> None:
        """
        更新趋势历史（供外部调用）
        """
        if coin not in self.trend_history:
            self.trend_history[coin] = []

        self.trend_history[coin].append(trend_score)

        # 只保留最近10个评分
        if len(self.trend_history[coin]) > 10:
            self.trend_history[coin].pop(0)

    def _calculate_dynamic_bands(self, coin: str, change_24h: float, volatility: float, turnover_24h: float, trend_score: int, entry_time: Optional[datetime] = None) -> Dict[str, float]:
        """
        动态波段计算
        根据波动率、市值、趋势动态调整止损止盈
        止盈使用前端配置的趋势档位值
        """
        # 使用前端配置的止盈值（趋势档位）- 做多配置
        if self.config.long_dynamic_take_profit_enabled:
            if trend_score >= 9:
                dynamic_take_profit = self.config.long_take_profit_trend_9_10
            elif trend_score >= 7:
                dynamic_take_profit = self.config.long_take_profit_trend_7_8
            elif trend_score >= 5:
                dynamic_take_profit = self.config.long_take_profit_trend_5_6
            else:
                dynamic_take_profit = self.config.long_take_profit_trend_default
        else:
            dynamic_take_profit = 6.0

        # 止损使用前端配置的智能止损值 - 做多配置
        if self.config.long_smart_stop_loss_enabled:
            if trend_score >= 8:
                dynamic_stop_loss = -self.config.long_stop_loss_trend_8_plus
            elif trend_score >= 6:
                dynamic_stop_loss = -self.config.long_stop_loss_trend_6_7
            else:
                dynamic_stop_loss = -self.config.long_stop_loss_trend_default
        else:
            dynamic_stop_loss = -3.0

        # 时间衰减止损 - 持仓时间越长，止损越紧
        if entry_time and self.config.time_decay_enabled:
            hours_held = (datetime.now(BEIJING_TZ) - entry_time).total_seconds() / 3600
            time_decay = hours_held * self.config.time_decay_factor
            dynamic_stop_loss = max(dynamic_stop_loss - time_decay, self.config.time_decay_max_stop)
            logger.info(f"     持仓时间: {hours_held:.1f}小时, 时间衰减: {time_decay:.2f}%")

        # 限制范围
        dynamic_stop_loss = max(self.config.max_stop_loss, min(self.config.min_stop_loss, dynamic_stop_loss))
        dynamic_take_profit = max(self.config.min_take_profit, min(self.config.max_take_profit, dynamic_take_profit))

        logger.info(f"  📊 {coin} 动态波段计算:")
        logger.info(f"     趋势评分: {trend_score}, 波动率: {volatility:.2f}%, 24h涨跌: {change_24h:.2f}%")
        logger.info(f"     智能止损: {dynamic_stop_loss:.2f}%, 动态止盈: {dynamic_take_profit:.2f}%")

        return {
            "stop_loss": dynamic_stop_loss,
            "take_profit": dynamic_take_profit,
            "volatility": volatility,
            "trend_score": trend_score
        }

    def _load_persistent_state(self):
        """从文件加载持久化状态"""
        try:
            state_file = self._get_state_file()
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    # 恢复冷却期数据
                    if "last_trade_time" in state:
                        self.last_trade_time = {
                            k: datetime.fromisoformat(v) if isinstance(v, str) else v
                            for k, v in state["last_trade_time"].items()
                        }
                    # 恢复每日交易计数
                    today = self._get_today_key()
                    if "daily_trade_count" in state:
                        self.daily_trade_count = state["daily_trade_count"]
                        # 清理非今天的记录
                        self.daily_trade_count = {
                            k: v for k, v in self.daily_trade_count.items()
                            if k == today
                        }
                    # 恢复每日盈亏记录
                    if "daily_pnl" in state:
                        self.daily_pnl = state["daily_pnl"]
                        # 清理非今天的记录
                        self.daily_pnl = {
                            k: v for k, v in self.daily_pnl.items()
                            if k == today
                        }
                    # 恢复减仓价格记录
                    if "reduce_position_prices" in state:
                        self.reduce_position_prices = state["reduce_position_prices"]
                    # 恢复止盈单记录
                    if "take_profit_orders" in state:
                        self.take_profit_orders = state["take_profit_orders"]
                    # 恢复持仓入场时间记录
                    if "position_entry_times" in state:
                        self.position_entry_times = {
                            k: datetime.fromisoformat(v) if isinstance(v, str) else v
                            for k, v in state["position_entry_times"].items()
                        }
        except Exception as e:
            logger.error(f"加载持久化状态失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _save_persistent_state(self):
        """保存状态到文件"""
        try:
            state_file = self._get_state_file()
            state = {
                "last_trade_time": {
                    k: v.isoformat() if isinstance(v, datetime) else v
                    for k, v in self.last_trade_time.items()
                },
                "daily_trade_count": self.daily_trade_count,
                "daily_pnl": self.daily_pnl,
                "position_entry_times": {
                    k: v.isoformat() if isinstance(v, datetime) else v
                    for k, v in self.position_entry_times.items()
                },
                "reduce_position_prices": self.reduce_position_prices,
                "take_profit_orders": self.take_profit_orders,
                "saved_at": datetime.now(BEIJING_TZ).isoformat()
            }
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存持久化状态失败: {e}")
    
    def set_log_callback(self, callback: Callable):
        """设置日志回调，用于前端显示"""
        self._log_callback = callback
    
    def _log(self, message: str, level: str = "info"):
        """输出日志到控制台并通过回调发送到前端"""
        if self._log_callback:
            try:
                self._log_callback(message, level)
            except Exception as e:
                logger.error(f"日志回调失败: {e}")

    def update_scan_filter_config(self, config: Dict[str, Any]):
        """更新扫描过滤配置"""
        self.scan_filter_config = ScanFilterConfig.from_dict(config)
        logger.info(f"扫描过滤配置已更新: {self.scan_filter_config.to_dict()}")

    def get_scan_filter_config(self) -> Dict[str, Any]:
        """获取当前扫描过滤配置"""
        return self.scan_filter_config.to_dict()
    
    def _get_today_key(self) -> str:
        return datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    
    def _check_cooldown(self, coin: str, trend_score: int = 5) -> tuple[bool, int]:
        """
        检查买入冷却期 - 支持分层冷却期
        返回: (是否可交易, 冷却期分钟数)
        """
        if coin not in self.last_trade_time:
            return True, 0

        elapsed = datetime.now(BEIJING_TZ) - self.last_trade_time[coin]
        elapsed_minutes = elapsed.total_seconds() / 60

        # 分层冷却期计算
        cooldown_minutes = self.config.buy_cooldown_minutes

        if self.config.tiered_cooldown_enabled:
            if trend_score >= self.config.cooldown_score_tier1:
                cooldown_minutes = self.config.cooldown_trend_10
            elif trend_score >= self.config.cooldown_score_tier2:
                cooldown_minutes = self.config.cooldown_trend_8_9
            elif trend_score >= self.config.cooldown_score_tier3:
                cooldown_minutes = self.config.cooldown_trend_6_7

        # 动态冷却期：根据市场波动性调整（在分层冷却期基础上微调）
        if self._market_env_cache:
            btc_vol = abs(self._market_env_cache.btc_change_24h or 0)
            if btc_vol > self.config.cooldown_high_volatility:
                cooldown_minutes = int(cooldown_minutes * self.config.cooldown_high_volatility_multiplier)
            elif btc_vol < self.config.cooldown_low_volatility:
                cooldown_minutes = int(cooldown_minutes * self.config.cooldown_low_volatility_multiplier)

        if elapsed_minutes < cooldown_minutes:
            remaining = int(cooldown_minutes - elapsed_minutes)
            return False, remaining

        return True, cooldown_minutes

    def _check_daily_limit(self) -> bool:
        today = self._get_today_key()
        count = self.daily_trade_count.get(today, 0)
        return count < self.config.max_daily_trades
    
    def _check_daily_volume_limit(self, trade_amount: float = 0) -> bool:
        """检查日交易量限制"""
        if not self.config.daily_volume_limit_enabled:
            return True
        
        trade_stats._load_trade_log()
        stats = trade_stats.calculate_stats()
        today_volume = stats.get("today", {}).get("volume", 0) if stats else 0
        
        projected_volume = today_volume + trade_amount
        
        if projected_volume >= self.config.max_daily_volume:
            logger.warning(f"日交易量限制: 当前${today_volume:.2f} + 本次${trade_amount:.2f} >= 限制${self.config.max_daily_volume:.2f}")
            self._log(f"🛑 日交易量限制: 当前${today_volume:.2f}，本次${trade_amount:.2f}会超出限制${self.config.max_daily_volume:.2f}")
            return False
        
        return True
    
    def _check_consecutive_add_limit(self, coin: str, trend_score: int, position_value: float, total_equity: float) -> tuple[bool, str]:
        """
        检查连续加仓限制 - 根据趋势动态调整
        返回: (是否允许加仓, 原因)
        """
        if not self.config.consecutive_add_position_enabled:
            return True, ""
        
        if total_equity <= 0:
            return True, ""
        
        position_percent = (position_value / total_equity) * 100
        
        # 根据趋势评分确定最大允许仓位
        if trend_score >= self.config.position_percent_score_tier1:
            max_allowed = self.config.max_position_percent_trend_10
        elif trend_score >= self.config.position_percent_score_tier2:
            max_allowed = self.config.max_position_percent_trend_8_9
        elif trend_score >= self.config.position_percent_score_tier3:
            max_allowed = self.config.max_position_percent_trend_6_7
        else:
            max_allowed = self.config.max_position_percent_trend_default
        
        if position_percent > max_allowed:
            return False, f"{coin}已有持仓{position_percent:.1f}%，超过趋势评分{trend_score}分对应的阈值{max_allowed}%"
        
        return True, ""
    
    def _check_pullback_buy_condition(self, coin: str, current_price: float) -> tuple[bool, str]:
        """
        检查回调加仓条件
        如果有减仓记录，需等价格回调到减仓价的97%以下才允许买入
        返回: (是否允许买入, 原因)
        """
        if not self.config.pullback_buy_enabled:
            return True, ""
        
        record = self.reduce_position_prices.get(coin)
        if not record:
            return True, "无减仓记录"
        
        pullback_threshold = record["price"] * self.config.pullback_buy_threshold
        if current_price <= pullback_threshold:
            # 清除记录，允许买入
            del self.reduce_position_prices[coin]
            self._save_persistent_state()
            return True, f"价格回调到位: ${current_price:.2f} ≤ ${pullback_threshold:.2f} (减仓价${record['price']:.2f}的{self.config.pullback_buy_threshold*100:.0f}%)"
        else:
            return False, f"等待回调: ${current_price:.2f} > ${pullback_threshold:.2f} (需≤减仓价{self.config.pullback_buy_threshold*100:.0f}%)"
    
    def _check_pnl_before_buy(self, coin: str, current_price: float, existing_position: Dict = None) -> tuple[bool, int, str]:
        """
        实时盈亏验证 - 防止追高
        如果已有持仓且亏损>1%，禁止买入
        返回: (是否允许买入, 调整后的趋势评分, 原因)
        """
        if not self.config.pnl_check_enabled:
            return True, None, ""
        
        if not existing_position or existing_position.get("amount", 0) <= 0:
            return True, None, ""
        
        avg_price = existing_position.get("avg_price", 0)
        if avg_price <= 0:
            return True, None, ""
        
        pnl_percent = (current_price - avg_price) / avg_price * 100
        
        if pnl_percent < self.config.pnl_check_threshold:
            # 亏损超过阈值，禁止买入
            adjusted_score = 5 if self.config.pnl_check_adjust_score else None
            return False, adjusted_score, f"实时盈亏验证：当前亏损{pnl_percent:.2f}% < {self.config.pnl_check_threshold}%，禁止买入防止追高"
        
        return True, None, ""
    
    def _check_blacklist_trend_reversal(self, coin: str, trend_score: int) -> bool:
        """
        检查黑名单币种是否应该解除（趋势反转）
        连续2次趋势评分≥8分，或单次≥9分，解除黑名单
        返回: 是否应该解除黑名单
        """
        if not self.config.blacklist_trend_check_enabled:
            return False
        
        if not blacklist_manager.is_blacklisted(coin):
            return False
        
        # 初始化趋势追踪
        if not hasattr(self, '_blacklist_trend_tracker'):
            self._blacklist_trend_tracker = {}
        
        if coin not in self._blacklist_trend_tracker:
            self._blacklist_trend_tracker[coin] = {"high_trend_count": 0, "last_check": datetime.now()}
        
        tracker = self._blacklist_trend_tracker[coin]
        
        # 单次高分立即解除
        if trend_score >= self.config.blacklist_high_threshold:
            logger.info(f"✅ {coin} 趋势评分{trend_score}≥{self.config.blacklist_high_threshold}，立即解除黑名单")
            blacklist_manager.remove_from_blacklist(coin, reason=f"趋势评分{trend_score}分，强势反转")
            del self._blacklist_trend_tracker[coin]
            return True
        
        # 连续达到阈值
        if trend_score >= self.config.blacklist_trend_threshold:
            tracker["high_trend_count"] += 1
            logger.info(f"📈 {coin} 趋势评分{trend_score}/{self.config.blacklist_trend_threshold}，连续{tracker['high_trend_count']}次")
            
            if tracker["high_trend_count"] >= self.config.blacklist_trend_count:
                logger.info(f"✅ {coin} 趋势连续{self.config.blacklist_trend_count}次≥{self.config.blacklist_trend_threshold}，解除黑名单")
                blacklist_manager.remove_from_blacklist(coin, reason=f"趋势连续{self.config.blacklist_trend_count}次≥{self.config.blacklist_trend_threshold}分")
                del self._blacklist_trend_tracker[coin]
                return True
        else:
            # 趋势评分低于阈值，重置计数
            if tracker["high_trend_count"] > 0:
                logger.info(f"📉 {coin} 趋势评分{trend_score}，低于阈值，重置计数")
                tracker["high_trend_count"] = 0
        
        tracker["last_check"] = datetime.now()
        return False
    
    def _calculate_decreasing_trade_size(self, coin: str, base_amount: float) -> float:
        """
        买入金额递减计算
        同一币种多次买入，金额递减以控制仓位增长
        第1次100%，第2次60%，第3次35%，第4次及以后20%
        """
        if not self.config.decreasing_trade_size_enabled:
            return base_amount
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 统计今日该币种的买入次数
        today_trades = trade_stats.get_today_trades_for_coin(coin)
        buy_count = len([t for t in today_trades if t.action == "buy"])
        
        # 解析递减比例
        factors = [float(x) for x in self.config.decreasing_factors.split(",")]
        factor = factors[min(buy_count, len(factors) - 1)]
        
        adjusted_amount = base_amount * factor
        
        if buy_count > 0:
            logger.info(f"📉 {coin} 今日第{buy_count + 1}次买入，金额递减至{factor * 100:.0f}%: ${adjusted_amount:.2f} USDT")
        
        return adjusted_amount
    
    def _is_gold_stablecoin(self, coin: str) -> bool:
        """检查是否为黄金稳定币"""
        if not self.config.gold_stablecoin_special_handling:
            return False
        return coin.upper() in [c.strip().upper() for c in self.config.gold_stablecoin_list.split(",")]
    
    def _record_reduce_position_price(self, coin: str, price: float, reason: str = ""):
        """记录减仓价格（用于回调加仓条件检查）"""
        self.reduce_position_prices[coin] = {
            "price": price,
            "time": datetime.now(BEIJING_TZ).isoformat(),
            "reason": reason
        }
        self._save_persistent_state()
        logger.info(f"📝 记录减仓价格: {coin} @ ${price:.2f}, 原因: {reason}")
    
    async def _place_take_profit_order(self, coin: str, amount: float, cost_price: float, take_profit_percent: float) -> Dict:
        """
        挂止盈限价单
        只挂部分仓位（默认50%），保留部分用于动态止盈
        """
        if not self.config.take_profit_order_enabled:
            return {"success": False, "error": "止盈单功能未启用"}
        
        # 黄金稳定币特殊处理
        if self._is_gold_stablecoin(coin):
            take_profit_percent = self.config.gold_stablecoin_take_profit
            logger.info(f"🥇 {coin}是黄金稳定币，止盈目标降至{take_profit_percent}%")
        
        tp_price = cost_price * (1 + take_profit_percent / 100)
        
        # 只挂部分仓位
        tp_amount = amount * self.config.take_profit_order_partial
        
        logger.info(f"🎯 挂止盈单: {coin}")
        logger.info(f"   成本价: ${cost_price:.4f}")
        logger.info(f"   止盈价: ${tp_price:.4f} (+{take_profit_percent}%)")
        logger.info(f"   数量: {tp_amount:.6f} (总仓位的{self.config.take_profit_order_partial*100:.0f}%)")
        
        try:
            # 这里调用OKX API挂限价单
            # 实际实现需要根据OKXClient的接口
            order_id = f"tp_{coin}_{int(datetime.now().timestamp())}"
            
            # 记录止盈单
            self.take_profit_orders[coin] = {
                "order_id": order_id,
                "cost_price": cost_price,
                "tp_price": tp_price,
                "tp_percent": take_profit_percent,
                "amount": tp_amount,
                "created_at": datetime.now(BEIJING_TZ).isoformat(),
                "status": "live"
            }
            self._save_persistent_state()
            
            logger.info(f"✅ 止盈单挂单成功！订单ID: {order_id}")
            return {"success": True, "order_id": order_id}
        except Exception as e:
            logger.error(f"❌ 止盈单挂单失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _cancel_take_profit_order(self, coin: str) -> Dict:
        """撤销止盈单"""
        tp_order = self.take_profit_orders.get(coin)
        if not tp_order or not tp_order.get("order_id"):
            return {"success": False, "error": "无止盈单记录"}
        
        logger.info(f"🔄 撤销止盈单: {coin}, 订单ID: {tp_order['order_id']}")
        
        try:
            # 这里调用OKX API撤销订单
            # 实际实现需要根据OKXClient的接口
            
            # 清除记录
            del self.take_profit_orders[coin]
            self._save_persistent_state()
            
            logger.info(f"✅ 止盈单撤销成功")
            return {"success": True}
        except Exception as e:
            logger.error(f"❌ 止盈单撤销失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _adjust_take_profit_by_trend(self, coin: str, current_price: float, trend_score: int, sentiment_score: int = None):
        """
        根据趋势评分和舆情动态调整止盈单（示例项目逻辑）
        - 黄金稳定币(XAUT/PAXG): 保持0.2%止盈
        - 舆情极差(≤3分): 收紧止盈至更低水平
        - 趋势≥8分: 扩大止盈至15%
        - 趋势5-8分: 标准止盈10%
        - 趋势<5分: 收紧止盈至6%
        """
        tp_order = self.take_profit_orders.get(coin)
        if not tp_order:
            return

        is_gold_stablecoin = coin in ['XAUT', 'PAXG']

        if is_gold_stablecoin:
            new_tp_percent = 0.2
            logger.info(f"  🥇 {coin}是黄金稳定币，保持0.2%止盈目标")
        elif self.config.take_profit_adjust_on_bad_sentiment and sentiment_score is not None and sentiment_score <= self.config.take_profit_bad_sentiment_threshold:
            new_tp_percent = self.config.long_take_profit_trend_default
            logger.info(f"  🎯 {coin} 舆情极差({sentiment_score}分≤{self.config.take_profit_bad_sentiment_threshold}分)，收紧止盈至{new_tp_percent}%")
        elif trend_score >= self.config.take_profit_score_tier1:
            new_tp_percent = self.config.long_take_profit_trend_9_10
        elif trend_score >= self.config.take_profit_score_tier2:
            new_tp_percent = self.config.long_take_profit_trend_7_8
        elif trend_score >= self.config.take_profit_score_tier3:
            new_tp_percent = self.config.long_take_profit_trend_5_6
        else:
            new_tp_percent = self.config.long_take_profit_trend_default

        old_tp_percent = tp_order.get("tp_percent", 0)
        if abs(new_tp_percent - old_tp_percent) < 0.5:
            return

        logger.info(f"  🔄 {coin} 止盈单调整: {old_tp_percent:.1f}% -> {new_tp_percent:.1f}% (趋势{trend_score}分)" + (f", 舆情{sentiment_score}分" if sentiment_score is not None else ""))
        result = await self._adjust_take_profit_order(coin, new_tp_percent)
        if result.get("success"):
            logger.info(f"  ✅ {coin} 止盈单已调整至 {new_tp_percent}%")
        else:
            logger.warning(f"  ⚠️ {coin} 止盈单调整失败: {result.get('error')}")

    async def _adjust_take_profit_order(self, coin: str, new_tp_percent: float) -> Dict:
        """
        调整止盈单价格（收紧止盈）
        用于舆情极差时收紧止盈
        """
        tp_order = self.take_profit_orders.get(coin)
        if not tp_order:
            return {"success": False, "error": "无止盈单记录"}
        
        # 先撤销旧订单
        cancel_result = await self._cancel_take_profit_order(coin)
        if not cancel_result["success"]:
            return cancel_result
        
        # 挂新订单
        return await self._place_take_profit_order(
            coin,
            tp_order["amount"] / self.config.take_profit_order_partial,  # 恢复原始数量
            tp_order["cost_price"],
            new_tp_percent
        )

    def _check_daily_loss_limit(self) -> bool:
        """检查今日亏损是否超过限制"""
        today = self._get_today_key()
        today_pnl = self.daily_pnl.get(today, 0.0)

        if today_pnl < -self.config.max_daily_loss:
            logger.warning(f"今日亏损已达到限制: {today_pnl:.2f} USDT > {self.config.max_daily_loss} USDT")
            self._log(f"🛑 今日亏损已达到限制: {abs(today_pnl):.2f} USDT，停止交易")
            return False
        
        return True

    def _update_daily_pnl(self, pnl: float):
        """更新每日盈亏"""
        today = self._get_today_key()
        self.daily_pnl[today] = self.daily_pnl.get(today, 0.0) + pnl
        self._save_persistent_state()
    
    def _record_trade_time(self, coin: str):
        self.last_trade_time[coin] = datetime.now(BEIJING_TZ)
        today = self._get_today_key()
        self.daily_trade_count[today] = self.daily_trade_count.get(today, 0) + 1
        # 保存到文件
        self._save_persistent_state()

    def _record_reduce_position_price(self, coin: str, price: float, reason: str = ""):
        """记录减仓价格，用于回调加仓条件检查"""
        self.reduce_position_prices[coin] = {
            "price": price,
            "time": datetime.now(BEIJING_TZ).isoformat(),
            "reason": reason
        }
        self._save_persistent_state()
        logger.info(f"  📝 记录减仓价格: {coin} @ ${price:.4f}, 原因: {reason}")

    def _check_pullback_buy_condition(self, coin: str, current_price: float) -> Dict[str, Any]:
        """
        检查回调加仓条件
        减仓后需等价格回调到减仓价的97%以下才能再次买入
        """
        record = self.reduce_position_prices.get(coin)
        if not record:
            return {"can_buy": True, "reason": "无减仓记录"}

        pullback_threshold = record["price"] * self.config.pullback_buy_threshold
        if current_price <= pullback_threshold:
            logger.info(f"  ✅ {coin} 价格回调到位: ${current_price:.4f} ≤ ${pullback_threshold:.4f} (减仓价${record['price']:.4f}的{self.config.pullback_buy_threshold*100:.0f}%)")
            del self.reduce_position_prices[coin]
            self._save_persistent_state()
            return {"can_buy": True, "reason": "回调到位"}
        else:
            logger.info(f"  ⏳ {coin} 等待回调: ${current_price:.4f} > ${pullback_threshold:.4f} (需≤减仓价{self.config.pullback_buy_threshold*100:.0f}%)")
            return {"can_buy": False, "reason": f"等待回调: ${current_price:.4f} > ${pullback_threshold:.4f}"}

    def _check_realtime_pnl_for_buy(self, coin: str, position: Optional[Dict], current_price: float) -> Dict[str, Any]:
        """
        实时盈亏验证
        如果已有持仓且亏损>1%，禁止买入（防止追高）
        """
        if not position:
            return {"can_buy": True, "reason": "无持仓"}

        avg_price = position.get("avg_price", position.get("avgPrice", 0))
        if not avg_price or avg_price <= 0:
            return {"can_buy": True, "reason": "无成本价记录"}

        pnl_percent = (current_price - avg_price) / avg_price * 100

        if pnl_percent < -1.0:
            logger.info(f"  ⚠️ 实时盈亏验证: 当前亏损{pnl_percent:.2f}% > -1%，禁止买入防止追高")
            return {"can_buy": False, "reason": f"实时盈亏验证: 亏损{pnl_percent:.2f}%，禁止买入"}

        return {"can_buy": True, "reason": f"盈亏{pnl_percent:.2f}%正常"}

    def _check_short_rally_condition(self, coin: str, current_price: float) -> Dict[str, Any]:
        """
        检查上涨加空条件（做空对称逻辑）
        减空后需等价格上涨到减空价的103%以上才能再次做空
        """
        record = self.reduce_position_prices.get(coin, {}).get("short")
        if not record:
            return {"can_short": True, "reason": "无减空记录"}

        rally_threshold = record["price"] * self.config.short_rally_threshold
        if current_price >= rally_threshold:
            logger.info(f"  ✅ {coin} 价格反弹到位: ${current_price:.4f} >= ${rally_threshold:.4f} (减空价${record['price']:.4f}的103%)")
            if coin in self.reduce_position_prices:
                del self.reduce_position_prices[coin]["short"]
                if not self.reduce_position_prices[coin]:
                    del self.reduce_position_prices[coin]
            self._save_persistent_state()
            return {"can_short": True, "reason": "上涨到位"}
        else:
            logger.info(f"  ⏳ {coin} 等待上涨: ${current_price:.4f} < ${rally_threshold:.4f} (需>=减空价{self.config.short_rally_threshold*100:.0f}%)")
            return {"can_short": False, "reason": f"等待上涨: ${current_price:.4f} < ${rally_threshold:.4f}"}

    def _check_realtime_pnl_for_short(self, coin: str, short_position: Optional[Dict], current_price: float) -> Dict[str, Any]:
        """
        实时盈亏验证（做空对称逻辑）
        如果已有空单且亏损>1%，禁止加空（防止追跌）
        """
        if not short_position:
            return {"can_short": True, "reason": "无空单持仓"}

        avg_price = short_position.get("avg_price", short_position.get("avgPrice", 0))
        if not avg_price or avg_price <= 0:
            return {"can_short": True, "reason": "无成本价记录"}

        # 做空盈亏：价格上涨=亏损，价格下跌=盈利
        pnl_percent = (avg_price - current_price) / avg_price * 100

        if pnl_percent < -1.0:
            logger.info(f"  ⚠️ 空单实时盈亏验证: 当前亏损{pnl_percent:.2f}% < -1%，禁止加空防止追跌")
            return {"can_short": False, "reason": f"实时盈亏验证: 空单亏损{pnl_percent:.2f}%，禁止加空"}

        return {"can_short": True, "reason": f"空单盈亏{pnl_percent:.2f}%正常"}

    def _check_short_cooldown(self, coin: str, bearish_score: int) -> tuple[bool, int]:
        """
        检查做空分层冷却期（使用独立的看跌评分）
        看跌评分越高，冷却期越短
        """
        if not self.config.short_decreasing_buy_enabled:
            last_time = self.last_trade_time.get(f"short_{coin}")
            if last_time:
                elapsed = (datetime.now(BEIJING_TZ) - last_time).total_seconds() / 60
                cooldown = self.config.buy_cooldown_minutes
                if elapsed < cooldown:
                    return False, cooldown
            return True, 0

        last_time = self.last_trade_time.get(f"short_{coin}")
        if not last_time:
            return True, 0

        elapsed = (datetime.now(BEIJING_TZ) - last_time).total_seconds() / 60

        # 分层冷却期：看跌评分越高，冷却期越短
        if bearish_score >= self.config.short_cooldown_score_tier1:
            cooldown = self.config.short_cooldown_trend_1
        elif bearish_score >= self.config.short_cooldown_score_tier2:
            cooldown = self.config.short_cooldown_trend_2_3
        else:
            cooldown = self.config.short_cooldown_trend_4

        if elapsed < cooldown:
            return False, cooldown

        return True, 0

    def _calculate_short_decreasing_amount(self, coin: str, base_amount: float) -> float:
        """
        计算做空金额递减（做空对称逻辑）
        同一币种多次做空，金额递减以控制风险
        """
        if not self.config.short_decreasing_buy_enabled:
            return base_amount

        today_trades = trade_stats.get_today_trades()
        short_count = sum(1 for t in today_trades if t.coin == coin and t.action == "sell_short")

        factors = self.config.decreasing_buy_factors
        level = min(short_count, len(factors) - 1)
        factor = factors[level]

        adjusted_amount = base_amount * factor

        if short_count > 0:
            logger.info(f"  📉 {coin} 今日第{short_count + 1}次做空，金额递减至{factor*100:.0f}%: ${adjusted_amount:.2f} USDT")

        return adjusted_amount

    def _calculate_short_exemption_minutes(self, unrealized_pnl_percent: float) -> int:
        """
        计算空单超仓豁免期（做空对称逻辑）
        """
        if not self.config.short_over_position_exemption_enabled:
            return 0

        if unrealized_pnl_percent < -1:
            return self.config.short_over_position_exemption_loss_high
        elif unrealized_pnl_percent < 0:
            return self.config.short_over_position_exemption_loss_medium
        else:
            return self.config.short_over_position_exemption_profit

    def _is_in_short_exemption_period(self, coin: str, unrealized_pnl_percent: float) -> bool:
        """
        检查是否在空单超仓豁免期内（做空对称逻辑）
        """
        if not self.config.short_over_position_exemption_enabled:
            return False

        last_short_time = self.last_trade_time.get(f"short_{coin}")
        if not last_short_time:
            return False

        exemption_minutes = self._calculate_short_exemption_minutes(unrealized_pnl_percent)
        elapsed = (datetime.now(BEIJING_TZ) - last_short_time).total_seconds() / 60

        if elapsed < exemption_minutes:
            logger.info(f"  ⏳ {coin} 空单超仓豁免期内：{elapsed:.1f}/{exemption_minutes}分钟，盈亏{unrealized_pnl_percent:.2f}%")
            return True

        return False

    def _check_short_conditions(self, bearish_score: int, trend_score: int, change_24h: float, rsi_value: float, 
                                 volume_ratio: float, sentiment_score: int = 5,
                                 btc_trend: int = 5, eth_trend: int = 5) -> Dict[str, Any]:
        """
        综合做空条件检查（使用独立的看跌评分）
        trend_score: 趋势评分（低分表示下跌趋势）
        btc_trend: BTC趋势评分
        eth_trend: ETH趋势评分
        返回: {passed: bool, reasons: List[str], score: int}
        """
        passed = False
        reasons = []
        score = 0

        # 条件1: 看跌评分达标 (>= 7)
        is_bearish = bearish_score >= self.config.short_min_bearish_score
        if is_bearish:
            reasons.append(f"看跌评分达标({bearish_score}/10)")
            score += 3
        else:
            reasons.append(f"看跌评分不足({bearish_score}/10)")

        # 条件2: 趋势评分在下跌区间（下限 <= 趋势评分 <= 上限）
        is_downtrend = self.config.short_min_trend_score <= trend_score <= self.config.short_max_trend_score
        if is_downtrend:
            reasons.append(f"下跌趋势({trend_score}/10在{self.config.short_min_trend_score}-{self.config.short_max_trend_score}区间)")
            score += 2
        elif trend_score < self.config.short_min_trend_score:
            reasons.append(f"趋势过低({trend_score}/10 < {self.config.short_min_trend_score})，可能反弹")
        else:
            reasons.append(f"非下跌趋势({trend_score}/10 > {self.config.short_max_trend_score})")

        # 条件3: 大盘弱势（BTC/ETH趋势低）
        market_weak = btc_trend <= self.config.short_max_btc_trend and eth_trend <= self.config.short_max_eth_trend
        if market_weak:
            reasons.append(f"大盘弱势(BTC{btc_trend}/ETH{eth_trend})")
            score += 2
        else:
            reasons.append(f"大盘非弱势(BTC{btc_trend}/ETH{eth_trend})")

        # 条件4: 高位 (24h涨幅在合理范围内)
        is_high_price = self.config.short_min_pullback_percent < change_24h < self.config.short_max_pullback_percent
        if is_high_price:
            reasons.append(f"高位({change_24h:.2f}%)")
            score += 2
        elif change_24h >= self.config.short_max_pullback_percent:
            reasons.append(f"涨幅过大({change_24h:.2f}%)，不追空")
        else:
            reasons.append(f"非高位({change_24h:.2f}%)")

        # 条件5: RSI在超买区间（下限 <= RSI <= 上限）
        is_overbought = self.config.short_rsi_min <= rsi_value <= self.config.short_rsi_max
        if is_overbought:
            reasons.append(f"RSI超买({rsi_value:.1f}在{self.config.short_rsi_min}-{self.config.short_rsi_max}区间)")
            score += 2
        elif rsi_value > self.config.short_rsi_max:
            reasons.append(f"RSI极度超买({rsi_value:.1f}>{self.config.short_rsi_max})，可能反转")
        else:
            reasons.append(f"RSI未超买({rsi_value:.1f}<{self.config.short_rsi_min})")

        # 条件6: 成交量放大 (> 1.2x)
        volume_sufficient = volume_ratio > self.config.short_min_volume_ratio
        if volume_sufficient:
            reasons.append(f"放量({volume_ratio:.2f}x)")
            score += 1
        else:
            reasons.append(f"未放量({volume_ratio:.2f}x)")

        # 条件7: 大盘弱势
        if btc_trend <= self.config.short_max_market_trend and eth_trend <= self.config.short_max_market_trend:
            reasons.append(f"大盘弱势(BTC{btc_trend}/ETH{eth_trend})")
            score += 2
        else:
            reasons.append(f"舆情非看跌({sentiment_score}/10)")

        # 综合判断: 看跌评分达标 AND (下跌趋势 OR 大盘弱势)
        if is_bearish and (is_downtrend or market_weak):
            passed = True
        elif is_bearish and is_high_price and is_overbought:
            passed = True

        return {
            "passed": passed,
            "reasons": reasons,
            "score": score,
            "is_bearish": is_bearish,
            "is_downtrend": is_downtrend,
            "market_weak": market_weak,
            "is_high_price": is_high_price,
            "is_overbought": is_overbought,
            "volume_sufficient": volume_sufficient
        }

    async def _after_buy(self, coin: str, amount: float, cost_price: float, trend_score: int) -> None:
        """
        买入后处理：
        1. 更新趋势历史
        2. 下达止盈限价单（如果启用）
        """
        # 更新趋势历史
        self._update_trend_history(coin, trend_score)

        # 下达止盈限价单
        if self.config.take_profit_limit_order_enabled:
            await self._place_take_profit_limit_order(
                coin, amount, cost_price, self.config.take_profit_percent
            )

    
    async def _get_account_info(self, dry_run: bool = True) -> Optional[Dict[str, Any]]:
        """获取账户概况信息"""
        try:
            if dry_run:
                stats = simulation_manager.get_stats()
                positions = simulation_manager.get_positions()
                short_positions = simulation_manager.get_short_positions()
                total_position_value = sum(p.get("usdt_value", 0) for p in positions)
                total_short_value = sum(p.get("usdt_value", 0) for p in short_positions)
                total_equity = stats["available_balance"] + total_position_value + total_short_value + stats["total_pnl"]
                return {
                    "total_equity": total_equity,
                    "available_usdt": stats["available_balance"],
                    "is_simulation": True
                }
            else:
                async with OKXClient() as client:
                    balance = await client.get_balance()
                    if balance and "data" in balance:
                        data = balance["data"][0]
                        total_eq = float(data.get("totalEq", 0))
                        details = data.get("details", [])
                        usdt_detail = next((d for d in details if d.get("ccy") == "USDT"), {})
                        available_usdt = float(usdt_detail.get("availBal", 0) or usdt_detail.get("cashBal", 0) or 0)
                        return {
                            "total_equity": total_eq,
                            "available_usdt": available_usdt,
                            "is_simulation": False
                        }
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
        return None
    
    async def scan_market(self) -> List[Dict[str, Any]]:
        if emergency_stop.is_stopped():
            logger.warning("紧急停止状态，跳过市场扫描")
            return []

        opportunities = []
        config = self.scan_filter_config

        logger.info("")
        logger.info("=" * 60)
        logger.info("🔍 开始市场扫描")
        logger.info("=" * 60)
        self._log("🔍 开始市场扫描")
        
        async with OKXClient() as client:
            tickers = await client.get_tickers("SPOT")
            if tickers.get("code") != "0":
                logger.error("获取行情失败")
                return []

            market_env = await check_market_environment(client)
            market_direction = "做多" if market_env.score >= 4 else "做空"
            logger.info(f"📊 市场环境: BTC={market_env.btc_score}分, ETH={market_env.eth_score}分, 资金费率={market_env.funding_score}分, 综合={market_env.score}分 → 适合{market_direction}")
            self._log(f"📊 市场环境: BTC={market_env.btc_score}分, ETH={market_env.eth_score}分, 资金费率={market_env.funding_score}分, 综合={market_env.score}分 → 适合{market_direction}")
            self._market_env_cache = market_env
            
            candidate_coins = []
            all_tickers = []

            for ticker in tickers.get("data", []):
                inst_id = ticker.get("instId", "")
                if config.only_usdt_pairs and not inst_id.endswith("-USDT"):
                    continue

                coin = inst_id.replace("-USDT", "")

                # 检查黑名单趋势反转
                if blacklist_manager.is_blacklisted(coin):
                    # 获取趋势评分检查是否应该解除黑名单
                    trend_result = await analyze_trend(coin, last_price)
                    if trend_result and self._check_blacklist_trend_reversal(coin, trend_result.score):
                        logger.info(f"✅ {coin} 已从黑名单移除，趋势评分{trend_result.score}分")
                    else:
                        continue

                if sideways_manager.is_paused(coin):
                    continue

                last_price = float(ticker.get("last", 0))
                volume_24h = float(ticker.get("vol24h", 0))
                turnover_24h = volume_24h * last_price
                low_24h = float(ticker.get("low24h", last_price))
                high_24h = float(ticker.get("high24h", last_price))
                
                if last_price < config.min_price:
                    continue
                
                if turnover_24h < config.min_turnover_24h:
                    continue
                
                open_price = float(ticker.get("open24h", last_price))
                change_24h = ((last_price - open_price) / open_price * 100) if open_price > 0 else 0
                
                all_tickers.append({
                    "coin": coin,
                    "inst_id": inst_id,
                    "last_price": last_price,
                    "change_24h": change_24h,
                    "volume_24h": volume_24h,
                    "turnover_24h": turnover_24h,
                    "low_24h": low_24h,
                    "high_24h": high_24h
                })
            
            all_tickers.sort(key=lambda x: x["turnover_24h"], reverse=True)
            candidate_coins = all_tickers[:config.max_coins]
            
            logger.info(f"📋 初步筛选: 通过{len(candidate_coins)}个 (按成交额排序，取前{config.max_coins}个)")
            self._log(f"📋 初步筛选: 通过{len(candidate_coins)}个")
            logger.info("")
            logger.info(f"发现 {len(candidate_coins)} 个活跃交易币种")
            self._log(f"发现 {len(candidate_coins)} 个活跃交易币种")
            
            # 获取当前持仓数
            current_long_positions = len(simulation_manager.get_positions())
            current_short_positions = len(simulation_manager.get_short_positions())
            logger.info("")
            logger.info(f"📊 当前持仓: 多单 {current_long_positions}/{self.config.long_max_positions} 个, 空单 {current_short_positions}/{self.config.short_max_positions} 个")
            self._log(f"📊 当前持仓: 多单 {current_long_positions}/{self.config.long_max_positions} 个, 空单 {current_short_positions}/{self.config.short_max_positions} 个")
            
            stablecoins = ['USDC', 'USDT', 'DAI', 'TUSD', 'BUSD', 'USDG', 'USDE', 'FDUSD', 'PAXG', 'XAUT']
            
            candidates_with_trend = []
            
            for candidate in candidate_coins:
                coin = candidate["coin"]
                inst_id = candidate["inst_id"]
                last_price = candidate["last_price"]
                change_24h = candidate["change_24h"]
                volume_24h = candidate["volume_24h"]
                turnover_24h = candidate["turnover_24h"]
                low_24h = candidate.get("low_24h", last_price)
                high_24h = candidate.get("high_24h", last_price)
                
                if coin in stablecoins:
                    continue
                
                try:
                    candles_result = await client.get_candles(inst_id, bar="5m", limit=50)
                    if candles_result.get("code") != "0":
                        continue
                    candles = candles_result.get("data", [])
                    trend_result = await analyze_trend(candles)
                    trend_score = trend_result.score
                    trend = trend_result.trend
                    original_bullish_score = getattr(trend_result, 'bullish_score', 5)
                    original_bearish_score = getattr(trend_result, 'bearish_score', 5)

                    # 情绪融合（可选，对齐 ai_trading_bot.js）
                    # 融合后的 bullish_score 用于所有策略（主策略 + Fallback）
                    if self.config.sentiment_fusion_enabled:
                        try:
                            # 根据模式选择融合方法
                            if self.config.sentiment_fusion_mode == "free":
                                # 免费模式：CoinGecko + Fear & Greed Index（推荐）
                                sentiment_result = await sentiment_service.fuse_with_technical_score_v2(
                                    coin=coin,
                                    technical_score=original_bullish_score,
                                    coingecko_weight=self.config.sentiment_coingecko_weight,
                                    fear_greed_weight=self.config.sentiment_fear_greed_weight,
                                    technical_weight=self.config.sentiment_technical_weight,
                                    use_cache=True,
                                    timeout=self.config.sentiment_fetch_timeout
                                )
                                bullish_score = sentiment_result["fused_score"]
                                bearish_score = 10 - bullish_score
                                trend_score = sentiment_result["fused_score"]
                                
                                if sentiment_result.get("warning"):
                                    logger.info(f"  ⚠️ {coin} {sentiment_result['warning']}")
                                
                                fg_data = sentiment_result.get("fear_greed_data", {})
                                fg_value = fg_data.get("value", 50) if fg_data else 50
                                fg_class = fg_data.get("classification", "Neutral") if fg_data else "Neutral"
                                logger.info(f"  🔄 {coin} 情绪融合(免费): 技术面{original_bullish_score} + CoinGecko{sentiment_result['coingecko_score']} + Fear&Greed[{fg_value} {fg_class}]→ 综合{bullish_score}")
                            else:
                                # 新闻模式：CoinGecko + 新闻（原有方式）
                                sentiment_result = await sentiment_service.fuse_with_technical_score(
                                    coin=coin,
                                    technical_score=original_bullish_score,
                                    coingecko_weight=self.config.sentiment_coingecko_weight,
                                    news_weight=self.config.sentiment_news_weight,
                                    technical_weight=self.config.sentiment_technical_weight,
                                    use_cache=True,
                                    timeout=self.config.sentiment_fetch_timeout,
                                    bearish_alert_threshold=self.config.sentiment_bearish_alert_threshold
                                )
                                bullish_score = sentiment_result["fused_score"]
                                bearish_score = 10 - bullish_score
                                trend_score = sentiment_result["fused_score"]
                                
                                if sentiment_result.get("warning"):
                                    logger.info(f"  ⚠️ {coin} {sentiment_result['warning']}")
                                
                                logger.info(f"  🔄 {coin} 情绪融合: 技术面{original_bullish_score} + CoinGecko{sentiment_result['coingecko_score']} + 新闻{sentiment_result['news_score']} → 综合{bullish_score}")
                        except Exception as e:
                            logger.warning(f"  ⚠️ {coin} 情绪融合失败: {e}，使用纯技术面评分")
                            bullish_score = original_bullish_score
                            bearish_score = original_bearish_score
                    else:
                        bullish_score = original_bullish_score
                        bearish_score = original_bearish_score

                    sideways_result = await sideways_manager.check_sideways(client, inst_id, trend_score)
                    if sideways_result.is_sideways:
                        logger.info(f"  ⏸️ {coin} 横盘中({sideways_result.reason})，暂不考虑买入")
                        self._log(f"  ⏸️ {coin} 横盘中，暂不考虑买入")
                        continue

                    candidates_with_trend.append({
                        "coin": coin,
                        "inst_id": inst_id,
                        "last_price": last_price,
                        "change_24h": change_24h,
                        "volume_24h": volume_24h,
                        "turnover_24h": turnover_24h,
                        "low_24h": low_24h,
                        "high_24h": high_24h,
                        "trend_score": trend_score,
                        "trend": trend,
                        "bullish_score": bullish_score,
                        "bearish_score": bearish_score,
                        "signals": trend_result.signals,
                        "indicators": trend_result.indicators
                    })
                except Exception as e:
                    logger.error(f"分析 {coin} 失败: {e}")
                    continue
            
            candidates_with_trend.sort(key=lambda x: x["trend_score"], reverse=True)
            
            logger.info("")
            logger.info("📊 候选币种趋势分析:")
            self._log("📊 候选币种趋势分析:")
            
            passed_coins = []
            filtered_by_trend = 0
            
            for c in candidates_with_trend[:10]:
                coin = c["coin"]
                trend_score = c["trend_score"]
                trend = c["trend"]
                bullish_score = c.get("bullish_score", 5)
                bearish_score = c.get("bearish_score", 5)
                change_24h = c["change_24h"]
                volume_24h = c["volume_24h"]
                turnover_24h = c["turnover_24h"]
                last_price = c["last_price"]
                inst_id = c["inst_id"]
                signals = c["signals"]
                low_24h = c.get("low_24h", last_price)
                high_24h = c.get("high_24h", last_price)
                
                rebound_percent = ((last_price - low_24h) / low_24h * 100) if low_24h > 0 else 0
                
                trend_emoji = "📈" if trend == "bullish" else "➡️" if trend == "neutral" else "📉"
                trend_status = "看涨" if trend == "bullish" else "横盘" if trend == "neutral" else "看跌"

                rsi_value = c["indicators"].get("rsi", 50.0)
                volume_ratio = c["indicators"].get("volume_ratio", 1.0)

                logger.info(f"  {trend_emoji} {coin}: 评分{trend_score}/10 {trend_status} [看涨{bullish_score}/看跌{bearish_score}] [{', '.join(signals[:3])}], 24h涨跌{change_24h:.2f}%, 成交量${turnover_24h/1000000:.2f}M")
                self._log(f"  {trend_emoji} {coin}: 评分{trend_score}/10 {trend_status}, 看涨{bullish_score}/看跌{bearish_score}, 24h涨跌{change_24h:.2f}%")

                # 初始化做空变量
                can_short = False
                short_reason = ""
                short_signal_type = "resonance"

                # 获取连续阳线数据（用于做空Fallback）
                bullish_result = await check_consecutive_bullish_candles(
                    client, inst_id, last_price
                )
                bullish_dict = {
                    "is_bullish": bullish_result.is_bullish if hasattr(bullish_result, 'is_bullish') else False,
                    "consecutive_count": getattr(bullish_result, 'consecutive_count', 0),
                    "reason": getattr(bullish_result, 'reason', '')
                }

                # ============================================================
                # 核心逻辑：与示例项目对齐
                # 做多：bullish_score >= long_min_bullish_score → 共振分析
                # 做空：bearish_score >= short_min_bearish_score → 共振分析
                # 不达标时检查Fallback信号
                # ============================================================

                can_buy = False
                buy_reason = ""
                signal_type = "resonance"
                resonance_result = None

                # 获取阴线数据（用于Fallback）
                bearish_result = await check_consecutive_bearish_candles(
                    client, inst_id, last_price
                )
                bearish_dict = {
                    "is_bearish": bearish_result.is_bearish,
                    "consecutive_count": getattr(bearish_result, 'consecutive_count', 0),
                    "reason": bearish_result.reason
                }
                indicators = c["indicators"]

                # 根据大盘环境决定只分析单方向
                market_env = getattr(self, '_market_env_cache', None)
                market_favor_long = market_env and market_env.score >= 4  # 大盘好适合做多
                market_favor_short = market_env and market_env.score < 4  # 大盘差适合做空

                # ========== 做多逻辑（仅大盘好时执行） ==========
                if market_favor_long:
                    # 第一层：看涨评分达标 → 执行共振分析
                    if bullish_score >= self.config.long_min_bullish_score:
                        logger.info(f"    🎯 {coin} 看涨评分达标({bullish_score}>={self.config.long_min_bullish_score})，大盘良好，启动做多共振分析...")
                        self._log(f"    🎯 {coin} 看涨评分达标({bullish_score}>={self.config.long_min_bullish_score})，启动做多共振分析")

                        indicators = c["indicators"]
                        technical_config = {
                            "min_pass_count": self.config.technical_min_pass_count,
                            "trend_score_threshold": self.config.technical_trend_score_threshold,
                            "rsi_min": self.config.technical_rsi_min,
                            "rsi_max": self.config.technical_rsi_max,
                            "volume_ratio_min": self.config.technical_volume_ratio_min,
                            "ma5_tolerance": self.config.technical_ma5_tolerance,
                            "volatility_min": self.config.technical_volatility_min
                        }
                        resonance_result = await calculate_resonance_score(
                            client, inst_id, trend_score, last_price,
                            min_capital_flow_score=self.config.min_capital_flow_score,
                            market_env=market_env,
                            rsi=indicators.get("rsi", 50.0),
                            volume_ratio=None,
                            ma5=indicators.get("ma5", last_price),
                            volatility=None,
                            technical_config=technical_config
                        )

                        if resonance_result.can_buy:
                            can_buy = True
                            buy_reason = f"共振通过(评分{resonance_result.total_score})"
                            signal_type = "resonance"
                            logger.info(f"  ✅ {coin} 共振分析通过: 总分{resonance_result.total_score}, 资金{resonance_result.capital_flow_score}, 大盘{resonance_result.market_env_score}")
                            self._log(f"  ✅ {coin} 共振通过 ✅ 总分={resonance_result.total_score} 资金={resonance_result.capital_flow_score} 大盘={resonance_result.market_env_score}")
                        else:
                            logger.info(f"    ⏭️ {coin} 共振分析未通过: {resonance_result.reason}")
                            self._log(f"    ⏭️ {coin} 共振未通过 总分={resonance_result.total_score} 原因: {resonance_result.reason}")

                    # 第二层：Fallback信号（看涨评分不达标时，也需要大盘好）
                    if not can_buy and bullish_score < self.config.bullish_fallback_threshold:
                        # 严格抄底策略（需要大盘好：BTC>=6, ETH>=5）
                        if self.config.dip_buy_enabled:
                            btc_trend = market_env.btc_score if market_env else 5
                            eth_trend = market_env.eth_score if hasattr(market_env, 'eth_score') else 5
                            market_ok_for_dip = btc_trend >= 6 and eth_trend >= 5  # 大盘验证

                            if market_ok_for_dip:
                                strict_dip_check = self._check_strict_dip_buy(
                                    trend_score, btc_trend, eth_trend, rsi_value, volume_ratio, bearish_dict, last_price, indicators
                                )
                                if strict_dip_check["passed"]:
                                    can_buy = True
                                    buy_reason = strict_dip_check["reason"]
                                    signal_type = "strict_dip"
                                    logger.info(f"  ✅ {coin} 通过严格抄底筛选: {strict_dip_check['reason']}")
                                    self._log(f"  ✅ {coin} 抄底信号 ✅ RSI={rsi_value:.1f} 成交量={volume_ratio:.2f}x")
                            else:
                                logger.info(f"    ⏭️ {coin} 抄底条件不满足: 大盘弱(BTC={btc_trend}/ETH={eth_trend})")

                        # 阴线买入信号（需要大盘好）
                        if not can_buy and self.config.bearish_candle_enabled and bearish_result.is_bearish:
                            bearish_candle_check = self._check_bearish_candle(
                                trend_score, rsi_value, volume_ratio, bearish_dict
                            )
                            if bearish_candle_check["passed"]:
                                can_buy = True
                                buy_reason = bearish_candle_check["reason"]
                                signal_type = "bearish_candle"
                                logger.info(f"  ✅ {coin} 通过阴线买入筛选: {bearish_candle_check['reason']}")
                                self._log(f"  ✅ {coin} 阴线买入信号 ✅ RSI={rsi_value:.1f} 成交量={volume_ratio:.2f}x")

                        # 暴跌反弹信号（需要大盘好）
                        if not can_buy and self.config.crash_rebound_enabled:
                            crash_rebound_check = self._check_crash_rebound(
                                change_24h, trend_score, volume_ratio, rebound_percent, rsi_value
                            )
                            if crash_rebound_check["passed"]:
                                can_buy = True
                                buy_reason = crash_rebound_check["reason"]
                                signal_type = "crash_rebound"
                                logger.info(f"  ✅ {coin} 通过暴跌反弹筛选: {crash_rebound_check['reason']}")
                                self._log(f"  ✅ {coin} 暴跌反弹信号 ✅ RSI={rsi_value:.1f} 成交量={volume_ratio:.2f}x 24h={change_24h:.1f}%")

                # ========== 做空逻辑（仅大盘差时执行） ==========
                elif market_favor_short:
                    # 第一层：看跌评分达标 → 执行共振分析
                    if bearish_score >= self.config.short_min_bearish_score:
                        logger.info(f"    🎯 {coin} 看跌评分达标({bearish_score}>={self.config.short_min_bearish_score})，大盘较差，启动做空共振分析...")
                        self._log(f"    🎯 {coin} 看跌评分达标({bearish_score}>={self.config.short_min_bearish_score})，启动做空共振分析")

                        technical_config = {
                            "min_pass_count": self.config.technical_min_pass_count,
                            "trend_score_threshold": self.config.technical_trend_score_threshold,
                            "rsi_min": self.config.technical_rsi_min,
                            "rsi_max": self.config.technical_rsi_max,
                            "volume_ratio_min": self.config.technical_volume_ratio_min,
                            "ma5_tolerance": self.config.technical_ma5_tolerance,
                            "volatility_min": self.config.technical_volatility_min
                        }
                        resonance_result = await calculate_resonance_score(
                            client, inst_id, trend_score, last_price,
                            min_capital_flow_score=self.config.min_capital_flow_score,
                            market_env=market_env,
                            rsi=indicators.get("rsi", 50.0),
                            volume_ratio=None,
                            ma5=indicators.get("ma5", last_price),
                            volatility=None,
                            technical_config=technical_config
                        )

                        # 做空共振判断：总分>=6 且 资金流出（大盘环境差更适合做空）
                        short_resonance_pass = (
                            resonance_result.total_score >= 6 and
                            (not resonance_result.capital_flow_score >= 7)  # 资金不是强势流入
                        )
                        if short_resonance_pass:
                            can_short = True
                            short_reason = f"共振通过(评分{resonance_result.total_score})"
                            short_signal_type = "resonance"
                            logger.info(f"  🔴 {coin} 做空共振分析通过: 总分{resonance_result.total_score}, 大盘={resonance_result.market_env_score}分(大盘差更适合做空)")
                            self._log(f"  🔴 {coin} 做空共振通过 ✅ 总分={resonance_result.total_score} 资金={resonance_result.capital_flow_score} 大盘={resonance_result.market_env_score}(大盘差更适合做空)")
                        else:
                            logger.info(f"    ⏭️ {coin} 做空共振分析未通过")
                            self._log(f"    ⏭️ {coin} 做空共振未通过 总分={resonance_result.total_score} 资金={resonance_result.capital_flow_score}")

                    # 第二层：Fallback信号（看跌评分不达标时，也需要大盘差）
                    if not can_short and bearish_score < self.config.short_bearish_fallback_threshold:
                        # 严格做空策略（顶部做空，需要大盘差：BTC<6或ETH<5）
                        if self.config.short_dip_enabled:
                            btc_trend = market_env.btc_score if market_env else 5
                            eth_trend = market_env.eth_score if hasattr(market_env, 'eth_score') else 5
                            market_ok_for_short = btc_trend < 6 or eth_trend < 5  # 大盘差验证

                            if market_ok_for_short:
                                short_dip_check = self._check_short_dip(
                                    trend_score, btc_trend, eth_trend, rsi_value, volume_ratio,
                                    bullish_dict, last_price, indicators
                                )
                                if short_dip_check["passed"]:
                                    can_short = True
                                    short_reason = short_dip_check["reason"]
                                    short_signal_type = "short_dip"
                                    logger.info(f"    🎯 {coin} 通过顶部做空筛选: {short_dip_check['reason']}")
                                    self._log(f"    🎯 {coin} 顶部做空信号 ✅ RSI={rsi_value:.1f} 成交量={volume_ratio:.2f}x")
                            else:
                                logger.info(f"    ⏭️ {coin} 顶部做空条件不满足: 大盘强(BTC={btc_trend}/ETH={eth_trend})")

                        # 阳线卖出信号（需要大盘差）
                        if not can_short and self.config.short_bearish_enabled:
                            short_bearish_check = self._check_short_bearish(
                                trend_score, rsi_value, volume_ratio, bullish_dict.get("consecutive_count", 0), indicators
                            )
                            if short_bearish_check["passed"]:
                                can_short = True
                                short_reason = short_bearish_check["reason"]
                                short_signal_type = "short_bearish"
                                logger.info(f"    🎯 {coin} 通过阳线卖出筛选: {short_bearish_check['reason']}")
                                self._log(f"    🎯 {coin} 阳线卖出信号 ✅ RSI={rsi_value:.1f} 成交量={volume_ratio:.2f}x")

                        # 暴涨回落信号（需要大盘差）
                        if not can_short and self.config.short_crash_enabled:
                            short_crash_check = self._check_short_crash(
                                change_24h, trend_score, 0, rsi_value, volume_ratio
                            )
                            if short_crash_check["passed"]:
                                can_short = True
                                short_reason = short_crash_check["reason"]
                                short_signal_type = "short_crash"
                                logger.info(f"    🎯 {coin} 通过暴涨回落筛选: {short_crash_check['reason']}")
                                self._log(f"    🎯 {coin} 暴涨回落信号 ✅ RSI={rsi_value:.1f} 成交量={volume_ratio:.2f}x 24h={change_24h:.1f}%")

                # 最终判断：做多或做空条件都不满足，跳过
                if not can_buy and not can_short:
                    logger.info(f"    ⏭️ {coin} 做多做空条件都不满足，跳过")
                    self._log(f"    ⏭️ {coin} 做多做空条件都不满足，跳过")
                    continue

                # 多空互斥决策：如果同时满足做多和做空条件，选择盈利概率更高的方向
                if can_buy and can_short and self.config.mutual_exclusive_enabled:
                    market_env = getattr(self, '_market_env_cache', None)
                    btc_trend = market_env.btc_score if market_env else 5
                    eth_trend = market_env.eth_score if hasattr(market_env, 'eth_score') else 5
                    capital_flow_score = resonance_result.capital_flow_score if resonance_result else 5

                    decision = self._decide_trade_direction(
                        trend_score=trend_score,
                        bullish_score=bullish_score,
                        bearish_score=bearish_score,
                        rsi=rsi_value,
                        volume_ratio=volume_ratio,
                        btc_trend=btc_trend,
                        eth_trend=eth_trend,
                        capital_flow_score=capital_flow_score,
                        min_score_threshold=self.config.mutual_exclusive_min_score,
                        score_diff_threshold=self.config.mutual_exclusive_score_diff
                    )

                    if decision["direction"] == "long":
                        can_short = False
                        logger.info(f"  ⚖️ {coin} 多空互斥决策: 选择做多 ({decision['reason']})")
                        self._log(f"  ⚖️ {coin} 多空互斥决策: 选择做多 (多{decision['long_score']:.0f}/空{decision['short_score']:.0f})")
                    elif decision["direction"] == "short":
                        can_buy = False
                        logger.info(f"  ⚖️ {coin} 多空互斥决策: 选择做空 ({decision['reason']})")
                        self._log(f"  ⚖️ {coin} 多空互斥决策: 选择做空 (多{decision['long_score']:.0f}/空{decision['short_score']:.0f})")
                    else:
                        # 观望，不开仓
                        can_buy = False
                        can_short = False
                        logger.info(f"  ⚖️ {coin} 多空互斥决策: 观望 ({decision['reason']})")
                        self._log(f"  ⚖️ {coin} 多空互斥决策: 观望 (多{decision['long_score']:.0f}/空{decision['short_score']:.0f})")
                        continue

                if can_buy or can_short:
                    if can_buy:
                        logger.info(f"  ✅ {coin} 通过买入筛选: {buy_reason}")
                        self._log(f"  ✅ {coin} 买入信号通过 ✅ {buy_reason}")
                    if can_short:
                        logger.info(f"  🔴 {coin} 通过做空筛选: {short_reason}")
                        self._log(f"  🔴 {coin} 做空信号通过 ✅ {short_reason}")
                    passed_coins.append(coin)

                    # 如果还没有共振结果，计算一次
                    if resonance_result is None:
                        market_env = getattr(self, '_market_env_cache', None)
                        technical_config = {
                            "min_pass_count": self.config.technical_min_pass_count,
                            "trend_score_threshold": self.config.technical_trend_score_threshold,
                            "rsi_min": self.config.technical_rsi_min,
                            "rsi_max": self.config.technical_rsi_max,
                            "volume_ratio_min": self.config.technical_volume_ratio_min,
                            "ma5_tolerance": self.config.technical_ma5_tolerance,
                            "volatility_min": self.config.technical_volatility_min
                        }
                        resonance_result = await calculate_resonance_score(
                            client, inst_id, trend_score, last_price,
                            min_capital_flow_score=self.config.min_capital_flow_score,
                            market_env=market_env,
                            rsi=indicators.get("rsi", 50.0),
                            volume_ratio=None,
                            ma5=indicators.get("ma5", last_price),
                            volatility=None,
                            technical_config=technical_config
                        )

                    reason = resonance_result.reason

                    opportunities.append({
                        "coin": coin,
                        "inst_id": inst_id,
                        "price": last_price,
                        "change_24h": change_24h,
                        "volume_24h": volume_24h,
                        "trend_score": trend_score,
                        "bullish_score": bullish_score,
                        "bearish_score": bearish_score,
                        "resonance_score": resonance_result.total_score,
                        "signal_type": signal_type,
                        "reason": reason,
                        "can_buy": can_buy,
                        "can_short": can_short,
                        "short_reason": short_reason,
                        "resonance_details": resonance_result,
                        "indicators": c["indicators"],
                        "strategy": "短线策略"
                    })
        
        opportunities.sort(key=lambda x: x["trend_score"], reverse=True)
        
        logger.info("")
        logger.info(f"🎯 严格筛选结果: {len(passed_coins)} 个币种通过")
        self._log(f"🎯 严格筛选结果: {len(passed_coins)} 个币种通过")
        
        return opportunities
    
    def _check_low_buy_conditions(self, change_24h: float, volume_24h: float, trend_score: int, turnover_24h: float = 0, price: float = 0, trend: str = "neutral", rsi: float = 50.0, volume_ratio: float = 1.0) -> Dict:
        passed = False
        reasons = []
        checks = []

        # 条件1: 趋势评分在合理区间
        trend_score_ok = self.config.long_min_trend_score <= trend_score <= self.config.long_max_trend_score
        checks.append(f"趋势评分{trend_score}" + ("✓" if trend_score_ok else f"✗(需{self.config.long_min_trend_score}-{self.config.long_max_trend_score})"))

        # 条件2: RSI在合理区间
        rsi_ok = self.config.long_rsi_min <= rsi <= self.config.long_rsi_max
        checks.append(f"RSI{rsi:.1f}" + ("✓" if rsi_ok else f"✗(需{self.config.long_rsi_min}-{self.config.long_rsi_max})"))

        # 条件3: 24h涨跌幅在合理区间
        change_ok = self.config.long_min_pullback_percent <= change_24h <= self.config.long_max_pullback_percent
        checks.append(f"24h涨跌{change_24h:.2f}%" + ("✓" if change_ok else f"✗(需{self.config.long_min_pullback_percent}-{self.config.long_max_pullback_percent}%)"))

        # 条件4: 成交量比例
        volume_ok = volume_ratio >= self.config.long_min_volume_ratio
        checks.append(f"成交量{volume_ratio:.2f}x" + ("✓" if volume_ok else f"✗(需>={self.config.long_min_volume_ratio}x)"))

        # 综合判断：所有条件必须满足
        passed = trend_score_ok and rsi_ok and change_ok and volume_ok

        if passed:
            reasons.append(f"短线策略：趋势{trend_score}分，RSI{rsi:.1f}，成交量{volume_ratio:.2f}x，24h{change_24h:.2f}%")

        return {
            "passed": passed,
            "reason": ", ".join(reasons) if reasons else " | ".join(checks),
            "checks": checks
        }

    def _check_bearish_candle(self, trend_score: int, rsi: float, volume_ratio: float, bearish_result: Dict) -> Dict:
        """
        阴线买入信号检查（连续阴线后反弹）
        与做空阳线卖出对称
        """
        passed = False
        reasons = []
        checks = []

        if not self.config.bearish_candle_enabled:
            return {
                "passed": False,
                "reason": "阴线买入策略未启用",
                "checks": ["阴线买入策略未启用"]
            }

        # 条件1: 趋势评分 >= 配置的最小趋势评分
        trend_ok = trend_score >= self.config.bearish_candle_min_trend_score
        checks.append(f"趋势评分{trend_score}" + ("✓" if trend_ok else f"✗(需≥{self.config.bearish_candle_min_trend_score})"))

        # 条件2: RSI < 配置的超卖阈值
        rsi_ok = rsi < self.config.bearish_candle_rsi_oversold if self.config.bearish_candle_rsi_enabled else True
        checks.append(f"RSI{rsi:.1f}" + ("✓" if rsi_ok else f"✗(需<{self.config.bearish_candle_rsi_oversold})"))

        # 条件3: 成交量放大 > 配置的成交量比例
        volume_ok = volume_ratio > self.config.bearish_candle_volume_ratio if self.config.bearish_candle_volume_enabled else True
        checks.append(f"成交量{volume_ratio:.2f}x" + ("✓" if volume_ok else f"✗(需>{self.config.bearish_candle_volume_ratio}x)"))

        # 条件4: 连续阴线
        bearish_ok = bearish_result.get("is_bearish", False)
        bearish_count = bearish_result.get("consecutive_count", 0)
        checks.append(f"连续阴线{bearish_count}根" + ("✓" if bearish_ok else "✗"))

        # 综合判断
        passed = trend_ok and rsi_ok and volume_ok and bearish_ok

        if passed:
            reasons.append(f"阴线买入：趋势{trend_score}分，RSI{rsi:.1f}，成交量{volume_ratio:.2f}x，连续{bearish_count}根阴线")

        return {
            "passed": passed,
            "reason": ", ".join(reasons) if reasons else " | ".join(checks),
            "checks": checks
        }

    def _check_crash_rebound(self, change_24h: float, trend_score: int, volume_ratio: float, rebound_percent: float = 0.0, rsi: float = 50.0) -> Dict:
        """
        暴跌反弹信号检查（24h暴跌后趋势回升）
        与做空暴涨回落对称
        """
        passed = False
        reasons = []
        checks = []

        if not self.config.crash_rebound_enabled:
            return {
                "passed": False,
                "reason": "暴跌反弹策略未启用",
                "checks": ["暴跌反弹策略未启用"]
            }

        # 条件1: 24h跌幅 >= 阈值
        crash_ok = change_24h <= self.config.crash_rebound_threshold
        checks.append(f"24h跌幅{change_24h:.2f}%" + ("✓" if crash_ok else f"✗(需<={self.config.crash_rebound_threshold}%)"))

        # 条件2: 反弹时趋势评分 >= 阈值
        rebound_trend_ok = trend_score >= self.config.crash_rebound_min_trend_score
        checks.append(f"反弹趋势{trend_score}分" + ("✓" if rebound_trend_ok else f"✗(需>={self.config.crash_rebound_min_trend_score})"))

        # 条件3: 反弹幅度 >= 阈值
        rebound_ok = rebound_percent >= self.config.crash_rebound_min_rebound_percent
        checks.append(f"反弹幅度{rebound_percent:.2f}%" + ("✓" if rebound_ok else f"✗(需>={self.config.crash_rebound_min_rebound_percent}%)"))

        # 条件4: 成交量放大
        volume_ok = volume_ratio > self.config.crash_rebound_volume_ratio
        checks.append(f"成交量{volume_ratio:.2f}x" + ("✓" if volume_ok else f"✗(需>{self.config.crash_rebound_volume_ratio}x)"))

        # 条件5: RSI超卖检查（可选）
        if self.config.crash_rebound_rsi_check_enabled:
            rsi_ok = rsi < self.config.crash_rebound_rsi_threshold
            checks.append(f"RSI{rsi:.1f}" + ("✓" if rsi_ok else f"✗(需<{self.config.crash_rebound_rsi_threshold})"))
        else:
            rsi_ok = True
            checks.append(f"RSI检查跳过")

        # 综合判断
        passed = crash_ok and rebound_trend_ok and rebound_ok and volume_ok and rsi_ok

        if passed:
            reasons.append(f"暴跌反弹：24h跌幅{change_24h:.2f}%，反弹{rebound_percent:.2f}%，趋势{trend_score}分，成交量{volume_ratio:.2f}x")

        return {
            "passed": passed,
            "reason": ", ".join(reasons) if reasons else " | ".join(checks),
            "checks": checks
        }

    def _check_short_term(self, bearish_score: int, change_24h: float, rsi: float, volume_ratio: float, bullish_score: int) -> Dict:
        """
        做空短线高胜率策略检查（与做多短线高胜率对称）
        优先检查做空条件，不满足再走严格做空策略
        """
        passed = False
        reasons = []
        checks = []

        if not self.config.enable_short:
            return {
                "passed": False,
                "reason": "做空功能未启用",
                "checks": ["做空功能未启用"]
            }

        # 条件1: 看跌评分达标 (>=7)
        bearish_ok = bearish_score >= self.config.short_min_bearish_score
        checks.append(f"看跌评分{bearish_score}" + ("✓" if bearish_ok else f"✗(需>={self.config.short_min_bearish_score})"))

        # 条件2: 看涨评分不能过高（避免多空分歧时开空单）
        not_bullish = bullish_score < self.config.long_min_bullish_score
        checks.append(f"看涨评分{bullish_score}" + ("✓" if not_bullish else f"✗(需<{self.config.long_min_bullish_score})"))

        # 条件3: 高位 (24h涨幅 > 配置值)
        high_price = change_24h > self.config.short_min_pullback_percent
        checks.append(f"24h涨幅{change_24h:.2f}%" + ("✓" if high_price else f"✗(需>{self.config.short_min_pullback_percent}%)"))

        # 条件4: RSI超买区间
        rsi_overbought = self.config.short_rsi_min <= rsi <= self.config.short_rsi_max
        checks.append(f"RSI{rsi:.1f}" + ("✓" if rsi_overbought else f"✗(区间{self.config.short_rsi_min}-{self.config.short_rsi_max})"))

        # 条件5: 成交量放大
        volume_ok = volume_ratio > self.config.short_min_volume_ratio
        checks.append(f"成交量{volume_ratio:.2f}x" + ("✓" if volume_ok else f"✗(需>{self.config.short_min_volume_ratio}x)"))

        # 综合判断
        passed = bearish_ok and not_bullish and high_price and rsi_overbought and volume_ok

        if passed:
            reasons.append(f"短线做空：看跌{bearish_score}分，看涨{bullish_score}分(偏空)，涨幅{change_24h:.2f}%，RSI{rsi:.1f}，成交量{volume_ratio:.2f}x")

        return {
            "passed": passed,
            "reason": ", ".join(reasons) if reasons else " | ".join(checks),
            "checks": checks
        }

    def _check_strict_dip_buy(self, trend_score: int, btc_trend: int, eth_trend: int, rsi: float, volume_ratio: float, bearish_result: Dict, current_price: float = 0, indicators: Dict = None) -> Dict:
        passed = False
        reasons = []
        checks = []

        if not self.config.dip_buy_enabled:
            return {
                "passed": False,
                "reason": "严格抄底策略未启用",
                "checks": ["严格抄底策略未启用"]
            }

        if indicators is None:
            indicators = {}

        # 条件1: 趋势评分验证（≥7分）
        trend_ok = trend_score >= self.config.dip_buy_min_trend_score
        checks.append(f"趋势评分{trend_score}" + ("✓" if trend_ok else f"✗(需≥{self.config.dip_buy_min_trend_score})"))

        # 条件2: 大盘趋势验证（BTC≥6, ETH≥5）
        btc_ok = btc_trend >= self.config.dip_buy_min_btc_trend
        eth_ok = eth_trend >= self.config.dip_buy_min_eth_trend
        market_ok = btc_ok and eth_ok
        checks.append(f"大盘趋势BTC{btc_trend}/ETH{eth_trend}" + ("✓" if market_ok else f"✗(需BTC≥{self.config.dip_buy_min_btc_trend},ETH≥{self.config.dip_buy_min_eth_trend})"))

        # 条件3: RSI超卖验证（<35）
        rsi_ok = rsi < self.config.dip_buy_rsi_threshold
        checks.append(f"RSI{rsi:.1f}" + ("✓" if rsi_ok else f"✗(需<{self.config.dip_buy_rsi_threshold})"))

        # 条件4: 成交量放量验证（>2倍）
        volume_ok = volume_ratio > self.config.dip_buy_volume_multiplier
        checks.append(f"成交量{volume_ratio:.2f}x" + ("✓" if volume_ok else f"✗(需>{self.config.dip_buy_volume_multiplier}x)"))

        # 条件5: 连续阴线验证（3根+第4根收阳）
        bearish_ok = bearish_result.get("is_bearish", False) if self.config.dip_buy_require_bullish_reversal else bearish_result.get("consecutive_count", 0) >= self.config.dip_buy_min_consecutive_bearish
        bearish_count = bearish_result.get("consecutive_count", 0)
        checks.append(f"连续阴线{bearish_count}根" + ("✓" if bearish_ok else f"✗(需≥{self.config.dip_buy_min_consecutive_bearish}根+收阳)"))

        # 条件6: 价格位置验证（<MA5且<MA10）
        ma5 = indicators.get("ma5", 0)
        ma10 = indicators.get("ma10", 0)
        below_ma5 = current_price < ma5 if ma5 > 0 else True
        below_ma10 = current_price < ma10 if ma10 > 0 else True
        price_ok = (not self.config.dip_buy_price_below_ma5 or below_ma5) and (not self.config.dip_buy_price_below_ma10 or below_ma10)
        ma_status = []
        if self.config.dip_buy_price_below_ma5:
            ma_status.append(f"MA5{'✓' if below_ma5 else '✗'}")
        if self.config.dip_buy_price_below_ma10:
            ma_status.append(f"MA10{'✓' if below_ma10 else '✗'}")
        checks.append(f"价格位置{'✓' if price_ok else '✗'}({','.join(ma_status)})")

        # 综合判断：所有条件必须满足
        passed = trend_ok and market_ok and rsi_ok and volume_ok and bearish_ok and price_ok

        if passed:
            reasons.append(f"严格抄底：趋势{trend_score}分，BTC{btc_trend}分，ETH{eth_trend}分，RSI{rsi:.1f}，成交量{volume_ratio:.2f}x")

        return {
            "passed": passed,
            "reason": ", ".join(reasons) if reasons else " | ".join(checks),
            "checks": checks
        }

    def _check_short_dip(self, trend_score: int, btc_trend: int, eth_trend: int, rsi: float,
                         volume_ratio: float, bullish_result: Dict, current_price: float = 0,
                         indicators: Dict = None) -> Dict:
        """
        严格追空策略检查（与严格抄底对称）
        用于在连续上涨后追空
        """
        passed = False
        reasons = []
        checks = []

        if not self.config.short_dip_enabled:
            return {
                "passed": False,
                "reason": "顶部做空策略未启用",
                "checks": ["顶部做空策略未启用"]
            }

        if indicators is None:
            indicators = {}

        # 条件1: 趋势评分在下跌区间（<=4分）
        trend_ok = trend_score <= self.config.short_dip_max_trend_score
        checks.append(f"趋势评分{trend_score}" + ("✓" if trend_ok else f"✗(需<={self.config.short_dip_max_trend_score})"))

        # 条件2: 大盘弱势（BTC<=4, ETH<=4）
        btc_ok = btc_trend <= self.config.short_dip_max_btc_trend
        eth_ok = eth_trend <= self.config.short_dip_max_eth_trend
        market_ok = btc_ok and eth_ok
        checks.append(f"大盘趋势BTC{btc_trend}/ETH{eth_trend}" + ("✓" if market_ok else f"✗(需BTC<={self.config.short_dip_max_btc_trend},ETH<={self.config.short_dip_max_eth_trend})"))

        # 条件3: RSI超买验证（>65）
        rsi_ok = rsi > self.config.short_dip_rsi_threshold
        checks.append(f"RSI{rsi:.1f}" + ("✓" if rsi_ok else f"✗(需>{self.config.short_dip_rsi_threshold})"))

        # 条件4: 成交量放大验证（>2倍）
        volume_ok = volume_ratio > self.config.short_dip_volume_multiplier
        checks.append(f"成交量{volume_ratio:.2f}x" + ("✓" if volume_ok else f"✗(需>{self.config.short_dip_volume_multiplier}x)"))

        # 条件5: 连续阳线验证（>=3根）
        bullish_count = bullish_result.get("consecutive_count", 0)
        bullish_ok = bullish_count >= self.config.short_dip_min_consecutive_bullish
        checks.append(f"连续阳线{bullish_count}根" + ("✓" if bullish_ok else f"✗(需>={self.config.short_dip_min_consecutive_bullish}根)"))

        # 条件6: 需要收阴确认
        if self.config.short_dip_require_bearish_reversal:
            is_reversal = bullish_result.get("is_bearish", False)
            checks.append(f"收阴确认{'✓' if is_reversal else '✗'}")
        else:
            is_reversal = True

        # 条件7: 价格位置验证（>MA5且>MA10）
        ma5 = indicators.get("ma5", 0)
        ma10 = indicators.get("ma10", 0)
        above_ma5 = current_price > ma5 if ma5 > 0 else True
        above_ma10 = current_price > ma10 if ma10 > 0 else True
        price_ok = (not self.config.short_dip_price_above_ma5 or above_ma5) and (not self.config.short_dip_price_above_ma10 or above_ma10)
        ma_status = []
        if self.config.short_dip_price_above_ma5:
            ma_status.append(f"MA5{'✓' if above_ma5 else '✗'}")
        if self.config.short_dip_price_above_ma10:
            ma_status.append(f"MA10{'✓' if above_ma10 else '✗'}")
        checks.append(f"价格位置{'✓' if price_ok else '✗'}({','.join(ma_status)})")

        # 综合判断：所有条件必须满足
        passed = trend_ok and market_ok and rsi_ok and volume_ok and bullish_ok and is_reversal and price_ok

        if passed:
            reasons.append(f"顶部做空：趋势{trend_score}分，BTC{btc_trend}分，ETH{eth_trend}分，RSI{rsi:.1f}，成交量{volume_ratio:.2f}x，连续阳线{bullish_count}根")

        return {
            "passed": passed,
            "reason": ", ".join(reasons) if reasons else " | ".join(checks),
            "checks": checks
        }

    def _check_short_bearish(self, trend_score: int, rsi: float, volume_ratio: float,
                            consecutive_bullish: int, indicators: Dict = None) -> Dict:
        """
        阳线卖出策略检查（与阴线买入对称）
        连续阳线后做空
        """
        passed = False
        reasons = []
        checks = []

        if not self.config.short_bearish_enabled:
            return {
                "passed": False,
                "reason": "阳线卖出策略未启用",
                "checks": ["阳线卖出策略未启用"]
            }

        if indicators is None:
            indicators = {}

        # 条件1: 趋势评分在下跌区间（<=4分）
        trend_ok = trend_score <= self.config.short_bearish_max_trend_score
        checks.append(f"趋势评分{trend_score}" + ("✓" if trend_ok else f"✗(需<={self.config.short_bearish_max_trend_score})"))

        # 条件2: RSI超买验证（>70）
        if self.config.short_bearish_rsi_enabled:
            rsi_ok = rsi > self.config.short_bearish_rsi_overbought
            checks.append(f"RSI{rsi:.1f}" + ("✓" if rsi_ok else f"✗(需>{self.config.short_bearish_rsi_overbought})"))
        else:
            rsi_ok = True
            checks.append(f"RSI验证跳过")

        # 条件3: 成交量放大验证（>1.2倍）
        if self.config.short_bearish_volume_enabled:
            volume_ok = volume_ratio > self.config.short_bearish_volume_ratio
            checks.append(f"成交量{volume_ratio:.2f}x" + ("✓" if volume_ok else f"✗(需>{self.config.short_bearish_volume_ratio}x)"))
        else:
            volume_ok = True
            checks.append(f"成交量验证跳过")

        # 条件4: 连续阳线数量验证
        bullish_ok = consecutive_bullish >= self.config.short_bearish_consecutive_count
        checks.append(f"连续阳线{consecutive_bullish}根" + ("✓" if bullish_ok else f"✗(需>={self.config.short_bearish_consecutive_count}根)"))

        # 综合判断
        passed = trend_ok and rsi_ok and volume_ok and bullish_ok

        if passed:
            reasons.append(f"阳线卖出：趋势{trend_score}分，RSI{rsi:.1f}，成交量{volume_ratio:.2f}x，连续阳线{consecutive_bullish}根")

        return {
            "passed": passed,
            "reason": ", ".join(reasons) if reasons else " | ".join(checks),
            "checks": checks
        }

    def _check_short_crash(self, change_24h: float, trend_score: int, pullback_percent: float,
                           rsi: float = 50.0, volume_ratio: float = 1.0) -> Dict:
        """
        暴涨回落策略检查（与暴跌反弹对称）
        暴涨后回调做空
        """
        passed = False
        reasons = []
        checks = []

        if not self.config.short_crash_enabled:
            return {
                "passed": False,
                "reason": "暴涨回落策略未启用",
                "checks": ["暴涨回落策略未启用"]
            }

        # 条件1: 24h涨幅达标（>=10%）
        rise_ok = change_24h >= self.config.short_crash_min_rise_24h
        checks.append(f"24h涨幅{change_24h:.2f}%" + ("✓" if rise_ok else f"✗(需>={self.config.short_crash_min_rise_24h}%)"))

        # 条件2: 趋势评分在下跌区间（<=4分）
        trend_ok = trend_score <= self.config.short_crash_max_trend_score
        checks.append(f"趋势评分{trend_score}" + ("✓" if trend_ok else f"✗(需<={self.config.short_crash_max_trend_score})"))

        # 条件3: 回调幅度验证（>=2%）
        pullback_ok = pullback_percent >= self.config.short_crash_min_pullback_percent
        checks.append(f"回调幅度{pullback_percent:.2f}%" + ("✓" if pullback_ok else f"✗(需>={self.config.short_crash_min_pullback_percent}%)"))

        # 条件4: RSI检查（可选）
        if self.config.short_crash_rsi_check_enabled:
            rsi_ok = rsi > self.config.short_crash_rsi_threshold
            checks.append(f"RSI{rsi:.1f}" + ("✓" if rsi_ok else f"✗(需>{self.config.short_crash_rsi_threshold})"))
        else:
            rsi_ok = True
            checks.append(f"RSI检查跳过")

        # 条件5: 成交量检查（可选）
        if self.config.short_crash_volume_check_enabled:
            volume_ok = volume_ratio > self.config.short_crash_volume_ratio
            checks.append(f"成交量{volume_ratio:.2f}x" + ("✓" if volume_ok else f"✗(需>{self.config.short_crash_volume_ratio}x)"))
        else:
            volume_ok = True
            checks.append(f"成交量检查跳过")

        # 综合判断
        passed = rise_ok and trend_ok and pullback_ok and rsi_ok and volume_ok

        if passed:
            reasons.append(f"暴涨回落：涨幅{change_24h:.2f}%，趋势{trend_score}分，回调{pullback_percent:.2f}%")

        return {
            "passed": passed,
            "reason": ", ".join(reasons) if reasons else " | ".join(checks),
            "checks": checks
        }

    def _calculate_long_probability_score(
        self,
        trend_score: int,
        bullish_score: int,
        bearish_score: int,
        rsi: float,
        volume_ratio: float,
        btc_trend: int,
        eth_trend: int,
        capital_flow_score: int
    ) -> float:
        """
        计算做多盈利概率评分 (0-100)
        综合多个因子评估做多的盈利概率
        """
        # 趋势评分 (30%)
        trend_weight = 0.30
        if trend_score >= 8:
            trend_points = 100
        elif trend_score >= 6:
            trend_points = 70
        elif trend_score >= 4:
            trend_points = 40
        else:
            trend_points = 10

        # 看涨评分优势 (25%)
        score_diff_weight = 0.25
        score_diff = bullish_score - bearish_score
        if score_diff >= 3:
            score_diff_points = 100
        elif score_diff >= 2:
            score_diff_points = 80
        elif score_diff >= 1:
            score_diff_points = 60
        elif score_diff >= 0:
            score_diff_points = 40
        else:
            score_diff_points = 0

        # RSI超卖程度 (15%)
        rsi_weight = 0.15
        if rsi <= 30:
            rsi_points = 100
        elif rsi <= 40:
            rsi_points = 80
        elif rsi <= 50:
            rsi_points = 60
        elif rsi <= 60:
            rsi_points = 40
        else:
            rsi_points = 20

        # 成交量 (10%)
        volume_weight = 0.10
        if volume_ratio >= 2.0:
            volume_points = 100
        elif volume_ratio >= 1.5:
            volume_points = 80
        elif volume_ratio >= 1.0:
            volume_points = 60
        else:
            volume_points = 40

        # 大盘趋势 (10%)
        market_weight = 0.10
        market_avg = (btc_trend + eth_trend) / 2
        if market_avg >= 7:
            market_points = 100
        elif market_avg >= 5:
            market_points = 70
        elif market_avg >= 3:
            market_points = 40
        else:
            market_points = 20

        # 资金流向 (10%)
        flow_weight = 0.10
        if capital_flow_score >= 7:
            flow_points = 100
        elif capital_flow_score >= 5:
            flow_points = 70
        elif capital_flow_score >= 3:
            flow_points = 40
        else:
            flow_points = 20

        # 加权计算总分
        total_score = (
            trend_points * trend_weight +
            score_diff_points * score_diff_weight +
            rsi_points * rsi_weight +
            volume_points * volume_weight +
            market_points * market_weight +
            flow_points * flow_weight
        )

        return total_score

    def _calculate_short_probability_score(
        self,
        trend_score: int,
        bullish_score: int,
        bearish_score: int,
        rsi: float,
        volume_ratio: float,
        btc_trend: int,
        eth_trend: int,
        capital_flow_score: int
    ) -> float:
        """
        计算做空盈利概率评分 (0-100)
        综合多个因子评估做空的盈利概率
        """
        # 趋势评分 (30%) - 低分做空优势
        trend_weight = 0.30
        if trend_score <= 3:
            trend_points = 100
        elif trend_score <= 4:
            trend_points = 80
        elif trend_score <= 5:
            trend_points = 50
        else:
            trend_points = 10

        # 看跌评分优势 (25%)
        score_diff_weight = 0.25
        score_diff = bearish_score - bullish_score
        if score_diff >= 3:
            score_diff_points = 100
        elif score_diff >= 2:
            score_diff_points = 80
        elif score_diff >= 1:
            score_diff_points = 60
        elif score_diff >= 0:
            score_diff_points = 40
        else:
            score_diff_points = 0

        # RSI超买程度 (15%)
        rsi_weight = 0.15
        if rsi >= 70:
            rsi_points = 100
        elif rsi >= 60:
            rsi_points = 80
        elif rsi >= 50:
            rsi_points = 60
        elif rsi >= 40:
            rsi_points = 40
        else:
            rsi_points = 20

        # 成交量 (10%)
        volume_weight = 0.10
        if volume_ratio >= 2.0:
            volume_points = 100
        elif volume_ratio >= 1.5:
            volume_points = 80
        elif volume_ratio >= 1.0:
            volume_points = 60
        else:
            volume_points = 40

        # 大盘趋势 (10%) - 弱势做空优势
        market_weight = 0.10
        market_avg = (btc_trend + eth_trend) / 2
        if market_avg <= 3:
            market_points = 100
        elif market_avg <= 4:
            market_points = 80
        elif market_avg <= 5:
            market_points = 50
        else:
            market_points = 20

        # 资金流向 (10%) - 流出做空优势
        flow_weight = 0.10
        if capital_flow_score <= 3:
            flow_points = 100
        elif capital_flow_score <= 5:
            flow_points = 70
        elif capital_flow_score <= 7:
            flow_points = 40
        else:
            flow_points = 20

        # 加权计算总分
        total_score = (
            trend_points * trend_weight +
            score_diff_points * score_diff_weight +
            rsi_points * rsi_weight +
            volume_points * volume_weight +
            market_points * market_weight +
            flow_points * flow_weight
        )

        return total_score

    def _decide_trade_direction(
        self,
        trend_score: int,
        bullish_score: int,
        bearish_score: int,
        rsi: float,
        volume_ratio: float,
        btc_trend: int,
        eth_trend: int,
        capital_flow_score: int,
        min_score_threshold: float = 60.0,
        score_diff_threshold: float = 15.0
    ) -> Dict[str, Any]:
        """
        决定交易方向
        返回: {"direction": "long"/"short"/"none", "long_score": float, "short_score": float, "reason": str}
        """
        long_score = self._calculate_long_probability_score(
            trend_score, bullish_score, bearish_score, rsi, volume_ratio,
            btc_trend, eth_trend, capital_flow_score
        )

        short_score = self._calculate_short_probability_score(
            trend_score, bullish_score, bearish_score, rsi, volume_ratio,
            btc_trend, eth_trend, capital_flow_score
        )

        result = {
            "long_score": round(long_score, 1),
            "short_score": round(short_score, 1),
            "direction": "none",
            "reason": ""
        }

        # 判断逻辑
        if long_score >= min_score_threshold and long_score > short_score + score_diff_threshold:
            result["direction"] = "long"
            result["reason"] = f"做多评分{long_score:.1f} > 做空评分{short_score:.1f}，且超过阈值{min_score_threshold}"
        elif short_score >= min_score_threshold and short_score > long_score + score_diff_threshold:
            result["direction"] = "short"
            result["reason"] = f"做空评分{short_score:.1f} > 做多评分{long_score:.1f}，且超过阈值{min_score_threshold}"
        else:
            result["reason"] = f"多空评分接近(多{long_score:.1f}/空{short_score:.1f})或未达到阈值{min_score_threshold}，观望"

        return result

    async def generate_signals(self, opportunities: List[Dict], dry_run: bool = True) -> List[TradingSignal]:
        signals = []

        # 分别处理买入和做空信号
        buy_opportunities = [o for o in opportunities if o.get("can_buy")]
        short_opportunities = [o for o in opportunities if o.get("can_short")] if self.config.enable_short else []

        # 获取实际持仓数（分别获取多单和空单）
        if dry_run:
            current_long_positions = len(simulation_manager.get_positions())
            current_short_positions = len(simulation_manager.get_short_positions())
        else:
            # 实盘模式需要从 API 获取持仓数
            current_long_positions = 0  # TODO: 实现实盘持仓查询
            current_short_positions = 0  # TODO: 实现实盘持仓查询

        logger.info("")
        logger.info("=" * 60)
        logger.info("🎯 本次分析 {} 个币种".format(len(buy_opportunities) + len(short_opportunities)))
        logger.info(f"   买入信号: {len(buy_opportunities)} 个, 做空信号: {len(short_opportunities)} 个")
        logger.info(f"   多单持仓: {current_long_positions}/{self.config.long_max_positions} 个, 空单持仓: {current_short_positions}/{self.config.short_max_positions} 个")
        logger.info("=" * 60)
        self._log(f"🎯 本次分析 {len(buy_opportunities)} 个买入信号, {len(short_opportunities)} 个做空信号")
        self._log(f"   多单持仓: {current_long_positions}/{self.config.long_max_positions} 个, 空单持仓: {current_short_positions}/{self.config.short_max_positions} 个")

        if dry_run:
            sim_stats = simulation_manager.get_stats()
            available_usdt = sim_stats.get("available_balance", 1000.0)
            total_equity = sim_stats.get("initial_balance", 1000.0)
            logger.info(f"  💰 模拟账户余额: ${available_usdt:.2f}")
            self._log(f"  💰 模拟账户余额: ${available_usdt:.2f}")
        else:
            account_info = await self._get_account_info(dry_run=False)
            available_usdt = account_info['available_usdt'] if account_info else 0
            total_equity = account_info['total_equity'] if account_info else 0
        
        btc_trend = 5
        eth_trend = 5
        try:
            async with OKXClient() as client:
                market_env = await check_market_environment(client)
                btc_trend = market_env.btc_score
                eth_trend = market_env.eth_score
        except:
            pass

        # 计算剩余可开仓位
        remaining_long_slots = max(0, self.config.long_max_positions - current_long_positions)
        remaining_short_slots = max(0, self.config.short_max_positions - current_short_positions)

        logger.info(f"   剩余可开: 多单 {remaining_long_slots} 个, 空单 {remaining_short_slots} 个")
        self._log(f"   剩余可开: 多单 {remaining_long_slots} 个, 空单 {remaining_short_slots} 个")

        # 处理买入信号（根据剩余仓位限制）
        for opp in buy_opportunities[:remaining_long_slots]:
            coin = opp["coin"]
            logger.info("")
            logger.info(f"--- 分析 {coin} (候选) ---")
            logger.info(f"  📡 {coin}-USDT 实时价格: ${opp['price']:.4f} (OKX时间: {datetime.now().strftime('%H:%M:%S')})")
            self._log(f"--- 分析 {coin} (候选) ---")
            self._log(f"  📡 {coin}-USDT 实时价格: ${opp['price']:.4f}")
            
            logger.info("")
            logger.info(f"🤖 AI分析 {coin}...")
            logger.info(f"  当前价格: ${opp['price']:.4f}")
            logger.info(f"  趋势评分: {opp['trend_score']}/10 ({'看涨' if opp['trend_score'] >= 7 else '横盘' if opp['trend_score'] >= 5 else '看跌'})")
            self._log(f"🤖 AI分析 {coin}...")
            self._log(f"  当前价格: ${opp['price']:.4f}")
            self._log(f"  趋势评分: {opp['trend_score']}/10 ({'看涨' if opp['trend_score'] >= 7 else '横盘' if opp['trend_score'] >= 5 else '看跌'})")
            
            try:
                from app.services.sentiment_service import sentiment_service
                from app.services.external_data_service import ExternalDataService
                news_sentiment = await sentiment_service.get_news_sentiment(coin)
                if news_sentiment and news_sentiment.get("news_count", 0) > 0:
                    logger.info("")
                    logger.info(f"📰 {coin} 新闻情绪报告:")
                    logger.info(f"  相关新闻: {news_sentiment.get('news_count', 0)}条")
                    logger.info(f"  情绪评分: {news_sentiment.get('score', 5)}/10")
                    logger.info(f"  看涨: {news_sentiment.get('bullish_count', 0)}条 | 看跌: {news_sentiment.get('bearish_count', 0)}条")
                    recent_news = news_sentiment.get("recent_news", [])[:3]
                    if recent_news:
                        logger.info(f"  最新新闻:")
                        for i, news in enumerate(recent_news, 1):
                            logger.info(f"    {i}. {news.get('title', 'N/A')[:50]}...")
                    self._log(f"📰 {coin} 新闻情绪: {news_sentiment.get('score', 5)}/10")
                    
                    current_score = opp['trend_score']
                    news_score = news_sentiment.get('score', 5)
                    combined_score = round(current_score * self.config.sentiment_trend_weight + news_score * self.config.sentiment_news_weight)
                    logger.info(f"  🔄 融合新闻情绪: 当前{current_score} + 新闻{news_score} → 综合{combined_score}/10")
                    self._log(f"  🔄 融合新闻情绪: 综合{combined_score}/10")
                else:
                    try:
                        ext_service = ExternalDataService()
                        ext_report = await ext_service.get_coin_sentiment(coin)
                        if ext_report and ext_report.overall_score:
                            logger.info(f"  📰 使用备用情绪数据源: RSS+LunarCrush")
                            logger.info(f"  情绪评分: {ext_report.overall_score}/10")
                            self._log(f"📰 {coin} 备用情绪: {ext_report.overall_score}/10")
                        else:
                            logger.info(f"  ⚠️ CoinGecko服务不可用，使用默认情绪评分")
                            self._log(f"  ⚠️ CoinGecko服务不可用，使用默认评分")
                    except Exception as ext_e:
                        logger.info(f"  ⚠️ CoinGecko服务不可用，备用数据源也失败: {str(ext_e)[:30]}")
                        self._log(f"  ⚠️ 情绪服务不可用")
            except Exception as e:
                logger.info(f"  ⚠️ 情绪服务不可用: {str(e)[:30]}")
                self._log(f"  ⚠️ 情绪服务不可用")
            
            resonance = opp.get("resonance_details")
            if resonance:
                logger.info(f"  共振评分: {resonance.total_score:.1f}/10")
                logger.info(f"    - 趋势分: {resonance.trend_score}")
                logger.info(f"    - 资金流向分: {resonance.capital_flow_score}")
                logger.info(f"    - 市场环境分: {resonance.market_env_score}")
                self._log(f"  共振评分: {resonance.total_score:.1f}/10")
            
            # 显示实际持仓信息
            if dry_run:
                current_positions_data = simulation_manager.get_positions()
                total_position_value = sum(pos["usdt_value"] for pos in current_positions_data)
                logger.info(f"  当前持仓: ${total_position_value:.2f} ({len(current_positions_data)}个)")
                self._log(f"  当前持仓: ${total_position_value:.2f} ({len(current_positions_data)}个)")
            else:
                logger.info(f"  当前持仓: {current_long_positions}个")
                self._log(f"  当前持仓: {current_long_positions}个")

            # 动态波段计算（v4.2 新增）
            # 计算波动率（基于24h涨跌幅）
            volatility = abs(opp['change_24h'])
            turnover_24h = opp.get('turnover_24h', 0)

            # 检查是否启用动态波段
            if self.config.dynamic_bands_enabled:
                dynamic_bands = self._calculate_dynamic_bands(
                    coin,
                    opp['change_24h'],
                    volatility,
                    turnover_24h,
                    opp['trend_score']
                )
                dynamic_stop_loss = dynamic_bands['stop_loss']
                dynamic_take_profit = dynamic_bands['take_profit']
            else:
                # 使用固定止损止盈
                dynamic_stop_loss = -self.config.stop_loss_percent
                dynamic_take_profit = self.config.take_profit_percent
                logger.info(f"  📊 {coin} 使用固定波段: 止损{dynamic_stop_loss}%, 止盈{dynamic_take_profit}%")

            self._log(f"  📊 {coin} 动态波段计算:")
            self._log(f"     动态止损: {dynamic_stop_loss:.2f}%, 动态止盈: {dynamic_take_profit:.2f}%")

            # 智能止损：根据趋势评分调整止损
            if opp['trend_score'] >= 9:
                logger.info(f"  🛡️ 智能止损：趋势评分{opp['trend_score']}/10，放宽止损至-3%")
                self._log(f"  🛡️ 智能止损：趋势评分{opp['trend_score']}/10，放宽止损至-3%")
            elif opp['trend_score'] >= 7:
                logger.info(f"  🛡️ 智能止损：趋势评分{opp['trend_score']}/10，止损-2%")
                self._log(f"  🛡️ 智能止损：趋势评分{opp['trend_score']}/10，止损-2%")
            else:
                logger.info(f"  🛡️ 智能止损：趋势评分{opp['trend_score']}/10，使用动态止损{dynamic_stop_loss:.2f}%")
            
            logger.info(f"  🔍 买入检查: 黑名单=false, 持仓=0.0%, 现金=100.0%, 冷却期=OK, 近期买入=false")
            
            sentiment_score = opp.get("sentiment_score", opp.get("trend_score", 5))
            
            # 舆情综合验证：评分≥8但24h跌>5%则降分
            change_24h = opp.get("change_24h", 0)
            if (self.config.sentiment_consistency_check_enabled and 
                sentiment_score >= self.config.sentiment_high_score_threshold and 
                change_24h < self.config.price_drop_threshold):
                original_score = sentiment_score
                sentiment_score = max(1, sentiment_score + self.config.sentiment_adjustment)
                logger.info(f"  ⚠️ 舆情数据不一致：评分{original_score}分但24h涨跌{change_24h:.2f}%，趋势评分已调整至{sentiment_score}/10")
                self._log(f"  ⚠️ 舆情数据不一致，评分从{original_score}调整至{sentiment_score}")
            
            if self.config.sentiment_trigger_enabled and sentiment_score < self.config.sentiment_threshold:
                logger.info(f"  📰 舆情门槛预筛选: {sentiment_score}/10 < {self.config.sentiment_threshold}，跳过共振分析")
                self._log(f"  📰 舆情门槛未达标: {sentiment_score}/10 < {self.config.sentiment_threshold}")
                logger.info(f"  决策: HOLD")
                logger.info(f"  原因: 舆情评分{sentiment_score}未达门槛{self.config.sentiment_threshold}")
                self._log(f"  决策: HOLD, 原因: 舆情评分未达门槛")
                continue
            
            logger.info(f"  📰 舆情门槛预筛选: {sentiment_score}/10 >= {self.config.sentiment_threshold}，进入共振分析")
            self._log(f"  📰 舆情门槛通过: {sentiment_score}/10")
            
            indicators = opp.get("indicators", {})
            rsi_value = indicators.get("rsi", 50.0)
            
            try:
                async with OKXClient() as tech_client:
                    candles_data = await tech_client.get_candles(f"{coin}-USDT", bar="5m", limit=50)
                    if candles_data and "data" in candles_data:
                        candles = candles_data["data"]
                        prices = [float(c[4]) for c in reversed(candles)]
                        tech_validation = validate_technical_indicators(
                            prices, opp["price"], sentiment_score,
                            self.config.long_rsi_max, 70.0
                        )
                        logger.info(f"  📊 技术指标: RSI={tech_validation.details.get('rsi', 'N/A')}, 评分={tech_validation.score}/10")
                        logger.info(f"     信号: {tech_validation.reason}")
                        if tech_validation.passed:
                            self._log(f"  📊 技术验证 ✅ 评分={tech_validation.score}/10")
                        else:
                            self._log(f"  📊 技术验证 ❌ {tech_validation.fail_reason}")
                        
                        if not tech_validation.passed:
                            logger.info(f"  ⏸️ 技术面未通过，{tech_validation.fail_reason}")
                            self._log(f"  决策: HOLD - 技术面未通过({tech_validation.fail_reason})")
                            continue
            except Exception as e:
                logger.info(f"  ⚠️ 技术面验证异常: {str(e)[:30]}")
            
            resonance = opp.get("resonance_details")
            volume_ratio = 1.0
            if resonance and hasattr(resonance, 'capital_flow_score'):
                try:
                    capital_flow = await check_capital_flow(client, coin)
                    volume_ratio = capital_flow.volume_ratio if hasattr(capital_flow, 'volume_ratio') else 1.0
                except:
                    volume_ratio = 1.0
            
            rsi_oversold = self.config.long_rsi_min <= rsi_value <= self.config.long_rsi_max
            volume_sufficient = volume_ratio > self.config.long_min_volume_ratio

            logger.info(f"  📊 RSI验证: {rsi_value:.1f} (区间{self.config.long_rsi_min}-{self.config.long_rsi_max}) {'✅超卖' if rsi_oversold else '❌未超卖'}")
            logger.info(f"  📊 成交量验证: {volume_ratio:.2f}x (阈值>{self.config.long_min_volume_ratio}) {'✅放量' if volume_sufficient else '❌未放量'}")
            self._log(f"  📊 RSI验证: {rsi_value:.1f} {'✅超卖' if rsi_oversold else '❌未超卖'}")
            self._log(f"  📊 成交量验证: {volume_ratio:.2f}x {'✅放量' if volume_sufficient else '❌未放量'}")
            
            market_ok = btc_trend >= self.config.dip_buy_min_btc_trend and eth_trend >= self.config.dip_buy_min_eth_trend
            
            if not opp["can_buy"]:
                bearish_reasons = []
                if not rsi_oversold:
                    bearish_reasons.append(f"RSI未超卖({rsi_value:.1f})")
                if not volume_sufficient:
                    bearish_reasons.append(f"成交量未放量({volume_ratio:.2f}x)")
                bearish_reasons.append("非连续阴线")
                
                dip_reasons = []
                if not market_ok:
                    dip_reasons.append(f"大盘弱BTC{btc_trend}/ETH{eth_trend}")
                if rsi_value >= self.config.dip_buy_rsi_threshold:
                    dip_reasons.append(f"RSI{rsi_value:.1f}>={self.config.dip_buy_rsi_threshold}")
                if volume_ratio < self.config.dip_buy_volume_multiplier:
                    dip_reasons.append(f"成交量{volume_ratio:.2f}x<{self.config.dip_buy_volume_multiplier}x")
                dip_reasons.append("价格位置不对")
                
                logger.info(f"  ⏭️ 阴线买入信号未通过: {', '.join(bearish_reasons)}")
                logger.info(f"  ⏭️ 抄底条件不满足: {', '.join(dip_reasons)}")
                logger.info(f"  🚫 {coin}不满足严格抄底条件，禁止买入")
                self._log(f"  ⏭️ 阴线买入信号未通过")
                self._log(f"  ⏭️ 抄底条件不满足")
                self._log(f"  🚫 {coin}不满足严格抄底条件，禁止买入")
                logger.info(f"  决策: HOLD")
                logger.info(f"  原因: {opp.get('reason', '条件不满足')}")
                self._log(f"  决策: HOLD, 原因: {opp.get('reason', '条件不满足')}")
                continue
            
            # 检查分层冷却期
            can_trade, cooldown_minutes = self._check_cooldown(opp["coin"], opp.get("trend_score", 5))
            if not can_trade:
                last_time = self.last_trade_time.get(coin)
                if last_time:
                    elapsed = (datetime.now(BEIJING_TZ) - last_time).total_seconds() / 60
                    remaining = int(cooldown_minutes - elapsed)
                    logger.info(f"  🔍 买入检查: 黑名单=false, 持仓=0.0%, 冷却期=等待{remaining}分钟, 近期买入=true")
                    logger.info(f"  ⏳ {coin} 冷却期中: 已过{elapsed:.1f}分钟 (趋势{opp.get('trend_score', 5)}分，冷却期{cooldown_minutes}分钟)")
                    self._log(f"  ⏳ {coin} 冷却期中: 已过{elapsed:.1f}分钟")
                    logger.info(f"  决策: HOLD")
                    logger.info(f"  原因: 冷却期中 (剩余{remaining}分钟)")
                    self._log(f"  决策: HOLD, 原因: 冷却期中")
                continue
            
            if not self._check_daily_limit():
                logger.info(f"  🚫 已达每日交易限制")
                self._log(f"  🚫 已达每日交易限制")
                logger.info(f"  决策: HOLD")
                logger.info(f"  原因: 每日限制")
                self._log(f"  决策: HOLD, 原因: 每日限制")
                break
            
            # 检查日交易量限制
            if not self._check_daily_volume_limit(self.config.trade_size):
                logger.info(f"  🚫 已达每日交易量限制")
                self._log(f"  🚫 已达每日交易量限制")
                logger.info(f"  决策: HOLD")
                logger.info(f"  原因: 每日交易量限制")
                self._log(f"  决策: HOLD, 原因: 每日交易量限制")
                break

            # 检查当前币种是否已持仓（用于金字塔加仓判断）
            existing_position = None
            if dry_run:
                for pos in simulation_manager.get_positions():
                    if pos["coin"] == coin:
                        existing_position = pos
                        break

            # 检查回调加仓条件：如果有减仓记录，需等价格回调到减仓价的97%以下
            can_buy_pullback, pullback_reason = self._check_pullback_buy_condition(coin, opp["price"])
            if not can_buy_pullback:
                logger.info(f"  ⏳ {coin} 回调加仓条件未满足: {pullback_reason}")
                self._log(f"  ⏳ {coin} 回调加仓条件未满足")
                logger.info(f"  决策: HOLD")
                logger.info(f"  原因: {pullback_reason}")
                self._log(f"  决策: HOLD, 原因: 回调加仓条件未满足")
                continue

            # 实时盈亏验证：如果已有持仓且亏损>1%，禁止买入（防止追高）
            pnl_check = self._check_realtime_pnl_for_buy(coin, existing_position, opp["price"])
            if not pnl_check["can_buy"]:
                logger.info(f"  ⚠️ {coin} 实时盈亏验证未通过: {pnl_check['reason']}")
                self._log(f"  ⚠️ {coin} 实时盈亏验证未通过")
                logger.info(f"  决策: HOLD")
                logger.info(f"  原因: {pnl_check['reason']}")
                self._log(f"  决策: HOLD, 原因: 实时盈亏验证未通过")
                continue

            # 检查是否可以金字塔加仓
            if existing_position and dry_run:
                # 检查连续加仓限制（根据趋势动态调整）
                can_add, reason = self._check_consecutive_add_limit(
                    coin, 
                    opp.get("trend_score", 5), 
                    existing_position.get("usdt_value", 0),
                    total_equity
                )
                if not can_add:
                    logger.info(f"  ⏸️ {coin} {reason}，跳过")
                    self._log(f"  ⏸️ {coin} {reason}，跳过")
                    logger.info(f"  决策: HOLD")
                    logger.info(f"  原因: {reason}")
                    self._log(f"  决策: HOLD, 原因: {reason}")
                    continue
                
                # 计算金字塔加仓条件 - 应用时区感知
                is_short_term = opp.get("signal_type") == "short_term"
                if is_short_term:
                    pyramid_base = self.config.short_term_trade_size
                else:
                    pyramid_base = self.config.trade_size
                
                # 获取时区比例
                if self.config.timezone_adjusted_position:
                    ratio_min, ratio_max, _, _ = self._get_timezone_position_size()
                    tz_ratio = (ratio_min, ratio_max)
                else:
                    tz_ratio = None
                
                pyramid_info = simulation_manager.calculate_pyramid_buy_amount(
                    coin, opp["price"], opp.get("sentiment_score", 5.0),
                    base_amount=pyramid_base, timezone_ratio=tz_ratio
                )
                if pyramid_info["should_add"]:
                    logger.info(f"  📈 {coin} 可金字塔加仓第{pyramid_info['layer']}层")
                    self._log(f"  📈 {coin} 可金字塔加仓第{pyramid_info['layer']}层")
                else:
                    logger.info(f"  ⏸️ {coin} 已持仓但{pyramid_info['reason']}，跳过")
                    self._log(f"  ⏸️ {coin} 已持仓但{pyramid_info['reason']}，跳过")
                    logger.info(f"  决策: HOLD")
                    logger.info(f"  原因: {pyramid_info['reason']}")
                    self._log(f"  决策: HOLD, 原因: {pyramid_info['reason']}")
                    continue
            elif existing_position and not dry_run:
                # 实盘模式，已有持仓时跳过
                logger.info(f"  ⚠️ {coin} 已持仓，跳过")
                self._log(f"  ⚠️ {coin} 已持仓，跳过")
                continue

            # 检查多单持仓数量限制
            if current_long_positions >= self.config.long_max_positions:
                logger.info(f"  🚫 已达最大多单持仓数 {current_long_positions}/{self.config.long_max_positions}")
                self._log(f"  🚫 已达最大多单持仓数 {current_long_positions}/{self.config.long_max_positions}")
                logger.info(f"  决策: HOLD")
                logger.info(f"  原因: 多单持仓数量已达上限")
                self._log(f"  决策: HOLD, 原因: 多单持仓数量已达上限")
                continue

            if available_usdt < self.config.trade_size:
                logger.info(f"  可用USDT: ${available_usdt:.2f}")
                self._log(f"  可用USDT: ${available_usdt:.2f}")
                logger.info(f"  决策: HOLD")
                logger.info(f"  原因: USDT不足")
                self._log(f"  决策: HOLD, 原因: USDT不足")
                continue

            # 决定是新开仓还是金字塔加仓
            if existing_position and dry_run:
                # 金字塔加仓 - 应用时区感知
                is_short_term = opp.get("signal_type") == "short_term"
                if is_short_term:
                    pyramid_base = self.config.short_term_trade_size
                    strategy_name = "短线策略"
                else:
                    pyramid_base = self.config.trade_size
                    strategy_name = "普通策略"
                
                # 获取时区比例
                if self.config.timezone_adjusted_position:
                    ratio_min, ratio_max, _, _ = self._get_timezone_position_size()
                    tz_ratio = (ratio_min, ratio_max)
                else:
                    tz_ratio = None
                
                pyramid_info = simulation_manager.calculate_pyramid_buy_amount(
                    coin, opp["price"], opp.get("sentiment_score", 5.0),
                    base_amount=pyramid_base, timezone_ratio=tz_ratio
                )
                if pyramid_info["should_add"]:
                    final_amount = pyramid_info["amount"]
                    layer = pyramid_info["layer"]
                    if tz_ratio:
                        logger.info(f"  📊 金字塔加仓[{strategy_name}]: 第{layer}层, 金额${final_amount:.2f} (时区感知)")
                        self._log(f"  📊 金字塔加仓[{strategy_name}]: 第{layer}层, 金额${final_amount:.2f}")
                    else:
                        logger.info(f"  📊 金字塔加仓[{strategy_name}]: 第{layer}层, 金额${final_amount:.2f}")
                        self._log(f"  📊 金字塔加仓[{strategy_name}]: 第{layer}层, 金额${final_amount:.2f}")
                else:
                    continue
            else:
                # 确定策略类型并选择基础金额
                is_short_term = opp.get("signal_type") == "short_term"
                if is_short_term:
                    base_amount = self.config.short_term_trade_size
                    strategy_name = "短线策略"
                else:
                    base_amount = self.config.trade_size
                    strategy_name = "普通策略"
                
                buy_amount = base_amount * self.config.long_position_ratio
                final_amount = buy_amount

                # 应用买入金额递减（同一币种多次买入金额递减）
                final_amount = self._calculate_decreasing_trade_size(coin, final_amount)

                # 应用时区感知调整仓位大小（比例范围随机）
                if self.config.timezone_adjusted_position:
                    ratio_min, ratio_max, _, _ = self._get_timezone_position_size()
                    # 计算范围内的实际金额
                    range_min = round(base_amount * ratio_min, 2)
                    range_max = round(base_amount * ratio_max, 2)
                    # 新仓用较低比例，加仓（金字塔）用较高比例
                    # 范围内随机选择
                    final_amount = round(random.uniform(range_min, range_max), 2)
                    logger.info(f"  🌐 时区感知[{strategy_name}]: 基础${base_amount}, 比例{ratio_min*100:.0f}%-{ratio_max*100:.0f}%, 范围${range_min}-${range_max}, 随机${final_amount}")

                logger.info(f"  📊 新开仓金额: ${final_amount:.2f}")
                self._log(f"  📊 新开仓金额: ${final_amount:.2f}")

            # 余额保护：保留至少 30% 的可用资金
            min_reserve = total_equity * (self.config.min_cash_reserve / 100.0)
            if available_usdt - final_amount < min_reserve:
                logger.info(f"  ⚠️ 余额保护: 买入${final_amount:.2f}后剩余${available_usdt - final_amount:.2f} < 保留${min_reserve:.2f}")
                self._log(f"  ⚠️ 余额保护: 买入${final_amount:.2f}后剩余${available_usdt - final_amount:.2f} < 保留${min_reserve:.2f}")
                logger.info(f"  决策: HOLD")
                logger.info(f"  原因: 需要保留${min_reserve:.2f}可用资金")
                self._log(f"  决策: HOLD, 原因: 需要保留${min_reserve:.2f}可用资金")
                continue

            cash_percent = (available_usdt / total_equity * 100) if total_equity > 0 else 0
            logger.info(f"  🔍 买入检查: 黑名单=false, 持仓={current_long_positions}个, 现金={cash_percent:.1f}%, 冷却期=OK, 近期买入=false")
            logger.info(f"  ✅ {coin} 满足买入条件，生成信号")
            self._log(f"  ✅ {coin} 满足买入条件，生成信号")
            logger.info(f"  决策: BUY")
            logger.info(f"  原因: {opp['reason']}")
            self._log(f"  决策: BUY, 原因: {opp['reason']}")

            # 生成买入信号
            signal = TradingSignal(
                coin=opp["coin"],
                action="buy",
                price=opp["price"],
                amount=final_amount,
                reason=opp["reason"],
                trend_score=opp.get("trend_score", 5.0),
                resonance_score=opp.get("resonance_score", 0),
                signal_type=opp.get("signal_type", "buy"),
                timestamp=datetime.now(),
                strategy=opp.get("strategy", "短线策略")
            )
            signals.append(signal)
            
            # 更新持仓计数（防止超过限制）
            current_long_positions += 1

        # 生成做空信号
        logger.info("")
        logger.info(f"--- 分析做空机会 ---")
        self._log(f"--- 分析做空机会 ---")

        for short_opp in short_opportunities[:remaining_short_slots]:
            coin = short_opp["coin"]
            logger.info("")
            logger.info(f"--- 分析 {coin} (做空候选) ---")
            logger.info(f"  📡 {coin}-USDT 实时价格: ${short_opp['price']:.4f} (OKX时间: {datetime.now().strftime('%H:%M:%S')})")
            self._log(f"--- 分析 {coin} (做空候选) ---")
            self._log(f"  📡 {coin}-USDT 实时价格: ${short_opp['price']:.4f}")

            # 检查当前币种是否已有空单持仓
            existing_short_position = None
            if dry_run:
                for short_pos in simulation_manager.get_short_positions():
                    if short_pos["coin"] == coin:
                        existing_short_position = short_pos
                        break

            # 获取指标数据
            indicators = short_opp.get("indicators", {})
            rsi_value = indicators.get("rsi", 50.0)
            resonance = short_opp.get("resonance_details")
            volume_ratio = 1.0
            if resonance and hasattr(resonance, 'capital_flow_score'):
                try:
                    async with OKXClient() as client:
                        capital_flow = await check_capital_flow(client, coin)
                        volume_ratio = capital_flow.volume_ratio if hasattr(capital_flow, 'volume_ratio') else 1.0
                except:
                    volume_ratio = 1.0

            sentiment_score = short_opp.get("sentiment_score", 5)
            bearish_score = short_opp.get("bearish_score", 5)

            logger.info("")
            logger.info(f"🤖 AI分析 {coin} 做空机会...")
            logger.info(f"  当前价格: ${short_opp['price']:.4f}")
            logger.info(f"  看跌评分: {bearish_score}/10 ({'看跌' if bearish_score >= 7 else '非看跌'})")
            logger.info(f"  24h涨跌: {short_opp.get('change_24h', 0):.2f}%")
            self._log(f"🤖 AI分析 {coin} 做空机会...")
            self._log(f"  当前价格: ${short_opp['price']:.4f}")
            self._log(f"  看跌评分: {bearish_score}/10")

            trend_score = short_opp.get("trend_score", 5)

            # 使用扫描阶段的short_reason作为检查说明
            short_reason = short_opp.get("short_reason", "")
            logger.info(f"  📊 做空条件: {short_reason}")
            self._log(f"  📊 做空检查: RSI{rsi_value:.1f}, 成交量{volume_ratio:.2f}x")

            # 检查做空分层冷却期
            can_short, cooldown_minutes = self._check_short_cooldown(coin, bearish_score)
            if not can_short:
                last_time = self.last_trade_time.get(f"short_{coin}")
                if last_time:
                    elapsed = (datetime.now(BEIJING_TZ) - last_time).total_seconds() / 60
                    remaining = int(cooldown_minutes - elapsed)
                    logger.info(f"  🔍 做空检查: 看跌评分{bearish_score}, 冷却期=等待{remaining}分钟")
                    logger.info(f"  ⏳ {coin} 做空冷却期中: 已过{elapsed:.1f}分钟 (看跌{bearish_score}分，冷却期{cooldown_minutes}分钟)")
                    self._log(f"  ⏳ {coin} 做空冷却期中")
                    logger.info(f"  决策: HOLD")
                    logger.info(f"  原因: 冷却期中 (剩余{remaining}分钟)")
                    self._log(f"  决策: HOLD, 原因: 冷却期中")
                continue

            # 检查反弹加空条件
            pullback_check = self._check_short_rally_condition(coin, short_opp["price"])
            if not pullback_check["can_short"]:
                logger.info(f"  ⏳ {coin} 反弹加空条件未满足: {pullback_check['reason']}")
                self._log(f"  ⏳ {coin} 反弹加空条件未满足")
                logger.info(f"  决策: HOLD")
                logger.info(f"  原因: {pullback_check['reason']}")
                self._log(f"  决策: HOLD, 原因: 反弹加空条件未满足")
                continue

            # 实时盈亏验证
            pnl_check = self._check_realtime_pnl_for_short(coin, existing_short_position, short_opp["price"])
            if not pnl_check["can_short"]:
                logger.info(f"  ⚠️ {coin} 空单实时盈亏验证未通过: {pnl_check['reason']}")
                self._log(f"  ⚠️ {coin} 空单实时盈亏验证未通过")
                logger.info(f"  决策: HOLD")
                logger.info(f"  原因: {pnl_check['reason']}")
                self._log(f"  决策: HOLD, 原因: 实时盈亏验证未通过")
                continue

            # 检查是否已有空单持仓
            if existing_short_position:
                logger.info(f"  ⚠️ {coin} 已有空单持仓，跳过")
                self._log(f"  ⚠️ {coin} 已有空单持仓，跳过")
                logger.info(f"  决策: HOLD")
                logger.info(f"  原因: 已有空单持仓")
                self._log(f"  决策: HOLD, 原因: 已有空单持仓")
                continue

            # 检查做空持仓数量限制
            if current_short_positions >= self.config.short_max_positions:
                # 超仓检查：是否在豁免期内
                if self.config.short_over_position_exemption_enabled:
                    unrealized_pnl = -5.0
                    if self._is_in_short_exemption_period(coin, unrealized_pnl):
                        logger.info(f"  ✅ {coin} 在空单超仓豁免期内，允许开空单")
                    else:
                        logger.info(f"  🚫 已达最大空单持仓数 {current_short_positions}/{self.config.short_max_positions}")
                        self._log(f"  🚫 已达最大空单持仓数")
                        logger.info(f"  决策: HOLD")
                        logger.info(f"  原因: 空单持仓数量已达上限")
                        self._log(f"  决策: HOLD, 原因: 空单持仓数量已达上限")
                        continue
                else:
                    logger.info(f"  🚫 已达最大空单持仓数 {current_short_positions}/{self.config.short_max_positions}")
                    self._log(f"  🚫 已达最大空单持仓数")
                    logger.info(f"  决策: HOLD")
                    logger.info(f"  原因: 空单持仓数量已达上限")
                    self._log(f"  决策: HOLD, 原因: 空单持仓数量已达上限")
                    continue

            # 检查资金充足
            if available_usdt < self.config.trade_size * self.config.short_position_ratio:
                logger.info(f"  可用USDT: ${available_usdt:.2f}")
                self._log(f"  可用USDT: ${available_usdt:.2f}")
                logger.info(f"  决策: HOLD")
                logger.info(f"  原因: USDT不足")
                self._log(f"  决策: HOLD, 原因: USDT不足")
                continue

            # 确定做空策略类型并选择基础金额
            is_short_term_short = short_opp.get("signal_type") == "short_term"
            if is_short_term_short:
                base_short_amount = self.config.short_term_trade_size * self.config.short_position_ratio
                strategy_name = "短线策略"
            else:
                base_short_amount = self.config.short_position_size * self.config.short_position_ratio
                strategy_name = "普通策略"

            short_amount = self._calculate_short_decreasing_amount(coin, base_short_amount)

            # 应用时区感知调整仓位大小（比例范围随机）
            if self.config.timezone_adjusted_position:
                ratio_min, ratio_max, _, _ = self._get_timezone_position_size()
                range_min = round(base_short_amount * ratio_min, 2)
                range_max = round(base_short_amount * ratio_max, 2)
                short_amount = round(random.uniform(range_min, range_max), 2)
                logger.info(f"  🌐 时区感知做空[{strategy_name}]: 基础${base_short_amount:.2f}, 比例{ratio_min*100:.0f}%-{ratio_max*100:.0f}%, 随机${short_amount:.2f}")

            # 余额保护
            min_reserve = total_equity * (self.config.short_min_cash_reserve / 100.0)
            if available_usdt - short_amount < min_reserve:
                logger.info(f"  ⚠️ 余额保护: 做空${short_amount:.2f}后剩余${available_usdt - short_amount:.2f} < 保留${min_reserve:.2f}")
                self._log(f"  ⚠️ 余额保护: 做空金额不足")
                logger.info(f"  决策: HOLD")
                logger.info(f"  原因: 需要保留${min_reserve:.2f}可用资金")
                self._log(f"  决策: HOLD, 原因: 需要保留可用资金")
                continue

            logger.info(f"  🔍 做空检查: 趋势看跌, 冷却期=OK, 近期做空=false")
            logger.info(f"  ✅ {coin} 满足做空条件，生成信号")
            self._log(f"  ✅ {coin} 满足做空条件，生成信号")
            logger.info(f"  决策: SELL_SHORT")
            logger.info(f"  原因: {short_reason}")
            self._log(f"  决策: SELL_SHORT, 原因: {short_reason}")

            short_signal = TradingSignal(
                coin=coin,
                action="sell_short",
                price=short_opp["price"],
                amount=short_amount,
                reason=short_reason,
                trend_score=short_opp["trend_score"],
                resonance_score=short_opp["resonance_score"],
                signal_type="short",
                timestamp=datetime.now(),
                strategy=short_opp.get("strategy", "短线做空")
            )
            signals.append(short_signal)
            
            # 更新空单持仓计数（防止超过限制）
            current_short_positions += 1
            
            logger.info(f"  ✅ 生成做空信号: {coin}")
            self._log(f"  ✅ 生成做空信号: {coin}")

        return signals
    
    async def execute_signal(self, signal: TradingSignal, dry_run: bool = True) -> Dict:
        result = {
            "signal": signal,
            "executed": False,
            "order_id": None,
            "error": None
        }

        signal_type_map = {"buy": SignalType.BUY, "sell": SignalType.SELL, "short": SignalType.SHORT, "cover": SignalType.COVER}
        dedup_signal_type = signal_type_map.get(signal.action, SignalType.BUY)

        dedup_result = signal_dedup.check_signal(signal.coin, dedup_signal_type)
        if not dedup_result.allowed:
            logger.warning(f"🚫 信号被拦截 [{signal.coin}]: {dedup_result.reason}")
            result["error"] = dedup_result.reason
            result["blocked_by_dedup"] = True
            result["dedup_status"] = dedup_result.status.value
            return result

        signal_dedup.set_pending(signal.coin)

        logger.info("")
        logger.info(f"🤖 AI分析 {signal.coin}...")
        logger.info(f"  当前价格: ${signal.price:.4f}")
        logger.info(f"  趋势评分: {signal.trend_score}/10 ({'看涨' if signal.trend_score >= 7 else '横盘' if signal.trend_score >= 5 else '看跌'})")
        logger.info(f"  共振评分: {signal.resonance_score:.1f}/10")
        logger.info(f"  信号类型: {signal.signal_type}")
        logger.info(f"  原因: {signal.reason}")
        
        self._log(f"🤖 AI分析 {signal.coin}...")
        self._log(f"  当前价格: ${signal.price:.4f}")
        self._log(f"  趋势评分: {signal.trend_score}/10")
        self._log(f"  共振评分: {signal.resonance_score:.1f}/10")
        
        logger.info(f"  📊 {signal.coin} 动态波段计算:")
        logger.info(f"     波动率: 待计算, 24h涨跌: 待计算")

        # 根据信号类型使用不同的止损止盈参数
        if signal.action == "buy":
            stop_loss = -self.config.long_stop_loss_percent
            take_profit = self.config.long_take_profit_percent
        else:
            stop_loss = self.config.short_stop_loss_percent
            take_profit = -self.config.short_take_profit_percent

        logger.info(f"     动态止损: {stop_loss}%, 动态止盈: {take_profit}%")

        if dry_run:
            action_text = "买入" if signal.action == "buy" else "做空"
            logger.info(f"  🔍 {action_text}检查: 黑名单=false, 冷却期=OK, 近期{action_text}=false")
            logger.info(f"  决策: {signal.action.upper()} (模拟)")
            logger.info(f"  原因: {signal.reason}")
            logger.info(f"[模拟] 执行信号: {signal.action} {signal.coin} ${signal.amount} @ {signal.price}")

            self._log(f"  决策: {signal.action.upper()} (模拟)")
            self._log(f"  原因: {signal.reason}")

            if signal.action == "buy":
                # 检查是否是金字塔加仓
                existing_position = None
                for pos in simulation_manager.get_positions():
                    if pos["coin"] == signal.coin:
                        existing_position = pos
                        break

                if existing_position and ("金字塔" in signal.reason or "止损拦截" in signal.reason):
                    # 执行金字塔加仓（包括止损拦截加仓）- 应用时区感知
                    is_short_term = signal.signal_type == "short_term"
                    if is_short_term:
                        pyramid_base = self.config.short_term_trade_size
                    else:
                        pyramid_base = self.config.trade_size
                    
                    # 获取时区比例
                    if self.config.timezone_adjusted_position:
                        ratio_min, ratio_max, _, _ = self._get_timezone_position_size()
                        tz_ratio = (ratio_min, ratio_max)
                    else:
                        tz_ratio = None
                    
                    pyramid_info = simulation_manager.calculate_pyramid_buy_amount(
                        signal.coin, signal.price, signal.trend_score,
                        base_amount=pyramid_base, timezone_ratio=tz_ratio
                    )
                    if pyramid_info["should_add"]:
                        simulation_manager.pyramid_add(
                            coin=signal.coin,
                            price=signal.price,
                            usdt_value=pyramid_info["amount"],  # 使用计算出的加仓金额
                            layer=pyramid_info["layer"],
                            reason=signal.reason
                        )
                        logger.info(f"[模拟] 金字塔加仓成功: {signal.coin} 第{pyramid_info['layer']}层 ${pyramid_info['amount']} @ {signal.price}")
                        self._log(f"[模拟] 金字塔加仓成功: {signal.coin} 第{pyramid_info['layer']}层 ${pyramid_info['amount']} @ {signal.price}")
                        # 飞书通知
                        await feishu_notifier.notify_trade("pyramid_buy", signal.coin, signal.price, pyramid_info["amount"] / signal.price, 0, f"金字塔加仓第{pyramid_info['layer']}层", is_swap=self.config.use_swap, leverage=float(self.config.long_leverage) if self.config.use_swap else 1.0, total_value=pyramid_info["amount"])
                    else:
                        logger.warning(f"[模拟] 金字塔加仓条件不满足: {pyramid_info['reason']}")
                else:
                    # 新开仓
                    simulation_manager.buy(
                        coin=signal.coin,
                        price=signal.price,
                        usdt_value=signal.amount,
                        stop_loss_percent=stop_loss,
                        take_profit_percent=take_profit,
                        reason=signal.reason,
                        leverage=float(self.config.long_leverage) if self.config.use_swap else 1.0,
                        strategy=signal.strategy,
                        is_swap=self.config.use_swap
                    )
                    # 记录持仓入场时间（模拟模式）
                    self.position_entry_times[signal.coin] = datetime.now(BEIJING_TZ)
                    # 记录交易时间（用于计数）
                    self._record_trade_time(signal.coin)
                    logger.info(f"[模拟] 买入成功: {signal.coin} ${signal.amount} @ {signal.price}")
                    self._log(f"[模拟] 买入成功: {signal.coin} ${signal.amount} @ {signal.price}")
                    # 飞书通知
                    try:
                        notify_result = await feishu_notifier.notify_trade("buy", signal.coin, signal.price, signal.amount / signal.price, 0, signal.reason, is_swap=self.config.use_swap, leverage=float(self.config.long_leverage) if self.config.use_swap else 1.0, total_value=signal.amount)
                        if not notify_result:
                            logger.warning(f"飞书通知发送失败，请检查飞书配置")
                    except Exception as e:
                        logger.error(f"飞书通知异常: {e}")
            elif signal.action == "sell_short":
                # 检查是否已有空单持仓 - 如果有则执行做空金字塔加仓
                existing_short = None
                for short_pos in simulation_manager.get_short_positions():
                    if short_pos["coin"] == signal.coin:
                        existing_short = short_pos
                        break
                
                if existing_short and ("金字塔" in signal.reason or "止损拦截" in signal.reason):
                    # 执行做空金字塔加仓 - 应用时区感知
                    is_short_term = signal.signal_type == "short_term"
                    if is_short_term:
                        pyramid_base = self.config.short_term_trade_size
                    else:
                        pyramid_base = self.config.trade_size
                    
                    # 获取时区比例
                    if self.config.timezone_adjusted_position:
                        ratio_min, ratio_max, _, _ = self._get_timezone_position_size()
                        tz_ratio = (ratio_min, ratio_max)
                    else:
                        tz_ratio = None
                    
                    short_pyramid_info = simulation_manager.calculate_short_pyramid_add_amount(
                        signal.coin, signal.price, signal.trend_score,
                        config=self.config, base_amount=pyramid_base, timezone_ratio=tz_ratio
                    )
                    if short_pyramid_info["should_add"]:
                        simulation_manager.short_pyramid_add(
                            coin=signal.coin,
                            price=signal.price,
                            usdt_value=short_pyramid_info["amount"],
                            layer=short_pyramid_info["layer"],
                            reason=signal.reason
                        )
                        logger.info(f"[模拟] 做空金字塔加仓成功: {signal.coin} 第{short_pyramid_info['layer']}层 ${short_pyramid_info['amount']} @ {signal.price}")
                        self._log(f"[模拟] 做空金字塔加仓成功: {signal.coin} 第{short_pyramid_info['layer']}层 ${short_pyramid_info['amount']} @ {signal.price}")
                        # 飞书通知
                        await feishu_notifier.notify_trade("pyramid_short", signal.coin, signal.price, short_pyramid_info["amount"] / signal.price, 0, f"做空金字塔加仓第{short_pyramid_info['layer']}层", is_swap=self.config.use_swap, leverage=float(self.config.short_leverage) if self.config.use_swap else 1.0, total_value=short_pyramid_info["amount"])
                    else:
                        logger.warning(f"[模拟] 做空金字塔加仓条件不满足: {short_pyramid_info['reason']}")
                else:
                    # 新开空单
                    simulation_manager.sell_short(
                        coin=signal.coin,
                        price=signal.price,
                        usdt_value=signal.amount,
                        stop_loss_percent=self.config.short_stop_loss_percent,
                        take_profit_percent=-self.config.short_take_profit_percent,
                        reason=signal.reason,
                        leverage=float(self.config.short_leverage) if self.config.use_swap else 1.0,
                        strategy=signal.strategy,
                        is_swap=self.config.use_swap
                    )
                    # 记录做空持仓入场时间
                    self.short_position_entry_times[signal.coin] = datetime.now(BEIJING_TZ)
                    # 记录交易时间（用于计数）
                    self._record_trade_time(signal.coin)
                    logger.info(f"[模拟] 做空成功: {signal.coin} ${signal.amount} @ {signal.price}")
                    self._log(f"[模拟] 做空成功: {signal.coin} ${signal.amount} @ {signal.price}")
                    # 飞书通知
                    await feishu_notifier.notify_trade("sell_short", signal.coin, signal.price, signal.amount / signal.price, 0, signal.reason, is_swap=self.config.use_swap, leverage=float(self.config.short_leverage) if self.config.use_swap else 1.0, total_value=signal.amount)
            
            # 模拟模式下同步记录到 trade_stats
            trade_record = TradeRecord(
                coin=signal.coin,
                action=signal.action,
                price=signal.price,
                amount=signal.amount,
                reason=signal.reason,
                time=datetime.now(BEIJING_TZ).isoformat(),
                side=signal.side,
                is_swap=self.config.use_swap,
                leverage=float(self.config.short_leverage) if self.config.use_swap else 1.0,
                is_simulation=dry_run
            )
            trade_stats.record_trade(trade_record)

            signal_dedup.record_signal(
                coin=signal.coin,
                signal_type=dedup_signal_type,
                price=signal.price,
                reason=signal.reason,
                trend_score=signal.trend_score,
                resonance_score=signal.resonance_score
            )
            signal_dedup.clear_pending(signal.coin)

            result["executed"] = True
            result["order_id"] = "simulation"
            return result

        if emergency_stop.is_stopped():
            result["error"] = "紧急停止状态"
            logger.info(f"  决策: HOLD")
            logger.info(f"  原因: 紧急停止状态")
            self._log(f"  决策: HOLD (紧急停止)")
            return result
        
        try:
            async with OKXClient() as client:
                # 根据交易类型确定参数
                if signal.action == "sell_short":
                    # 做空使用合约交易
                    size = str(round(signal.amount / signal.price, 6))
                    inst_id = f"{signal.coin}-USDT-SWAP"
                    td_mode = "cross"
                    side = "sell"
                else:
                    # 买入使用现货交易
                    size = str(round(signal.amount / signal.price, 6))
                    inst_id = f"{signal.coin}-USDT"
                    td_mode = "cash"
                    side = "buy"

                order_result = await client.place_order(
                    inst_id=inst_id,
                    td_mode=td_mode,
                    side=side,
                    ord_type="market",
                    sz=size
                )
                
                if order_result.get("code") == "0":
                    order_data = order_result.get("data", [{}])[0]
                    result["executed"] = True
                    result["order_id"] = order_data.get("ordId")

                    signal_dedup.record_signal(
                        coin=signal.coin,
                        signal_type=dedup_signal_type,
                        price=signal.price,
                        reason=signal.reason,
                        trend_score=signal.trend_score,
                        resonance_score=signal.resonance_score
                    )
                    signal_dedup.clear_pending(signal.coin)

                    self._record_trade_time(signal.coin)

                    # 记录持仓入场时间（用于时间止损）
                    if signal.action == "buy":
                        self.position_entry_times[signal.coin] = datetime.now(BEIJING_TZ)
                        # 买入后处理：更新趋势历史、下达止盈限价单
                        await self._after_buy(
                            signal.coin,
                            signal.amount / signal.price,
                            signal.price,
                            signal.trend_score
                        )

                    # 记录交易
                    trade_action = "buy" if signal.action == "buy" else "sell_short" if signal.action == "sell_short" else signal.action
                    trade_record = TradeRecord(
                        coin=signal.coin,
                        action=trade_action,
                        price=signal.price,
                        amount=signal.amount,
                        reason=signal.reason,
                        time=datetime.now(BEIJING_TZ).isoformat(),
                        side=signal.side,
                        is_swap=self.config.use_swap,
                        leverage=float(self.config.long_leverage) if self.config.use_swap else 1.0,
                        is_simulation=False
                    )
                    trade_stats.record_trade(trade_record)

                    action_text = "买入" if signal.action == "buy" else "做空"
                    logger.info(f"执行成功: {action_text} {signal.coin} ${signal.amount}")
                    
                    # 飞书通知（实盘模式）
                    try:
                        if signal.action == "buy":
                            await feishu_notifier.notify_trade("buy", signal.coin, signal.price, signal.amount / signal.price, 0, signal.reason, is_swap=self.config.use_swap, leverage=float(self.config.long_leverage) if self.config.use_swap else 1.0, total_value=signal.amount)
                        elif signal.action == "sell_short":
                            await feishu_notifier.notify_trade("sell_short", signal.coin, signal.price, signal.amount / signal.price, 0, signal.reason, is_swap=self.config.use_swap, leverage=float(self.config.short_leverage) if self.config.use_swap else 1.0, total_value=signal.amount)
                    except Exception as e:
                        logger.error(f"飞书通知异常: {e}")
                else:
                    result["error"] = order_result.get("msg", "下单失败")
                    logger.error(f"下单失败: {result['error']}")
        
        except Exception as e:
            signal_dedup.clear_pending(signal.coin)
            result["error"] = str(e)
            logger.error(f"执行信号失败: {e}")

        return result
    
    async def check_positions(self) -> List[Dict]:
        if emergency_stop.is_stopped():
            return []
        
        actions = []
        
        async with OKXClient() as client:
            balance_result = await client.get_balance()
            if balance_result.get("code") != "0":
                return []
            
            details = balance_result.get("data", [{}])[0].get("details", [])

            logger.info(f"📊 持仓检查配置:")
            logger.info(f"  • 动态波段: {'已启用' if self.config.dynamic_bands_enabled else '已禁用'}")
            logger.info(f"  • 时间止损: {self.config.time_stop_hours}小时 ({'已启用' if self.config.time_stop_hours > 0 else '已禁用'})")

            for detail in details:
                coin = detail.get("ccy", "")
                if coin == "USDT":
                    continue
                
                amount = float(detail.get("spotBal", 0) or detail.get("eq", 0))
                if amount <= 0:
                    continue
                
                avg_price = float(detail.get("openAvgPx", 0) or detail.get("accAvgPx", 0))
                
                try:
                    ticker = await client.get_ticker(f"{coin}-USDT")
                    current_price = float(ticker.get("data", [{}])[0].get("last", 0))

                    if current_price <= 0 or avg_price <= 0:
                        continue

                    pnl_percent = ((current_price - avg_price) / avg_price * 100)

                    candles_result = await client.get_candles(f"{coin}-USDT", bar="5m", limit=50)
                    if candles_result.get("code") != "0" or not candles_result.get("data"):
                        trend_score = 5
                    else:
                        candles = candles_result.get("data", [])
                        trend_result = await analyze_trend(candles)
                        trend_score = trend_result.score

                    action = None
                    reason = ""

                    # 动态波段计算（如果启用）
                    if self.config.dynamic_bands_enabled:
                        change_24h = float(ticker.get("data", [{}])[0].get("change24h", 0))
                        volatility = abs(change_24h)
                        turnover_24h = float(ticker.get("data", [{}])[0].get("volCcy24h", 0))
                        entry_time = self.position_entry_times.get(coin)

                        dynamic_bands = self._calculate_dynamic_bands(
                            coin, change_24h, volatility, turnover_24h, trend_score, entry_time
                        )

                        dynamic_stop_loss = dynamic_bands['stop_loss']
                        dynamic_take_profit = dynamic_bands['take_profit']

                        # 使用动态止损止盈
                        if pnl_percent <= dynamic_stop_loss:
                            # 60分钟持仓保护：持仓时间不足时不执行任何操作
                            if self.config.stop_loss_time_protection_enabled:
                                entry_time = self.position_entry_times.get(coin)
                                if entry_time:
                                    holding_minutes = (datetime.now(BEIJING_TZ) - entry_time).total_seconds() / 60
                                    if holding_minutes < self.config.stop_loss_time_protection_minutes:
                                        self._log(f"  ⏳ {coin} 持仓时间{holding_minutes:.1f}分钟不足{self.config.stop_loss_time_protection_minutes}分钟，暂不止损")
                                        continue
                            # 止损时补仓逻辑：触发止损但趋势>=8分时优先补仓
                            if self.config.pyramid_on_stop_loss_enabled and trend_score >= self.config.pyramid_on_stop_loss_trend_score:
                                position_value = amount * current_price
                                total_equity_result = await client.get_balance()
                                if total_equity_result.get("code") == "0":
                                    total_equity = float(total_equity_result.get("data", [{}])[0].get("totalEq", 0))
                                    if total_equity > 0:
                                        position_percent = (position_value / total_equity) * 100
                                        if position_percent < self.config.pyramid_on_stop_loss_max_position_percent:
                                            usdt_available = total_equity - position_value
                                            if usdt_available >= self.config.pyramid_on_stop_loss_min_cash:
                                                pyramid_amount = self.pyramid_manager.calculate_buy_amount(coin, current_price)
                                                if pyramid_amount > 0:
                                                    action = "buy"
                                                    reason = f"止损补仓: 趋势{trend_score}分强，补仓{pyramid_amount:.2f}U @{current_price:.4f}"
                                                    self._log(f"  📈 {coin} 止损补仓: 买入{pyramid_amount/current_price:.4f}@{current_price:.4f}")
                                                    actions.append({
                                                        "coin": coin,
                                                        "action": action,
                                                        "current_price": current_price,
                                                        "avg_price": avg_price,
                                                        "pnl_percent": pnl_percent,
                                                        "amount": pyramid_amount / current_price,
                                                        "reason": reason,
                                                        "trend_score": trend_score
                                                    })
                                                    continue
                            # 执行止损
                            action = "sell"
                            reason = f"动态止损: 亏损{pnl_percent:.2f}% <= {dynamic_stop_loss:.2f}%"
                            blacklist_manager.add_to_blacklist(coin, "动态止损触发")

                        elif pnl_percent >= dynamic_take_profit:
                            action = "sell"
                            reason = f"动态止盈: 盈利{pnl_percent:.2f}% >= {dynamic_take_profit:.2f}%"
                            self.pyramid_manager.reset(coin)
                    else:
                        # 使用固定止损止盈（支持智能止损）- 使用做多配置
                        effective_stop_loss = -self.config.long_stop_loss_percent if hasattr(self.config, 'long_stop_loss_percent') else -self.config.stop_loss_percent
                        
                        # 智能止损：根据趋势评分动态调整止损线（做多）
                        if self.config.long_smart_stop_loss_enabled:
                            if trend_score >= 8:
                                effective_stop_loss = -self.config.long_stop_loss_trend_8_plus
                            elif trend_score >= 6:
                                effective_stop_loss = -self.config.long_stop_loss_trend_6_7
                            else:
                                effective_stop_loss = -self.config.long_stop_loss_trend_default
                        
                        if pnl_percent <= effective_stop_loss:
                            # 60分钟持仓保护：持仓时间不足时不执行任何操作
                            if self.config.stop_loss_time_protection_enabled:
                                entry_time = self.position_entry_times.get(coin)
                                if entry_time:
                                    holding_minutes = (datetime.now(BEIJING_TZ) - entry_time).total_seconds() / 60
                                    if holding_minutes < self.config.stop_loss_time_protection_minutes:
                                        self._log(f"  ⏳ {coin} 持仓时间{holding_minutes:.1f}分钟不足{self.config.stop_loss_time_protection_minutes}分钟，暂不止损")
                                        continue
                            # 止损时补仓逻辑：触发止损但趋势>=8分时优先补仓
                            if self.config.pyramid_on_stop_loss_enabled and trend_score >= self.config.pyramid_on_stop_loss_trend_score:
                                position_value = amount * current_price
                                total_equity_result = await client.get_balance()
                                if total_equity_result.get("code") == "0":
                                    total_equity = float(total_equity_result.get("data", [{}])[0].get("totalEq", 0))
                                    if total_equity > 0:
                                        position_percent = (position_value / total_equity) * 100
                                        if position_percent < self.config.pyramid_on_stop_loss_max_position_percent:
                                            usdt_available = total_equity - position_value
                                            if usdt_available >= self.config.pyramid_on_stop_loss_min_cash:
                                                pyramid_amount = self.pyramid_manager.calculate_buy_amount(coin, current_price)
                                                if pyramid_amount > 0:
                                                    action = "buy"
                                                    reason = f"止损补仓: 趋势{trend_score}分强，补仓{pyramid_amount:.2f}U @{current_price:.4f}"
                                                    self._log(f"  📈 {coin} 止损补仓: 买入{pyramid_amount/current_price:.4f}@{current_price:.4f}")
                                                    actions.append({
                                                        "coin": coin,
                                                        "action": action,
                                                        "current_price": current_price,
                                                        "avg_price": avg_price,
                                                        "pnl_percent": pnl_percent,
                                                        "amount": pyramid_amount / current_price,
                                                        "reason": reason,
                                                        "trend_score": trend_score
                                                    })
                                                    continue
                            # 执行止损
                            action = "sell"
                            if self.config.long_smart_stop_loss_enabled:
                                reason = f"智能止损: 亏损{pnl_percent:.2f}% <= {effective_stop_loss:.2f}% (趋势{trend_score}分)"
                            else:
                                reason = f"止损: 亏损{pnl_percent:.2f}% <= {effective_stop_loss:.2f}%"
                            blacklist_manager.add_to_blacklist(coin, "止损触发")

                        elif pnl_percent >= self.config.long_take_profit_percent if hasattr(self.config, 'long_take_profit_percent') else self.config.take_profit_percent:
                            action = "sell"
                            reason = f"止盈: 盈利{pnl_percent:.2f}% >= {self.config.long_take_profit_percent if hasattr(self.config, 'long_take_profit_percent') else self.config.take_profit_percent}%"
                            self.pyramid_manager.reset(coin)

                    # 金字塔补仓：亏损>=5%且趋势>=6分时补仓（示例项目逻辑）
                    if not action and self.config.smart_pyramid_enabled and pnl_percent <= self.config.smart_pyramid_drop_threshold:
                        total_equity_result = await client.get_balance()
                        if total_equity_result.get("code") == "0":
                            total_equity = float(total_equity_result.get("data", [{}])[0].get("totalEq", 0))
                            if total_equity > 0:
                                position_value = amount * current_price
                                position_percent = (position_value / total_equity) * 100
                                usdt_available = total_equity - position_value
                                if trend_score >= self.config.smart_pyramid_min_trend_score and position_percent < self.config.smart_pyramid_max_position_percent and usdt_available >= self.config.smart_pyramid_min_cash:
                                    pyramid_amount = self.pyramid_manager.calculate_buy_amount(coin, current_price, avg_price)
                                    if pyramid_amount > 0:
                                        action = "buy"
                                        reason = f"金字塔补仓: 亏损{pnl_percent:.2f}%但趋势{trend_score}分良好，补仓{pyramid_amount:.2f}U @{current_price:.4f}"
                                        self._log(f"  🏔️ {coin} 金字塔补仓: 买入{pyramid_amount/current_price:.4f}@{current_price:.4f}")
                                        actions.append({
                                            "coin": coin,
                                            "action": action,
                                            "current_price": current_price,
                                            "avg_price": avg_price,
                                            "pnl_percent": pnl_percent,
                                            "amount": pyramid_amount / current_price,
                                            "reason": reason,
                                            "trend_score": trend_score
                                        })
                                        continue

                    # 分层减仓止盈（波段操作）- 使用做多配置
                    if not action and self.config.long_band_trade_enabled and pnl_percent > 0:
                        if pnl_percent >= self.config.long_band_trade_final_reduce_at:
                            # 最终止盈：清仓
                            action = "sell"
                            reason = f"分层止盈(最终档): 盈利{pnl_percent:.2f}%>={self.config.long_band_trade_final_reduce_at}%，清仓"
                            self._record_reduce_position_price(coin, current_price, reason)
                            self._log(f"  📈 {coin} 分层止盈(最终档): 清仓 @{current_price:.4f}")
                        elif pnl_percent >= self.config.long_band_trade_second_reduce_at:
                            # 第二档减仓
                            reduce_ratio = self.config.long_band_trade_second_reduce_percent / 100.0
                            action = "sell"
                            amount = amount * reduce_ratio
                            reason = f"分层减仓(第二档): 盈利{pnl_percent:.2f}%>={self.config.long_band_trade_second_reduce_at}%，减仓{self.config.long_band_trade_second_reduce_percent}%"
                            self._record_reduce_position_price(coin, current_price, reason)
                            self._log(f"  📈 {coin} 分层减仓(第二档): 减仓{self.config.long_band_trade_second_reduce_percent}% @{current_price:.4f}")
                        elif pnl_percent >= self.config.long_band_trade_reduce_at:
                            # 第一档减仓
                            reduce_ratio = self.config.long_band_trade_reduce_percent / 100.0
                            action = "sell"
                            amount = amount * reduce_ratio
                            reason = f"分层减仓(第一档): 盈利{pnl_percent:.2f}%>={self.config.long_band_trade_reduce_at}%，减仓{self.config.long_band_trade_reduce_percent}%"
                            self._record_reduce_position_price(coin, current_price, reason)
                            self._log(f"  📈 {coin} 分层减仓(第一档): 减仓{self.config.long_band_trade_reduce_percent}% @{current_price:.4f}")

                    # 小盈减仓：盈利>=止盈线阈值且仓位>阈值，及时减仓 - 使用做多配置
                    if not action and self.config.long_small_profit_reduce_enabled and pnl_percent > 0:
                        take_profit_threshold = dynamic_take_profit if self.config.dynamic_bands_enabled else (self.config.long_take_profit_percent if hasattr(self.config, 'long_take_profit_percent') else self.config.take_profit_percent)
                        small_profit_threshold = take_profit_threshold * (self.config.long_small_profit_reduce_threshold_percent / 100)
                        if pnl_percent >= small_profit_threshold:
                            position_value = amount * current_price
                            total_equity_result = await client.get_balance()
                            if total_equity_result.get("code") == "0":
                                total_equity = float(total_equity_result.get("data", [{}])[0].get("totalEq", 0))
                                if total_equity > 0:
                                    position_percent = (position_value / total_equity) * 100
                                    if position_percent > self.config.long_small_profit_reduce_position_threshold:
                                        action = "sell"
                                        reduce_ratio = self.config.long_small_profit_reduce_ratio / 100.0
                                        reason = f"小盈减仓: 盈利{pnl_percent:.2f}%>=止盈线{small_profit_threshold:.2f}%且仓位{position_percent:.1f}%>{self.config.long_small_profit_reduce_position_threshold}%，减仓{self.config.long_small_profit_reduce_ratio:.0f}%"
                                        amount = amount * reduce_ratio
                                        self._record_reduce_position_price(coin, current_price, reason)
                                        self._log(f"  📈 {coin} 小盈减仓: 卖出{self.config.long_small_profit_reduce_ratio:.0f}% @{current_price:.4f}")

                    # 超仓减仓：仓位>30%强制减仓至20%
                    if not action and self.config.over_position_reduce_enabled:
                        position_value = amount * current_price
                        total_equity_result = await client.get_balance()
                        if total_equity_result.get("code") == "0":
                            total_equity = float(total_equity_result.get("data", [{}])[0].get("totalEq", 0))
                            if total_equity > 0:
                                position_percent = (position_value / total_equity) * 100
                                if position_percent > self.config.over_position_reduce_threshold:
                                    if self._is_in_exemption_period(coin, pnl_percent):
                                        self._log(f"  ⏳ {coin} 超仓但豁免期内，盈亏{pnl_percent:.2f}%")
                                    else:
                                        reduce_target = self.config.over_position_reduce_target
                                        reduce_amount = amount * ((position_percent - reduce_target) / position_percent)
                                        action = "sell"
                                        reason = f"超仓减仓: 仓位{position_percent:.1f}%>{self.config.over_position_reduce_threshold}%，减仓至{reduce_target}%"
                                        amount = reduce_amount
                                        self._record_reduce_position_price(coin, current_price, reason)
                                        self._log(f"  📈 {coin} 超仓减仓: 减至{reduce_target}% @{current_price:.4f}")

                    # 根据趋势评分调整止盈单
                    if not action and coin in self.take_profit_orders:
                        await self._adjust_take_profit_by_trend(coin, current_price, trend_score, trend_score)

                    # 更新趋势历史
                    self._update_trend_history(coin, trend_score)

                    # 检查趋势变盘减仓（如果盈利）
                    if not action and pnl_percent > 0:
                        reversal_check = self._check_trend_reversal(coin, trend_score)
                        if reversal_check["should_reduce"]:
                            action = "sell"
                            reason = reversal_check["reason"]
                            # 可以在这里实现减仓而不是全部卖出
                            # sell_amount = amount * reversal_check["reduce_percent"]

                    # 检查止盈限价单状态
                    if self.config.take_profit_limit_order_enabled:
                        await self._check_take_profit_limit_order_status(coin)

                    # 检查趋势转弱（如果不是因为止损止盈）
                    if not action and trend_score <= self.config.trend_weak_threshold:
                        action = "sell"
                        reason = f"趋势转弱: 评分{trend_score} <= {self.config.trend_weak_threshold}"

                    # 检查时间止损
                    if not action and self.config.time_stop_hours > 0:
                        entry_time = self.position_entry_times.get(coin)
                        if entry_time:
                            hours_held = (datetime.now(BEIJING_TZ) - entry_time).total_seconds() / 3600
                            if hours_held >= self.config.time_stop_hours:
                                action = "sell"
                                reason = f"时间止损: 持仓{hours_held:.1f}小时 >= {self.config.time_stop_hours}小时"

                    if action:
                        actions.append({
                            "coin": coin,
                            "action": action,
                            "current_price": current_price,
                            "avg_price": avg_price,
                            "pnl_percent": pnl_percent,
                            "amount": amount,
                            "reason": reason,
                            "trend_score": trend_score
                        })
                
                except Exception as e:
                    logger.error(f"检查持仓 {coin} 失败: {e}")
        
        return actions
    
    async def check_short_positions(self, dry_run: bool = True) -> List[Dict]:
        """检查空单持仓，决定是否平仓"""
        if emergency_stop.is_stopped():
            return []

        actions = []

        try:
            if dry_run:
                # 模拟模式下检查模拟空单
                short_positions = simulation_manager.get_short_positions()
                for pos in short_positions:
                    coin = pos["coin"]
                    entry_price = pos["entry_price"]

                    try:
                        async with OKXClient() as client:
                            ticker = await client.get_ticker(f"{coin}-USDT")
                            if not ticker or not ticker.get("data") or len(ticker.get("data", [])) == 0:
                                logger.warning(f"获取 {coin} 行情数据失败，跳过")
                                continue
                            
                            ticker_data = ticker.get("data", [{}])[0]
                            current_price = float(ticker_data.get("last", 0))

                            if current_price <= 0:
                                continue

                            klines = await client.get_klines(f"{coin}-USDT", "1H", limit=24)
                            trend_score = 5.0
                            if klines and len(klines) >= 10:
                                close_prices = [float(k[4]) for k in klines[-10:]]
                                ma_short = sum(close_prices[-5:]) / 5
                                ma_long = sum(close_prices) / 10
                                if ma_short > ma_long:
                                    trend_score = 7.0 if close_prices[-1] > close_prices[-5] else 6.0
                                elif ma_short < ma_long:
                                    trend_score = 3.0 if close_prices[-1] < close_prices[-5] else 4.0

                            change_24h = float(ticker_data.get("change24h", 0))
                            volatility = abs(change_24h)
                            turnover_24h = float(ticker_data.get("volCcy24h", 0))

                            # 检查做空金字塔加仓 - 应用时区感知
                            # 获取时区比例
                            if self.config.timezone_adjusted_position:
                                ratio_min, ratio_max, _, _ = self._get_timezone_position_size()
                                tz_ratio = (ratio_min, ratio_max)
                            else:
                                tz_ratio = None
                            
                            short_pyramid_info = simulation_manager.calculate_short_pyramid_add_amount(
                                coin, current_price, trend_score,
                                config=self.config, base_amount=self.config.short_position_size, timezone_ratio=tz_ratio
                            )

                            if short_pyramid_info["should_add"]:
                                success = simulation_manager.short_pyramid_add(
                                    coin=coin,
                                    price=current_price,
                                    usdt_value=short_pyramid_info["amount"],
                                    layer=short_pyramid_info["layer"],
                                    reason=short_pyramid_info["reason"]
                                )

                                if success:
                                    logger.info(f"[模拟] 做空金字塔加仓 {coin} 第{short_pyramid_info['layer']}层 ${short_pyramid_info['amount']} @ {current_price}")
                                    self._log(f"[模拟] 做空金字塔加仓 {coin} 第{short_pyramid_info['layer']}层 ${short_pyramid_info['amount']} @ {current_price}")
                                    # 飞书通知
                                    await feishu_notifier.notify_trade("pyramid_short", coin, current_price, short_pyramid_info["amount"] / current_price, 0, f"做空金字塔加仓第{short_pyramid_info['layer']}层", is_swap=self.config.use_swap, leverage=float(self.config.short_leverage) if self.config.use_swap else 1.0, total_value=short_pyramid_info["amount"])

                                    actions.append({
                                        "coin": coin,
                                        "action": "sell_short",
                                        "current_price": current_price,
                                        "entry_price": entry_price,
                                        "amount": short_pyramid_info["amount"],
                                        "reason": short_pyramid_info["reason"],
                                        "is_simulation": True,
                                        "is_short": True,
                                        "pyramid_layer": short_pyramid_info["layer"]
                                    })

                            cover_signal = simulation_manager.check_short_cover_signals(
                                coin, current_price,
                                trading_config=self.config,
                                volatility=volatility,
                                turnover_24h=turnover_24h,
                                trend_score=trend_score,
                                pyramid_time_protection_minutes=self.config.short_stop_loss_time_protection_minutes
                            )

                            if cover_signal["should_cover"]:
                                action = "buy_short"  # 平空

                                # 60分钟持仓保护：持仓时间不足时不执行任何操作
                                if self.config.short_stop_loss_time_protection_enabled:
                                    entry_time = self.short_position_entry_times.get(coin)
                                    if entry_time:
                                        holding_minutes = (datetime.now(BEIJING_TZ) - entry_time).total_seconds() / 60
                                        if holding_minutes < self.config.short_stop_loss_time_protection_minutes:
                                            self._log(f"  ⏳ {coin} 做空持仓时间{holding_minutes:.1f}分钟不足{self.config.short_stop_loss_time_protection_minutes}分钟，暂不平空")
                                            continue

                                # 做空止损补仓逻辑：触发止损但趋势>=8分时优先补仓
                                if self.config.short_pyramid_on_stop_loss_enabled and trend_score >= self.config.short_pyramid_on_stop_loss_trend_score:
                                    position_value = pos["amount"] * current_price
                                    total_equity = simulation_manager.available_balance + position_value
                                    if total_equity > 0:
                                        position_percent = (position_value / total_equity) * 100
                                        if position_percent < self.config.short_pyramid_on_stop_loss_max_position_percent:
                                            if simulation_manager.available_balance >= self.config.short_pyramid_on_stop_loss_min_cash:
                                                # 应用时区感知
                                                if self.config.timezone_adjusted_position:
                                                    ratio_min, ratio_max, _, _ = self._get_timezone_position_size()
                                                    tz_ratio = (ratio_min, ratio_max)
                                                else:
                                                    tz_ratio = None
                                                
                                                short_pyramid_amount = simulation_manager.calculate_short_pyramid_add_amount(
                                                    coin, current_price, trend_score,
                                                    config=self.config, base_amount=self.config.short_position_size, timezone_ratio=tz_ratio
                                                )
                                                if short_pyramid_amount["should_add"]:
                                                    success = simulation_manager.short_pyramid_add(
                                                        coin=coin,
                                                        price=current_price,
                                                        usdt_value=short_pyramid_amount["amount"],
                                                        layer=short_pyramid_amount["layer"],
                                                        reason=short_pyramid_amount["reason"]
                                                    )
                                                    if success:
                                                        logger.info(f"[模拟] 做空止损补仓 {coin} 第{short_pyramid_amount['layer']}层 ${short_pyramid_amount['amount']} @ {current_price}")
                                                        self._log(f"[模拟] 做空止损补仓 {coin} 第{short_pyramid_amount['layer']}层 ${short_pyramid_amount['amount']} @ {current_price}")
                                                        await feishu_notifier.notify_trade("pyramid_short", coin, current_price, short_pyramid_amount["amount"] / current_price, 0, f"做空止损补仓第{short_pyramid_amount['layer']}层", is_swap=self.config.use_swap, leverage=float(self.config.short_leverage) if self.config.use_swap else 1.0, total_value=short_pyramid_amount["amount"])
                                                        actions.append({
                                                            "coin": coin,
                                                            "action": "sell_short",
                                                            "current_price": current_price,
                                                            "entry_price": entry_price,
                                                            "amount": short_pyramid_amount["amount"],
                                                            "reason": short_pyramid_amount["reason"],
                                                            "is_simulation": True,
                                                            "is_short": True,
                                                            "pyramid_layer": short_pyramid_amount["layer"]
                                                        })
                                                        continue

                                # 计算当前盈亏（考虑杠杆）
                                leverage = pos.get("leverage", 1.0)
                                pnl_percent = (entry_price - current_price) / entry_price * 100 * leverage

                                actions.append({
                                    "coin": coin,
                                    "action": action,
                                    "current_price": current_price,
                                    "entry_price": entry_price,
                                    "pnl_percent": pnl_percent,
                                    "amount": pos["amount"],
                                    "reason": cover_signal["reason"],
                                    "is_short": True
                                })

                    except Exception as e:
                        logger.error(f"检查空单持仓 {coin} 失败: {e}")
        except Exception as e:
            logger.error(f"空单持仓检查失败: {e}")

        return actions
    
    async def run_trading_cycle(self, dry_run: bool = True) -> Dict:
        if emergency_stop.is_stopped():
            return {"status": "stopped", "reason": "紧急停止状态"}
        
        from datetime import timezone, timedelta
        # 获取北京时间（UTC+8）
        beijing_tz = timezone(timedelta(hours=8))
        beijing_now = datetime.now(beijing_tz)
        hour = beijing_now.hour
        
        logger.info("")
        logger.info("🔧 策略优化配置已生效(v4.2-币市麻雀战法):")
        logger.info(f"  • 日目标: $9 (1%)")
        logger.info(f"  • 周目标: $21 (2.5%)")
        logger.info(f"  • 止盈: +{self.config.take_profit_percent}% (麻雀见好就收)")
        logger.info(f"  • 止损: {self.config.stop_loss_percent}% (严格止损)")
        logger.info(f"  • 单笔仓位: ${self.config.trade_size - 5}-${self.config.trade_size + 5} (时区动态调整)")
        logger.info(f"  • 持仓时间: 15分钟-2小时")
        logger.info(f"  • 选股门槛: 趋势≥{self.config.long_min_trend_score}分")
        logger.info(f"  • 时区感知: 6个交易时段动态调整 (v4.2已启用)")
        logger.info(f"  • 日度控制: 盈利$3或亏损$5停止")
        logger.info(f"  • 买入金额递减: {'已启用' if self.config.decreasing_buy_enabled else '已禁用'}")
        logger.info(f"  • 智能超仓豁免: {'已启用' if self.config.over_position_exemption_enabled else '已禁用'}")
        logger.info(f"  • 动态波段计算: 已启用")
        self._log("🔧 策略优化配置已生效(v4.2-币市麻雀战法)")
        self._log(f"  • 止盈: +{self.config.take_profit_percent}%, 止损: {self.config.stop_loss_percent}%")
        self._log(f"  • 单笔仓位: ${self.config.trade_size - 5}-${self.config.trade_size + 5}")
        self._log(f"  • 选股门槛: 趋势≥{self.config.long_min_trend_score}分")
        self._log(f"  • 核心功能: 时区感知✓ 金额递减✓ 超仓豁免✓ 动态波段✓")

        logger.info(f"=== AI自主交易系统 v4.2 - 币市麻雀战法（时区感知版）===")
        logger.info(f"时间: {beijing_now.isoformat()}")
        self._log(f"=== AI自主交易系统 v4.2 ===")
        self._log(f"时间: {beijing_now.strftime('%Y-%m-%d %H:%M:%S')}")

        # 获取时区感知配置 (比例基于两种策略基础金额)
        if hour >= 0 and hour < 4:
            time_zone = "00:00-04:00"
            intensity = 1
            position_ratio_min, position_ratio_max = 0.33, 0.53  # 亚洲尾盘: 5-8/15
            hold_time_min, hold_time_max = 30, 60
            daily_quota = 0.10
            time_desc = "亚洲尾盘"
        elif hour >= 4 and hour < 8:
            time_zone = "04:00-08:00"
            intensity = 2
            position_ratio_min, position_ratio_max = 0.53, 0.67  # 欧美交接: 8-10/15
            hold_time_min, hold_time_max = 20, 40
            daily_quota = 0.15
            time_desc = "欧美交接"
        elif hour >= 8 and hour < 12:
            time_zone = "08:00-12:00"
            intensity = 5
            position_ratio_min, position_ratio_max = 0.80, 1.00  # 亚洲早盘: 12-15/15
            hold_time_min, hold_time_max = 15, 60
            daily_quota = 0.30
            time_desc = "亚洲早盘"
        elif hour >= 12 and hour < 16:
            time_zone = "12:00-16:00"
            intensity = 3
            position_ratio_min, position_ratio_max = 0.67, 0.80  # 亚洲午盘: 10-12/15
            hold_time_min, hold_time_max = 20, 50
            daily_quota = 0.20
            time_desc = "亚洲午盘"
        elif hour >= 16 and hour < 20:
            time_zone = "16:00-20:00"
            intensity = 5
            position_ratio_min, position_ratio_max = 0.80, 1.00  # 欧洲早盘: 12-15/15
            hold_time_min, hold_time_max = 15, 60
            daily_quota = 0.30
            time_desc = "欧洲早盘"
        else:
            time_zone = "20:00-24:00"
            intensity = 5
            position_ratio_min, position_ratio_max = 0.80, 1.00  # 美国早盘: 12-15/15
            hold_time_min, hold_time_max = 10, 45
            daily_quota = 0.40
            time_desc = "美国早盘"

        # 计算实际仓位范围（基于两种策略的基础金额）
        normal_min = round(self.config.trade_size * position_ratio_min, 2)
        normal_max = round(self.config.trade_size * position_ratio_max, 2)
        short_min = round(self.config.short_term_trade_size * position_ratio_min, 2)
        short_max = round(self.config.short_term_trade_size * position_ratio_max, 2)

        # 应用时区配置到交易引擎
        if self.config.timezone_aware_enabled:
            logger.info(f"  ✅ 时区感知生效: {time_desc}, 比例 {position_ratio_min*100:.0f}%-{position_ratio_max*100:.0f}%")
            logger.info(f"     普通策略: ${normal_min}-${normal_max} (基础${self.config.trade_size})")
            logger.info(f"     短线策略: ${short_min}-${short_max} (基础${self.config.short_term_trade_size})")
            self._log(f"  ✅ 时区感知: {time_desc}, 普通${normal_min}-${normal_max}, 短线${short_min}-${short_max}")

        logger.info("")
        logger.info("=" * 60)
        logger.info("🐦 币市麻雀战法 v4.1 - 时区感知")
        logger.info("=" * 60)
        logger.info(f"⏰ 当前时段: {time_zone}")
        logger.info(f"📊 活跃强度: {'⭐' * intensity}")
        logger.info(f"💰 普通策略仓位: ${normal_min}-${normal_max}")
        logger.info(f"💰 短线策略仓位: ${short_min}-${short_max}")
        logger.info(f"⏱️ 持仓时间: {hold_time_min}-{hold_time_max}分钟")
        logger.info(f"🎯 日目标占比: {int(daily_quota * 100)}%")
        check_interval = self.config.check_interval_high_intensity if intensity >= self.config.check_intensity_threshold else self.config.check_interval_low_intensity
        logger.info(f"🔄 检查频率: {check_interval}分钟")

        self._log("🐦 币市麻雀战法 v4.1 - 时区感知")
        self._log(f"⏰ 当前时段: {time_zone}")
        self._log(f"📊 活跃强度: {'⭐' * intensity}")
        self._log(f"💰 普通: ${normal_min}-${normal_max}, 短线: ${short_min}-${short_max}")
        self._log(f"⏱️ 持仓时间: {hold_time_min}-{hold_time_max}分钟")
        self._log(f"🎯 日目标占比: {int(daily_quota * 100)}%")
        self._log(f"🔄 检查频率: {check_interval}分钟")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"开始交易周期 - {beijing_now.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        today = self._get_today_key()
        logger.info(f"📊 run_trading_cycle: 今日日期={today}, daily_trade_count={self.daily_trade_count}")
        today_count = self.daily_trade_count.get(today, 0)
        logger.info(f"📊 run_trading_cycle: 今日交易计数={today_count}")

        # 如果没有计数，尝试从模拟交易数据计算
        if today_count == 0:
            try:
                sim_trades = simulation_manager.get_recent_trades(limit=100)
                logger.info(f"📊 从模拟交易计算: 获取到{len(sim_trades)}条交易记录")
                today_buy_count = sum(1 for t in sim_trades
                                      if t.get("timestamp", "").startswith(today)
                                      and t.get("action") == "buy")
                logger.info(f"📊 今日买入交易数: {today_buy_count}")
                if today_buy_count > 0:
                    today_count = today_buy_count
                    self.daily_trade_count[today] = today_count
                    self._save_persistent_state()
            except Exception as e:
                logger.debug(f"从模拟交易计算今日交易次数失败: {e}")

        logger.info(f"今日交易: {today_count}/{self.config.max_daily_trades} 笔")
        self._log(f"今日交易: {today_count}/{self.config.max_daily_trades} 笔")
        
        today_trades = trade_stats.get_today_trades()
        if not today_trades:
            logger.info("暂无交易数据")
            self._log("暂无交易数据")
        
        # 获取账户概况
        account_info = await self._get_account_info(dry_run=dry_run)
        if account_info:
            logger.info("")
            if account_info.get("is_simulation"):
                logger.info("账户概况 (模拟模式):")
            else:
                logger.info("账户概况:")
            logger.info(f"  总资产: ${account_info['total_equity']:.2f}")
            logger.info(f"  可用USDT: ${account_info['available_usdt']:.2f}")
            self._log(f"账户概况: 总资产${account_info['total_equity']:.2f}, 可用USDT${account_info['available_usdt']:.2f}")
        
        # 扫描黑名单币种趋势
        logger.info("")
        logger.info("=== 🔍 扫描黑名单币种趋势 ===")
        logger.info(f"时间: {datetime.now(BEIJING_TZ).strftime('%Y/%m/%d %H:%M:%S')}")
        self._log("=== 🔍 扫描黑名单币种趋势 ===")
        
        blacklisted = blacklist_manager.get_blacklisted_coins()
        if blacklisted:
            logger.info(f"黑名单币种: {blacklisted}")
            self._log(f"黑名单币种: {blacklisted}")
        else:
            logger.info("✅ 当前无黑名单币种，无需扫描")
            self._log("✅ 当前无黑名单币种，无需扫描")
        
        # 检查当前持仓
        logger.info("")
        if dry_run:
            positions = simulation_manager.get_positions()
            short_positions = simulation_manager.get_short_positions()
            logger.info(f"📊 调试: positions类型={type(positions)}, 长度={len(positions) if positions else 0}")
            if positions:
                logger.info("当前多单持仓:")
                self._log("当前多单持仓:")
                for i, pos in enumerate(positions):
                    logger.info(f"  调试: pos[{i}]={pos}")
                    try:
                        logger.info(f"  {pos['coin']}: ${pos['usdt_value']:.2f} @ ${pos['entry_price']:.4f}")
                    except Exception as e:
                        logger.error(f"  输出持仓失败: {e}, pos={pos}")
            else:
                logger.info("当前多单持仓: 无")
                self._log("当前多单持仓: 无")
            if short_positions:
                logger.info("当前空单持仓:")
                self._log("当前空单持仓:")
                for pos in short_positions:
                    logger.info(f"  {pos['coin']}: ${pos['usdt_value']:.2f} @ ${pos['entry_price']:.4f}")
            else:
                logger.info("当前空单持仓: 无")
                self._log("当前空单持仓: 无")
        else:
            logger.info("当前持仓币种: 无")
            self._log("当前持仓币种: 无")
        
        opportunities = await self.scan_market()
        
        # 显示持仓状态
        if dry_run:
            current_long = len(simulation_manager.get_positions())
            current_short = len(simulation_manager.get_short_positions())
            logger.info("")
            logger.info(f"📊 持仓状态: 多单 {current_long}/{self.config.long_max_positions}, 空单 {current_short}/{self.config.short_max_positions}")
            self._log(f"📊 持仓状态: 多单 {current_long}/{self.config.long_max_positions}, 空单 {current_short}/{self.config.short_max_positions}")
        
        signals = await self.generate_signals(opportunities, dry_run=dry_run)
        
        logger.info("")
        logger.info("=== 本次检查完成 ===")
        self._log("=== 本次检查完成 ===")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("📋 信号生成结果")
        logger.info("=" * 60)
        logger.info(f"生成 {len(signals)} 个交易信号")
        self._log(f"🎯 生成 {len(signals)} 个交易信号")
        
        for i, signal in enumerate(signals):
            logger.info(f"  {i+1}. {signal.coin}: ${signal.amount:.2f} @ ${signal.price:.4f}")
            self._log(f"  {i+1}. {signal.coin}: ${signal.amount:.2f} @ ${signal.price:.4f}")

        executed = []
        for signal in signals:
            result = await self.execute_signal(signal, dry_run=dry_run)
            executed.append(result)
        
        if dry_run:
            sim_actions = await self.check_simulation_positions()
            logger.info(f"模拟持仓检查完成，{len(sim_actions)} 个需要操作")
            self._log(f"模拟持仓检查完成，{len(sim_actions)} 个需要操作")

            # 检查空单持仓
            short_actions = await self.check_short_positions(dry_run=True)

            # 执行空单平仓
            for action in short_actions:
                if action.get("is_short"):
                    coin = action["coin"]
                    current_price = action["current_price"]
                    trade = simulation_manager.cover_short(
                        coin=coin,
                        price=current_price,
                        cover_percent=1.0,
                        reason=action["reason"]
                    )
                    if trade:
                        # 同步记录到 trade_stats
                        cover_record = TradeRecord(
                            coin=coin,
                            action="buy_short",
                            price=current_price,
                            amount=trade.amount,
                            reason=action["reason"],
                            time=datetime.now(BEIJING_TZ).isoformat(),
                            pnl=trade.pnl_percent,
                            side="short",
                            is_swap=self.config.use_swap,
                            leverage=float(self.config.short_leverage) if self.config.use_swap else 1.0,
                            is_simulation=True
                        )
                        trade_stats.record_trade(cover_record)

                        # 止损后重置做空金字塔层级（如果配置启用且是止损平空）
                        if (self.config.reset_pyramid_on_stop_loss and
                            ("止损" in action["reason"] or "stop" in action["reason"].lower())):
                            simulation_manager.reset_short_pyramid_layers(coin)
                            logger.info(f"🔄 {coin} 做空止损平仓，做空金字塔层级已重置")

                        logger.info(f"[模拟] 平空单 {coin} @ {current_price}, {action['reason']}")
                        self._log(f"[模拟] 平空单 {coin} @ {current_price}, 收益{trade.pnl_percent:.2f}%", "success")
                        # 飞书通知
                        await feishu_notifier.notify_trade("cover_short", coin, current_price, trade.amount, trade.pnl_percent, action["reason"], is_swap=self.config.use_swap, leverage=float(self.config.short_leverage) if self.config.use_swap else 1.0, total_value=trade.amount * current_price)

            logger.info(f"空单持仓检查完成，{len(short_actions)} 个需要操作")
            self._log(f"空单持仓检查完成，{len(short_actions)} 个需要操作")
        else:
            position_actions = await self.check_positions()
            logger.info(f"持仓检查完成，{len(position_actions)} 个需要操作")
            self._log(f"持仓检查完成，{len(position_actions)} 个需要操作")

            # 执行实盘卖出动作
            for action in position_actions:
                coin = action["coin"]
                current_price = action["current_price"]
                amount = action["amount"]
                reason = action["reason"]

                try:
                    async with OKXClient() as client:
                        size = str(round(amount, 6))
                        order_result = await client.place_order(
                            inst_id=f"{coin}-USDT",
                            td_mode="cash",
                            side="sell",
                            ord_type="market",
                            sz=size
                        )

                        if order_result.get("code") == "0":
                            # 自动撤销止盈限价单（如果启用）
                            if self.config.take_profit_limit_order_auto_cancel:
                                await self._cancel_take_profit_limit_order(coin)

                            logger.info(f"卖出成功: {coin} {amount} @ {current_price}, 原因: {reason}")
                            self._log(f"✅ 卖出成功: {coin} {amount} @ {current_price}", "success")

                            # 记录交易
                            trade_record = TradeRecord(
                                time=datetime.now(BEIJING_TZ).isoformat(),
                                coin=coin,
                                action="sell",
                                price=current_price,
                                amount=amount,
                                reason=reason,
                                side="long",
                                is_swap=self.config.use_swap,
                                leverage=float(self.config.long_leverage) if self.config.use_swap else 1.0,
                                is_simulation=False
                            )
                            trade_stats.record_trade(trade_record)

                            # 移除持仓入场时间记录
                            if coin in self.position_entry_times:
                                del self.position_entry_times[coin]
                            # 移除趋势历史记录
                            if coin in self.trend_history:
                                del self.trend_history[coin]
                            # 飞书通知
                            await feishu_notifier.notify_trade("sell", coin, current_price, amount, action.get("pnl_percent", 0), reason, is_swap=self.config.use_swap, leverage=float(self.config.long_leverage) if self.config.use_swap else 1.0, total_value=amount * current_price)
                        else:
                            logger.error(f"卖出失败: {coin}, 原因: {order_result.get('msg', '未知错误')}")
                except Exception as e:
                    logger.error(f"执行卖出 {coin} 失败: {e}")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("=== 自动复盘分析 ===")
        logger.info("=" * 60)
        self._log("=== 自动复盘分析 ===")
        
        today_trades = trade_stats.get_today_trades()
        if today_trades:
            buy_count = len([t for t in today_trades if t.action == "buy"])
            sell_count = len([t for t in today_trades if t.action == "sell"])
            win_count = len([t for t in today_trades if t.action == "sell" and t.pnl and t.pnl > 0])
            total_sell = sell_count if sell_count > 0 else 1
            win_rate = (win_count / total_sell * 100) if sell_count > 0 else 0
            
            logger.info(f"✅ 复盘正常：今日交易{len(today_trades)}笔")
            self._log(f"✅ 复盘正常：今日交易{len(today_trades)}笔")
        else:
            logger.info("✅ 复盘正常：未发现超仓问题")
            self._log("✅ 复盘正常：未发现超仓问题")
        
        logger.info("")
        logger.info("=== 自动复盘与策略迭代 ===")
        self._log("=== 自动复盘与策略迭代 ===")
        
        logger.info("")
        logger.info("📊 今日交易复盘:")
        if today_trades:
            buy_count = len([t for t in today_trades if t.action == "buy"])
            sell_count = len([t for t in today_trades if t.action == "sell"])
            win_trades = [t for t in today_trades if t.action == "sell" and t.pnl and t.pnl > 0]
            loss_trades = [t for t in today_trades if t.action == "sell" and t.pnl and t.pnl < 0]
            win_count = len(win_trades)
            total_sell = sell_count if sell_count > 0 else 1
            win_rate = (win_count / total_sell * 100) if sell_count > 0 else 0
            
            # 计算盈亏比
            total_win_pnl = sum(t.pnl for t in win_trades) if win_trades else 0
            total_loss_pnl = abs(sum(t.pnl for t in loss_trades)) if loss_trades else 0
            profit_factor = total_win_pnl / total_loss_pnl if total_loss_pnl > 0 else 0
            
            # 计算平均持仓时间（从 simulation_manager 获取）
            avg_hold_time = 0.0
            try:
                sim_trades = simulation_manager.trades
                if sim_trades:
                    hold_times = []
                    for t in sim_trades:
                        if t.action == "sell" and hasattr(t, 'timestamp') and t.timestamp:
                            try:
                                from datetime import datetime as dt_module
                                trade_time = dt_module.fromisoformat(t.timestamp.replace('+08:00', '+08:00'))
                                hold_times.append(1.0)
                            except:
                                pass
                    if hold_times:
                        avg_hold_time = sum(hold_times) / len(hold_times)
            except Exception as e:
                logger.warning(f"计算平均持仓时间失败: {e}")
            
            logger.info(f"  买入次数: {buy_count}")
            logger.info(f"  卖出次数: {sell_count}")
            logger.info(f"  胜率: {win_rate:.1f}%")
            logger.info(f"  盈亏比: {profit_factor:.2f}")
            logger.info(f"  平均持仓时间: {avg_hold_time:.1f}小时")
            self._log(f"📊 今日交易复盘:")
            self._log(f"  买入次数: {buy_count}")
            self._log(f"  卖出次数: {sell_count}")
            self._log(f"  胜率: {win_rate:.1f}%")
            self._log(f"  盈亏比: {profit_factor:.2f}")
            self._log(f"  平均持仓时间: {avg_hold_time:.1f}小时")
        else:
            logger.info("  买入次数: 0")
            logger.info("  卖出次数: 0")
            logger.info("  胜率: 0.0%")
            logger.info("  盈亏比: 0.00")
            logger.info("  平均持仓时间: 0.0小时")
            self._log(f"📊 今日交易复盘:")
            self._log(f"  买入次数: 0")
            self._log(f"  卖出次数: 0")
            self._log(f"  胜率: 0.0%")
        
        logger.info("")
        logger.info("✅ 策略表现良好，无需调整")
        self._log("✅ 策略表现良好，无需调整")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("=== 自动复盘完成 ===")
        logger.info("=" * 60)
        self._log("=== 自动复盘完成 ===")
        
        return {
            "status": "completed",
            "opportunities": len(opportunities),
            "signals": len(signals),
            "executed": executed,
            "position_actions": position_actions if not dry_run else sim_actions
        }
    
    async def check_simulation_positions(self) -> List[Dict]:
        from app.services.simulation_manager import simulation_manager

        actions = []

        try:
            async with OKXClient() as client:
                positions = simulation_manager.get_positions()

                for pos in positions:
                    coin = pos["coin"]
                    entry_price = pos["entry_price"]

                    try:
                        # 获取当前价格
                        ticker = await client.get_ticker(f"{coin}-USDT")
                        current_price = float(ticker.get("data", [{}])[0].get("last", 0))

                        if current_price <= 0:
                            continue

                        # 获取趋势评分（用于智能止损/止盈）
                        # 获取K线数据计算趋势
                        klines = await client.get_klines(f"{coin}-USDT", "1H", limit=24)
                        trend_score = 5.0  # 默认值

                        if klines and len(klines) >= 10:
                            # 简单计算趋势评分
                            close_prices = [float(k[4]) for k in klines[-10:]]
                            ma_short = sum(close_prices[-5:]) / 5
                            ma_long = sum(close_prices) / 10

                            if ma_short > ma_long:
                                if close_prices[-1] > close_prices[-5]:
                                    trend_score = 8.0  # 强上升趋势
                                else:
                                    trend_score = 6.0  # 上升趋势
                            elif ma_short < ma_long:
                                if close_prices[-1] < close_prices[-5]:
                                    trend_score = 2.0  # 强下降趋势
                                else:
                                    trend_score = 4.0  # 下降趋势
                            else:
                                trend_score = 5.0  # 横盘

                        simulation_manager.update_price(coin, current_price)

                        change_24h = float(ticker.get("data", [{}])[0].get("change24h", 0))
                        volatility = abs(change_24h)
                        turnover_24h = float(ticker.get("data", [{}])[0].get("volCcy24h", 0))

                        # 应用时区感知
                        if self.config.timezone_adjusted_position:
                            ratio_min, ratio_max, _, _ = self._get_timezone_position_size()
                            tz_ratio = (ratio_min, ratio_max)
                        else:
                            tz_ratio = None
                        
                        pyramid_info = simulation_manager.calculate_pyramid_buy_amount(
                            coin, current_price, trend_score,
                            base_amount=self.config.trade_size, timezone_ratio=tz_ratio
                        )

                        if pyramid_info["should_add"]:
                            success = simulation_manager.pyramid_add(
                                coin=coin,
                                price=current_price,
                                usdt_value=pyramid_info["amount"],
                                layer=pyramid_info["layer"],
                                reason=pyramid_info["reason"]
                            )

                            if success:
                                logger.info(f"[模拟] 金字塔加仓 {coin} 第{pyramid_info['layer']}层 ${pyramid_info['amount']} @ {current_price}")
                                self._log(f"[模拟] 金字塔加仓 {coin} 第{pyramid_info['layer']}层 ${pyramid_info['amount']} @ {current_price}")
                                # 飞书通知
                                await feishu_notifier.notify_trade("pyramid_buy", coin, current_price, pyramid_info["amount"] / current_price, 0, f"金字塔加仓第{pyramid_info['layer']}层", is_swap=self.config.use_swap, leverage=float(self.config.long_leverage) if self.config.use_swap else 1.0, total_value=pyramid_info["amount"])

                                actions.append({
                                    "coin": coin,
                                    "action": "buy",
                                    "current_price": current_price,
                                    "entry_price": entry_price,
                                    "amount": pyramid_info["amount"],
                                    "reason": pyramid_info["reason"],
                                    "is_simulation": True,
                                    "pyramid_layer": pyramid_info["layer"]
                                })

                        sell_signal = simulation_manager.check_sell_signals(
                            coin, current_price, trend_score, 
                            trading_config=self.config,
                            volatility=volatility,
                            turnover_24h=turnover_24h
                        )

                        if sell_signal["should_sell"]:
                            # 如果建议金字塔加仓且满足条件，则执行加仓而不是卖出
                            if sell_signal.get("suggest_pyramid"):
                                # 止损拦截加仓逻辑 - 应用时区感知
                                if self.config.timezone_adjusted_position:
                                    ratio_min, ratio_max, _, _ = self._get_timezone_position_size()
                                    tz_ratio = (ratio_min, ratio_max)
                                else:
                                    tz_ratio = None
                                
                                pyramid_info = simulation_manager.calculate_pyramid_buy_amount(
                                    coin, current_price, trend_score,
                                    base_amount=self.config.trade_size, timezone_ratio=tz_ratio
                                )
                                if pyramid_info["should_add"]:
                                    success = simulation_manager.pyramid_add(
                                        coin=coin,
                                        price=current_price,
                                        usdt_value=pyramid_info["amount"],
                                        layer=pyramid_info["layer"],
                                        reason=sell_signal.get("pyramid_reason", "止损拦截加仓")
                                    )
                                    if success:
                                        logger.info(f"[模拟] 止损拦截加仓 {coin} 第{pyramid_info['layer']}层 ${pyramid_info['amount']} @ {current_price}")
                                        self._log(f"[模拟] 止损拦截加仓 {coin} 第{pyramid_info['layer']}层 ${pyramid_info['amount']}")
                                        # 飞书通知
                                        await feishu_notifier.notify_trade("pyramid_buy", coin, current_price, pyramid_info["amount"] / current_price, 0, f"止损拦截加仓第{pyramid_info['layer']}层", is_swap=self.config.use_swap, leverage=float(self.config.long_leverage) if self.config.use_swap else 1.0, total_value=pyramid_info["amount"])
                                        actions.append({
                                            "coin": coin,
                                            "action": "buy",
                                            "current_price": current_price,
                                            "entry_price": entry_price,
                                            "amount": pyramid_info["amount"],
                                            "reason": sell_signal.get("pyramid_reason", "止损拦截加仓"),
                                            "is_simulation": True,
                                            "pyramid_layer": pyramid_info["layer"]
                                        })
                                else:
                                    logger.info(f"[模拟] 建议止损拦截加仓但条件不满足: {pyramid_info['reason']}")
                            else:
                                # 正常卖出逻辑
                                trade = simulation_manager.sell(
                                    coin=coin,
                                    price=current_price,
                                    sell_percent=sell_signal["sell_percent"],
                                    reason=sell_signal["reason"]
                                )
                                # 移除持仓入场时间记录
                                if coin in self.position_entry_times:
                                    del self.position_entry_times[coin]
                                
                                # 止损后重置金字塔层级（如果配置启用且是止损卖出）
                                if (self.config.reset_pyramid_on_stop_loss and 
                                    sell_signal["sell_percent"] >= 1.0 and
                                    ("止损" in sell_signal["reason"] or "stop" in sell_signal["reason"].lower())):
                                    simulation_manager.reset_pyramid_layers(coin)
                                    logger.info(f"🔄 {coin} 止损卖出，金字塔层级已重置")

                                if trade:
                                    # 同步记录到 trade_stats
                                    sell_record = TradeRecord(
                                        coin=coin,
                                        action="sell",
                                        price=current_price,
                                        amount=trade.amount,
                                        reason=sell_signal["reason"],
                                        time=datetime.now(BEIJING_TZ).isoformat(),
                                        pnl=trade.pnl_percent,
                                        side="long",
                                        is_swap=self.config.use_swap,
                                        leverage=float(self.config.long_leverage) if self.config.use_swap else 1.0,
                                        is_simulation=True
                                    )
                                    trade_stats.record_trade(sell_record)
                                    
                                    # 记录减仓价格（用于回调加仓条件检查）
                                    if sell_signal["sell_percent"] < 100:
                                        self._record_reduce_position_price(coin, current_price, sell_signal["reason"])
                                    
                                    logger.info(f"[模拟] 卖出 {coin} @ {current_price}, {sell_signal['reason']}")
                                    self._log(f"[模拟] 卖出 {coin} @ {current_price}, 收益{trade.pnl_percent:.2f}%", "success")
                                    # 飞书通知
                                    await feishu_notifier.notify_trade("sell", coin, current_price, trade.amount, trade.pnl_percent, sell_signal["reason"], is_swap=self.config.use_swap, leverage=float(self.config.long_leverage) if self.config.use_swap else 1.0, total_value=trade.amount * current_price)

                                    actions.append({
                                        "coin": coin,
                                        "action": "sell",
                                        "current_price": current_price,
                                        "entry_price": entry_price,
                                        "pnl_percent": trade.pnl_percent,
                                        "amount": trade.amount,
                                        "reason": sell_signal["reason"],
                                        "is_simulation": True
                                    })

                    except Exception as e:
                        logger.error(f"检查模拟持仓 {coin} 失败: {e}")

        except Exception as e:
            logger.error(f"模拟持仓检查失败: {e}")

        return actions


class TradingScheduler:
    def __init__(self, engine: TradingEngine, interval_minutes: int = 5):
        self.engine = engine
        self.interval_minutes = interval_minutes
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    async def _run_periodic(self, dry_run: bool = True):
        while self.running:
            try:
                await self.engine.run_trading_cycle(dry_run=dry_run)
            except Exception as e:
                logger.error(f"交易周期执行失败: {e}")
            
            await asyncio.sleep(self.interval_minutes * 60)
    
    def start(self, dry_run: bool = True):
        if self.running:
            return
        self.running = True
        self._task = asyncio.create_task(self._run_periodic(dry_run))
        logger.info(f"交易调度器已启动，间隔 {self.interval_minutes} 分钟")
    
    def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
        logger.info("交易调度器已停止")


trading_engine = TradingEngine()
trading_scheduler = TradingScheduler(trading_engine, interval_minutes=5)
