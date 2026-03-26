# 外部数据源功能 - 安装配置指南

## 1. 安装依赖包

在 `backend` 目录下运行：

```bash
cd backend
pip install aiohttp feedparser
```

或者更新 `requirements.txt` 添加：

```
aiohttp>=3.9.0
feedparser>=6.0.10
```

然后运行：

```bash
pip install -r requirements.txt
```

## 2. 配置API凭证

在项目根目录的 `.env` 文件中添加以下配置：

### Twitter API（可选）

如果需要使用Twitter搜索功能，需要配置Twitter API凭证：

1. 访问 https://developer.twitter.com/
2. 创建应用并获取API凭证
3. 在 `.env` 文件中添加：

```env
TWITTER_CONSUMER_KEY=your_consumer_key_here
TWITTER_CONSUMER_SECRET=your_consumer_secret_here
TWITTER_ACCESS_TOKEN=your_access_token_here
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret_here
```

### LunarCrush API（可选）

如果需要使用LunarCrush数据，需要配置LunarCrush API凭证：

1. 访问 https://lunarcrush.com/developers
2. 注册并获取API密钥
3. 在 `.env` 文件中添加：

```env
LUNARCRUSH_API_KEY=your_api_key_here
```

### 数据源开关

控制哪些数据源启用：

```env
# 启用RSS新闻监控（默认启用）
ENABLE_RSS_MONITOR=true

# 启用Twitter监控（需要配置API凭证）
ENABLE_TWITTER_MONITOR=false

# 启用LunarCrush监控（需要配置API凭证）
ENABLE_LUNARCRUSH_MONITOR=false
```

## 3. 测试功能

运行测试脚本验证功能是否正常：

```bash
cd backend
python test_external_data.py
```

测试脚本会自动测试：
- RSS新闻监控
- Twitter搜索（如果已配置）
- LunarCrush集成（如果已配置）
- 统一服务接口

## 4. 启动服务

启动后端服务：

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 5. 访问API

### 获取币种综合情绪
```bash
curl http://localhost:8000/api/v1/external/sentiment/BTC
```

### 获取整体市场情绪
```bash
curl http://localhost:8000/api/v1/external/market-sentiment
```

### 获取最新新闻
```bash
curl http://localhost:8000/api/v1/external/news?limit=10
```

### 获取数据源状态
```bash
curl http://localhost:8000/api/v1/external/sources/status
```

## 6. 前端集成

在前端组件中使用 `ExternalDataCard` 组件：

```vue
<template>
  <ExternalDataCard />
</template>

<script setup>
import ExternalDataCard from '@/components/ExternalDataCard.vue'
</script>
```

## 7. API端点列表

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/external/sentiment/{coin}` | GET | 获取币种综合情绪 |
| `/api/v1/external/sentiment/batch` | GET | 批量获取情绪 |
| `/api/v1/external/market-sentiment` | GET | 获取整体市场情绪 |
| `/api/v1/external/news` | GET | 获取最新新闻 |
| `/api/v1/external/rss/{coin}` | GET | 获取RSS情绪 |
| `/api/v1/external/twitter/{username}` | GET | 获取Twitter情绪 |
| `/api/v1/external/lunarcrush/{coin}` | GET | 获取LunarCrush情绪 |
| `/api/v1/external/sources/status` | GET | 获取数据源状态 |

## 8. 缓存说明

各数据源的缓存时间：

- RSS新闻: 15分钟
- Twitter数据: 5分钟
- LunarCrush数据: 5分钟

缓存文件存储在 `data/` 目录下：
- `rss_cache.json` - RSS新闻缓存
- `twitter_cache.json` - Twitter数据缓存
- `lunarcrush_cache.json` - LunarCrush数据缓存

## 9. 故障排除

### 问题1: RSS新闻无法获取

**解决方案**:
- 检查网络连接
- 确认RSS源地址可访问
- 查看后端日志获取详细错误信息

### 问题2: Twitter API请求失败

**解决方案**:
- 确认API凭证配置正确
- 检查Twitter API配额
- 确认应用权限设置正确

### 问题3: LunarCrush无数据返回

**解决方案**:
- 确认API密钥配置正确
- 检查API配额是否用尽
- 某些币种可能无LunarCrush数据

### 问题4: 前端无法加载组件

**解决方案**:
- 确认后端服务已启动
- 检查API地址配置
- 查看浏览器控制台错误信息

## 10. 性能优化建议

1. **合理使用缓存**: 避免频繁刷新，利用缓存机制
2. **批量查询**: 使用批量接口减少请求次数
3. **限制数据量**: 限制返回的新闻数量，避免传输大量数据
4. **异步处理**: 所有API调用都是异步的，不会阻塞主线程

## 11. 安全建议

1. **保护API凭证**: 不要将 `.env` 文件提交到版本控制
2. **限制API访问**: 考虑添加认证机制保护API端点
3. **监控用量**: 定期检查API配额使用情况
4. **日志记录**: 记录所有API调用，便于审计和调试

## 12. 更多信息

详细功能说明请参考:
- `EXTERNAL_DATA_FEATURES.md` - 功能特性文档
- `EXTERNAL_DATA_FEATURES.md` - API文档

如有问题，请查看:
- 后端日志: `logs/app.log`
- 前端控制台: 浏览器开发者工具
- API文档: `http://localhost:8000/docs`
