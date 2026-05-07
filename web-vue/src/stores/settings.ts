import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AppSettings } from '@/types/api'
import { CONST } from '@/constants'

const DEFAULT_FAVICON_PATH = '/icons/default-favicon.svg'

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref<AppSettings | null>(null)
  const loading = ref(false)
  const loaded = ref(false)

  // Computed accessors
  const theme = computed(() => settings.value?.theme ?? 'cast-iron')
  const appName = computed(() => settings.value?.app_name ?? 'Morsl')
  const kioskEnabled = computed(() => settings.value?.kiosk_enabled ?? false)
  const kioskGesture = computed(() => settings.value?.kiosk_gesture ?? 'menu')
  const kioskPinEnabled = computed(() => settings.value?.kiosk_pin_enabled ?? false)
  const adminPinEnabled = computed(() => settings.value?.admin_pin_enabled ?? false)
  const hasPin = computed(() => settings.value?.has_pin ?? false)
  const itemNoun = computed(() => settings.value?.item_noun ?? 'recipe')
  const showRatings = computed(() => settings.value?.show_ratings ?? true)
  const ratingsEnabled = computed(() => settings.value?.ratings_enabled ?? true)
  const ordersEnabled = computed(() => settings.value?.orders_enabled ?? true)
  const saveRatingsToTandoor = computed(() => settings.value?.save_ratings_to_tandoor ?? true)
  const showNewBadge = computed(() => settings.value?.show_new_badge ?? true)
  const toastSeconds = computed(() => settings.value?.toast_seconds ?? CONST.DEFAULT_TOAST_SECONDS)
  const showLogo = computed(() => settings.value?.show_logo !== false)
  const logoUrl = computed(() => showLogo.value ? (settings.value?.logo_url ?? '') : '')
  const sloganHeader = computed(() => settings.value?.slogan_header ?? '')
  const sloganFooter = computed(() => settings.value?.slogan_footer ?? '')
  const maxPreviousRecipes = computed(() => settings.value?.max_previous_recipes ?? CONST.DEFAULT_MAX_PREVIOUS_RECIPES)
  const qrShowOnMenu = computed(() => settings.value?.qr_show_on_menu ?? false)
  const qrWifiString = computed(() => settings.value?.qr_wifi_string ?? '')
  const qrMenuUrl = computed(() => settings.value?.qr_menu_url ?? '')

  const loadingIconUrl = computed(() => {
    if (settings.value?.loading_icon_use_logo && settings.value?.logo_url) {
      return settings.value.logo_url
    }
    return settings.value?.loading_icon_url || DEFAULT_FAVICON_PATH
  })

  async function load() {
    loading.value = true
    try {
      const res = await fetch('/api/settings/public')
      if (res.ok) {
        settings.value = await res.json()
        loaded.value = true
        document.title = settings.value?.app_name || 'Morsl'
        _updateFaviconLinks()
      }
    } catch (e) {
      console.warn('Failed to load settings:', e)
    } finally {
      loading.value = false
    }
  }

  function _updateFaviconLinks() {
    const url = (settings.value?.favicon_use_logo && settings.value?.logo_url)
      ? settings.value.logo_url
      : settings.value?.favicon_url
    if (!url) return
    document.querySelectorAll('link[rel="icon"]').forEach(link => {
      ;(link as HTMLLinkElement).href = url as string
    })
  }

  function patch(updates: Partial<AppSettings>) {
    if (settings.value) {
      Object.assign(settings.value, updates)
    }
  }

  return {
    settings,
    loading,
    loaded,
    theme,
    appName,
    kioskEnabled,
    kioskGesture,
    kioskPinEnabled,
    adminPinEnabled,
    hasPin,
    itemNoun,
    showRatings,
    ratingsEnabled,
    ordersEnabled,
    saveRatingsToTandoor,
    showNewBadge,
    toastSeconds,
    showLogo,
    logoUrl,
    sloganHeader,
    sloganFooter,
    maxPreviousRecipes,
    loadingIconUrl,
    qrShowOnMenu,
    qrWifiString,
    qrMenuUrl,
    load,
    patch,
  }
})
