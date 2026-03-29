"""
配置热更新模块
支持无需重启服务即可调整参数
"""
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
import json
import os


class ConfigEvent(str, Enum):
    UPDATED = "updated"
    RELOADED = "reloaded"
    SAVED = "saved"


@dataclass
class ConfigChange:
    key: str
    old_value: Any
    new_value: Any
    timestamp: datetime
    source: str = "manual"


@dataclass
class HotReloadConfig:
    enabled: bool = True
    watch_interval: int = 5
    auto_reload: bool = True
    backup_on_change: bool = True


class ConfigChangeObserver:
    """配置变更观察者"""

    def __init__(self, callback: Callable[[str, Any, Any], None], name: str = ""):
        self.callback = callback
        self.name = name

    def on_change(self, key: str, old_value: Any, new_value: Any):
        if callable(self.callback):
            try:
                self.callback(key, old_value, new_value)
            except Exception:
                pass


class ConfigHotReloader:
    """
    配置热更新器
    支持配置变更监听、自动备份、回调通知
    """
    _instance: Optional['ConfigHotReloader'] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._config: Dict[str, Any] = {}
        self._config_file: str = ""
        self._observers: List[ConfigChangeObserver] = []
        self._change_history: List[ConfigChange] = []
        self._settings = HotReloadConfig()
        self._file_mtime: float = 0
        self._last_check: datetime = datetime.now()

    def initialize(self, config: Dict[str, Any], config_file: str = ""):
        """初始化配置"""
        self._config = config.copy() if config else {}
        self._config_file = config_file
        if config_file and os.path.exists(config_file):
            self._file_mtime = os.path.getmtime(config_file)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def set(self, key: str, value: Any, source: str = "manual", save: bool = False):
        """设置配置值"""
        old_value = self.get(key)
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

        change = ConfigChange(
            key=key,
            old_value=old_value,
            new_value=value,
            timestamp=datetime.now(),
            source=source
        )
        self._change_history.append(change)

        self._notify_observers(key, old_value, value)

        if save or self._settings.auto_reload:
            self.save_to_file()

    def update(self, updates: Dict[str, Any], source: str = "manual"):
        """批量更新配置"""
        for key, value in updates.items():
            self.set(key, value, source=source, save=False)

        if self._settings.auto_reload:
            self.save_to_file()

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.copy()

    def add_observer(self, callback: Callable[[str, Any, Any], None], name: str = ""):
        """添加配置变更观察者"""
        observer = ConfigChangeObserver(callback, name)
        self._observers.append(observer)

    def remove_observer(self, name: str):
        """移除观察者"""
        self._observers = [o for o in self._observers if o.name != name]

    def _notify_observers(self, key: str, old_value: Any, new_value: Any):
        """通知所有观察者"""
        for observer in self._observers:
            observer.on_change(key, old_value, new_value)

    def save_to_file(self, file_path: str = None) -> bool:
        """保存配置到文件"""
        target_file = file_path or self._config_file
        if not target_file:
            return False

        try:
            if self._settings.backup_on_change:
                backup_file = f"{target_file}.bak"
                if os.path.exists(target_file):
                    with open(target_file, 'r', encoding='utf-8') as f:
                        backup_content = f.read()
                    with open(backup_file, 'w', encoding='utf-8') as f:
                        f.write(backup_content)

            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)

            self._file_mtime = os.path.getmtime(target_file)
            return True
        except Exception:
            return False

    def reload_from_file(self, file_path: str = None) -> bool:
        """从文件重新加载配置"""
        target_file = file_path or self._config_file
        if not target_file or not os.path.exists(target_file):
            return False

        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                new_config = json.load(f)

            old_config = self._config.copy()
            self._config = new_config

            for key, new_value in self._flatten_dict(new_config).items():
                old_value = self._get_nested(old_config, key)
                if old_value != new_value:
                    self._notify_observers(key, old_value, new_value)

            self._file_mtime = os.path.getmtime(target_file)
            return True
        except Exception:
            return False

    def check_file_changes(self) -> bool:
        """检查文件是否有变更"""
        if not self._config_file or not os.path.exists(self._config_file):
            return False

        try:
            current_mtime = os.path.getmtime(self._config_file)
            if current_mtime > self._file_mtime:
                self._file_mtime = current_mtime
                return True
        except Exception:
            pass
        return False

    def get_change_history(self, limit: int = 50) -> List[Dict]:
        """获取配置变更历史"""
        history = sorted(self._change_history, key=lambda x: x.timestamp, reverse=True)
        return [
            {
                "key": c.key,
                "old_value": c.old_value,
                "new_value": c.new_value,
                "timestamp": c.timestamp.isoformat(),
                "source": c.source
            }
            for c in history[:limit]
        ]

    def _flatten_dict(self, d: Dict, parent_key: str = "", sep: str = ".") -> Dict:
        """扁平化字典"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def _get_nested(self, d: Dict, key: str, sep: str = ".") -> Any:
        """获取嵌套值"""
        keys = key.split(sep)
        value = d
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None
        return value

    def reset(self):
        """重置热更新器"""
        self._observers.clear()
        self._change_history.clear()


config_hot_reloader = ConfigHotReloader()


def get_hot_reloader() -> ConfigHotReloader:
    return config_hot_reloader


def hot_config(key: str, default: Any = None) -> Any:
    """便捷函数：获取热更新配置"""
    return config_hot_reloader.get(key, default)


def set_hot_config(key: str, value: Any, source: str = "manual"):
    """便捷函数：设置热更新配置"""
    config_hot_reloader.set(key, value, source=source)