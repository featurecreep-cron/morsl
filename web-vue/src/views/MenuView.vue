<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useMenuStore } from '@/stores/menu'
import { useProfilesStore } from '@/stores/profiles'
import { useSettingsStore } from '@/stores/settings'
import { useSSE } from '@/composables/useSSE'
import { useKiosk } from '@/composables/useKiosk'
import { useTheme } from '@/composables/useTheme'
import { prefetchBrandSvg, getLoadingIconHtml, STOCK_ICON_SVG, inlineSvg } from '@/utils/icons'
import { formatMenuDate } from '@/utils/formatting'

import CategoryBar from '@/components/menu/CategoryBar.vue'
import WarningsBanner from '@/components/menu/WarningsBanner.vue'
import DeckStrip from '@/components/menu/DeckStrip.vue'
import Carousel from '@/components/menu/Carousel.vue'
import GeneratingOverlay from '@/components/menu/GeneratingOverlay.vue'
import RecipeModal from '@/components/menu/RecipeModal.vue'
import NamePrompt from '@/components/shared/NamePrompt.vue'
import ConfirmModal from '@/components/shared/ConfirmModal.vue'
import Toast from '@/components/shared/Toast.vue'
import MealPlanSave from '@/components/shared/MealPlanSave.vue'

const menu = useMenuStore()
const profiles = useProfilesStore()
const settings = useSettingsStore()
const { apply: applyTheme } = useTheme()

// Template refs
const headerRef = ref<HTMLElement | null>(null)
const logoRef = ref<HTMLElement | null>(null)
const kioskPinInput = ref<HTMLInputElement | null>(null)

// Loading icon HTML (computed from settings)
const loadingIconHtml = computed(() =>
  getLoadingIconHtml(settings.loadingIconUrl, settings.loaded) || STOCK_ICON_SVG,
)

// SSE connection
const { connect: connectSSE, disconnect: disconnectSSE } = useSSE({
  url: '/api/menu/stream',
  onGenerating: () => menu.handleSSEGenerating(),
  onMenuUpdated: (clearOthers) => menu.handleSSEMenuUpdated(clearOthers),
  onMenuCleared: () => menu.handleSSEMenuCleared(settings.kioskEnabled),
  onConnected: (version) => menu.handleSSEConnected(version),
})

// Kiosk gesture setup
const kiosk = useKiosk({
  gesture: settings.kioskGesture,
  enabled: settings.kioskEnabled,
  headerRef,
  onActivate: () => kioskAdminAccess(),
})

// Visibility-based polling
let visibilityPollId: ReturnType<typeof setInterval> | null = null

function onVisibilityChange() {
  if (document.visibilityState === 'visible') {
    menu.debouncedLoadMenu()
  }
}

// Kiosk admin access — PIN gate or direct nav
function kioskAdminAccess(url?: string) {
  menu.navOpen = false
  if (settings.kioskEnabled && settings.adminPinEnabled && settings.hasPin) {
    menu.showKioskPin = true
    menu.kioskPinValue = ''
    menu.kioskPinError = ''
    nextTick(() => kioskPinInput.value?.focus())
  } else {
    window.location.href = url || '/admin'
  }
}

// Quick save to meal plan (no dialog)
async function quickSaveMealPlan() {
  menu.navOpen = false
  const info = menu.getShelfGenerations()
  if (!info?.generations?.length) return
  const gen = info.generations[0]
  try {
    const mtRes = await fetch('/api/meal-types')
    let mealTypeId: number | null = null
    if (mtRes.ok) {
      const mealTypes = await mtRes.json()
      const arr = Array.isArray(mealTypes) ? mealTypes : (mealTypes.results || [])
      if (arr.length > 0) mealTypeId = arr[0].id
    }
    const res = await fetch('/api/meal-plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        date: new Date().toISOString().slice(0, 10),
        meal_type_id: mealTypeId,
        shared: [],
        recipes: gen.recipes.map(r => ({ id: r.id, name: r.name })),
      }),
    })
    if (res.ok) {
      menu.mealPlanToast = true
      setTimeout(() => { menu.mealPlanToast = false }, settings.toastSeconds * 1000)
    }
  } catch {
    // silent
  }
}

// Escape key handler
function onEscapeKey(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    menu.closeRecipe()
  }
}

// Apply logo to header
async function applyLogo() {
  if (!settings.logoUrl || !logoRef.value) return
  await inlineSvg(settings.logoUrl, logoRef.value)
}

// Auto-generate from URL param
function checkAutoGenerate() {
  const params = new URLSearchParams(window.location.search)
  const profile = params.get('generate')
  if (profile) {
    // Clean up URL
    const url = new URL(window.location.href)
    url.searchParams.delete('generate')
    window.history.replaceState({}, '', url.toString())
    menu.generate(profile)
  }
}

// Initialize everything
onMounted(async () => {
  // Load persisted state first
  menu.loadShelves()
  menu.restorePreviousRecipes()
  menu.loadRecentNames()

  // Initial data fetch (parallel)
  await Promise.all([
    menu.loadHealth(),
    settings.load(),
    profiles.load(),
    profiles.loadCategories(),
    menu.loadIconMappings(),
  ])

  // Apply theme
  applyTheme(settings.theme)

  // Prefetch brand SVG for logo
  if (settings.logoUrl) {
    await prefetchBrandSvg(settings.logoUrl)
    await applyLogo()
  }

  // Load menu data
  await menu.loadMenu()

  // Connect SSE
  connectSSE()

  // Kiosk gesture setup
  nextTick(() => kiosk.setup())

  // Visibility listener
  document.addEventListener('visibilitychange', onVisibilityChange)

  // Escape key
  document.addEventListener('keydown', onEscapeKey)

  // Check auto-generate
  checkAutoGenerate()
})

onUnmounted(() => {
  disconnectSSE()
  menu.stopStatusPolling()
  document.removeEventListener('visibilitychange', onVisibilityChange)
  document.removeEventListener('keydown', onEscapeKey)
  if (visibilityPollId) {
    clearInterval(visibilityPollId)
    visibilityPollId = null
  }
  kiosk.cleanup()
})

// Watch theme changes
watch(() => settings.theme, (newTheme) => {
  applyTheme(newTheme)
})

// Watch logo changes
watch(() => settings.logoUrl, async () => {
  if (settings.logoUrl) {
    await prefetchBrandSvg(settings.logoUrl)
    await applyLogo()
  }
})

// Watch kiosk PIN modal — focus input on open
watch(() => menu.showKioskPin, (show) => {
  if (show) {
    nextTick(() => kioskPinInput.value?.focus())
  }
})
</script>

<template>
  <div class="menu-page" :class="{ 'is-kiosk': settings.kioskEnabled }">

    <!-- Loading overlay (app startup only) -->
    <Transition name="fade">
      <div v-if="menu.isLoading" class="loading-overlay">
        <div class="loading-content">
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div class="shaker-icon" v-html="loadingIconHtml" />
          <p>Loading...</p>
        </div>
      </div>
    </Transition>

    <!-- Header: branding centered -->
    <header ref="headerRef" class="menu-header">
      <div class="menu-brand">
        <div
          v-if="settings.showLogo && settings.logoUrl"
          ref="logoRef"
          class="menu-logo"
          aria-hidden="true"
        />
        <div class="menu-brand-text">
          <h1 class="menu-title">{{ settings.appName }}</h1>
          <p v-if="settings.sloganHeader" class="menu-slogan">{{ settings.sloganHeader }}</p>
        </div>
      </div>
    </header>

    <!-- Category bar -->
    <CategoryBar />

    <!-- Warnings / relaxed constraints banner -->
    <WarningsBanner
      :warnings="menu.warnings"
      :relaxed-constraints="menu.relaxedConstraints"
    />

    <!-- Generating overlay -->
    <GeneratingOverlay :visible="menu.isGenerating" />

    <!-- Content area: deck strip + carousel -->
    <div v-show="menu.isReady || menu.isGenerating" class="content-area">

      <!-- Deck strip tabs -->
      <DeckStrip
        v-if="menu.shelves.length > 1"
        :shelves="menu.shelves"
        :active-deck-name="menu.activeDeckName"
        :item-noun="settings.itemNoun"
      />

      <!-- Main carousel -->
      <main class="carousel-container">
        <!-- Empty state: no profiles at all -->
        <div
          v-if="!profiles.hasProfiles && menu.isReady"
          class="empty-state"
        >
          <h2>No profiles yet</h2>
          <p>Create a profile to start generating menus</p>
          <a href="/admin#profiles" class="empty-state-btn">Create Profile</a>
        </div>

        <!-- Empty state: profiles exist, visible — tap to generate -->
        <div
          v-else-if="profiles.visibleProfiles.length > 0
            && menu.mainCarouselRecipes.length === 0
            && menu.shelves.length === 0
            && menu.isReady"
          class="empty-state"
        >
          <h2>No menu generated</h2>
          <p>Tap a profile above to generate your menu</p>
        </div>

        <!-- Empty state: profiles exist but none visible -->
        <div
          v-else-if="profiles.hasProfiles
            && profiles.visibleProfiles.length === 0
            && menu.mainCarouselRecipes.length === 0
            && menu.shelves.length === 0
            && menu.isReady"
          class="empty-state"
        >
          <h2>No menu available</h2>
          <p>Generate a menu from the admin page</p>
          <a href="/admin#generate" class="empty-state-btn">Go to Admin</a>
        </div>

        <!-- Carousel -->
        <Carousel
          v-if="menu.mainCarouselRecipes.length > 0"
          :items="menu.mainCarouselRecipes"
        />

        <!-- Footer slogan (inside carousel-container) -->
        <footer
          v-if="(menu.isReady || menu.isGenerating) && (settings.sloganFooter || settings.sloganHeader)"
          class="menu-footer"
        >
          <p class="footer-slogan">{{ settings.sloganFooter || settings.sloganHeader }}</p>
        </footer>
      </main>
    </div>

    <!-- Top-right corner: date + QR -->
    <div class="top-right-corner">
      <span
        v-if="menu.generatedAt && menu.mainCarouselRecipes.length > 0"
        class="corner-date"
      >{{ formatMenuDate(menu.generatedAt) }}</span>
    </div>

    <!-- Error state -->
    <div v-if="menu.state === 'error'" class="error-state">
      <p>{{ menu.errorMessage || 'Something went wrong' }}</p>
      <button class="retry-btn" @click="menu.retryGeneration()">Try Again</button>
    </div>

    <!-- Hamburger navigation -->
    <button
      v-if="!settings.kioskEnabled || settings.kioskGesture === 'menu'"
      class="nav-hamburger"
      :aria-label="menu.navOpen ? 'Close navigation menu' : 'Open navigation menu'"
      :aria-expanded="menu.navOpen"
      @click="menu.navOpen = !menu.navOpen"
    >&#9776;</button>

    <Transition name="nav-slide">
      <div
        v-if="menu.navOpen"
        class="nav-menu"
        role="menu"
        @click.stop
      >
        <a
          href="/admin"
          class="nav-menu-item"
          role="menuitem"
          @click.prevent="kioskAdminAccess()"
        >Admin</a>
        <a
          v-if="!settings.kioskEnabled"
          href="/admin#weekly"
          class="nav-menu-item"
          role="menuitem"
          @click.prevent="kioskAdminAccess('/admin#weekly')"
        >Plan Your Week</a>
        <a
          v-if="menu.mainCarouselRecipes.length > 0"
          href="#"
          class="nav-menu-item"
          role="menuitem"
          @click.prevent="quickSaveMealPlan()"
        >Quick Save to Meal Plan</a>
        <a
          v-if="menu.mainCarouselRecipes.length > 0"
          href="#"
          class="nav-menu-item"
          role="menuitem"
          @click.prevent="menu.openMealPlanSave()"
        >Save to Meal Plan...</a>
        <span v-if="menu.appVersion" class="nav-menu-version">{{ menu.appVersion }}</span>
      </div>
    </Transition>

    <!-- Click-outside handler for nav menu -->
    <div
      v-if="menu.navOpen"
      class="nav-backdrop"
      @click="menu.navOpen = false"
    />

    <!-- Recipe detail modal -->
    <RecipeModal />

    <!-- Name prompt (ordering + rating) -->
    <NamePrompt />

    <!-- Confirmation modal -->
    <ConfirmModal />

    <!-- Order status toast -->
    <Toast
      :visible="!!menu.pendingOrder"
      :message="
        menu.pendingOrder
          ? menu.pendingOrder.recipe_name + ' \u2014 '
            + (menu.pendingOrder.status === 'ready' ? 'Ready!' : 'Order received')
          : ''
      "
      :variant="menu.pendingOrder?.status === 'ready' ? 'success' : 'default'"
      :dismissible="true"
      @dismiss="menu.dismissPendingOrder()"
    />

    <!-- Order confirmation toast (fallback when no pending order) -->
    <Toast
      :visible="!!menu.orderConfirm && !menu.pendingOrder"
      message="Request placed!"
      variant="success"
    />

    <!-- Meal plan save toast -->
    <Toast
      :visible="menu.mealPlanToast"
      message="Saved to meal plan!"
      variant="success"
    />

    <!-- Meal plan save bottom sheet -->
    <MealPlanSave />

    <!-- Kiosk PIN modal -->
    <Teleport to="body">
      <div
        v-if="menu.showKioskPin"
        class="pin-gate-backdrop"
        @click.self="menu.showKioskPin = false"
      >
        <div class="pin-gate-modal" role="dialog" aria-modal="true">
          <h2 class="pin-gate-title">Admin Access</h2>
          <p class="pin-gate-subtitle">Enter PIN to continue</p>
          <form @submit.prevent="menu.submitKioskPin()">
            <div class="pin-gate-input-wrap">
              <input
                ref="kioskPinInput"
                v-model="menu.kioskPinValue"
                :type="menu.showKioskPinText ? 'tel' : 'password'"
                class="pin-gate-input"
                placeholder="PIN"
                maxlength="4"
                pattern="[0-9]*"
                autocomplete="off"
                inputmode="numeric"
                @input="() => { if (menu.kioskPinValue.length >= 4) menu.submitKioskPin() }"
              >
              <button
                type="button"
                class="pin-gate-show-toggle"
                tabindex="-1"
                :title="menu.showKioskPinText ? 'Hide PIN' : 'Show PIN'"
                @click="menu.showKioskPinText = !menu.showKioskPinText"
              >
                <span v-if="!menu.showKioskPinText">&#128065;</span>
                <span v-else>&#128064;</span>
              </button>
            </div>
            <p v-if="menu.kioskPinError" class="pin-gate-error">{{ menu.kioskPinError }}</p>
            <button type="submit" class="pin-gate-submit">Unlock</button>
          </form>
          <button class="pin-gate-back" @click="menu.showKioskPin = false">Cancel</button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* ---- Page layout ---- */
.menu-page {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  background: var(--bg-color);
  color: var(--text-color);
  position: relative;
  overflow-x: hidden;
}

/* ---- Loading overlay ---- */
.loading-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: var(--bg-color, #0d0d0d);
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  color: var(--text-muted);
  font-family: var(--body-font);
  font-size: 0.9rem;
}

.loading-content .shaker-icon {
  width: 6rem;
  height: 6rem;
  color: var(--accent-color);
  animation: shake 0.6s ease-in-out infinite;
}

@keyframes shake {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(-15deg); }
  75% { transform: rotate(15deg); }
}

/* ---- Header ---- */
.menu-header {
  padding: 1.5rem 1rem 0.5rem;
  text-align: center;
  flex: 0 0 auto;
  user-select: none;
}

.menu-brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.menu-logo {
  width: 48px;
  height: 48px;
  color: var(--accent-color);
}

.menu-logo :deep(svg) {
  width: 100%;
  height: 100%;
  display: block;
}

.menu-brand-text { text-align: center; }

.menu-title {
  font-family: var(--heading-font);
  font-size: var(--title-size, 3rem);
  font-weight: 400;
  margin: 0;
  text-shadow: var(--title-shadow);
  color: var(--text-color);
}

.menu-slogan {
  font-family: var(--body-font);
  font-size: 0.85rem;
  color: var(--text-muted);
  margin: 0.25rem 0 0;
  font-style: italic;
}

/* ---- Content area ---- */
.content-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.carousel-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* ---- Empty states ---- */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2rem;
  text-align: center;
}

.empty-state h2 {
  font-family: var(--heading-font);
  font-size: 1.3rem;
  color: var(--accent-color);
  margin: 0;
}

.empty-state p {
  font-size: 0.9rem;
  color: var(--text-muted);
  margin: 0;
}

.empty-state-btn {
  background: var(--btn-bg);
  color: var(--btn-text);
  border: 1px solid var(--btn-border);
  border-radius: var(--card-radius, 0.75rem);
  padding: 0.6rem 1.5rem;
  font-family: var(--body-font);
  font-size: 0.9rem;
  text-decoration: none;
  display: inline-block;
}

.empty-state-btn:hover {
  background: var(--btn-active-bg);
  color: var(--btn-active-text);
}

/* ---- Footer ---- */
.menu-footer {
  flex: 0 0 auto;
  text-align: center;
  padding: 1.5rem 1rem;
}

.footer-slogan {
  font-family: var(--body-font);
  font-size: 0.8rem;
  color: var(--text-muted);
  margin: 0;
  font-style: italic;
}

/* ---- Top-right corner ---- */
.top-right-corner {
  position: fixed;
  top: 0.75rem;
  right: 0.75rem;
  z-index: 50;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.5rem;
  pointer-events: none;
}

.corner-date {
  font-family: var(--body-font);
  font-size: 0.65rem;
  color: var(--text-muted);
  opacity: 0.6;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* ---- Error state ---- */
.error-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 2rem;
  text-align: center;
  color: var(--text-color);
}

.error-state p {
  font-size: 0.95rem;
  color: var(--text-muted);
  margin: 0;
}

.retry-btn {
  background: var(--btn-bg);
  color: var(--btn-text);
  border: 1px solid var(--btn-border);
  border-radius: var(--card-radius, 0.75rem);
  padding: 0.6rem 1.5rem;
  font-family: var(--body-font);
  font-size: 0.9rem;
  cursor: pointer;
}

.retry-btn:hover {
  background: var(--btn-active-bg);
  color: var(--btn-active-text);
}

/* ---- Hamburger navigation ---- */
.nav-hamburger {
  position: fixed;
  top: 0.75rem;
  left: 0.75rem;
  z-index: 1200;
  background: var(--btn-bg, rgba(255,255,255,0.08));
  border: 1px solid var(--btn-border, rgba(255,255,255,0.1));
  border-radius: 8px;
  color: var(--text-muted);
  font-size: 1.3rem;
  cursor: pointer;
  padding: 0.35rem 0.5rem;
  line-height: 1;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.nav-hamburger:hover { opacity: 1; }

.nav-menu {
  position: fixed;
  top: 3rem;
  left: 0.75rem;
  z-index: 1200;
  background: var(--modal-bg, #1a1a1a);
  border: 1px solid var(--card-border, rgba(255,255,255,0.1));
  border-radius: 0.75rem;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  padding: 0.5rem 0;
  min-width: 180px;
}

.nav-menu-item {
  display: block;
  padding: 0.6rem 1rem;
  font-family: var(--body-font);
  font-size: 0.85rem;
  color: var(--text-color);
  text-decoration: none;
  transition: background 0.15s;
}

.nav-menu-item:hover {
  background: var(--btn-active-bg, rgba(255,255,255,0.05));
}

.nav-menu-version {
  display: block;
  padding: 0.4rem 1rem;
  font-size: 0.7rem;
  color: var(--text-muted);
  border-top: 1px solid var(--card-border, rgba(255,255,255,0.1));
  margin-top: 0.25rem;
}

.nav-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1100;
}

/* ---- Kiosk PIN gate ---- */
.pin-gate-backdrop {
  position: fixed;
  inset: 0;
  background: var(--overlay-bg, rgba(0,0,0,0.7));
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1300;
  padding: 1rem;
}

.pin-gate-modal {
  background: var(--modal-bg, #1a1a1a);
  border: 1px solid var(--card-border, rgba(255,255,255,0.1));
  border-radius: var(--modal-radius, 0.75rem);
  box-shadow: var(--card-shadow, none);
  padding: 2rem;
  max-width: 320px;
  width: 90%;
  text-align: center;
}

.pin-gate-title {
  font-family: var(--heading-font);
  font-size: 1.4rem;
  color: var(--accent-color);
  margin: 0 0 0.25rem;
}

.pin-gate-subtitle {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin: 0 0 1.25rem;
}

.pin-gate-input-wrap {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.pin-gate-input {
  flex: 1;
  background: var(--input-bg, rgba(255,255,255,0.06));
  border: 1px solid var(--border-subtle, rgba(255,255,255,0.15));
  border-radius: 0.5rem;
  padding: 0.75rem;
  font-size: 1.5rem;
  text-align: center;
  letter-spacing: 0.5rem;
  color: var(--text-color);
  outline: none;
}

.pin-gate-input:focus { border-color: var(--accent-color); }

.pin-gate-show-toggle {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
}

.pin-gate-error {
  color: #ef4444;
  font-size: 0.85rem;
  margin: 0 0 0.75rem;
}

.pin-gate-submit {
  background: var(--accent-color);
  border: none;
  border-radius: 0.5rem;
  padding: 0.65rem 2rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--bg-color, #000);
  cursor: pointer;
  width: 100%;
  margin-bottom: 0.5rem;
}

.pin-gate-back {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 0.85rem;
  cursor: pointer;
  padding: 0.5rem;
}

/* ---- Transitions ---- */
.fade-enter-active,
.fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from,
.fade-leave-to { opacity: 0; }

.nav-slide-enter-active { transition: opacity 0.15s ease-out, transform 0.15s ease-out; }
.nav-slide-leave-active { transition: opacity 0.1s ease-in; }
.nav-slide-enter-from { opacity: 0; transform: translateX(-0.5rem); }
.nav-slide-leave-to { opacity: 0; }

/* ---- Focus visible ---- */
.nav-hamburger:focus-visible,
.retry-btn:focus-visible,
.empty-state-btn:focus-visible,
.pin-gate-submit:focus-visible {
  outline: 2px solid var(--accent-color);
  outline-offset: 2px;
}
</style>
