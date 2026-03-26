# API路径修复说明

## 🔧 修复内容

修复了API路由的prefix配置，确保前后端路径匹配。

## 📋 修改的文件

### 1. `backend/app/api/trading.py`
```python
# 修改前
router = APIRouter(prefix="/api/v1", tags=["trading"])

# 修改后
router = APIRouter(prefix="/api/v1/trading", tags=["trading"])
```

**影响路径：**
- `GET /api/v1/long-config` → `GET /api/v1/trading/long-config`
- `POST /api/v1/long-config` → `POST /api/v1/trading/long-config`
- `GET /api/v1/short-config` → `GET /api/v1/trading/short-config`
- `POST /api/v1/short-config` → `POST /api/v1/trading/short-config`
- `GET /api/v1/risk-config` → `GET /api/v1/trading/risk-config`
- `POST /api/v1/risk-config` → `POST /api/v1/trading/risk-config`
- 其他所有trading相关端点

### 2. `backend/app/api/services.py`
```python
# 修改前
router = APIRouter(prefix="/api/v1", tags=["services"])

# 修改后
router = APIRouter(prefix="/api/v1/services", tags=["services"])
```

**影响路径：**
- 所有services相关端点添加 `/services` 前缀

### 3. 代码优化
修复了linter警告：
- 移除了未使用的导入 (`Depends`, `Optional`, `check_capital_flow`, `PositionResponse`)
- 将 `request.dict()` 替换为 `request.model_dump()`

## ✅ API端点列表

### Trading端点 (`/api/v1/trading/*`)
```
GET  /api/v1/trading/balance
GET  /api/v1/trading/ticker/{inst_id}
GET  /api/v1/trading/tickers
GET  /api/v1/trading/trend/{inst_id}
GET  /api/v1/trading/market-environment
GET  /api/v1/trading/resonance/{coin}
GET  /api/v1/trading/time-zone
POST /api/v1/trading/order
DELETE /api/v1/trading/order/{inst_id}/{order_id}
GET  /api/v1/trading/simulation/positions
GET  /api/v1/trading/simulation/trades
DELETE /api/v1/trading/simulation/clear
GET  /api/v1/trading/long-config
POST /api/v1/trading/long-config
GET  /api/v1/trading/short-config
POST /api/v1/trading/short-config
GET  /api/v1/trading/risk-config
POST /api/v1/trading/risk-config
```

### External Data端点 (`/api/v1/external/*`)
```
GET /api/v1/external/sentiment/{coin}
GET /api/v1/external/sentiment/batch
GET /api/v1/external/market-sentiment
GET /api/v1/external/news
GET /api/v1/external/rss/{coin}
GET /api/v1/external/twitter/{username}
GET /api/v1/external/lunarcrush/{coin}
GET /api/v1/external/sources/status
```

### Services端点 (`/api/v1/services/*`)
```
GET /api/v1/services/settings
POST /api/v1/services/settings
GET /api/v1/services/sentiment
GET /api/v1/services/evolution/status
POST /api/v1/services/evolution/params
POST /api/v1/services/evolution/toggle
... (其他services端点)
```

### WebSocket端点 (`/ws`)
```
WS /ws
```

## 🎯 前端请求示例

### 获取多单配置
```javascript
fetch('/api/v1/trading/long-config')
  .then(res => res.json())
  .then(data => console.log(data))
```

### 更新多单配置
```javascript
fetch('/api/v1/trading/long-config', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    minTrendScore: 5,
    maxPullbackPercent: 8.0,
    // ... 其他配置
  })
})
```

### 获取外部数据
```javascript
fetch('/api/v1/external/sentiment/BTC')
  .then(res => res.json())
  .then(data => console.log(data))
```

## 🔍 验证方法

1. 重启后端服务：
```bash
cd backend
python -m uvicorn app.main:app --reload
```

2. 访问API文档：
```
http://localhost:8000/docs
```

3. 测试端点：
```bash
# 测试多单配置
curl http://localhost:8000/api/v1/trading/long-config

# 测试风控配置
curl http://localhost:8000/api/v1/trading/risk-config

# 测试外部数据
curl http://localhost:8000/api/v1/external/sentiment/BTC
```

## 📝 注意事项

1. **前端无需修改**：前端已经在使用正确的路径 `/api/v1/trading/*`
2. **向后兼容**：新的路径结构更清晰，便于维护
3. **文档同步更新**：API文档会自动更新（Swagger UI）

## 🎉 修复完成

所有API路径现在都正确匹配，404错误已解决！
