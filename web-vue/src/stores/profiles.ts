import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ProfileSummary, Category } from '@/types/api'

export const useProfilesStore = defineStore('profiles', () => {
  const profiles = ref<ProfileSummary[]>([])
  const categories = ref<Category[]>([])
  const loading = ref(false)

  const visibleProfiles = computed(
    () => profiles.value.filter(p => p.show_on_menu !== false),
  )

  const defaultProfile = computed(
    () => profiles.value.find(p => p.is_default || p.default) ?? profiles.value[0] ?? null,
  )

  const hasProfiles = computed(() => profiles.value.length > 0)

  const displayCategories = computed(() => {
    if (categories.value.length > 0) return categories.value
    if (profiles.value.length === 0) return []
    return [{ id: '_all', display_name: '', subtitle: '', icon: '' }] as Category[]
  })

  const categorizedProfiles = computed(() => {
    const result: Record<string | number, ProfileSummary[]> = {}
    const categoryIds = new Set<string | number>()
    const visible = visibleProfiles.value

    for (const cat of displayCategories.value) {
      if (cat.id === '_all') {
        result['_all'] = visible
      } else {
        categoryIds.add(cat.id)
        result[cat.id] = visible.filter(p => p.category === cat.id)
      }
    }

    // Profiles not assigned to any defined category
    if (categoryIds.size > 0) {
      const uncategorized = visible.filter(
        p => !p.category || !categoryIds.has(p.category),
      )
      if (uncategorized.length > 0) {
        result['_uncategorized'] = uncategorized
      }
    }

    return result
  })

  async function load() {
    loading.value = true
    try {
      const res = await fetch('/api/profiles')
      if (res.ok) {
        profiles.value = await res.json()
      }
    } catch (e) {
      console.warn('Failed to load profiles:', e)
    } finally {
      loading.value = false
    }
  }

  async function loadCategories() {
    try {
      const res = await fetch('/api/categories')
      if (res.ok) {
        categories.value = await res.json()
      }
    } catch (e) {
      console.warn('Failed to load categories:', e)
    }
  }

  function resolveNoun(profileName: string, globalNoun: string): string {
    const p = profiles.value.find(x => x.name === profileName)
    return (p?.item_noun) || globalNoun || 'recipe'
  }

  return {
    profiles,
    categories,
    loading,
    visibleProfiles,
    defaultProfile,
    hasProfiles,
    displayCategories,
    categorizedProfiles,
    load,
    loadCategories,
    resolveNoun,
  }
})
