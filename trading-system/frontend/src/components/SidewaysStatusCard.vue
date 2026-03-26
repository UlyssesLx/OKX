<template>
  <div class="sideways-card card">
    <div class="card-header">
      <div class="header-left">
        <div class="card-icon gradient-icon blue">
          <el-icon :size="20"><DataBoard /></el-icon>
        </div>
        <div class="title-section">
          <div class="card-title">横盘状态监控</div>
          <div class="card-subtitle">检测市场横盘币种</div>
        </div>
      </div>
      <div class="header-actions">
        <el-button
          v-if="Object.keys(sidewaysStatus).length > 0"
          type="danger"
          size="small"
          @click="resetAll"
        >
          重置全部
        </el-button>
      </div>
    </div>

    <div class="card-content">
      <div v-if="Object.keys(sidewaysStatus).length === 0" class="empty-state">
        <div class="empty-icon">
          <el-icon :size="64"><Document /></el-icon>
        </div>
        <span class="empty-text">暂无横盘币种</span>
        <span class="empty-hint">系统会自动检测横盘状态</span>
      </div>

      <div v-else class="sideways-list">
        <div
          v-for="(status, coin) in sidewaysStatus"
          :key="coin"
          class="sideways-item"
        >
          <div class="coin-info">
            <div class="coin-icon gradient-icon yellow sm">
              <el-icon :size="16"><Coin /></el-icon>
            </div>
            <div class="coin-details">
              <span class="coin-name">{{ coin }}</span>
              <el-tag type="warning" size="small" effect="light">横盘中</el-tag>
            </div>
          </div>
          <div class="status-detail">
            <div class="detail-row">
              <span class="detail-label">周期数</span>
              <span class="detail-value">{{ status.periods }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">开始时间</span>
              <span class="detail-value">{{ formatTime(status.since) }}</span>
            </div>
          </div>
          <el-button
            type="primary"
            size="small"
            @click="resetCoin(coin)"
          >
            解除
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataBoard, Document, Coin } from '@element-plus/icons-vue'

const sidewaysStatus = ref<Record<string, any>>({})
let pollInterval: number | null = null

async function fetchStatus() {
  try {
    const response = await fetch('/api/v1/services/sideways/status')
    if (response.ok) {
      sidewaysStatus.value = await response.json()
    }
  } catch (error) {
    console.error('Failed to fetch sideways status:', error)
  }
}

function formatTime(isoString: string | null): string {
  if (!isoString) return '未知'
  try {
    const date = new Date(isoString)
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return isoString
  }
}

async function resetCoin(coin: string) {
  try {
    await ElMessageBox.confirm(
      `确定要解除 ${coin} 的横盘状态吗？`,
      '确认',
      { type: 'warning' }
    )
    
    const response = await fetch(`/api/v1/services/sideways/${coin}`, {
      method: 'DELETE'
    })
    
    if (response.ok) {
      ElMessage.success(`${coin} 横盘状态已解除`)
      await fetchStatus()
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

async function resetAll() {
  try {
    await ElMessageBox.confirm(
      '确定要解除所有币种的横盘状态吗？',
      '确认',
      { type: 'warning' }
    )
    
    const response = await fetch('/api/v1/services/sideways', {
      method: 'DELETE'
    })
    
    if (response.ok) {
      ElMessage.success('所有横盘状态已解除')
      await fetchStatus()
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

onMounted(() => {
  fetchStatus()
  pollInterval = window.setInterval(fetchStatus, 30000)
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>

<style lang="scss" scoped>
.sideways-card {
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

  .card-content {
    margin-top: 20px;
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

  .sideways-list {
    max-height: 400px;
    overflow-y: auto;

    .sideways-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 12px;
      margin-bottom: 12px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      transition: all $transition-normal;

      &:hover {
        background: rgba(255, 255, 255, 0.1);
        box-shadow: $dark-shadow;
        transform: translateY(-2px);
      }

      &:last-child {
        margin-bottom: 0;
      }

      .coin-info {
        display: flex;
        align-items: center;
        gap: 12px;
        flex: 1;

        .coin-details {
          display: flex;
          align-items: center;
          gap: 8px;

          .coin-name {
            font-weight: 600;
            font-size: 15px;
            color: #ffffff;
          }
        }
      }

      .status-detail {
        display: flex;
        flex-direction: column;
        gap: 6px;
        font-size: 13px;
        color: rgba(255, 255, 255, 0.8);
        min-width: 180px;

        .detail-row {
          display: flex;
          justify-content: space-between;

          .detail-label {
            color: rgba(255, 255, 255, 0.6);
          }

          .detail-value {
            font-weight: 500;
            color: #ffffff;
          }
        }
      }
    }
  }
}
</style>
