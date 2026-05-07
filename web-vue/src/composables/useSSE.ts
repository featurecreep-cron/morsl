import { ref, onUnmounted } from 'vue'
import { CONST } from '@/constants'

interface UseSSEOptions {
  url: string
  onGenerating?: () => void
  onMenuUpdated?: (clearOthers: boolean) => void
  onMenuCleared?: () => void
  onConnected?: (version: string) => void
  onError?: () => void
}

/**
 * SSE composable matching the morsl /api/menu/stream endpoint.
 * Named events: generating, menu_updated, menu_cleared, connected.
 */
export function useSSE(options: UseSSEOptions) {
  const connected = ref(false)
  let source: EventSource | null = null
  let retryMs: number = CONST.SSE_INITIAL_RETRY_MS
  let retryTimeout: ReturnType<typeof setTimeout> | null = null

  function connect() {
    if (source) {
      source.close()
    }

    retryMs = CONST.SSE_INITIAL_RETRY_MS
    source = new EventSource(options.url)

    source.addEventListener('generating', () => {
      options.onGenerating?.()
    })

    source.addEventListener('menu_updated', (event) => {
      let clearOthers = false
      try {
        const data = JSON.parse((event as MessageEvent).data)
        clearOthers = !!data.clear_others
      } catch {
        // ignore parse errors
      }
      options.onMenuUpdated?.(clearOthers)
    })

    source.addEventListener('menu_cleared', () => {
      options.onMenuCleared?.()
    })

    source.addEventListener('connected', (event) => {
      connected.value = true
      retryMs = CONST.SSE_INITIAL_RETRY_MS
      let version = ''
      try {
        const data = JSON.parse((event as MessageEvent).data)
        version = data.version || ''
      } catch {
        // ignore
      }
      options.onConnected?.(version)
    })

    source.onerror = () => {
      connected.value = false
      source?.close()
      source = null
      options.onError?.()

      retryTimeout = setTimeout(() => {
        retryMs = Math.min(retryMs * 2, CONST.SSE_MAX_RETRY_MS)
        connect()
      }, retryMs)
    }
  }

  function disconnect() {
    if (retryTimeout) {
      clearTimeout(retryTimeout)
      retryTimeout = null
    }
    if (source) {
      source.close()
      source = null
    }
    connected.value = false
  }

  function isOpen(): boolean {
    return source !== null && source.readyState === EventSource.OPEN
  }

  onUnmounted(disconnect)

  return { connected, connect, disconnect, isOpen }
}
