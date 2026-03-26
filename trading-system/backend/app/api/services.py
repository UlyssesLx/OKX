from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from pathlib import Path
import json

from app.services.sentiment_service import sentiment_service
from app.services.strategy_evolution import strategy_evolution, StrategyParams
from app.services.blacklist_manager import blacklist_manager
from app.services.trade_stats import trade_stats, TradeRecord
from app.services.band_trade_manager import band_trade_manager
from app.services.position_manager import position_manager
from app.services.trading_engine import trading_engine
from app.services.coordinator import coordinator
from app.strategies.grid_trading import grid_trading_strategy
from app.strategies.trend_trading import trend_trading_strategy
from app.strategies.smart_grid import smart_grid_strategy
from app.strategies.sparrow_config import sparrow_config, get_default_config, SparrowConfig

router = APIRouter(prefix="/api/v1/services", tags=["services"])

SETTINGS_FILE = Path("settings.json")
SPARROW_CONFIG_FILE = Path("sparrow_config.json")

DEFAULT_SETTINGS = {
    "tradingMode": "simulation",
    "useSwap": False,
    "longLeverage": 3,
    "shortLeverage": 3,
    "strategyVersion": "sparrow",
    "timeStop": 48,
    "minTrendScore": 5,
    "minResonanceScore": 6,
    "minVolatility": 0.3,
    "maxVolatility": 5.0,
    "maxDailyTrades": 5,
    "maxDailyLoss": 5,
    "minCashReserve": 30,
    "minCapitalFlowScore": 6,
    "minVolumeRatio": 0.8
}

def load_settings():
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
        except:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings_file(settings: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


class SentimentResponse(BaseModel):
    coin: str
    coingecko: Optional[dict]
    news: Optional[dict]
    combined_score: int
    timestamp: str


class EvolutionResponse(BaseModel):
    paused: bool
    params: dict
    performance: Optional[dict] = None
    version: Optional[str] = None
    iterations_count: Optional[int] = None
    total_trades: Optional[int] = None
    wins: Optional[int] = None
    losses: Optional[int] = None
    consecutive_losses: Optional[int] = None
    last_trade_time: Optional[str] = None


class BlacklistResponse(BaseModel):
    stopped_out: List[str]
    manual_ban: List[str]
    stablecoins: List[str]
    total_count: int


class StatsResponse(BaseModel):
    summary: dict
    coin_stats: dict
    today: dict
    last_updated: str


class SignalResponse(BaseModel):
    type: str
    coin: str
    price: float
    reason: str
    urgency: str
    score: int
    timestamp: str


class BandPositionResponse(BaseModel):
    coin: str
    entry_price: float
    current_amount: float
    original_amount: float
    highest_price: float
    take_profit_executed: List[int]
    callback_buy_count: int
    trailing_stop_activated: bool
    remaining_percent: float


@router.get("/settings")
async def get_settings():
    settings = load_settings()
    
    # 同步设置到交易引擎（确保重启后配置一致）
    from app.services.trading_engine import trading_engine
    if "useSwap" in settings:
        trading_engine.config.use_swap = settings["useSwap"]
    if "longLeverage" in settings:
        trading_engine.config.long_leverage = settings["longLeverage"]
    if "shortLeverage" in settings:
        trading_engine.config.short_leverage = settings["shortLeverage"]
    
    return settings


@router.post("/settings")
async def update_settings(settings: dict):
    save_settings_file(settings)
    
    # 同步更新交易引擎配置
    from app.services.trading_engine import trading_engine
    if "useSwap" in settings:
        trading_engine.config.use_swap = settings["useSwap"]
    if "longLeverage" in settings:
        trading_engine.config.long_leverage = settings["longLeverage"]
    if "shortLeverage" in settings:
        trading_engine.config.short_leverage = settings["shortLeverage"]
    
    return {"success": True, "settings": settings}


@router.get("/sentiment/{coin}", response_model=SentimentResponse)
async def get_sentiment(coin: str):
    data = await sentiment_service.get_combined_sentiment(coin.upper())
    return SentimentResponse(**data)


@router.get("/evolution/params")
async def get_evolution_params():
    try:
        from app.services.trading_engine import trading_engine
        return {
            "long": {
                "stop_loss": trading_engine.config.stop_loss_trend_8_plus,
                "take_profit": trading_engine.config.take_profit_trend_9_10,
                "max_positions": trading_engine.config.long_max_positions,
                "trade_size": trading_engine.config.long_position_size,
                "sentiment_threshold": trading_engine.config.sentiment_threshold
            },
            "short": {
                "stop_loss": -trading_engine.config.short_stop_loss_percent,
                "take_profit": trading_engine.config.short_take_profit_percent,
                "max_positions": trading_engine.config.short_max_positions,
                "trade_size": trading_engine.config.short_position_size,
                "sentiment_threshold": trading_engine.config.short_sentiment_threshold
            }
        }
    except (ImportError, AttributeError):
        params = strategy_evolution.get_current_params()
        return {
            "long": params.long.model_dump(),
            "short": params.short.model_dump()
        }


@router.post("/evolution/params")
async def update_evolution_params(params_data: dict):
    try:
        from app.services.trading_engine import trading_engine
        if "long" in params_data:
            long_params = params_data["long"]
            trading_engine.config.stop_loss_trend_8_plus = long_params.get("stop_loss", -3.0)
            trading_engine.config.take_profit_trend_9_10 = long_params.get("take_profit", 15.0)
            trading_engine.config.long_max_positions = long_params.get("max_positions", 5)
            trading_engine.config.long_position_size = long_params.get("trade_size", 60.0)
            trading_engine.config.sentiment_threshold = long_params.get("sentiment_threshold", 7)
        if "short" in params_data:
            short_params = params_data["short"]
            trading_engine.config.short_stop_loss_percent = abs(short_params.get("stop_loss", 3.0))
            trading_engine.config.short_take_profit_percent = short_params.get("take_profit", 6.0)
            trading_engine.config.short_max_positions = short_params.get("max_positions", 1)
            trading_engine.config.short_position_size = short_params.get("trade_size", 40.0)
            trading_engine.config.short_sentiment_threshold = short_params.get("sentiment_threshold", 3)
    except (ImportError, AttributeError):
        pass

    from app.services.strategy_evolution import StrategyParams, LongShortParams
    if "long" in params_data:
        strategy_evolution.log.current_params.long = StrategyParams(**params_data["long"])
    if "short" in params_data:
        strategy_evolution.log.current_params.short = StrategyParams(**params_data["short"])
    strategy_evolution._save_log()
    return {"success": True, "params": {
        "long": strategy_evolution.log.current_params.long.model_dump(),
        "short": strategy_evolution.log.current_params.short.model_dump()
    }}


@router.get("/evolution/status", response_model=EvolutionResponse)
async def get_evolution_status():
    status = strategy_evolution.get_status()
    params = strategy_evolution.get_current_params()
    return EvolutionResponse(
        paused=status["is_paused"],
        params=params.model_dump(),
        version=status["version"],
        iterations_count=status["iterations_count"],
        total_trades=status["total_trades"],
        wins=status["wins"],
        losses=status["losses"],
        consecutive_losses=status["consecutive_losses"],
        last_trade_time=status["last_trade_time"]
    )


@router.get("/evolution/history")
async def get_evolution_history(limit: int = 20):
    """获取策略进化历史记录"""
    from app.services.strategy_evolution import EvolutionIteration
    history = strategy_evolution.log.iterations
    # 返回最近的 N 条记录
    recent_history = history[-limit:] if len(history) > limit else history
    return {
        "version": strategy_evolution.log.version,
        "total_iterations": len(history),
        "iterations": [
            {
                "version": iter.version,
                "date": iter.date,
                "trigger": iter.trigger,
                "changes": iter.changes,
                "params_before": iter.params_before,
                "params_after": iter.params_after,
                "performance": iter.performance
            }
            for iter in recent_history
        ]
    }


@router.get("/evolution/iterations")
async def get_evolution_iterations():
    """获取所有进化迭代详情"""
    return {
        "version": strategy_evolution.log.version,
        "iterations": strategy_evolution.log.iterations
    }


@router.get("/evolution/config")
async def get_evolution_config():
    """获取策略进化配置参数"""
    config = strategy_evolution.config
    return {
        "min_trades_for_review": config.min_trades_for_review,
        "consecutive_loss_threshold": config.consecutive_loss_threshold,
        "win_rate_high": config.win_rate_high,
        "win_rate_low": config.win_rate_low,
        "pause_after_losses_hours": config.pause_after_losses_hours
    }


@router.post("/evolution/config")
async def update_evolution_config(config_data: dict):
    """更新策略进化配置参数"""
    config = strategy_evolution.config
    if "min_trades_for_review" in config_data:
        config.min_trades_for_review = config_data["min_trades_for_review"]
    if "consecutive_loss_threshold" in config_data:
        config.consecutive_loss_threshold = config_data["consecutive_loss_threshold"]
    if "win_rate_high" in config_data:
        config.win_rate_high = config_data["win_rate_high"]
    if "win_rate_low" in config_data:
        config.win_rate_low = config_data["win_rate_low"]
    if "pause_after_losses_hours" in config_data:
        config.pause_after_losses_hours = config_data["pause_after_losses_hours"]
    return {"success": True, "config": {
        "min_trades_for_review": config.min_trades_for_review,
        "consecutive_loss_threshold": config.consecutive_loss_threshold,
        "win_rate_high": config.win_rate_high,
        "win_rate_low": config.win_rate_low,
        "pause_after_losses_hours": config.pause_after_losses_hours
    }}


@router.get("/blacklist", response_model=BlacklistResponse)
async def get_blacklist():
    summary = blacklist_manager.get_blacklist_summary()
    return BlacklistResponse(
        stopped_out=summary["stopped_out"],
        manual_ban=summary["manual_ban"],
        stablecoins=summary["stablecoins"],
        total_count=summary["total_count"]
    )


@router.post("/blacklist/{coin}")
async def add_to_blacklist(coin: str, reason: str = "手动添加"):
    blacklist_manager.add_to_blacklist(coin.upper(), reason)
    return {"success": True, "coin": coin.upper(), "reason": reason}


@router.delete("/blacklist/{coin}")
async def remove_from_blacklist(coin: str):
    removed = blacklist_manager.remove_from_blacklist(coin.upper())
    if not removed:
        raise HTTPException(status_code=404, detail="币种不在黑名单中")
    return {"success": True, "coin": coin.upper()}


@router.get("/stats", response_model=StatsResponse)
async def get_trade_stats():
    stats = trade_stats.calculate_stats()
    if not stats:
        return StatsResponse(
            summary={"total_trades": 0, "buy_count": 0, "sell_count": 0, "win_count": 0, "loss_count": 0, "win_rate": 0, "avg_profit": 0, "avg_loss": 0},
            coin_stats={},
            today={"trades": 0, "profit": 0},
            last_updated=""
        )
    return StatsResponse(**stats)


@router.get("/stats/report")
async def get_stats_report():
    report = trade_stats.generate_report()
    return {"report": report}


@router.post("/stats/trade")
async def record_trade(trade: TradeRecord):
    trade_stats.record_trade(trade)
    return {"success": True, "trade": trade.model_dump()}


@router.get("/stats/recent")
async def get_recent_trades(limit: int = 20):
    trades = trade_stats.get_recent_trades(limit)
    return [t.model_dump() for t in trades]


@router.get("/bandtrade/positions")
async def get_band_positions():
    positions = band_trade_manager.get_all_positions()
    return positions


@router.get("/bandtrade/position/{coin}")
async def get_band_position(coin: str):
    summary = band_trade_manager.get_position_summary(coin.upper())
    if not summary:
        raise HTTPException(status_code=404, detail="仓位不存在")
    return summary


@router.post("/bandtrade/position/{coin}")
async def add_band_position(coin: str, entry_price: float, amount: float):
    band_trade_manager.add_position(coin.upper(), entry_price, amount)
    return {"success": True, "coin": coin.upper()}


@router.delete("/bandtrade/position/{coin}")
async def remove_band_position(coin: str):
    band_trade_manager.remove_position(coin.upper())
    return {"success": True, "coin": coin.upper()}


@router.get("/bandtrade/config")
async def get_band_config():
    return band_trade_manager.config.model_dump()


@router.post("/bandtrade/config")
async def update_band_config(config: dict):
    updated = band_trade_manager.update_config(config)
    return {"success": True, "config": updated.model_dump()}


from app.services.coordinator import coordinator
from app.services.trading_engine import trading_engine
from app.strategies.enhanced import emergency_stop, sideways_manager


class CoordinatorStatusResponse(BaseModel):
    is_running: bool
    last_cycle_time: Optional[str]
    total_cycles: int
    errors: List[str]
    trading_enabled: bool


class EmergencyStopResponse(BaseModel):
    is_stopped: bool
    reason: Optional[str] = None
    stopped_at: Optional[str] = None


@router.get("/coordinator/status", response_model=CoordinatorStatusResponse)
async def get_coordinator_status():
    status = coordinator.get_status()
    return CoordinatorStatusResponse(
        is_running=status.is_running,
        last_cycle_time=status.last_cycle_time.isoformat() if status.last_cycle_time else None,
        total_cycles=status.total_cycles,
        errors=status.errors,
        trading_enabled=status.trading_enabled
    )


@router.post("/coordinator/start")
async def start_coordinator(dry_run: bool = True):
    """启动协调器，检查间隔由时区感知配置统一管理"""
    from app.config.sparrow_config import sparrow_config, get_check_interval, get_current_time_zone
    
    # 使用配置的默认间隔（安静时段）作为基础间隔
    base_interval = get_check_interval(sparrow_config)
    coordinator.start(interval_minutes=base_interval, dry_run=dry_run)
    
    current_tz = get_current_time_zone()
    if sparrow_config.timezone_aware_enabled:
        return {
            "success": True, 
            "message": f"协调器已启动，当前时段: {current_tz}，检查间隔: {base_interval}分钟（时区感知已启用）"
        }
    else:
        return {
            "success": True, 
            "message": f"协调器已启动，检查间隔: {base_interval}分钟（时区感知已禁用）"
        }


@router.post("/coordinator/stop")
async def stop_coordinator():
    coordinator.stop()
    return {"success": True, "message": "协调器已停止"}


@router.post("/coordinator/cycle")
async def run_single_cycle(dry_run: bool = True):
    result = await coordinator.run_single_cycle(dry_run=dry_run)
    return result


@router.delete("/coordinator/errors")
async def clear_coordinator_errors():
    """清除协调器的错误列表"""
    coordinator.clear_errors()
    return {"success": True, "message": "错误列表已清除"}


@router.get("/emergency-stop", response_model=EmergencyStopResponse)
async def get_emergency_stop_status():
    is_stopped = emergency_stop.is_stopped()
    info = emergency_stop.get_stop_info() if is_stopped else None
    return EmergencyStopResponse(
        is_stopped=is_stopped,
        reason=info.get("reason") if info else None,
        stopped_at=info.get("stopped_at") if info else None
    )


@router.post("/emergency-stop")
async def trigger_emergency_stop(reason: str = "API触发"):
    success = coordinator.emergency_stop(reason)
    return {"success": success, "reason": reason}


@router.delete("/emergency-stop")
async def clear_emergency_stop():
    success = coordinator.resume()
    return {"success": success}


@router.get("/sideways/status")
async def get_sideways_status():
    return sideways_manager.status


@router.delete("/sideways/{coin}")
async def reset_sideways(coin: str):
    sideways_manager.reset(coin.upper())
    return {"success": True, "coin": coin.upper()}


@router.delete("/sideways")
async def reset_all_sideways():
    coordinator.reset_sideways()
    return {"success": True, "message": "所有横盘状态已重置"}


# 扫描过滤配置 API
@router.get("/trading/scan-config")
async def get_scan_config():
    """获取市场扫描过滤配置"""
    return trading_engine.get_scan_filter_config()


@router.post("/trading/scan-config")
async def update_scan_config(config: dict):
    """更新市场扫描过滤配置"""
    trading_engine.update_scan_filter_config(config)
    return {"success": True, "config": trading_engine.get_scan_filter_config()}


# 统一持仓管理 API - 废弃，改用 trading_engine 统一配置
@router.get("/position/config")
async def get_position_config():
    """获取止盈止损配置 - 从 trading_engine 读取"""
    from app.services.trading_engine import trading_engine
    return {
        "stop_loss_percent": trading_engine.config.stop_loss_percent,
        "take_profit_percent": trading_engine.config.take_profit_percent,
        "trailing_stop_enabled": True,
        "trailing_stop_trigger": 3.0,
        "trailing_stop_distance": 1.5,
        "time_stop_hours": trading_engine.config.time_stop_hours,
        "dynamic_bands_enabled": trading_engine.config.dynamic_bands_enabled
    }


@router.post("/position/config")
async def update_position_config(config: dict):
    """更新止盈止损配置 - 统一到 trading_engine"""
    from app.services.trading_engine import trading_engine

    # 更新 trading_engine 配置
    if "stop_loss_percent" in config:
        trading_engine.config.stop_loss_percent = config["stop_loss_percent"]
    if "take_profit_percent" in config:
        trading_engine.config.take_profit_percent = config["take_profit_percent"]
    if "time_stop_hours" in config:
        trading_engine.config.time_stop_hours = config["time_stop_hours"]
    if "dynamic_bands_enabled" in config:
        trading_engine.config.dynamic_bands_enabled = config["dynamic_bands_enabled"]

    # 保存到持久化文件
    trading_engine._save_persistent_state()

    return {"success": True, "config": await get_position_config()}


@router.get("/position/all")
async def get_all_positions():
    """获取所有持仓"""
    positions = position_manager.get_all_positions()
    return {
        "positions": {
            k: {
                "coin": v.coin,
                "entry_price": v.entry_price,
                "amount": v.amount,
                "stop_loss": v.stop_loss,
                "take_profit": v.take_profit,
                "trailing_activated": v.trailing_activated,
                "trailing_stop_price": v.trailing_stop_price,
                "highest_price": v.highest_price,
                "layers": v.layers,
                "total_invested": v.total_invested,
                "entry_time": v.entry_time
            } for k, v in positions.items()
        },
        "count": len(positions)
    }


@router.delete("/position/{coin}")
async def remove_position(coin: str):
    """移除持仓"""
    position_manager.remove_position(coin.upper())
    return {"success": True, "coin": coin.upper()}


@router.delete("/position")
async def clear_all_positions():
    """清空所有持仓"""
    position_manager.reset()
    return {"success": True, "message": "所有持仓已清空"}


# v4.2 核心功能配置 API
V42_FEATURES_FILE = Path("data/v42_features.json")

DEFAULT_V42_FEATURES = {
    "timezone_aware": True,
    "timezone_adjusted_position": True,
    "decreasing_buy_enabled": True,
    "decreasing_buy_factors": [1.0, 0.6, 0.35, 0.2],
    "over_position_exemption_enabled": True,
    "exemption_loss_high": 60,
    "exemption_loss_medium": 45,
    "exemption_profit": 30,
    "dynamic_bands_enabled": True
}


def load_v42_features():
    """加载 v4.2 功能配置"""
    V42_FEATURES_FILE.parent.mkdir(exist_ok=True)
    if V42_FEATURES_FILE.exists():
        try:
            with open(V42_FEATURES_FILE, "r", encoding="utf-8") as f:
                return {**DEFAULT_V42_FEATURES, **json.load(f)}
        except Exception as e:
            print(f"加载 v4.2 功能配置失败: {e}")
    return DEFAULT_V42_FEATURES.copy()


def save_v42_features(features: dict):
    """保存 v4.2 功能配置"""
    V42_FEATURES_FILE.parent.mkdir(exist_ok=True)
    with open(V42_FEATURES_FILE, "w", encoding="utf-8") as f:
        json.dump(features, f, indent=2, ensure_ascii=False)


@router.get("/v42-features")
async def get_v42_features():
    """获取 v4.2 核心功能配置"""
    return load_v42_features()


@router.post("/v42-features")
async def update_v42_features(config: dict):
    """更新 v4.2 核心功能配置"""
    features = load_v42_features()
    features.update(config)
    save_v42_features(features)

    # 更新交易引擎配置
    if "timezone_aware" in features:
        trading_engine.config.timezone_aware_enabled = features["timezone_aware"]
    if "timezone_adjusted_position" in features:
        trading_engine.config.timezone_adjusted_position = features["timezone_adjusted_position"]
    if "decreasing_buy_enabled" in features:
        trading_engine.config.decreasing_buy_enabled = features["decreasing_buy_enabled"]
    if "decreasing_buy_factors" in features:
        trading_engine.config.decreasing_buy_factors = features["decreasing_buy_factors"]
    if "over_position_exemption_enabled" in features:
        trading_engine.config.over_position_exemption_enabled = features["over_position_exemption_enabled"]
    if "exemption_loss_high" in features:
        trading_engine.config.exemption_loss_high = features["exemption_loss_high"]
    if "exemption_loss_medium" in features:
        trading_engine.config.exemption_loss_medium = features["exemption_loss_medium"]
    if "exemption_profit" in features:
        trading_engine.config.exemption_profit = features["exemption_profit"]

    return {"success": True, "features": features}


@router.get("/trading/scan")
async def scan_market():
    opportunities = await trading_engine.scan_market()
    return {"opportunities": opportunities, "count": len(opportunities)}


@router.post("/trading/execute")
async def execute_trading(dry_run: bool = True):
    result = await trading_engine.run_trading_cycle(dry_run=dry_run)
    return result


@router.get("/grid/status")
async def get_grid_status():
    return grid_trading_strategy.get_status()


@router.post("/grid/add")
async def add_grid(name: str, inst_id: str, min_price: float, max_price: float, grid_num: int = 10, investment: float = 40.0, enable_short: bool = False):
    from app.strategies.grid_trading import GridConfig
    config = GridConfig(
        inst_id=inst_id,
        min_price=min_price,
        max_price=max_price,
        grid_num=grid_num,
        investment=investment,
        enable_short=enable_short
    )
    grid_trading_strategy.add_grid(name, config)
    return {"success": True, "message": f"网格 {name} 已添加"}


@router.delete("/grid/{name}")
async def remove_grid(name: str):
    grid_trading_strategy.remove_grid(name)
    return {"success": True, "message": f"网格 {name} 已移除"}


@router.post("/grid/run")
async def run_grid_cycle():
    from app.core.okx_client import okx_client
    results = await grid_trading_strategy.run_cycle(okx_client)
    return results


@router.get("/trendstrategy/status")
async def get_trend_status():
    return trend_trading_strategy.get_status()


@router.post("/trendstrategy/run")
async def run_trend_cycle():
    from app.core.okx_client import okx_client
    results = await trend_trading_strategy.run_cycle(okx_client)
    return results


@router.get("/simulation/balance")
async def get_simulation_balance():
    """获取模拟持仓初始金额"""
    from app.services.simulation_manager import simulation_manager
    return {
        "initial_balance": simulation_manager.initial_balance,
        "available_balance": simulation_manager.available_balance
    }


@router.post("/simulation/balance")
async def set_simulation_balance(config: dict):
    """设置模拟持仓初始金额并重置"""
    from app.services.simulation_manager import simulation_manager
    initial_balance = config.get("initial_balance", 1000.0)
    simulation_manager.reset_balance(initial_balance)
    return {
        "success": True,
        "initial_balance": initial_balance,
        "available_balance": initial_balance
    }


@router.get("/smartgrid/status")
async def get_smartgrid_status():
    return smart_grid_strategy.get_status()


@router.post("/smartgrid/add")
async def add_smartgrid(name: str, inst_id: str, min_price: float, max_price: float, grid_num: int = 20, investment: float = 40.0):
    from app.strategies.smart_grid import SmartGridConfig
    config = SmartGridConfig(
        inst_id=inst_id,
        min_price=min_price,
        max_price=max_price,
        grid_num=grid_num,
        investment=investment
    )
    smart_grid_strategy.add_grid(name, config)
    return {"success": True, "message": f"智能网格 {name} 已添加"}


@router.delete("/smartgrid/{name}")
async def remove_smartgrid(name: str):
    smart_grid_strategy.remove_grid(name)
    return {"success": True, "message": f"智能网格 {name} 已移除"}


# 智能交易配置 API
SMART_TRADING_CONFIG_FILE = Path("smart_trading_config.json")

# 默认配置（与示例项目一致）
DEFAULT_SMART_TRADING_CONFIG = {
    "pyramid_enabled": True,
    "pyramid_max_layers": 3,
    "pyramid_drop_threshold": -5.0,
    "pyramid_drop_per_layer": -10.0,
    "pyramid_min_trend_score": 6,
    "pyramid_base_amount": 25.0,
    "pyramid_layer_ratios": "1.0,0.6,0.35",
    "pyramid_max_position_percent": 15.0,
    "pyramid_min_cash": 15.0,
    # 止损拦截加仓配置
    "pyramid_on_stop_loss_enabled": True,
    "pyramid_on_stop_loss_trend_score": 8,
    "pyramid_on_stop_loss_max_position_percent": 15.0,
    "pyramid_on_stop_loss_min_cash": 25.0,
    # 智能止损配置
    "smart_stop_loss_enabled": True,
    "stop_loss_trend_8_plus": -3.0,
    "stop_loss_trend_6_7": -2.0,
    "stop_loss_trend_default": -1.5,
    "stop_loss_time_protection_enabled": True,
    "stop_loss_time_protection_minutes": 60,
    # 动态止盈配置
    "dynamic_take_profit_enabled": True,
    "take_profit_trend_9_10": 15.0,
    "take_profit_trend_7_8": 10.0,
    "take_profit_trend_5_6": 8.0,
    "take_profit_trend_default": 6.0,
    "partial_take_profit_percent": 0.5,
    # 时间衰减配置
    "time_decay_enabled": True,
    "time_decay_factor": 0.1,
    # 小盈减仓配置
    "small_profit_reduce_enabled": True,
    "small_profit_reduce_threshold_percent": 50.0,
    "small_profit_reduce_position_threshold": 15.0,
    # 超仓减仓配置
    "over_position_reduce_enabled": True,
    "over_position_reduce_threshold": 30.0,
    "over_position_reduce_target": 20.0,
    # 智能豁免期配置
    "over_position_exemption_enabled": True,
    "exemption_loss_high_minutes": 60,
    "exemption_loss_medium_minutes": 45,
    "exemption_profit_minutes": 30,
    # 波段操作配置
    "band_trade_enabled": True,
    "band_trade_reduce_at": 1.5,
    "band_trade_second_reduce_at": 3.0,
    "band_trade_final_reduce_at": 6.0,
    "band_trade_reduce_percent": 30.0,
    "band_trade_second_reduce_percent": 50.0,
    "band_trade_buy_back_at": -2.0,
    # 技术面验证配置
    "technical_validation_enabled": True,
    "technical_min_pass_count": 2,
    "technical_trend_score_threshold": 5,
    "technical_rsi_min": 30.0,
    "technical_rsi_max": 80.0,
    "technical_volume_ratio_min": 0.8,
    "technical_ma5_tolerance": 0.98,
    "technical_volatility_min": 0.2
}


def load_smart_trading_config():
    """加载智能交易配置"""
    if SMART_TRADING_CONFIG_FILE.exists():
        try:
            with open(SMART_TRADING_CONFIG_FILE, "r", encoding="utf-8") as f:
                return {**DEFAULT_SMART_TRADING_CONFIG, **json.load(f)}
        except:
            pass
    return DEFAULT_SMART_TRADING_CONFIG.copy()


def save_smart_trading_config_file(config: dict):
    """保存智能交易配置"""
    with open(SMART_TRADING_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    # 更新配置到 settings.py（通过环境变量）
    import os
    os.environ["PYRAMID_ENABLED"] = str(config["pyramid_enabled"])
    os.environ["PYRAMID_MAX_LAYERS"] = str(config["pyramid_max_layers"])
    os.environ["PYRAMID_DROP_THRESHOLD"] = str(config["pyramid_drop_threshold"])
    os.environ["PYRAMID_DROP_PER_LAYER"] = str(config["pyramid_drop_per_layer"])
    os.environ["PYRAMID_MIN_TREND_SCORE"] = str(config["pyramid_min_trend_score"])
    os.environ["PYRAMID_BASE_AMOUNT"] = str(config["pyramid_base_amount"])
    os.environ["PYRAMID_LAYER_RATIOS"] = str(config["pyramid_layer_ratios"])
    os.environ["PYRAMID_MAX_POSITION_PERCENT"] = str(config["pyramid_max_position_percent"])
    # 止损拦截加仓配置
    os.environ["PYRAMID_ON_STOP_LOSS_ENABLED"] = str(config.get("pyramid_on_stop_loss_enabled", True))
    os.environ["PYRAMID_ON_STOP_LOSS_TREND_SCORE"] = str(config.get("pyramid_on_stop_loss_trend_score", 8))
    os.environ["PYRAMID_ON_STOP_LOSS_MAX_POSITION_PERCENT"] = str(config.get("pyramid_on_stop_loss_max_position_percent", 15.0))
    os.environ["PYRAMID_ON_STOP_LOSS_MIN_CASH"] = str(config.get("pyramid_on_stop_loss_min_cash", 25.0))
    os.environ["SMART_STOP_LOSS_ENABLED"] = str(config["smart_stop_loss_enabled"])
    os.environ["STOP_LOSS_TREND_8_PLUS"] = str(config["stop_loss_trend_8_plus"])
    os.environ["STOP_LOSS_TREND_6_7"] = str(config["stop_loss_trend_6_7"])
    os.environ["STOP_LOSS_TREND_DEFAULT"] = str(config["stop_loss_trend_default"])
    os.environ["STOP_LOSS_TIME_PROTECTION_MINUTES"] = str(config["stop_loss_time_protection_minutes"])
    os.environ["DYNAMIC_TAKE_PROFIT_ENABLED"] = str(config["dynamic_take_profit_enabled"])
    os.environ["TAKE_PROFIT_TREND_9_10"] = str(config["take_profit_trend_9_10"])
    os.environ["TAKE_PROFIT_TREND_7_8"] = str(config["take_profit_trend_7_8"])
    os.environ["TAKE_PROFIT_TREND_5_6"] = str(config["take_profit_trend_5_6"])
    os.environ["TAKE_PROFIT_TREND_DEFAULT"] = str(config["take_profit_trend_default"])
    os.environ["PARTIAL_TAKE_PROFIT_PERCENT"] = str(config["partial_take_profit_percent"])
    
    # 技术面验证配置
    os.environ["TECHNICAL_VALIDATION_ENABLED"] = str(config.get("technical_validation_enabled", True))
    os.environ["TECHNICAL_MIN_PASS_COUNT"] = str(config.get("technical_min_pass_count", 2))
    os.environ["TECHNICAL_TREND_SCORE_THRESHOLD"] = str(config.get("technical_trend_score_threshold", 5))
    os.environ["TECHNICAL_RSI_MIN"] = str(config.get("technical_rsi_min", 30.0))
    os.environ["TECHNICAL_RSI_MAX"] = str(config.get("technical_rsi_max", 80.0))
    os.environ["TECHNICAL_VOLUME_RATIO_MIN"] = str(config.get("technical_volume_ratio_min", 0.8))
    os.environ["TECHNICAL_MA5_TOLERANCE"] = str(config.get("technical_ma5_tolerance", 0.98))
    os.environ["TECHNICAL_VOLATILITY_MIN"] = str(config.get("technical_volatility_min", 0.2))

    # 更新 simulation_manager 的配置（需要重新加载）
    from app.services.simulation_manager import simulation_manager
    from app.core.config import settings

    # 更新配置
    settings.PYRAMID_ENABLED = config["pyramid_enabled"]
    settings.PYRAMID_MAX_LAYERS = config["pyramid_max_layers"]
    settings.PYRAMID_DROP_THRESHOLD = config["pyramid_drop_threshold"]
    settings.PYRAMID_DROP_PER_LAYER = config["pyramid_drop_per_layer"]
    settings.PYRAMID_MIN_TREND_SCORE = config["pyramid_min_trend_score"]
    settings.PYRAMID_BASE_AMOUNT = config["pyramid_base_amount"]
    settings.PYRAMID_LAYER_RATIOS = config["pyramid_layer_ratios"]
    settings.PYRAMID_MAX_POSITION_PERCENT = config["pyramid_max_position_percent"]
    # 止损拦截加仓配置
    settings.PYRAMID_ON_STOP_LOSS_ENABLED = config.get("pyramid_on_stop_loss_enabled", True)
    settings.PYRAMID_ON_STOP_LOSS_TREND_SCORE = config.get("pyramid_on_stop_loss_trend_score", 8)
    settings.PYRAMID_ON_STOP_LOSS_MAX_POSITION_PERCENT = config.get("pyramid_on_stop_loss_max_position_percent", 15.0)
    settings.PYRAMID_ON_STOP_LOSS_MIN_CASH = config.get("pyramid_on_stop_loss_min_cash", 25.0)
    settings.SMART_STOP_LOSS_ENABLED = config["smart_stop_loss_enabled"]
    settings.STOP_LOSS_TREND_8_PLUS = config["stop_loss_trend_8_plus"]
    settings.STOP_LOSS_TREND_6_7 = config["stop_loss_trend_6_7"]
    settings.STOP_LOSS_TREND_DEFAULT = config["stop_loss_trend_default"]
    settings.STOP_LOSS_TIME_PROTECTION_MINUTES = config["stop_loss_time_protection_minutes"]
    settings.DYNAMIC_TAKE_PROFIT_ENABLED = config["dynamic_take_profit_enabled"]
    settings.TAKE_PROFIT_TREND_9_10 = config["take_profit_trend_9_10"]
    settings.TAKE_PROFIT_TREND_7_8 = config["take_profit_trend_7_8"]
    settings.TAKE_PROFIT_TREND_5_6 = config["take_profit_trend_5_6"]
    settings.TAKE_PROFIT_TREND_DEFAULT = config["take_profit_trend_default"]
    settings.PARTIAL_TAKE_PROFIT_PERCENT = config["partial_take_profit_percent"]
    # 技术面验证配置
    settings.TECHNICAL_VALIDATION_ENABLED = config.get("technical_validation_enabled", True)
    settings.TECHNICAL_MIN_PASS_COUNT = config.get("technical_min_pass_count", 2)
    settings.TECHNICAL_TREND_SCORE_THRESHOLD = config.get("technical_trend_score_threshold", 5)
    settings.TECHNICAL_RSI_MIN = config.get("technical_rsi_min", 30.0)
    settings.TECHNICAL_RSI_MAX = config.get("technical_rsi_max", 80.0)
    settings.TECHNICAL_VOLUME_RATIO_MIN = config.get("technical_volume_ratio_min", 0.8)
    settings.TECHNICAL_MA5_TOLERANCE = config.get("technical_ma5_tolerance", 0.98)
    settings.TECHNICAL_VOLATILITY_MIN = config.get("technical_volatility_min", 0.2)


@router.get("/config/smart-trading")
async def get_smart_trading_config():
    """获取智能交易配置"""
    config = load_smart_trading_config()
    return config


@router.post("/config/smart-trading")
async def update_smart_trading_config(config: dict):
    """更新智能交易配置"""
    save_smart_trading_config_file(config)

    # 同步配置到 trading_engine
    from app.services.trading_engine import trading_engine
    
    _direct_attrs = [
        'smart_stop_loss_enabled',
        'cooldown_score_tier1', 'cooldown_score_tier2', 'cooldown_score_tier3',
        'position_percent_score_tier1', 'position_percent_score_tier2', 'position_percent_score_tier3',
        'take_profit_score_tier1', 'take_profit_score_tier2', 'take_profit_score_tier3',
        'stop_loss_score_tier1', 'stop_loss_score_tier2',
        'bullish_fallback_threshold', 'short_bearish_fallback_threshold',
    ]
    _key_attr_map = {
        'pyramid_enabled': 'smart_pyramid_enabled',
        'pyramid_max_layers': 'smart_pyramid_max_layers',
        'pyramid_drop_threshold': 'smart_pyramid_drop_threshold',
        'pyramid_drop_per_layer': 'smart_pyramid_drop_per_layer',
        'pyramid_base_amount': 'smart_pyramid_base_amount',
        'pyramid_layer_ratios': 'smart_pyramid_layer_ratios',
        'pyramid_max_position_percent': 'smart_pyramid_max_position_percent',
        'pyramid_min_trend_score': 'smart_pyramid_min_trend_score',
        'pyramid_min_cash': 'smart_pyramid_min_cash',
    }
    for attr in _direct_attrs:
        if attr in config:
            setattr(trading_engine.config, attr, config[attr])
    for key, attr in _key_attr_map.items():
        if key in config:
            setattr(trading_engine.config, attr, config[key])

    import os
    from app.services.notification_agent import feishu_notifier
    feishu_app_id = os.getenv("FEISHU_APP_ID", "")
    feishu_app_secret = os.getenv("FEISHU_APP_SECRET", "")
    feishu_chat_id = os.getenv("FEISHU_CHAT_ID", "")
    feishu_enabled = os.getenv("FEISHU_NOTIFICATION_ENABLED", "true").lower() == "true"
    if feishu_app_id and feishu_app_secret:
        feishu_notifier.configure(
            app_id=feishu_app_id,
            app_secret=feishu_app_secret,
            enabled=feishu_enabled,
            chat_id=feishu_chat_id
        )

    if "stop_loss_trend_8_plus" in config:
        trading_engine.config.stop_loss_trend_8_plus = config["stop_loss_trend_8_plus"]
    if "stop_loss_trend_6_7" in config:
        trading_engine.config.stop_loss_trend_6_7 = config["stop_loss_trend_6_7"]
    if "stop_loss_trend_default" in config:
        trading_engine.config.stop_loss_trend_default = config["stop_loss_trend_default"]
    if "stop_loss_time_protection_enabled" in config:
        trading_engine.config.stop_loss_time_protection_enabled = config["stop_loss_time_protection_enabled"]
    if "stop_loss_time_protection_minutes" in config:
        trading_engine.config.stop_loss_time_protection_minutes = config["stop_loss_time_protection_minutes"]

    if "dynamic_take_profit_enabled" in config:
        trading_engine.config.dynamic_take_profit_enabled = config["dynamic_take_profit_enabled"]
    if "take_profit_trend_9_10" in config:
        trading_engine.config.take_profit_trend_9_10 = config["take_profit_trend_9_10"]
    if "take_profit_trend_7_8" in config:
        trading_engine.config.take_profit_trend_7_8 = config["take_profit_trend_7_8"]
    if "take_profit_trend_5_6" in config:
        trading_engine.config.take_profit_trend_5_6 = config["take_profit_trend_5_6"]
    if "take_profit_trend_default" in config:
        trading_engine.config.take_profit_trend_default = config["take_profit_trend_default"]
    if "partial_take_profit_percent" in config:
        trading_engine.config.partial_take_profit_percent = config["partial_take_profit_percent"]

    if "time_decay_enabled" in config:
        trading_engine.config.time_decay_enabled = config["time_decay_enabled"]
    if "time_decay_factor" in config:
        trading_engine.config.time_decay_factor = config["time_decay_factor"]

    if "small_profit_reduce_enabled" in config:
        trading_engine.config.small_profit_reduce_enabled = config["small_profit_reduce_enabled"]
    if "small_profit_reduce_threshold_percent" in config:
        trading_engine.config.small_profit_reduce_threshold_percent = config["small_profit_reduce_threshold_percent"]
    if "small_profit_reduce_position_threshold" in config:
        trading_engine.config.small_profit_reduce_position_threshold = config["small_profit_reduce_position_threshold"]

    if "over_position_reduce_enabled" in config:
        trading_engine.config.over_position_reduce_enabled = config["over_position_reduce_enabled"]
    if "over_position_reduce_threshold" in config:
        trading_engine.config.over_position_reduce_threshold = config["over_position_reduce_threshold"]
    if "over_position_reduce_target" in config:
        trading_engine.config.over_position_reduce_target = config["over_position_reduce_target"]

    if "over_position_exemption_enabled" in config:
        trading_engine.config.over_position_exemption_enabled = config["over_position_exemption_enabled"]
    if "exemption_loss_high_minutes" in config:
        trading_engine.config.exemption_loss_high_minutes = config["exemption_loss_high_minutes"]
    if "exemption_loss_medium_minutes" in config:
        trading_engine.config.exemption_loss_medium_minutes = config["exemption_loss_medium_minutes"]
    if "exemption_profit_minutes" in config:
        trading_engine.config.exemption_profit_minutes = config["exemption_profit_minutes"]

    if "band_trade_enabled" in config:
        trading_engine.config.band_trade_enabled = config["band_trade_enabled"]
    if "band_trade_reduce_at" in config:
        trading_engine.config.band_trade_reduce_at = config["band_trade_reduce_at"]
    if "band_trade_second_reduce_at" in config:
        trading_engine.config.band_trade_second_reduce_at = config["band_trade_second_reduce_at"]
    if "band_trade_final_reduce_at" in config:
        trading_engine.config.band_trade_final_reduce_at = config["band_trade_final_reduce_at"]
    if "band_trade_reduce_percent" in config:
        trading_engine.config.band_trade_reduce_percent = config["band_trade_reduce_percent"]
    if "band_trade_second_reduce_percent" in config:
        trading_engine.config.band_trade_second_reduce_percent = config["band_trade_second_reduce_percent"]
    if "band_trade_buy_back_at" in config:
        trading_engine.config.band_trade_buy_back_at = config["band_trade_buy_back_at"]

    if "pyramid_on_stop_loss_enabled" in config:
        trading_engine.config.pyramid_on_stop_loss_enabled = config["pyramid_on_stop_loss_enabled"]
    if "pyramid_on_stop_loss_trend_score" in config:
        trading_engine.config.pyramid_on_stop_loss_trend_score = config["pyramid_on_stop_loss_trend_score"]
    if "pyramid_on_stop_loss_max_position_percent" in config:
        trading_engine.config.pyramid_on_stop_loss_max_position_percent = config["pyramid_on_stop_loss_max_position_percent"]
    if "pyramid_on_stop_loss_min_cash" in config:
        trading_engine.config.pyramid_on_stop_loss_min_cash = config["pyramid_on_stop_loss_min_cash"]

    return {"success": True, "config": config}


@router.post("/smartgrid/run")
async def run_smartgrid_cycle():
    from app.core.okx_client import okx_client
    results = await smart_grid_strategy.run_cycle(okx_client)
    return results


@router.get("/config/dip-buy")
async def get_dip_buy_config():
    """获取抄底策略配置"""
    from app.services.trading_engine import trading_engine
    return {
        "dip_buy_enabled": trading_engine.config.dip_buy_enabled,
        "dip_buy_min_trend_score": trading_engine.config.dip_buy_min_trend_score,
        "dip_buy_min_btc_trend": trading_engine.config.dip_buy_min_btc_trend,
        "dip_buy_min_eth_trend": trading_engine.config.dip_buy_min_eth_trend,
        "dip_buy_rsi_threshold": trading_engine.config.dip_buy_rsi_threshold,
        "dip_buy_volume_multiplier": trading_engine.config.dip_buy_volume_multiplier,
        "dip_buy_min_consecutive_bearish": trading_engine.config.dip_buy_min_consecutive_bearish,
        "dip_buy_require_bullish_reversal": trading_engine.config.dip_buy_require_bullish_reversal,
        "dip_buy_price_below_ma5": trading_engine.config.dip_buy_price_below_ma5,
        "dip_buy_price_below_ma10": trading_engine.config.dip_buy_price_below_ma10
    }


@router.post("/config/dip-buy")
async def update_dip_buy_config(config: dict):
    """更新抄底策略配置"""
    from app.services.trading_engine import trading_engine
    trading_engine.config.dip_buy_enabled = config.get("dip_buy_enabled", True)
    trading_engine.config.dip_buy_min_trend_score = config.get("dip_buy_min_trend_score", 7)
    trading_engine.config.dip_buy_min_btc_trend = config.get("dip_buy_min_btc_trend", 6)
    trading_engine.config.dip_buy_min_eth_trend = config.get("dip_buy_min_eth_trend", 5)
    trading_engine.config.dip_buy_rsi_threshold = config.get("dip_buy_rsi_threshold", 35.0)
    trading_engine.config.dip_buy_volume_multiplier = config.get("dip_buy_volume_multiplier", 2.0)
    trading_engine.config.dip_buy_min_consecutive_bearish = config.get("dip_buy_min_consecutive_bearish", 3)
    trading_engine.config.dip_buy_require_bullish_reversal = config.get("dip_buy_require_bullish_reversal", True)
    trading_engine.config.dip_buy_price_below_ma5 = config.get("dip_buy_price_below_ma5", True)
    trading_engine.config.dip_buy_price_below_ma10 = config.get("dip_buy_price_below_ma10", True)
    return {"success": True, "config": config}


@router.get("/config/bearish-candle")
async def get_bearish_candle_config():
    """获取阴线买入配置"""
    from app.services.trading_engine import trading_engine
    return {
        "bearish_candle_enabled": trading_engine.config.bearish_candle_enabled,
        "bearish_candle_consecutive_count": trading_engine.config.bearish_candle_consecutive_count,
        "bearish_candle_min_trend_score": trading_engine.config.bearish_candle_min_trend_score,
        "bearish_candle_price_below_ma": trading_engine.config.bearish_candle_price_below_ma,
        "bearish_candle_rsi_enabled": trading_engine.config.bearish_candle_rsi_enabled,
        "bearish_candle_rsi_oversold": trading_engine.config.bearish_candle_rsi_oversold,
        "bearish_candle_volume_enabled": trading_engine.config.bearish_candle_volume_enabled,
        "bearish_candle_volume_ratio": trading_engine.config.bearish_candle_volume_ratio,
        "bearish_candle_interval": trading_engine.config.bearish_candle_interval
    }


@router.post("/config/bearish-candle")
async def update_bearish_candle_config(config: dict):
    """更新阴线买入配置"""
    from app.services.trading_engine import trading_engine
    trading_engine.config.bearish_candle_enabled = config.get("bearish_candle_enabled", True)
    trading_engine.config.bearish_candle_consecutive_count = config.get("bearish_candle_consecutive_count", 2)
    trading_engine.config.bearish_candle_min_trend_score = config.get("bearish_candle_min_trend_score", 6)
    trading_engine.config.bearish_candle_price_below_ma = config.get("bearish_candle_price_below_ma", True)
    trading_engine.config.bearish_candle_rsi_enabled = config.get("bearish_candle_rsi_enabled", True)
    trading_engine.config.bearish_candle_rsi_oversold = config.get("bearish_candle_rsi_oversold", 40)
    trading_engine.config.bearish_candle_volume_enabled = config.get("bearish_candle_volume_enabled", True)
    trading_engine.config.bearish_candle_volume_ratio = config.get("bearish_candle_volume_ratio", 1.2)
    trading_engine.config.bearish_candle_interval = config.get("bearish_candle_interval", "5m")
    return {"success": True, "config": config}


@router.get("/config/crash-rebound")
async def get_crash_rebound_config():
    """获取暴跌反弹策略配置"""
    from app.services.trading_engine import trading_engine
    return {
        "crash_rebound_enabled": trading_engine.config.crash_rebound_enabled,
        "crash_rebound_threshold": trading_engine.config.crash_rebound_threshold,
        "crash_rebound_min_trend_score": trading_engine.config.crash_rebound_min_trend_score,
        "crash_rebound_min_rebound_percent": trading_engine.config.crash_rebound_min_rebound_percent,
        "crash_rebound_rsi_check_enabled": trading_engine.config.crash_rebound_rsi_check_enabled,
        "crash_rebound_rsi_threshold": trading_engine.config.crash_rebound_rsi_threshold,
        "crash_rebound_volume_check_enabled": trading_engine.config.crash_rebound_volume_check_enabled,
        "crash_rebound_volume_ratio": trading_engine.config.crash_rebound_volume_ratio
    }


@router.post("/config/crash-rebound")
async def update_crash_rebound_config(config: dict):
    """更新暴跌反弹策略配置"""
    from app.services.trading_engine import trading_engine
    trading_engine.config.crash_rebound_enabled = config.get("crash_rebound_enabled", True)
    trading_engine.config.crash_rebound_threshold = config.get("crash_rebound_threshold", -10.0)
    trading_engine.config.crash_rebound_min_trend_score = config.get("crash_rebound_min_trend_score", 6)
    trading_engine.config.crash_rebound_min_rebound_percent = config.get("crash_rebound_min_rebound_percent", 2.0)
    trading_engine.config.crash_rebound_rsi_check_enabled = config.get("crash_rebound_rsi_check_enabled", False)
    trading_engine.config.crash_rebound_rsi_threshold = config.get("crash_rebound_rsi_threshold", 30.0)
    trading_engine.config.crash_rebound_volume_check_enabled = config.get("crash_rebound_volume_check_enabled", False)
    trading_engine.config.crash_rebound_volume_ratio = config.get("crash_rebound_volume_ratio", 1.5)
    return {"success": True, "config": config}


@router.get("/config/short-crash")
async def get_short_crash_config():
    """获取暴跌做空配置"""
    from app.services.trading_engine import trading_engine
    return {
        "short_crash_enabled": trading_engine.config.short_crash_enabled,
        "short_crash_min_rise_24h": trading_engine.config.short_crash_min_rise_24h,
        "short_crash_max_trend_score": trading_engine.config.short_crash_max_trend_score,
        "short_crash_min_pullback_percent": trading_engine.config.short_crash_min_pullback_percent,
        "short_crash_rsi_check_enabled": trading_engine.config.short_crash_rsi_check_enabled,
        "short_crash_rsi_threshold": trading_engine.config.short_crash_rsi_threshold,
        "short_crash_volume_check_enabled": trading_engine.config.short_crash_volume_check_enabled,
        "short_crash_volume_ratio": trading_engine.config.short_crash_volume_ratio
    }


@router.post("/config/short-crash")
async def update_short_crash_config(config: dict):
    """更新暴跌做空配置"""
    from app.services.trading_engine import trading_engine
    trading_engine.config.short_crash_enabled = config.get("short_crash_enabled", True)
    trading_engine.config.short_crash_min_rise_24h = config.get("short_crash_min_rise_24h", 10.0)
    trading_engine.config.short_crash_max_trend_score = config.get("short_crash_max_trend_score", 4)
    trading_engine.config.short_crash_min_pullback_percent = config.get("short_crash_min_pullback_percent", 2.0)
    trading_engine.config.short_crash_rsi_check_enabled = config.get("short_crash_rsi_check_enabled", False)
    trading_engine.config.short_crash_rsi_threshold = config.get("short_crash_rsi_threshold", 70.0)
    trading_engine.config.short_crash_volume_check_enabled = config.get("short_crash_volume_check_enabled", False)
    trading_engine.config.short_crash_volume_ratio = config.get("short_crash_volume_ratio", 1.2)
    return {"success": True, "config": config}


@router.get("/config/take-profit-order")
async def get_take_profit_order_config():
    """获取止盈单配置"""
    from app.services.trading_engine import trading_engine
    return {
        "take_profit_order_enabled": trading_engine.config.take_profit_order_enabled,
        "take_profit_order_partial": trading_engine.config.take_profit_order_partial,
        "take_profit_adjust_on_bad_sentiment": trading_engine.config.take_profit_adjust_on_bad_sentiment,
        "take_profit_bad_sentiment_threshold": trading_engine.config.take_profit_bad_sentiment_threshold
    }


@router.post("/config/take-profit-order")
async def update_take_profit_order_config(config: dict):
    """更新止盈单配置"""
    from app.services.trading_engine import trading_engine
    trading_engine.config.take_profit_order_enabled = config.get("take_profit_order_enabled", True)
    trading_engine.config.take_profit_order_partial = config.get("take_profit_order_partial", 0.5)
    trading_engine.config.take_profit_adjust_on_bad_sentiment = config.get("take_profit_adjust_on_bad_sentiment", True)
    trading_engine.config.take_profit_bad_sentiment_threshold = config.get("take_profit_bad_sentiment_threshold", 3)
    return {"success": True, "config": config}


@router.get("/config/short-dip")
async def get_short_dip_config():
    """获取做空抄底配置"""
    from app.services.trading_engine import trading_engine
    return {
        "short_dip_enabled": trading_engine.config.short_dip_enabled,
        "short_dip_max_trend_score": trading_engine.config.short_dip_max_trend_score,
        "short_dip_max_btc_trend": trading_engine.config.short_dip_max_btc_trend,
        "short_dip_max_eth_trend": trading_engine.config.short_dip_max_eth_trend,
        "short_dip_rsi_threshold": trading_engine.config.short_dip_rsi_threshold,
        "short_dip_volume_multiplier": trading_engine.config.short_dip_volume_multiplier,
        "short_dip_min_consecutive_bullish": trading_engine.config.short_dip_min_consecutive_bullish,
        "short_dip_require_bearish_reversal": trading_engine.config.short_dip_require_bearish_reversal,
        "short_dip_price_above_ma5": trading_engine.config.short_dip_price_above_ma5,
        "short_dip_price_above_ma10": trading_engine.config.short_dip_price_above_ma10
    }


@router.post("/config/short-dip")
async def update_short_dip_config(config: dict):
    """更新做空抄底配置"""
    from app.services.trading_engine import trading_engine
    trading_engine.config.short_dip_enabled = config.get("short_dip_enabled", True)
    trading_engine.config.short_dip_max_trend_score = config.get("short_dip_max_trend_score", 4)
    trading_engine.config.short_dip_max_btc_trend = config.get("short_dip_max_btc_trend", 4)
    trading_engine.config.short_dip_max_eth_trend = config.get("short_dip_max_eth_trend", 4)
    trading_engine.config.short_dip_rsi_threshold = config.get("short_dip_rsi_threshold", 65.0)
    trading_engine.config.short_dip_volume_multiplier = config.get("short_dip_volume_multiplier", 2.0)
    trading_engine.config.short_dip_min_consecutive_bullish = config.get("short_dip_min_consecutive_bullish", 3)
    trading_engine.config.short_dip_require_bearish_reversal = config.get("short_dip_require_bearish_reversal", True)
    trading_engine.config.short_dip_price_above_ma5 = config.get("short_dip_price_above_ma5", True)
    trading_engine.config.short_dip_price_above_ma10 = config.get("short_dip_price_above_ma10", True)
    return {"success": True, "config": config}


@router.get("/config/bullish-candle")
async def get_bullish_candle_config():
    """获取阳线做空配置"""
    from app.services.trading_engine import trading_engine
    return {
        "short_bearish_enabled": trading_engine.config.short_bearish_enabled,
        "short_bearish_consecutive_count": trading_engine.config.short_bearish_consecutive_count,
        "short_bearish_max_trend_score": trading_engine.config.short_bearish_max_trend_score,
        "short_bearish_price_above_ma": trading_engine.config.short_bearish_price_above_ma,
        "short_bearish_rsi_enabled": trading_engine.config.short_bearish_rsi_enabled,
        "short_bearish_rsi_overbought": trading_engine.config.short_bearish_rsi_overbought,
        "short_bearish_volume_enabled": trading_engine.config.short_bearish_volume_enabled,
        "short_bearish_volume_ratio": trading_engine.config.short_bearish_volume_ratio,
        "short_bearish_candle_interval": trading_engine.config.short_bearish_candle_interval
    }


@router.post("/config/bullish-candle")
async def update_bullish_candle_config(config: dict):
    """更新阳线做空配置"""
    from app.services.trading_engine import trading_engine
    trading_engine.config.short_bearish_enabled = config.get("short_bearish_enabled", True)
    trading_engine.config.short_bearish_consecutive_count = config.get("short_bearish_consecutive_count", 2)
    trading_engine.config.short_bearish_max_trend_score = config.get("short_bearish_max_trend_score", 4)
    trading_engine.config.short_bearish_price_above_ma = config.get("short_bearish_price_above_ma", True)
    trading_engine.config.short_bearish_rsi_enabled = config.get("short_bearish_rsi_enabled", True)
    trading_engine.config.short_bearish_rsi_overbought = config.get("short_bearish_rsi_overbought", 70.0)
    trading_engine.config.short_bearish_volume_enabled = config.get("short_bearish_volume_enabled", True)
    trading_engine.config.short_bearish_volume_ratio = config.get("short_bearish_volume_ratio", 1.2)
    trading_engine.config.short_bearish_candle_interval = config.get("short_bearish_candle_interval", "5m")
    return {"success": True, "config": config}


# 麻雀战法配置 API
@router.get("/sparrow-config")
async def get_sparrow_config():
    """获取麻雀战法配置"""
    if SPARROW_CONFIG_FILE.exists():
        try:
            with open(SPARROW_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception as e:
            print(f"加载麻雀战法配置失败: {e}")
    # 返回默认配置
    return {
        "enabled": False,
        "timezone_aware_enabled": sparrow_config.timezone_aware_enabled,
        "base_capital": 287.0,
        "daily_target": 9.0,
        "weekly_target": 21.0,
        "time_zones": sparrow_config.time_zones,
        "take_profit": sparrow_config.take_profit.model_dump(),
        "stop_loss": sparrow_config.stop_loss.model_dump(),
        "entry_threshold": sparrow_config.entry_threshold.model_dump(),
        "position": sparrow_config.position.model_dump(),
        "daily_control": sparrow_config.daily_control.model_dump(),
        "check_interval": sparrow_config.check_interval.model_dump(),
        "buy_conditions": {
            "sentiment_threshold": 7,
            "long_min_bullish_score": 7,
            "long_bullish_gap": 2,
            "long_min_trend_score": 5,
            "long_rsi_min": 30,
            "long_rsi_max": 70,
            "long_min_volume_ratio": 0.8,
            "long_max_pullback_percent": 8,
            "long_min_pullback_percent": -15
        },
        "cooldown": {
            "tiered_cooldown_enabled": True,
            "cooldown_trend_10": 15,
            "cooldown_trend_8_9": 20,
            "cooldown_trend_6_7": 30
        },
        "decreasing_buy": {
            "decreasing_buy_enabled": True,
            "factor_1": 1.0,
            "factor_2": 0.6,
            "factor_3": 0.35,
            "factor_4": 0.2
        },
        "pullback": {
            "pullback_buy_threshold": 0.97
        },
        "cash_reserve": {
            "min_cash_reserve": 30
        },
        "exemption": {
            "over_position_exemption_enabled": True,
            "exemption_loss_high": 60,
            "exemption_loss_medium": 45,
            "exemption_profit": 30
        },
        "volatility": {
            "volatility_filter_enabled": True,
            "volatility_min": 0.5,
            "volatility_preferred": 1.5
        },
        "short_conditions": {
            "short_min_bearish_score": 7,
            "short_min_trend_score": 0,
            "short_max_trend_score": 4,
            "short_max_btc_trend": 4,
            "short_max_eth_trend": 4,
            "short_min_pullback_percent": -8.0,
            "short_max_pullback_percent": 5.0,
            "short_rsi_min": 60,
            "short_rsi_max": 80,
            "short_min_volume_ratio": 0.8,
            "short_max_market_trend": 4
        },
        "short_cooldown": {
            "short_cooldown_trend_1": 15,
            "short_cooldown_trend_2_3": 20,
            "short_cooldown_trend_4": 30
        },
        "short_decreasing": {
            "short_decreasing_buy_enabled": True,
            "short_position_ratio": 0.8,
            "short_max_positions": 1
        },
        "short_risk": {
            "short_stop_loss_percent": 2.0,
            "short_take_profit_percent": 3.0,
            "short_pullback_threshold": 1.03
        },
        "short_exemption": {
            "short_exemption_enabled": True,
            "short_exemption_loss_high": 60,
            "short_exemption_loss_medium": 45,
            "short_exemption_profit": 30
        }
    }


@router.post("/sparrow-config")
async def update_sparrow_config(config: dict):
    """更新麻雀战法配置"""
    # 保存配置到文件
    with open(SPARROW_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    # 更新时区感知开关
    if "timezone_aware_enabled" in config:
        sparrow_config.timezone_aware_enabled = config["timezone_aware_enabled"]

    # 更新检查频率配置
    if "check_interval" in config:
        ci = config["check_interval"]
        if "active" in ci:
            sparrow_config.check_interval.active = ci["active"]
        if "quiet" in ci:
            sparrow_config.check_interval.quiet = ci["quiet"]
        if "fixed" in ci:
            sparrow_config.check_interval.fixed = ci["fixed"]

    # 如果配置启用，更新全局 sparrow_config 和 trading_engine
    if config.get("enabled", False):
        # 更新基础参数
        if "base_capital" in config:
            sparrow_config.base_capital = config["base_capital"]
        if "daily_target" in config:
            sparrow_config.daily_target = config["daily_target"]
        if "weekly_target" in config:
            sparrow_config.weekly_target = config["weekly_target"]

        # 更新trading_engine配置
        # 开多条件
        if "buy_conditions" in config:
            bc = config["buy_conditions"]
            if "sentiment_threshold" in bc:
                trading_engine.config.sentiment_threshold = bc["sentiment_threshold"]
            if "long_min_trend_score" in bc:
                trading_engine.config.long_min_trend_score = bc["long_min_trend_score"]
            if "long_rsi_min" in bc:
                trading_engine.config.long_rsi_min = bc["long_rsi_min"]
            if "long_rsi_max" in bc:
                trading_engine.config.long_rsi_max = bc["long_rsi_max"]
            if "long_min_volume_ratio" in bc:
                trading_engine.config.long_min_volume_ratio = bc["long_min_volume_ratio"]
            if "long_max_pullback_percent" in bc:
                trading_engine.config.long_max_pullback_percent = bc["long_max_pullback_percent"]
            if "long_min_pullback_percent" in bc:
                trading_engine.config.long_min_pullback_percent = bc["long_min_pullback_percent"]

        # 冷却期
        if "cooldown" in config:
            cd = config["cooldown"]
            if "tiered_cooldown_enabled" in cd:
                trading_engine.config.tiered_cooldown_enabled = cd["tiered_cooldown_enabled"]
            if "cooldown_trend_10" in cd:
                trading_engine.config.cooldown_trend_10 = cd["cooldown_trend_10"]
            if "cooldown_trend_8_9" in cd:
                trading_engine.config.cooldown_trend_8_9 = cd["cooldown_trend_8_9"]
            if "cooldown_trend_6_7" in cd:
                trading_engine.config.cooldown_trend_6_7 = cd["cooldown_trend_6_7"]

        # 买入金额递减
        if "decreasing_buy" in config:
            db = config["decreasing_buy"]
            if "decreasing_buy_enabled" in db:
                trading_engine.config.decreasing_buy_enabled = db["decreasing_buy_enabled"]
            if "factor_1" in db or "factor_2" in db or "factor_3" in db or "factor_4" in db:
                factors = [
                    db.get("factor_1", 1.0),
                    db.get("factor_2", 0.6),
                    db.get("factor_3", 0.35),
                    db.get("factor_4", 0.2)
                ]
                trading_engine.config.decreasing_buy_factors = factors

        # 回调加仓
        if "pullback" in config:
            pb = config["pullback"]
            if "pullback_buy_threshold" in pb:
                trading_engine.config.pullback_buy_threshold = pb["pullback_buy_threshold"]

        # 现金保留
        if "cash_reserve" in config:
            cr = config["cash_reserve"]
            if "min_cash_reserve" in cr:
                trading_engine.config.min_cash_reserve = cr["min_cash_reserve"]

        # 豁免期
        if "exemption" in config:
            ex = config["exemption"]
            if "over_position_exemption_enabled" in ex:
                trading_engine.config.over_position_exemption_enabled = ex["over_position_exemption_enabled"]
            if "exemption_loss_high" in ex:
                trading_engine.config.exemption_loss_high = ex["exemption_loss_high"]
            if "exemption_loss_medium" in ex:
                trading_engine.config.exemption_loss_medium = ex["exemption_loss_medium"]
            if "exemption_profit" in ex:
                trading_engine.config.exemption_profit = ex["exemption_profit"]

        # 波动率
        if "volatility" in config:
            vol = config["volatility"]
            if "volatility_filter_enabled" in vol:
                trading_engine.config.volatility_filter_enabled = vol["volatility_filter_enabled"]
            if "volatility_min" in vol:
                trading_engine.config.volatility_min = vol["volatility_min"]
            if "volatility_preferred" in vol:
                trading_engine.config.volatility_preferred = vol["volatility_preferred"]

        # 做空条件
        if "short_conditions" in config:
            sc = config["short_conditions"]
            if "short_min_bearish_score" in sc:
                trading_engine.config.short_min_bearish_score = sc["short_min_bearish_score"]
            if "short_min_trend_score" in sc:
                trading_engine.config.short_min_trend_score = sc["short_min_trend_score"]
            if "short_max_trend_score" in sc:
                trading_engine.config.short_max_trend_score = sc["short_max_trend_score"]
            if "short_max_btc_trend" in sc:
                trading_engine.config.short_max_btc_trend = sc["short_max_btc_trend"]
            if "short_max_eth_trend" in sc:
                trading_engine.config.short_max_eth_trend = sc["short_max_eth_trend"]
            if "short_min_pullback_percent" in sc:
                trading_engine.config.short_min_pullback_percent = sc["short_min_pullback_percent"]
            if "short_max_pullback_percent" in sc:
                trading_engine.config.short_max_pullback_percent = sc["short_max_pullback_percent"]
            if "short_rsi_min" in sc:
                trading_engine.config.short_rsi_min = sc["short_rsi_min"]
            if "short_rsi_max" in sc:
                trading_engine.config.short_rsi_max = sc["short_rsi_max"]
            if "short_min_volume_ratio" in sc:
                trading_engine.config.short_min_volume_ratio = sc["short_min_volume_ratio"]
            if "short_max_market_trend" in sc:
                trading_engine.config.short_max_market_trend = sc["short_max_market_trend"]

        # 做空冷却期
        if "short_cooldown" in config:
            scd = config["short_cooldown"]
            if "short_cooldown_trend_1" in scd:
                trading_engine.config.short_cooldown_trend_1 = scd["short_cooldown_trend_1"]
            if "short_cooldown_trend_2_3" in scd:
                trading_engine.config.short_cooldown_trend_2_3 = scd["short_cooldown_trend_2_3"]
            if "short_cooldown_trend_4" in scd:
                trading_engine.config.short_cooldown_trend_4 = scd["short_cooldown_trend_4"]

        # 做空递减
        if "short_decreasing" in config:
            sd = config["short_decreasing"]
            if "short_decreasing_buy_enabled" in sd:
                trading_engine.config.short_decreasing_buy_enabled = sd["short_decreasing_buy_enabled"]
            if "short_position_ratio" in sd:
                trading_engine.config.short_position_ratio = sd["short_position_ratio"]
            if "short_max_positions" in sd:
                trading_engine.config.short_max_positions = sd["short_max_positions"]

        # 做空止损止盈
        if "short_risk" in config:
            sr = config["short_risk"]
            if "short_stop_loss_percent" in sr:
                trading_engine.config.short_stop_loss_percent = sr["short_stop_loss_percent"]
            if "short_take_profit_percent" in sr:
                trading_engine.config.short_take_profit_percent = sr["short_take_profit_percent"]
            if "short_pullback_threshold" in sr:
                trading_engine.config.short_pullback_threshold = sr["short_pullback_threshold"]

        # 做空豁免期
        if "short_exemption" in config:
            se = config["short_exemption"]
            if "short_exemption_enabled" in se:
                trading_engine.config.short_exemption_enabled = se["short_exemption_enabled"]
            if "short_exemption_loss_high" in se:
                trading_engine.config.short_exemption_loss_high = se["short_exemption_loss_high"]
            if "short_exemption_loss_medium" in se:
                trading_engine.config.short_exemption_loss_medium = se["short_exemption_loss_medium"]
            if "short_exemption_profit" in se:
                trading_engine.config.short_exemption_profit = se["short_exemption_profit"]

    return {"success": True, "config": config}
