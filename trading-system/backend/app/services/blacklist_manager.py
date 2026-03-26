"""
黑名单管理模块
止损黑名单 + 趋势解锁机制
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
from pydantic import BaseModel
from loguru import logger


class BlacklistEntry(BaseModel):
    coin: str
    reason: str
    added_at: str
    stop_loss_price: Optional[float] = None
    unlock_trend_threshold: int = 8


class BlacklistData(BaseModel):
    stopped_out: List[str] = []
    manual_ban: List[str] = []
    stablecoins: List[str] = ["USDC", "USDT", "USDG", "USDE", "DAI", "TUSD", "PAXG", "XAUT"]
    entries: Dict[str, BlacklistEntry] = {}


class BlacklistManager:
    def __init__(self, data_dir: str = "."):
        self.data_dir = Path(data_dir)
        self.blacklist_file = self.data_dir / "blacklist.json"
        self.trend_tracker: Dict[str, Dict] = {}
        self.strong_trend_threshold = 8
        self.medium_trend_threshold = 6
        self.medium_trend_count_required = 2
        self._load_blacklist()
    
    def _load_blacklist(self):
        if self.blacklist_file.exists():
            try:
                with open(self.blacklist_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.blacklist = BlacklistData(**data)
            except Exception as e:
                logger.error(f"Failed to load blacklist: {e}")
                self.blacklist = BlacklistData()
        else:
            self.blacklist = BlacklistData()
    
    def _save_blacklist(self):
        try:
            with open(self.blacklist_file, "w", encoding="utf-8") as f:
                json.dump(self.blacklist.model_dump(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save blacklist: {e}")
    
    def add_to_blacklist(
        self, 
        coin: str, 
        reason: str, 
        stop_loss_price: Optional[float] = None
    ):
        if coin in self.blacklist.stablecoins:
            return
        
        if coin not in self.blacklist.stopped_out:
            self.blacklist.stopped_out.append(coin)
        
        self.blacklist.entries[coin] = BlacklistEntry(
            coin=coin,
            reason=reason,
            added_at=datetime.now().isoformat(),
            stop_loss_price=stop_loss_price,
            unlock_trend_threshold=self.strong_trend_threshold
        )
        
        self._save_blacklist()
        logger.info(f"🚫 {coin} 已加入黑名单: {reason}")
    
    def remove_from_blacklist(self, coin: str) -> bool:
        removed = False
        
        if coin in self.blacklist.stopped_out:
            self.blacklist.stopped_out.remove(coin)
            removed = True
        
        if coin in self.blacklist.entries:
            del self.blacklist.entries[coin]
            removed = True
        
        if coin in self.trend_tracker:
            del self.trend_tracker[coin]
        
        if removed:
            self._save_blacklist()
            logger.info(f"✅ {coin} 已从黑名单移除")
        
        return removed
    
    def is_blacklisted(self, coin: str) -> bool:
        # 先检查过期
        self._check_expired(coin)

        return (
            coin in self.blacklist.stopped_out or
            coin in self.blacklist.manual_ban or
            coin in self.blacklist.stablecoins
        )

    def _check_expired(self, coin: str):
        """检查单个币种是否过期"""
        if coin not in self.blacklist.entries:
            return

        entry = self.blacklist.entries[coin]
        added_at = datetime.fromisoformat(entry.added_at)
        age_hours = (datetime.now() - added_at).total_seconds() / 3600

        # 止损黑名单72小时后自动过期
        if coin in self.blacklist.stopped_out and age_hours > 72:
            self.remove_from_blacklist(coin)
            logger.info(f"⏰ {coin} 止损黑名单已过期(72小时)，自动移除")

        # 手动黑名单168小时(7天)后自动过期
        if coin in self.blacklist.manual_ban and age_hours > 168:
            self.remove_from_blacklist(coin)
            logger.info(f"⏰ {coin} 手动黑名单已过期(168小时)，自动移除")
    
    def get_blacklist_reason(self, coin: str) -> Optional[str]:
        if coin in self.blacklist.entries:
            return self.blacklist.entries[coin].reason
        if coin in self.blacklist.stablecoins:
            return "稳定币，不参与交易"
        if coin in self.blacklist.manual_ban:
            return "手动禁用"
        return None
    
    def check_trend_unlock(self, coin: str, current_trend_score: int) -> bool:
        if not self.is_blacklisted(coin):
            return False
        
        if coin in self.blacklist.stablecoins:
            return False
        
        if current_trend_score >= self.strong_trend_threshold:
            logger.info(f"✅ {coin} 趋势评分{current_trend_score}≥{self.strong_trend_threshold}，立即解除黑名单")
            self.remove_from_blacklist(coin)
            return True
        
        if coin not in self.trend_tracker:
            self.trend_tracker[coin] = {
                "high_trend_count": 0,
                "last_check": datetime.now().isoformat()
            }
        
        tracker = self.trend_tracker[coin]
        
        if current_trend_score >= self.medium_trend_threshold:
            tracker["high_trend_count"] += 1
            logger.info(f"📈 {coin} 趋势评分{current_trend_score}/{self.medium_trend_threshold}，连续{tracker['high_trend_count']}次")
            
            if tracker["high_trend_count"] >= self.medium_trend_count_required:
                logger.info(f"✅ {coin} 趋势连续{self.medium_trend_count_required}次≥{self.medium_trend_threshold}，解除黑名单")
                self.remove_from_blacklist(coin)
                return True
        else:
            if tracker["high_trend_count"] > 0:
                logger.info(f"📉 {coin} 趋势评分{current_trend_score}，低于阈值，重置计数")
                tracker["high_trend_count"] = 0
        
        tracker["last_check"] = datetime.now().isoformat()
        return False
    
    def get_all_blacklisted_coins(self) -> Set[str]:
        return set(
            self.blacklist.stopped_out +
            self.blacklist.manual_ban +
            self.blacklist.stablecoins
        )
    
    def get_blacklisted_coins(self) -> List[str]:
        """获取黑名单币种列表（不包含稳定币）"""
        return list(set(self.blacklist.stopped_out + self.blacklist.manual_ban))
    
    def get_blacklist_summary(self) -> Dict:
        # 检查所有过期条目
        self._cleanup_all_expired()

        return {
            "stopped_out": self.blacklist.stopped_out,
            "manual_ban": self.blacklist.manual_ban,
            "stablecoins": self.blacklist.stablecoins,
            "total_count": len(self.get_all_blacklisted_coins()),
            "entries": {
                coin: entry.model_dump()
                for coin, entry in self.blacklist.entries.items()
            }
        }

    def _cleanup_all_expired(self):
        """清理所有过期的黑名单条目"""
        now = datetime.now()

        for coin in list(self.blacklist.entries.keys()):
            if coin not in self.blacklist.entries:
                continue

            entry = self.blacklist.entries[coin]
            added_at = datetime.fromisoformat(entry.added_at)
            age_hours = (now - added_at).total_seconds() / 3600

            # 止损黑名单72小时后自动过期
            if coin in self.blacklist.stopped_out and age_hours > 72:
                self.remove_from_blacklist(coin)
                logger.info(f"⏰ {coin} 止损黑名单已过期(72小时)，自动移除")

            # 手动黑名单168小时(7天)后自动过期
            if coin in self.blacklist.manual_ban and age_hours > 168:
                self.remove_from_blacklist(coin)
                logger.info(f"⏰ {coin} 手动黑名单已过期(168小时)，自动移除")
    
    def clear_expired_entries(self, max_age_hours: int = 72):
        now = datetime.now()
        expired_coins = []

        for coin, entry in list(self.blacklist.entries.items()):
            added_at = datetime.fromisoformat(entry.added_at)
            age_hours = (now - added_at).total_seconds() / 3600

            if age_hours > max_age_hours:
                expired_coins.append(coin)

        for coin in expired_coins:
            self.remove_from_blacklist(coin)
            logger.info(f"⏰ {coin} 黑名单已过期({max_age_hours}小时)，自动移除")


blacklist_manager = BlacklistManager()
