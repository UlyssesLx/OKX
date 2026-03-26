<template>
  <div class="timezone-card card">
    <div class="card-header">
      <span class="card-title">🕐 时区感知</span>
    </div>

    <div class="timezone-info">
      <div class="info-row">
        <span class="label">当前时段</span>
        <span class="value highlight">{{ timeZoneInfo.current_time_zone }}</span>
      </div>

      <div class="info-row">
        <span class="label">活跃强度</span>
        <div class="intensity-stars">
          <span
            v-for="i in 5"
            :key="i"
            class="star"
            :class="{ active: i <= timeZoneInfo.intensity }"
          >⭐</span>
        </div>
      </div>

      <div class="info-row">
        <span class="label">建议仓位</span>
        <span class="value">${{ timeZoneInfo.position_size.min }} - ${{ timeZoneInfo.position_size.max }}</span>
      </div>

      <div class="info-row">
        <span class="label">持仓时间</span>
        <span class="value">{{ timeZoneInfo.hold_time.min }} - {{ timeZoneInfo.hold_time.max }} 分钟</span>
      </div>

      <div class="info-row">
        <span class="label">日目标占比</span>
        <span class="value">{{ (timeZoneInfo.daily_quota * 100).toFixed(0) }}%</span>
      </div>

      <div class="info-row">
        <span class="label">检查频率</span>
        <span class="value">{{ timeZoneInfo.check_interval }} 分钟</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TimeZoneInfo } from '@/types'

interface Props {
  timeZoneInfo: TimeZoneInfo
}

defineProps<Props>()
</script>

<style lang="scss" scoped>
.timezone-card {
  height: 100%;
  display: flex;
  flex-direction: column;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .timezone-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .info-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: $border-radius-sm;
    border: 1px solid rgba(255, 255, 255, 0.1);

    .label {
      color: rgba(255, 255, 255, 0.7);
      font-size: 13px;
    }

    .value {
      font-weight: 600;
      font-size: 14px;
      color: #ffffff;

      &.highlight {
        color: $primary-color;
      }
    }

    .intensity-stars {
      display: flex;
      gap: 2px;

      .star {
        opacity: 0.3;
        font-size: 14px;

        &.active {
          opacity: 1;
        }
      }
    }
  }
}
</style>
