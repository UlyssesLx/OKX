<template>
  <div class="enhanced-dashboard">
    <!-- 页面标题区 -->
    <div class="dashboard-header">
      <div class="header-left">
        <div class="header-icon gradient-icon-purple">
          <el-icon :size="28"><TrendCharts /></el-icon>
        </div>
        <div class="header-title">
          <h1>交易仪表板</h1>
          <p class="subtitle">实时监控 · 智能决策 · 数据驱动</p>
        </div>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="refreshData" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新数据
        </el-button>
        <el-button @click="exportReport">
          <el-icon><Download /></el-icon>
          导出报告
        </el-button>
      </div>
    </div>

    <!-- 统计卡片区 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :xs="24" :sm="12" :md="6" v-for="stat in stats" :key="stat.key">
        <div class="stat-card" :class="stat.colorClass">
          <div class="stat-icon" :class="stat.iconClass">
            <el-icon :size="24"><component :is="stat.icon" /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.label }}</div>
            <div class="stat-change" v-if="stat.change" :class="stat.changeClass">
              <el-icon><component :is="stat.changeIcon" /></el-icon>
              {{ stat.change }}
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 主要内容区 -->
    <el-row :gutter="16" class="content-row">
      <!-- 左侧：市场情绪 -->
      <el-col :xs="24" :lg="12">
        <el-card class="content-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>市场情绪</span>
              <el-tag :type="getSentimentType(marketSentiment.score)">
                {{ marketSentiment.score }}/10
              </el-tag>
            </div>
          </template>
          <div class="sentiment-content">
            <div class="sentiment-gauge">
              <div class="gauge-value">{{ marketSentiment.score }}</div>
              <div class="gauge-label">综合评分</div>
            </div>
            <div class="sentiment-breakdown">
              <div class="breakdown-item">
                <span class="label">RSS新闻</span>
                <el-progress
                  :percentage="marketSentiment.rss * 10"
                  :color="getProgressColor(marketSentiment.rss)"
                  :show-text="false"
                />
                <span class="value">{{ marketSentiment.rss }}/10</span>
              </div>
              <div class="breakdown-item">
                <span class="label">Twitter</span>
                <el-progress
                  :percentage="marketSentiment.twitter * 10"
                  :color="getProgressColor(marketSentiment.twitter)"
                  :show-text="false"
                />
                <span class="value">{{ marketSentiment.twitter }}/10</span>
              </div>
              <div class="breakdown-item">
                <span class="label">LunarCrush</span>
                <el-progress
                  :percentage="marketSentiment.lunarcrush * 10"
                  :color="getProgressColor(marketSentiment.lunarcrush)"
                  :show-text="false"
                />
                <span class="value">{{ marketSentiment.lunarcrush }}/10</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：最新新闻 -->
      <el-col :xs="24" :lg="12">
        <el-card class="content-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>最新新闻</span>
              <el-tag size="small">{{ newsList.length }} 条</el-tag>
            </div>
          </template>
          <div class="news-list">
            <div
              v-for="(news, index) in newsList.slice(0, 5)"
              :key="index"
              class="news-item"
            >
              <div class="news-icon" :class="getSentimentClass(news.sentiment_score)">
                <el-icon><Document /></el-icon>
              </div>
              <div class="news-content">
                <div class="news-title">{{ news.title }}</div>
                <div class="news-meta">
                  <span class="news-source">{{ news.source }}</span>
                  <span class="news-time">{{ formatTime(news.timestamp) }}</span>
                </div>
              </div>
              <div class="news-sentiment" :class="getSentimentClass(news.sentiment_score)">
                {{ news.sentiment_score }}
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 币种情绪表格 -->
    <el-row :gutter="16" class="content-row">
      <el-col :span="24">
        <el-card class="content-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>币种情绪分析</span>
              <div class="header-actions">
                <el-input
                  v-model="searchKeyword"
                  placeholder="搜索币种..."
                  prefix-icon="Search"
                  clearable
                  style="width: 200px; margin-right: 10px"
                />
                <el-select
                  v-model="sentimentFilter"
                  placeholder="情绪筛选"
                  clearable
                  style="width: 120px"
                >
                  <el-option label="全部" value="" />
                  <el-option label="强烈看涨" value="bullish" />
                  <el-option label="中性" value="neutral" />
                  <el-option label="强烈看跌" value="bearish" />
                </el-select>
              </div>
            </div>
          </template>
          <el-table
            :data="filteredCoinList"
            stripe
            style="width: 100%"
            :row-class-name="getRowClassName"
          >
            <el-table-column prop="coin" label="币种" width="100" />
            <el-table-column label="情绪评分" width="150">
              <template #default="{ row }">
                <el-progress
                  :percentage="row.combined_score * 10"
                  :color="getProgressColor(row.combined_score)"
                />
              </template>
            </el-table-column>
            <el-table-column label="RSS" width="120">
              <template #default="{ row }">
                <el-tag :type="getSentimentType(row.rss_score)" size="small">
                  {{ row.rss_score }}/10
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="Twitter" width="120">
              <template #default="{ row }">
                <el-tag :type="getSentimentType(row.twitter_score)" size="small">
                  {{ row.twitter_score }}/10
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="LunarCrush" width="130">
              <template #default="{ row }">
                <el-tag :type="getSentimentType(row.lunarcrush_score)" size="small">
                  {{ row.lunarcrush_score }}/10
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="news_count" label="新闻数" width="100" />
            <el-table-column prop="social_score" label="社交评分" width="120">
              <template #default="{ row }">
                <span v-if="row.social_score">{{ row.social_score }}/10</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="更新时间" min-width="180">
              <template #default="{ row }">
                {{ formatTime(row.timestamp) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 底部：配置和状态 -->
    <el-row :gutter="16" class="content-row">
      <el-col :xs="24" :md="8">
        <el-card class="content-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>回调加仓状态</span>
              <el-switch v-model="pullbackEnabled" />
            </div>
          </template>
          <div class="pullback-status">
            <div class="status-item">
              <span class="label">回调阈值</span>
              <span class="value">{{ pullbackThreshold }}%</span>
            </div>
            <div class="status-item">
              <span class="label">冷却时间</span>
              <span class="value">{{ pullbackCooldown }}分钟</span>
            </div>
            <div class="status-item">
              <span class="label">记录数量</span>
              <span class="value">{{ pullbackRecordsCount }}</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="8">
        <el-card class="content-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>数据源状态</span>
            </div>
          </template>
          <div class="source-status">
            <div class="source-item" v-for="source in sources" :key="source.name">
              <el-icon :size="16" :color="source.active ? '#67C23A' : '#F56C6C'">
                <CircleCheck v-if="source.active" />
                <CircleClose v-else />
              </el-icon>
              <span class="name">{{ source.name }}</span>
              <span class="status">{{ source.active ? '正常' : '离线' }}</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="8">
        <el-card class="content-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>系统状态</span>
            </div>
          </template>
          <div class="system-status">
            <div class="status-item">
              <span class="label">运行时间</span>
              <span class="value">{{ uptime }}</span>
            </div>
            <div class="status-item">
              <span class="label">最后更新</span>
              <span class="value">{{ lastUpdate }}</span>
            </div>
            <div class="status-item">
              <span class="label">API延迟</span>
              <span class="value">{{ apiLatency }}ms</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  TrendCharts, Refresh, Download, Document, Search,
  CircleCheck, CircleClose, ArrowUp, ArrowDown, Minus
} from '@element-plus/icons-vue'

// ============================================
// 数据状态
// ============================================
const loading = ref(false)
const searchKeyword = ref('')
const sentimentFilter = ref('')

// 统计数据
const stats = ref([
  {
    key: 'total_profit',
    label: '总盈利',
    value: '$1,234.56',
    change: '+12.3%',
    changeClass: 'positive',
    changeIcon: ArrowUp,
    colorClass: 'purple',
    iconClass: 'gradient-icon-purple',
    icon: TrendCharts
  },
  {
    key: 'win_rate',
    label: '胜率',
    value: '68.5%',
    change: '+3.2%',
    changeClass: 'positive',
    changeIcon: ArrowUp,
    colorClass: 'green',
    iconClass: 'gradient-icon-green',
    icon: TrendCharts
  },
  {
    key: 'total_trades',
    label: '交易次数',
    value: '156',
    change: '-2.1%',
    changeClass: 'negative',
    changeIcon: ArrowDown,
    colorClass: 'blue',
    iconClass: 'gradient-icon-blue',
    icon: TrendCharts
  },
  {
    key: 'active_positions',
    label: '活跃持仓',
    value: '5',
    change: '0%',
    changeClass: 'neutral',
    changeIcon: Minus,
    colorClass: 'pink',
    iconClass: 'gradient-icon-pink',
    icon: TrendCharts
  }
])

// 市场情绪
const marketSentiment = ref({
  score: 7.2,
  rss: 6.8,
  twitter: 7.5,
  lunarcrush: 7.1
})

// 新闻列表
const newsList = ref([
  {
    title: '比特币突破历史新高，市场情绪高涨',
    source: 'CoinDesk',
    timestamp: Date.now(),
    sentiment_score: 9
  },
  {
    title: '以太坊Layer2解决方案获得重大突破',
    source: 'Cointelegraph',
    timestamp: Date.now() - 3600000,
    sentiment_score: 8
  },
  {
    title: 'SEC推迟比特币ETF决策至下月',
    source: 'Decrypt',
    timestamp: Date.now() - 7200000,
    sentiment_score: 4
  }
])

// 币种列表
const coinList = ref([
  {
    coin: 'BTC',
    combined_score: 8.5,
    rss_score: 8.2,
    twitter_score: 8.8,
    lunarcrush_score: 8.5,
    news_count: 12,
    social_score: 8.7,
    timestamp: Date.now()
  },
  {
    coin: 'ETH',
    combined_score: 7.8,
    rss_score: 7.5,
    twitter_score: 8.0,
    lunarcrush_score: 7.9,
    news_count: 8,
    social_score: 7.6,
    timestamp: Date.now()
  },
  {
    coin: 'XRP',
    combined_score: 6.5,
    rss_score: 6.2,
    twitter_score: 6.8,
    lunarcrush_score: 6.5,
    news_count: 5,
    social_score: 6.4,
    timestamp: Date.now()
  }
])

// 回调加仓配置
const pullbackEnabled = ref(true)
const pullbackThreshold = ref(97)
const pullbackCooldown = ref(60)
const pullbackRecordsCount = ref(3)

// 数据源状态
const sources = ref([
  { name: 'RSS', active: true },
  { name: 'Twitter', active: false },
  { name: 'LunarCrush', active: true }
])

// 系统状态
const uptime = ref('2天 3小时 45分钟')
const lastUpdate = ref(formatTime(Date.now()))
const apiLatency = ref(125)

// ============================================
// 计算属性
// ============================================
const filteredCoinList = computed(() => {
  let filtered = coinList.value

  // 搜索过滤
  if (searchKeyword.value) {
    filtered = filtered.filter(coin =>
      coin.coin.toLowerCase().includes(searchKeyword.value.toLowerCase())
    )
  }

  // 情绪过滤
  if (sentimentFilter.value) {
    filtered = filtered.filter(coin => {
      const score = coin.combined_score
      if (sentimentFilter.value === 'bullish') return score >= 7
      if (sentimentFilter.value === 'neutral') return score >= 4 && score < 7
      if (sentimentFilter.value === 'bearish') return score < 4
      return true
    })
  }

  return filtered
})

// ============================================
// 方法
// ============================================
const refreshData = async () => {
  loading.value = true
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    lastUpdate.value = formatTime(Date.now())
    ElMessage.success('数据刷新成功')
  } catch (error) {
    ElMessage.error('数据刷新失败')
  } finally {
    loading.value = false
  }
}

const exportReport = () => {
  ElMessage.success('报告导出成功')
}

const getSentimentType = (score) => {
  if (score >= 7) return 'success'
  if (score >= 4) return 'warning'
  return 'danger'
}

const getSentimentClass = (score) => {
  if (score >= 7) return 'sentiment-bullish'
  if (score >= 4) return 'sentiment-neutral'
  return 'sentiment-bearish'
}

const getProgressColor = (score) => {
  if (score >= 7) return '#67C23A'
  if (score >= 4) return '#E6A23C'
  return '#F56C6C'
}

const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return date.toLocaleDateString()
}

const getRowClassName = ({ row }) => {
  if (row.combined_score >= 7) return 'row-bullish'
  if (row.combined_score < 4) return 'row-bearish'
  return ''
}

// ============================================
// 生命周期
// ============================================
onMounted(() => {
  refreshData()
})
</script>

<style scoped lang="scss">
.enhanced-dashboard {
  padding: 20px;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  min-height: 100vh;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 20px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.12);

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;

    .header-icon {
      width: 56px;
      height: 56px;
      border-radius: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
    }

    .header-title {
      h1 {
        margin: 0 0 4px 0;
        font-size: 24px;
        font-weight: 600;
        color: #ffffff;
      }

      .subtitle {
        margin: 0;
        font-size: 14px;
        color: rgba(255, 255, 255, 0.7);
      }
    }
  }

  .header-actions {
    display: flex;
    gap: 12px;
  }
}

.stats-row {
  margin-bottom: 20px;

  .stat-card {
    background: rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 20px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    gap: 16px;

    &:hover {
      transform: translateY(-5px);
      background: rgba(255, 255, 255, 0.12);
      border-color: rgba(255, 255, 255, 0.2);
    }

    .stat-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
    }

    .stat-content {
      flex: 1;

      .stat-value {
        font-size: 24px;
        font-weight: 600;
        color: #ffffff;
        margin-bottom: 4px;
      }

      .stat-label {
        font-size: 14px;
        color: rgba(255, 255, 255, 0.7);
        margin-bottom: 4px;
      }

      .stat-change {
        font-size: 12px;
        display: flex;
        align-items: center;
        gap: 4px;

        &.positive {
          color: #4caf50;
        }

        &.negative {
          color: #f44336;
        }

        &.neutral {
          color: rgba(255, 255, 255, 0.5);
        }
      }
    }
  }
}

.content-row {
  margin-bottom: 20px;
}

.content-card {
  border-radius: 16px;
  border: none;
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;

  &:hover {
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    background: rgba(255, 255, 255, 0.1);
  }

  :deep(.el-card__header) {
    border-bottom: 1px solid rgba(255, 255, 255, 0.12);
    padding: 16px 20px;
  }

  :deep(.el-card__body) {
    padding: 20px;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 16px;
    font-weight: 600;
    color: #ffffff;

    .header-actions {
      display: flex;
      align-items: center;
    }
  }
}

.sentiment-content {
  display: flex;
  gap: 24px;

  .sentiment-gauge {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 16px;
    padding: 30px;
    color: #fff;

    .gauge-value {
      font-size: 48px;
      font-weight: 700;
      margin-bottom: 8px;
    }

    .gauge-label {
      font-size: 14px;
      opacity: 0.9;
    }
  }

  .sentiment-breakdown {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 16px;

    .breakdown-item {
      display: flex;
      align-items: center;
      gap: 12px;

      .label {
        width: 80px;
        font-size: 14px;
        color: rgba(255, 255, 255, 0.7);
      }

      :deep(.el-progress) {
        flex: 1;
      }

      .value {
        width: 40px;
        text-align: right;
        font-size: 14px;
        color: #ffffff;
        font-weight: 600;
      }
    }
  }
}

.news-list {
  .news-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid #f0f0f0;

    &:last-child {
      border-bottom: none;
    }

    .news-icon {
      width: 36px;
      height: 36px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;

      &.sentiment-bullish {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
      }

      &.sentiment-neutral {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
      }

      &.sentiment-bearish {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
      }
    }

    .news-content {
      flex: 1;

      .news-title {
        font-size: 14px;
        color: #ffffff;
        margin-bottom: 4px;
        line-height: 1.5;
      }

      .news-meta {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.6);
        display: flex;
        gap: 12px;
      }
    }

    .news-sentiment {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      font-weight: 600;

      &.sentiment-bullish {
        background: rgba(76, 175, 80, 0.2);
        color: #4caf50;
      }

      &.sentiment-neutral {
        background: rgba(255, 255, 255, 0.1);
        color: rgba(255, 255, 255, 0.7);
      }

      &.sentiment-bearish {
        background: rgba(244, 67, 54, 0.2);
        color: #f44336;
      }
    }
  }
}

:deep(.el-table) {
  .row-bullish {
    background-color: #f0f9ff;
  }

  .row-bearish {
    background-color: #fef0f0;
  }
}

.pullback-status,
.source-status,
.system-status {
  display: flex;
  flex-direction: column;
  gap: 16px;

  .status-item {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .label {
      font-size: 14px;
      color: rgba(255, 255, 255, 0.7);
    }

    .value {
      font-size: 14px;
      color: #ffffff;
      font-weight: 600;
    }
  }
}

.source-item {
  display: flex;
  align-items: center;
  gap: 8px;

  .name {
    flex: 1;
    font-size: 14px;
    color: #ffffff;
  }

  .status {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.6);
  }
}

// 渐变图标类
.gradient-icon-purple {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.gradient-icon-green {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
}

.gradient-icon-pink {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.gradient-icon-blue {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

@media (max-width: 768px) {
  .dashboard-header {
    flex-direction: column;
    gap: 16px;
  }

  .sentiment-content {
    flex-direction: column;
  }
}
</style>
