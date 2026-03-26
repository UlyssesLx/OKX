<template>
  <div class="market-environment-card card">
    <div class="card-header">
      <div class="header-left">
        <div class="icon-wrapper gradient-icon blue md">
          <el-icon :size="24"><DataBoard /></el-icon>
        </div>
        <div class="title-info">
          <div class="card-title">大盘环境</div>
          <div class="card-subtitle">市场评分与建议</div>
        </div>
      </div>
      <div class="status-badge" :class="environment.can_trade ? 'success' : 'danger'">
        <el-icon><Select v-if="environment.can_trade" /><Warning v-else /></el-icon>
        {{ environment.can_trade ? '可交易' : '建议空仓' }}
      </div>
    </div>

    <div class="environment-content">
      <div class="environment-score">
        <div class="score-circle" :class="scoreClass">
          <div class="score-value">{{ environment.score }}</div>
          <div class="score-label">/ 10</div>
        </div>
      </div>

      <div class="environment-details">
        <div class="detail-row">
          <div class="label-group">
            <el-icon><Coin /></el-icon>
            <span class="label">BTC 评分</span>
          </div>
          <div class="value-group">
            <span class="score">{{ environment.btc_score }}/10</span>
            <span class="trend-badge" :class="environment.btc_change_24h >= 0 ? 'positive' : 'negative'">
              {{ environment.btc_change_24h >= 0 ? '+' : '' }}{{ environment.btc_change_24h.toFixed(2) }}%
            </span>
          </div>
        </div>

        <div class="detail-row">
          <div class="label-group">
            <el-icon><Wallet /></el-icon>
            <span class="label">ETH 评分</span>
          </div>
          <div class="value-group">
            <span class="score">{{ environment.eth_score }}/10</span>
            <span class="trend-badge" :class="environment.eth_change_24h >= 0 ? 'positive' : 'negative'">
              {{ environment.eth_change_24h >= 0 ? '+' : '' }}{{ environment.eth_change_24h.toFixed(2) }}%
            </span>
          </div>
        </div>

        <div class="detail-row">
          <div class="label-group">
            <el-icon><DataAnalysis /></el-icon>
            <span class="label">资金费率</span>
          </div>
          <div class="value-group">
            <span class="score">{{ environment.funding_score }}/10</span>
          </div>
        </div>
      </div>

      <div class="environment-reason">
        {{ environment.reason }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { DataBoard, Select, Warning, Coin, Wallet, DataAnalysis } from '@element-plus/icons-vue'
import type { MarketEnvironment } from '@/types'

interface Props {
  environment: MarketEnvironment
}

const props = defineProps<Props>()

const scoreClass = computed(() => {
  const score = props.environment.score
  if (score >= 7) return 'excellent'
  if (score >= 5) return 'good'
  return 'poor'
})
</script>

<style lang="scss" scoped>
.market-environment-card {
  height: 100%;
  display: flex;
  flex-direction: column;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 0;
    border: none;

    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;

      .icon-wrapper {
        width: 48px;
        height: 48px;
      }

      .title-info {
        .card-title {
          font-size: 16px;
          font-weight: 600;
          color: #ffffff;
          margin: 0;
          padding: 0;
          border: none;
        }

        .card-subtitle {
          font-size: 12px;
          color: rgba(255, 255, 255, 0.6);
          margin-top: 4px;
        }
      }
    }

    .status-badge {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 8px 16px;
      border-radius: 20px;
      font-size: 13px;
      font-weight: 600;

      &.success {
        background: rgba($success-color, 0.1);
        color: $success-color;
      }

      &.danger {
        background: rgba($danger-color, 0.1);
        color: $danger-color;
      }
    }
  }

  .environment-content {
    flex: 1;
    display: flex;
    flex-direction: column;

    .environment-score {
      display: flex;
      justify-content: center;
      margin-bottom: 20px;

      .score-circle {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: rgba(255, 255, 255, 0.05);
        border: 4px solid;
        box-shadow: $dark-shadow;
        transition: all $transition-normal;

        &.excellent {
          border-color: $success-color;
          background: rgba($success-color, 0.05);
        }

        &.good {
          border-color: $warning-color;
          background: rgba($warning-color, 0.05);
        }

        &.poor {
          border-color: $danger-color;
          background: rgba($danger-color, 0.05);
        }

        .score-value {
          font-size: 36px;
          font-weight: 700;
          color: #ffffff;
          line-height: 1;
        }

        .score-label {
          font-size: 12px;
          color: rgba(255, 255, 255, 0.6);
          margin-top: 4px;
        }
      }
    }

    .environment-details {
      display: flex;
      flex-direction: column;
      gap: 12px;

      .detail-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 16px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: $border-radius-sm;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all $transition-normal;

        &:hover {
          background: rgba(102, 126, 234, 0.1);
          border-color: rgba(102, 126, 234, 0.3);
        }

        .label-group {
          display: flex;
          align-items: center;
          gap: 8px;
          color: rgba(255, 255, 255, 0.7);
          font-size: 13px;

          .el-icon {
            color: rgba(255, 255, 255, 0.5);
          }
        }

        .value-group {
          display: flex;
          align-items: center;
          gap: 12px;

          .score {
            color: #ffffff;
            font-weight: 600;
            font-size: 14px;
          }

          .trend-badge {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;

            &.positive {
              background: rgba($success-color, 0.1);
              color: $success-color;
            }

            &.negative {
              background: rgba($danger-color, 0.1);
              color: $danger-color;
            }
          }
        }
      }
    }

    .environment-reason {
      margin-top: 16px;
      padding: 12px;
      background: rgba($info-color, 0.05);
      border-left: 3px solid $info-color;
      border-radius: $border-radius-sm;
      font-size: 13px;
      color: rgba(255, 255, 255, 0.7);
      line-height: 1.6;
    }
  }
}
</style>
