<template>
  <div class="emergency-card card">
    <div class="card-header">
      <div class="header-left">
        <div class="card-icon gradient-icon red">
          <el-icon :size="20"><Warning /></el-icon>
        </div>
        <div class="title-section">
          <div class="card-title">紧急停止控制</div>
          <div class="card-subtitle">紧急情况下停止所有交易</div>
        </div>
      </div>
      <div class="header-actions">
        <el-tag :type="isStopped ? 'danger' : 'success'" size="small" effect="dark">
          {{ isStopped ? '已停止' : '正常运行' }}
        </el-tag>
      </div>
    </div>

    <div class="card-content">
      <div v-if="isStopped" class="stopped-status">
        <div class="status-icon-wrapper gradient-icon red lg">
          <el-icon :size="40"><CircleClose /></el-icon>
        </div>
        <div class="status-title">系统已紧急停止</div>
        <div v-if="stopInfo" class="stop-info">
          <div class="info-row">
            <span class="label">停止原因</span>
            <span class="value">{{ stopInfo.reason }}</span>
          </div>
          <div class="info-row">
            <span class="label">停止时间</span>
            <span class="value">{{ stopInfo.stopped_at || '未知' }}</span>
          </div>
        </div>
        <el-button type="success" size="large" @click="clearEmergencyStop" :loading="loading">
          <el-icon style="margin-right: 6px"><Check /></el-icon>
          解除紧急停止
        </el-button>
      </div>

      <div v-else class="normal-status">
        <div class="status-icon-wrapper gradient-icon green lg">
          <el-icon :size="40"><CircleCheck /></el-icon>
        </div>
        <div class="status-title">系统正常运行中</div>
        <div class="status-hint">点击下方按钮将立即停止所有交易活动</div>
        <el-input
          v-model="stopReason"
          placeholder="请输入停止原因"
          style="margin: 20px 0; max-width: 400px;"
          size="large"
        />
        <el-button type="danger" size="large" @click="triggerEmergencyStop" :loading="loading">
          <el-icon style="margin-right: 6px"><Warning /></el-icon>
          触发紧急停止
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Warning, CircleClose, CircleCheck, Check } from '@element-plus/icons-vue'

interface StopInfo {
  reason: string | null
  stopped_at: string | null
}

const isStopped = ref(false)
const stopInfo = ref<StopInfo | null>(null)
const stopReason = ref('')
const loading = ref(false)
let pollInterval: number | null = null

async function fetchStatus() {
  try {
    const response = await fetch('/api/v1/services/emergency-stop')
    if (response.ok) {
      const data = await response.json()
      isStopped.value = data.is_stopped
      stopInfo.value = {
        reason: data.reason,
        stopped_at: data.stopped_at
      }
    }
  } catch (error) {
    console.error('Failed to fetch emergency stop status:', error)
  }
}

async function triggerEmergencyStop() {
  if (!stopReason.value.trim()) {
    ElMessage.warning('请输入停止原因')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      '确定要触发紧急停止吗？这将立即停止所有交易活动！',
      '紧急停止确认',
      {
        confirmButtonText: '确定停止',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    loading.value = true
    const response = await fetch('/api/v1/services/emergency-stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: stopReason.value })
    })
    
    if (response.ok) {
      ElMessage.success('紧急停止已触发')
      await fetchStatus()
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  } finally {
    loading.value = false
  }
}

async function clearEmergencyStop() {
  try {
    await ElMessageBox.confirm(
      '确定要解除紧急停止吗？系统将恢复交易活动。',
      '解除确认',
      {
        confirmButtonText: '确定解除',
        cancelButtonText: '取消',
        type: 'info'
      }
    )
    
    loading.value = true
    const response = await fetch('/api/v1/services/emergency-stop', {
      method: 'DELETE'
    })
    
    if (response.ok) {
      ElMessage.success('紧急停止已解除')
      stopReason.value = ''
      await fetchStatus()
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStatus()
  pollInterval = window.setInterval(fetchStatus, 5000)
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>

<style lang="scss" scoped>
.emergency-card {
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
    margin-top: 24px;
    text-align: center;
  }

  .stopped-status {
    .status-icon-wrapper {
      margin: 0 auto 24px;
      width: 100px;
      height: 100px;
      border-radius: 50%;
    }

    .status-title {
      font-size: 24px;
      font-weight: 700;
      color: $danger-color;
      margin-bottom: 24px;
    }

    .stop-info {
      background: rgba(244, 67, 54, 0.08);
      border: 1px solid rgba(244, 67, 54, 0.2);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 24px;
      max-width: 400px;
      margin-left: auto;
      margin-right: auto;
    }
  }

  .normal-status {
    .status-icon-wrapper {
      margin: 0 auto 24px;
      width: 100px;
      height: 100px;
      border-radius: 50%;
    }

    .status-title {
      font-size: 24px;
      font-weight: 700;
      color: $success-color;
      margin-bottom: 8px;
    }

    .status-hint {
      font-size: 14px;
      color: rgba(255, 255, 255, 0.7);
      margin-bottom: 16px;
    }
  }

  .info-row {
    display: flex;
    justify-content: space-between;
    padding: 12px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);

    &:last-child {
      border-bottom: none;
    }

    .label {
      color: rgba(255, 255, 255, 0.7);
      font-weight: 500;
    }

    .value {
      font-weight: 600;
      color: #ffffff;
    }
  }
}
</style>
