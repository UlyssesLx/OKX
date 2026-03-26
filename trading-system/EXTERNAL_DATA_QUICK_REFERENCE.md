# 外部数据源功能 - 快速参考

## 📦 安装依赖

```bash
pip install aiohttp feedparser
```

## ⚙️ 配置（.env）

```env
# Twitter（可选）
TWITTER_CONSUMER_KEY=xxx
TWITTER_CONSUMER_SECRET=xxx
TWITTER_ACCESS_TOKEN=xxx
TWITTER_ACCESS_TOKEN_SECRET=xxx

# LunarCrush（可选）
LUNARCRUSH_API_KEY=xxx

# 开关
ENABLE_RSS_MONITOR=true
ENABLE_TWITTER_MONITOR=false
ENABLE_LUNARCRUSH_MONITOR=false
```

## 🚀 快速开始

### 1. 测试功能

```bash
cd backend
python test_external_data.py
```

### 2. 启动服务

```bash
python -m uvicorn app.main:app --reload
```

### 3. 使用API

```bash
# 获取BTC情绪
curl http://localhost:8000/api/v1/external/sentiment/BTC

# 获取市场情绪
curl http://localhost:8000/api/v1/external/market-sentiment

# 获取新闻
curl http://localhost:8000/api/v1/external/news?limit=10
```

### 4. 前端使用

```vue
<template>
  <ExternalDataCard />
</template>

<script setup>
import ExternalDataCard from '@/components/ExternalDataCard.vue'
</script>
```

## 📊 API端点

| 端点 | 描述 |
|------|------|
| `/api/v1/external/sentiment/{coin}` | 币种综合情绪 |
| `/api/v1/external/sentiment/batch` | 批量查询 |
| `/api/v1/external/market-sentiment` | 整体市场情绪 |
| `/api/v1/external/news` | 最新新闻 |
| `/api/v1/external/rss/{coin}` | RSS情绪 |
| `/api/v1/external/twitter/{username}` | Twitter情绪 |
| `/api/v1/external/lunarcrush/{coin}` | LunarCrush情绪 |
| `/api/v1/external/sources/status` | 数据源状态 |

## 💻 Python代码示例

```python
from app.services.external_data_service import external_data_service

# 获取币种情绪
report = await external_data_service.get_coin_sentiment("BTC")
print(f"综合评分: {report.overall_score}/10")

# 批量查询
reports = await external_data_service.batch_get_sentiment(["BTC", "ETH", "SOL"])

# 获取市场情绪
market = await external_data_service.get_overall_market_sentiment()
```

## 📁 文件结构

```
backend/app/
├── api/external_data.py          # API端点
├── core/config.py               # 配置
├── services/
│   ├── external_data_service.py # 统一服务
│   └── external_data_sources/
│       ├── rss_monitor.py
│       ├── twitter_monitor.py
│       └── lunarcrush_monitor.py

frontend/src/components/
└── ExternalDataCard.vue        # 前端组件
```

## 📖 文档

- `EXTERNAL_DATA_FEATURES.md` - 功能详情
- `EXTERNAL_DATA_SETUP.md` - 安装配置
- `EXTERNAL_DATA_IMPLEMENTATION_SUMMARY.md` - 实现总结

## ⚡ 性能

- RSS: 15分钟缓存
- Twitter: 5分钟缓存
- LunarCrush: 5分钟缓存
- 响应时间: <5秒

## 🎯 评分权重

- RSS新闻: 40%
- Twitter: 20%
- LunarCrush: 40%

## 📝 缓存位置

```
data/
├── rss_cache.json
├── twitter_cache.json
└── lunarcrush_cache.json
```

## 🔧 故障排除

### RSS无法获取
- 检查网络连接
- 查看后端日志

### Twitter失败
- 确认API凭证配置
- 检查API配额

### LunarCrush无数据
- 确认API密钥
- 某些币种可能无数据

## 📞 支持

查看详细文档或查看日志：
- 后端日志: `logs/app.log`
- API文档: `http://localhost:8000/docs`
