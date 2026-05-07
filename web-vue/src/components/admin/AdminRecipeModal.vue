<template>
  <Teleport to="body">
    <!-- Recipe detail modal -->
    <Transition name="recipe-fade">
      <div class="modal-backdrop"
           v-show="admin.selectedRecipe"
           @click.self="admin.closeRecipe()">
        <Transition name="recipe-scale">
          <div class="recipe-modal"
               :class="{ 'recipe-modal--full': admin.selectedRecipe?.steps?.length }"
               v-show="admin.selectedRecipe"
               role="dialog" aria-modal="true" aria-labelledby="admin-recipe-title">
            <button class="modal-close" @click="admin.closeRecipe()" aria-label="Close">&times;</button>
            <img v-show="admin.selectedRecipe?.image"
                 :src="admin.selectedRecipe?.image ?? undefined"
                 :alt="admin.selectedRecipe?.name"
                 class="modal-image">
            <h2 id="admin-recipe-title">{{ admin.selectedRecipe?.name }}</h2>
            <div class="modal-rating"
                 v-show="admin.selectedRecipe && admin.settings.admin_show_ratings !== false"
                 role="group" aria-label="Rate this recipe">
              <button v-for="i in 5" :key="i"
                      class="star-btn"
                      @click="admin.setRating(admin.selectedRecipe?.id ?? 0, i)"
                      :class="{ filled: i <= Math.round(admin.selectedRecipe?.rating || 0) }"
                      :aria-label="i + ' star' + (i > 1 ? 's' : '')"
                      :aria-pressed="i <= Math.round(admin.selectedRecipe?.rating || 0)"
                      style="cursor:pointer; font-size:1.5rem; background:none; border:none; padding:0;">
                {{ i <= Math.round(admin.selectedRecipe?.rating || 0) ? '\u2605' : '\u2606' }}
              </button>
            </div>
            <p class="modal-description"
               v-show="admin.selectedRecipe?.description && admin.settings.admin_show_descriptions !== false">
              {{ admin.selectedRecipe?.description }}
            </p>
            <div class="modal-columns"
                 v-show="admin.selectedRecipe?.steps?.length && (admin.settings.admin_show_ingredients !== false || admin.settings.admin_show_instructions !== false)">
              <div class="modal-col-ingredients" v-show="admin.settings.admin_show_ingredients !== false">
                <h3>Ingredients</h3>
                <ul class="ingredient-list" v-show="admin.selectedRecipe?.ingredients?.length">
                  <li v-for="(ing, ingIdx) in (admin.selectedRecipe?.ingredients || [])"
                      :key="'admin-modal-ing-' + (admin.selectedRecipe?.id || '0') + '-' + ingIdx">
                    {{ formatIngredient(ing) }}
                  </li>
                </ul>
              </div>
              <div class="modal-col-instructions" v-show="admin.settings.admin_show_instructions !== false">
                <h3>Instructions</h3>
                <div v-for="(step, sIdx) in (admin.selectedRecipe?.steps || [])"
                     :key="'step-' + sIdx"
                     class="modal-step">
                  <div class="modal-step-header"
                       v-show="(admin.selectedRecipe?.steps?.length ?? 0) > 1">
                    <span class="modal-step-number">Step {{ sIdx + 1 }}</span>
                    <span class="modal-step-name" v-show="step.name">{{ step.name }}</span>
                    <span class="modal-step-time" v-show="step.time">{{ step.time }} min</span>
                  </div>
                  <p class="modal-step-text">{{ step.instruction }}</p>
                </div>
              </div>
            </div>
            <ul class="ingredient-list"
                v-show="admin.selectedRecipe?.ingredients?.length && !admin.selectedRecipe?.steps?.length && admin.settings.admin_show_ingredients !== false">
              <li v-for="(ing, ingIdx) in (admin.selectedRecipe?.ingredients || [])"
                  :key="'admin-modal-ing-simple-' + (admin.selectedRecipe?.id || '0') + '-' + ingIdx">
                {{ formatIngredient(ing) }}
              </li>
            </ul>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { useAdminStore } from '@/stores/admin'
import { formatIngredient } from '@/utils/formatting'

const admin = useAdminStore()
</script>

<style scoped>
.recipe-fade-enter-active { transition: opacity 0.2s ease-out; }
.recipe-fade-leave-active { transition: opacity 0.2s ease-in; }
.recipe-fade-enter-from,
.recipe-fade-leave-to { opacity: 0; }

.recipe-scale-enter-active { transition: all 0.2s ease-out; }
.recipe-scale-leave-active { transition: all 0.15s ease-in; }
.recipe-scale-enter-from { opacity: 0; transform: scale(0.95); }
.recipe-scale-leave-to { opacity: 0; transform: scale(0.95); }
</style>
