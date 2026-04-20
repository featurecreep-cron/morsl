import { describe, it, expect } from 'vitest'
import { CONST } from '@/constants'

describe('CONST', () => {
  it('has expected timer values', () => {
    expect(CONST.STATUS_POLL_MS).toBe(2000)
    expect(CONST.SSE_INITIAL_RETRY_MS).toBe(1000)
    expect(CONST.SSE_MAX_RETRY_MS).toBe(30000)
  })

  it('has search debounce values', () => {
    expect(CONST.KEYWORD_DEBOUNCE_MS).toBe(150)
    expect(CONST.FOOD_DEBOUNCE_MS).toBe(300)
    expect(CONST.BOOK_DEBOUNCE_MS).toBe(300)
  })

  it('has localStorage keys', () => {
    expect(CONST.LS_MENU_SHELVES).toBe('menu-shelves')
    expect(CONST.LS_ACTIVE_DECK).toBe('menu-active-deck')
    expect(CONST.LS_RECENT_NAMES).toBe('recentNames')
  })

  it('has layout constants', () => {
    expect(CONST.MAX_SHELF_GENERATIONS).toBe(5)
    expect(CONST.MAX_RECENT_NAMES).toBe(10)
    expect(CONST.CAROUSEL_GAP_PX).toBe(16)
  })

  it('has default values for settings-backed constants', () => {
    expect(CONST.DEFAULT_MENU_POLL_SECONDS).toBe(60)
    expect(CONST.DEFAULT_TOAST_SECONDS).toBe(2)
    expect(CONST.DEFAULT_MAX_DISCOVER_GENS).toBe(10)
    expect(CONST.DEFAULT_MAX_PREVIOUS_RECIPES).toBe(50)
  })
})
