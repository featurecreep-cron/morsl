<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useMenuStore } from '@/stores/menu'
import { useSettingsStore } from '@/stores/settings'
import { ratingStars } from '@/utils/formatting'

const menu = useMenuStore()
const settings = useSettingsStore()
const inputRef = ref<HTMLInputElement | null>(null)

const isOpen = computed(() => menu.namePrompt.show)
const isRating = computed(() => menu.namePrompt.action === 'rate')
const isConfirmStep = computed(() => menu.namePrompt.confirmStep)
const recipe = computed(() => menu.namePrompt.recipe)
const currentRating = computed(() => menu.namePrompt.rating)
const confirmStars = computed(() => ratingStars(currentRating.value))

// Focus input on open
watch(isOpen, (open) => {
  if (open) {
    nextTick(() => {
      inputRef.value?.focus()
    })
  }
})

function selectNameChip(name: string) {
  menu.namePrompt.name = name
  menu.saveRecentName(name)
  if (isRating.value && currentRating.value) {
    submitName(name)
  } else if (!isRating.value) {
    submitName(name)
  }
}

function selectRating(i: number) {
  menu.namePrompt.rating = i
  if (menu.namePrompt.name.trim()) {
    submitName(menu.namePrompt.name)
  }
}

function submitName(name?: string) {
  const trimmed = (name || menu.namePrompt.name || '').trim()
  if (trimmed) menu.saveRecentName(trimmed)

  // Rating + Tandoor save: show confirmation
  if (isRating.value && settings.saveRatingsToTandoor && !menu.namePrompt.confirmStep) {
    menu.namePrompt.name = trimmed
    menu.namePrompt.confirmStep = true
    return
  }

  const rating = menu.namePrompt.rating || 0
  const recipeObj = menu.namePrompt.recipe
  const action = menu.namePrompt.action

  // Reset prompt
  menu.namePrompt = {
    show: false, name: '', recipe: null, action: '', rating: 0, confirmStep: false,
  }

  if (!recipeObj) return

  if (action === 'rate' && rating > 0) {
    menu.setRating(recipeObj.id, rating, trimmed || null)
  } else if (action === 'order') {
    menu.placeOrder(recipeObj, trimmed || null)
  }
}

function skip() {
  menu.namePrompt = {
    show: false, name: '', recipe: null, action: '', rating: 0, confirmStep: false,
  }
}

function confirmRating() {
  const rating = menu.namePrompt.rating || 0
  const name = menu.namePrompt.name || null
  const recipeObj = menu.namePrompt.recipe
  menu.namePrompt = {
    show: false, name: '', recipe: null, action: '', rating: 0, confirmStep: false,
  }
  if (recipeObj && rating > 0) {
    menu.setRating(recipeObj.id, rating, name)
  }
}

function cancelConfirmation() {
  menu.namePrompt.confirmStep = false
}

function onBackdropClick(e: MouseEvent) {
  if ((e.target as HTMLElement).classList.contains('name-prompt-backdrop')) {
    skip()
  }
}

function onSubmitForm() {
  submitName()
}
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="name-prompt-backdrop" @click="onBackdropClick">
      <div class="name-prompt">
        <!-- Confirmation step -->
        <template v-if="isConfirmStep">
          <div class="rating-confirm-summary">
            <div class="rating-confirm-recipe">{{ recipe?.name }}</div>
            <div class="rating-confirm-stars">
              <span v-for="i in 5" :key="i">{{ i <= confirmStars ? '\u2605' : '\u2606' }}</span>
            </div>
            <div v-if="menu.namePrompt.name" class="rating-confirm-name">
              by {{ menu.namePrompt.name }}
            </div>
            <div class="rating-confirm-warning">
              This will save the rating to Tandoor
            </div>
          </div>
          <div class="rating-confirm-actions">
            <button class="rating-confirm-back" @click="cancelConfirmation">Back</button>
            <button class="rating-confirm-submit" @click="confirmRating">Confirm</button>
          </div>
        </template>

        <!-- Name entry step -->
        <template v-else>
          <div class="name-prompt-header">
            <div>
              <div class="name-prompt-title">
                {{ isRating ? 'Rate' : 'Order' }} {{ recipe?.name }}
              </div>
              <div class="name-prompt-subtitle">
                {{ isRating ? 'Who is rating?' : 'Who is ordering?' }}
              </div>
            </div>
            <button class="name-prompt-skip" @click="skip">Skip</button>
          </div>

          <!-- Star rating (for rate action) -->
          <div v-if="isRating" class="name-prompt-stars">
            <button
              v-for="i in 5"
              :key="i"
              class="star-btn"
              :class="{ filled: i <= currentRating }"
              @click="selectRating(i)"
            >{{ i <= currentRating ? '\u2605' : '\u2606' }}</button>
          </div>

          <!-- Recent names -->
          <div v-if="menu.recentNames.length > 0" class="name-prompt-recent">
            <button
              v-for="rn in menu.recentNames"
              :key="rn"
              class="name-prompt-chip"
              :class="{ active: menu.namePrompt.name === rn }"
              @click="selectNameChip(rn)"
            >{{ rn }}</button>
          </div>

          <!-- Name input -->
          <form class="name-prompt-input-row" @submit.prevent="onSubmitForm">
            <input
              ref="inputRef"
              v-model="menu.namePrompt.name"
              class="name-prompt-input"
              type="text"
              placeholder="Enter name..."
              autocomplete="off"
            >
            <button
              type="submit"
              class="name-prompt-submit"
              :disabled="!menu.namePrompt.name.trim() && !(isRating && currentRating > 0)"
            >
              &rarr;
            </button>
          </form>
        </template>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.name-prompt-backdrop {
  position: fixed;
  inset: 0;
  background: var(--overlay-bg);
  z-index: 1100;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.name-prompt {
  background: var(--modal-bg);
  color: var(--text-color);
  border-radius: 1rem 1rem 0 0;
  padding: 1.25rem 1.25rem 1.5rem;
  width: 100%;
  max-width: 420px;
}

.name-prompt-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.name-prompt-title {
  font-family: var(--heading-font);
  font-size: 1.1rem;
  color: var(--accent-color);
}

.name-prompt-subtitle {
  font-family: var(--body-font);
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 0.15rem;
}

.name-prompt-skip {
  background: none;
  border: none;
  color: var(--text-muted);
  font-family: var(--body-font);
  font-size: 0.85rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
}

.name-prompt-skip:hover { color: var(--text-color); }

.name-prompt-stars {
  display: flex;
  justify-content: center;
  gap: 0.25rem;
  margin-bottom: 0.75rem;
}

.star-btn {
  color: var(--accent-color);
  font-size: 1.5rem;
  background: none;
  border: none;
  padding: 0.3rem;
  cursor: pointer;
  transition: transform 0.15s;
}

.star-btn:hover { transform: scale(1.15); }

.name-prompt-recent {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.name-prompt-chip {
  background: var(--card-bg);
  color: var(--accent-color);
  border: 1px solid var(--accent-color-dim);
  border-radius: 2rem;
  padding: 0.4rem 1rem;
  font-family: var(--body-font);
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.name-prompt-chip:hover,
.name-prompt-chip.active {
  background: var(--accent-color);
  color: var(--bg-color);
  border-color: var(--accent-color);
}

.name-prompt-input-row {
  display: flex;
  gap: 0.5rem;
}

.name-prompt-input {
  flex: 1;
  background: var(--input-bg);
  border: 1px solid var(--border-subtle);
  border-radius: 0.5rem;
  padding: 0.65rem 0.75rem;
  font-family: var(--body-font);
  font-size: 1rem;
  color: var(--text-color);
  outline: none;
}

.name-prompt-input:focus { border-color: var(--accent-color); }
.name-prompt-input::placeholder { color: var(--text-muted); }

.name-prompt-submit {
  background: var(--accent-color);
  border: none;
  border-radius: 0.5rem;
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  color: var(--bg-color, #000);
}

.name-prompt-submit:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Rating confirmation */
.rating-confirm-summary {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 0;
}

.rating-confirm-recipe {
  font-family: var(--heading-font);
  color: var(--accent-color);
  font-size: 1.2rem;
  text-align: center;
}

.rating-confirm-stars {
  display: flex;
  gap: 0.15rem;
  color: var(--accent-color);
  font-size: 1.2rem;
}

.rating-confirm-name {
  color: var(--text-muted);
  font-size: 0.9rem;
}

.rating-confirm-warning {
  color: var(--text-muted);
  font-size: 0.85rem;
  font-style: italic;
}

.rating-confirm-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
  padding: 0.5rem 0;
}

.rating-confirm-back {
  background: transparent;
  border: 1.5px solid var(--accent-color);
  color: var(--accent-color);
  border-radius: 0.5rem;
  padding: 0.5rem 1.25rem;
  cursor: pointer;
  font-size: 0.95rem;
}

.rating-confirm-submit {
  background: var(--accent-color);
  border: none;
  color: var(--bg-primary, #000);
  border-radius: 0.5rem;
  padding: 0.5rem 1.25rem;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.95rem;
}
</style>
