<script setup lang="ts">
import { computed } from 'vue'
import { useMenuStore } from '@/stores/menu'

const menu = useMenuStore()
const isOpen = computed(() => menu.mealPlanSave.show)

function close() {
  menu.mealPlanSave.show = false
}

function toggleUser(userId: number) {
  const idx = menu.mealPlanSave.selectedUsers.indexOf(userId)
  if (idx >= 0) {
    menu.mealPlanSave.selectedUsers.splice(idx, 1)
  } else {
    menu.mealPlanSave.selectedUsers.push(userId)
  }
}

function selectGen(idx: number) {
  menu.mealPlanSave.selectedGen = idx
}

function toggleExpand(idx: number) {
  menu.mealPlanSave.expandedGen = menu.mealPlanSave.expandedGen === idx ? null : idx
}

function onBackdropClick(e: MouseEvent) {
  if ((e.target as HTMLElement).classList.contains('name-prompt-backdrop')) {
    close()
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="name-prompt-backdrop" @click="onBackdropClick">
      <div class="name-prompt" style="max-width: 480px;">
        <div class="name-prompt-header">
          <div>
            <div class="name-prompt-title">Save to Meal Plan</div>
            <div v-if="menu.mealPlanSave.profile" class="name-prompt-subtitle">
              {{ menu.mealPlanSave.profile }}
            </div>
          </div>
          <button class="name-prompt-skip" @click="close">&times;</button>
        </div>

        <!-- Date -->
        <div style="margin-bottom: 0.75rem;">
          <label style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.25rem;">Date</label>
          <input
            v-model="menu.mealPlanSave.date"
            type="date"
            class="name-prompt-input"
            style="width: 100%;"
          >
        </div>

        <!-- Meal type -->
        <div v-if="menu.mealPlanSave.mealTypes.length > 0" style="margin-bottom: 0.75rem;">
          <label style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.25rem;">Meal Type</label>
          <select
            v-model="menu.mealPlanSave.mealTypeId"
            class="name-prompt-input"
            style="width: 100%;"
          >
            <option
              v-for="mt in menu.mealPlanSave.mealTypes"
              :key="mt.id"
              :value="mt.id"
            >{{ mt.name }}</option>
          </select>
        </div>

        <!-- Generation picker -->
        <div v-if="menu.mealPlanSave.generations.length > 1" style="margin-bottom: 0.75rem;">
          <label style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.25rem;">Generation</label>
          <div style="display: flex; flex-direction: column; gap: 0.5rem;">
            <div
              v-for="(gen, idx) in menu.mealPlanSave.generations"
              :key="idx"
              class="gen-card"
              :class="{ 'gen-card-active': menu.mealPlanSave.selectedGen === idx }"
              @click="selectGen(idx)"
            >
              <div class="gen-card-summary">
                <div class="gen-card-images">
                  <img
                    v-for="recipe in gen.recipes.slice(0, 3)"
                    :key="recipe.id"
                    :src="recipe.image || ''"
                    :alt="recipe.name"
                    class="gen-card-thumb"
                  >
                </div>
                <div class="gen-card-names">
                  {{ gen.recipes.map(r => r.name).join(', ') }}
                </div>
                <div class="gen-card-count">{{ gen.recipes.length }}</div>
                <button class="gen-card-toggle" @click.stop="toggleExpand(idx)">
                  {{ menu.mealPlanSave.expandedGen === idx ? '\u25B2' : '\u25BC' }}
                </button>
              </div>
              <div v-if="menu.mealPlanSave.expandedGen === idx" class="gen-card-detail">
                <div v-for="recipe in gen.recipes" :key="recipe.id" class="gen-card-recipe">
                  <img
                    v-if="recipe.image"
                    :src="recipe.image"
                    :alt="recipe.name"
                    class="gen-card-recipe-img"
                  >
                  <div v-else class="gen-card-recipe-placeholder">&bull;</div>
                  <span class="gen-card-recipe-name">{{ recipe.name }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Users -->
        <div v-if="menu.mealPlanSave.users.length > 0" style="margin-bottom: 0.75rem;">
          <label style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.25rem;">Share with</label>
          <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">
            <button
              v-for="user in menu.mealPlanSave.users"
              :key="user.id"
              class="name-prompt-chip"
              :class="{ active: menu.mealPlanSave.selectedUsers.includes(user.id) }"
              @click="toggleUser(user.id)"
            >{{ user.display_name || user.username }}</button>
          </div>
        </div>

        <!-- Submit -->
        <button
          class="name-prompt-submit"
          style="width: 100%; justify-content: center; padding: 0.75rem; font-size: 0.95rem;"
          :disabled="menu.mealPlanSave.saving"
          @click="menu.submitMealPlanSave()"
        >
          {{ menu.mealPlanSave.saving ? 'Saving...' : 'Save to Meal Plan' }}
        </button>
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
  max-height: 80vh;
  overflow-y: auto;
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
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
}

.name-prompt-input {
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

.name-prompt-chip {
  background: var(--card-bg);
  color: var(--accent-color);
  border: 1px solid var(--accent-color-dim);
  border-radius: 2rem;
  padding: 0.4rem 1rem;
  font-family: var(--body-font);
  font-size: 0.9rem;
  cursor: pointer;
}

.name-prompt-chip.active {
  background: var(--accent-color);
  color: var(--bg-color);
  border-color: var(--accent-color);
}

.name-prompt-submit {
  background: var(--accent-color);
  border: none;
  border-radius: 0.5rem;
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  color: var(--bg-color, #000);
  font-weight: 600;
}

.name-prompt-submit:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Gen cards */
.gen-card {
  border-radius: 0.5rem;
  border: 1.5px solid var(--border-color);
  background: var(--card-bg);
  cursor: pointer;
  transition: border-color 0.15s;
  font-size: 0.85rem;
  width: 100%;
  overflow: hidden;
}

.gen-card-active { border-color: var(--accent-color); background: var(--btn-active-bg); }

.gen-card-summary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.65rem;
  min-height: 48px;
}

.gen-card-images { display: flex; gap: 0.2rem; flex-shrink: 0; }

.gen-card-thumb {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
}

.gen-card-names {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-muted);
}

.gen-card-count { flex-shrink: 0; color: var(--text-muted); font-size: 0.8rem; }

.gen-card-toggle {
  flex-shrink: 0;
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0.25rem;
  font-size: 0.7rem;
}

.gen-card-detail {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 0 0.65rem 0.5rem;
  border-top: 1px solid var(--border-color);
  padding-top: 0.5rem;
}

.gen-card-recipe { display: flex; align-items: center; gap: 0.5rem; }

.gen-card-recipe-img {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  object-fit: cover;
  flex-shrink: 0;
}

.gen-card-recipe-placeholder {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  background: var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--text-muted);
}

.gen-card-recipe-name { font-size: 0.82rem; color: var(--text-color); }
</style>
