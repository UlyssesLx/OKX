from pydantic import BaseModel
from typing import Dict, Optional
from dataclasses import dataclass
from pathlib import Path
import json


class PyramidConfig(BaseModel):
    enabled: bool = True
    first_layer: float = 25.0
    second_layer: float = 15.0
    third_layer: float = 10.0
    drop_threshold: float = 0.10
    max_layers: int = 3


@dataclass
class PyramidLayer:
    layers: int = 0
    first_buy_price: float = 0.0
    last_buy_price: float = 0.0
    total_invested: float = 0.0


class PyramidManager:
    def __init__(self, config: PyramidConfig, data_file: str = None):
        self.config = config
        if data_file is None:
            self.data_file = Path(__file__).parent.parent.parent / "data" / "pyramid_layers.json"
        else:
            self.data_file = Path(data_file)
        self.layers: Dict[str, PyramidLayer] = {}
        self._ensure_data_dir()
        self._load_layers()
    
    def _ensure_data_dir(self):
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_layers(self):
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for coin, layer_data in data.items():
                        mapped_data = {
                            "layers": layer_data.get("layers", 0),
                            "first_buy_price": layer_data.get("firstBuyPrice", layer_data.get("first_buy_price", 0)),
                            "last_buy_price": layer_data.get("lastBuyPrice", layer_data.get("last_buy_price", 0)),
                            "total_invested": layer_data.get("totalInvested", layer_data.get("total_invested", 0))
                        }
                        self.layers[coin] = PyramidLayer(**mapped_data)
            except Exception as e:
                print(f"Error loading pyramid layers: {e}")
                pass
    
    def _save_layers(self):
        data = {}
        for coin, layer in self.layers.items():
            data[coin] = {
                "layers": layer.layers,
                "first_buy_price": layer.first_buy_price,
                "last_buy_price": layer.last_buy_price,
                "total_invested": layer.total_invested
            }
        
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def calculate_buy_amount(self, coin: str, current_price: float, avg_cost_price: float = 0.0) -> float:
        if not self.config.enabled:
            return 40.0
        
        if coin not in self.layers:
            self.layers[coin] = PyramidLayer()
        
        layer = self.layers[coin]
        
        if layer.layers == 0:
            layer.layers = 1
            layer.first_buy_price = current_price
            layer.last_buy_price = current_price
            layer.total_invested = self.config.first_layer
            self._save_layers()
            return self.config.first_layer
        
        drop_percent = (layer.last_buy_price - current_price) / layer.last_buy_price
        
        if drop_percent >= self.config.drop_threshold:
            layer.layers += 1
            layer.last_buy_price = current_price
            
            buy_amount = 0.0
            if layer.layers == 2:
                buy_amount = self.config.second_layer
            elif layer.layers == 3:
                buy_amount = self.config.third_layer
            else:
                return 0.0
            
            layer.total_invested += buy_amount
            self._save_layers()
            return buy_amount
        
        return 0.0
    
    def reset(self, coin: str):
        if coin in self.layers:
            del self.layers[coin]
            self._save_layers()
    
    def get_layer_info(self, coin: str) -> Optional[PyramidLayer]:
        return self.layers.get(coin)


pyramid_config = PyramidConfig()
pyramid_manager = PyramidManager(pyramid_config)
