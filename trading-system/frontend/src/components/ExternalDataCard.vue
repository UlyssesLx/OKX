<template>
  <div class="external-data-card">
    <!-- 标题区 -->
    <div class="card-header">
      <div class="header-left">
        <div class="gradient-icon">
          <el-icon :size="28"><DataAnalysis /></el-icon>
        </div>
        <div class="header-title">
          <h3>外部数据源</h3>
          <p class="subtitle">RSS新闻 · Twitter · LunarCrush</p>
        </div>
      </div>
      <div class="header-actions">
        <el-button
          :type="overallScore >= 7 ? 'success' : overallScore <= 4 ? 'danger' : 'primary'"
          :icon="Refresh"
          @click="refreshData"
          :loading="loading"
        >
          刷新数据
        </el-button>
      </div>
    </div>

    <!-- 整体市场情绪 -->
    <div class="market-sentiment-section">
      <div class="section-title">
        <el-icon><TrendCharts /></el-icon>
        <span>整体市场情绪</span>
      </div>
      <div class="sentiment-display">
        <div class="score-circle">
          <div class="score-value" :class="sentimentClass">
            {{ marketSentiment.score }}/10
          </div>
          <div class="score-label">
            {{ sentimentText }}
          </div>
        </div>
        <div class="sentiment-stats">
          <div class="stat-item">
            <span class="stat-label">新闻数量</span>
            <span class="stat-value">{{ marketSentiment.news_count }}</span>
          </div>
          <div class="stat-item bullish">
            <span class="stat-label">看涨</span>
            <span class="stat-value">{{ marketSentiment.bullish_count }}</span>
          </div>
          <div class="stat-item bearish">
            <span class="stat-label">看跌</span>
            <span class="stat-value">{{ marketSentiment.bearish_count }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 最新新闻 -->
    <div class="news-section">
      <div class="section-title">
        <el-icon><Document /></el-icon>
        <span>最新新闻</span>
      </div>
      <div class="news-list">
        <div
          v-for="item in latestNews.slice(0, 5)"
          :key="item.link"
          class="news-item"
        >
          <div class="news-source">{{ item.source }}</div>
          <div class="news-title">{{ item.title }}</div>
          <div class="news-meta">
            <span class="news-time">{{ formatTime(item.timestamp) }}</span>
            <el-tag
              :type="item.sentiment.score >= 6 ? 'success' : item.sentiment.score <= 4 ? 'danger' : 'info'"
              size="small"
            >
              {{ item.sentiment.score }}/10
            </el-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- 币种情绪查询 -->
    <div class="coin-query-section">
      <div class="section-title">
        <el-icon><Search /></el-icon>
        <span>币种情绪查询</span>
      </div>
      <div class="query-input">
        <el-input
          v-model="queryCoin"
          placeholder="输入币种符号（如BTC、ETH）"
          clearable
          @keyup.enter="queryCoinSentiment"
        >
          <template #append>
            <el-button :icon="Search" @click="queryCoinSentiment">查询</el-button>
          </template>
        </el-input>
      </div>

      <!-- 查询结果 -->
      <div v-if="coinSentiment" class="coin-sentiment-result">
        <div class="coin-header">
          <h4>{{ coinSentiment.coin }} 综合情绪</h4>
          <div class="overall-score" :class="getSentimentClass(coinSentiment.overall_score)">
            {{ coinSentiment.overall_score }}/10
          </div>
        </div>

        <el-tabs v-model="activeTab">
          <el-tab-pane label="RSS新闻" name="rss">
            <div v-if="coinSentiment.rss_sentiment" class="tab-content">
              <div class="sentiment-item">
                <span class="label">情绪评分:</span>
                <span class="value">{{ coinSentiment.rss_sentiment.score }}/10</span>
              </div>
              <div class="sentiment-item">
                <span class="label">相关新闻:</span>
                <span class="value">{{ coinSentiment.rss_sentiment.news_count }}条</span>
              </div>
              <div class="sentiment-item">
                <span class="label">看涨/看跌:</span>
                <span class="value">
                  {{ coinSentiment.rss_sentiment.bullish_count }} / {{ coinSentiment.rss_sentiment.bearish_count }}
                </span>
              </div>
            </div>
            <div v-else class="no-data">24小时内无相关新闻</div>
          </el-tab-pane>

          <el-tab-pane label="LunarCrush" name="lunarcrush">
            <div v-if="coinSentiment.lunarcrush_sentiment" class="tab-content">
              <div class="sentiment-item">
                <span class="label">情绪评分:</span>
                <span class="value">{{ coinSentiment.lunarcrush_sentiment.score }}/5</span>
              </div>
              <div class="sentiment-item">
                <span class="label">趋势评分:</span>
                <span class="value">{{ coinSentiment.lunarcrush_sentiment.trend_score }}/10</span>
              </div>
              <div class="sentiment-item">
                <span class="label">看涨比例:</span>
                <span class="value">{{ coinSentiment.lunarcrush_sentiment.bullish_percent.toFixed(1) }}%</span>
              </div>
              <div class="sentiment-item">
                <span class="label">社交量:</span>
                <span class="value">{{ formatNumber(coinSentiment.lunarcrush_sentiment.social_volume) }}</span>
              </div>
              <div class="sentiment-item">
                <span class="label">Galaxy Score:</span>
                <span class="value">{{ coinSentiment.lunarcrush_sentiment.galaxy_score.toFixed(0) }}</span>
              </div>
            </div>
            <div v-else class="no-data">无LunarCrush数据</div>
          </el-tab-pane>

          <el-tab-pane label="Twitter" name="twitter">
            <div v-if="coinSentiment.twitter_sentiment" class="tab-content">
              <div class="sentiment-item">
                <span class="label">用户:</span>
                <span class="value">@{{ coinSentiment.twitter_sentiment.username }}</span>
              </div>
              <div class="sentiment-item">
                <span class="label">情绪评分:</span>
                <span class="value">{{ coinSentiment.twitter_sentiment.sentiment_score }}/10</span>
              </div>
              <div class="sentiment-item">
                <span class="label">推文数:</span>
                <span class="value">{{ coinSentiment.twitter_sentiment.tweet_count }}</span>
              </div>
              <div class="sentiment-item">
                <span class="label">粉丝数:</span>
                <span class="value">{{ formatNumber(coinSentiment.twitter_sentiment.followers_count) }}</span>
              </div>
            </div>
            <div v-else class="no-data">未指定Twitter用户或未配置API</div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <!-- 数据源状态 -->
    <div class="data-sources-status">
      <div class="section-title">
        <el-icon><Connection /></el-icon>
        <span>数据源状态</span>
      </div>
      <div class="sources-grid">
        <div
          v-for="(source, key) in dataSources"
          :key="key"
          class="source-item"
          :class="{ enabled: source.enabled, configured: source.configured }"
        >
          <div class="source-icon">
            <el-icon><component :is="source.icon" /></el-icon>
          </div>
          <div class="source-info">
            <div class="source-name">{{ source.name }}</div>
            <div class="source-status">
              <el-tag :type="source.enabled ? 'success' : 'info'" size="small">
                {{ source.enabled ? '启用' : '禁用' }}
              </el-tag>
              <el-tag v-if="source.configured" type="success" size="small">
                已配置
              </el-tag>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  DataAnalysis, Refresh, TrendCharts, Document, Search, Connection,
  Newspaper, ChatLineRound, Star
} from '@element-plus/icons-vue'
import axios from 'axios'

const API_BASE = '/api/v1/external'

// 数据
const loading = ref(false)
const marketSentiment = ref({
  score: 5,
  news_count: 0,
  bullish_count: 0,
  bearish_count: 0
})
const latestNews = ref([])
const queryCoin = ref('')
const coinSentiment = ref(null)
const activeTab = ref('rss')
const dataSources = ref({
  rss: {
    name: 'RSS新闻',
    enabled: true,
    configured: true,
    icon: 'Newspaper'
  },
  twitter: {
    name: 'Twitter',
    enabled: false,
    configured: false,
    icon: 'ChatLineRound'
  },
  lunarcrush: {
    name: 'LunarCrush',
    enabled: false,
    configured: false,
    icon: 'Star'
  }
})

// 计算属性
const overallScore = computed(() => marketSentiment.value.score)
const sentimentClass = computed(() => {
  if (overallScore.value >= 7) return 'bullish'
  if (overallScore.value <= 4) return 'bearish'
  return 'neutral'
})
const sentimentText = computed(() => {
  if (overallScore.value >= 7) return '极度看涨'
  if (overallScore.value >= 6) return '温和看涨'
  if (overallScore.value <= 3) return '极度看跌'
  if (overallScore.value <= 4) return '温和看跌'
  return '中性'
})

// 方法
const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date

  if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}分钟前`
  } else if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}小时前`
  } else {
    return date.toLocaleDateString()
  }
}

const formatNumber = (num) => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}

const getSentimentClass = (score) => {
  if (score >= 7) return 'bullish'
  if (score <= 4) return 'bearish'
  return 'neutral'
}

const refreshData = async () => {
  loading.value = true
  try {
    await Promise.all([
      fetchMarketSentiment(),
      fetchLatestNews()
    ])
    ElMessage.success('数据刷新成功')
  } catch (error) {
    ElMessage.error('刷新失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const fetchMarketSentiment = async () => {
  try {
    const response = await axios.get(`${API_BASE}/market-sentiment`)
    if (response.data.success) {
      marketSentiment.value = response.data.data
    }
  } catch (error) {
    console.error('获取市场情绪失败:', error)
  }
}

const fetchLatestNews = async () => {
  try {
    const response = await axios.get(`${API_BASE}/news?limit=10`)
    if (response.data.success) {
      latestNews.value = response.data.data
    }
  } catch (error) {
    console.error('获取最新新闻失败:', error)
  }
}

const queryCoinSentiment = async () => {
  if (!queryCoin.value) {
    ElMessage.warning('请输入币种符号')
    return
  }

  loading.value = true
  try {
    const response = await axios.get(`${API_BASE}/sentiment/${queryCoin.value.toUpperCase()}`)
    if (response.data.success) {
      coinSentiment.value = response.data.data
      ElMessage.success('查询成功')
    } else {
      ElMessage.warning(response.data.message || '查询失败')
    }
  } catch (error) {
    ElMessage.error('查询失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const fetchDataSourcesStatus = async () => {
  try {
    const response = await axios.get(`${API_BASE}/sources/status`)
    if (response.data.success) {
      const sources = response.data.data
      dataSources.value.rss.enabled = sources.rss.enabled
      dataSources.value.twitter.enabled = sources.twitter.enabled
      dataSources.value.twitter.configured = sources.twitter.configured
      dataSources.value.lunarcrush.enabled = sources.lunarcrush.enabled
      dataSources.value.lunarcrush.configured = sources.lunarcrush.configured
    }
  } catch (error) {
    console.error('获取数据源状态失败:', error)
  }
}

// 生命周期
onMounted(() => {
  refreshData()
  fetchDataSourcesStatus()
})
</script>

<style scoped>
.external-data-card {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  padding: 24px;
  margin-bottom: 16px;
  transition: all 0.3s ease;
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.external-data-card:hover {
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  background: rgba(255, 255, 255, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.gradient-icon {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.header-title h3 {
  margin: 0 0 4px 0;
  font-size: 18px;
  color: #ffffff;
  font-weight: 600;
}

.subtitle {
  margin: 0;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.market-sentiment-section {
  margin-bottom: 24px;
  padding: 20px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.sentiment-display {
  display: flex;
  gap: 32px;
  align-items: center;
}

.score-circle {
  flex-shrink: 0;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.score-value {
  font-size: 32px;
  font-weight: 700;
  color: #ffffff;
}

.score-value.bullish {
  color: #4caf50;
}

.score-value.bearish {
  color: #f44336;
}

.score-value.neutral {
  color: rgba(255, 255, 255, 0.7);
}

.score-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  margin-top: 4px;
}

.sentiment-stats {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.stat-item {
  text-align: center;
  padding: 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.stat-item.bullish {
  border-left: 4px solid #4caf50;
}

.stat-item.bearish {
  border-left: 4px solid #f44336;
}

.stat-label {
  display: block;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 8px;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: #ffffff;
}

.news-section {
  margin-bottom: 24px;
}

.news-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.news-item {
  padding: 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  border-left: 4px solid #2196f3;
}

.news-source {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 4px;
}

.news-title {
  font-size: 14px;
  color: #ffffff;
  margin-bottom: 8px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.news-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.news-time {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

.coin-query-section {
  margin-bottom: 24px;
}

.query-input {
  margin-bottom: 16px;
}

.coin-sentiment-result {
  padding: 20px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
}

.coin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.coin-header h4 {
  margin: 0;
  font-size: 16px;
  color: #ffffff;
}

.overall-score {
  font-size: 28px;
  font-weight: 700;
  padding: 8px 16px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.overall-score.bullish {
  color: #4caf50;
}

.overall-score.bearish {
  color: #f44336;
}

.overall-score.neutral {
  color: rgba(255, 255, 255, 0.7);
}

.tab-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sentiment-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.sentiment-item .label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
}

.sentiment-item .value {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}

.no-data {
  text-align: center;
  padding: 32px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
}

.data-sources-status {
  margin-bottom: 0;
}

.sources-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.source-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  border: 2px solid transparent;
}

.source-item.enabled {
  border-color: #4caf50;
}

.source-item.configured {
  background: rgba(102, 126, 234, 0.2);
}

.source-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.source-name {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 4px;
}

.source-status {
  display: flex;
  gap: 4px;
}

@media (max-width: 768px) {
  .sentiment-display {
    flex-direction: column;
  }

  .sentiment-stats {
    grid-template-columns: 1fr;
    width: 100%;
  }

  .sources-grid {
    grid-template-columns: 1fr;
  }
}
</style>
