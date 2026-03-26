<template>
  <div class="stats-card card dark-card">
    <div class="card-header">
      <div class="icon-wrapper" :class="iconClass">
        <el-icon :size="24">
          <component :is="iconComponent" />
        </el-icon>
      </div>
      <div class="title-wrapper">
        <div class="card-title">{{ title }}</div>
        <div class="card-subtitle">实时数据</div>
      </div>
      <div class="trend-indicator" :class="trendClass" v-if="trend !== 'neutral'">
        <el-icon :size="20">
          <CaretTop v-if="trend === 'up'" />
          <CaretBottom v-else />
        </el-icon>
      </div>
    </div>
    <div class="card-value" :class="trendClass">
      {{ value }}
    </div>
    <div class="card-footer">
      <span class="trend-text">
        {{ trendText }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { CaretTop, CaretBottom, TrendCharts, Wallet, Coin, DataLine } from '@element-plus/icons-vue'

interface Props {
  title: string
  value: string
  icon: string
  trend?: 'up' | 'down' | 'neutral'
}

const props = withDefaults(defineProps<Props>(), {
  trend: 'neutral'
})

const iconMap: Record<string, any> = {
  '💰': TrendCharts,
  '💵': Wallet,
  '📊': DataLine,
  '📈': Coin
}

const iconComponent = computed(() => iconMap[props.icon] || TrendCharts)

const iconClass = computed(() => {
  if (props.icon === '💰') return 'purple'
  if (props.icon === '💵') return 'green'
  if (props.icon === '📊') return 'blue'
  if (props.icon === '📈') return 'yellow'
  return 'purple'
})

const trendClass = computed(() => {
  if (props.trend === 'up') return 'positive'
  if (props.trend === 'down') return 'negative'
  return ''
})

const trendText = computed(() => {
  if (props.trend === 'up') return '较上期上升'
  if (props.trend === 'down') return '较上期下降'
  return '保持稳定'
})
</script>

<style lang="scss" scoped>
.stats-card {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 180px;
  padding: 20px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-4px);
    background: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.2);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 16px;

    .icon-wrapper {
      width: 52px;
      height: 52px;
      border-radius: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);

      &.purple {
        background: linear-gradient(135deg, #667eea, #764ba2);
      }

      &.green {
        background: linear-gradient(135deg, #11998e, #38ef7d);
      }

      &.blue {
        background: linear-gradient(135deg, #4facfe, #00f2fe);
      }

      &.yellow {
        background: linear-gradient(135deg, #fa709a, #fee140);
      }
    }

    .title-wrapper {
      flex: 1;

      .card-title {
        font-size: 14px;
        font-weight: 600;
        color: #ffffff;
        margin: 0;
        padding: 0;
        border: none;
      }

      .card-subtitle {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.65);
        margin-top: 4px;
      }
    }

    .trend-indicator {
      width: 30px;
      height: 30px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;

      &.positive {
        background: rgba(76, 175, 80, 0.25);
        color: #4caf50;
      }

      &.negative {
        background: rgba(244, 67, 54, 0.25);
        color: #f44336;
      }
    }
  }

  .card-value {
    font-size: 32px;
    font-weight: 700;
    margin-top: auto;
    margin-bottom: 12px;
    color: #ffffff;
  }

  .card-footer {
    padding-top: 12px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);

    .trend-text {
      font-size: 12px;
      color: rgba(255, 255, 255, 0.6);
    }
  }
}
</style>
