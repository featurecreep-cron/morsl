import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSettingsStore } from '@/stores/settings'
import type { AppSettings } from '@/types/api'

describe('useSettingsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('has correct defaults before loading', () => {
    const store = useSettingsStore()
    expect(store.loaded).toBe(false)
    expect(store.theme).toBe('cast-iron')
    expect(store.appName).toBe('Morsl')
    expect(store.itemNoun).toBe('recipe')
    expect(store.kioskEnabled).toBe(false)
    expect(store.showRatings).toBe(true)
    expect(store.ratingsEnabled).toBe(true)
    expect(store.ordersEnabled).toBe(true)
    expect(store.toastSeconds).toBe(2)
    expect(store.showNewBadge).toBe(true)
    expect(store.qrShowOnMenu).toBe(false)
  })

  it('patch updates settings', () => {
    const store = useSettingsStore()
    store.settings = {
      app_name: 'Morsl',
      theme: 'cast-iron',
      kiosk_enabled: false,
    } as AppSettings

    store.patch({ app_name: 'My Menu', theme: 'honey' })
    expect(store.appName).toBe('My Menu')
    expect(store.theme).toBe('honey')
  })

  it('loadingIconUrl uses logo when loading_icon_use_logo is set', () => {
    const store = useSettingsStore()
    store.settings = {
      loading_icon_use_logo: true,
      logo_url: '/uploads/logo.svg',
      loading_icon_url: '/icons/spinner.svg',
    } as AppSettings

    expect(store.loadingIconUrl).toBe('/uploads/logo.svg')
  })

  it('loadingIconUrl falls back to loading_icon_url', () => {
    const store = useSettingsStore()
    store.settings = {
      loading_icon_use_logo: false,
      logo_url: '/uploads/logo.svg',
      loading_icon_url: '/icons/spinner.svg',
    } as AppSettings

    expect(store.loadingIconUrl).toBe('/icons/spinner.svg')
  })

  it('loadingIconUrl falls back to default favicon', () => {
    const store = useSettingsStore()
    store.settings = {
      loading_icon_use_logo: false,
    } as AppSettings

    expect(store.loadingIconUrl).toBe('/icons/default-favicon.svg')
  })

  it('logoUrl respects showLogo setting', () => {
    const store = useSettingsStore()
    store.settings = {
      show_logo: false,
      logo_url: '/uploads/logo.svg',
    } as AppSettings

    expect(store.logoUrl).toBe('')

    store.patch({ show_logo: true })
    expect(store.logoUrl).toBe('/uploads/logo.svg')
  })

  it('maxPreviousRecipes uses default when not set', () => {
    const store = useSettingsStore()
    expect(store.maxPreviousRecipes).toBe(50)

    store.settings = { max_previous_recipes: 25 } as AppSettings
    expect(store.maxPreviousRecipes).toBe(25)
  })
})
