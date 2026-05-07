<script setup lang="ts">
import type { Category, ProfileSummary } from '@/types/api'
import { useMenuStore } from '@/stores/menu'
import { useProfilesStore } from '@/stores/profiles'
import { useSettingsStore } from '@/stores/settings'
import { getBrandIcon, getIconByKey } from '@/utils/icons'

const menu = useMenuStore()
const profilesStore = useProfilesStore()
const settings = useSettingsStore()

function getProfileIcon(profile: ProfileSummary): string {
  if (profile.icon) {
    return getIconByKey(profile.icon)
  }
  return getBrandIcon(settings.logoUrl)
}

function getCategoryIcon(category: Category): string {
  if (category.icon === 'logo') return getBrandIcon(settings.logoUrl)
  if (category.icon) return getIconByKey(category.icon)
  const profiles = profilesStore.categorizedProfiles[category.id] || []
  if (profiles.length > 0 && profiles[0].icon) {
    return getIconByKey(profiles[0].icon)
  }
  return getBrandIcon(settings.logoUrl)
}

function handleCategoryClick(category: Category) {
  const profiles = profilesStore.categorizedProfiles[category.id] || []
  if (profiles.length === 1) {
    // Single profile: generate directly
    menu._targetShelf = profiles[0].name
    menu.selectCategory(profiles[0].name)
  } else if (profiles.length > 1) {
    // Multi profile: toggle panel
    menu.toggleCategoryPanel(category.id)
  }
}

function handleProfileClick(profile: ProfileSummary) {
  menu._targetShelf = profile.name
  menu.categoryPanelOpen = null
  menu.generate(profile.name)
}

function isGenerating(): boolean {
  return menu.state === 'generating'
}
</script>

<template>
  <nav class="category-bar">
    <template v-for="category in profilesStore.displayCategories" :key="category.id">
      <!-- Virtual _all category: show profile chips directly -->
      <template v-if="category.id === '_all'">
        <button
          v-for="profile in profilesStore.visibleProfiles"
          :key="profile.name"
          class="explore-btn"
          :disabled="isGenerating()"
          @click="handleProfileClick(profile)"
        >
          <!-- eslint-disable-next-line vue/no-v-html -->
          <span class="explore-btn-icon" v-html="getProfileIcon(profile)" />
          <span class="explore-btn-label">{{ profile.display_name || profile.name }}</span>
        </button>
      </template>

      <!-- Named category -->
      <template v-else>
        <button
          class="explore-btn"
          :class="{ active: menu.categoryPanelOpen === category.id }"
          :disabled="isGenerating()"
          @click="handleCategoryClick(category)"
        >
          <!-- eslint-disable-next-line vue/no-v-html -->
          <span class="explore-btn-icon" v-html="getCategoryIcon(category)" />
          <span class="explore-btn-label">{{ category.display_name }}</span>
        </button>
      </template>
    </template>
  </nav>

  <!-- Expanded category panel -->
  <div
    v-if="menu.categoryPanelOpen !== null"
    class="category-panel"
  >
    <span class="category-panel-hint">Choose a style</span>
    <div class="category-group">
      <button
        v-for="profile in (profilesStore.categorizedProfiles[menu.categoryPanelOpen] || [])"
        :key="profile.name"
        class="category-chip"
        :disabled="isGenerating()"
        @click="handleProfileClick(profile)"
      >
        <span class="chip-name">{{ profile.display_name || profile.name }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.category-bar {
  flex: 0 0 auto;
  display: flex;
  gap: 0.4rem;
  padding: 0.25rem 1rem;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
}

.explore-btn {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  padding: 0.3rem 0.75rem;
  background: var(--btn-bg);
  color: var(--accent-color);
  border: 1px solid var(--btn-border);
  border-radius: 2rem;
  cursor: pointer;
  transition: all 0.2s;
  height: 38px;
}

.explore-btn:hover:not(:disabled),
.explore-btn.active {
  background: var(--btn-active-bg);
  color: var(--btn-active-text);
  border-color: var(--accent-color);
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

.explore-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.explore-btn-icon {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}

.explore-btn-icon :deep(svg) {
  width: 100%;
  height: 100%;
  stroke-width: 2;
}

.explore-btn-label {
  font-family: var(--heading-font);
  font-size: 0.75rem;
  text-align: center;
  line-height: 1.2;
  white-space: nowrap;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
}

.category-panel {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  align-items: center;
  max-height: 30vh;
  overflow-y: auto;
  padding: 0.25rem 0;
}

.category-panel-hint {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.category-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  justify-content: center;
}

.category-chip {
  background: var(--btn-bg);
  color: var(--btn-text);
  border: 1px solid var(--btn-border);
  border-radius: 2rem;
  padding: 0.25rem 0.75rem;
  font-family: var(--body-font);
  font-size: 0.8rem;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
  text-transform: capitalize;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 0.3rem;
  height: 34px;
}

.category-chip:hover {
  background: var(--btn-active-bg);
  color: var(--btn-active-text);
  border-color: var(--btn-active-border);
}

.category-chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Focus visible */
.explore-btn:focus-visible,
.category-chip:focus-visible {
  outline: 2px solid var(--accent-color);
  outline-offset: 2px;
}
</style>
