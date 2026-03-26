import { ref, onMounted, onUnmounted } from 'vue'
import { useTradingStore } from '@/stores/trading'

export function useWebSocket() {
  const tradingStore = useTradingStore()
  const ws = ref<WebSocket | null>(null)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 5

  function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/trading`

    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      console.log('WebSocket connected')
      tradingStore.setConnected(true)
      reconnectAttempts.value = 0
    }

    ws.value.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        tradingStore.updateFromWebSocket(message)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    ws.value.onclose = () => {
      console.log('WebSocket disconnected')
      tradingStore.setConnected(false)

      if (reconnectAttempts.value < maxReconnectAttempts) {
        reconnectAttempts.value++
        setTimeout(() => {
          console.log(`Reconnecting... (${reconnectAttempts.value}/${maxReconnectAttempts})`)
          connect()
        }, 3000)
      }
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  function disconnect() {
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
  }

  function send(message: any) {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(message))
    }
  }

  return {
    connect,
    disconnect,
    send
  }
}
