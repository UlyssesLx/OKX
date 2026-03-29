"""
统一配置管理模块
整合所有配置来源，消除配置分散问题
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import json
import os
from pathlib import Path


class TradingMode(str, Enum):
    SIMULATION = "simulation"
    LIVE = "live"


class ConfigSource(BaseModel):
    """配置来源追踪"""
    source_file: str
    loaded_at: str
    priority: int = 0


class UnifiedConfig(BaseModel):
    """统一配置模型"""
    version: str = "3.0"
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    trading_mode: TradingMode = TradingMode.SIMULATION
    use_swap: bool = True
    long_leverage: int = 2
    short_leverage: int = 2
    simulation_balance: float = 1000.0

    strategy_version: str = "sparrow"
    time_stop: int = 48
    min_trend_score: int = 5
    min_resonance_score: int = 6
    min_volatility: float = 0.3
    max_volatility: float = 5.0
    max_daily_trades: int = 5
    max_daily_loss: float = 5.0
    min_cash_reserve: float = 30.0
    min_capital_flow_score: int = 6
    min_volume_ratio: float = 0.8

    short_config: Dict[str, Any] = Field(default_factory=dict)
    long_config: Dict[str, Any] = Field(default_factory=dict)
    sparrow_config: Dict[str, Any] = Field(default_factory=dict)
    smart_trading_config: Dict[str, Any] = Field(default_factory=dict)


class ConfigManager:
    """
    统一配置管理器
    从多个JSON文件加载配置并合并
    """
    _instance: Optional['ConfigManager'] = None
    _config: Optional[UnifiedConfig] = None
    _sources: Dict[str, ConfigSource] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self._config = UnifiedConfig()
            self._load_all_configs()

    def _get_backend_dir(self) -> Path:
        return Path(__file__).parent.parent.parent

    def _load_json_config(self, file_path: Path) -> Dict:
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _load_all_configs(self):
        """从所有JSON文件加载配置"""
        backend_dir = self._get_backend_dir()

        settings_file = backend_dir / "settings.json"
        if settings_file.exists():
            settings_data = self._load_json_config(settings_file)
            self._sources["settings"] = ConfigSource(
                source_file=str(settings_file),
                loaded_at=datetime.now().isoformat(),
                priority=1
            )
            self._apply_settings_config(settings_data)

        sparrow_file = backend_dir / "sparrow_config.json"
        if sparrow_file.exists():
            sparrow_data = self._load_json_config(sparrow_file)
            self._sources["sparrow"] = ConfigSource(
                source_file=str(sparrow_file),
                loaded_at=datetime.now().isoformat(),
                priority=2
            )
            self._config.sparrow_config = sparrow_data

        smart_trading_file = backend_dir / "smart_trading_config.json"
        if smart_trading_file.exists():
            smart_data = self._load_json_config(smart_trading_file)
            self._sources["smart_trading"] = ConfigSource(
                source_file=str(smart_trading_file),
                loaded_at=datetime.now().isoformat(),
                priority=3
            )
            self._config.smart_trading_config = smart_data

    def _apply_settings_config(self, data: Dict):
        """应用settings.json配置到统一模型"""
        if not data:
            return

        self._config.trading_mode = TradingMode(data.get("tradingMode", "simulation"))
        self._config.use_swap = data.get("useSwap", True)
        self._config.long_leverage = data.get("longLeverage", 2)
        self._config.short_leverage = data.get("shortLeverage", 2)
        self._config.simulation_balance = data.get("simulationBalance", 1000.0)
        self._config.strategy_version = data.get("strategyVersion", "sparrow")
        self._config.time_stop = data.get("timeStop", 48)
        self._config.min_trend_score = data.get("minTrendScore", 5)
        self._config.min_resonance_score = data.get("minResonanceScore", 6)
        self._config.min_volatility = data.get("minVolatility", 0.3)
        self._config.max_volatility = data.get("maxVolatility", 5.0)
        self._config.max_daily_trades = data.get("maxDailyTrades", 5)
        self._config.max_daily_loss = data.get("maxDailyLoss", 5.0)
        self._config.min_cash_reserve = data.get("minCashReserve", 30.0)
        self._config.min_capital_flow_score = data.get("minCapitalFlowScore", 6)
        self._config.min_volume_ratio = data.get("minVolumeRatio", 0.8)

        if "shortConfig" in data:
            self._config.short_config = data["shortConfig"]

    def get_config(self) -> UnifiedConfig:
        """获取统一配置"""
        return self._config

    def get_sparrow_setting(self, key: str, default: Any = None) -> Any:
        """获取sparrow配置项"""
        return self._config.sparrow_config.get(key, default)

    def get_smart_trading_setting(self, key: str, default: Any = None) -> Any:
        """获取smart trading配置项"""
        return self._config.smart_trading_config.get(key, default)

    def get_short_config(self, key: str, default: Any = None) -> Any:
        """获取做空配置项"""
        return self._config.short_config.get(key, default)

    def get_long_config(self, key: str, default: Any = None) -> Any:
        """获取做多配置项"""
        return self._config.long_config.get(key, default)

    def reload(self):
        """重新加载所有配置"""
        self._config = UnifiedConfig()
        self._sources = {}
        self._load_all_configs()

    def get_sources(self) -> Dict[str, ConfigSource]:
        """获取配置来源信息"""
        return self._sources


config_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    return config_manager


def get_unified_config() -> UnifiedConfig:
    return config_manager.get_config()