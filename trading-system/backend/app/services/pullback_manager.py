"""
回调加仓管理器
管理减仓后的价格记录和回调加仓条件检查
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass, asdict
from loguru import logger


@dataclass
class ReducePriceRecord:
    """减仓价格记录"""
    coin: str
    price: float
    timestamp: int
    amount: float  # 减仓数量


class PullbackManager:
    """回调加仓管理器"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.data_dir / "reduce_position_prices.json"
        self.records: Dict[str, ReducePriceRecord] = {}
        self.pullback_threshold = 0.97  # 回调阈值97%
        self.load_records()
    
    def load_records(self):
        """加载减仓价格记录"""
        try:
            if self.file_path.exists():
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.records = {
                        coin: ReducePriceRecord(**record)
                        for coin, record in data.items()
                    }
                logger.info(f"📋 已加载减仓价格记录: {list(self.records.keys())}")
        except Exception as e:
            logger.error(f"加载减仓价格记录失败: {str(e)}")
            self.records = {}
    
    def save_records(self):
        """保存减仓价格记录"""
        try:
            data = {
                coin: asdict(record)
                for coin, record in self.records.items()
            }
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存减仓价格记录失败: {str(e)}")
    
    def record_reduce_price(
        self,
        coin: str,
        price: float,
        amount: float
    ):
        """记录减仓价格"""
        record = ReducePriceRecord(
            coin=coin,
            price=price,
            timestamp=int(datetime.now().timestamp() * 1000),
            amount=amount
        )
        self.records[coin] = record
        self.save_records()
        logger.info(f"📝 记录减仓价格: {coin} @ ${price:.4f}, 数量: {amount}")
    
    def check_pullback_condition(
        self,
        coin: str,
        current_price: float
    ) -> Dict[str, any]:
        """
        检查是否满足回调加仓条件
        
        返回:
            {
                "can_buy": bool,       # 是否可以买入
                "reason": str,         # 原因
                "record_price": float, # 减仓价格
                "threshold": float     # 触发价格
            }
        """
        record = self.records.get(coin)
        
        if not record:
            return {
                "can_buy": True,
                "reason": "无减仓记录",
                "record_price": 0,
                "threshold": 0
            }
        
        # 计算回调阈值价格
        threshold_price = record.price * self.pullback_threshold
        
        if current_price <= threshold_price:
            logger.info(
                f"✅ {coin} 价格回调到位: ${current_price:.4f} ≤ ${threshold_price:.4f} "
                f"(减仓价${record.price:.4f}的{self.pullback_threshold*100}%)"
            )
            # 清除记录，允许买入
            del self.records[coin]
            self.save_records()
            return {
                "can_buy": True,
                "reason": "回调到位",
                "record_price": record.price,
                "threshold": threshold_price
            }
        else:
            logger.info(
                f"⏳ {coin} 等待回调: ${current_price:.4f} > ${threshold_price:.4f} "
                f"(需≤减仓价{self.pullback_threshold*100}%)"
            )
            return {
                "can_buy": False,
                "reason": f"等待回调: ${current_price:.4f} > ${threshold_price:.4f}",
                "record_price": record.price,
                "threshold": threshold_price
            }
    
    def clear_record(self, coin: str):
        """清除指定币种的记录"""
        if coin in self.records:
            del self.records[coin]
            self.save_records()
            logger.info(f"🗑️ 清除{coin}的减仓记录")
    
    def clear_all_records(self):
        """清除所有记录"""
        self.records.clear()
        self.save_records()
        logger.info("🗑️ 清除所有减仓记录")
    
    def get_record(self, coin: str) -> Optional[ReducePriceRecord]:
        """获取指定币种的记录"""
        return self.records.get(coin)
    
    def get_all_records(self) -> Dict[str, ReducePriceRecord]:
        """获取所有记录"""
        return self.records.copy()
    
    def set_pullback_threshold(self, threshold: float):
        """设置回调阈值"""
        if 0.9 <= threshold <= 1.0:
            self.pullback_threshold = threshold
            logger.info(f"⚙️ 设置回调阈值为 {threshold*100}%")
        else:
            logger.warning(f"无效的回调阈值: {threshold}，应在0.9-1.0之间")
    
    def cleanup_old_records(self, max_age_hours: int = 24):
        """清理过期记录（超过指定小时数）"""
        current_time = int(datetime.now().timestamp() * 1000)
        max_age_ms = max_age_hours * 60 * 60 * 1000
        
        coins_to_remove = []
        for coin, record in self.records.items():
            age = current_time - record.timestamp
            if age > max_age_ms:
                logger.info(f"🧹 清理过期记录: {coin} ({age/(60*60*1000):.1f}小时前)")
                coins_to_remove.append(coin)
        
        for coin in coins_to_remove:
            del self.records[coin]
        
        if coins_to_remove:
            self.save_records()
            logger.info(f"🧹 清理了 {len(coins_to_remove)} 条过期记录")


# 创建全局管理器实例
pullback_manager = PullbackManager()
