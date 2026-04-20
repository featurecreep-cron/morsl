import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { CONST } from '@/constants'
import { THEME_REGISTRY } from '@/theme-registry'
import type {
  AdminConstraint,
  AdminConstraintType,
  AdminProfileSummary,
  AnalyticsData,
  AppSettings,
  Category,
  ConfirmModalState,
  ConstraintOperator,
  ConstraintTypeInfo,
  CustomFilter,
  GenerationStatus,
  HistoryEntry,
  IconMappings,
  MealType,
  Order,
  OrderCount,
  ProfileEditorState,
  Recipe,
  RecipeDetail,
  RelaxedConstraint,
  Schedule,
  ScheduleForm,
  Template,
  TemplateEditorState,
  WeeklyPlanDay,
  WeeklyStatus,
} from '@/types/api'

// ---------------------------------------------------------------------------
// Types local to this store
// ---------------------------------------------------------------------------

interface MenuMeta {
  generated_at?: string
  requested_count?: number
  constraint_count?: number
  status?: string
}

interface SelectedConstraintItem {
  id: number
  name: string
  count: number
  operator: ConstraintOperator
}

interface WeeklyRegenSlot {
  date: string
  mealTypeId: number
}

interface CategoryForm {
  display_name: string
  subtitle: string
  icon: string
}

interface CredTestResult {
  success: boolean
  error?: string
}

type AdminTier = 'essential' | 'standard' | 'advanced'

// ---------------------------------------------------------------------------
// Static data
// ---------------------------------------------------------------------------

const TIER_LEVELS: Record<AdminTier, number> = {
  essential: 0,
  standard: 1,
  advanced: 2,
}

const TAB_TIERS: Record<string, AdminTier> = {
  generate: 'essential',
  profiles: 'essential',
  weekly: 'essential',
  settings: 'essential',
  orders: 'advanced',
  branding: 'advanced',
}

const OPERATOR_LABELS: Record<ConstraintOperator, string> = {
  '>=': 'At least',
  '<=': 'At most',
  '==': 'Exactly',
}

const CONSTRAINT_TYPE_ORDER = ['keyword', 'food', 'book', 'rating', 'cookedon', 'createdon', 'makenow']

export const SCHEDULE_DAYS = [
  { key: 'mon', label: 'Mon' },
  { key: 'tue', label: 'Tue' },
  { key: 'wed', label: 'Wed' },
  { key: 'thu', label: 'Thu' },
  { key: 'fri', label: 'Fri' },
  { key: 'sat', label: 'Sat' },
  { key: 'sun', label: 'Sun' },
] as const

/** Constraint type metadata for the UI. Icons are text placeholders — components render real SVGs. */
export const CONSTRAINT_TYPES: Record<AdminConstraintType, ConstraintTypeInfo> = {
  keyword: {
    label: 'Keyword',
    icon: 'tag',
    description: 'Require recipes with specific tags like "Italian", "Quick", or "Vegetarian"',
    help: 'Keywords are tags assigned to recipes in Tandoor. Use this to filter by cuisine, meal type, or any custom tags you\'ve created.',
  },
  food: {
    label: 'Ingredient',
    icon: 'food',
    description: 'Require recipes containing specific ingredients like bourbon or lime juice',
    help: 'Filter recipes by their ingredients. Great for using up specific bottles or avoiding ingredients you don\'t have.',
  },
  book: {
    label: 'Book',
    icon: 'book',
    description: 'Require recipes from specific recipe books or collections',
    help: 'If your recipes are organized into books in Tandoor, use this to pull from specific collections.',
  },
  rating: {
    label: 'Rating',
    icon: 'star',
    description: 'Require recipes with a minimum star rating',
    help: 'Filter by how you\'ve rated recipes. Great for ensuring quality picks or finding underrated gems to try again.',
  },
  cookedon: {
    label: 'Last Made',
    icon: 'calendar',
    description: 'Filter by when you last made a recipe',
    help: 'Avoid recipes you\'ve had recently, or specifically include recent favorites. Based on Tandoor\'s meal plan history.',
  },
  createdon: {
    label: 'Date Added',
    icon: 'clock',
    description: 'Filter by when recipes were added to your collection',
    help: 'Find new additions you haven\'t tried yet, or stick to tried-and-true classics.',
  },
  makenow: {
    label: 'Make Now',
    icon: 'check',
    description: 'Prefer recipes you can make with ingredients on hand',
    help: 'Uses Tandoor\'s on-hand tracking. Mark ingredients as "on hand" in Tandoor, then use this to prefer recipes you can make right now.',
  },
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useAdminStore = defineStore('admin', () => {
  // ========================================================================
  // 1. Navigation & UI
  // ========================================================================

  const activeTab = ref('generate')
  const adminTier = ref<AdminTier>(
    (localStorage.getItem(CONST.LS_ADMIN_TIER) as AdminTier) || 'essential',
  )
  const navOpen = ref(false)
  const adminReady = ref(false)
  const appVersion = ref('')

  const confirmModal = ref<ConfirmModalState>({
    show: false,
    title: '',
    message: '',
    confirmText: '',
    onConfirm: () => {},
  })

  // Reload toast
  const reloadToastMsg = ref('')
  const reloadToastShow = ref(false)

  function reloadPrompt(message: string) {
    reloadToastMsg.value = message
    reloadToastShow.value = true
  }

  function dismissReloadPrompt() {
    reloadToastShow.value = false
  }

  // Error toast
  const errorMsg = ref('')
  const errorShow = ref(false)

  function showError(msg: string) {
    errorMsg.value = msg
    errorShow.value = true
  }

  function dismissError() {
    errorShow.value = false
  }

  // ========================================================================
  // 2. PIN Gate
  // ========================================================================

  const showPinGate = ref(false)
  const pinInput = ref('')
  const pinError = ref('')
  const showPinText = ref(false)

  function _isPinRequired(s: Partial<AppSettings>): boolean {
    const featureOn = s.admin_pin_enabled || (s.kiosk_enabled && s.kiosk_pin_enabled)
    return !!(featureOn && s.has_pin)
  }

  async function submitPin() {
    pinError.value = ''
    try {
      const res = await fetch('/api/settings/verify-pin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin: pinInput.value }),
      })
      if (res.ok) {
        const data = await res.json()
        if (data.valid) {
          if (data.token) {
            sessionStorage.setItem(CONST.SS_ADMIN_TOKEN, data.token)
            sessionStorage.setItem(CONST.SS_ADMIN_TOKEN_TS, String(Date.now()))
          }
          showPinGate.value = false
          pinInput.value = ''
          await _loadAdminData()
        } else {
          pinError.value = 'Incorrect PIN'
          pinInput.value = ''
        }
      } else {
        pinError.value = 'Failed to verify PIN'
      }
    } catch {
      pinError.value = 'Cannot reach server'
    }
  }

  // ========================================================================
  // 3. Auth — adminFetch
  // ========================================================================

  let _adminAbort: AbortController | null = null

  interface AdminFetchOptions extends RequestInit {
    _skipAbort?: boolean
    _silent?: boolean
  }

  async function adminFetch(url: string, opts: AdminFetchOptions = {}): Promise<Response> {
    const token = sessionStorage.getItem(CONST.SS_ADMIN_TOKEN)
    const headers = new Headers(opts.headers as HeadersInit | undefined)
    if (token) {
      headers.set('X-Admin-Token', token)
    }
    const init: RequestInit = {
      ...opts,
      headers,
    }
    if (!opts._skipAbort && _adminAbort) {
      init.signal = _adminAbort.signal
    }
    // Remove custom keys before passing to fetch
    delete (init as AdminFetchOptions)._skipAbort
    delete (init as AdminFetchOptions)._silent

    const res = await fetch(url, init)

    if (res.status === 401 && !opts._silent) {
      if (!showPinGate.value) {
        sessionStorage.removeItem(CONST.SS_ADMIN_TOKEN)
        adminReady.value = false
        showPinGate.value = true
        if (_adminAbort) _adminAbort.abort()
      }
    }

    return res
  }

  // ========================================================================
  // 4. Init & Lifecycle
  // ========================================================================

  async function init() {
    applyTheme(currentTheme.value)

    // Fetch version (no auth required)
    try {
      const h = await fetch('/health')
      if (h.ok) appVersion.value = (await h.json()).version || ''
    } catch {
      /* ignore */
    }

    // Check if PIN is required before loading admin data
    if (await _checkPinGate()) return

    await _loadAdminData()
  }

  async function _checkPinGate(): Promise<boolean> {
    try {
      const pubRes = await fetch('/api/settings/public')
      if (pubRes.ok) {
        const pub = await pubRes.json()
        if (!_isPinRequired(pub)) return false

        const token = sessionStorage.getItem(CONST.SS_ADMIN_TOKEN)
        const tokenTs = parseInt(sessionStorage.getItem(CONST.SS_ADMIN_TOKEN_TS) || '0', 10)
        const pinTimeout = pub.pin_timeout ?? 0

        let needsPin = !token
        if (token && pinTimeout === 0) {
          sessionStorage.removeItem(CONST.SS_ADMIN_TOKEN)
          sessionStorage.removeItem(CONST.SS_ADMIN_TOKEN_TS)
          needsPin = true
        } else if (token && pinTimeout > 0 && tokenTs) {
          if (Date.now() - tokenTs > pinTimeout * 1000) {
            sessionStorage.removeItem(CONST.SS_ADMIN_TOKEN)
            sessionStorage.removeItem(CONST.SS_ADMIN_TOKEN_TS)
            needsPin = true
          }
        }

        if (needsPin) {
          showPinGate.value = true
          return true
        }
      }
    } catch {
      /* proceed without gate */
    }
    return false
  }

  async function _loadAdminData() {
    _adminAbort = new AbortController()
    try {
      await Promise.all([
        loadProfiles(),
        loadTemplates(),
        loadStatus(),
        loadMenu(),
        loadKeywords(),
        loadOrders(),
        loadSchedules(),
        loadCategories(),
        loadSettings(),
        loadMealTypes(),
        loadHistory(),
        loadAnalytics(),
        loadIconMappings(),
        loadCustomFilters(),
      ])
      adminReady.value = true

      // Hash-based tab activation
      const hash = window.location.hash.replace('#', '')
      if (hash && TAB_TIERS[hash] && tierVisible(TAB_TIERS[hash])) {
        activeTab.value = hash
      }
    } catch (e: unknown) {
      if (e instanceof DOMException && e.name === 'AbortError') return
      throw e
    } finally {
      _adminAbort = null
    }

    const dflt = profiles.value.find(p => p.default)
    if (dflt) selectedProfile.value = dflt.name

    if (templates.value.length && !selectedWeeklyTemplate.value) {
      selectedWeeklyTemplate.value = templates.value[0].name
    }

    connectOrderSSE()
  }

  // Timer/interval IDs
  let _statusPollId: ReturnType<typeof setInterval> | null = null
  let _weeklyPollId: ReturnType<typeof setInterval> | null = null
  let _foodDebounceId: ReturnType<typeof setTimeout> | null = null
  let _keywordDebounceId: ReturnType<typeof setTimeout> | null = null
  let _generatingTickId: ReturnType<typeof setInterval> | null = null
  let _sseReconnectId: ReturnType<typeof setTimeout> | null = null
  let _mappingKwDebounceId: ReturnType<typeof setTimeout> | null = null
  let _mappingFoodDebounceId: ReturnType<typeof setTimeout> | null = null
  let _orderSSE: EventSource | null = null
  let _sseRetryDelay: number = CONST.SSE_INITIAL_RETRY_MS

  function destroy() {
    if (_statusPollId) { clearInterval(_statusPollId); _statusPollId = null }
    if (_weeklyPollId) { clearInterval(_weeklyPollId); _weeklyPollId = null }
    if (_foodDebounceId) { clearTimeout(_foodDebounceId); _foodDebounceId = null }
    if (_keywordDebounceId) { clearTimeout(_keywordDebounceId); _keywordDebounceId = null }
    if (_sseReconnectId) { clearTimeout(_sseReconnectId); _sseReconnectId = null }
    if (_mappingKwDebounceId) { clearTimeout(_mappingKwDebounceId); _mappingKwDebounceId = null }
    if (_mappingFoodDebounceId) { clearTimeout(_mappingFoodDebounceId); _mappingFoodDebounceId = null }
    if (_orderSSE) { _orderSSE.close(); _orderSSE = null }
    _stopGeneratingTick()
  }

  // ========================================================================
  // 5. Tier — Progressive Disclosure
  // ========================================================================

  function tierVisible(tier: AdminTier): boolean {
    return TIER_LEVELS[adminTier.value] >= TIER_LEVELS[tier]
  }

  function setTier(tier: AdminTier) {
    adminTier.value = tier
    localStorage.setItem(CONST.LS_ADMIN_TIER, tier)
    if (!tierVisible(TAB_TIERS[activeTab.value] || 'essential')) {
      activeTab.value = 'generate'
    }
  }

  // ========================================================================
  // 6. Data Loading
  // ========================================================================

  // --- Status ---
  const status = ref<GenerationStatus & { started_at?: string }>({ state: 'idle' })

  async function loadStatus() {
    try {
      const res = await fetch('/api/status')
      if (res.ok) status.value = await res.json()
    } catch {
      status.value = { state: 'error' }
    }
  }

  // --- Profiles ---
  const profiles = ref<AdminProfileSummary[]>([])
  const selectedProfile = ref('')

  async function loadProfiles() {
    try {
      const res = await fetch('/api/profiles')
      if (res.ok) {
        profiles.value = await res.json()
        if (profiles.value.length > 0 && !selectedProfile.value) {
          selectedProfile.value = profiles.value[0].name
        }
      }
    } catch (e) {
      console.warn('Failed to load profiles:', e)
    }
  }

  // --- Menu ---
  const recipes = ref<Recipe[]>([])
  const warnings = ref<string[]>([])
  const relaxedConstraints = ref<RelaxedConstraint[]>([])
  const menuVersion = ref<number | null>(null)
  const menuMeta = ref<MenuMeta>({})

  async function loadMenu() {
    try {
      const res = await fetch('/api/menu')
      if (res.ok) {
        const data = await res.json()
        recipes.value = data.recipes || []
        warnings.value = data.warnings || []
        relaxedConstraints.value = data.relaxed_constraints || []
        menuVersion.value = data.version
        menuMeta.value = {
          generated_at: data.generated_at,
          requested_count: data.requested_count,
          constraint_count: data.constraint_count,
          status: data.status,
        }
      }
    } catch {
      /* silent */
    }
  }

  function clearMenu() {
    confirmModal.value = {
      show: true,
      title: 'Clear Menu?',
      message: 'This will remove the current menu.',
      confirmText: 'Clear',
      onConfirm: async () => {
        try {
          const res = await adminFetch('/api/menu', { method: 'DELETE' })
          if (res.ok || res.status === 204) {
            recipes.value = []
            warnings.value = []
            relaxedConstraints.value = []
            menuMeta.value = {}
          }
        } catch (e: unknown) {
          showError('Failed to clear menu: ' + (e instanceof Error ? e.message : String(e)))
        }
      },
    }
  }

  // --- Keywords ---
  const keywords = ref<Array<{ id: number; name: string; parent?: number }>>([])
  const keywordMap = ref<Record<number, { id: number; name: string; parent?: number }>>({})
  const keywordFilter = ref('')
  const keywordSearch = ref('')
  const keywordResults = ref<Array<{ id: number; name: string; path: string }>>([])
  const selectedKeywords = ref<SelectedConstraintItem[]>([])

  async function loadKeywords() {
    try {
      const res = await fetch('/api/keywords')
      if (res.ok) {
        const data = await res.json()
        keywords.value = data.results || data || []
        const map: Record<number, { id: number; name: string; parent?: number }> = {}
        for (const kw of keywords.value) {
          map[kw.id] = kw
        }
        keywordMap.value = map
      }
    } catch (e) {
      console.warn('Failed to load keywords:', e)
    }
  }

  // --- Custom Filters ---
  const customFilters = ref<CustomFilter[]>([])

  async function loadCustomFilters() {
    try {
      const res = await fetch('/api/custom-filters')
      if (res.ok) {
        const data = await res.json()
        customFilters.value = data.results || data || []
      }
    } catch {
      /* not fatal */
    }
  }

  // --- Foods ---
  const foodSearch = ref('')
  const foodResults = ref<Array<{ id: number; name: string; path: string; supermarket_category?: { name: string } }>>([])
  const foodMap = ref<Record<number, { id: number; name: string }>>({})
  const selectedFoods = ref<SelectedConstraintItem[]>([])

  function searchFoods() {
    if (_foodDebounceId) clearTimeout(_foodDebounceId)
    _foodDebounceId = setTimeout(async () => {
      if (!foodSearch.value || foodSearch.value.length < CONST.MIN_KEYWORD_SEARCH_LEN) {
        foodResults.value = []
        return
      }
      try {
        const res = await fetch(`/api/foods?search=${encodeURIComponent(foodSearch.value)}`)
        if (res.ok) {
          const data = await res.json()
          const results = data.results || data || []
          foodResults.value = results.map((f: Record<string, unknown>) => ({
            ...f,
            path: (f.supermarket_category as { name?: string } | null)?.name
              ? `${(f.supermarket_category as { name: string }).name} \u203a ${f.name}`
              : f.name,
          }))
        }
      } catch {
        foodResults.value = []
      }
    }, CONST.FOOD_DEBOUNCE_MS)
  }

  function searchKeywords() {
    if (_keywordDebounceId) clearTimeout(_keywordDebounceId)
    _keywordDebounceId = setTimeout(() => {
      if (!keywordSearch.value || keywordSearch.value.length < CONST.MIN_KEYWORD_SEARCH_LEN) {
        keywordResults.value = []
        return
      }
      const query = keywordSearch.value.toLowerCase()
      keywordResults.value = keywords.value
        .filter(k => k.name.toLowerCase().includes(query))
        .map(k => ({ ...k, path: getKeywordPath(k) }))
        .slice(0, CONST.MAX_KEYWORD_RESULTS)
    }, CONST.KEYWORD_DEBOUNCE_MS)
  }

  // --- Path helpers ---

  function getKeywordPath(kw: { id: number; name: string; parent?: number }): string {
    if (!kw) return '?'
    const parts = [kw.name]
    let current = kw
    while (current.parent && keywordMap.value[current.parent]) {
      current = keywordMap.value[current.parent]
      parts.unshift(current.name)
    }
    return parts.length > 1 ? parts.join(' \u203a ') : kw.name
  }

  function getFoodPath(food: { id: number; name: string; supermarket_category?: number }): string {
    if (!food) return '?'
    const parts = [food.name]
    let current: Record<string, unknown> = food
    while (current.supermarket_category && foodMap.value[current.supermarket_category as number]) {
      current = foodMap.value[current.supermarket_category as number]
      parts.unshift(current.name as string)
    }
    return parts.length > 1 ? parts.join(' \u203a ') : food.name
  }

  // --- Keyword/food selection helpers (for custom generation) ---

  const filteredKeywords = computed(() => {
    if (!keywordFilter.value) return keywords.value
    const q = keywordFilter.value.toLowerCase()
    return keywords.value.filter(k => k.name.toLowerCase().includes(q))
  })

  function addKeyword(kw: { id: number; name: string }) {
    if (selectedKeywords.value.some(k => k.id === kw.id)) return
    selectedKeywords.value.push({ id: kw.id, name: kw.name, count: 1, operator: '>=' })
    keywordSearch.value = ''
    keywordResults.value = []
  }

  function removeKeyword(idx: number) {
    selectedKeywords.value.splice(idx, 1)
  }

  function toggleKeyword(kw: { id: number; name: string }) {
    const idx = selectedKeywords.value.findIndex(s => s.id === kw.id)
    if (idx >= 0) {
      selectedKeywords.value.splice(idx, 1)
    } else {
      selectedKeywords.value.push({ id: kw.id, name: kw.name, count: 1, operator: '>=' })
    }
  }

  function isKeywordSelected(kw: { id: number }): boolean {
    return selectedKeywords.value.some(s => s.id === kw.id)
  }

  function getKeywordConstraint(kw: { id: number }): SelectedConstraintItem | undefined {
    return selectedKeywords.value.find(s => s.id === kw.id)
  }

  function addFood(food: { id: number; name: string }) {
    if (selectedFoods.value.some(f => f.id === food.id)) return
    selectedFoods.value.push({ id: food.id, name: food.name, count: 1, operator: '>=' })
    foodSearch.value = ''
    foodResults.value = []
  }

  function removeFood(idx: number) {
    selectedFoods.value.splice(idx, 1)
  }

  // --- Constraint label helpers ---

  function getConstraintLabel(type: string, condition: unknown[]): string {
    if (!Array.isArray(condition) || condition.length === 0) return 'Any'
    if (type === 'keyword') {
      return condition.map((id) => keywordMap.value[id as number]?.name || `#${id}`).join(', ')
    } else if (type === 'food') {
      return condition.map((id) => foodMap.value[id as number]?.name || `#${id}`).join(', ')
    } else if (type === 'rating') {
      return condition.join(' - ')
    } else if (type === 'cookedon' || type === 'createdon') {
      return condition.join(' to ')
    }
    return JSON.stringify(condition)
  }

  async function cacheFood(id: number) {
    if (foodMap.value[id]) return
    try {
      const res = await fetch(`/api/foods/${id}`)
      if (res.ok) {
        const food = await res.json()
        foodMap.value[id] = food
      }
    } catch {
      /* silent */
    }
  }

  // ========================================================================
  // 7. Generation
  // ========================================================================

  const customChoices = ref(CONST.DEFAULT_CUSTOM_CHOICES)
  const _generatingTick = ref(0)

  function _startGeneratingTick() {
    _stopGeneratingTick()
    _generatingTickId = setInterval(() => { _generatingTick.value++ }, CONST.GENERATING_TICK_MS)
  }

  function _stopGeneratingTick() {
    if (_generatingTickId) { clearInterval(_generatingTickId); _generatingTickId = null }
  }

  function generatingElapsed(): string {
    // Access tick to make this reactive
    void _generatingTick.value
    const startedAt = (status.value as { started_at?: string }).started_at
    const start = startedAt ? new Date(startedAt) : null
    if (!start) return 'generating'
    const secs = Math.max(0, Math.round((Date.now() - start.getTime()) / 1000))
    return `generating \u00b7 ${secs}s`
  }

  async function generateProfile() {
    if (status.value.state === 'generating' || !selectedProfile.value) return
    status.value = { state: 'generating', started_at: new Date().toISOString() }
    _startGeneratingTick()

    try {
      const url = `/api/generate/${encodeURIComponent(selectedProfile.value)}`
      const res = await adminFetch(url, { method: 'POST' })
      if (res.status === 202 || res.status === 409) {
        startStatusPolling()
      } else {
        status.value = { state: 'error', error: 'Failed to start generation' }
      }
    } catch {
      status.value = { state: 'error', error: 'Cannot reach server' }
    }
  }

  async function generateCustom() {
    if (status.value.state === 'generating') return
    status.value = { state: 'generating', started_at: new Date().toISOString() }
    _startGeneratingTick()

    const body = {
      choices: customChoices.value,
      keyword: selectedKeywords.value.map(k => ({
        condition: Array.isArray(k.id) ? k.id : [k.id],
        count: String(k.count),
        operator: k.operator,
      })),
      food: selectedFoods.value.map(f => ({
        condition: [f.id],
        count: String(f.count),
        operator: f.operator,
      })),
    }

    try {
      const res = await adminFetch('/api/generate/custom', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (res.status === 202 || res.status === 409) {
        startStatusPolling()
      } else {
        status.value = { state: 'error', error: 'Failed to start custom generation' }
      }
    } catch {
      status.value = { state: 'error', error: 'Cannot reach server' }
    }
  }

  function startStatusPolling() {
    if (_statusPollId) clearInterval(_statusPollId)
    _statusPollId = setInterval(async () => {
      try {
        const res = await fetch('/api/status')
        if (!res.ok) return
        status.value = await res.json()

        if (status.value.state === 'complete' || status.value.state === 'idle') {
          clearInterval(_statusPollId!)
          _statusPollId = null
          _stopGeneratingTick()
          await loadMenu()
          loadHistory(0, { _silent: true, _skipAbort: true })
          loadAnalytics({ _silent: true, _skipAbort: true })
        } else if (status.value.state === 'error') {
          clearInterval(_statusPollId!)
          _statusPollId = null
          _stopGeneratingTick()
        }
      } catch {
        /* keep polling */
      }
    }, CONST.STATUS_POLL_MS)
  }

  // ========================================================================
  // 8. Profile CRUD
  // ========================================================================

  const editingProfile = ref(false)
  const isNewProfile = ref(false)
  const profileSaving = ref(false)
  const profilePreviewing = ref(false)
  const previewResult = ref<number | string | null>(null)
  const expandedConstraint = ref<number | null>(null)
  const collapsedGroups = ref<Record<string, boolean>>({})
  const showAddConstraintMenu = ref(false)

  const profileEditor = ref<ProfileEditorState>({
    name: '',
    originalName: '',
    description: '',
    choices: 5,
    min_choices: null,
    default: false,
    show_on_menu: true,
    icon: '',
    item_noun: '',
    category: '',
    constraints: [],
    filters: [],
  })

  async function loadProfileDetail(name: string): Promise<Record<string, unknown> | null> {
    try {
      const res = await fetch(`/api/profiles/${encodeURIComponent(name)}`)
      if (res.ok) {
        const data = await res.json()
        return data.config
      }
    } catch (e) {
      console.warn('Failed to load profile detail:', e)
    }
    return null
  }

  function startNewProfile() {
    if (adminTier.value === 'essential') {
      window.location.href = '/setup?mode=add-profile'
      return
    }
    isNewProfile.value = true
    editingProfile.value = true
    expandedConstraint.value = null
    collapsedGroups.value = {}
    profileEditor.value = {
      name: '',
      originalName: '',
      description: '',
      icon: '',
      category: '',
      choices: 5,
      min_choices: null,
      default: false,
      show_on_menu: true,
      item_noun: '',
      filters: [],
      constraints: [],
    }
  }

  async function startEditProfile(name: string) {
    const config = await loadProfileDetail(name)
    if (!config) return
    const profileInfo = profiles.value.find(p => p.name === name)
    isNewProfile.value = false
    editingProfile.value = true
    expandedConstraint.value = null

    profileEditor.value = {
      name,
      originalName: name,
      description: (config.description as string) || '',
      icon: (config.icon as string) || '',
      category: (config.category as string) || '',
      choices: (config.choices as number) || 5,
      min_choices: (config.min_choices as number) || null,
      default: profileInfo?.default || false,
      show_on_menu: config.show_on_menu !== false,
      item_noun: (config.item_noun as string) || '',
      filters: (config.filters as number[]) || [],
      constraints: (config.constraints as AdminConstraint[]) || [],
    }

    sortConstraintsByType()
    const types = new Set((profileEditor.value.constraints || []).map(c => c.type))
    collapsedGroups.value = {}
    for (const t of types) collapsedGroups.value[t] = true
    await resolveConstraintItemNames()
  }

  async function resolveConstraintItemNames() {
    const foodIdsToFetch = new Set<number>()

    for (const c of profileEditor.value.constraints) {
      if (c.type === 'cookedon' || c.type === 'createdon') {
        initDateFields(c)
      }
      if (c.type === 'keyword' && c.items) {
        for (const item of c.items) {
          if (keywordMap.value[item.id]?.name && !/^#\d+$/.test(keywordMap.value[item.id].name)) {
            item.name = keywordMap.value[item.id].name
          }
        }
      } else if (c.type === 'food') {
        if (c.items) {
          for (const item of c.items) {
            if (!foodMap.value[item.id] || /^#\d+$/.test(foodMap.value[item.id]?.name || '')) {
              foodIdsToFetch.add(item.id)
            }
          }
        }
        if (c.except) {
          for (const item of c.except) {
            if (!foodMap.value[item.id] || /^#\d+$/.test(foodMap.value[item.id]?.name || '')) {
              foodIdsToFetch.add(item.id)
            }
          }
        }
      }
    }

    // Fetch food names in parallel
    await Promise.all([...foodIdsToFetch].map(async (id) => {
      try {
        const res = await fetch(`/api/foods/${id}`)
        if (res.ok) {
          const food = await res.json()
          foodMap.value[id] = food
        }
      } catch {
        /* silent */
      }
    }))

    // Second pass: update food item names
    for (const c of profileEditor.value.constraints) {
      if (c.type === 'food') {
        if (c.items) {
          for (const item of c.items) {
            if (foodMap.value[item.id]?.name) item.name = foodMap.value[item.id].name
          }
        }
        if (c.except) {
          for (const item of c.except) {
            if (foodMap.value[item.id]?.name) item.name = foodMap.value[item.id].name
          }
        }
      }
    }
  }

  function cancelEditProfile() {
    editingProfile.value = false
    isNewProfile.value = false
  }

  async function saveProfile() {
    if (!profileEditor.value.name) return
    profileSaving.value = true

    const cleanConstraints = (profileEditor.value.constraints || []).map(c => {
      const cleaned = { ...c } as Record<string, unknown>
      delete cleaned.label
      delete cleaned.date_mode
      if (c.type === 'cookedon' || c.type === 'createdon') {
        syncDateFields(cleaned as unknown as AdminConstraint)
      }
      delete cleaned.goal
      delete cleaned.date_direction
      delete cleaned.date_days
      return cleaned
    })

    const body = {
      name: profileEditor.value.name,
      description: profileEditor.value.description,
      icon: profileEditor.value.icon,
      category: profileEditor.value.category,
      choices: profileEditor.value.choices,
      min_choices: profileEditor.value.min_choices,
      default: profileEditor.value.default,
      show_on_menu: profileEditor.value.show_on_menu,
      item_noun: profileEditor.value.item_noun,
      filters: profileEditor.value.filters.length > 0 ? profileEditor.value.filters : undefined,
      constraints: cleanConstraints,
    }

    try {
      const isRename = !isNewProfile.value && profileEditor.value.name !== profileEditor.value.originalName
      let res: Response

      if (isNewProfile.value) {
        res = await adminFetch('/api/profiles', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
      } else if (isRename) {
        res = await adminFetch('/api/profiles', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        if (res.ok) {
          await adminFetch(`/api/profiles/${encodeURIComponent(profileEditor.value.originalName)}`, {
            method: 'DELETE',
          })
        }
      } else {
        res = await adminFetch(`/api/profiles/${encodeURIComponent(profileEditor.value.name)}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
      }

      if (res.ok) {
        editingProfile.value = false
        isNewProfile.value = false
        await loadProfiles()
      } else {
        const err = await res.json().catch(() => ({} as Record<string, string>))
        showError('Save failed: ' + (err.detail || res.statusText))
      }
    } catch (e: unknown) {
      showError('Save failed: ' + (e instanceof Error ? e.message : String(e)))
    } finally {
      profileSaving.value = false
    }
  }

  function deleteProfile(name: string) {
    confirmModal.value = {
      show: true,
      title: 'Delete Profile?',
      message: `Are you sure you want to delete the profile "${name}"? This cannot be undone.`,
      confirmText: 'Delete',
      onConfirm: async () => {
        try {
          const res = await adminFetch(`/api/profiles/${encodeURIComponent(name)}`, { method: 'DELETE' })
          if (res.ok || res.status === 204) await loadProfiles()
        } catch (e: unknown) {
          showError('Delete failed: ' + (e instanceof Error ? e.message : String(e)))
        }
      },
    }
  }

  async function previewProfile() {
    if (profilePreviewing.value) return
    profilePreviewing.value = true
    previewResult.value = null

    const body = {
      name: profileEditor.value.name || 'preview',
      description: profileEditor.value.description,
      choices: profileEditor.value.choices,
      min_choices: profileEditor.value.min_choices,
      constraints: profileEditor.value.constraints || [],
    }

    try {
      const res = await adminFetch('/api/profiles/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (res.ok) {
        const data = await res.json()
        previewResult.value = data.matching_count
      } else {
        const err = await res.json().catch(() => ({} as Record<string, string>))
        previewResult.value = `Error: ${err.detail || res.statusText}`
      }
    } catch (e: unknown) {
      previewResult.value = `Error: ${e instanceof Error ? e.message : String(e)}`
    } finally {
      profilePreviewing.value = false
    }
  }

  // ========================================================================
  // 9. Constraint Builder
  // ========================================================================

  function addConstraint(type: AdminConstraintType) {
    const newConstraint: AdminConstraint = {
      type,
      operator: '>=',
      count: 1,
    }

    if (type === 'keyword' || type === 'food' || type === 'book') {
      newConstraint.items = []
    } else if (type === 'rating') {
      (newConstraint as unknown as Record<string, unknown>).min_rating = 3
    } else if (type === 'cookedon' || type === 'createdon') {
      newConstraint.date_direction = 'within'
      newConstraint.date_days = 30
      ;(newConstraint as unknown as Record<string, unknown>).within_days = 30
    }

    const lastOfType = profileEditor.value.constraints.reduce(
      (last, c, i) => c.type === type ? i : last, -1,
    )
    if (lastOfType >= 0) {
      profileEditor.value.constraints.splice(lastOfType + 1, 0, newConstraint)
      expandedConstraint.value = lastOfType + 1
    } else {
      profileEditor.value.constraints.push(newConstraint)
      expandedConstraint.value = profileEditor.value.constraints.length - 1
    }
    collapsedGroups.value[type] = false
  }

  function removeConstraint(idx: number) {
    profileEditor.value.constraints.splice(idx, 1)
    if (expandedConstraint.value === idx) {
      expandedConstraint.value = null
    } else if (expandedConstraint.value !== null && expandedConstraint.value > idx) {
      expandedConstraint.value--
    }
  }

  function toggleConstraintExpand(idx: number) {
    expandedConstraint.value = expandedConstraint.value === idx ? null : idx
  }

  function countConstraintsByType(type: AdminConstraintType): number {
    return (profileEditor.value.constraints || []).filter(c => c.type === type).length
  }

  function toggleGroupCollapse(type: string) {
    collapsedGroups.value[type] = !collapsedGroups.value[type]
  }

  function areAllGroupsCollapsed(): boolean {
    const types = new Set((profileEditor.value.constraints || []).map(c => c.type))
    if (types.size === 0) return false
    for (const t of types) {
      if (!collapsedGroups.value[t]) return false
    }
    return true
  }

  function toggleAllGroups() {
    const types = new Set((profileEditor.value.constraints || []).map(c => c.type))
    const allCollapsed = areAllGroupsCollapsed()
    for (const t of types) {
      collapsedGroups.value[t] = !allCollapsed
    }
  }

  function sortConstraintsByType() {
    profileEditor.value.constraints.sort((a, b) => {
      const ai = CONSTRAINT_TYPE_ORDER.indexOf(a.type)
      const bi = CONSTRAINT_TYPE_ORDER.indexOf(b.type)
      return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi)
    })
    expandedConstraint.value = null
  }

  function duplicateConstraint(idx: number) {
    const original = profileEditor.value.constraints[idx]
    const copy: AdminConstraint = JSON.parse(JSON.stringify(original))
    copy.label = (copy.label || '') + ' (copy)'
    profileEditor.value.constraints.splice(idx + 1, 0, copy)
    expandedConstraint.value = idx + 1
  }

  function moveConstraintUp(idx: number) {
    if (idx <= 0) return
    const constraints = profileEditor.value.constraints
    ;[constraints[idx - 1], constraints[idx]] = [constraints[idx], constraints[idx - 1]]
    if (expandedConstraint.value === idx) expandedConstraint.value = idx - 1
    else if (expandedConstraint.value === idx - 1) expandedConstraint.value = idx
  }

  function moveConstraintDown(idx: number) {
    const constraints = profileEditor.value.constraints
    if (idx >= constraints.length - 1) return
    ;[constraints[idx], constraints[idx + 1]] = [constraints[idx + 1], constraints[idx]]
    if (expandedConstraint.value === idx) expandedConstraint.value = idx + 1
    else if (expandedConstraint.value === idx + 1) expandedConstraint.value = idx
  }

  function quickAddConstraint(preset: string) {
    const presets: Record<string, AdminConstraint> = {
      'theme-keywords': { type: 'keyword', operator: '>=', count: 1, items: [], label: 'Theme' },
      'avoid-keywords': { type: 'keyword', operator: '==', count: 0, items: [], label: 'Avoid' },
      'include-foods': { type: 'food', operator: '>=', count: 1, items: [], label: 'Include Foods' },
      'avoid-foods': { type: 'food', operator: '==', count: 0, items: [], label: 'Avoid Foods' },
      'from-books': { type: 'book', operator: '>=', count: 1, items: [], label: 'From Books' },
      'min-rating': { type: 'rating', operator: '>=', count: 1, min: 4, label: 'Min Rating' },
      'avoid-recent': { type: 'cookedon', operator: '==', count: 0, date_direction: 'within', date_days: 14, label: 'Avoid Recent' },
      'include-new': { type: 'createdon', operator: '>=', count: 1, date_direction: 'within', date_days: 30, label: 'Include New' },
    }
    const c = presets[preset]
    if (!c) return
    const newConstraint = { ...c }

    const lastOfType = profileEditor.value.constraints.reduce(
      (last, x, i) => x.type === c.type ? i : last, -1,
    )
    if (lastOfType >= 0) {
      profileEditor.value.constraints.splice(lastOfType + 1, 0, newConstraint)
      expandedConstraint.value = lastOfType + 1
    } else {
      profileEditor.value.constraints.push(newConstraint)
      expandedConstraint.value = profileEditor.value.constraints.length - 1
    }
    collapsedGroups.value[c.type] = false
    showAddConstraintMenu.value = false
  }

  function addItemToConstraint(constraint: AdminConstraint, item: { id: number; name: string }) {
    if (!Array.isArray(constraint.items)) constraint.items = []
    if (constraint.items.some(i => i.id === item.id)) return
    constraint.items.push({ id: item.id, name: item.name })
    if (constraint.type === 'keyword') {
      keywordMap.value[item.id] = { id: item.id, name: item.name }
    } else if (constraint.type === 'food') {
      foodMap.value[item.id] = { id: item.id, name: item.name }
    }
  }

  function removeItemFromConstraint(constraint: AdminConstraint, itemId: number) {
    if (!Array.isArray(constraint.items)) return
    const idx = constraint.items.findIndex(i => i.id === itemId)
    if (idx >= 0) constraint.items.splice(idx, 1)
  }

  function isConstraintSoft(c: AdminConstraint): boolean {
    return (c as unknown as Record<string, unknown>).soft === true
  }

  function toggleConstraintSoft(c: AdminConstraint) {
    const record = c as unknown as Record<string, unknown>
    record.soft = !record.soft
    if (record.soft) {
      c.weight = c.weight || 10
    } else {
      delete record.soft
      delete record.weight
    }
  }

  function syncDateFields(c: AdminConstraint) {
    const record = c as unknown as Record<string, unknown>
    if (c.date_direction === 'within') {
      record.within_days = c.date_days || 30
      delete record.older_than_days
    } else {
      record.older_than_days = c.date_days || 30
      delete record.within_days
    }
  }

  function initDateFields(c: AdminConstraint) {
    const record = c as unknown as Record<string, unknown>
    if (record.older_than_days !== undefined) {
      c.date_direction = 'older'
      c.date_days = record.older_than_days as number
    } else {
      c.date_direction = 'within'
      c.date_days = (record.within_days as number) || 30
    }
  }

  function getItemDisplayName(item: { id: number; name?: string } | null, type: string): string {
    if (!item) return '?'
    if (item.name && /^#\d+$/.test(item.name)) {
      if (type === 'keyword' && keywordMap.value[item.id]?.name) {
        return keywordMap.value[item.id].name
      } else if (type === 'food' && foodMap.value[item.id]?.name) {
        return foodMap.value[item.id].name
      }
    }
    return item.name || `#${item.id}`
  }

  function getConstraintSummary(c: AdminConstraint): string {
    const opLabel = OPERATOR_LABELS[c.operator] || c.operator

    if (c.type === 'keyword' || c.type === 'food' || c.type === 'book') {
      const items = c.items || []
      if (items.length === 0) return `${opLabel} ${c.count} (no items selected)`
      const names = items.slice(0, 3).map(i => getItemDisplayName(i, c.type))
      let itemStr = names.join(', ')
      if (items.length > 3) itemStr += ` +${items.length - 3} more`
      return `${opLabel} ${c.count} with ${itemStr}`
    } else if (c.type === 'rating') {
      const min = c.min !== undefined ? c.min : 0
      const max = c.max !== undefined ? c.max : 5
      if (min > 0 && max < 5) return `${opLabel} ${c.count} rated ${min}-${max} stars`
      if (min > 0) return `${opLabel} ${c.count} rated ${min}+ stars`
      if (max < 5) return `${opLabel} ${c.count} rated up to ${max} stars`
      return `${opLabel} ${c.count} (any rating)`
    } else if (c.type === 'cookedon') {
      const record = c as unknown as Record<string, unknown>
      const days = c.date_days ?? (record.within_days as number) ?? (record.older_than_days as number) ?? 30
      const direction = c.date_direction ?? ((record.older_than_days !== undefined) ? 'older' : 'within')
      if (direction === 'older') return `${opLabel} ${c.count} made more than ${days} days ago`
      return `${opLabel} ${c.count} made within last ${days} days`
    } else if (c.type === 'createdon') {
      const record = c as unknown as Record<string, unknown>
      const days = c.date_days ?? (record.within_days as number) ?? (record.older_than_days as number) ?? 30
      const direction = c.date_direction ?? ((record.older_than_days !== undefined) ? 'older' : 'within')
      if (direction === 'older') return `${opLabel} ${c.count} added more than ${days} days ago`
      return `${opLabel} ${c.count} added within last ${days} days`
    } else if (c.type === 'makenow') {
      return `${opLabel} ${c.count} with on-hand ingredients`
    }
    return `${opLabel} ${c.count}`
  }

  function describeConstraint(c: AdminConstraint | null): string {
    if (!c) return ''
    const type = c.type
    const items = c.items || []
    const names = items.slice(0, 4).map(i => getItemDisplayName(i, type))
    const nameStr = names.join(', ') + (items.length > 4 ? ` +${items.length - 4} more` : '')
    const count = c.count || 0
    const op = c.operator || '>='
    const record = c as unknown as Record<string, unknown>

    if (type === 'keyword' || type === 'food' || type === 'book') {
      const typeLabel = type === 'keyword' ? 'keywords' : type === 'food' ? 'foods' : 'books'
      if (record.exclude) {
        return items.length ? `Exclude ${typeLabel}: ${nameStr}` : `Exclude ${typeLabel}`
      }
      if (op === '==' && count === 0) {
        return items.length ? `Exclude ${typeLabel}: ${nameStr}` : `Exclude ${typeLabel}`
      }
      if (op === '>=') return items.length ? `At least ${count} from: ${nameStr}` : `At least ${count} ${typeLabel}`
      if (op === '<=') return items.length ? `At most ${count} from: ${nameStr}` : `At most ${count} ${typeLabel}`
      if (op === '==') return items.length ? `Exactly ${count} from: ${nameStr}` : `Exactly ${count} ${typeLabel}`
    }
    if (type === 'rating') {
      const min = c.min !== undefined ? c.min : 0
      if (min > 0) return `Rating ${min}+ stars`
      return 'Rating filter'
    }
    if (type === 'cookedon') {
      const days = c.date_days ?? (record.within_days as number) ?? (record.older_than_days as number) ?? 30
      const dir = c.date_direction ?? ((record.older_than_days !== undefined) ? 'older' : 'within')
      if (record.exclude || (op === '==' && count === 0)) return `Avoid recipes cooked in last ${days} days`
      if (dir === 'older') return `${count}+ not cooked in ${days} days`
      return `${count}+ cooked within last ${days} days`
    }
    if (type === 'createdon') {
      const days = c.date_days ?? (record.within_days as number) ?? (record.older_than_days as number) ?? 30
      const dir = c.date_direction ?? ((record.older_than_days !== undefined) ? 'older' : 'within')
      if (dir === 'within') return `Include ${count}+ recipes added in last ${days} days`
      return `${count}+ recipes added over ${days} days ago`
    }
    if (type === 'makenow') return `At least ${count} with on-hand ingredients`
    return getConstraintSummary(c)
  }

  // ========================================================================
  // 10. Templates
  // ========================================================================

  const templates = ref<Template[]>([])
  const editingTemplate = ref(false)
  const isNewTemplate = ref(false)
  const templateSaving = ref(false)
  const expandedSlot = ref<number | null>(null)

  const templateEditor = ref<TemplateEditorState>({
    name: '',
    originalName: '',
    description: '',
    deduplicate: true,
    slots: [],
  })

  async function loadTemplates() {
    try {
      const res = await adminFetch('/api/templates')
      if (res.ok) templates.value = await res.json()
    } catch {
      /* silent */
    }
  }

  function startNewTemplate() {
    isNewTemplate.value = true
    templateEditor.value = { name: '', originalName: '', description: '', deduplicate: true, slots: [] }
    expandedSlot.value = null
    editingTemplate.value = true
  }

  async function startEditTemplate(name: string) {
    try {
      const res = await adminFetch(`/api/templates/${encodeURIComponent(name)}`)
      if (!res.ok) return
      const data = await res.json()
      isNewTemplate.value = false
      templateEditor.value = {
        name: data.name,
        originalName: data.name,
        description: data.description || '',
        deduplicate: data.deduplicate !== false,
        slots: data.slots || [],
      }
      expandedSlot.value = null
      editingTemplate.value = true
    } catch (e: unknown) {
      showError('Failed to load template: ' + (e instanceof Error ? e.message : String(e)))
    }
  }

  function cancelEditTemplate() {
    editingTemplate.value = false
  }

  async function saveTemplate() {
    if (!templateEditor.value.name) return
    templateSaving.value = true
    try {
      let res: Response
      if (isNewTemplate.value) {
        res = await adminFetch('/api/templates', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: templateEditor.value.name,
            description: templateEditor.value.description,
            deduplicate: templateEditor.value.deduplicate,
            slots: templateEditor.value.slots,
          }),
        })
      } else {
        res = await adminFetch(`/api/templates/${encodeURIComponent(templateEditor.value.originalName)}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            description: templateEditor.value.description,
            deduplicate: templateEditor.value.deduplicate,
            slots: templateEditor.value.slots,
          }),
        })
      }
      if (res.ok) {
        editingTemplate.value = false
        await loadTemplates()
        if (!selectedWeeklyTemplate.value && templates.value.length) {
          selectedWeeklyTemplate.value = templates.value[0].name
        }
      } else {
        const err = await res.json().catch(() => ({} as Record<string, string>))
        showError('Save failed: ' + (err.detail || res.statusText))
      }
    } catch (e: unknown) {
      showError('Save failed: ' + (e instanceof Error ? e.message : String(e)))
    } finally {
      templateSaving.value = false
    }
  }

  function deleteTemplate(name: string) {
    confirmModal.value = {
      show: true,
      title: 'Delete Template?',
      message: `Are you sure you want to delete the template "${name}"? This cannot be undone.`,
      confirmText: 'Delete',
      onConfirm: async () => {
        try {
          await adminFetch(`/api/templates/${encodeURIComponent(name)}`, { method: 'DELETE' })
          await loadTemplates()
        } catch (e: unknown) {
          showError('Delete failed: ' + (e instanceof Error ? e.message : String(e)))
        }
      },
    }
  }

  function addSlot() {
    templateEditor.value.slots.push({
      days: ['mon', 'tue', 'wed', 'thu', 'fri'],
      meal_type_id: mealTypes.value[0]?.id || 0,
      meal_type_name: mealTypes.value[0]?.name || '',
      profile: profiles.value[0]?.name || '',
      recipes_per_day: 1,
    })
    expandedSlot.value = templateEditor.value.slots.length - 1
  }

  function removeSlot(idx: number) {
    templateEditor.value.slots.splice(idx, 1)
    if (expandedSlot.value === idx) expandedSlot.value = null
    else if (expandedSlot.value !== null && expandedSlot.value > idx) expandedSlot.value--
  }

  function toggleSlotExpand(idx: number) {
    expandedSlot.value = expandedSlot.value === idx ? null : idx
  }

  function toggleSlotDay(slotIdx: number, day: string) {
    const days = templateEditor.value.slots[slotIdx].days
    const i = days.indexOf(day)
    if (i >= 0) {
      if (days.length <= 1) return
      days.splice(i, 1)
    } else {
      days.push(day)
    }
  }

  // ========================================================================
  // 11. Weekly
  // ========================================================================

  const weeklyStatus = ref<WeeklyStatus>({ state: 'idle', profile_progress: {} })
  const weeklyPlan = ref<Record<string, unknown> | null>(null)
  const weeklyPlanTemplate = ref('')
  const selectedWeeklyTemplate = ref('')
  const weeklyWeekStart = ref('')
  const weeklyGenerating = ref(false)
  const weeklyPlanSaving = ref(false)
  const weeklyPlanSaved = ref(false)
  const weeklyRegenSlot = ref<WeeklyRegenSlot | null>(null)

  const weeklyPlanDays = computed<WeeklyPlanDay[]>(() => {
    const plan = weeklyPlan.value as { days?: Record<string, unknown> } | null
    if (!plan?.days) return []
    return Object.entries(plan.days)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, data]) => ({ date, data: data as WeeklyPlanDay['data'] }))
  })

  async function generateWeekly() {
    if (weeklyGenerating.value || !selectedWeeklyTemplate.value) return
    weeklyGenerating.value = true
    weeklyPlanSaved.value = false
    weeklyPlanTemplate.value = selectedWeeklyTemplate.value
    weeklyStatus.value = { state: 'generating', profile_progress: {} }

    try {
      const body: Record<string, string> = {}
      if (weeklyWeekStart.value) body.week_start = weeklyWeekStart.value
      const res = await adminFetch(`/api/weekly/generate/${encodeURIComponent(selectedWeeklyTemplate.value)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (res.status === 202) {
        startWeeklyPolling()
      } else if (res.status === 409) {
        const err = await res.json().catch(() => ({} as Record<string, string>))
        showError(err.detail || 'Generation already in progress')
        startWeeklyPolling()
      } else {
        const err = await res.json().catch(() => ({} as Record<string, string>))
        showError(err.detail || 'Failed to start generation')
        weeklyGenerating.value = false
        weeklyStatus.value = { state: 'error', error: err.detail || 'Failed', profile_progress: {} }
      }
    } catch (e: unknown) {
      showError('Cannot reach server')
      weeklyGenerating.value = false
      weeklyStatus.value = { state: 'error', error: e instanceof Error ? e.message : String(e), profile_progress: {} }
    }
  }

  function startWeeklyPolling() {
    stopWeeklyPolling(true)
    _weeklyPollId = setInterval(async () => {
      try {
        const res = await fetch('/api/weekly/status')
        if (!res.ok) return
        const data: WeeklyStatus = await res.json()
        weeklyStatus.value = data

        if (data.state === 'complete' || data.state === 'idle') {
          stopWeeklyPolling()
          if (data.state === 'complete') await loadWeeklyPlan()
        } else if (data.state === 'error') {
          stopWeeklyPolling()
        }
      } catch {
        /* keep polling */
      }
    }, CONST.STATUS_POLL_MS)
  }

  function stopWeeklyPolling(keepGenerating = false) {
    if (_weeklyPollId) { clearInterval(_weeklyPollId); _weeklyPollId = null }
    if (!keepGenerating) weeklyGenerating.value = false
  }

  async function loadWeeklyPlan() {
    if (!weeklyPlanTemplate.value) return
    try {
      const res = await adminFetch(`/api/weekly/plan/${encodeURIComponent(weeklyPlanTemplate.value)}`)
      if (res.ok) {
        weeklyPlan.value = await res.json()
      } else if (res.status === 404) {
        weeklyPlan.value = null
      }
    } catch {
      /* silent */
    }
  }

  function discardWeeklyPlan() {
    confirmModal.value = {
      show: true,
      title: 'Discard Weekly Plan?',
      message: 'This will remove the generated weekly plan. This cannot be undone.',
      confirmText: 'Discard',
      onConfirm: async () => {
        try {
          await adminFetch(`/api/weekly/plan/${encodeURIComponent(weeklyPlanTemplate.value)}`, { method: 'DELETE' })
        } catch {
          /* ignore 404 */
        }
        weeklyPlan.value = null
        weeklyPlanSaved.value = false
      },
    }
  }

  async function regenerateSlot(date: string, mealTypeId: number) {
    weeklyRegenSlot.value = { date, mealTypeId }
    try {
      const res = await adminFetch('/api/weekly/regenerate-slot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template: weeklyPlanTemplate.value, date, meal_type_id: mealTypeId }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({} as Record<string, string>))
        showError(err.detail || 'Regeneration failed')
      }
    } catch (e: unknown) {
      showError('Regeneration failed: ' + (e instanceof Error ? e.message : String(e)))
    } finally {
      weeklyRegenSlot.value = null
      await loadWeeklyPlan()
    }
  }

  async function saveWeeklyPlan() {
    if (weeklyPlanSaving.value || !weeklyPlanTemplate.value) return
    weeklyPlanSaving.value = true
    try {
      const res = await adminFetch('/api/weekly/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template: weeklyPlanTemplate.value, shared: [] }),
      })
      if (res.ok) {
        const data = await res.json()
        weeklyPlanSaved.value = true
        const msg = `Saved ${data.created}/${data.total} meals to Tandoor`
        if (data.errors?.length) {
          showError(msg + '. Errors: ' + data.errors.join(', '))
        } else {
          reloadPrompt(msg)
        }
      } else {
        const err = await res.json().catch(() => ({} as Record<string, string>))
        showError('Save failed: ' + (err.detail || res.statusText))
      }
    } catch (e: unknown) {
      showError('Save failed: ' + (e instanceof Error ? e.message : String(e)))
    } finally {
      weeklyPlanSaving.value = false
    }
  }

  // ========================================================================
  // 12. Schedules
  // ========================================================================

  const schedules = ref<Schedule[]>([])
  const showScheduleForm = ref(false)
  const editingScheduleId = ref<number | null>(null)
  const mealTypes = ref<MealType[]>([])
  const showNewMealType = ref(false)
  const newMealTypeName = ref('')

  const scheduleForm = ref<ScheduleForm>({
    mode: 'profile',
    template: '',
    profile: '',
    day_of_week: 'mon-fri',
    hour: 16,
    minute: 0,
    enabled: true,
    clear_before_generate: false,
    create_meal_plan: false,
    meal_plan_type: null,
    cleanup_uncooked_days: 0,
    _selectedDays: ['mon', 'tue', 'wed', 'thu', 'fri'],
  })

  async function loadSchedules() {
    try {
      const res = await adminFetch('/api/schedules')
      if (res.ok) schedules.value = await res.json()
    } catch {
      /* silent */
    }
  }

  async function loadMealTypes() {
    try {
      const res = await fetch('/api/meal-types')
      if (res.ok) {
        const data = await res.json()
        mealTypes.value = Array.isArray(data) ? data : (data.results || [])
      }
    } catch {
      /* silent */
    }
  }

  async function createMealType() {
    const name = (newMealTypeName.value || '').trim()
    if (!name) return
    try {
      const res = await adminFetch('/api/meal-types', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, color: '#FF5722' }),
      })
      if (res.ok) {
        const created = await res.json()
        await loadMealTypes()
        settings.value.order_meal_type_id = created.id
        await saveSettings({ order_meal_type_id: created.id })
        showNewMealType.value = false
        newMealTypeName.value = ''
      } else {
        const err = await res.json().catch(() => ({} as Record<string, string>))
        showError('Failed to create meal type: ' + (err.detail || res.statusText))
      }
    } catch (e: unknown) {
      showError('Failed to create meal type: ' + (e instanceof Error ? e.message : String(e)))
    }
  }

  function parseCronDays(cronStr: string): string[] {
    const dayOrder = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    if (!cronStr || cronStr === '*') return [...dayOrder]
    const result = new Set<string>()
    const parts = cronStr.toLowerCase().split(',')
    for (const part of parts) {
      if (part.includes('-')) {
        const [start, end] = part.split('-')
        const si = dayOrder.indexOf(start.trim())
        const ei = dayOrder.indexOf(end.trim())
        if (si >= 0 && ei >= 0) {
          for (let i = si; i <= ei; i++) result.add(dayOrder[i])
        }
      } else {
        const d = part.trim()
        if (dayOrder.includes(d)) result.add(d)
      }
    }
    return dayOrder.filter(d => result.has(d))
  }

  function buildCronDays(selected: string[]): string {
    const dayOrder = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    const sorted = dayOrder.filter(d => selected.includes(d))
    if (sorted.length === 7) return '*'
    if (sorted.length === 0) return 'mon'

    const ranges: string[] = []
    let rangeStart: string | null = null
    let prev = -1
    for (const d of sorted) {
      const idx = dayOrder.indexOf(d)
      if (rangeStart === null) {
        rangeStart = d
        prev = idx
      } else if (idx === prev + 1) {
        prev = idx
      } else {
        ranges.push(
          dayOrder.indexOf(rangeStart) === prev ? rangeStart : `${rangeStart}-${dayOrder[prev]}`,
        )
        rangeStart = d
        prev = idx
      }
    }
    if (rangeStart !== null) {
      ranges.push(
        dayOrder.indexOf(rangeStart) === prev ? rangeStart : `${rangeStart}-${dayOrder[prev]}`,
      )
    }
    return ranges.join(',')
  }

  function toggleScheduleDay(day: string) {
    const idx = scheduleForm.value._selectedDays.indexOf(day)
    if (idx >= 0) {
      if (scheduleForm.value._selectedDays.length <= 1) return
      scheduleForm.value._selectedDays.splice(idx, 1)
    } else {
      scheduleForm.value._selectedDays.push(day)
    }
    scheduleForm.value.day_of_week = buildCronDays(scheduleForm.value._selectedDays)
  }

  function formatScheduleDays(cronStr: string): string {
    const dayLabels: Record<string, string> = { mon: 'Mon', tue: 'Tue', wed: 'Wed', thu: 'Thu', fri: 'Fri', sat: 'Sat', sun: 'Sun' }
    const days = parseCronDays(cronStr)
    if (days.length === 7) return 'Every day'
    if (days.length === 5 && !days.includes('sat') && !days.includes('sun')) return 'Weekdays'
    if (days.length === 2 && days.includes('sat') && days.includes('sun')) return 'Weekends'
    return days.map(d => dayLabels[d]).join(', ')
  }

  function startNewSchedule() {
    editingScheduleId.value = null
    scheduleForm.value = {
      mode: 'profile',
      template: templates.value[0]?.name || '',
      profile: profiles.value[0]?.name || '',
      day_of_week: 'mon-fri',
      hour: 16,
      minute: 0,
      enabled: true,
      clear_before_generate: false,
      create_meal_plan: false,
      meal_plan_type: null,
      cleanup_uncooked_days: 0,
      _selectedDays: parseCronDays('mon-fri'),
    }
    showScheduleForm.value = true
  }

  function editSchedule(s: Schedule) {
    editingScheduleId.value = s.id
    scheduleForm.value = {
      mode: s.template ? 'template' : 'profile',
      template: s.template || templates.value[0]?.name || '',
      profile: s.profile || profiles.value[0]?.name || '',
      day_of_week: s.day_of_week,
      hour: s.hour,
      minute: s.minute,
      enabled: s.enabled,
      clear_before_generate: s.clear_before_generate || false,
      create_meal_plan: s.create_meal_plan || false,
      meal_plan_type: s.meal_plan_type || null,
      cleanup_uncooked_days: s.cleanup_uncooked_days || 0,
      _selectedDays: parseCronDays(s.day_of_week),
    }
    showScheduleForm.value = true
  }

  async function saveSchedule() {
    const body: Record<string, unknown> = { ...scheduleForm.value }
    delete body._selectedDays
    delete body.mode
    if (scheduleForm.value.mode === 'template') {
      body.profile = null
      body.day_of_week = '*'
    } else {
      body.template = null
    }
    try {
      let res: Response
      if (editingScheduleId.value) {
        res = await adminFetch(`/api/schedules/${editingScheduleId.value}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
      } else {
        res = await adminFetch('/api/schedules', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
      }
      if (res.ok) {
        showScheduleForm.value = false
        editingScheduleId.value = null
        await loadSchedules()
      }
    } catch (e: unknown) {
      showError('Failed to save schedule: ' + (e instanceof Error ? e.message : String(e)))
    }
  }

  async function toggleScheduleEnabled(s: Schedule) {
    const body = {
      profile: s.profile,
      day_of_week: s.day_of_week,
      hour: s.hour,
      minute: s.minute,
      enabled: !s.enabled,
      create_meal_plan: s.create_meal_plan || false,
      meal_plan_type: s.meal_plan_type || null,
      cleanup_uncooked_days: s.cleanup_uncooked_days || 0,
    }
    try {
      const res = await adminFetch(`/api/schedules/${s.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (res.ok) await loadSchedules()
    } catch {
      /* silent */
    }
  }

  function deleteSchedule(id: number) {
    confirmModal.value = {
      show: true,
      title: 'Delete Schedule?',
      message: 'Are you sure you want to delete this schedule? This cannot be undone.',
      confirmText: 'Delete',
      onConfirm: async () => {
        try {
          await adminFetch(`/api/schedules/${id}`, { method: 'DELETE' })
          await loadSchedules()
        } catch {
          /* silent */
        }
      },
    }
  }

  // ========================================================================
  // 13. Orders
  // ========================================================================

  const orders = ref<Order[]>([])
  const orderCounts = ref<OrderCount[]>([])

  async function loadOrders() {
    try {
      const res = await adminFetch('/api/orders')
      if (res.ok) orders.value = await res.json()
    } catch {
      /* silent */
    }
    try {
      const res = await adminFetch('/api/orders/counts')
      if (res.ok) {
        const data = await res.json()
        orderCounts.value = data.counts || []
      }
    } catch {
      /* silent */
    }
  }

  function connectOrderSSE() {
    if (_orderSSE) _orderSSE.close()
    _sseRetryDelay = CONST.SSE_INITIAL_RETRY_MS

    // SSE can't send X-Admin-Token, skip when PIN auth is active
    const s = settings.value
    const pinActive = s.admin_pin_enabled || (s.kiosk_enabled && s.kiosk_pin_enabled)
    if (pinActive && s.has_pin) return

    _orderSSE = new EventSource('/api/orders/stream')
    _orderSSE.addEventListener('order', (e: MessageEvent) => {
      try {
        const order = JSON.parse(e.data)
        orders.value.unshift(order)
        const existing = orderCounts.value.find(c => c.recipe_id === order.recipe_id)
        if (existing) {
          existing.count += order.count
        } else {
          orderCounts.value.push({
            recipe_id: order.recipe_id,
            recipe_name: order.recipe_name,
            count: order.count,
          })
        }
      } catch {
        /* ignore parse errors */
      }
    })
    _orderSSE.addEventListener('connected', () => {
      _sseRetryDelay = CONST.SSE_INITIAL_RETRY_MS
    })
    _orderSSE.onerror = () => {
      _orderSSE!.close()
      _sseReconnectId = setTimeout(() => {
        connectOrderSSE()
      }, _sseRetryDelay)
      _sseRetryDelay = Math.min(_sseRetryDelay * 2, CONST.SSE_MAX_RETRY_MS)
    }
  }

  function clearOrders() {
    confirmModal.value = {
      show: true,
      title: 'Clear All Requests?',
      message: 'This will remove all requests from the queue. This cannot be undone.',
      confirmText: 'Clear All',
      onConfirm: async () => {
        try {
          await adminFetch('/api/orders', { method: 'DELETE' })
          orders.value = []
          orderCounts.value = []
        } catch {
          /* silent */
        }
      },
    }
  }

  async function markOrderReady(order: Order) {
    try {
      await adminFetch(`/api/orders/${order.id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'ready' }),
      })
    } catch (e) {
      console.warn('Failed to mark order ready:', e)
    }
  }

  async function deleteOrder(order: Order) {
    try {
      const res = await adminFetch(`/api/orders/${order.id}`, { method: 'DELETE' })
      if (res.ok || res.status === 204 || res.status === 404) {
        orders.value = orders.value.filter(o => o.id !== order.id)
        // Recompute counts
        const counts: Record<number, OrderCount> = {}
        for (const o of orders.value) {
          if (!counts[o.recipe_id]) {
            counts[o.recipe_id] = { recipe_id: o.recipe_id, recipe_name: o.recipe_name, count: 0 }
          }
          counts[o.recipe_id].count += 1
        }
        orderCounts.value = Object.values(counts)
      }
    } catch {
      /* silent */
    }
  }

  async function viewOrderRecipe(order: Order) {
    if (!order.recipe_id) return
    try {
      const res = await fetch(`/api/recipe/${order.recipe_id}`)
      if (res.ok) {
        const data = await res.json()
        openRecipe({
          id: data.id,
          name: data.name,
          image: data.image,
          rating: data.rating,
          description: data.description || '',
          ingredients: (data.steps || []).flatMap(
            (s: { ingredients?: Array<{ amount?: number; unit?: { name?: string }; food?: { name?: string } }> }) =>
              (s.ingredients || []).map(i => ({
                amount: i.amount,
                unit: i.unit?.name || '',
                food: i.food?.name || '',
              })),
          ),
          steps: (data.steps || [])
            .filter((s: { instruction?: string }) => s.instruction)
            .map((s: { name?: string; instruction: string; order: number; time?: number }) => ({
              name: s.name || '',
              instruction: s.instruction,
              order: s.order,
              time: s.time || 0,
            })),
        })
      }
    } catch (e) {
      console.warn('Failed to load recipe for order:', e)
    }
  }

  // ========================================================================
  // 14. Categories
  // ========================================================================

  const categories = ref<Category[]>([])
  const showCategoryForm = ref(false)
  const editingCategoryId = ref<string | number | null>(null)
  const categoryForm = ref<CategoryForm>({ display_name: '', subtitle: '', icon: '' })

  async function loadCategories() {
    try {
      const res = await fetch('/api/categories')
      if (res.ok) categories.value = await res.json()
    } catch {
      /* silent */
    }
  }

  function startNewCategory() {
    editingCategoryId.value = null
    categoryForm.value = { display_name: '', subtitle: '', icon: '' }
    showCategoryForm.value = true
  }

  function editCategory(cat: Category) {
    editingCategoryId.value = cat.id
    categoryForm.value = {
      display_name: cat.display_name,
      subtitle: cat.subtitle || '',
      icon: cat.icon || '',
    }
    showCategoryForm.value = true
  }

  async function saveCategory() {
    const body = {
      display_name: categoryForm.value.display_name,
      subtitle: categoryForm.value.subtitle,
      icon: categoryForm.value.icon,
    }
    try {
      let res: Response
      if (editingCategoryId.value) {
        res = await adminFetch(`/api/categories/${encodeURIComponent(String(editingCategoryId.value))}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
      } else {
        res = await adminFetch('/api/categories', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
      }
      if (res.ok) {
        showCategoryForm.value = false
        editingCategoryId.value = null
        await loadCategories()
      } else {
        const err = await res.json().catch(() => ({} as Record<string, string>))
        showError('Failed to save category: ' + (err.detail || res.statusText))
      }
    } catch (e: unknown) {
      showError('Failed to save category: ' + (e instanceof Error ? e.message : String(e)))
    }
  }

  function deleteCategory(id: string | number) {
    confirmModal.value = {
      show: true,
      title: 'Delete Category?',
      message: 'Are you sure you want to delete this category? Profiles using it will have their category cleared.',
      confirmText: 'Delete',
      onConfirm: async () => {
        try {
          await adminFetch(`/api/categories/${encodeURIComponent(String(id))}`, { method: 'DELETE' })
          await loadCategories()
        } catch {
          /* silent */
        }
      },
    }
  }

  async function reorderCategories(orderedIds: Array<string | number>) {
    try {
      const res = await adminFetch('/api/categories/reorder', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderedIds),
      })
      if (res.ok) categories.value = await res.json()
    } catch (e) {
      console.debug('Category reorder failed:', e)
    }
  }

  // ========================================================================
  // 15. Settings
  // ========================================================================

  const settings = ref<AppSettings & Record<string, unknown>>({
    app_name: 'Morsl',
    theme: 'cast-iron',
    kiosk_enabled: false,
    kiosk_pin_enabled: false,
    kiosk_gesture: 'menu',
    admin_pin_enabled: false,
    has_pin: false,
    show_logo: true,
    logo_url: '',
    favicon_url: '',
    favicon_use_logo: false,
    loading_icon_url: '',
    loading_icon_use_logo: false,
    slogan_header: '',
    slogan_footer: '',
    show_ratings: true,
    ratings_enabled: true,
    orders_enabled: true,
    save_ratings_to_tandoor: true,
    show_new_badge: true,
    item_noun: 'recipe',
    toast_seconds: CONST.DEFAULT_TOAST_SECONDS,
    menu_poll_seconds: CONST.DEFAULT_MENU_POLL_SECONDS,
    max_discover_generations: CONST.DEFAULT_MAX_DISCOVER_GENS,
    max_previous_recipes: CONST.DEFAULT_MAX_PREVIOUS_RECIPES,
    qr_show_on_menu: false,
    qr_wifi_string: '',
    qr_menu_url: '',
  })
  const settingsLoaded = ref(false)

  // Credential editing
  const credEditing = ref(false)
  const credEnvLocked = ref(false)
  const credUrl = ref('')
  const credToken = ref('')
  const credTesting = ref(false)
  const credSaving = ref(false)
  const credTestResult = ref<CredTestResult | null>(null)
  const credError = ref('')

  async function loadSettings() {
    try {
      const res = await adminFetch('/api/settings')
      if (res.ok) {
        settings.value = await res.json()
        settingsLoaded.value = true
        if (settings.value.theme) {
          currentTheme.value = settings.value.theme
          applyTheme(settings.value.theme)
        }
        document.title = (settings.value.app_name || 'Morsl') + ' - Admin'
        _updateFaviconLinks()
      }
      // Check if credentials are locked by env vars
      const statusRes = await fetch('/api/settings/setup-status')
      if (statusRes.ok) {
        const st = await statusRes.json()
        credEnvLocked.value = st.has_env_credentials
      }
    } catch (e) {
      console.warn('Failed to load settings:', e)
    }
  }

  async function saveSettings(updates: Record<string, unknown>) {
    try {
      const res = await adminFetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })
      if (res.ok) settings.value = await res.json()
    } catch (e) {
      console.warn('Failed to save settings:', e)
    }
  }

  async function toggleSetting(key: string, value: unknown) {
    settings.value[key] = value
    await saveSettings({ [key]: value })
    if (key === 'orders_enabled' && !value && activeTab.value === 'orders') {
      activeTab.value = 'generate'
    }
  }

  async function testCredentials() {
    if (!credUrl.value) return
    if (!credToken.value) {
      credError.value = 'Enter a token to test the connection.'
      return
    }
    credTesting.value = true
    credTestResult.value = null
    credError.value = ''
    try {
      const res = await adminFetch('/api/settings/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: credUrl.value, token: credToken.value }),
      })
      credTestResult.value = res.ok
        ? await res.json()
        : { success: false, error: 'Server error' }
    } catch {
      credTestResult.value = { success: false, error: 'Cannot reach server' }
    } finally {
      credTesting.value = false
    }
  }

  async function saveCredentials() {
    if (!credTestResult.value?.success) return
    credSaving.value = true
    credError.value = ''
    try {
      const res = await adminFetch('/api/settings/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: credUrl.value, token: credToken.value }),
      })
      if (res.ok) {
        credEditing.value = false
        await loadSettings()
        reloadPrompt('Tandoor credentials updated \u2014 reload to apply')
      } else {
        credError.value = 'Failed to save credentials.'
      }
    } catch {
      credError.value = 'Failed to save credentials. Please try again.'
    } finally {
      credSaving.value = false
    }
  }

  function _updateFaviconLinks() {
    const url = (settings.value.favicon_use_logo && settings.value.logo_url)
      ? settings.value.logo_url
      : settings.value.favicon_url
    if (!url) return
    document.querySelectorAll('link[rel="icon"]').forEach(link => {
      ;(link as HTMLLinkElement).href = url as string
    })
  }

  // ========================================================================
  // 16. Branding
  // ========================================================================

  async function saveBranding(key: string, value: unknown) {
    settings.value[key] = value
    await saveSettings({ [key]: value })
    document.title = (settings.value.app_name || 'Morsl') + ' - Admin'
  }

  async function uploadBranding(type: string, event: Event) {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await adminFetch(`/api/settings/upload/${type}`, {
        method: 'POST',
        body: formData,
      })
      if (res.ok) {
        settings.value = await res.json()
        if (type === 'favicon') {
          reloadPrompt('Icons regenerated. Reload to see favicon changes.')
        }
      } else {
        const err = await res.text()
        showError(`Upload failed: ${err}`)
      }
    } catch (e: unknown) {
      showError(`Upload failed: ${e instanceof Error ? e.message : String(e)}`)
    }
    input.value = ''
  }

  async function removeBranding(type: string) {
    try {
      const res = await adminFetch(`/api/settings/upload/${type}`, { method: 'DELETE' })
      if (res.ok) {
        settings.value = await res.json()
        if (type === 'favicon') {
          reloadPrompt('Favicon reset to default. Reload to see changes.')
        }
      }
    } catch (e: unknown) {
      showError(`Remove failed: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  async function syncIconToLogo(type: string, checked: boolean) {
    const settingKey = type === 'favicon' ? 'favicon_use_logo' : 'loading_icon_use_logo'
    settings.value[settingKey] = checked
    await saveSettings({ [settingKey]: checked })

    if (checked && settings.value.logo_url) {
      try {
        const blob = await (await fetch(settings.value.logo_url as string)).blob()
        const ext = (settings.value.logo_url as string).split('.').pop()?.split('?')[0] || 'png'
        const formData = new FormData()
        formData.append('file', blob, `logo.${ext}`)
        const res = await adminFetch(`/api/settings/upload/${type}`, {
          method: 'POST',
          body: formData,
        })
        if (res.ok) {
          settings.value = await res.json()
          if (type === 'favicon') {
            reloadPrompt('Favicon updated from logo. Reload to see changes.')
          }
        }
      } catch (e: unknown) {
        showError(`Sync failed: ${e instanceof Error ? e.message : String(e)}`)
      }
    }
  }

  function resetBranding() {
    confirmModal.value = {
      show: true,
      title: 'Reset Branding?',
      message: 'This will clear your app name, taglines, logo, favicon, and loading icon. This cannot be undone.',
      confirmText: 'Reset All',
      onConfirm: async () => {
        try {
          const res = await adminFetch('/api/settings/reset-branding', { method: 'POST' })
          if (res.ok) {
            settings.value = await res.json()
            document.title = (settings.value.app_name || 'Morsl') + ' - Admin'
            reloadPrompt('Branding reset! Reload to see all changes.')
          }
        } catch (e: unknown) {
          showError(`Reset failed: ${e instanceof Error ? e.message : String(e)}`)
        }
      },
    }
  }

  // ========================================================================
  // 17. QR
  // ========================================================================

  async function saveQrSetting(key: string, value: unknown) {
    settings.value[key] = value
    await saveSettings({ [key]: value })
  }

  async function saveWifiQr(ssid: string, password: string, encryption: string) {
    let wifiString = ''
    if (ssid) {
      const esc = (s: string) => s.replace(/([\\;,":])/, '\\$1')
      wifiString = `WIFI:T:${encryption};S:${esc(ssid)};`
      if (encryption !== 'nopass' && password) {
        wifiString += `P:${esc(password)};`
      }
      wifiString += ';'
    }
    settings.value.qr_wifi_ssid = ssid
    settings.value.qr_wifi_password = password
    settings.value.qr_wifi_encryption = encryption
    settings.value.qr_wifi_string = wifiString
    await saveSettings({
      qr_wifi_ssid: ssid,
      qr_wifi_password: password,
      qr_wifi_encryption: encryption,
      qr_wifi_string: wifiString,
    })
  }

  // ========================================================================
  // 18. Icon Mappings
  // ========================================================================

  const iconMappings = ref<IconMappings>({ keyword_icons: {}, food_icons: {} })
  const newKwName = ref('')
  const newKwIcon = ref('')
  const newFoodName = ref('')
  const newFoodIcon = ref('')
  const mappingKwSearch = ref('')
  const mappingKwResults = ref<Array<{ id: number; name: string }>>([])
  const mappingFoodSearch = ref('')
  const mappingFoodResults = ref<Array<{ id: number; name: string }>>([])
  const mappingFoodSearched = ref(false)

  async function loadIconMappings() {
    try {
      const res = await fetch('/api/icon-mappings')
      if (res.ok) iconMappings.value = await res.json()
    } catch (e) {
      console.warn('Failed to load icon mappings:', e)
    }
  }

  async function saveIconMappings() {
    try {
      await adminFetch('/api/icon-mappings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(iconMappings.value),
      })
    } catch (e: unknown) {
      showError(`Failed to save icon mappings: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  function addMapping(type: 'keyword' | 'food') {
    const nameRef = type === 'keyword' ? newKwName : newFoodName
    const iconRef = type === 'keyword' ? newKwIcon : newFoodIcon
    const searchRef = type === 'keyword' ? mappingKwSearch : mappingFoodSearch
    const name = (nameRef.value || searchRef.value || '').trim()
    const icon = iconRef.value
    if (!name || !icon) return

    const mapKey = type === 'keyword' ? 'keyword_icons' : 'food_icons'
    iconMappings.value[mapKey][name.toLowerCase()] = icon
    nameRef.value = ''
    iconRef.value = ''

    if (type === 'keyword') {
      mappingKwSearch.value = ''
      mappingKwResults.value = []
    } else {
      mappingFoodSearch.value = ''
      mappingFoodResults.value = []
    }
    saveIconMappings()
  }

  function searchMappingKeywords() {
    if (_mappingKwDebounceId) clearTimeout(_mappingKwDebounceId)
    _mappingKwDebounceId = setTimeout(() => {
      if (!mappingKwSearch.value || mappingKwSearch.value.length < CONST.MIN_KEYWORD_SEARCH_LEN) {
        mappingKwResults.value = []
        return
      }
      const query = mappingKwSearch.value.toLowerCase()
      mappingKwResults.value = keywords.value
        .filter(k => k.name.toLowerCase().includes(query))
        .slice(0, CONST.MAX_KEYWORD_RESULTS)
    }, CONST.KEYWORD_DEBOUNCE_MS)
  }

  function selectMappingKeyword(kw: { name: string }) {
    newKwName.value = kw.name
    mappingKwSearch.value = ''
    mappingKwResults.value = []
  }

  function searchMappingFoods() {
    if (_mappingFoodDebounceId) clearTimeout(_mappingFoodDebounceId)
    _mappingFoodDebounceId = setTimeout(async () => {
      if (!mappingFoodSearch.value || mappingFoodSearch.value.length < CONST.MIN_KEYWORD_SEARCH_LEN) {
        mappingFoodResults.value = []
        mappingFoodSearched.value = false
        return
      }
      try {
        const res = await fetch(`/api/foods?search=${encodeURIComponent(mappingFoodSearch.value)}`)
        if (res.ok) {
          const data = await res.json()
          mappingFoodResults.value = data.results || data || []
        }
      } catch {
        mappingFoodResults.value = []
      }
      mappingFoodSearched.value = true
    }, CONST.FOOD_DEBOUNCE_MS)
  }

  function selectMappingFood(food: { name: string }) {
    newFoodName.value = food.name
    mappingFoodSearch.value = ''
    mappingFoodResults.value = []
  }

  function removeMapping(type: 'keyword' | 'food', name: string) {
    const mapKey = type === 'keyword' ? 'keyword_icons' : 'food_icons'
    delete iconMappings.value[mapKey][name]
    saveIconMappings()
  }

  // ========================================================================
  // 19. History & Analytics
  // ========================================================================

  const history = ref<HistoryEntry[]>([])
  const historyTotal = ref(0)
  const historyPage = ref(0)
  const historyPageSize = ref(CONST.HISTORY_PAGE_SIZE)
  const historyLoading = ref(false)
  const expandedHistoryId = ref<number | null>(null)
  const analytics = ref<AnalyticsData>({
    total_generations: 0,
    avg_duration_ms: 0,
    status_counts: {},
    profile_counts: {},
    most_relaxed: [],
    avg_recipes_per_generation: 0,
  })

  const historyTotalPages = computed(() =>
    Math.max(1, Math.ceil(historyTotal.value / historyPageSize.value)),
  )

  async function loadHistory(page = 0, fetchOpts: AdminFetchOptions = {}) {
    historyLoading.value = true
    try {
      const offset = page * historyPageSize.value
      const res = await adminFetch(`/api/history?limit=${historyPageSize.value}&offset=${offset}`, fetchOpts)
      if (res.ok) {
        const data = await res.json()
        history.value = data.entries
        historyTotal.value = data.total
        historyPage.value = page
      }
    } catch (e) {
      console.debug('loadHistory failed:', e)
    } finally {
      historyLoading.value = false
    }
  }

  async function loadAnalytics(fetchOpts: AdminFetchOptions = {}) {
    try {
      const res = await adminFetch('/api/history/analytics', fetchOpts)
      if (res.ok) analytics.value = await res.json()
    } catch (e) {
      console.debug('loadAnalytics failed:', e)
    }
  }

  function toggleHistoryDetail(id: number) {
    expandedHistoryId.value = expandedHistoryId.value === id ? null : id
  }

  function clearHistory() {
    confirmModal.value = {
      show: true,
      title: 'Clear Generation History?',
      message: 'This will delete all generation history and reset analytics. This cannot be undone.',
      confirmText: 'Clear History',
      onConfirm: async () => {
        try {
          const res = await adminFetch('/api/history', { method: 'DELETE' })
          if (res.ok) {
            history.value = []
            historyTotal.value = 0
            historyPage.value = 0
            analytics.value = {
              total_generations: 0,
              avg_duration_ms: 0,
              status_counts: {},
              profile_counts: {},
              most_relaxed: [],
              avg_recipes_per_generation: 0,
            }
          }
        } catch (e: unknown) {
          showError('Failed to clear history: ' + (e instanceof Error ? e.message : String(e)))
        }
      },
    }
  }

  // ========================================================================
  // 20. Ratings
  // ========================================================================

  async function setRating(recipeId: number, rating: number) {
    if (!recipeId) return
    try {
      const res = await fetch(`/api/recipe/${recipeId}/rating`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating }),
      })
      if (res.ok) {
        const recipe = recipes.value.find(r => r.id === recipeId)
        if (recipe) recipe.rating = rating
        if (selectedRecipe.value && selectedRecipe.value.id === recipeId) {
          selectedRecipe.value.rating = rating
        }
      }
    } catch (e) {
      console.warn('Failed to set rating:', e)
    }
  }

  // ========================================================================
  // 21. Recipe Modal
  // ========================================================================

  const selectedRecipe = ref<Recipe | RecipeDetail | null>(null)

  function openRecipe(recipe: Recipe | RecipeDetail | Record<string, unknown>) {
    selectedRecipe.value = recipe as Recipe
  }

  function closeRecipe() {
    selectedRecipe.value = null
  }

  // ========================================================================
  // 22. Factory Reset & Kiosk Lock
  // ========================================================================

  function factoryReset() {
    confirmModal.value = {
      show: true,
      title: 'Factory Reset?',
      message: 'This will permanently delete all profiles, categories, schedules, history, branding, and settings. The app will return to the first-run setup wizard. This cannot be undone.',
      confirmText: 'Reset Everything',
      onConfirm: async () => {
        try {
          const res = await adminFetch('/api/settings/factory-reset', { method: 'POST' })
          if (res.ok) {
            localStorage.clear()
            sessionStorage.clear()
            window.location.href = '/setup'
          } else {
            showError('Factory reset failed.')
          }
        } catch (e: unknown) {
          showError('Factory reset failed: ' + (e instanceof Error ? e.message : String(e)))
        }
      },
    }
  }

  function lockKiosk() {
    sessionStorage.removeItem(CONST.SS_ADMIN_TOKEN)
    window.location.href = '/'
  }

  // ========================================================================
  // 23. Theming
  // ========================================================================

  const currentTheme = ref(localStorage.getItem('morsl-theme') || 'cast-iron')
  const themeRegistry = THEME_REGISTRY

  function applyTheme(name: string) {
    const entry = THEME_REGISTRY[name]
    if (!entry) return
    currentTheme.value = name
    localStorage.setItem('morsl-theme', name)
    document.documentElement.setAttribute('data-theme', name)
  }

  async function changeTheme(name: string) {
    applyTheme(name)
    settings.value.theme = name
    await saveSettings({ theme: name })
  }

  // ========================================================================
  // 24. Helpers
  // ========================================================================

  function formatSolverStatus(s: string): string {
    const map: Record<string, string> = {
      optimal: 'Generated successfully',
      infeasible: 'Could not generate \u2014 rules too strict',
      error: 'Failed',
    }
    return map[s] || s || ''
  }

  function resolveNoun(profileName: string): string {
    const p = profiles.value.find(x => x.name === profileName)
    return (p?.item_noun) || (settings.value.item_noun as string) || 'recipe'
  }

  // ========================================================================
  // Return
  // ========================================================================

  return {
    // 1. Navigation & UI
    activeTab,
    adminTier,
    navOpen,
    adminReady,
    appVersion,
    confirmModal,
    reloadToastMsg,
    reloadToastShow,
    reloadPrompt,
    dismissReloadPrompt,
    errorMsg,
    errorShow,
    showError,
    dismissError,

    // 2. PIN Gate
    showPinGate,
    pinInput,
    pinError,
    showPinText,
    submitPin,

    // 3. Auth
    adminFetch,

    // 4. Init & Lifecycle
    init,
    destroy,

    // 5. Tier
    tierVisible,
    setTier,

    // 6. Data Loading
    status,
    loadStatus,
    profiles,
    selectedProfile,
    loadProfiles,
    recipes,
    warnings,
    relaxedConstraints,
    menuVersion,
    menuMeta,
    loadMenu,
    clearMenu,
    keywords,
    keywordMap,
    keywordFilter,
    keywordSearch,
    keywordResults,
    selectedKeywords,
    loadKeywords,
    customFilters,
    loadCustomFilters,
    foodSearch,
    foodResults,
    foodMap,
    selectedFoods,
    searchFoods,
    searchKeywords,
    filteredKeywords,
    addKeyword,
    removeKeyword,
    toggleKeyword,
    isKeywordSelected,
    getKeywordConstraint,
    addFood,
    removeFood,
    getKeywordPath,
    getFoodPath,
    getConstraintLabel,
    cacheFood,

    // 7. Generation
    customChoices,
    generatingElapsed,
    generateProfile,
    generateCustom,
    startStatusPolling,

    // 8. Profile CRUD
    editingProfile,
    isNewProfile,
    profileSaving,
    profilePreviewing,
    previewResult,
    expandedConstraint,
    collapsedGroups,
    showAddConstraintMenu,
    profileEditor,
    loadProfileDetail,
    startNewProfile,
    startEditProfile,
    resolveConstraintItemNames,
    cancelEditProfile,
    saveProfile,
    deleteProfile,
    previewProfile,

    // 9. Constraint Builder
    addConstraint,
    removeConstraint,
    toggleConstraintExpand,
    countConstraintsByType,
    toggleGroupCollapse,
    areAllGroupsCollapsed,
    toggleAllGroups,
    sortConstraintsByType,
    duplicateConstraint,
    moveConstraintUp,
    moveConstraintDown,
    quickAddConstraint,
    addItemToConstraint,
    removeItemFromConstraint,
    isConstraintSoft,
    toggleConstraintSoft,
    syncDateFields,
    initDateFields,
    getItemDisplayName,
    getConstraintSummary,
    describeConstraint,

    // 10. Templates
    templates,
    editingTemplate,
    isNewTemplate,
    templateSaving,
    expandedSlot,
    templateEditor,
    loadTemplates,
    startNewTemplate,
    startEditTemplate,
    cancelEditTemplate,
    saveTemplate,
    deleteTemplate,
    addSlot,
    removeSlot,
    toggleSlotExpand,
    toggleSlotDay,

    // 11. Weekly
    weeklyStatus,
    weeklyPlan,
    weeklyPlanTemplate,
    selectedWeeklyTemplate,
    weeklyWeekStart,
    weeklyGenerating,
    weeklyPlanSaving,
    weeklyPlanSaved,
    weeklyRegenSlot,
    weeklyPlanDays,
    generateWeekly,
    startWeeklyPolling,
    stopWeeklyPolling,
    loadWeeklyPlan,
    discardWeeklyPlan,
    regenerateSlot,
    saveWeeklyPlan,

    // 12. Schedules
    schedules,
    showScheduleForm,
    editingScheduleId,
    mealTypes,
    showNewMealType,
    newMealTypeName,
    scheduleForm,
    loadSchedules,
    loadMealTypes,
    createMealType,
    parseCronDays,
    buildCronDays,
    toggleScheduleDay,
    formatScheduleDays,
    startNewSchedule,
    editSchedule,
    saveSchedule,
    toggleScheduleEnabled,
    deleteSchedule,

    // 13. Orders
    orders,
    orderCounts,
    loadOrders,
    connectOrderSSE,
    clearOrders,
    markOrderReady,
    deleteOrder,
    viewOrderRecipe,

    // 14. Categories
    categories,
    showCategoryForm,
    editingCategoryId,
    categoryForm,
    loadCategories,
    startNewCategory,
    editCategory,
    saveCategory,
    deleteCategory,
    reorderCategories,

    // 15. Settings
    settings,
    settingsLoaded,
    credEditing,
    credEnvLocked,
    credUrl,
    credToken,
    credTesting,
    credSaving,
    credTestResult,
    credError,
    loadSettings,
    saveSettings,
    toggleSetting,
    testCredentials,
    saveCredentials,

    // 16. Branding
    saveBranding,
    uploadBranding,
    removeBranding,
    syncIconToLogo,
    resetBranding,

    // 17. QR
    saveQrSetting,
    saveWifiQr,

    // 18. Icon Mappings
    iconMappings,
    newKwName,
    newKwIcon,
    newFoodName,
    newFoodIcon,
    mappingKwSearch,
    mappingKwResults,
    mappingFoodSearch,
    mappingFoodResults,
    mappingFoodSearched,
    loadIconMappings,
    saveIconMappings,
    addMapping,
    searchMappingKeywords,
    selectMappingKeyword,
    searchMappingFoods,
    selectMappingFood,
    removeMapping,

    // 19. History & Analytics
    history,
    historyTotal,
    historyPage,
    historyPageSize,
    historyLoading,
    expandedHistoryId,
    analytics,
    historyTotalPages,
    loadHistory,
    loadAnalytics,
    toggleHistoryDetail,
    clearHistory,

    // 20. Ratings
    setRating,

    // 21. Recipe Modal
    selectedRecipe,
    openRecipe,
    closeRecipe,

    // 22. Factory Reset & Kiosk
    factoryReset,
    lockKiosk,

    // 23. Theming
    currentTheme,
    themeRegistry,
    applyTheme,
    changeTheme,

    // 24. Helpers
    formatSolverStatus,
    resolveNoun,
    OPERATOR_LABELS,
  }
})
