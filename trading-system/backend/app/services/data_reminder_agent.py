import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
import aiofiles
from loguru import logger


@dataclass
class DataFreshnessStatus:
    is_fresh: bool
    last_update: Optional[datetime]
    minutes_ago: int
    warning_level: str


class DataReminderAgent:
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self.config_file = os.path.join(data_dir, "data_reminder_config.json")
        self.last_report_file = os.path.join(data_dir, "last_report_timestamp.json")
        self._ensure_data_dir()
        self.config = self._load_config()
    
    def _ensure_data_dir(self):
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _load_config(self) -> Dict[str, Any]:
        default_config = {
            "enabled": True,
            "reminder_interval_minutes": 5,
            "force_check_threshold_minutes": 10,
            "warning_threshold_minutes": 8,
            "data_sources": {
                "balance": {"max_age_minutes": 5, "required": True},
                "market": {"max_age_minutes": 2, "required": True},
                "sentiment": {"max_age_minutes": 30, "required": False},
                "positions": {"max_age_minutes": 5, "required": True}
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    default_config.update(loaded)
            except Exception as e:
                logger.error(f"加载配置失败: {e}")
        
        return default_config
    
    def _save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    async def record_report_timestamp(self, report_type: str = "trading_check"):
        timestamp = datetime.now()
        data = {
            "timestamp": timestamp.isoformat(),
            "unix_timestamp": timestamp.timestamp(),
            "report_type": report_type,
            "local_time": timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            async with aiofiles.open(self.last_report_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False))
            logger.debug(f"记录报告时间戳: {timestamp}")
        except Exception as e:
            logger.error(f"记录时间戳失败: {e}")
    
    def get_last_report_time(self) -> Optional[Dict[str, Any]]:
        if not os.path.exists(self.last_report_file):
            return None
        
        try:
            with open(self.last_report_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取上次报告时间失败: {e}")
            return None
    
    def check_data_freshness(self, source: str) -> DataFreshnessStatus:
        last_report = self.get_last_report_time()
        
        if not last_report:
            return DataFreshnessStatus(
                is_fresh=False,
                last_update=None,
                minutes_ago=-1,
                warning_level="critical"
            )
        
        try:
            last_update = datetime.fromisoformat(last_report["timestamp"])
            minutes_ago = int((datetime.now() - last_update).total_seconds() / 60)
            
            source_config = self.config["data_sources"].get(source, {})
            max_age = source_config.get("max_age_minutes", 5)
            
            is_fresh = minutes_ago <= max_age
            
            if minutes_ago > self.config["force_check_threshold_minutes"]:
                warning_level = "critical"
            elif minutes_ago > self.config["warning_threshold_minutes"]:
                warning_level = "warning"
            else:
                warning_level = "ok"
            
            return DataFreshnessStatus(
                is_fresh=is_fresh,
                last_update=last_update,
                minutes_ago=minutes_ago,
                warning_level=warning_level
            )
        
        except Exception as e:
            logger.error(f"检查数据新鲜度失败: {e}")
            return DataFreshnessStatus(
                is_fresh=False,
                last_update=None,
                minutes_ago=-1,
                warning_level="error"
            )
    
    def generate_reminder(self) -> Dict[str, Any]:
        if not self.config["enabled"]:
            return {"enabled": False, "reminder": None}
        
        last_report = self.get_last_report_time()
        now = datetime.now()
        
        reminder = {
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "last_report": None,
            "minutes_since_last_report": None,
            "needs_refresh": False,
            "warnings": [],
            "data_status": {}
        }
        
        if last_report:
            last_time = datetime.fromisoformat(last_report["timestamp"])
            minutes_ago = int((now - last_time).total_seconds() / 60)
            
            reminder["last_report"] = last_report["local_time"]
            reminder["minutes_since_last_report"] = minutes_ago
            
            if minutes_ago > self.config["force_check_threshold_minutes"]:
                reminder["needs_refresh"] = True
                reminder["warnings"].append(
                    f"🚨 数据过期！距上次报告已 {minutes_ago} 分钟，请立即获取最新数据！"
                )
            elif minutes_ago > self.config["warning_threshold_minutes"]:
                reminder["warnings"].append(
                    f"⚠️ 数据即将过期，距上次报告 {minutes_ago} 分钟"
                )
            
            for source, source_config in self.config["data_sources"].items():
                status = self.check_data_freshness(source)
                reminder["data_status"][source] = {
                    "is_fresh": status.is_fresh,
                    "minutes_ago": status.minutes_ago,
                    "warning_level": status.warning_level
                }
        else:
            reminder["needs_refresh"] = True
            reminder["warnings"].append("🚨 无报告记录，请立即执行交易检查！")
        
        return reminder
    
    def print_reminder(self):
        reminder = self.generate_reminder()
        
        print("\n" + "=" * 60)
        print("📢 数据提醒 Agent 报告")
        print("=" * 60)
        print(f"当前时间: {reminder['current_time']}")
        
        if reminder["last_report"]:
            print(f"上次报告: {reminder['last_report']}")
            print(f"时间间隔: {reminder['minutes_since_last_report']} 分钟")
        else:
            print("上次报告: 无记录")
        
        if reminder["warnings"]:
            print("\n" + "-" * 60)
            for warning in reminder["warnings"]:
                print(warning)
        
        print("=" * 60 + "\n")
        
        return reminder
    
    async def run_check(self) -> Dict[str, Any]:
        reminder = self.generate_reminder()
        
        if reminder["needs_refresh"]:
            logger.warning("数据需要刷新，建议立即执行交易检查")
        
        return reminder


data_reminder_agent = DataReminderAgent()
