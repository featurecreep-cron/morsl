<script setup lang="ts">
import { ref } from 'vue'
import type { Shelf, Recipe } from '@/types/api'
import { useMenuStore } from '@/stores/menu'
import { itemNounText } from '@/utils/formatting'

defineProps<{
  shelves: Shelf[]
  activeDeckName: string | null
  itemNoun: string
}>()

const menu = useMenuStore()

// Long press state
const longPressTimer = ref<ReturnType<typeof setTimeout> | null>(null)
const longPressFired = ref(false)

function activate(name: string) {
  if (longPressFired.value) {
    longPressFired.value = false
    return
  }
  menu.activateDeck(name)
}

function startLongPress(name: string) {
  longPressFired.value = false
  longPressTimer.value = setTimeout(() => {
    longPressFired.value = true
    menu.removeShelf(name)
  }, 500)
}

function cancelLongPress() {
  if (longPressTimer.value) {
    clearTimeout(longPressTimer.value)
    longPressTimer.value = null
  }
}

function onContextMenu(e: Event, name: string) {
  e.preventDefault()
  menu.removeShelf(name)
}

function getPreview(shelf: Shelf): Recipe | null {
  return menu.deckPreview(shelf)
}

function getRecipeCount(shelf: Shelf): number {
  const gen = shelf.generations[shelf.currentIndex || 0]
  return gen?.recipes?.length ?? 0
}
</script>

<template>
  <div v-if="shelves.length > 1" class="deck-strip">
    <div
      v-for="shelf in shelves"
      :key="shelf.name"
      class="deck-card"
      :class="{ 'deck-card--active': shelf.name === activeDeckName }"
      role="tab"
      :aria-selected="shelf.name === activeDeckName"
      :aria-label="`${shelf.name} shelf`"
      tabindex="0"
      @click="activate(shelf.name)"
      @contextmenu="onContextMenu($event, shelf.name)"
      @pointerdown="startLongPress(shelf.name)"
      @pointerup="cancelLongPress()"
      @pointercancel="cancelLongPress()"
      @pointerleave="cancelLongPress()"
    >
      <div class="deck-card-stack">
        <div class="deck-card-face">
          <img
            v-if="getPreview(shelf)?.image"
            :src="getPreview(shelf)!.image!"
            :alt="shelf.name"
            class="deck-card-img"
            loading="lazy"
          >
          <div v-else class="deck-card-placeholder">
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
              <path d="M17 21a1 1 0 0 0 1-1v-5.35c0-.457.316-.844.727-1.041a4 4 0 0 0-2.134-7.589 5 5 0 0 0-9.186 0 4 4 0 0 0-2.134 7.588c.411.198.727.585.727 1.041V20a1 1 0 0 0 1 1Z"/>
              <path d="M6 17h12"/>
            </svg>
          </div>
          <div class="deck-card-overlay">
            <span class="deck-card-title">{{ shelf.name }}</span>
            <span class="deck-card-count">{{ itemNounText(getRecipeCount(shelf), itemNoun) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.deck-strip {
  flex: 0 0 auto;
  display: flex;
  gap: 0.75rem;
  padding: 0.25rem 1rem;
  overflow-x: auto;
  scrollbar-width: none;
  justify-content: center;
  align-items: flex-end;
}

.deck-strip::-webkit-scrollbar { display: none; }

.deck-card {
  position: relative;
  cursor: pointer;
  flex: 0 0 auto;
  transition: transform 0.2s;
  overflow: visible;
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  user-select: none;
}

.deck-card:hover { transform: translateY(-2px); }
.deck-card--active { transform: translateY(-3px); }

.deck-card-stack {
  position: relative;
  width: 100px;
  height: 70px;
  margin-right: 6px;
  margin-bottom: 6px;
}

.deck-card-stack::before,
.deck-card-stack::after {
  content: '';
  position: absolute;
  border-radius: var(--card-radius, 0.4rem);
  background: var(--card-bg);
  border: 1px solid var(--accent-color);
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

.deck-card-stack::before {
  inset: 0;
  transform: translate(6px, 5px) rotate(2.5deg);
  z-index: 0;
}

.deck-card-stack::after {
  inset: 0;
  transform: translate(3px, 2.5px) rotate(1deg);
  z-index: 1;
}

.deck-card-face {
  position: relative;
  z-index: 2;
  width: 100%;
  height: 100%;
  border-radius: var(--card-radius, 0.4rem);
  overflow: hidden;
  background: var(--card-bg);
  border: 1px solid var(--btn-border);
  transition: border-color 0.2s;
}

.deck-card:hover .deck-card-face { border-color: var(--accent-color); }
.deck-card--active .deck-card-face { border-color: var(--accent-color); border-width: 2px; }

.deck-card-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.deck-card-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--card-bg);
  color: var(--accent-color);
  opacity: 0.8;
}

.deck-card-placeholder svg {
  width: 85%;
  height: 85%;
}

.deck-card-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0.2) 50%, transparent 100%);
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
  padding: 0.3rem;
  gap: 0.1rem;
}

.deck-card-title {
  font-family: var(--heading-font);
  color: #fff;
  font-size: 0.75rem;
  text-transform: capitalize;
  line-height: 1.1;
  text-align: center;
  text-shadow: 0 1px 3px rgba(0,0,0,0.6);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.deck-card-count {
  background: var(--input-bg);
  color: #fff;
  font-size: 0.6rem;
  padding: 0.05rem 0.35rem;
  border-radius: 1rem;
  line-height: 1.3;
}

@media (max-width: 575.98px) {
  .deck-card-stack { width: 85px; height: 60px; }
  .deck-card-title { font-size: 0.65rem; }
}
</style>
