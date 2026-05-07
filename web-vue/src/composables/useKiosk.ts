import { onUnmounted, type Ref } from 'vue'
import { CONST } from '@/constants'

interface UseKioskOptions {
  gesture: string
  enabled: boolean
  headerRef: Ref<HTMLElement | null>
  onActivate: () => void
}

/**
 * Kiosk gesture detection: double-tap, long-press, or swipe-up.
 */
export function useKiosk(options: UseKioskOptions) {
  const cleanupFns: Array<() => void> = []
  let longPressTimer: ReturnType<typeof setTimeout> | null = null

  function setup() {
    cleanup()
    if (!options.enabled) return
    const gesture = options.gesture
    if (gesture === 'menu') return // hamburger handles it

    if (gesture === 'double-tap') {
      setupDoubleTap()
    } else if (gesture === 'long-press') {
      setupLongPress()
    } else if (gesture === 'swipe-up') {
      setupSwipeUp()
    }
  }

  function setupDoubleTap() {
    const header = options.headerRef.value
    if (!header) return
    const handler = (e: MouseEvent) => {
      if (e.detail === 2) {
        options.onActivate()
      }
    }
    header.addEventListener('click', handler)
    cleanupFns.push(() => header.removeEventListener('click', handler))
  }

  function setupLongPress() {
    const header = options.headerRef.value
    if (!header) return

    const startHandler = () => {
      longPressTimer = setTimeout(() => {
        options.onActivate()
      }, 2000)
    }
    const cancelHandler = () => {
      if (longPressTimer) {
        clearTimeout(longPressTimer)
        longPressTimer = null
      }
    }
    header.addEventListener('pointerdown', startHandler)
    header.addEventListener('pointerup', cancelHandler)
    header.addEventListener('pointercancel', cancelHandler)
    header.addEventListener('pointerleave', cancelHandler)
    cleanupFns.push(() => {
      header.removeEventListener('pointerdown', startHandler)
      header.removeEventListener('pointerup', cancelHandler)
      header.removeEventListener('pointercancel', cancelHandler)
      header.removeEventListener('pointerleave', cancelHandler)
    })
  }

  function setupSwipeUp() {
    let startY = 0
    const touchStart = (e: TouchEvent) => {
      const touch = e.touches[0]
      if (touch.clientY > window.innerHeight - CONST.SWIPE_ZONE_PX) {
        startY = touch.clientY
      } else {
        startY = 0
      }
    }
    const touchEnd = (e: TouchEvent) => {
      if (!startY) return
      const touch = e.changedTouches[0]
      const deltaY = startY - touch.clientY
      if (deltaY > CONST.SWIPE_DISTANCE_PX) {
        options.onActivate()
      }
      startY = 0
    }
    document.addEventListener('touchstart', touchStart, { passive: true })
    document.addEventListener('touchend', touchEnd, { passive: true })
    cleanupFns.push(() => {
      document.removeEventListener('touchstart', touchStart)
      document.removeEventListener('touchend', touchEnd)
    })
  }

  function cleanup() {
    cleanupFns.forEach(fn => fn())
    cleanupFns.length = 0
    if (longPressTimer) {
      clearTimeout(longPressTimer)
      longPressTimer = null
    }
  }

  onUnmounted(cleanup)

  return { setup, cleanup }
}
