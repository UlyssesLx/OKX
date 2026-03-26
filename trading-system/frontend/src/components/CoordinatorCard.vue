<template>
  <div class="coordinator-card card">
    <div class="card-header">
      <span class="title">🔄 自动交易协调器</span>
      <el-tag :type="status.is_running ? 'success' : 'info'" size="small">
        {{ status.is_running ? '运行中' : '已停止' }}
      </el-tag>
    </div>

    <div class="card-content vertical-layout">
      <!-- 上部：控制面板 -->
      <div class="top-panel">
        <div class="top-row">
          <div class="status-info">
            <div class="info-row">
              <span class="label">状态:</span>
              <span class="value">{{ status.is_running ? '🟢 运行中' : '⚪ 已停止' }}</span>
            </div>
            <div class="info-row">
              <span class="label">总周期数:</span>
              <span class="value">{{ status.total_cycles }}</span>
            </div>
            <div class="info-row">
              <span class="label">上次运行:</span>
              <span class="value">{{ status.last_cycle_time || '未运行' }}</span>
            </div>
            <div class="info-row">
              <span class="label">交易模式:</span>
              <span class="value">{{ status.trading_enabled ? '实盘' : '模拟' }}</span>
            </div>
          </div>

          <div class="control-section">
            <div class="control-buttons">
              <el-button
                class="start-btn"
                type="success"
                :disabled="status.is_running"
                @click="startCoordinator"
                :loading="loading"
              >
                ▶ 启动
              </el-button>
              <el-button
                class="stop-btn"
                type="danger"
                :disabled="!status.is_running"
                @click="stopCoordinator"
                :loading="loading"
              >
                ⏹ 停止
              </el-button>
              <el-button
                type="primary"
                @click="runSingleCycle"
                :loading="loading"
              >
                🔄 执行一次
              </el-button>
            </div>

            <div class="config-section">
              <div class="config-row">
                <span class="label">扫描间隔:</span>
                <span class="value">由时区感知统一管理</span>
                <el-tooltip content="扫描间隔在「时区感知」页面配置，根据不同时段自动调整">
                  <el-icon><QuestionFilled /></el-icon>
                </el-tooltip>
              </div>
              <div class="config-row">
                <el-checkbox v-model="dryRun">模拟模式</el-checkbox>
              </div>
            </div>
          </div>
        </div>

        <div v-if="cycleResult" class="cycle-result">
          <div class="result-header">📊 执行结果 {{ cycleResult.timestamp ? new Date(cycleResult.timestamp).toLocaleString('zh-CN') : '#' + (cycleResult.cycle || 1) }}</div>
          <div class="result-status" :class="cycleResult.status">
            <span v-if="cycleResult.status === 'completed'">✅ 完成</span>
            <span v-else-if="cycleResult.status === 'stopped'">⏸ 已停止</span>
            <span v-else>❌ 失败</span>
          </div>

          <div v-if="cycleResult.steps" class="result-steps">
            <div v-if="cycleResult.steps.data_reminder" class="step-item">
              <div class="step-title">📊 数据</div>
              <div v-if="cycleResult.steps.data_reminder.needs_refresh" class="step-warning">
                ⚠️ 需刷新
              </div>
              <div v-else class="step-ok">✓ 正常</div>
            </div>

            <div v-if="cycleResult.steps.trading" class="step-item">
              <div class="step-title">📈 扫描</div>
              <div class="step-detail">
                机会: <strong>{{ cycleResult.steps.trading.opportunities?.length || 0 }}</strong>
                信号: <strong>{{ cycleResult.steps.trading.signals?.length || 0 }}</strong>
              </div>
            </div>

            <div v-if="cycleResult.steps.evolution" class="step-item">
              <div class="step-title">🧬 进化</div>
              <div class="step-detail">
                v{{ cycleResult.steps.evolution.version || 'N/A' }}
              </div>
            </div>

            <div v-if="cycleResult.steps.signals" class="step-item">
              <div class="step-title">📢 信号</div>
              <div class="step-detail">{{ cycleResult.steps.signals.length }}个</div>
            </div>
          </div>

          <div v-if="cycleResult.error" class="result-error">
            错误: {{ cycleResult.error }}
          </div>
        </div>

        <div v-if="status.errors.length > 0" class="errors-section">
          <div class="errors-header">
            <span>最近错误:</span>
            <el-button type="danger" link size="small" @click="clearErrors">
              <el-icon><Close /></el-icon> 清除
            </el-button>
          </div>
          <div v-for="(error, index) in status.errors" :key="index" class="error-item">
            {{ error }}
          </div>
        </div>
      </div>

      <!-- 下部：日志面板 -->
      <div class="bottom-panel">
        <div class="activity-log">
          <div class="log-header">
            <span class="log-title">📝 活动日志</span>
            <div class="log-filters">
              <el-select v-model="selectedCycle" size="small" clearable placeholder="选择周期" style="width: 220px">
                <el-option :label="`最新 (${cycleLogs[cycleLogs.length-1]?.startTime || '无'})`" :value="0" />
                <el-option
                  v-for="c in recentCycles"
                  :key="c.cycle"
                  :label="c.startTime"
                  :value="c.cycle"
                />
              </el-select>
              <el-date-picker
                v-model="timeRange"
                type="daterange"
                size="small"
                range-separator="-"
                start-placeholder="开始"
                end-placeholder="结束"
                format="MM-DD"
                value-format="YYYY-MM-DD"
                :clearable="true"
                :editable="false"
                style="width: 200px"
              />
              <el-input
                v-model="searchKeyword"
                placeholder="搜索日志..."
                size="small"
                clearable
                class="search-input"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
              <el-select v-model="filterType" size="small" clearable placeholder="类型" style="width: 80px">
                <el-option label="全部" value="" />
                <el-option label="信息" value="info" />
                <el-option label="成功" value="success" />
                <el-option label="警告" value="warning" />
                <el-option label="错误" value="error" />
              </el-select>
            </div>
            <div class="log-actions">
              <el-button
                :type="autoScroll ? 'primary' : 'default'"
                size="small"
                @click="toggleAutoScroll"
                :title="autoScroll ? '自动滚动中' : '点击开启自动滚动'"
              >
                <el-icon v-if="autoScroll"><Position /></el-icon>
                <el-icon v-else><Bottom /></el-icon>
              </el-button>
              <el-button type="default" size="small" @click="scrollToTop" title="滚动到顶部">
                <el-icon><Top /></el-icon>
              </el-button>
              <el-button type="default" size="small" @click="scrollToBottom" title="滚动到底部">
                <el-icon><Bottom /></el-icon>
              </el-button>
              <el-button type="primary" size="small" @click="exportLogs" title="导出日志">
                <el-icon><Download /></el-icon>
              </el-button>
              <el-button type="danger" size="small" @click="clearLogs" title="清空日志">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          <div class="log-stats">
            <span class="stat-item">
              <el-tag type="info" size="small">共 {{ filteredLogs.length }} 条</el-tag>
            </span>
            <span class="stat-item">
              <el-tag type="success" size="small">✓ {{ getTypeCount('success') }}</el-tag>
            </span>
            <span class="stat-item">
              <el-tag type="warning" size="small">⚠ {{ getTypeCount('warning') }}</el-tag>
            </span>
            <span class="stat-item">
              <el-tag type="danger" size="small">✕ {{ getTypeCount('error') }}</el-tag>
            </span>
          </div>
          <div class="log-entries" ref="logContainer" @scroll="handleScroll">
            <template v-if="groupedLogs.length === 0">
              <div class="empty-logs">
                <el-empty description="暂无日志数据" :image-size="80" />
              </div>
            </template>
            <template v-else>
              <div
                v-for="(group, gIndex) in groupedLogs"
                :key="gIndex"
                class="log-group"
              >
                <!-- 日期分隔条 -->
                <div class="date-divider">
                  <span class="date-label">{{ group.date }}</span>
                </div>

                <!-- 周期列表 -->
                <div
                  v-for="(cycleGroup, cIndex) in group.cycles"
                  :key="cIndex"
                  class="cycle-block"
                  @click="showCycleDetail(cycleGroup)"
                >
                  <div class="cycle-header">
                    <div class="cycle-info">
                      <el-icon class="cycle-icon"><Clock /></el-icon>
                      <span class="cycle-title">{{ cycleGroup.startTime || '未分类' }}</span>
                      <el-tag size="small" :type="getCycleTagType(cycleGroup)">
                        {{ cycleGroup.logs.length }}条
                      </el-tag>
                    </div>
                    <div class="cycle-stats">
                      <el-tag v-if="getTypeCountInCycle(cycleGroup, 'success') > 0" type="success" size="small">
                        ✓ {{ getTypeCountInCycle(cycleGroup, 'success') }}
                      </el-tag>
                      <el-tag v-if="getTypeCountInCycle(cycleGroup, 'warning') > 0" type="warning" size="small">
                        ⚠ {{ getTypeCountInCycle(cycleGroup, 'warning') }}
                      </el-tag>
                      <el-tag v-if="getTypeCountInCycle(cycleGroup, 'error') > 0" type="danger" size="small">
                        ✕ {{ getTypeCountInCycle(cycleGroup, 'error') }}
                      </el-tag>
                    </div>
                  </div>

                  <!-- 简略日志预览 -->
                  <div class="cycle-preview">
                    <div
                      v-for="(log, lIndex) in cycleGroup.logs.slice(0, 3)"
                      :key="lIndex"
                      class="preview-log"
                    >
                      <span class="preview-icon">{{ getLogIcon(log.type) }}</span>
                      <span class="preview-time">{{ formatLogTime(log.time) }}</span>
                      <span class="preview-message">{{ getLogSummary(log.message) }}</span>
                    </div>
                    <div v-if="cycleGroup.logs.length > 3" class="preview-more">
                      还有 {{ cycleGroup.logs.length - 3 }} 条日志...
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </div>

          <!-- 浮动的回到顶部按钮 -->
          <transition name="fade">
            <el-button
              v-show="showScrollToTop"
              class="scroll-to-top-btn"
              type="primary"
              size="small"
              circle
              @click="scrollToTop"
              title="回到顶部"
            >
              <el-icon><Top /></el-icon>
            </el-button>
          </transition>
        </div>
      </div>
    </div>

    <!-- 周期详情对话框 -->
    <el-dialog
      v-model="cycleDetailVisible"
      title="周期详情"
      width="700px"
      class="cycle-detail-dialog"
    >
      <template #header>
        <div class="dialog-header">
          <span class="dialog-title">周期详情</span>
          <el-button
            v-if="selectedCycleDetail"
            type="primary"
            size="small"
            @click="exportCycleLogs(selectedCycleDetail)"
            :icon="Download"
          >
            导出日志
          </el-button>
        </div>
      </template>
      <div v-if="selectedCycleDetail" class="cycle-detail-content">
        <div class="detail-header">
          <el-icon class="detail-icon"><Clock /></el-icon>
          <div class="detail-info">
            <h3>{{ selectedCycleDetail.startTime || '未分类' }}</h3>
            <p class="start-time">开始时间: {{ selectedCycleDetail.startTime }}</p>
          </div>
          <div class="detail-stats">
            <el-tag size="small" :type="getCycleTagType(selectedCycleDetail)">
              {{ selectedCycleDetail.logs.length }} 条日志
            </el-tag>
            <el-tag v-if="getTypeCountInCycle(selectedCycleDetail, 'success') > 0" type="success" size="small">
              ✓ {{ getTypeCountInCycle(selectedCycleDetail, 'success') }}
            </el-tag>
            <el-tag v-if="getTypeCountInCycle(selectedCycleDetail, 'warning') > 0" type="warning" size="small">
              ⚠ {{ getTypeCountInCycle(selectedCycleDetail, 'warning') }}
            </el-tag>
            <el-tag v-if="getTypeCountInCycle(selectedCycleDetail, 'error') > 0" type="danger" size="small">
              ✕ {{ getTypeCountInCycle(selectedCycleDetail, 'error') }}
            </el-tag>
          </div>
        </div>

        <el-divider />

        <div class="detail-logs">
          <div
            v-for="(log, index) in selectedCycleDetail.logs"
            :key="index"
            class="detail-log-entry"
            :class="log.type"
          >
            <span class="log-icon">{{ getLogIcon(log.type) }}</span>
            <span class="log-time">{{ log.time }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Position, Bottom, Top, Download, Delete, Clock, Close } from '@element-plus/icons-vue'

interface CoordinatorStatus {
  is_running: boolean
  last_cycle_time: string | null
  total_cycles: number
  errors: string[]
  trading_enabled: boolean
}

interface ActivityLog {
  time: string
  message: string
  type: 'info' | 'success' | 'warning' | 'error'
  cycle?: number
}

interface CycleLog {
  cycle: number
  startTime: string
  logs: ActivityLog[]
}

interface CycleGroup {
  cycle: number | null
  startTime: string
  logs: ActivityLog[]
}

const status = ref<CoordinatorStatus>({
  is_running: false,
  last_cycle_time: null,
  total_cycles: 0,
  errors: [],
  trading_enabled: false
})
const loading = ref(false)
const intervalMinutes = ref(5)
const dryRun = ref(true)
const cycleResult = ref<any>(null)
const activityLogs = ref<ActivityLog[]>([])
const cycleLogs = ref<CycleLog[]>([])
const currentCycle = ref<number>(0)
const selectedCycle = ref<number>(0)
const logContainer = ref<HTMLElement | null>(null)
let pollInterval: number | null = null
const autoScroll = ref(true)
const searchKeyword = ref('')
const errorsClearedAt = ref<number>(0)
const filterType = ref('')
const timeRange = ref<[string, string] | null>(null)
const showScrollToTop = ref(false)
const cycleDetailVisible = ref(false)
const selectedCycleDetail = ref<CycleGroup | null>(null)

const recentCycles = computed(() => {
  return cycleLogs.value.slice(-5).reverse()
})

const lastCycle = computed(() => {
  if (cycleLogs.value.length > 0) {
    return cycleLogs.value[cycleLogs.value.length - 1].cycle
  }
  return 0
})

const filteredLogs = computed(() => {
  let logs = activityLogs.value

  const effectiveCycle = selectedCycle.value === 0 ? lastCycle.value : selectedCycle.value

  if (effectiveCycle > 0) {
    logs = logs.filter(log => log.cycle === effectiveCycle)
  }

  // 时间范围筛选
  if (timeRange.value && timeRange.value[0] && timeRange.value[1]) {
    const [startDate, endDate] = timeRange.value
    logs = logs.filter(log => {
      const logDate = log.time.split(' ')[0]
      return logDate >= startDate && logDate <= endDate
    })
  }

  // 类型筛选
  if (filterType.value) {
    logs = logs.filter(log => log.type === filterType.value)
  }

  // 关键词搜索
  if (searchKeyword.value.trim()) {
    const keyword = searchKeyword.value.toLowerCase()
    logs = logs.filter(log =>
      log.message.toLowerCase().includes(keyword) ||
      log.time.includes(keyword)
    )
  }

  return logs
})

// 按日期和周期分组的日志
const groupedLogs = computed(() => {
  const logs = filteredLogs.value
  const groups: Record<string, Record<string, ActivityLog[]>> = {}

  logs.forEach(log => {
    const date = log.time.split(' ')[0]
    const cycle = String(log.cycle ?? 'null')

    if (!groups[date]) {
      groups[date] = {}
    }
    if (!groups[date][cycle]) {
      groups[date][cycle] = []
    }
    groups[date][cycle].push(log)
  })

  // 转换为数组格式并按日期倒序排序
  const result: Array<{
    date: string
    cycles: Array<{ cycle: number | null; startTime: string; logs: ActivityLog[] }>
  }> = []

  const sortedDates = Object.keys(groups).sort((a, b) => b.localeCompare(a))

  sortedDates.forEach(date => {
    const cycles = Object.entries(groups[date]).map(([cycleNum, cycleLogs]) => ({
      cycle: cycleNum === 'null' ? null : parseInt(cycleNum),
      startTime: cycleLogs[0]?.time || '',
      logs: cycleLogs
    }))

    // 按周期倒序排序
    cycles.sort((a, b) => {
      if (a.cycle === null) return 1
      if (b.cycle === null) return -1
      return b.cycle - a.cycle
    })

    result.push({ date, cycles })
  })

  return result
})

function getTypeCount(type: string) {
  return filteredLogs.value.filter(log => log.type === type).length
}

function getTypeCountInCycle(cycleGroup: CycleGroup, type: string) {
  return cycleGroup.logs.filter(log => log.type === type).length
}

function getCycleTagType(cycleGroup: CycleGroup) {
  const errorCount = getTypeCountInCycle(cycleGroup, 'error')
  const warningCount = getTypeCountInCycle(cycleGroup, 'warning')
  if (errorCount > 0) return 'danger'
  if (warningCount > 0) return 'warning'
  return 'info'
}

function showCycleDetail(cycleGroup: CycleGroup) {
  selectedCycleDetail.value = cycleGroup
  cycleDetailVisible.value = true
}

function getLogIcon(type: string) {
  const icons: Record<string, string> = {
    info: '📋',
    success: '✅',
    warning: '⚠️',
    error: '❌'
  }
  return icons[type] || '📝'
}

function formatLogTime(fullTime: string): string {
  // 只显示时间部分，去掉日期，更紧凑
  const match = fullTime.match(/\d{2}:\d{2}:\d{2}/)
  return match ? match[0] : fullTime
}

function getLogSummary(message: string): string {
  // 提取摘要信息，简化显示
  const patterns = [
    { regex: /🔄 开始第\s*(\d+)\s*个周期/, summary: (m: RegExpMatchArray) => `开始周期 #${m[1]}` },
    { regex: /📈 市场扫描: 发现\s*(\d+)\s*个机会.*生成\s*(\d+)\s*个信号/, summary: (m: RegExpMatchArray) => `扫描: ${m[1]}机会/${m[2]}信号` },
    { regex: /✅ 周期\s*(\d+)\s*完成/, summary: (m: RegExpMatchArray) => `周期 #${m[1]} 完成` },
    { regex: /❌ 周期\s*(\d+)\s*失败:\s*(.+)/, summary: (m: RegExpMatchArray) => `周期失败: ${m[2].slice(0, 20)}...` },
    { regex: /→ (.+?): \$(.+) 趋势(\d+)共振(\d+)/, summary: (m: RegExpMatchArray) => `${m[1]} 趋势${m[3]} 共振${m[4]}` },
    { regex: /✓ 数据状态正常/, summary: () => `数据正常` },
    { regex: /⚠️ 数据需要刷新/, summary: () => `需刷新数据` },
    { regex: /协调器已启动，间隔(\d+)分钟，模拟:(true|false)/, summary: (m: RegExpMatchArray) => `启动 ${m[1]}min ${m[2] === 'true' ? '模拟' : '实盘'}` },
    { regex: /协调器已停止/, summary: () => `已停止` },
    { regex: /执行交易检查中...\s*检查\s*(\d+)\s*个币种/, summary: (m: RegExpMatchArray) => `检查 ${m[1]} 币种` },
    { regex: /🚀 协调器已启动/, summary: () => `协调器启动` },
    { regex: /⏹ 协调器已停止/, summary: () => `协调器停止` },
  ]

  for (const { regex, summary } of patterns) {
    const match = message.match(regex)
    if (match) {
      return summary(match)
    }
  }

  // 默认：显示前 50 个字符
  if (message.length <= 50) {
    return message
  }
  return message.slice(0, 50) + '...'
}

function exportCycleLogs(cycleGroup: CycleGroup) {
  const lines: string[] = []

  lines.push(`--- 分析周期 ${cycleGroup.startTime || '未分类'} ---`)
  lines.push(`  开始时间: ${cycleGroup.startTime}`)
  lines.push('')

  cycleGroup.logs.forEach(log => {
    // 移除时间戳中的日期部分，只保留时间
    const timeParts = log.time.split(' ')
    const timeShort = timeParts.length > 1 ? timeParts[1] : timeParts[0]
    
    // 判断缩进级别
    let message = log.message
    let indent = '  '
    
    if (message.startsWith('  ') || message.startsWith('    ')) {
      // 已经有缩进
      const existingIndent = message.match(/^(\s*)/)?.[1] || ''
      message = message.trim()
      indent = existingIndent
    } else if (message.match(/^(📋|🔧|📊|📈|📉|🔄|⏰|💰|⚠️|✅|❌|🎯|🐦|⏱️)/)) {
      // 带图标的主标题
      indent = ''
    } else if (message.match(/^(步骤|分析|检查|验证|计算)/)) {
      // 主步骤，2空格缩进
      indent = ''
    } else if (message.match(/^(当前|动态|智能|技术面|成交量|RSI|舆情|价格|趋势)/)) {
      // 分析项，2空格缩进
      indent = '  '
    } else if (message.match(/^(波动率|市值|止损|止盈|检查:)/)) {
      // 深层分析，4空格缩进
      indent = '    '
    } else if (message.startsWith('• ')) {
      // 列表项，2空格缩进
      indent = '  '
    } else if (message.startsWith('决策:')) {
      // 决策行
      indent = ''
    } else if (message.startsWith('原因:')) {
      // 原因行
      indent = '  '
    }
    
    // 错误和警告添加图标前缀
    let prefix = ''
    if (log.type === 'error' || log.type === 'warning') {
      const icon = getLogIcon(log.type)
      prefix = `${icon}${timeShort}  `
    } else if (!message.match(/^(📋|🔧|📊|📈|📉|🔄|⏰|💰|⚠️|✅|❌|🎯|🐦|⏱️)/)) {
      // 没有图标的日志，添加时间
      prefix = `${timeShort}  `
    }
    
    // 处理多行消息
    const messageLines = message.split('\n')
    messageLines.forEach((line, idx) => {
      if (idx === 0) {
        lines.push(`${indent}${prefix}${line}`)
      } else {
        lines.push(`${indent}${' '.repeat(prefix.length)}${line}`)
      }
    })
  })

  const content = lines.join('\n')

  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `cycle-${cycleGroup.cycle || 'uncategorized'}-logs-${new Date().toISOString().slice(0, 10)}.txt`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)

  ElMessage.success(`已导出 ${cycleGroup.logs.length} 条日志`)
}

function exportLogs() {
  const logs = filteredLogs.value
  if (logs.length === 0) {
    ElMessage.warning('没有可导出的日志')
    return
  }

  const grouped = groupedLogs.value
  const lines: string[] = []

  grouped.forEach((group, gIndex) => {
    // 第一个日期时添加标题
    if (gIndex === 0) {
      lines.push('=== AI自主交易系统日志 ===')
      lines.push(`导出时间: ${new Date().toLocaleString('zh-CN')}`)
      lines.push(`总计 ${logs.length} 条日志`)
      lines.push('')
    }

    lines.push(`${''.repeat(60)}`)
    lines.push(`📅 ${group.date}`)
    lines.push(''.repeat(60))

    group.cycles.forEach((cycle, cIndex) => {
      // 添加周期标题或空行分隔
      if (cycle.cycle === null) {
        if (cIndex > 0) lines.push('')
        lines.push('📋 未分类日志')
      } else {
        if (cIndex > 0) lines.push('')
        lines.push(`🔄 周期 #${cycle.cycle}`)
        lines.push(`  ⏰ 开始时间: ${cycle.startTime}`)
      }
      lines.push('')

      cycle.logs.forEach(log => {
        // 移除时间戳中的日期部分，只保留时间
        const timeParts = log.time.split(' ')
        const timeShort = timeParts.length > 1 ? timeParts[1] : timeParts[0]
        
        // 移除消息开头的图标（如果有），根据类型判断缩进级别
        let message = log.message
        let indent = ''
        
        // 根据消息内容判断缩进层级
        if (message.startsWith('  ') || message.startsWith('    ')) {
          // 已经有缩进，保持原样
          indent = message.match(/^(\s*)/)?.[1] || ''
          message = message.trim()
        } else if (message.startsWith('• ') || message.match(/^\[.*\]/)) {
          // 列表项或括号内容，2空格缩进
          indent = '  '
          message = message
        } else if (message.match(/^(步骤|分析|检查|验证|计算|决策|结果|扫描)/)) {
          // 主步骤标题，不缩进
          indent = ''
        } else if (message.match(/^(当前|动态|智能|技术面|成交量|RSI|舆情|价格|趋势|📊|📡)/)) {
          // 详细分析项，2空格缩进
          indent = '  '
        } else if (message.match(/^(波动率|市值|止损|止盈|检查:)/)) {
          // 深层分析项，4空格缩进
          indent = '    '
        }
        
        // 根据日志类型添加图标前缀（仅某些重要日志）
        let prefix = ''
        if (log.type === 'error' || log.type === 'warning') {
          const icon = getLogIcon(log.type)
          prefix = `${icon}${timeShort}  `
        } else if (message.match(/^(📋|🔧|📊|📈|📉|🔄|⏰|💰|⚠️|✅|❌|🎯|🐦|⏱️)/)) {
          // 消息本身已有图标，直接使用
          prefix = ''
        } else if (!indent) {
          // 顶级消息，添加时间
          prefix = `${timeShort}  `
        }
        
        // 处理多行消息
        const messageLines = message.split('\n')
        messageLines.forEach((line, idx) => {
          if (idx === 0) {
            lines.push(`${indent}${prefix}${line}`)
          } else {
            // 续行保持缩进
            lines.push(`${indent}${' '.repeat(prefix.length)}${line}`)
          }
        })
      })
    })
  })

  const content = lines.join('\n')

  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `trading-logs-${new Date().toISOString().slice(0, 10)}.txt`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)

  ElMessage.success(`已导出 ${logs.length} 条日志`)
}

const LOG_STORAGE_KEY = 'coordinator_logs'
const CYCLE_LOGS_KEY = 'coordinator_cycle_logs'
const MAX_LOGS = 1000
const MAX_CYCLES = 50

// 从 localStorage 加载日志
function loadLogsFromStorage() {
  try {
    const stored = localStorage.getItem(LOG_STORAGE_KEY)
    if (stored) {
      const logs = JSON.parse(stored)
      activityLogs.value = logs
    }
    const cycleStored = localStorage.getItem(CYCLE_LOGS_KEY)
    if (cycleStored) {
      cycleLogs.value = JSON.parse(cycleStored)
      if (cycleLogs.value.length > 0) {
        currentCycle.value = cycleLogs.value[cycleLogs.value.length - 1].cycle
      }
    }
  } catch (e) {
    console.error('Failed to load logs from storage:', e)
  }
}

// 保存日志到 localStorage
function saveLogsToStorage() {
  try {
    localStorage.setItem(LOG_STORAGE_KEY, JSON.stringify(activityLogs.value))
    localStorage.setItem(CYCLE_LOGS_KEY, JSON.stringify(cycleLogs.value))
  } catch (e) {
    console.error('Failed to save logs to storage:', e)
  }
}

function addLog(message: string, type: 'info' | 'success' | 'warning' | 'error' = 'info', logTime?: string, cycle?: number) {
  const now = new Date()
  const beijingOptions = { timeZone: 'Asia/Shanghai' }
  const time = logTime || now.toLocaleTimeString('zh-CN', beijingOptions)
  const date = now.toLocaleDateString('zh-CN', beijingOptions)
  const logCycle = cycle || currentCycle.value
  
  const logEntry: ActivityLog = { 
    time: `${date} ${time}`, 
    message, 
    type,
    cycle: logCycle
  }
  
  activityLogs.value.push(logEntry)
  if (activityLogs.value.length > MAX_LOGS) {
    activityLogs.value = activityLogs.value.slice(-MAX_LOGS)
  }
  
  // 添加到当前周期的日志
  if (logCycle > 0) {
    let cycleLog = cycleLogs.value.find(c => c.cycle === logCycle)
    if (!cycleLog) {
      cycleLog = {
        cycle: logCycle,
        startTime: `${date} ${time}`,
        logs: []
      }
      cycleLogs.value.push(cycleLog)
      if (cycleLogs.value.length > MAX_CYCLES) {
        cycleLogs.value = cycleLogs.value.slice(-MAX_CYCLES)
      }
    }
    cycleLog.logs.push(logEntry)
  }
  
  // 保存到 localStorage
  saveLogsToStorage()
  // 自动滚动到底部
  if (autoScroll.value) {
    nextTick(() => {
      scrollToBottom()
    })
  }
}

function startNewCycle(cycleNumber: number) {
  currentCycle.value = cycleNumber
  const now = new Date()
  const beijingOptions = { timeZone: 'Asia/Shanghai' }
  const startTime = `${now.toLocaleDateString('zh-CN', beijingOptions)} ${now.toLocaleTimeString('zh-CN', beijingOptions)}`
  
  const cycleLog: CycleLog = {
    cycle: cycleNumber,
    startTime: startTime,
    logs: []
  }
  cycleLogs.value.push(cycleLog)
  if (cycleLogs.value.length > MAX_CYCLES) {
    cycleLogs.value = cycleLogs.value.slice(-MAX_CYCLES)
  }
  saveLogsToStorage()
}

function toggleAutoScroll() {
  autoScroll.value = !autoScroll.value
  if (autoScroll.value) {
    scrollToBottom()
    ElMessage.success('自动滚动已开启')
  } else {
    ElMessage.info('自动滚动已关闭')
  }
}

function scrollToTop() {
  if (logContainer.value) {
    logContainer.value.scrollTop = 0
  }
}

function scrollToBottom() {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}

function handleScroll() {
  if (!logContainer.value) return
  const { scrollTop, scrollHeight, clientHeight } = logContainer.value
  const isAtBottom = scrollHeight - scrollTop - clientHeight < 10

  // 显示/隐藏回到顶部按钮
  showScrollToTop.value = scrollTop > 200

  // 如果用户手动滚动到底部，自动开启自动滚动
  if (isAtBottom && !autoScroll.value) {
    autoScroll.value = true
  }
  // 如果用户向上滚动，关闭自动滚动
  if (!isAtBottom && autoScroll.value) {
    autoScroll.value = false
  }
}

function clearLogs() {
  activityLogs.value = []
  cycleLogs.value = []
  currentCycle.value = 0
  selectedCycle.value = 0
  saveLogsToStorage()
  addLog('🗑️ 日志已清空', 'info')
}

async function clearErrors() {
  try {
    const response = await fetch('/api/coordinator/errors', { method: 'DELETE' })
    if (response.ok) {
      status.value.errors = []
      errorsClearedAt.value = Date.now()
      ElMessage.success('错误信息已清除')
    }
  } catch (error) {
    ElMessage.error('清除错误失败')
  }
}

function addResultLogs(result: any, cycle?: number) {
  // 优先使用后端返回的日志
  if (result?.logs && result.logs.length > 0) {
    result.logs.forEach((log: any) => {
      addLog(log.message, log.type || 'info', log.time, cycle)
    })
    return
  }

  // 兼容旧逻辑
  if (!result || !result.steps) return

  if (result.steps.data_reminder) {
    if (result.steps.data_reminder.needs_refresh) {
      addLog('⚠️ 数据需要刷新，建议立即执行交易检查', 'warning', undefined, cycle)
    } else {
      addLog('✓ 数据状态正常', 'success', undefined, cycle)
    }
  }

  if (result.steps.trading) {
    const oppCount = result.steps.trading.opportunities?.length || 0
    const sigCount = result.steps.trading.signals?.length || 0
    addLog(`📈 市场扫描: 发现${oppCount}个机会, 生成${sigCount}个信号`, 'info', undefined, cycle)

    if (result.steps.trading.opportunities?.length > 0) {
      result.steps.trading.opportunities.forEach((opp: any) => {
        addLog(`  → ${opp.coin}: $${opp.price?.toFixed(6)} 趋势${opp.trend_score}共振${opp.resonance_score}`, 'info', undefined, cycle)
      })
    }
  }

  if (result.status === 'completed') {
    addLog(`✅ 周期 ${result.cycle} 完成`, 'success', undefined, cycle)
  } else if (result.status === 'error') {
    addLog(`❌ 周期 ${result.cycle} 失败: ${result.error}`, 'error', undefined, cycle)
  }
}

async function fetchStatus() {
  try {
    const response = await fetch('/api/v1/services/coordinator/status')
    if (response.ok) {
      const data = await response.json()
      const wasRunning = status.value.is_running
      
      // 如果用户手动清除了错误，且后端返回的错误没有变化，则保持清除状态
      if (errorsClearedAt.value > 0) {
        data.errors = []
      }
      
      status.value = data

      if (data.is_running && !wasRunning) {
        addLog('🚀 协调器已启动', 'success')
      } else if (!data.is_running && wasRunning) {
        addLog('⏹ 协调器已停止', 'warning')
      }

      if (data.last_cycle_time && data.last_cycle_time !== status.value.last_cycle_time) {
        addLog(`🔄 上次运行: ${data.last_cycle_time}`, 'info')
      }
    }
  } catch (error) {
    console.error('Failed to fetch coordinator status:', error)
  }
}

async function startCoordinator() {
  loading.value = true
  try {
    const response = await fetch('/api/v1/services/coordinator/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        dry_run: dryRun.value
      })
    })
    if (response.ok) {
      const result = await response.json()
      ElMessage.success('协调器已启动')
      addLog(`🚀 ${result.message}`, 'success')
      await fetchStatus()
    }
  } catch (error) {
    ElMessage.error('启动失败')
    addLog('❌ 启动失败', 'error')
  } finally {
    loading.value = false
  }
}

async function stopCoordinator() {
  loading.value = true
  try {
    const response = await fetch('/api/v1/services/coordinator/stop', {
      method: 'POST'
    })
    if (response.ok) {
      ElMessage.success('协调器已停止')
      addLog('⏹ 协调器已停止', 'warning')
      await fetchStatus()
    }
  } catch (error) {
    ElMessage.error('停止失败')
  } finally {
    loading.value = false
  }
}

async function runSingleCycle() {
  loading.value = true
  cycleResult.value = null
  // 每次执行前检查是否是开始新周期
  const statusResponse = await fetch('/api/v1/services/coordinator/status')
  if (statusResponse.ok) {
    const statusData = await statusResponse.json()
    if (statusData.total_cycles !== currentCycle.value) {
      startNewCycle(statusData.total_cycles)
    }
  }
  try {
    addLog('🔄 开始执行交易周期...', 'info')
    const response = await fetch('/api/v1/services/coordinator/cycle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dry_run: dryRun.value })
    })
    if (response.ok) {
      const result = await response.json()
      cycleResult.value = result
      // 使用result中的cycle信息
      if (result.cycle) {
        if (result.cycle !== currentCycle.value) {
          startNewCycle(result.cycle)
        }
        addResultLogs(result, result.cycle)
      }
      ElMessage.success('执行完成')
      await fetchStatus()
    } else {
      addLog('❌ 执行失败', 'error')
    }
  } catch (error) {
    ElMessage.error('执行失败')
    addLog('❌ 执行失败', 'error')
  } finally {
    loading.value = false
  }
}

let ws: WebSocket | null = null
let wsReconnectTimer: number | null = null
let wsReconnectCount = 0
const MAX_RECONNECT_COUNT = 5

function connectWebSocket() {
  // 清除之前的重连定时器
  if (wsReconnectTimer) {
    clearTimeout(wsReconnectTimer)
    wsReconnectTimer = null
  }

  // 如果已达到最大重连次数，不再重连
  if (wsReconnectCount >= MAX_RECONNECT_COUNT) {
    addLog('⚠️ WebSocket 重连次数过多，已停止', 'warning')
    return
  }

  // 使用固定的后端地址 - WebSocket 路径是 /ws/trading
  const wsUrl = `ws://localhost:8000/ws/trading`

  try {
    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      wsReconnectCount = 0
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'coordinator_log') {
          const log = data.data
          // 检测是否是周期开始的日志
          if (log.message && log.message.includes('开始第') && log.message.includes('个周期')) {
            const match = log.message.match(/第\s*(\d+)\s*个周期/)
            if (match) {
              const cycleNum = parseInt(match[1])
              if (cycleNum !== currentCycle.value) {
                startNewCycle(cycleNum)
              }
            }
          }
          addLog(log.message, log.type || 'info', log.time, currentCycle.value)
        }
      } catch (e) {
        console.error('WebSocket message error:', e)
      }
    }

    ws.onclose = (event) => {
      if (!event.wasClean) {
        if (wsReconnectCount === 0) {
          addLog('⚠️ 与服务器连接断开，正在尝试重连...', 'warning', undefined, currentCycle.value)
        }
        if (wsReconnectCount < MAX_RECONNECT_COUNT) {
          wsReconnectCount++
          wsReconnectTimer = window.setTimeout(() => {
            connectWebSocket()
          }, 3000)
        } else {
          addLog('❌ 服务器连接失败，请检查后端服务是否正常运行', 'error', undefined, currentCycle.value)
        }
      }
    }

    ws.onerror = (error) => {
      if (wsReconnectCount === 0) {
        addLog('❌ WebSocket连接错误，服务器可能已停止', 'error', undefined, currentCycle.value)
        console.error('WebSocket error:', error)
      }
    }
  } catch (e) {
    console.error('Failed to create WebSocket:', e)
  }
}

function disconnectWebSocket() {
  if (wsReconnectTimer) {
    clearTimeout(wsReconnectTimer)
    wsReconnectTimer = null
  }
  if (ws) {
    ws.close()
    ws = null
  }
}

onMounted(() => {
  // 先加载历史日志
  loadLogsFromStorage()
  fetchStatus()
  // 只在首次加载时添加面板加载日志
  if (activityLogs.value.length === 0) {
    addLog('📊 协调器面板已加载', 'info')
  }
  pollInterval = window.setInterval(fetchStatus, 5000)
  connectWebSocket()
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
  disconnectWebSocket()
})
</script>

<style lang="scss" scoped>
.coordinator-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .title {
      font-size: 16px;
      font-weight: 600;
    }
  }

  .card-content {
    margin-top: 16px;

    &.vertical-layout {
      display: flex;
      flex-direction: column;
      gap: 16px;
      height: calc(100% - 40px);
      min-height: 450px;

      .top-panel {
        flex: 0 0 auto;

        .top-row {
          display: flex;
          gap: 20px;
          margin-bottom: 12px;

          .status-info {
            flex: 1;
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
          }

          .control-section {
            display: flex;
            flex-direction: column;
            gap: 12px;

            .control-buttons {
              display: flex;
              gap: 8px;
            }

            .config-section {
              display: flex;
              gap: 16px;
              align-items: center;
              padding: 8px 12px;
              background: rgba(255, 255, 255, 0.05);
              border-radius: 8px;
              border: 1px solid rgba(255, 255, 255, 0.1);

              .config-row {
                display: flex;
                align-items: center;
                gap: 8px;

                .unit {
                  font-size: 12px;
                  color: rgba(255, 255, 255, 0.7);
                }
              }
            }
          }
        }

        .cycle-result {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 8px;
          padding: 10px;
          margin-bottom: 12px;

          .result-header {
            font-weight: 600;
            margin-bottom: 6px;
            font-size: 13px;
          }

          .result-status {
            margin-bottom: 8px;
            font-size: 12px;
          }

          .result-steps {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
          }

          .step-item {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 6px;
            padding: 6px 10px;
            min-width: 80px;

            .step-title {
              font-weight: 600;
              margin-bottom: 2px;
              font-size: 12px;
            }

            .step-detail {
              font-size: 11px;
              color: rgba(255, 255, 255, 0.7);
            }

            .step-warning {
              color: #e6a23c;
              font-size: 11px;
            }

            .step-ok {
              color: #67c23a;
              font-size: 11px;
            }
          }
        }
      }

      .bottom-panel {
        height: 400px;
        flex-shrink: 0;
        display: flex;
        flex-direction: column;
        position: relative;

        .activity-log {
          height: 100%;
          max-height: none;
          position: relative;
        }
      }
    }
  }

  .status-info {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    margin-bottom: 16px;

    .info-row {
      display: flex;
      gap: 8px;

      .label {
        color: rgba(255, 255, 255, 0.7);
      }

      .value {
        font-weight: 500;
        color: #ffffff;
      }
    }
  }

  .control-buttons {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;

    :deep(.el-button) {
      min-width: 90px;
      font-weight: 600;
    }

    .start-btn {
      background: linear-gradient(135deg, #11998e, #38ef7d) !important;
      border: none !important;
      color: #ffffff !important;
      box-shadow: 0 2px 8px rgba(56, 239, 125, 0.3) !important;

      &:hover {
        background: linear-gradient(135deg, #12b89a, #4ff99a) !important;
      }

      &:disabled {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        color: rgba(255, 255, 255, 0.4) !important;
        box-shadow: none !important;
      }
    }

    .stop-btn {
      background: linear-gradient(135deg, #ff4d4f, #d32f2f) !important;
      border: none !important;
      color: #ffffff !important;
      box-shadow: 0 2px 8px rgba(255, 77, 79, 0.3) !important;

      &:hover {
        background: linear-gradient(135deg, #ff6659, #f44336) !important;
      }

      &:disabled {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        color: rgba(255, 255, 255, 0.4) !important;
        box-shadow: none !important;
      }
    }
  }

  .config-section {
    display: flex;
    gap: 16px;
    align-items: center;
    margin-bottom: 16px;
    padding: 12px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.1);

    .config-row {
      display: flex;
      align-items: center;
      gap: 8px;

      .label {
        color: rgba(255, 255, 255, 0.7);
      }
    }
  }

  .cycle-result {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 16px;
    border: 1px solid rgba(255, 255, 255, 0.1);

    .result-header {
      font-weight: 600;
      margin-bottom: 8px;
      color: #ffffff;
    }

    .result-status {
      margin-bottom: 12px;
      font-size: 14px;
      color: rgba(255, 255, 255, 0.7);
    }

    .result-steps {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .step-item {
      background: rgba(0, 0, 0, 0.2);
      border-radius: 6px;
      padding: 8px;

      .step-title {
        font-weight: 600;
        margin-bottom: 4px;
      }

      .step-detail {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.7);
      }

      .step-warning {
        color: #e6a23c;
        font-size: 12px;
      }

      .step-ok {
        color: #67c23a;
        font-size: 12px;
      }
    }

    .opportunities-preview {
      margin-top: 8px;
      padding: 8px;
      background: #e6f7ff;
      border-radius: 4px;
      border: 1px solid rgba(102, 126, 234, 0.3);

      .opp-header {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.7);
        margin-bottom: 4px;
      }

      .opp-item {
        display: flex;
        gap: 8px;
        font-size: 11px;
        padding: 2px 0;
        align-items: center;

        .opp-coin {
          font-weight: 600;
          min-width: 50px;
          color: #ffffff;
        }

        .opp-price {
          color: rgba(255, 255, 255, 0.7);
          min-width: 80px;
        }

        .opp-score {
          color: #409eff;
          min-width: 80px;
        }

        .opp-reason {
          color: rgba(255, 255, 255, 0.7);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
}

    .signals-list {
      .signal-item {
        font-size: 12px;
        padding: 2px 0;
      }
    }

    .result-error {
      color: #f56c6c;
      font-size: 12px;
      margin-top: 8px;
    }
  }

  .activity-log {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    height: 100%;
    border: 1px solid rgba(255, 255, 255, 0.1);

    .log-header {
      font-weight: 600;
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;
      flex-wrap: wrap;
      gap: 8px;
      color: #ffffff;
      padding-bottom: 8px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);

      .log-title {
        font-size: 14px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 6px;
      }

      .log-filters {
        display: flex;
        gap: 8px;
        flex: 1;
        align-items: center;

        :deep(.el-select),
        :deep(.el-date-editor) {
          .el-input__wrapper {
            padding: 4px 8px;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
          }

          .el-input__inner {
            font-size: 12px;
          }
        }

        .search-input {
          flex: 1;
          min-width: 150px;
        }
      }

      .log-actions {
        display: flex;
        gap: 4px;

        .el-button {
          padding: 4px 8px;
          font-size: 12px;

          .el-icon {
            font-size: 14px;
          }
        }
      }
    }

    .log-stats {
      display: flex;
      gap: 8px;
      margin-bottom: 8px;
      padding: 6px 10px;
      background: rgba(0, 0, 0, 0.03);
      border-radius: 6px;
      flex-wrap: wrap;
      font-size: 12px;

      .stat-item {
        display: flex;
        align-items: center;
        gap: 4px;
      }
    }

    .log-entries {
      display: flex;
      flex-direction: column;
      gap: 4px;
      overflow-y: auto;
      flex: 1;
      min-height: 0;
      padding-right: 4px;

      &::-webkit-scrollbar {
        width: 6px;
      }

      &::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.05);
        border-radius: 3px;
      }

      &::-webkit-scrollbar-thumb {
        background: rgba(0, 0, 0, 0.2);
        border-radius: 3px;

        &:hover {
          background: rgba(0, 0, 0, 0.3);
        }
      }

      .empty-logs {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        min-height: 200px;
      }

      .log-group {
        margin-bottom: 20px;

        &:last-child {
          margin-bottom: 0;
        }

        .date-divider {
          display: flex;
          align-items: center;
          padding: 12px 0;
          position: sticky;
          top: 0;
          background: rgba(255, 255, 255, 0.05);
          z-index: 10;

          &::before,
          &::after {
            content: '';
            flex: 1;
            height: 1px;
            background: rgba(255, 255, 255, 0.1);
          }

          .date-label {
            padding: 4px 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            font-size: 12px;
            font-weight: 600;
            border-radius: 12px;
            margin: 0 12px;
          }
        }

        .cycle-block {
          background: rgba(255, 255, 255, 0.08);
          border-radius: 8px;
          border: 1px solid rgba(0, 0, 0, 0.06);
          margin-bottom: 12px;
          cursor: pointer;
          transition: all 0.3s ease;
          overflow: hidden;

          &:hover {
            border-color: rgba(102, 126, 234, 0.3);
            box-shadow: 0 4px 16px rgba(102, 126, 234, 0.1);
            transform: translateX(4px);
          }

          .cycle-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 12px;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.02) 0%, rgba(118, 75, 162, 0.02) 100%);
            border-bottom: 1px solid rgba(0, 0, 0, 0.04);

            .cycle-info {
              display: flex;
              align-items: center;
              gap: 8px;
              flex: 1;

              .cycle-icon {
                color: #667eea;
                font-size: 14px;
              }

              .cycle-title {
                font-size: 13px;
                font-weight: 600;
                color: #ffffff;
              }

              .cycle-time {
                font-size: 11px;
                color: rgba(255, 255, 255, 0.6);
                font-family: 'Monaco', 'Consolas', monospace;
              }

              :deep(.el-tag) {
                margin-left: 6px;
              }
            }

            .cycle-stats {
              display: flex;
              gap: 4px;

              :deep(.el-tag) {
                font-size: 11px;
                padding: 2px 6px;
                height: 20px;
                line-height: 16px;
              }
            }
          }

          .cycle-preview {
            padding: 8px 12px;
            background: rgba(255, 255, 255, 0.05);

            .preview-log {
              display: flex;
              align-items: center;
              gap: 8px;
              padding: 4px 0;
              font-size: 11px;

              .preview-icon {
                min-width: 14px;
                font-size: 11px;
              }

              .preview-time {
                min-width: 50px;
                color: rgba(255, 255, 255, 0.6);
                font-family: 'Monaco', 'Consolas', monospace;
              }

              .preview-message {
                flex: 1;
                color: rgba(255, 255, 255, 0.8);
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
              }
            }

            .preview-more {
              text-align: center;
              padding: 4px 0;
              font-size: 11px;
              color: #667eea;
              font-weight: 500;
            }
          }
        }
      }

      .log-entry {
      display: flex;
      flex-direction: column;
      gap: 4px;
      font-size: 12px;
      padding: 6px 10px;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 6px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      cursor: pointer;
      transition: all 0.2s ease;
      min-height: 32px;

      &:hover {
        border-color: rgba(102, 126, 234, 0.3);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        transform: translateX(2px);
      }

      &.expanded {
        .log-message {
          font-weight: 500;
        }
      }

      .log-main {
        display: flex;
        align-items: center;
        gap: 8px;
        width: 100%;

        .log-icon {
          font-size: 12px;
          min-width: 18px;
          line-height: 1;
        }

        .log-time {
          color: rgba(255, 255, 255, 0.5);
          font-size: 11px;
          min-width: 65px;
          font-family: 'Monaco', 'Consolas', monospace;
          font-weight: 500;
        }

        .log-message {
          flex: 1;
          word-break: break-word;
          line-height: 1.4;
          color: #ffffff;
          font-size: 11px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .expand-icon {
          color: rgba(255, 255, 255, 0.5);
          transition: transform 0.2s ease;
          flex-shrink: 0;
          font-size: 14px;

          &.expanded {
            transform: rotate(90deg);
            color: #667eea;
          }
        }
      }

      .log-meta {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 10px;
        padding-left: 26px;

        :deep(.el-tag) {
          height: 18px;
          line-height: 18px;
          font-size: 10px;
          padding: 0 6px;
        }
      }

      .log-detail {
        margin-top: 8px;
        padding: 10px;
        background: rgba(0, 0, 0, 0.03);
        border-radius: 6px;
        border-left: 3px solid currentColor;

        .detail-label {
          font-size: 10px;
          color: rgba(255, 255, 255, 0.5);
          margin-bottom: 6px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .detail-content {
          font-size: 11px;
          color: #ffffff;
          line-height: 1.6;
          word-break: break-word;
          white-space: pre-wrap;
          font-family: 'Monaco', 'Consolas', monospace;
          background: rgba(255, 255, 255, 0.08);
          padding: 8px;
          border-radius: 4px;
          margin-bottom: 8px;
          border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .detail-meta {
          display: flex;
          gap: 16px;
          font-size: 10px;
          color: rgba(255, 255, 255, 0.6);

          span {
            display: flex;
            align-items: center;
            gap: 4px;

            &:before {
              content: '•';
              color: currentColor;
            }
          }
        }
      }

      &.info {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.03) 0%, rgba(118, 75, 162, 0.03) 100%);
        border-left: 2px solid #667eea;

        .log-detail {
          border-left-color: #667eea;
        }
      }

      &.success {
        background: linear-gradient(135deg, rgba(103, 194, 58, 0.03) 0%, rgba(56, 239, 125, 0.03) 100%);
        border-left: 2px solid #67c23a;

        .log-detail {
          border-left-color: #67c23a;
        }
      }

      &.warning {
        background: linear-gradient(135deg, rgba(230, 162, 60, 0.03) 0%, rgba(240, 147, 251, 0.03) 100%);
        border-left: 2px solid #e6a23c;

        .log-detail {
          border-left-color: #e6a23c;
        }
      }

      &.error {
        background: linear-gradient(135deg, rgba(245, 108, 108, 0.03) 0%, rgba(245, 87, 108, 0.03) 100%);
        border-left: 2px solid #f56c6c;

        .log-detail {
          border-left-color: #f56c6c;
        }
      }
    }

    // 日志详情展开动画
    .log-detail-enter-active,
    .log-detail-leave-active {
      transition: all 0.3s ease;
    }

    .log-detail-enter-from,
    .log-detail-leave-to {
      opacity: 0;
      transform: translateY(-10px);
      max-height: 0;
      margin-top: 0;
      padding-top: 0;
      padding-bottom: 0;
    }
    }
  }

  // 浮动的回到顶部按钮
  .scroll-to-top-btn {
    position: absolute;
    right: 20px;
    bottom: 20px;
    z-index: 10;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);

    .el-icon {
      font-size: 16px;
    }
  }

  // 淡入淡出动画
  .fade-enter-active,
  .fade-leave-active {
    transition: all 0.3s ease;
  }

  .fade-enter-from,
  .fade-leave-to {
    opacity: 0;
    transform: scale(0.8);
  }
}

// 周期详情弹窗
.cycle-detail-dialog {
  :deep(.el-dialog__header) {
    padding: 16px 20px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
    background: linear-gradient(135deg, #f8f9fa 0%, #fff 100%);
  }

  :deep(.el-dialog__body) {
    padding: 0;
  }

  :deep(.el-dialog__title) {
    font-size: 16px;
    font-weight: 600;
    color: #ffffff;
  }

  .cycle-detail-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 20px;
    background: rgba(255, 255, 255, 0.05);
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);

    .detail-info {
      display: flex;
      gap: 20px;
      align-items: center;

      .info-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: rgba(255, 255, 255, 0.8);

        .el-icon {
          color: #667eea;
          font-size: 14px;
        }
      }
    }

    .detail-actions {
      display: flex;
      gap: 8px;

      .el-button {
        display: flex;
        align-items: center;
        gap: 4px;
      }
    }
  }

  .log-scrollbar {
    padding: 12px 20px 20px;

    .cycle-logs-list {
      display: flex;
      flex-direction: column;
      gap: 8px;

      .detail-log-entry {
        display: flex;
        flex-direction: column;
        gap: 4px;
        padding: 10px 12px;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 6px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-left: 3px solid rgba(255, 255, 255, 0.3);
        transition: all 0.2s ease;

        &:hover {
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }

        &.info {
          border-left-color: #667eea;
          background: linear-gradient(135deg, rgba(102, 126, 234, 0.02) 0%, rgba(118, 75, 162, 0.02) 100%);
        }

        &.success {
          border-left-color: #67c23a;
          background: linear-gradient(135deg, rgba(103, 194, 58, 0.02) 0%, rgba(56, 239, 125, 0.02) 100%);
        }

        &.warning {
          border-left-color: #e6a23c;
          background: linear-gradient(135deg, rgba(230, 162, 60, 0.02) 0%, rgba(240, 147, 251, 0.02) 100%);
        }

        &.error {
          border-left-color: #f56c6c;
          background: linear-gradient(135deg, rgba(245, 108, 108, 0.02) 0%, rgba(245, 87, 108, 0.02) 100%);
        }

        .detail-log-main {
          display: flex;
          align-items: center;
          gap: 10px;

          .detail-log-icon {
            font-size: 14px;
            min-width: 18px;
          }

          .detail-log-time {
            font-size: 11px;
            color: rgba(255, 255, 255, 0.6);
            font-family: 'Monaco', 'Consolas', monospace;
            min-width: 65px;
          }

          .detail-log-message {
            flex: 1;
            font-size: 12px;
            color: rgba(255, 255, 255, 0.9);
            line-height: 1.5;
            word-break: break-word;
            white-space: pre-wrap;
          }
        }
      }
    }
  }
}

.errors-section {
  margin-top: 16px;
  padding: 12px;
  background: rgba(245, 108, 108, 0.1);
  border: 1px solid #f56c6c;
  border-radius: 8px;

  .errors-header {
    font-weight: 600;
    margin-bottom: 8px;
    color: #f56c6c;
    display: flex;
    justify-content: space-between;
    align-items: center;

    .el-button {
      padding: 2px 6px;
      font-size: 12px;
    }
  }

  .error-item {
    font-size: 12px;
    color: #f56c6c;
    padding: 2px 0;
  }
}
</style>
