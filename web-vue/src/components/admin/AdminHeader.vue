<template>
  <button class="nav-hamburger" v-show="admin.adminReady" @click="admin.navOpen = !admin.navOpen" aria-label="Navigation menu">&#9776;</button>
  <Transition name="nav-fade">
    <div class="nav-menu" v-show="admin.adminReady && admin.navOpen" role="menu" v-click-outside="() => admin.navOpen = false">
      <a href="/" class="nav-menu-item" role="menuitem">Menu</a>
      <a href="/docs" class="nav-menu-item" role="menuitem">API Docs</a>
      <span class="nav-menu-version" v-show="admin.appVersion">{{ admin.appVersion }}</span>
    </div>
  </Transition>

  <header class="admin-header" v-show="admin.adminReady">
    <h1 style="margin-left: 2.5rem;">{{ admin.settings.app_name || 'Morsl' }}</h1>
    <div class="header-right">
      <div class="tier-selector" role="radiogroup" aria-label="Admin complexity tier"
           title="Controls which settings are visible. Standard: essentials only. Advanced: display, integration, and tuning. Expert: all features including branding.">
        <button class="tier-pill" role="radio"
                :aria-checked="admin.adminTier === 'essential'"
                @click="admin.setTier('essential')"
                title="Essential settings for everyday use">
          <span class="tier-label-full">Standard</span><span class="tier-label-short">S</span>
        </button>
        <button class="tier-pill" role="radio"
                :aria-checked="admin.adminTier === 'standard'"
                @click="admin.setTier('standard')"
                title="Display, integration, and tuning options">
          <span class="tier-label-full">Advanced</span><span class="tier-label-short">A</span>
        </button>
        <button class="tier-pill" role="radio"
                :aria-checked="admin.adminTier === 'advanced'"
                @click="admin.setTier('advanced')"
                title="All features including branding and custom icons">
          <span class="tier-label-full">Expert</span><span class="tier-label-short">E</span>
        </button>
      </div>
      <button class="btn-generate btn-secondary"
              v-show="admin.settings.kiosk_enabled"
              @click="admin.lockKiosk()"
              style="height:30px; font-size:0.8rem; padding:0 0.75rem; margin-right:0.5rem;"
              title="Lock and return to menu page">&#128274; Lock</button>
      <span class="status-badge" :class="admin.status.state" aria-live="polite" role="status">
        <span class="dot"></span>
        <span>{{ admin.status.state === 'generating' ? admin.generatingElapsed() : admin.status.state }}</span>
      </span>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useAdminStore } from '@/stores/admin'

const admin = useAdminStore()

const vClickOutside = {
  mounted(el: HTMLElement, binding: { value: () => void }) {
    (el as HTMLElement & { _clickOutside: (e: Event) => void })._clickOutside = (e: Event) => {
      if (!el.contains(e.target as Node)) binding.value()
    }
    document.addEventListener('click', (el as HTMLElement & { _clickOutside: (e: Event) => void })._clickOutside)
  },
  unmounted(el: HTMLElement) {
    document.removeEventListener('click', (el as HTMLElement & { _clickOutside: (e: Event) => void })._clickOutside)
  },
}
</script>

<style scoped>
.nav-hamburger {
  position: fixed;
  top: 0.85rem;
  left: 0.75rem;
  z-index: 200;
  background: none;
  border: none;
  color: var(--text-color, #e8e0d0);
  font-size: 1.4rem;
  cursor: pointer;
  padding: 0.25rem;
  line-height: 1;
}

.nav-menu {
  position: fixed;
  top: 3rem;
  left: 0.75rem;
  z-index: 200;
  background: var(--modal-bg, #1a1a1a);
  border: 1px solid var(--card-border, rgba(255,255,255,0.1));
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.4);
  padding: 0.25rem 0;
  min-width: 140px;
}

.nav-menu-item {
  display: block;
  padding: 0.5rem 1rem;
  color: var(--text-color, #e8e0d0);
  text-decoration: none;
  font-size: 0.85rem;
  transition: background 0.15s;
}

.nav-menu-item:hover {
  background: var(--surface-hover);
}

.nav-menu-version {
  display: block;
  padding: 0.35rem 1rem;
  font-size: 0.7rem;
  color: var(--text-muted, rgba(255,255,255,0.35));
  border-top: 1px solid var(--card-border, rgba(255,255,255,0.08));
}

.nav-fade-enter-active { transition: opacity 0.15s ease-out; }
.nav-fade-leave-active { transition: opacity 0.1s ease-in; }
.nav-fade-enter-from,
.nav-fade-leave-to { opacity: 0; }
</style>
