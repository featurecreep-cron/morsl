import { watch } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { THEME_REGISTRY, type ThemeEntry } from '@/theme-registry'

/**
 * Apply the current theme from settings store.
 * Loads the theme CSS file and updates meta tags.
 */
export function useTheme() {
  const settings = useSettingsStore()

  function apply(name: string) {
    const theme: ThemeEntry = THEME_REGISTRY[name] ?? THEME_REGISTRY['cast-iron']
    const safeName = THEME_REGISTRY[name] ? name : 'cast-iron'

    // Swap CSS file
    const link = document.getElementById('theme-css') as HTMLLinkElement | null
    if (link) {
      link.href = `/css/theme-${safeName}.css`
    }

    // Update body data attribute
    document.body.dataset.theme = safeName

    // Update theme-color meta
    const meta = document.querySelector('meta[name="theme-color"]')
    if (meta) {
      meta.setAttribute('content', theme.accentColor)
    }

    // Persist to localStorage
    try {
      localStorage.setItem('morsl-theme', safeName)
    } catch {
      // Private browsing
    }
  }

  // Apply theme whenever settings change
  watch(() => settings.theme, apply, { immediate: true })

  return { apply, THEME_REGISTRY }
}
