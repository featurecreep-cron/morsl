<script setup lang="ts">
import { computed } from 'vue'
import type { Recipe } from '@/types/api'
import { useMenuStore } from '@/stores/menu'
import { useSettingsStore } from '@/stores/settings'
import { ratingStars, formatIngredient } from '@/utils/formatting'
import { getPlaceholderSvg } from '@/utils/icons'

const props = defineProps<{
  recipe: Recipe
}>()

const menu = useMenuStore()
const settings = useSettingsStore()

const stars = computed(() => ratingStars(props.recipe.rating))
const hasImage = computed(() => !!props.recipe.image)
const isOrdered = computed(() => menu.orderConfirm === props.recipe.id)
const ingredients = computed(() => props.recipe.ingredients ?? [])
const placeholderSvg = computed(() =>
  getPlaceholderSvg(props.recipe, menu.activeProfile, menu.iconMappings, settings.logoUrl),
)

function onCardClick() {
  menu.openRecipe(props.recipe)
}

function onRate(e: Event) {
  e.stopPropagation()
  if (!settings.ratingsEnabled) return
  menu.namePrompt = {
    show: true, name: '', recipe: props.recipe, action: 'rate', rating: 0, confirmStep: false,
  }
}

function onOrder(e: Event) {
  e.stopPropagation()
  if (!settings.ordersEnabled) return
  menu.namePrompt = {
    show: true, name: '', recipe: props.recipe, action: 'order', rating: 0, confirmStep: false,
  }
}
</script>

<template>
  <div class="cocktail-card" @click="onCardClick" tabindex="0" role="button">
    <!-- Image or placeholder -->
    <img v-if="hasImage" :src="recipe.image!" :alt="recipe.name" class="cocktail-image" loading="lazy">
    <!-- eslint-disable-next-line vue/no-v-html -->
    <div v-else class="cocktail-placeholder" v-html="placeholderSvg" />

    <!-- Header -->
    <div class="cocktail-header">
      <h3 class="cocktail-name">{{ recipe.name }}</h3>
      <div v-if="stars > 0" class="cocktail-rating">
        <span v-for="i in 5" :key="i" class="star">{{ i <= stars ? '\u2605' : '\u2606' }}</span>
      </div>
    </div>

    <!-- Inline ingredients -->
    <div v-if="ingredients.length > 0"
         class="cocktail-ingredients-section">
      <ul class="ingredient-inline">
        <li v-for="(ing, idx) in ingredients" :key="idx">
          {{ formatIngredient(ing) }}
        </li>
      </ul>
    </div>

    <span class="tap-hint">Tap for details</span>

    <!-- FAB: Rate -->
    <button
      v-if="settings.ratingsEnabled"
      class="card-fab card-fab--rate"
      :aria-label="`Rate ${recipe.name}`"
      @click="onRate"
    >
      <span class="fab-icon">&starf;</span>
    </button>

    <!-- FAB: Order -->
    <button
      v-if="settings.ordersEnabled"
      class="card-fab card-fab--order"
      :class="{ ordered: isOrdered }"
      :aria-label="`Order ${recipe.name}`"
      @click="onOrder"
    >
      <span class="fab-icon">{{ isOrdered ? '\u2713' : '+' }}</span>
    </button>
  </div>
</template>

<style scoped>
.cocktail-card {
  background: var(--card-bg);
  border: var(--card-border);
  border-radius: var(--card-radius, 0.5rem);
  padding: 1rem 1rem 2.25rem;
  text-align: center;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: var(--card-shadow, none);
  backdrop-filter: var(--card-backdrop, none);
  -webkit-backdrop-filter: var(--card-backdrop, none);
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: center;
  width: 100%;
  height: 100%;
  position: relative;
}

.cocktail-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--card-hover-shadow);
}

.cocktail-header { flex: 0 0 auto; }

.cocktail-name {
  font-family: var(--heading-font);
  font-size: 1.25rem;
  color: var(--accent-color);
  margin: 0 0 0.2rem;
  line-height: 1.2;
}

.cocktail-rating {
  display: flex;
  justify-content: center;
  gap: 0.1rem;
  margin: 0.15rem 0 0.25rem;
}

.cocktail-rating .star {
  color: var(--accent-color);
  font-size: 0.9rem;
}

.cocktail-image {
  width: 100%;
  max-height: 150px;
  object-fit: cover;
  border-radius: var(--card-radius, 0.5rem) var(--card-radius, 0.5rem) 0 0;
  margin: -1rem -1rem 0.75rem -1rem;
  width: calc(100% + 2rem);
}

.cocktail-placeholder {
  width: calc(100% + 2rem);
  height: 150px;
  margin: -1rem -1rem 0.75rem -1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--placeholder-bg, rgba(255,255,255,0.03));
  color: var(--accent-color);
  opacity: 0.55;
  pointer-events: none;
}

.cocktail-placeholder :deep(svg) {
  width: 180px;
  height: 120px;
}

.cocktail-ingredients-section {
  padding-top: 0.5rem;
  border-top: 1px solid var(--divider-color, rgba(255,255,255,0.1));
  width: 100%;
}

.ingredient-inline {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.2rem 0.4rem;
  justify-content: center;
}

.ingredient-inline li {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: capitalize;
}

.ingredient-inline li:not(:last-child)::after {
  content: "\00b7";
  margin-left: 0.4rem;
}

.tap-hint {
  font-size: 0.65rem;
  color: var(--accent-color);
  opacity: 0.75;
  margin-top: auto;
  padding-top: 0.5rem;
  flex: 0 0 auto;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.cocktail-card:hover .tap-hint { opacity: 0.9; }

.card-fab {
  position: absolute;
  bottom: 0.75rem;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid var(--btn-border);
  background: var(--card-bg);
  color: var(--text-muted);
  font-size: 1.3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 6px rgba(0,0,0,0.3);
  z-index: 5;
  opacity: 0.7;
}

.card-fab--rate {
  left: 0.75rem;
  color: var(--accent-color);
}

.fab-icon {
  font-size: 1.1rem;
  line-height: 1;
}

.card-fab--order {
  right: 0.75rem;
  color: var(--accent-color);
}

.cocktail-card:hover .card-fab,
.cocktail-card:focus-within .card-fab {
  opacity: 1;
}

@media (hover: none) {
  .card-fab { opacity: 1; }
}

@media (max-width: 1024px) and (pointer: coarse) {
  .card-fab { opacity: 1; }
}

.card-fab:hover {
  background: var(--btn-active-bg);
  color: var(--btn-active-text);
  border-color: var(--btn-active-border);
  transform: scale(1.1);
}

.card-fab--order.ordered {
  background: var(--btn-active-bg);
  color: var(--btn-active-text);
}

@media (max-width: 575.98px) {
  .cocktail-card { padding: 0.75rem 0.75rem 2rem; }
  .cocktail-name { font-size: 1.15rem; }
}
</style>
