<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { CarouselItem, CarouselDivider, Recipe } from '@/types/api'
import { useCarousel } from '@/composables/useCarousel'
import { useMenuStore } from '@/stores/menu'
import { timeAgo } from '@/utils/formatting'
import RecipeCard from './RecipeCard.vue'

const props = defineProps<{
  items: CarouselItem[]
}>()

const emit = defineEmits<{
  scrollToStart: []
}>()

const trackRef = ref<HTMLElement | null>(null)
const {
  canScrollLeft, canScrollRight, canPageLeft, canPageRight,
  scrollCarousel, scrollToPrevPage, scrollToNextPage, scrollToStart,
  onTrackScroll, scheduleScrollArrowUpdate,
} = useCarousel(trackRef)

function isDivider(item: CarouselItem): item is CarouselDivider {
  return '_isDivider' in item && item._isDivider === true
}

function asRecipe(item: CarouselItem): Recipe {
  return item as Recipe
}

// Re-evaluate scroll arrows when items change
watch(() => props.items, () => {
  nextTick(() => scheduleScrollArrowUpdate())
})

// Expose scrollToStart so parent can call it
defineExpose({ scrollToStart })

// Watch store's carousel scroll trigger — scroll to start on key actions
const menuStore = useMenuStore()
watch(() => menuStore.carouselScrollTrigger, () => {
  nextTick(() => scrollToStart())
})

// Suppress unused warning
void emit
</script>

<template>
  <div class="carousel-container">
    <div class="carousel-wrapper">
      <!-- Left page arrow -->
      <button
        v-if="canPageLeft"
        class="carousel-arrow carousel-arrow--double-left"
        aria-label="Previous page"
        @click="scrollToPrevPage()"
      >&laquo;</button>

      <!-- Left arrow -->
      <button
        v-if="canScrollLeft"
        class="carousel-arrow carousel-arrow--left"
        aria-label="Scroll left"
        @click="scrollCarousel(-1)"
      >&lsaquo;</button>

      <!-- Track -->
      <div ref="trackRef" class="carousel-track" @scroll="onTrackScroll">
        <template v-for="(item, idx) in items" :key="isDivider(item) ? `div-${idx}` : asRecipe(item).id">
          <!-- Divider -->
          <div v-if="isDivider(item)" class="carousel-slide carousel-slide--divider">
            <div class="page-divider">
              <div class="page-divider-line" />
              <div class="page-divider-content">
                <span class="page-divider-label">Page {{ item._pageNum }}</span>
                <span class="page-divider-profile">{{ item._profile }}</span>
                <span class="page-divider-time">{{ timeAgo(item._generatedAt) }}</span>
              </div>
              <div class="page-divider-line" />
            </div>
          </div>

          <!-- Recipe card -->
          <div v-else class="carousel-slide">
            <RecipeCard :recipe="asRecipe(item)" />
          </div>
        </template>
      </div>

      <!-- Right arrow -->
      <button
        v-if="canScrollRight"
        class="carousel-arrow carousel-arrow--right"
        aria-label="Scroll right"
        @click="scrollCarousel(1)"
      >&rsaquo;</button>

      <!-- Right page arrow -->
      <button
        v-if="canPageRight"
        class="carousel-arrow carousel-arrow--double-right"
        aria-label="Next page"
        @click="scrollToNextPage()"
      >&raquo;</button>
    </div>
  </div>
</template>

<style scoped>
.carousel-container {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.carousel-wrapper {
  position: relative;
}

.carousel-track {
  display: flex;
  align-items: stretch;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  gap: 1rem;
  padding: 0.25rem 1rem;
}

.carousel-track::-webkit-scrollbar { display: none; }

.carousel-slide {
  flex: 0 0 300px;
  scroll-snap-align: center;
}

@media (max-width: 575.98px) {
  .carousel-slide { flex: 0 0 calc(100vw - 4rem); }
  .carousel-track { padding: 0.5rem 1rem; }
}

.carousel-arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 10;
  background: rgba(0, 0, 0, 0.4);
  color: white;
  border: none;
  border-radius: 50%;
  width: 44px;
  height: 44px;
  font-size: 2rem;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  opacity: 0.7;
}

.carousel-arrow:hover {
  opacity: 1;
  background: rgba(0, 0, 0, 0.7);
}

.carousel-arrow--left { left: 0.5rem; }
.carousel-arrow--right { right: 0.5rem; }
.carousel-arrow--double-left { left: 0.5rem; font-weight: bold; }
.carousel-arrow--double-right { right: 0.5rem; font-weight: bold; }

@media (max-width: 575.98px) {
  .carousel-arrow { display: none; }
}

/* Divider */
.carousel-slide--divider {
  flex: 0 0 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.page-divider {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 1rem 0;
  gap: 0.5rem;
}

.page-divider-line {
  width: 2px;
  flex: 1;
  background: linear-gradient(to bottom, transparent, var(--accent-color-dim), transparent);
  opacity: 0.4;
}

.page-divider-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem;
}

.page-divider-label {
  font-family: var(--heading-font);
  font-size: 0.7rem;
  color: var(--accent-color);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  white-space: nowrap;
}

.page-divider-profile {
  font-family: var(--body-font);
  font-size: 0.65rem;
  color: var(--text-muted);
  text-transform: capitalize;
  opacity: 0.7;
}

.page-divider-time {
  font-size: 0.6rem;
  color: var(--text-muted);
  opacity: 0.5;
}

@media (max-width: 575.98px) {
  .carousel-slide--divider { flex: 0 0 60px; }
}
</style>
