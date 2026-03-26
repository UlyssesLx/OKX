# Trading System 快速参考指南

## 🚀 快速开始

### 开发环境
```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 访问 http://localhost:5173
```

### 生产构建
```bash
# 构建生产版本
npm run build

# 预览构建结果
npm run preview
```

---

## 📁 项目结构

```
frontend/
├── src/
│   ├── api/              # API 接口层
│   │   └── index.ts     # 统一 API 导出
│   ├── assets/          # 静态资源
│   ├── components/      # Vue 组件 (18个)
│   │   ├── StatsCard.vue
│   │   ├── PositionsCard.vue
│   │   └── ...
│   ├── composables/     # 组合式函数
│   │   └── useWebSocket.ts
│   ├── layouts/         # 布局组件
│   │   └── MainLayout.vue
│   ├── router/          # 路由配置
│   │   └── index.ts
│   ├── stores/          # Pinia 状态管理
│   │   └── trading.ts
│   ├── styles/          # 全局样式
│   │   ├── variables.scss   # SCSS 变量
│   │   └── global.scss      # 全局样式
│   ├── types/           # TypeScript 类型
│   │   └── index.ts
│   ├── utils/           # 工具函数
│   │   └── format.ts
│   ├── views/           # 页面视图
│   │   └── Dashboard.vue
│   ├── App.vue          # 根组件
│   └── main.ts          # 入口文件
├── public/              # 公共静态资源
├── index.html           # HTML 模板
├── vite.config.ts       # Vite 配置
├── tsconfig.json        # TypeScript 配置
└── package.json         # 项目配置
```

---

## 🎨 样式系统

### SCSS 变量 (`styles/variables.scss`)

```scss
// 渐变色
$gradient-purple: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
$gradient-green: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
$gradient-pink: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
$gradient-blue: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
$gradient-yellow: linear-gradient(135deg, #fa709a 0%, #fee140 100%);

// 颜色
$primary-color: #667eea;
$success-color: #4caf50;
$warning-color: #ffc107;
$danger-color: #f44336;

// 背景色
$bg-page: #f5f7fa;
$bg-card: #ffffff;

// 圆角
$border-radius: 16px;
$border-radius-sm: 8px;

// 阴影
$shadow-sm: 0 2px 12px rgba(0, 0, 0, 0.04);
$shadow-md: 0 4px 16px rgba(0, 0, 0, 0.08);
$shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.12);

// 过渡
$transition-fast: 0.15s ease;
$transition-normal: 0.3s ease;
$transition-slow: 0.5s ease;
```

### 全局样式类 (`styles/global.scss`)

```html
<!-- 渐变图标 -->
<div class="gradient-icon purple md">
  <el-icon><TrendCharts /></el-icon>
</div>

<!-- 状态徽章 -->
<span class="status-badge success">成功</span>
<span class="status-badge warning">警告</span>
<span class="status-badge danger">错误</span>
<span class="status-badge info">信息</span>

<!-- 趋势分数 -->
<span class="trend-score bullish">看涨</span>
<span class="trend-score bearish">看跌</span>
<span class="trend-score neutral">中性</span>

<!-- 趋势类 -->
<span class="positive">正值/上涨</span>
<span class="negative">负值/下跌</span>

<!-- 页面标题区 -->
<div class="page-header">
  <div class="page-title">
    <div class="page-icon gradient-icon purple">
      <el-icon><TrendCharts /></el-icon>
    </div>
    <div class="title-info">
      <div class="page-title-text">页面标题</div>
      <div class="page-subtitle">副标题</div>
    </div>
  </div>
</div>

<!-- 统计卡片网格 -->
<div class="stats-grid">
  <StatsCard title="标题" value="值" icon="💰" trend="up" />
</div>
```

---

## 🔧 工具函数 (`utils/format.ts`)

```typescript
import {
  formatTime,
  formatDateTime,
  formatPrice,
  formatPercent,
  formatUsd,
  formatAmount,
  formatTimeAgo,
  getTrendClass,
  getTrendIcon,
  debounce,
  throttle,
  copyToClipboard,
  generateId
} from '@/utils/format'

// 格式化时间
formatTime(new Date()) // "14:30:45"
formatDateTime(new Date()) // "2024-03-21 14:30:45"
formatTimeAgo(new Date()) // "5分钟前"

// 格式化数值
formatPrice(123.4567) // "123.4567"
formatPercent(12.34) // "+12.34%"
formatUsd(123.45) // "+$123.45"
formatAmount(12.345678) // "12.345678"

// 获取趋势
getTrendClass(12.34) // "positive"
getTrendClass(-5.67) // "negative"
getTrendClass(0) // "neutral"

getTrendIcon(12.34) // "CaretTop"
getTrendIcon(-5.67) // "CaretBottom"
getTrendIcon(0) // "Minus"

// 工具函数
debounce(fn, 300) // 防抖
throttle(fn, 300) // 节流
copyToClipboard('text') // 复制到剪贴板
generateId() // 生成唯一ID
```

---

## 🧩 组件使用示例

### StatsCard 统计卡片

```vue
<StatsCard
  title="总资产"
  value="$1,234.56"
  icon="💰"
  trend="up"  // 'up' | 'down' | 'neutral'
/>
```

### Page Header 页面标题

```vue
<div class="page-header">
  <div class="page-title">
    <div class="page-icon gradient-icon purple">
      <el-icon><TrendCharts /></el-icon>
    </div>
    <div class="title-info">
      <div class="page-title-text">页面标题</div>
      <div class="page-subtitle">页面副标题</div>
    </div>
  </div>
  <div class="page-actions">
    <el-button type="primary">操作按钮</el-button>
  </div>
</div>
```

### Status Badge 状态徽章

```vue
<span class="status-badge success">
  <el-icon><SuccessFilled /></el-icon>
  成功
</span>

<span class="status-badge warning">
  <el-icon><WarningFilled /></el-icon>
  警告
</span>
```

### Gradient Icon 渐变图标

```vue
<!-- 紫色，中等尺寸 -->
<div class="gradient-icon purple md">
  <el-icon><TrendCharts /></el-icon>
</div>

<!-- 绿色，小尺寸 -->
<div class="gradient-icon green sm">
  <el-icon><SuccessFilled /></el-icon>
</div>

<!-- 蓝色，大尺寸 -->
<div class="gradient-icon blue lg">
  <el-icon><DataBoard /></el-icon>
</div>
```

---

## 📊 状态管理 (Pinia)

### Trading Store

```typescript
import { useTradingStore } from '@/stores/trading'

const store = useTradingStore()

// 状态数据
store.balance
store.marketEnvironment
store.timeZoneInfo
store.isConnected

// 计算属性
store.totalEquity
store.availableUsdt
store.positions
store.positionCount
store.marketScore

// 方法
await store.fetchBalance()
await store.fetchMarketEnvironment()
await store.fetchTimeZoneInfo()
store.setConnected(true)
store.updateFromWebSocket(message)
```

---

## 🔌 API 调用

### Trading API

```typescript
import { tradingApi } from '@/api'

// 获取余额
const balance = await tradingApi.getBalance()

// 获取行情
const tickers = await tradingApi.getTickers('SPOT')

// 获取市场环境
const env = await tradingApi.getMarketEnvironment()

// 下单
const order = await tradingApi.placeOrder({
  inst_id: 'BTC-USDT',
  side: 'buy',
  order_type: 'market',
  size: '0.001'
})

// 获取模拟统计
const simStats = await tradingApi.getSimulationStats()
```

---

## 🎯 常用模式

### 组件 Props 定义

```typescript
interface Props {
  title: string
  value: string
  icon: string
  trend?: 'up' | 'down' | 'neutral'
}

const props = withDefaults(defineProps<Props>(), {
  trend: 'neutral'
})
```

### 事件定义

```typescript
const emit = defineEmits<{
  refresh: []
  update: [value: string]
}>()

// 触发事件
emit('refresh')
emit('update', 'new value')
```

### 计算属性

```typescript
const filteredList = computed(() => {
  return list.value.filter(item => item.active)
})

const trendClass = computed(() => {
  if (value.value > 0) return 'positive'
  if (value.value < 0) return 'negative'
  return 'neutral'
})
```

### 生命周期

```typescript
onMounted(async () => {
  await fetchData()
  startInterval()
})

onUnmounted(() => {
  stopInterval()
  cleanup()
})
```

---

## 🎨 Element Plus 图标

### 常用图标

```typescript
import {
  // 趋势图标
  TrendCharts,
  DataAnalysis,
  DataBoard,
  ArrowUp,
  ArrowDown,
  CaretTop,
  CaretBottom,

  // 财务图标
  Wallet,
  Coin,
  Money,

  // 操作图标
  Setting,
  Refresh,
  Delete,
  Edit,
  Plus,
  Minus,
  Check,

  // 状态图标
  SuccessFilled,
  WarningFilled,
  CircleCloseFilled,
  InfoFilled,

  // 其他图标
  Document,
  Grid,
  Monitor,
  Lightning,
  Promotion,
  Select
} from '@element-plus/icons-vue'
```

### 图标使用

```vue
<template>
  <!-- 直接使用 -->
  <el-icon :size="24"><TrendCharts /></el-icon>

  <!-- 按钮中 -->
  <el-button>
    <el-icon><Refresh /></el-icon>
    刷新
  </el-button>

  <!-- 渐变图标包装 -->
  <div class="gradient-icon purple md">
    <el-icon><TrendCharts /></el-icon>
  </div>
</template>
```

---

## 🐛 调试技巧

### 开发工具
```typescript
// Vue DevTools
// 在浏览器中安装 Vue DevTools 扩展

// 控制台日志
console.log('Debug info:', data)

// 性能监控
console.time('operation')
// ... 操作
console.timeEnd('operation')
```

### 错误处理
```typescript
try {
  const result = await api.call()
} catch (error) {
  console.error('API Error:', error)
  ElMessage.error('操作失败')
}
```

---

## 📝 代码规范

### 命名规范
```typescript
// 组件文件：PascalCase
StatsCard.vue
Dashboard.vue

// 函数/变量：camelCase
formatPrice()
totalEquity

// 常量：UPPER_SNAKE_CASE
const MAX_SIZE = 100

// 类型：PascalCase
interface TradeLog {
  // ...
}

type TrendType = 'up' | 'down' | 'neutral'
```

### 组件结构
```vue
<script setup lang="ts">
// 1. 导入
import { ref, computed } from 'vue'
import { TradingApi } from '@/api'

// 2. Props 和 Emits
interface Props { }
const props = defineProps<Props>()
const emit = defineEmits<{ ... }>()

// 3. 响应式数据
const count = ref(0)

// 4. 计算属性
const doubleCount = computed(() => count.value * 2)

// 5. 方法
function increment() {
  count.value++
}

// 6. 生命周期
onMounted(() => { })
</script>

<template>
  <!-- 模板 -->
</template>

<style lang="scss" scoped>
/* 样式 */
</style>
```

---

## 🔗 有用链接

- [Vue 3 文档](https://cn.vuejs.org/)
- [Element Plus 文档](https://element-plus.org/zh-CN/)
- [Pinia 文档](https://pinia.vuejs.org/zh/)
- [Vite 文档](https://cn.vitejs.dev/)
- [TypeScript 文档](https://www.typescriptlang.org/docs/)

---

## 💡 常见问题

### 如何修改主题颜色？
修改 `src/styles/variables.scss` 中的颜色变量。

### 如何添加新组件？
在 `src/components/` 目录下创建 `.vue` 文件，遵循组件命名规范。

### 如何添加新页面？
在 `src/views/` 目录下创建页面组件，然后在 `src/router/index.ts` 中配置路由。

### 如何调用后端 API？
使用 `tradingApi` 对象调用对应方法，具体方法参考 `src/api/index.ts`。

### 如何优化构建性能？
1. 使用 `vite.config.ts` 中的代码分割配置
2. 启用 tree-shaking
3. 使用生产环境构建

---

**更新日期**: 2026-03-21
