<template>
  <div class="sentiment-card card">
    <div class="card-header">
      <div class="header-left">
        <div class="card-icon gradient-icon pink">
          <el-icon :size="20"><TrendCharts /></el-icon>
        </div>
        <div class="title-section">
          <div class="card-title">市场情绪</div>
          <div class="card-subtitle">分析币种市场情绪</div>
        </div>
      </div>
      <div class="header-actions">
        <el-input
          v-model="searchCoin"
          placeholder="输入币种"
          size="default"
          style="width: 140px"
          @keyup.enter="fetchSentiment"
        >
          <template #append>
            <el-button @click="fetchSentiment" :loading="loading">
              <el-icon><Search /></el-icon>
            </el-button>
          </template>
        </el-input>
      </div>
    </div>

    <div v-if="sentiment" class="sentiment-content">
      <div class="score-display">
        <div class="score-circle-wrapper" :class="scoreClass">
          <div class="score-circle">
            <span class="score-value">{{ sentiment.combined_score }}</span>
            <span class="score-label">综合评分</span>
          </div>
        </div>
      </div>

      <div class="sentiment-details" v-if="sentiment.coingecko">
        <div class="detail-item">
          <span class="label">当前价格</span>
          <span class="value">${{ formatPrice(sentiment.coingecko.price) }}</span>
        </div>
        <div class="detail-item">
          <span class="label">24h涨跌</span>
          <span class="value" :class="sentiment.coingecko.price_change_24h >= 0 ? 'positive' : 'negative'">
            {{ sentiment.coingecko.price_change_24h >= 0 ? '+' : '' }}{{ sentiment.coingecko.price_change_24h?.toFixed(2) }}%
          </span>
        </div>
        <div class="detail-item">
          <span class="label">7d涨跌</span>
          <span class="value" :class="sentiment.coingecko.price_change_7d >= 0 ? 'positive' : 'negative'">
            {{ sentiment.coingecko.price_change_7d >= 0 ? '+' : '' }}{{ sentiment.coingecko.price_change_7d?.toFixed(2) }}%
          </span>
        </div>
        <div class="detail-item">
          <span class="label">市值排名</span>
          <span class="value">#{{ sentiment.coingecko.market_cap_rank }}</span>
        </div>
        <div class="detail-item">
          <span class="label">看涨情绪</span>
          <span class="value positive">{{ sentiment.coingecko.sentiment_up }}%</span>
        </div>
        <div class="detail-item">
          <span class="label">看跌情绪</span>
          <span class="value negative">{{ sentiment.coingecko.sentiment_down }}%</span>
        </div>
      </div>

      <div class="news-section" v-if="sentiment.news && sentiment.news.news_count > 0">
        <div class="news-title">
          <el-icon :size="18"><Document /></el-icon>
          新闻情绪 ({{ sentiment.news.score }}/10)
        </div>
        <div class="news-stats">
          <el-tag type="success" size="small" effect="light">看涨 {{ sentiment.news.bullish_count }}</el-tag>
          <el-tag type="danger" size="small" effect="light">看跌 {{ sentiment.news.bearish_count }}</el-tag>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <div class="empty-icon">
        <el-icon :size="64"><TrendCharts /></el-icon>
      </div>
      <span class="empty-text">输入币种查询情绪数据</span>
      <span class="empty-hint">支持查询市场情绪和新闻分析</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { TrendCharts, Search, Document } from '@element-plus/icons-vue'

interface SentimentData {
  coin: string
  coingecko: any
  news: any
  combined_score: number
}

const searchCoin = ref('BTC')
const sentiment = ref<SentimentData | null>(null)
const loading = ref(false)

const scoreClass = computed(() => {
  if (!sentiment.value) return ''
  const score = sentiment.value.combined_score
  if (score >= 7) return 'high'
  if (score >= 5) return 'medium'
  return 'low'
})

function formatPrice(price: number): string {
  if (price >= 1000) return price.toFixed(0)
  if (price >= 1) return price.toFixed(2)
  return price.toFixed(6)
}

async function fetchSentiment() {
  if (!searchCoin.value) return
  
  loading.value = true
  try {
    const response = await fetch(`/api/v1/services/sentiment/${searchCoin.value.toUpperCase()}`)
    if (response.ok) {
      sentiment.value = await response.json()
    } else {
      ElMessage.warning('获取情绪数据失败')
    }
  } catch (error) {
    console.error('Failed to fetch sentiment:', error)
    ElMessage.error('网络错误')
  } finally {
    loading.value = false
  }
}

fetchSentiment()
</script>

<style lang="scss" scoped>
.sentiment-card {
  .card-header {
    padding-bottom: 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);

    .header-left {
      display: flex;
      align-items: center;
      gap: 16px;

      .title-section {
        .card-title {
          font-size: 18px;
          font-weight: 600;
          margin-bottom: 4px;
        }

        .card-subtitle {
          font-size: 13px;
          color: rgba(255, 255, 255, 0.6);
        }
      }
    }
  }

  .sentiment-content {
    .score-display {
      display: flex;
      justify-content: center;
      margin-bottom: 32px;

      .score-circle-wrapper {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 8px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.05);

        &.high {
          background: rgba($success-color, 0.1);
        }

        &.medium {
          background: rgba($warning-color, 0.1);
        }

        &.low {
          background: rgba($danger-color, 0.1);
        }

        .score-circle {
          width: 120px;
          height: 120px;
          border-radius: 50%;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          background: rgba(255, 255, 255, 0.1);
          border: 3px solid;
          box-shadow: $dark-shadow;

          .score-value {
            font-size: 36px;
            font-weight: 700;
            line-height: 1.2;
            color: #ffffff;
          }

          .score-label {
            font-size: 13px;
            color: rgba(255, 255, 255, 0.7);
            margin-top: 4px;
          }
        }
      }
    }

    .sentiment-details {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;

      .detail-item {
        display: flex;
        justify-content: space-between;
        padding: 12px 16px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all $transition-normal;

        &:hover {
          background: rgba(255, 255, 255, 0.1);
          box-shadow: $dark-shadow;
        }

        .label {
          color: rgba(255, 255, 255, 0.7);
          font-size: 13px;
          font-weight: 500;
        }

        .value {
          font-weight: 600;
          color: #ffffff;

          &.positive {
            color: $success-color;
          }

          &.negative {
            color: $danger-color;
          }
        }
      }
    }

    .news-section {
      margin-top: 24px;
      padding-top: 24px;
      border-top: 1px solid rgba(255, 255, 255, 0.1);

      .news-title {
        font-size: 15px;
        font-weight: 600;
        margin-bottom: 12px;
        color: #ffffff;
        display: flex;
        align-items: center;
        gap: 6px;
      }

      .news-stats {
        display: flex;
        gap: 12px;
      }
    }
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 30px;

    .empty-icon {
      color: rgba(255, 255, 255, 0.5);
      margin-bottom: 16px;
      opacity: 0.5;
    }

    .empty-text {
      font-size: 16px;
      font-weight: 500;
      color: rgba(255, 255, 255, 0.8);
      margin-bottom: 8px;
    }

    .empty-hint {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.5);
    }
  }
}
</style>
