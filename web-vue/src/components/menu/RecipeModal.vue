<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import type { RecipeDetail } from '@/types/api'
import { useMenuStore } from '@/stores/menu'
import { useSettingsStore } from '@/stores/settings'
import { formatIngredient, ratingStars } from '@/utils/formatting'
import { STOCK_ICON_SVG } from '@/utils/icons'

const menu = useMenuStore()
const settings = useSettingsStore()

const detail = ref<RecipeDetail | null>(null)
const loading = ref(false)

const isOpen = computed(() => menu.selectedRecipe !== null)
const recipe = computed(() => menu.selectedRecipe)
const stars = computed(() => ratingStars(detail.value?.rating ?? recipe.value?.rating ?? 0))

// Fetch detail when recipe opens
watch(() => menu.selectedRecipe, async (newRecipe) => {
  if (!newRecipe) {
    detail.value = null
    return
  }
  loading.value = true
  try {
    const res = await fetch(`/api/recipe/${newRecipe.id}`)
    if (res.ok) {
      detail.value = await res.json()
    }
  } catch (e) {
    console.warn('Failed to load recipe detail:', e)
  } finally {
    loading.value = false
  }
})

function close() {
  menu.closeRecipe()
}

function rateDrink(rating: number) {
  if (!recipe.value) return
  if (!settings.ratingsEnabled) return
  menu.namePrompt = {
    show: true, name: '', recipe: recipe.value, action: 'rate',
    rating, confirmStep: false,
  }
}

function orderDrink() {
  if (!recipe.value) return
  if (!settings.ordersEnabled) return
  menu.namePrompt = {
    show: true, name: '', recipe: recipe.value, action: 'order',
    rating: 0, confirmStep: false,
  }
}

function onBackdropClick(e: MouseEvent) {
  if ((e.target as HTMLElement).classList.contains('modal-backdrop')) {
    close()
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="modal-backdrop" @click="onBackdropClick" @keydown.escape="close">
      <div class="recipe-modal" :class="{ 'recipe-modal--full': detail?.steps?.length }">
        <button class="modal-close" aria-label="Close" @click="close">&times;</button>

        <!-- Loading state -->
        <div v-if="loading" class="loading-sm">Loading details...</div>

        <template v-else-if="detail">
          <!-- Image -->
          <img v-if="detail.image" :src="detail.image" :alt="detail.name" class="modal-image">
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div v-else class="modal-placeholder" v-html="STOCK_ICON_SVG" />

          <h2>{{ detail.name }}</h2>

          <!-- Rating stars (interactive) -->
          <div v-if="settings.ratingsEnabled" class="modal-rating-wrapper">
            <span class="modal-rating-label">Rating</span>
            <div class="modal-rating">
              <button
                v-for="i in 5"
                :key="i"
                class="star-btn"
                :class="{ filled: i <= stars }"
                @click="rateDrink(i)"
              >{{ i <= stars ? '\u2605' : '\u2606' }}</button>
            </div>
          </div>

          <!-- Timing -->
          <div v-if="detail.working_time || detail.waiting_time" class="modal-timing">
            <span v-if="detail.working_time">Prep: {{ detail.working_time }}m</span>
            <span v-if="detail.waiting_time">Wait: {{ detail.waiting_time }}m</span>
          </div>

          <!-- Description -->
          <p v-if="detail.description" class="modal-description">{{ detail.description }}</p>

          <!-- Two-column layout for ingredients + steps -->
          <div v-if="detail.steps?.length" class="modal-columns">
            <div class="modal-col-ingredients">
              <h3>Ingredients</h3>
              <ul class="ingredient-list">
                <li v-for="(ing, idx) in detail.ingredients" :key="idx">
                  {{ formatIngredient(ing) }}
                </li>
              </ul>
            </div>
            <div class="modal-col-instructions">
              <h3>Instructions</h3>
              <div v-for="(step, idx) in detail.steps" :key="idx" class="modal-step">
                <div class="modal-step-header">
                  <span class="modal-step-number">Step {{ idx + 1 }}</span>
                  <span v-if="step.name" class="modal-step-name">{{ step.name }}</span>
                  <span v-if="step.time" class="modal-step-time">{{ step.time }}m</span>
                </div>
                <p class="modal-step-text">{{ step.instruction }}</p>
              </div>
            </div>
          </div>

          <!-- Simple ingredient list (no steps) -->
          <div v-else-if="detail.ingredients?.length">
            <ul class="ingredient-list">
              <li v-for="(ing, idx) in detail.ingredients" :key="idx">
                {{ formatIngredient(ing) }}
              </li>
            </ul>
          </div>
        </template>

        <!-- Fallback to basic recipe info -->
        <template v-else-if="recipe">
          <h2>{{ recipe.name }}</h2>
        </template>

        <!-- Order button -->
        <button
          v-if="settings.ordersEnabled && recipe"
          class="btn-order"
          @click="orderDrink"
        >
          <span>Order</span>
        </button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: var(--overlay-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.recipe-modal {
  background: var(--modal-bg);
  color: var(--text-color);
  border: var(--modal-border, none);
  border-radius: var(--modal-radius, 0.75rem);
  box-shadow: var(--card-shadow, none);
  padding: 2rem 1.5rem;
  max-width: 400px;
  width: 100%;
  position: relative;
  max-height: 80vh;
  overflow-y: auto;
}

.recipe-modal--full { max-width: 700px; }

.modal-image {
  width: calc(100% + 3rem);
  max-height: 220px;
  object-fit: cover;
  border-radius: var(--modal-radius, 0.75rem) var(--modal-radius, 0.75rem) 0 0;
  margin: -2rem -1.5rem 1rem -1.5rem;
}

.modal-placeholder {
  width: calc(100% + 3rem);
  height: 180px;
  margin: -2rem -1.5rem 1rem -1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--placeholder-bg, rgba(255,255,255,0.03));
  color: var(--accent-color);
  opacity: 0.55;
  border-radius: var(--modal-radius, 0.75rem) var(--modal-radius, 0.75rem) 0 0;
  pointer-events: none;
}

.modal-placeholder :deep(svg) {
  width: 200px;
  height: 140px;
}

.modal-close {
  position: absolute;
  top: 0.5rem;
  right: 0.75rem;
  background: rgba(0, 0, 0, 0.5);
  border: none;
  border-radius: 50%;
  color: rgba(255, 255, 255, 0.85);
  font-size: 1.5rem;
  cursor: pointer;
  line-height: 1;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
}

.modal-close:hover {
  color: #fff;
  background: rgba(0, 0, 0, 0.7);
}

.recipe-modal h2 {
  font-family: var(--heading-font);
  color: var(--accent-color);
  font-size: 1.6rem;
  margin: 0 0 0.5rem;
  padding-right: 1.5rem;
}

.modal-rating-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 0.75rem;
}

.modal-rating-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}

.modal-rating {
  display: flex;
  gap: 0.15rem;
}

.star-btn {
  color: var(--accent-color);
  font-size: 1.5rem;
  background: none;
  border: none;
  padding: 0.3rem;
  cursor: pointer;
  transition: transform 0.15s, color 0.15s;
}

.star-btn:hover { transform: scale(1.15); }
.star-btn.filled { color: var(--accent-color); }

.modal-timing {
  display: flex;
  gap: 1rem;
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.modal-description {
  font-size: 0.9rem;
  color: var(--text-muted, rgba(255,255,255,0.6));
  line-height: 1.5;
  margin: 0 0 1rem;
  font-style: italic;
}

.ingredient-list {
  list-style: none;
  padding: 0;
  margin: 0.75rem 0 0;
}

.ingredient-list li {
  padding: 0.45rem 0;
  border-bottom: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
  font-family: var(--body-font);
  color: var(--text-color);
  text-transform: capitalize;
  font-size: 0.95rem;
}

.ingredient-list li:last-child { border-bottom: none; }

.modal-columns {
  display: flex;
  gap: 1.5rem;
  margin-top: 0.5rem;
}

.modal-col-ingredients { flex: 0 0 40%; min-width: 0; }
.modal-col-instructions { flex: 1; min-width: 0; }

.modal-columns h3 {
  font-family: var(--heading-font);
  font-size: 0.9rem;
  color: var(--accent-color);
  margin: 0 0 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.modal-step { margin-bottom: 0.75rem; }
.modal-step:last-child { margin-bottom: 0; }

.modal-step-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.modal-step-number {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--accent-color);
  letter-spacing: 0.04em;
}

.modal-step-name {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-style: italic;
}

.modal-step-time {
  font-size: 0.7rem;
  color: var(--text-muted);
  margin-left: auto;
}

.modal-step-text {
  font-size: 0.85rem;
  line-height: 1.55;
  color: var(--text-color);
  margin: 0;
  white-space: pre-line;
}

@media (max-width: 550px) {
  .modal-columns { flex-direction: column; gap: 1rem; }
  .modal-col-ingredients { flex: none; }
}

.loading-sm {
  text-align: center;
  color: var(--text-muted);
  padding: 1rem 0;
  font-style: italic;
}

.btn-order {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  position: sticky;
  bottom: -2rem;
  z-index: 1;
  background: var(--modal-bg);
  margin: 0.75rem -1.5rem -2rem;
  padding: 0.75rem 1.5rem 2rem;
  width: calc(100% + 3rem);
  border-top: 1px solid var(--btn-border, rgba(255,255,255,0.1));
  border-left: none;
  border-right: none;
  border-bottom: none;
  border-radius: 0;
  font-family: var(--heading-font);
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--accent-color);
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-order:hover:not(:disabled) {
  background: var(--btn-active-bg);
}

/* Focus visible */
.modal-close:focus-visible,
.star-btn:focus-visible,
.btn-order:focus-visible {
  outline: 2px solid var(--accent-color);
  outline-offset: 2px;
}
</style>
