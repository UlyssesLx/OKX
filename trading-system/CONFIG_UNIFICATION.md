# 配置系统统一方案

## 问题背景

系统存在两套独立的配置系统，导致配置不同步、管理混乱：

1. **trading_engine.py** 中的 `TradingConfig` 类
2. **position_manager.py** 中的 `PositionProfitConfig` 类
3. **config.py** 中的 `Settings` 类（环境变量配置）

## 问题表现

1. 前端保存风控配置时，需要同时更新两套配置系统
2. `time_stop_hours` 和 `dynamic_bands_enabled` 等配置在两处重复定义
3. 配置可能不同步，导致行为不一致

## 解决方案

### 统一配置源

将 **trading_engine.py** 中的 `TradingConfig` 作为唯一的配置源。

### 修改内容

#### 1. **trading.py** (API 路由)

**修改前：**
```python
@router.post("/risk-config")
async def update_risk_config(config: dict):
    # 更新 trading_engine
    trading_engine.config.time_stop_hours = config.get("timeStopHours", 48.0)
    trading_engine.config.dynamic_bands_enabled = config.get("dynamicBandsEnabled", False)

    # 同步到 position_manager
    position_manager.update_config({
        "time_stop_hours": config.get("timeStopHours", 48.0),
        "dynamic_bands_enabled": config.get("dynamicBandsEnabled", False)
    })
```

**修改后：**
```python
@router.post("/risk-config")
async def update_risk_config(config: dict):
    # 只更新 trading_engine（统一配置源）
    trading_engine.config.time_stop_hours = config.get("timeStopHours", 48.0)
    trading_engine.config.dynamic_bands_enabled = config.get("dynamicBandsEnabled", False)

    # 保存到持久化文件
    trading_engine._save_persistent_state()
```

#### 2. **services.py** (API 路由)

**修改前：**
```python
@router.get("/position/config")
async def get_position_config():
    return position_manager.get_config()

@router.post("/position/config")
async def update_position_config(config: dict):
    position_manager.update_config(config)
    return {"success": True, "config": position_manager.get_config()}
```

**修改后：**
```python
@router.get("/position/config")
async def get_position_config():
    # 从 trading_engine 读取配置
    return {
        "stop_loss_percent": trading_engine.config.stop_loss_percent,
        "take_profit_percent": trading_engine.config.take_profit_percent,
        "time_stop_hours": trading_engine.config.time_stop_hours,
        "dynamic_bands_enabled": trading_engine.config.dynamic_bands_enabled
    }

@router.post("/position/config")
async def update_position_config(config: dict):
    # 更新 trading_engine（统一配置源）
    if "stop_loss_percent" in config:
        trading_engine.config.stop_loss_percent = config["stop_loss_percent"]
    # ...

    # 保存到持久化文件
    trading_engine._save_persistent_state()
```

#### 3. **position_manager.py** (持仓管理)

**修改前：**
```python
class PositionManager:
    def __init__(self, data_dir: str = "./data"):
        self.config = PositionProfitConfig()  # 独立配置

    def add_position(self, coin: str, entry_price: float, amount: float, ...):
        if stop_loss is None:
            stop_loss = entry_price * (1 + self.config.stop_loss_percent / 100)
```

**修改后：**
```python
class PositionManager:
    def __init__(self, data_dir: str = "./data"):
        # 保留 config 字段以兼容旧代码，但实际值从 trading_engine 获取
        self.config = PositionProfitConfig()

    def _get_config(self) -> PositionProfitConfig:
        """从 trading_engine 获取配置（统一配置源）"""
        from app.services.trading_engine import trading_engine
        return PositionProfitConfig(
            stop_loss_percent=trading_engine.config.stop_loss_percent,
            take_profit_percent=trading_engine.config.take_profit_percent,
            time_stop_hours=trading_engine.config.time_stop_hours,
            dynamic_bands_enabled=trading_engine.config.dynamic_bands_enabled
        )

    def add_position(self, coin: str, entry_price: float, amount: float, ...):
        config = self._get_config()  # 从 trading_engine 读取
        if stop_loss is None:
            stop_loss = entry_price * (1 + config.stop_loss_percent / 100)
```

### 配置层级

```
前端 (StrategyConfigCard.vue)
    ↓ POST /api/v1/trading/risk-config
后端 API (trading.py)
    ↓ 更新
trading_engine.config (TradingConfig) ← 统一配置源
    ↓ _save_persistent_state()
持久化文件 (data/trading_state.json)
    ↓ _load_persistent_state()
trading_engine.config (重启后恢复)
    ↓ _get_config()
position_manager._get_config() ← 读取配置
```

## 配置字段映射

| 配置项 | TradingConfig | PositionProfitConfig | 说明 |
|--------|--------------|---------------------|------|
| 止损比例 | `stop_loss_percent` | `stop_loss_percent` | 统一到 TradingConfig |
| 止盈比例 | `take_profit_percent` | `take_profit_percent` | 统一到 TradingConfig |
| 时间止损 | `time_stop_hours` | `time_stop_hours` | 统一到 TradingConfig |
| 动态波段 | `dynamic_bands_enabled` | `dynamic_bands_enabled` | 统一到 TradingConfig |
| 移动止损 | - | `trailing_stop_enabled` | 保留在 PositionProfitConfig |
| 移动止损触发 | - | `trailing_stop_trigger` | 保留在 PositionProfitConfig |
| 移动止损距离 | - | `trailing_stop_distance` | 保留在 PositionProfitConfig |

## 向后兼容性

- `position_manager.config` 字段保留，仅用于兼容旧代码
- `position_manager.update_config()` 方法保留，但已废弃，会调用 trading_engine 更新
- 所有内部方法通过 `_get_config()` 从 trading_engine 读取最新配置

## 测试验证

1. 前端修改风控配置（时间止损、动态波段）
2. 验证 trading_engine.config 已更新
3. 验证 position_manager 读取到最新配置
4. 重启服务后验证配置已持久化恢复

## 注意事项

1. **不要直接修改 `position_manager.config`**：应通过 `trading_engine.config` 修改
2. **API 更新配置后调用 `_save_persistent_state()`**：确保持久化
3. **前端调用统一 API**：使用 `/api/v1/trading/risk-config` 而非 `/api/v1/position/config`

## 配置持久化

配置通过 `trading_engine._save_persistent_state()` 保存到 `data/trading_state.json`：

```json
{
  "config": {
    "time_stop_hours": 48.0,
    "dynamic_bands_enabled": false
  },
  "position_entry_times": {}
}
```
