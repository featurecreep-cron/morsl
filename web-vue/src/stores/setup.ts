import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  SetupStatus,
  ConnectionTestResult,
  ProfilePreset,
  ProfileEntry,
  ProfileRules,
  CategoryPreset,
  ProfileAssignment,
  RuleSummaryLine,
  TagItem,
  Category,
} from '@/types/api'

export type SubPage =
  | 'basics'
  | 'keywords'
  | 'ingredients'
  | 'books'
  | 'avoid'
  | 'rating'
  | 'freshness'
  | 'new-recipes'
  | 'review'

const RULE_PAGES: SubPage[] = [
  'basics',
  'keywords',
  'ingredients',
  'books',
  'avoid',
  'rating',
  'freshness',
  'new-recipes',
  'review',
]

function makeProfileEntry(
  name: string,
  icon: string,
  choices: number,
  isDefault: boolean,
): ProfileEntry {
  return {
    name,
    description: '',
    icon: icon || '',
    category: '',
    choices: choices || 5,
    min_choices: null,
    default: isDefault,
    rules: {
      tagsInclude: { active: false, theme: [], balance: [] },
      foodsInclude: { active: false, items: [], except: [], count: 1 },
      booksInclude: { active: false, items: [], count: choices || 5 },
      tagsExclude: { active: false, items: [] },
      foodsExclude: { active: false, items: [] },
      rating: { active: false, min: 4 },
      avoidRecent: { active: false, days: 14 },
      includeNew: { active: false, count: 1, days: 30 },
    },
  }
}

function buildConstraints(rules: ProfileRules, choices: number) {
  const constraints: Record<string, unknown>[] = []

  if (rules.tagsInclude.active) {
    if (rules.tagsInclude.theme.length) {
      constraints.push({
        type: 'keyword',
        items: rules.tagsInclude.theme.map((i) => ({ id: i.id, name: i.name })),
        operator: '>=',
        count: choices,
      })
    }
    for (const item of rules.tagsInclude.balance) {
      constraints.push({
        type: 'keyword',
        items: [{ id: item.id, name: item.name }],
        operator: '>=',
        count: item.count,
      })
    }
  }
  if (rules.foodsInclude.active && rules.foodsInclude.items.length) {
    const c: Record<string, unknown> = {
      type: 'food',
      items: rules.foodsInclude.items.map((i) => ({ id: i.id, name: i.name })),
      operator: '>=',
      count: rules.foodsInclude.count,
    }
    if (rules.foodsInclude.except.length) {
      c.except = rules.foodsInclude.except.map((i) => ({ id: i.id, name: i.name }))
    }
    constraints.push(c)
  }
  if (rules.booksInclude.active && rules.booksInclude.items.length) {
    constraints.push({
      type: 'book',
      items: rules.booksInclude.items.map((i) => ({ id: i.id, name: i.name })),
      operator: '>=',
      count: rules.booksInclude.count,
    })
  }
  if (rules.tagsExclude.active && rules.tagsExclude.items.length) {
    constraints.push({
      type: 'keyword',
      items: rules.tagsExclude.items.map((i) => ({ id: i.id, name: i.name })),
      operator: '==',
      count: 0,
    })
  }
  if (rules.foodsExclude.active && rules.foodsExclude.items.length) {
    constraints.push({
      type: 'food',
      items: rules.foodsExclude.items.map((i) => ({ id: i.id, name: i.name })),
      operator: '==',
      count: 0,
    })
  }
  if (rules.rating.active) {
    constraints.push({
      type: 'rating',
      min: rules.rating.min,
      operator: '>=',
      count: 1,
    })
  }
  if (rules.avoidRecent.active) {
    constraints.push({
      type: 'cookedon',
      within_days: rules.avoidRecent.days,
      operator: '==',
      count: 0,
    })
  }
  if (rules.includeNew.active) {
    constraints.push({
      type: 'createdon',
      within_days: rules.includeNew.days,
      operator: '>=',
      count: rules.includeNew.count,
    })
  }
  return constraints
}

export const useSetupStore = defineStore('setup', () => {
  // Navigation
  const step = ref(1)
  const profileSubPage = ref<SubPage>('basics')
  const profileIndex = ref(0)
  const addProfileMode = ref(false)

  // Step 1: Credentials
  const url = ref('')
  const token = ref('')
  const testing = ref(false)
  const testResult = ref<ConnectionTestResult | null>(null)
  const saving = ref(false)
  const error = ref('')

  // Step 2: Profile selection
  const presets = ref<ProfilePreset[]>([
    { key: 'breakfast', name: 'Breakfast', subtitle: 'Eggs, oats, and morning favorites', icon: 'breakfast', selected: false, choices: 3 },
    { key: 'lunch', name: 'Lunch', subtitle: 'Lighter dishes for midday', icon: 'lunch', selected: false, choices: 5 },
    { key: 'dinner', name: 'Dinner', subtitle: 'A full week of evening meals', icon: 'dinner', selected: false, choices: 5 },
    { key: 'weekday', name: 'Weekday Meals', subtitle: 'Everyday recipes for busy days', icon: 'lunchbox', selected: false, choices: 5 },
    { key: 'weekend', name: 'Weekend Meals', subtitle: 'More time to cook, more variety', icon: 'brunch', selected: false, choices: 3 },
    { key: 'weeknight', name: 'Weeknight Dinners', subtitle: 'Fast recipes when time is short', icon: 'timer', selected: false, choices: 5 },
  ])
  const customProfileName = ref('')
  const customProfiles = ref<Array<{ name: string; _id: number }>>([])

  // Step 3: Profile configuration
  const profileQueue = ref<ProfileEntry[]>([])
  const availableCategories = ref<Category[]>([])

  // Step 4: Categories
  const categoryPresets = ref<CategoryPreset[]>([
    { key: 'by-cuisine', display_name: 'By Cuisine', subtitle: 'Italian, Mexican, Asian...', icon: 'bowl', selected: true },
    { key: 'by-meal', display_name: 'By Meal', subtitle: 'Breakfast, Lunch, Dinner...', icon: 'dinner', selected: true },
  ])
  const customCategories = ref<Array<{ display_name: string; subtitle: string; _id: number }>>([])
  const customCatName = ref('')

  // Step 5: Assignments
  const createdCategories = ref<Category[]>([])
  const profileAssignments = ref<ProfileAssignment[]>([])

  // Setup status
  const setupStatus = ref<SetupStatus | null>(null)

  // Computed
  const currentProfile = computed(() => profileQueue.value[profileIndex.value] ?? null)
  const subPageIndex = computed(() => RULE_PAGES.indexOf(profileSubPage.value))
  const subPageCount = computed(() => RULE_PAGES.length)
  const rulePages = RULE_PAGES

  const hasProfileSelections = computed(
    () => presets.value.some((p) => p.selected) || customProfiles.value.length > 0,
  )

  const hasActiveConstraint = computed(() => {
    const r = currentProfile.value?.rules
    if (!r) return false
    return (
      r.tagsInclude.active ||
      r.tagsExclude.active ||
      r.foodsInclude.active ||
      r.foodsExclude.active ||
      r.booksInclude.active ||
      r.rating.active ||
      r.avoidRecent.active ||
      r.includeNew.active
    )
  })

  const balanceAssigned = computed(
    () => currentProfile.value?.rules.tagsInclude.balance.reduce((s, b) => s + b.count, 0) ?? 0,
  )

  const balanceComplete = computed(
    () => currentProfile.value != null && balanceAssigned.value >= currentProfile.value.choices,
  )

  const avoidDaysIsPreset = computed(() =>
    [7, 14, 21, 30].includes(currentProfile.value?.rules.avoidRecent.days ?? -1),
  )

  const ruleSummary = computed((): RuleSummaryLine[] => {
    if (!currentProfile.value) return []
    const r = currentProfile.value.rules
    const lines: RuleSummaryLine[] = []

    if (r.tagsInclude.active) {
      if (r.tagsInclude.theme.length) {
        const count = currentProfile.value.choices
        const names = r.tagsInclude.theme.map((i) => i.name).join(' or ')
        lines.push({
          text: `${names}: at least ${count} recipe${count !== 1 ? 's' : ''}`,
          page: 'keywords',
        })
      }
      for (const item of r.tagsInclude.balance) {
        lines.push({
          text: `${item.name}: at least ${item.count} recipe${item.count !== 1 ? 's' : ''}`,
          page: 'keywords',
        })
      }
    }
    if (r.foodsInclude.active && r.foodsInclude.items.length) {
      let text = `Ingredients: ${r.foodsInclude.items.map((i) => i.name).join(', ')} (at least ${r.foodsInclude.count})`
      if (r.foodsInclude.except.length) {
        text += `, except ${r.foodsInclude.except.map((i) => i.name).join(', ')}`
      }
      lines.push({ text, page: 'ingredients' })
    }
    if (r.booksInclude.active && r.booksInclude.items.length) {
      const names = r.booksInclude.items.map((i) => i.name).join(', ')
      lines.push({ text: `Books: ${names} (at least ${r.booksInclude.count})`, page: 'books' })
    }
    if (r.tagsExclude.active && r.tagsExclude.items.length) {
      for (const item of r.tagsExclude.items) {
        lines.push({ text: `Avoids: ${item.name} keyword`, page: 'avoid' })
      }
    }
    if (r.foodsExclude.active && r.foodsExclude.items.length) {
      for (const item of r.foodsExclude.items) {
        lines.push({ text: `Avoids: ${item.name} ingredient`, page: 'avoid' })
      }
    }
    if (r.rating.active) {
      lines.push({ text: `Minimum rating: ${r.rating.min} stars`, page: 'rating' })
    }
    if (r.avoidRecent.active) {
      lines.push({
        text: `Skips recipes cooked in last ${r.avoidRecent.days} days`,
        page: 'freshness',
      })
    }
    if (r.includeNew.active) {
      lines.push({
        text: `Includes ${r.includeNew.count}+ recipes added in last ${r.includeNew.days} days`,
        page: 'new-recipes',
      })
    }
    return lines
  })

  // --- Actions ---

  async function init() {
    const params = new URLSearchParams(window.location.search)
    addProfileMode.value = params.get('mode') === 'add-profile'

    // Load theme
    try {
      const themeRes = await fetch('/api/settings')
      if (themeRes.ok) {
        const s = await themeRes.json()
        if (s.theme) {
          const link = document.getElementById('theme-css') as HTMLLinkElement | null
          if (link) link.href = `/css/theme-${s.theme}.css`
        }
      }
    } catch {
      /* use default */
    }

    try {
      const res = await fetch('/api/settings/setup-status')
      if (res.ok) {
        setupStatus.value = await res.json()
        if (addProfileMode.value && setupStatus.value!.has_credentials) {
          profileQueue.value = [makeProfileEntry('', '', 5, false)]
          profileIndex.value = 0
          profileSubPage.value = 'basics'
          await loadCategories()
          step.value = 3
        } else if (setupStatus.value!.has_credentials) {
          if (setupStatus.value!.has_profiles) {
            step.value = setupStatus.value!.has_categories ? 6 : 4
          } else {
            step.value = 2
          }
        }
      }
    } catch {
      /* start at step 1 */
    }
  }

  // Step 1
  async function testConnection() {
    if (!url.value || !token.value) return
    testing.value = true
    testResult.value = null
    error.value = ''
    try {
      const res = await fetch('/api/settings/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.value, token: token.value }),
      })
      testResult.value = res.ok
        ? await res.json()
        : { success: false, error: 'Server error' }
    } catch {
      testResult.value = { success: false, error: 'Cannot reach server' }
    } finally {
      testing.value = false
    }
  }

  async function saveCredentials() {
    if (!testResult.value?.success) return
    saving.value = true
    error.value = ''
    try {
      const res = await fetch('/api/settings/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.value, token: token.value }),
      })
      if (res.ok) {
        const statusRes = await fetch('/api/settings/setup-status')
        if (statusRes.ok) setupStatus.value = await statusRes.json()
        step.value = 2
      } else {
        error.value = 'Failed to save credentials.'
      }
    } catch {
      error.value = 'Failed to save credentials. Please try again.'
    } finally {
      saving.value = false
    }
  }

  // Step 2
  function togglePreset(preset: ProfilePreset) {
    preset.selected = !preset.selected
  }

  function addCustomProfile() {
    const name = customProfileName.value.trim()
    if (!name) return
    if (customProfiles.value.some((p) => p.name.toLowerCase() === name.toLowerCase())) return
    customProfiles.value.push({ name, _id: Date.now() + Math.random() })
    customProfileName.value = ''
  }

  function removeCustomProfile(idx: number) {
    customProfiles.value.splice(idx, 1)
  }

  function buildProfileQueue() {
    const queue: ProfileEntry[] = []
    let first = true
    for (const p of presets.value) {
      if (!p.selected) continue
      queue.push(makeProfileEntry(p.name, p.icon, p.choices, first))
      first = false
    }
    for (const c of customProfiles.value) {
      queue.push(makeProfileEntry(c.name, '', 5, first))
      first = false
    }
    profileQueue.value = queue
    if (queue.length === 0) {
      step.value = 4
    } else {
      profileIndex.value = 0
      profileSubPage.value = 'basics'
      step.value = 3
    }
  }

  // Step 3: Sub-page navigation
  function nextSubPage() {
    const idx = subPageIndex.value
    if (idx < RULE_PAGES.length - 1) {
      profileSubPage.value = RULE_PAGES[idx + 1]
    }
  }

  function prevSubPage() {
    const idx = subPageIndex.value
    if (idx > 0) {
      profileSubPage.value = RULE_PAGES[idx - 1]
    } else if (profileIndex.value > 0) {
      profileIndex.value--
      profileSubPage.value = 'review'
    } else if (addProfileMode.value) {
      window.location.href = '/admin'
    } else {
      step.value = 2
    }
  }

  function goToSubPage(page: string) {
    profileSubPage.value = page as SubPage
  }

  // Step 3: Profile CRUD
  function advanceProfile() {
    if (profileIndex.value < profileQueue.value.length - 1) {
      profileIndex.value++
      profileSubPage.value = 'basics'
      error.value = ''
    } else if (addProfileMode.value) {
      window.location.href = '/admin'
    } else {
      step.value = 4
      error.value = ''
    }
  }

  async function createCurrentProfile() {
    const p = currentProfile.value
    if (!p) return
    saving.value = true
    error.value = ''
    try {
      const body: Record<string, unknown> = {
        name: p.name.trim(),
        description: p.description,
        icon: p.icon,
        choices: p.choices,
        default: p.default,
        constraints: buildConstraints(p.rules, p.choices),
      }
      if (p.min_choices) body.min_choices = p.min_choices
      const res = await fetch('/api/profiles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (res.ok || res.status === 409) {
        if (p.category) {
          await fetch(`/api/profiles/${encodeURIComponent(p.name.trim())}/category`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category: p.category }),
          })
        }
        advanceProfile()
      } else {
        const err = await res.json().catch(() => ({}))
        error.value = (err as { detail?: string }).detail || 'Failed to create profile.'
      }
    } catch {
      error.value = 'Failed to create profile. Please try again.'
    } finally {
      saving.value = false
    }
  }

  function skipProfile() {
    advanceProfile()
  }

  // Choices helpers
  function incrementChoices() {
    if (currentProfile.value && currentProfile.value.choices < 50) {
      currentProfile.value.choices++
    }
  }

  function decrementChoices() {
    const min = currentProfile.value?.min_choices || 1
    if (currentProfile.value && currentProfile.value.choices > min) {
      currentProfile.value.choices--
    }
  }

  function incrementMin() {
    if (!currentProfile.value) return
    const cur = currentProfile.value.min_choices || currentProfile.value.choices
    if (cur < currentProfile.value.choices) {
      currentProfile.value.min_choices = cur + 1
    }
  }

  function decrementMin() {
    if (!currentProfile.value) return
    const cur = currentProfile.value.min_choices || currentProfile.value.choices
    if (cur > 1) {
      currentProfile.value.min_choices = cur - 1
    }
  }

  // Tags/Foods/Books helpers
  function addThemeKeyword(kw: TagItem) {
    currentProfile.value?.rules.tagsInclude.theme.push({ id: kw.id, name: kw.name })
  }

  function removeThemeKeyword(idx: number) {
    currentProfile.value?.rules.tagsInclude.theme.splice(idx, 1)
  }

  function addBalanceKeyword(kw: TagItem) {
    currentProfile.value?.rules.tagsInclude.balance.push({ id: kw.id, name: kw.name, count: 1 })
  }

  function removeBalanceKeyword(idx: number) {
    currentProfile.value?.rules.tagsInclude.balance.splice(idx, 1)
  }

  function addIncludeFood(food: TagItem) {
    currentProfile.value?.rules.foodsInclude.items.push({ id: food.id, name: food.name })
  }

  function removeIncludeFood(idx: number) {
    currentProfile.value?.rules.foodsInclude.items.splice(idx, 1)
  }

  function addFoodException(food: TagItem) {
    currentProfile.value?.rules.foodsInclude.except.push({ id: food.id, name: food.name })
  }

  function removeFoodException(idx: number) {
    currentProfile.value?.rules.foodsInclude.except.splice(idx, 1)
  }

  function addBook(book: TagItem) {
    currentProfile.value?.rules.booksInclude.items.push({ id: book.id, name: book.name })
  }

  function removeBook(idx: number) {
    currentProfile.value?.rules.booksInclude.items.splice(idx, 1)
  }

  function addExcludeKeyword(kw: TagItem) {
    currentProfile.value?.rules.tagsExclude.items.push({ id: kw.id, name: kw.name })
  }

  function removeExcludeKeyword(idx: number) {
    currentProfile.value?.rules.tagsExclude.items.splice(idx, 1)
  }

  function addExcludeFood(food: TagItem) {
    currentProfile.value?.rules.foodsExclude.items.push({ id: food.id, name: food.name })
  }

  function removeExcludeFood(idx: number) {
    currentProfile.value?.rules.foodsExclude.items.splice(idx, 1)
  }

  function setRating(stars: number) {
    if (currentProfile.value) {
      currentProfile.value.rules.rating.min = stars
    }
  }

  function setAvoidDays(days: number) {
    if (currentProfile.value) {
      currentProfile.value.rules.avoidRecent.days = days
    }
  }

  function keywordExclusionSet(): Set<number> {
    const tags = currentProfile.value?.rules.tagsInclude
    if (!tags) return new Set()
    return new Set([...tags.theme.map((i) => i.id), ...tags.balance.map((i) => i.id)])
  }

  // Step 4: Categories
  function toggleCategory(preset: CategoryPreset) {
    preset.selected = !preset.selected
  }

  function addCustomCategory() {
    const name = customCatName.value.trim()
    if (!name) return
    customCategories.value.push({ display_name: name, subtitle: '', _id: Date.now() + Math.random() })
    customCatName.value = ''
  }

  function removeCustomCategory(idx: number) {
    customCategories.value.splice(idx, 1)
  }

  async function createCategories() {
    const toCreate: Array<{ display_name: string; subtitle: string; icon: string }> = []
    for (const preset of categoryPresets.value) {
      if (preset.selected && preset.display_name?.trim()) {
        toCreate.push({
          display_name: preset.display_name.trim(),
          subtitle: preset.subtitle?.trim() || '',
          icon: preset.icon || '',
        })
      }
    }
    for (const custom of customCategories.value) {
      if (custom.display_name?.trim()) {
        toCreate.push({
          display_name: custom.display_name.trim(),
          subtitle: custom.subtitle?.trim() || '',
          icon: '',
        })
      }
    }
    if (toCreate.length === 0) {
      step.value = 6
      return
    }
    saving.value = true
    error.value = ''
    try {
      for (const cat of toCreate) {
        const res = await fetch('/api/categories', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(cat),
        })
        if (!res.ok && res.status !== 409) {
          const err = await res.json().catch(() => ({}))
          throw new Error((err as { detail?: string }).detail || res.statusText)
        }
      }
      await loadAssignmentData()
      step.value = 5
    } catch (e) {
      error.value = 'Failed to create categories: ' + (e instanceof Error ? e.message : String(e))
    } finally {
      saving.value = false
    }
  }

  // Step 5: Assignments
  async function loadAssignmentData() {
    try {
      const [catRes, profRes] = await Promise.all([
        fetch('/api/categories'),
        fetch('/api/profiles'),
      ])
      if (catRes.ok) createdCategories.value = await catRes.json()
      if (profRes.ok) {
        const profiles = await profRes.json()
        profileAssignments.value = profiles.map((p: { name: string; category?: string }) => ({
          name: p.name,
          category: p.category || '',
        }))
      }
    } catch {
      /* best effort */
    }
  }

  async function saveAssignments() {
    saving.value = true
    error.value = ''
    try {
      for (const pa of profileAssignments.value) {
        if (!pa.category) continue
        await fetch(`/api/profiles/${encodeURIComponent(pa.name)}/category`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ category: pa.category }),
        })
      }
      step.value = 6
    } catch (e) {
      error.value = 'Failed to save assignments: ' + (e instanceof Error ? e.message : String(e))
    } finally {
      saving.value = false
    }
  }

  async function loadCategories() {
    try {
      const res = await fetch('/api/categories')
      if (res.ok) availableCategories.value = await res.json()
    } catch {
      /* best effort */
    }
  }

  // Step 6: Finish
  function generateAndFinish() {
    const firstProfile = profileQueue.value[0]?.name || 'default'
    window.location.href = `/?generate=${encodeURIComponent(firstProfile)}`
  }

  function finishSetup() {
    window.location.href = '/'
  }

  return {
    // State
    step,
    profileSubPage,
    profileIndex,
    addProfileMode,
    url,
    token,
    testing,
    testResult,
    saving,
    error,
    presets,
    customProfileName,
    customProfiles,
    profileQueue,
    availableCategories,
    categoryPresets,
    customCategories,
    customCatName,
    createdCategories,
    profileAssignments,
    setupStatus,

    // Computed
    currentProfile,
    subPageIndex,
    subPageCount,
    rulePages,
    hasProfileSelections,
    hasActiveConstraint,
    balanceAssigned,
    balanceComplete,
    avoidDaysIsPreset,
    ruleSummary,

    // Actions
    init,
    testConnection,
    saveCredentials,
    togglePreset,
    addCustomProfile,
    removeCustomProfile,
    buildProfileQueue,
    nextSubPage,
    prevSubPage,
    goToSubPage,
    createCurrentProfile,
    skipProfile,
    advanceProfile,
    incrementChoices,
    decrementChoices,
    incrementMin,
    decrementMin,
    addThemeKeyword,
    removeThemeKeyword,
    addBalanceKeyword,
    removeBalanceKeyword,
    addIncludeFood,
    removeIncludeFood,
    addFoodException,
    removeFoodException,
    addBook,
    removeBook,
    addExcludeKeyword,
    removeExcludeKeyword,
    addExcludeFood,
    removeExcludeFood,
    setRating,
    setAvoidDays,
    keywordExclusionSet,
    toggleCategory,
    addCustomCategory,
    removeCustomCategory,
    createCategories,
    saveAssignments,
    generateAndFinish,
    finishSetup,
  }
})
