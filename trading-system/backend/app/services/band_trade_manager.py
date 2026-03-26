"""
波段操作配置
分层止盈、回调加仓策略
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel
from loguru import logger


class TakeProfitLevel(BaseModel):
    trigger_percent: float
    sell_percent: float
    description: str = ""


class BandTradeConfig(BaseModel):
    enabled: bool = True
    take_profit_levels: List[TakeProfitLevel] = [
        TakeProfitLevel(trigger_percent=3.0, sell_percent=30, description="第一层止盈30%"),
        TakeProfitLevel(trigger_percent=5.0, sell_percent=30, description="第二层止盈30%"),
        TakeProfitLevel(trigger_percent=8.0, sell_percent=40, description="第三层止盈40%"),
    ]
    callback_buy_enabled: bool = True
    callback_buy_threshold: float = -3.0
    callback_buy_size_multiplier: float = 0.5
    max_callback_buys: int = 2
    trailing_stop_enabled: bool = True
    trailing_stop_trigger: float = 5.0
    trailing_stop_distance: float = 2.0


class PositionState(BaseModel):
    coin: str
    entry_price: float
    current_amount: float
    original_amount: float
    highest_price: float
    take_profit_executed: List[int] = []
    callback_buy_count: int = 0
    trailing_stop_activated: bool = False
    last_update: str = ""


class BandTradeManager:
    def __init__(self, data_dir: str = "."):
        self.data_dir = Path(data_dir)
        self.config_file = self.data_dir / "band_trade_config.json"
        self.state_file = self.data_dir / "band_trade_state.json"
        self.config = self._load_config()
        self.positions: Dict[str, PositionState] = self._load_positions()
    
    def _load_config(self) -> BandTradeConfig:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return BandTradeConfig(**data)
            except Exception as e:
                logger.error(f"Failed to load band trade config: {e}")
        return BandTradeConfig()
    
    def _save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config.model_dump(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save band trade config: {e}")
    
    def _load_positions(self) -> Dict[str, PositionState]:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return {k: PositionState(**v) for k, v in data.items()}
            except Exception as e:
                logger.error(f"Failed to load band trade positions: {e}")
        return {}
    
    def _save_positions(self):
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(
                    {k: v.model_dump() for k, v in self.positions.items()},
                    f, indent=2, ensure_ascii=False
                )
        except Exception as e:
            logger.error(f"Failed to save band trade positions: {e}")
    
    def add_position(self, coin: str, entry_price: float, amount: float):
        self.positions[coin] = PositionState(
            coin=coin,
            entry_price=entry_price,
            current_amount=amount,
            original_amount=amount,
            highest_price=entry_price,
            take_profit_executed=[],
            callback_buy_count=0,
            trailing_stop_activated=False,
            last_update=datetime.utcnow().isoformat()
        )
        self._save_positions()
        logger.info(f"📊 波段仓位添加: {coin} @ ${entry_price:.4f}, 数量 {amount}")
    
    def remove_position(self, coin: str):
        if coin in self.positions:
            del self.positions[coin]
            self._save_positions()
            logger.info(f"📊 波段仓位移除: {coin}")
    
    def update_price(self, coin: str, current_price: float) -> Optional[Dict[str, Any]]:
        if coin not in self.positions:
            return None
        
        pos = self.positions[coin]
        pos.last_update = datetime.utcnow().isoformat()
        
        if current_price > pos.highest_price:
            pos.highest_price = current_price
        
        actions = []
        
        if self.config.enabled:
            for i, level in enumerate(self.config.take_profit_levels):
                if i in pos.take_profit_executed:
                    continue
                
                profit_percent = (current_price - pos.entry_price) / pos.entry_price * 100
                
                if profit_percent >= level.trigger_percent:
                    sell_amount = pos.original_amount * level.sell_percent / 100
                    actions.append({
                        "action": "take_profit",
                        "level": i + 1,
                        "sell_percent": level.sell_percent,
                        "sell_amount": sell_amount,
                        "trigger_price": current_price,
                        "profit_percent": profit_percent,
                        "description": level.description
                    })
                    pos.take_profit_executed.append(i)
                    pos.current_amount -= sell_amount
        
        if self.config.trailing_stop_enabled and pos.trailing_stop_activated:
            trailing_stop_price = pos.highest_price * (1 - self.config.trailing_stop_distance / 100)
            
            if current_price <= trailing_stop_price:
                actions.append({
                    "action": "trailing_stop",
                    "sell_amount": pos.current_amount,
                    "trigger_price": current_price,
                    "highest_price": pos.highest_price,
                    "stop_price": trailing_stop_price
                })
        
        if self.config.trailing_stop_enabled and not pos.trailing_stop_activated:
            profit_percent = (current_price - pos.entry_price) / pos.entry_price * 100
            if profit_percent >= self.config.trailing_stop_trigger:
                pos.trailing_stop_activated = True
                actions.append({
                    "action": "trailing_stop_activated",
                    "trigger_price": current_price,
                    "profit_percent": profit_percent
                })
        
        self._save_positions()
        
        return {"coin": coin, "actions": actions} if actions else None
    
    def check_callback_buy(self, coin: str, current_price: float) -> Optional[Dict[str, Any]]:
        if not self.config.callback_buy_enabled:
            return None
        
        if coin not in self.positions:
            return None
        
        pos = self.positions[coin]
        
        if pos.callback_buy_count >= self.config.max_callback_buys:
            return None
        
        drawdown = (current_price - pos.entry_price) / pos.entry_price * 100
        
        if drawdown <= self.config.callback_buy_threshold:
            buy_amount = pos.original_amount * self.config.callback_buy_size_multiplier
            pos.callback_buy_count += 1
            pos.current_amount += buy_amount
            
            new_avg_price = (
                (pos.entry_price * pos.current_amount + current_price * buy_amount) /
                (pos.current_amount + buy_amount)
            )
            pos.entry_price = new_avg_price
            
            self._save_positions()
            
            return {
                "action": "callback_buy",
                "coin": coin,
                "buy_amount": buy_amount,
                "buy_price": current_price,
                "drawdown": drawdown,
                "new_avg_price": new_avg_price,
                "callback_buy_count": pos.callback_buy_count
            }
        
        return None
    
    def get_position_summary(self, coin: str) -> Optional[Dict[str, Any]]:
        if coin not in self.positions:
            return None
        
        pos = self.positions[coin]
        
        return {
            "coin": coin,
            "entry_price": pos.entry_price,
            "current_amount": pos.current_amount,
            "original_amount": pos.original_amount,
            "highest_price": pos.highest_price,
            "take_profit_executed": pos.take_profit_executed,
            "callback_buy_count": pos.callback_buy_count,
            "trailing_stop_activated": pos.trailing_stop_activated,
            "remaining_percent": (pos.current_amount / pos.original_amount * 100) if pos.original_amount else 0
        }
    
    def get_all_positions(self) -> Dict[str, Dict[str, Any]]:
        return {coin: self.get_position_summary(coin) for coin in self.positions}
    
    def update_config(self, new_config: Dict[str, Any]) -> BandTradeConfig:
        self.config = BandTradeConfig(**new_config)
        self._save_config()
        return self.config


band_trade_manager = BandTradeManager()
