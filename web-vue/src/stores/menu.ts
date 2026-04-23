import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  Menu, Recipe, GenerationStatus, Shelf, ShelfGeneration,
  CarouselItem, CarouselDivider, IconMappings,
  NamePromptState, ConfirmModalState, MealPlanSaveState,
  PendingOrder,
} from '@/types/api'
import { CONST } from '@/constants'
import { useProfilesStore } from '@/stores/profiles'
import { useSettingsStore } from '@/stores/settings'

export const useMenuStore = defineStore('menu', () => {
  // Application state
  const state = ref<'loading' | 'ready' | 'generating' | 'error'>('loading')
  const errorMessage = ref('')
  const appVersion = ref('')

  // Menu data
  const currentRecipes = ref<Recipe[]>([])
  const previousRecipes = ref<Recipe[]>([])
  const warnings = ref<string[]>([])
  const relaxedConstraints = ref<Menu['relaxed_constraints']>([])
  const menuVersion = ref<number | null>(null)
  const generatedAt = ref('')

  // Active profile for generation
  const activeProfile = ref<string | null>(null)

  // Shelves (localStorage persistence)
  const shelves = ref<Shelf[]>([])
  const activeDeckName = ref<string | null>(null)
  const _targetShelf = ref<string | null>(null)

  // Icon mappings
  const iconMappings = ref<IconMappings>({ keyword_icons: {}, food_icons: {} })

  // SSE internals
  const _loadMenuInFlight = ref(false)
  const _loadMenuPending = ref(false)
  const _pendingClearOthers = ref(false)

  // Polling handles
  let _statusPollId: ReturnType<typeof setInterval> | null = null

  // Customer order SSE
  let _customerSSE: EventSource | null = null

  // Recipe modal
  const selectedRecipe = ref<Recipe | null>(null)
  const orderConfirm = ref<number | null>(null)
  const pendingOrder = ref<PendingOrder | null>(null)

  // Name prompt
  const namePrompt = ref<NamePromptState>({
    show: false, name: '', recipe: null, action: '', rating: 0, confirmStep: false,
  })
  const recentNames = ref<string[]>([])

  // Navigation
  const navOpen = ref(false)

  // Category panel
  const categoryPanelOpen = ref<string | number | null>(null)

  // Confirmation modal
  const confirmModal = ref<ConfirmModalState>({
    show: false, title: '', message: '', confirmText: '', onConfirm: () => {},
  })

  // Meal plan
  const mealPlanSave = ref<MealPlanSaveState>({
    show: false, date: new Date().toISOString().slice(0, 10),
    mealTypeId: null, mealTypes: [], users: [], selectedUsers: [],
    saving: false, profile: null, generations: [], selectedGen: 0, expandedGen: null,
  })
  const mealPlanToast = ref(false)

  // Kiosk PIN
  const showKioskPin = ref(false)
  const showKioskPinText = ref(false)
  const kioskPinValue = ref('')
  const kioskPinError = ref('')

  // Carousel cache
  let _carouselCache: CarouselItem[] | null = null
  let _carouselCacheKey: string | null = null

  // Carousel scroll trigger — increment to signal scroll-to-start
  const carouselScrollTrigger = ref(0)

  // ---- Computed ----

  const isGenerating = computed(() => state.value === 'generating')
  const isReady = computed(() => state.value === 'ready')
  const isLoading = computed(() => state.value === 'loading')
  const hasMenu = computed(() => shelves.value.length > 0)
  const recipes = computed(() => [...currentRecipes.value, ...previousRecipes.value])

  const activeShelf = computed<Shelf | null>(() => {
    if (activeDeckName.value === null) return null
    return shelves.value.find(s => s.name === activeDeckName.value) ?? null
  })

  const mainCarouselRecipes = computed<CarouselItem[]>(() => {
    let gens: ShelfGeneration[]
    if (activeDeckName.value) {
      gens = (shelves.value.find(s => s.name === activeDeckName.value))?.generations ?? []
    } else if (shelves.value.length > 0) {
      gens = shelves.value[0].generations ?? []
    } else {
      return []
    }
    const cacheKey = (activeDeckName.value || '_first') + ':' + gens.length + ':' +
      gens.reduce((s, g) => s + (g.recipes ? g.recipes.length : 0), 0)
    if (_carouselCacheKey === cacheKey && _carouselCache) {
      return _carouselCache
    }
    const profile = activeDeckName.value || (shelves.value[0]?.name) || 'mixed'
    _carouselCache = flattenGenerations(gens, profile)
    _carouselCacheKey = cacheKey
    return _carouselCache
  })

  function flattenGenerations(generations: ShelfGeneration[], defaultProfile: string): CarouselItem[] {
    const items: CarouselItem[] = []
    for (let i = 0; i < generations.length; i++) {
      const gen = generations[i]
      if (!gen || !Array.isArray(gen.recipes)) continue
      if (i > 0) {
        const divider: CarouselDivider = {
          _isDivider: true,
          _pageNum: i + 1,
          _totalPages: generations.length,
          _generatedAt: gen.generatedAt,
          _profile: gen.profile || defaultProfile,
        }
        items.push(divider)
      }
      for (const recipe of gen.recipes) {
        if (recipe && recipe.id) {
          items.push({ ...recipe, _genIndex: i })
        }
      }
    }
    return items
  }

  // ---- Data Loading ----

  async function loadHealth() {
    try {
      const h = await fetch('/health')
      if (h.ok) appVersion.value = ((await h.json()) as { version?: string }).version || ''
    } catch {
      // ignore
    }
  }

  async function loadMenu(opts: { clearOthers?: boolean } = {}) {
    try {
      const res = await fetch('/api/menu')
      if (res.ok) {
        const data: Menu = await res.json()
        const effectiveClear = opts.clearOthers || !!data.clear_others
        applyMenuData(data, { clearOthers: effectiveClear })
        state.value = 'ready'
      } else if (res.status === 404) {
        shelves.value = []
        activeDeckName.value = null
        currentRecipes.value = []
        saveShelves()
        await _checkGenerationStatus()
      } else {
        state.value = 'error'
        errorMessage.value = 'Failed to load menu'
      }
    } catch {
      state.value = 'error'
      errorMessage.value = 'Cannot reach server'
    }
  }

  async function _checkGenerationStatus() {
    try {
      const res = await fetch('/api/status')
      if (res.ok) {
        const status: GenerationStatus = await res.json()
        if (status.state === 'error') {
          state.value = 'error'
          errorMessage.value = status.error || 'Generation failed'
          return
        } else if (status.state === 'generating') {
          state.value = 'generating'
          startStatusPolling()
          return
        }
      }
    } catch {
      // Fall through
    }
    state.value = 'ready'
  }

  function applyMenuData(data: Menu, opts: { clearOthers?: boolean } = {}) {
    const newRecipes = data.recipes || []
    warnings.value = data.warnings || []
    relaxedConstraints.value = data.relaxed_constraints || []
    generatedAt.value = data.generated_at || ''

    const versionChanged = data.version !== menuVersion.value

    if (newRecipes.length > 0) {
      currentRecipes.value = newRecipes

      if (opts.clearOthers && versionChanged) {
        shelves.value = []
        activeDeckName.value = null
        _carouselCache = null
        _carouselCacheKey = null
      }

      if (shelves.value.length === 0) {
        const name = data.profile || activeProfile.value || 'Menu'
        addShelf(name, newRecipes, data.generated_at)
        activeDeckName.value = name
      } else if (versionChanged) {
        const target = data.profile || activeDeckName.value || activeProfile.value || 'Menu'
        addShelf(target, newRecipes, data.generated_at)
        activeDeckName.value = target
        saveShelves()
      }

      // Merge previous recipes
      const newIdSet = new Set(newRecipes.map(r => r.id))
      const merged = [
        ...currentRecipes.value.filter(r => !newIdSet.has(r.id)),
        ...previousRecipes.value.filter(r => !newIdSet.has(r.id)),
      ]
      const seen = new Set<number>()
      previousRecipes.value = merged.filter(r => {
        if (seen.has(r.id)) return false
        seen.add(r.id)
        return true
      }).slice(0, CONST.DEFAULT_MAX_PREVIOUS_RECIPES)

      try {
        localStorage.setItem(CONST.LS_MENU_HISTORY, JSON.stringify(previousRecipes.value))
      } catch {
        // storage full
      }
    }

    menuVersion.value = data.version
  }

  // Debounced menu load
  function debouncedLoadMenu() {
    if (_loadMenuInFlight.value) {
      _loadMenuPending.value = true
      return
    }
    _loadMenuInFlight.value = true
    const clearOthers = _pendingClearOthers.value
    _pendingClearOthers.value = false
    loadMenu({ clearOthers }).finally(() => {
      _loadMenuInFlight.value = false
      if (_loadMenuPending.value) {
        _loadMenuPending.value = false
        debouncedLoadMenu()
      }
    })
  }

  async function loadIconMappings() {
    try {
      const res = await fetch('/api/icon-mappings')
      if (res.ok) {
        iconMappings.value = await res.json()
      }
    } catch (e) {
      console.warn('Failed to load icon mappings:', e)
    }
  }

  // ---- Generation ----

  async function generate(profileName: string) {
    if (state.value === 'generating') return
    activeProfile.value = profileName
    state.value = 'generating'
    errorMessage.value = ''

    try {
      const res = await fetch(
        `/api/generate/${encodeURIComponent(profileName)}`,
        { method: 'POST' },
      )
      if (res.status === 202 || res.status === 409) {
        startStatusPolling()
      } else {
        state.value = 'error'
        errorMessage.value = 'Failed to start generation'
      }
    } catch {
      state.value = 'error'
      errorMessage.value = 'Cannot reach server'
    }
  }

  function retryGeneration() {
    if (activeProfile.value) {
      generate(activeProfile.value)
    } else {
      const profilesStore = useProfilesStore()
      const visible = profilesStore.visibleProfiles
      if (visible.length > 0) {
        generate(visible[0].name)
      } else {
        loadMenu()
      }
    }
  }

  function startStatusPolling() {
    if (_statusPollId) clearInterval(_statusPollId)
    _statusPollId = setInterval(async () => {
      try {
        const res = await fetch('/api/status')
        if (!res.ok) return
        const status: GenerationStatus = await res.json()

        if (status.state === 'complete' || status.state === 'idle') {
          clearInterval(_statusPollId!)
          _statusPollId = null
          await loadMenuResult()
        } else if (status.state === 'error') {
          clearInterval(_statusPollId!)
          _statusPollId = null
          state.value = 'error'
          errorMessage.value = status.error || 'Generation failed'
        }
      } catch {
        // Keep polling
      }
    }, CONST.STATUS_POLL_MS)
  }

  async function loadMenuResult() {
    try {
      const res = await fetch('/api/menu')
      if (res.ok) {
        const data: Menu = await res.json()
        if (data.version && data.version === menuVersion.value) {
          _targetShelf.value = null
          state.value = 'ready'
          return
        }
        const target = _targetShelf.value || data.profile || activeProfile.value || 'Menu'
        _targetShelf.value = null
        addShelf(target, data.recipes || [], data.generated_at)
        activeDeckName.value = target
        generatedAt.value = data.generated_at || ''
        menuVersion.value = data.version
        currentRecipes.value = data.recipes || []
        saveShelves()
        carouselScrollTrigger.value++
        state.value = 'ready'
      } else if (res.status === 404) {
        state.value = 'ready'
      } else {
        state.value = 'error'
        errorMessage.value = 'Failed to load menu'
      }
    } catch {
      state.value = 'error'
      errorMessage.value = 'Cannot reach server'
    }
  }

  // ---- Category / Profile Actions ----

  function selectCategory(name: string) {
    _targetShelf.value = name
    categoryPanelOpen.value = null
    generate(name)
  }

  function toggleCategoryPanel(id: string | number) {
    categoryPanelOpen.value = categoryPanelOpen.value === id ? null : id
  }

  function discover() {
    const profilesStore = useProfilesStore()
    const settingsStore = useSettingsStore()
    const available = profilesStore.visibleProfiles
    if (available.length === 0) return

    // Check discover generation limit
    const maxGens = settingsStore.settings?.max_discover_generations ?? CONST.DEFAULT_MAX_DISCOVER_GENS
    try {
      const count = parseInt(localStorage.getItem(CONST.LS_DISCOVER_GENS) || '0', 10)
      if (count >= maxGens) return
      localStorage.setItem(CONST.LS_DISCOVER_GENS, String(count + 1))
    } catch {
      // ignore localStorage errors
    }

    const pick = available.find(p => p.is_default || p.default)
      || available[Math.floor(Math.random() * available.length)]
    _targetShelf.value = pick.name
    generate(pick.name)
  }

  // ---- Shelf Management ----

  function addShelf(name: string, recipeList: Recipe[], genAt?: string) {
    _carouselCache = null
    _carouselCacheKey = null
    const generation: ShelfGeneration = {
      recipes: recipeList,
      generatedAt: genAt || new Date().toISOString(),
    }
    const existing = shelves.value.find(s => s.name === name)
    if (existing) {
      existing.generations.unshift(generation)
      if (existing.generations.length > CONST.MAX_SHELF_GENERATIONS) {
        existing.generations = existing.generations.slice(0, CONST.MAX_SHELF_GENERATIONS)
      }
      existing.currentIndex = 0
      const idx = shelves.value.indexOf(existing)
      if (idx > 0) {
        shelves.value.splice(idx, 1)
        shelves.value.unshift(existing)
      }
    } else {
      shelves.value.unshift({ name, generations: [generation], currentIndex: 0 })
    }
    saveShelves()
  }

  function removeShelf(name: string) {
    confirmModal.value = {
      show: true,
      title: 'Remove Shelf?',
      message: `Remove the ${name} shelf? This will clear its recipe history.`,
      confirmText: 'Remove',
      onConfirm: () => {
        if (activeDeckName.value === name) {
          const remaining = shelves.value.filter(s => s.name !== name)
          activeDeckName.value = remaining.length > 0 ? remaining[0].name : null
        }
        shelves.value = shelves.value.filter(s => s.name !== name)
        saveShelves()
        confirmModal.value.show = false
      },
    }
  }

  function activateDeck(name: string) {
    activeDeckName.value = name
    carouselScrollTrigger.value++
    saveShelves()
  }

  function saveShelves() {
    try {
      localStorage.setItem(CONST.LS_MENU_SHELVES, JSON.stringify(shelves.value))
      localStorage.setItem(CONST.LS_ACTIVE_DECK, JSON.stringify(activeDeckName.value))
    } catch {
      // storage full
    }
  }

  function loadShelves() {
    try {
      const saved = localStorage.getItem(CONST.LS_MENU_SHELVES)
      if (!saved) return
      const parsed = JSON.parse(saved) as Shelf[]
      if (!Array.isArray(parsed)) return
      shelves.value = parsed.filter(s =>
        s.name && Array.isArray(s.generations) && s.generations.length > 0,
      ).map(s => ({
        name: s.name,
        generations: s.generations.slice(0, CONST.MAX_SHELF_GENERATIONS),
        currentIndex: Math.min(s.currentIndex || 0, s.generations.length - 1),
      }))
    } catch {
      // ignore corrupt data
    }
    try {
      const savedDeck = localStorage.getItem(CONST.LS_ACTIVE_DECK)
      if (savedDeck) {
        const deckName = JSON.parse(savedDeck) as string | null
        if (deckName === null || shelves.value.find(s => s.name === deckName)) {
          activeDeckName.value = deckName
        }
      }
    } catch {
      // ignore corrupt data
    }
  }

  // ---- Generation Navigation ----

  function prevGeneration(shelfName: string) {
    const shelf = shelves.value.find(s => s.name === shelfName)
    if (!shelf || shelf.generations.length === 0) return
    shelf.currentIndex = Math.min((shelf.currentIndex || 0) + 1, shelf.generations.length - 1)
    _carouselCache = null
    _carouselCacheKey = null
    carouselScrollTrigger.value++
    saveShelves()
  }

  function nextGeneration(shelfName: string) {
    const shelf = shelves.value.find(s => s.name === shelfName)
    if (!shelf || shelf.generations.length === 0) return
    shelf.currentIndex = Math.max((shelf.currentIndex || 0) - 1, 0)
    _carouselCache = null
    _carouselCacheKey = null
    carouselScrollTrigger.value++
    saveShelves()
  }

  function goToGeneration(shelfName: string, index: number) {
    const shelf = shelves.value.find(s => s.name === shelfName)
    if (!shelf || shelf.generations.length === 0) return
    shelf.currentIndex = Math.max(0, Math.min(index, shelf.generations.length - 1))
    _carouselCache = null
    _carouselCacheKey = null
    carouselScrollTrigger.value++
    saveShelves()
  }

  function currentGeneration(shelf: Shelf): Recipe[] {
    if (!shelf.generations || shelf.generations.length === 0) return []
    const idx = shelf.currentIndex || 0
    return shelf.generations[idx].recipes
  }

  function getShelfGenerations() {
    const shelf = activeShelf.value ?? (shelves.value.length > 0 ? shelves.value[0] : null)
    if (!shelf?.generations?.length) return null
    return {
      profile: shelf.name,
      generations: shelf.generations.map(g => {
        const valid = (g.recipes || []).filter(r => r && r.id)
        return {
          recipes: valid,
          recipeCount: valid.length,
          preview: valid.slice(0, 3),
        }
      }),
    }
  }

  function deckPreview(shelf: Shelf): Recipe | null {
    const recipeList = currentGeneration(shelf)
    return recipeList.length > 0 ? recipeList[0] : null
  }

  // ---- Recipe Modal ----

  function openRecipe(recipe: Recipe) {
    selectedRecipe.value = recipe
  }

  function closeRecipe() {
    selectedRecipe.value = null
  }

  // ---- Ratings ----

  async function setRating(recipeId: number, rating: number, userName: string | null) {
    try {
      const res = await fetch(`/api/recipe/${recipeId}/rating`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating, customer_name: userName }),
      })
      if (res.ok) {
        const updateRating = (list: Recipe[]) => {
          for (const r of list) {
            if (r.id === recipeId) r.rating = rating
          }
        }
        updateRating(currentRecipes.value)
        updateRating(previousRecipes.value)
        // Update in shelves too
        for (const shelf of shelves.value) {
          for (const gen of shelf.generations) {
            updateRating(gen.recipes)
          }
        }
        if (selectedRecipe.value?.id === recipeId) {
          selectedRecipe.value.rating = rating
        }
      }
    } catch (e) {
      console.warn('Failed to set rating:', e)
    }
  }

  // ---- Name Prompt ----

  function loadRecentNames() {
    try {
      recentNames.value = JSON.parse(localStorage.getItem(CONST.LS_RECENT_NAMES) || '[]')
    } catch {
      recentNames.value = []
    }
  }

  function saveRecentName(name: string) {
    try {
      let names: string[] = JSON.parse(localStorage.getItem(CONST.LS_RECENT_NAMES) || '[]')
      names = names.filter(n => n.toLowerCase() !== name.toLowerCase())
      names.unshift(name)
      if (names.length > CONST.MAX_RECENT_NAMES) names = names.slice(0, CONST.MAX_RECENT_NAMES)
      localStorage.setItem(CONST.LS_RECENT_NAMES, JSON.stringify(names))
      recentNames.value = names
    } catch {
      // storage full
    }
  }

  // ---- Ordering ----

  async function placeOrder(recipe: Recipe, userName: string | null) {
    try {
      const res = await fetch('/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipe_id: recipe.id,
          recipe_name: recipe.name,
          customer_name: userName,
        }),
      })
      if (res.ok) {
        const order = (await res.json()) as { id: number }
        pendingOrder.value = { id: order.id, recipe_name: recipe.name, status: 'received' }
        orderConfirm.value = recipe.id
        _connectCustomerSSE(order.id)
        return order.id
      }
    } catch (e) {
      console.warn('Failed to place order:', e)
    }
    return null
  }

  function _connectCustomerSSE(orderId: number) {
    if (_customerSSE) _customerSSE.close()
    const es = new EventSource(`/api/orders/customer-stream?order_id=${orderId}`)
    _customerSSE = es
    es.addEventListener('status_update', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as { order_id: number; status: string }
        if (data.order_id === orderId && pendingOrder.value) {
          pendingOrder.value = { ...pendingOrder.value, status: data.status }
          if (data.status === 'ready') {
            const settingsStore = useSettingsStore()
            const toastMs = settingsStore.toastSeconds * 1000
            setTimeout(() => {
              pendingOrder.value = null
              orderConfirm.value = null
              es.close()
              _customerSSE = null
            }, toastMs * 3)
          }
        }
      } catch {
        // ignore malformed events
      }
    })
    es.onerror = () => {
      // Reconnect handled by browser EventSource
    }
  }

  function dismissPendingOrder() {
    pendingOrder.value = null
    orderConfirm.value = null
    if (_customerSSE) {
      _customerSSE.close()
      _customerSSE = null
    }
  }

  // ---- Meal Plan ----

  async function openMealPlanSave() {
    navOpen.value = false
    const info = getShelfGenerations()
    mealPlanSave.value.profile = info?.profile || null
    mealPlanSave.value.generations = info?.generations?.map(g => ({
      recipes: g.recipes,
      generatedAt: '',
    })) || []
    mealPlanSave.value.selectedGen = 0
    mealPlanSave.value.expandedGen = null
    mealPlanSave.value.date = new Date().toISOString().slice(0, 10)
    mealPlanSave.value.saving = false
    mealPlanSave.value.selectedUsers = []
    mealPlanSave.value.show = true
    try {
      const [mtRes, uRes] = await Promise.all([
        fetch('/api/meal-types'),
        fetch('/api/users'),
      ])
      if (mtRes.ok) {
        const mtData = await mtRes.json()
        mealPlanSave.value.mealTypes = Array.isArray(mtData) ? mtData : (mtData.results || [])
        if (!mealPlanSave.value.mealTypeId && mealPlanSave.value.mealTypes.length) {
          mealPlanSave.value.mealTypeId = mealPlanSave.value.mealTypes[0].id
        }
      }
      if (uRes.ok) {
        const uData = await uRes.json()
        mealPlanSave.value.users = Array.isArray(uData) ? uData : (uData.results || [])
      }
    } catch (e) {
      console.warn('Failed to load meal plan options:', e)
    }
  }

  async function submitMealPlanSave() {
    if (mealPlanSave.value.saving) return
    mealPlanSave.value.saving = true
    try {
      const gen = mealPlanSave.value.generations[mealPlanSave.value.selectedGen]
      const payload = {
        date: mealPlanSave.value.date,
        meal_type_id: mealPlanSave.value.mealTypeId,
        shared: mealPlanSave.value.selectedUsers,
        recipes: gen?.recipes?.map(r => ({ id: r.id, name: r.name })) ?? [],
      }
      const res = await fetch('/api/meal-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (res.ok) {
        mealPlanSave.value.show = false
        mealPlanToast.value = true
        setTimeout(() => { mealPlanToast.value = false }, CONST.DEFAULT_TOAST_SECONDS * 1000)
      }
    } catch {
      // silent
    } finally {
      mealPlanSave.value.saving = false
    }
  }

  // ---- Kiosk PIN ----

  async function submitKioskPin() {
    kioskPinError.value = ''
    try {
      const res = await fetch('/api/settings/verify-pin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin: kioskPinValue.value }),
      })
      if (res.ok) {
        const data = (await res.json()) as { valid: boolean; token?: string }
        if (data.valid) {
          if (data.token) {
            sessionStorage.setItem(CONST.SS_ADMIN_TOKEN, data.token)
            sessionStorage.setItem(CONST.SS_ADMIN_TOKEN_TS, String(Date.now()))
          }
          showKioskPin.value = false
          window.location.href = '/admin'
        } else {
          kioskPinError.value = 'Incorrect PIN'
          kioskPinValue.value = ''
        }
      } else {
        kioskPinError.value = 'Failed to verify PIN'
      }
    } catch {
      kioskPinError.value = 'Cannot reach server'
    }
  }

  // ---- SSE handlers ----

  function handleSSEGenerating() {
    // Only show spinner on kiosk displays
    const settingsStore = useSettingsStore()
    if (settingsStore.kioskEnabled && state.value !== 'generating') {
      state.value = 'generating'
    }
  }

  function handleSSEMenuUpdated(clearOthers: boolean) {
    _pendingClearOthers.value = clearOthers
    debouncedLoadMenu()
  }

  function handleSSEMenuCleared(isKiosk: boolean) {
    if (isKiosk) {
      shelves.value = []
      activeDeckName.value = null
      menuVersion.value = null
      currentRecipes.value = []
      generatedAt.value = ''
      saveShelves()
      state.value = 'ready'
    }
  }

  function handleSSEConnected(serverVersion: string) {
    if (appVersion.value && serverVersion && serverVersion !== appVersion.value) {
      location.reload()
      return
    }
    debouncedLoadMenu()
  }

  // ---- Cleanup ----

  function stopStatusPolling() {
    if (_statusPollId) {
      clearInterval(_statusPollId)
      _statusPollId = null
    }
  }

  function cleanupCustomerSSE() {
    if (_customerSSE) {
      _customerSSE.close()
      _customerSSE = null
    }
  }

  // ---- Init helpers ----

  function restorePreviousRecipes() {
    try {
      const saved = localStorage.getItem(CONST.LS_MENU_HISTORY)
      if (saved) previousRecipes.value = JSON.parse(saved)
    } catch {
      // ignore
    }
  }

  return {
    // State
    state,
    errorMessage,
    appVersion,
    currentRecipes,
    previousRecipes,
    recipes,
    warnings,
    relaxedConstraints,
    menuVersion,
    generatedAt,
    activeProfile,
    shelves,
    activeDeckName,
    iconMappings,
    navOpen,
    categoryPanelOpen,

    // Recipe modal
    selectedRecipe,
    orderConfirm,
    pendingOrder,

    // Name prompt
    namePrompt,
    recentNames,

    // Confirm modal
    confirmModal,

    // Meal plan
    mealPlanSave,
    mealPlanToast,

    // Kiosk
    showKioskPin,
    showKioskPinText,
    kioskPinValue,
    kioskPinError,

    // Carousel scroll trigger
    carouselScrollTrigger,

    // Computed
    isGenerating,
    isReady,
    isLoading,
    hasMenu,
    activeShelf,
    mainCarouselRecipes,

    // Actions
    loadHealth,
    loadMenu,
    loadMenuResult,
    loadIconMappings,
    loadShelves,
    loadRecentNames,
    restorePreviousRecipes,
    generate,
    retryGeneration,
    selectCategory,
    toggleCategoryPanel,
    discover,
    addShelf,
    removeShelf,
    activateDeck,
    saveShelves,
    prevGeneration,
    nextGeneration,
    goToGeneration,
    currentGeneration,
    getShelfGenerations,
    deckPreview,
    openRecipe,
    closeRecipe,
    setRating,
    saveRecentName,
    placeOrder,
    dismissPendingOrder,
    openMealPlanSave,
    submitMealPlanSave,
    submitKioskPin,
    debouncedLoadMenu,
    stopStatusPolling,
    cleanupCustomerSSE,

    // SSE handlers
    handleSSEGenerating,
    handleSSEMenuUpdated,
    handleSSEMenuCleared,
    handleSSEConnected,

    // Internal
    _targetShelf,
    flattenGenerations,
  }
})
