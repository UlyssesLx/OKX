<template>
  <div class="blacklist-card card">
    <div class="card-header">
      <div class="header-left">
        <div class="card-icon gradient-icon pink">
          <el-icon :size="20"><CircleClose /></el-icon>
        </div>
        <div class="title-section">
          <div class="card-title">黑名单管理</div>
          <div class="card-subtitle">管理禁用币种</div>
        </div>
      </div>
      <div class="header-actions">
        <el-button size="default" @click="showAddDialog = true">
          <el-icon style="margin-right: 6px"><Plus /></el-icon>
          添加
        </el-button>
      </div>
    </div>

    <div class="blacklist-sections">
      <div class="section" v-if="blacklist.stopped_out.length > 0">
        <div class="section-title">
          止损黑名单
          <el-tooltip content="72小时后自动过期" placement="top">
            <el-icon class="info-icon"><InfoFilled /></el-icon>
          </el-tooltip>
        </div>
        <div class="coin-list">
          <el-tag
            v-for="coin in blacklist.stopped_out"
            :key="coin"
            closable
            type="danger"
            @close="removeCoin(coin)"
          >
            {{ coin }}
          </el-tag>
        </div>
      </div>

      <div class="section" v-if="blacklist.manual_ban.length > 0">
        <div class="section-title">
          手动禁用
          <el-tooltip content="7天后自动过期" placement="top">
            <el-icon class="info-icon"><InfoFilled /></el-icon>
          </el-tooltip>
        </div>
        <div class="coin-list">
          <el-tag
            v-for="coin in blacklist.manual_ban"
            :key="coin"
            closable
            type="warning"
            @close="removeCoin(coin)"
          >
            {{ coin }}
          </el-tag>
        </div>
      </div>

      <div class="section">
        <div class="section-title">稳定币 (不交易)</div>
        <div class="coin-list">
          <el-tag
            v-for="coin in blacklist.stablecoins"
            :key="coin"
            type="info"
          >
            {{ coin }}
          </el-tag>
        </div>
      </div>
    </div>

    <div class="stats-footer">
      <span>共 {{ blacklist.total_count }} 个币种在黑名单中</span>
      <span class="auto-expire-hint" v-if="hasAutoExpire">
        <el-icon><Clock /></el-icon>
        自动过期: 止损72h, 手动7天
      </span>
    </div>

    <el-dialog v-model="showAddDialog" title="添加到黑名单" width="350px">
      <el-form>
        <el-form-item label="币种">
          <el-input v-model="newCoin" placeholder="如: BTC" uppercase />
        </el-form-item>
        <el-form-item label="原因">
          <el-select v-model="newReason" placeholder="选择原因" style="width: 100%">
            <el-option label="手动禁用" value="手动禁用" />
            <el-option label="止损" value="止损" />
            <el-option label="流动性不足" value="流动性不足" />
            <el-option label="异常波动" value="异常波动" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addCoin">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled, Clock, CircleClose, Plus } from '@element-plus/icons-vue'

interface BlacklistData {
  stopped_out: string[]
  manual_ban: string[]
  stablecoins: string[]
  total_count: number
}

const blacklist = ref<BlacklistData>({
  stopped_out: [],
  manual_ban: [],
  stablecoins: [],
  total_count: 0
})

const showAddDialog = ref(false)
const newCoin = ref('')
const newReason = ref('手动禁用')

const hasAutoExpire = computed(() => {
  return blacklist.value.stopped_out.length > 0 || blacklist.value.manual_ban.length > 0
})

async function fetchBlacklist() {
  try {
    const response = await fetch('/api/v1/services/blacklist')
    if (response.ok) {
      blacklist.value = await response.json()
    }
  } catch (error) {
    console.error('Failed to fetch blacklist:', error)
  }
}

async function addCoin() {
  if (!newCoin.value) {
    ElMessage.warning('请输入币种')
    return
  }

  try {
    const response = await fetch(`/api/v1/services/blacklist/${newCoin.value.toUpperCase()}?reason=${encodeURIComponent(newReason.value)}`, {
      method: 'POST'
    })
    if (response.ok) {
      ElMessage.success(`${newCoin.value.toUpperCase()} 已添加到黑名单`)
      showAddDialog.value = false
      newCoin.value = ''
      fetchBlacklist()
    }
  } catch (error) {
    ElMessage.error('添加失败')
  }
}

async function removeCoin(coin: string) {
  try {
    const response = await fetch(`/api/v1/services/blacklist/${coin}`, {
      method: 'DELETE'
    })
    if (response.ok) {
      ElMessage.success(`${coin} 已从黑名单移除`)
      fetchBlacklist()
    }
  } catch (error) {
    ElMessage.error('移除失败')
  }
}

onMounted(fetchBlacklist)
</script>

<style lang="scss" scoped>
.blacklist-card {
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

  .blacklist-sections {
    .section {
      margin-bottom: 24px;

      .section-title {
        font-size: 14px;
        color: rgba(255, 255, 255, 0.8);
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 6px;
        font-weight: 500;

        .info-icon {
          font-size: 16px;
          color: rgba(255, 255, 255, 0.5);
          cursor: help;
        }
      }

      .coin-list {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;

        :deep(.el-tag) {
          padding: 8px 14px;
          font-weight: 500;
        }
      }
    }
  }

  .stats-footer {
    padding-top: 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    font-size: 14px;
    color: rgba(255, 255, 255, 0.7);
    display: flex;
    justify-content: space-between;
    align-items: center;

    .auto-expire-hint {
      display: flex;
      align-items: center;
      gap: 6px;
      color: $primary-color;
      font-size: 13px;
      font-weight: 500;
      background: rgba($primary-color, 0.08);
      padding: 6px 12px;
      border-radius: 8px;
    }
  }
}
</style>
