# 外部数据源集成功能 - v1.0

## 概述

本功能模块整合了多个外部数据源，为交易系统提供丰富的市场情绪分析能力。

## 功能特性

### 1. RSS新闻监控
- **数据源**: CoinDesk、Cointelegraph、Decrypt
- **功能**: 监控加密货币新闻，提取正负面关键词，生成情绪评分
- **缓存**: 15分钟缓存机制，避免频繁请求
- **情绪分析**: 基于关键词库分析看涨/看跌情绪

### 2. Twitter搜索
- **API**: Twitter API v2
- **功能**: 搜索用户推文，分析市场情绪
- **数据**: 用户信息、推文内容、互动数据
- **情绪分析**: 基于推文内容分析情绪倾向

### 3. LunarCrush社交媒体情绪
- **API**: LunarCrush API v2
- **功能**: 获取专业社交媒体数据
- **数据**: 社交量、看涨看跌比例、Galaxy Score等
- **转换**: 将LunarCrush评分转换为系统趋势评分

### 4. 统一服务接口
- **综合评分**: 加权整合多源数据，生成综合情绪评分
- **批量查询**: 支持批量获取多个币种的情绪数据
- **缓存管理**: 智能缓存机制，减少API调用

## 文件结构

```
backend/
├── app/
│   ├── api/
│   │   └── external_data.py          # 外部数据API端点
│   ├── core/
│   │   └── config.py                 # 配置文件（新增API凭证）
│   └── services/
│       ├── external_data_service.py  # 统一服务管理器
│       └── external_data_sources/
│           ├── __init__.py
│           ├── rss_monitor.py         # RSS监控模块
│           ├── twitter_monitor.py    # Twitter监控模块
│           └── lunarcrush_monitor.py # LunarCrush监控模块

frontend/
└── src/
    └── components/
        └── ExternalDataCard.vue      # 外部数据展示组件
```

## API端点

### 1. 获取币种综合情绪
```
GET /api/v1/external/sentiment/{coin}
Query: twitter_username (可选)
```

### 2. 批量获取情绪
```
GET /api/v1/external/sentiment/batch
Query: coins (逗号分隔)
Query: usernames (JSON格式，可选)
```

### 3. 获取整体市场情绪
```
GET /api/v1/external/market-sentiment
```

### 4. 获取最新新闻
```
GET /api/v1/external/news
Query: limit (1-100)
```

### 5. 获取RSS情绪
```
GET /api/v1/external/rss/{coin}
```

### 6. 获取Twitter情绪
```
GET /api/v1/external/twitter/{username}
```

### 7. 获取LunarCrush情绪
```
GET /api/v1/external/lunarcrush/{coin}
```

### 8. 获取数据源状态
```
GET /api/v1/external/sources/status
```

## 配置说明

在 `.env` 文件中添加以下配置：

```env
# Twitter API凭证（可选）
TWITTER_CONSUMER_KEY=your_consumer_key
TWITTER_CONSUMER_SECRET=your_consumer_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret

# LunarCrush API凭证（可选）
LUNARCRUSH_API_KEY=your_api_key

# 外部数据源开关
ENABLE_RSS_MONITOR=true
ENABLE_TWITTER_MONITOR=false
ENABLE_LUNARCRUSH_MONITOR=false
```

## 依赖包

需要安装以下Python包：

```bash
pip install aiohttp feedparser
```

## 使用示例

### 后端使用

```python
from app.services.external_data_service import external_data_service

# 获取币种综合情绪
report = await external_data_service.get_coin_sentiment("BTC")
print(f"综合评分: {report.overall_score}/10")

# 批量获取
reports = await external_data_service.batch_get_sentiment(["BTC", "ETH", "SOL"])

# 获取整体市场情绪
market = await external_data_service.get_overall_market_sentiment()
```

### 前端使用

```vue
<ExternalDataCard />
```

## 评分权重

综合评分采用加权平均：

- RSS新闻: 40%
- Twitter: 20% (如果有数据)
- LunarCrush: 40%

## 缓存策略

- RSS新闻: 15分钟
- Twitter数据: 5分钟
- LunarCrush数据: 5分钟

## 关键词库

### 看涨关键词
bullish, surge, rally, breakout, moon, ATH, adoption, partnership, listing, institutional, ETF, approve, upgrade, mainnet, launch, growth, profit, gain, pump, 突破, 上涨, 利好, 合作, 采用, 升级, 启动, 盈利

### 看跌关键词
bearish, crash, dump, plunge, drop, fall, decline, hack, exploit, scam, fraud, ban, regulation, SEC, lawsuit, investigation, delist, suspend, risk, warning, 下跌, 暴跌, 黑客, 诈骗, 禁止, 监管, 诉讼, 风险, 警告

## 注意事项

1. **Twitter API限制**: 基础API只支持用户查询，不支持关键词搜索
2. **LunarCrush限制**: 需要注册获取API密钥
3. **频率限制**: 所有外部数据源都有频率限制，请合理使用缓存
4. **错误处理**: API失败时会返回null或空数据，不会影响主流程

## 未来扩展

1. 支持更多RSS源
2. 集成Reddit数据
3. 添加Telegram监控
4. 支持自定义关键词库
5. 添加情绪趋势图表
6. 实现实时推送通知

## 版本历史

- v1.0 (2025-03-21)
  - 初始版本
  - 实现RSS新闻监控
  - 实现Twitter搜索
  - 实现LunarCrush集成
  - 创建统一服务接口
  - 开发前端展示组件
