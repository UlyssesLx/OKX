import dayjs from 'dayjs'

/**
 * 格式化时间为 HH:mm:ss
 * @param date 日期
 * @returns 格式化后的时间字符串
 */
export function formatTime(date: Date | string | null): string {
  if (!date) return '-'
  return dayjs(date).format('HH:mm:ss')
}

/**
 * 格式化日期时间为 YYYY-MM-DD HH:mm:ss
 * @param date 日期
 * @returns 格式化后的日期时间字符串
 */
export function formatDateTime(date: Date | string | null): string {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

/**
 * 格式化价格
 * @param price 价格
 * @param decimals 小数位数，默认4位
 * @returns 格式化后的价格字符串
 */
export function formatPrice(price: number, decimals: number = 4): string {
  if (price === undefined || price === null || isNaN(price)) {
    return '0.0000'
  }
  return price.toFixed(decimals)
}

/**
 * 格式化百分比
 * @param value 数值
 * @param decimals 小数位数，默认2位
 * @returns 格式化后的百分比字符串
 */
export function formatPercent(value: number, decimals: number = 2): string {
  if (value === undefined || value === null || isNaN(value)) {
    return '0.00%'
  }
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(decimals)}%`
}

/**
 * 格式化美元金额
 * @param value 数值
 * @param decimals 小数位数，默认2位
 * @returns 格式化后的美元字符串
 */
export function formatUsd(value: number, decimals: number = 2): string {
  if (value === undefined || value === null || isNaN(value)) {
    return '$0.00'
  }
  const sign = value >= 0 ? '+' : ''
  return `${sign}$${value.toFixed(decimals)}`
}

/**
 * 格式化数量
 * @param amount 数量
 * @param decimals 小数位数，默认6位
 * @returns 格式化后的数量字符串
 */
export function formatAmount(amount: number, decimals: number = 6): string {
  if (amount === undefined || amount === null || isNaN(amount)) {
    return '0.000000'
  }
  return amount.toFixed(decimals)
}

/**
 * 格式化时间差（相对时间）
 * @param date 日期
 * @returns 格式化后的相对时间字符串
 */
export function formatTimeAgo(date: Date | string | null): string {
  if (!date) return '-'
  const now = dayjs()
  const past = dayjs(date)
  const diffSeconds = now.diff(past, 'second')
  const diffMinutes = now.diff(past, 'minute')
  const diffHours = now.diff(past, 'hour')
  const diffDays = now.diff(past, 'day')

  if (diffSeconds < 60) {
    return '刚刚'
  }
  if (diffMinutes < 60) {
    return `${diffMinutes}分钟前`
  }
  if (diffHours < 24) {
    return `${diffHours}小时前`
  }
  if (diffDays < 7) {
    return `${diffDays}天前`
  }
  return formatDateTime(date)
}

/**
 * 获取趋势类名
 * @param value 数值
 * @returns CSS类名
 */
export function getTrendClass(value: number): 'positive' | 'negative' | 'neutral' {
  if (value > 0) return 'positive'
  if (value < 0) return 'negative'
  return 'neutral'
}

/**
 * 获取趋势图标名称
 * @param value 数值
 * @returns 图标名称
 */
export function getTrendIcon(value: number): 'CaretTop' | 'CaretBottom' | 'Minus' {
  if (value > 0) return 'CaretTop'
  if (value < 0) return 'CaretBottom'
  return 'Minus'
}

/**
 * 防抖函数
 * @param fn 要执行的函数
 * @param delay 延迟时间(ms)，默认300ms
 * @returns 防抖后的函数
 */
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number = 300
): (...args: Parameters<T>) => void {
  let timeoutId: number | null = null

  return (...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
    timeoutId = window.setTimeout(() => {
      fn(...args)
      timeoutId = null
    }, delay)
  }
}

/**
 * 节流函数
 * @param fn 要执行的函数
 * @param delay 延迟时间(ms)，默认300ms
 * @returns 节流后的函数
 */
export function throttle<T extends (...args: any[]) => any>(
  fn: T,
  delay: number = 300
): (...args: Parameters<T>) => void {
  let lastCall = 0

  return (...args: Parameters<T>) => {
    const now = Date.now()
    if (now - lastCall >= delay) {
      fn(...args)
      lastCall = now
    }
  }
}

/**
 * 复制文本到剪贴板
 * @param text 要复制的文本
 * @returns Promise<boolean> 是否成功
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
      return true
    }
    // 降级方案
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    return true
  } catch {
    return false
  }
}

/**
 * 生成唯一ID
 * @returns 唯一ID字符串
 */
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

/**
 * 安全的JSON解析
 * @param str JSON字符串
 * @param defaultValue 默认值
 * @returns 解析结果或默认值
 */
export function safeJsonParse<T = any>(str: string, defaultValue: T): T {
  try {
    return JSON.parse(str) as T
  } catch {
    return defaultValue
  }
}

/**
 * 格式化大数字为K/M/B单位
 * @param num 数字
 * @returns 格式化后的字符串
 */
export function formatLargeNumber(num: number): string {
  if (num >= 1_000_000_000) {
    return `${(num / 1_000_000_000).toFixed(2)}B`
  }
  if (num >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(2)}M`
  }
  if (num >= 1_000) {
    return `${(num / 1_000).toFixed(2)}K`
  }
  return num.toFixed(2)
}
