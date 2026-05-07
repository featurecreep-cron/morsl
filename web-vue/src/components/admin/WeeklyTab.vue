<template>
  <div id="panel-weekly" role="tabpanel" aria-labelledby="tab-weekly">

    <!-- Templates -->
    <section class="admin-section">
      <h2 class="section-title">Meal Plan Templates</h2>
      <small class="section-help">Templates define multi-day meal plans — which profiles, days, and meal types. Generate one manually below. To auto-generate weekly plans on a schedule, create a schedule on the Generate tab and choose "Template" mode.</small>
      <button class="btn-generate btn-secondary" @click="admin.startNewTemplate()"
              style="margin-bottom:0.75rem; height:30px; font-size:0.85rem;">
        + New Template
      </button>
      <div v-show="admin.templates.length === 0" class="tag-empty">No templates yet. Create one to get started.</div>
      <div v-for="t in admin.templates" :key="t.name"
           class="constraint-chip" style="justify-content:space-between;">
        <span style="flex:1; display:flex; flex-wrap:wrap; align-items:center; gap:0.35rem;">
          <strong>{{ t.name }}</strong>
          <span v-show="t.description" style="color:var(--text-muted); font-size:0.8rem;">{{ t.description }}</span>
          <span class="schedule-badge">{{ t.slot_count }} slot{{ t.slot_count !== 1 ? 's' : '' }}</span>
        </span>
        <span style="display:flex; gap:0.15rem;">
          <button class="btn-chip-remove" @click.stop="admin.startEditTemplate(t.name)" title="Edit" style="color:var(--accent-color);">&#9998;</button>
          <button class="btn-chip-remove" @click.stop="admin.deleteTemplate(t.name)" title="Delete">&times;</button>
        </span>
      </div>
    </section>

    <!-- Weekly Generation -->
    <section class="admin-section" v-show="admin.templates.length > 0">
      <h2 class="section-title">Generate Weekly Plan</h2>
      <small class="section-help">Generate a multi-day meal plan from a template.</small>
      <div class="generate-row" style="margin-bottom:0.75rem;">
        <select v-model="admin.selectedWeeklyTemplate" :disabled="admin.weeklyGenerating">
          <option v-for="t in admin.templates" :key="t.name" :value="t.name">
            {{ t.name }} ({{ t.slot_count }} slots)
          </option>
        </select>
        <input type="date" class="drawer-input" v-model="admin.weeklyWeekStart"
               :disabled="admin.weeklyGenerating"
               title="Week start date (defaults to this Monday)"
               style="width:auto; max-width:160px;">
        <button class="btn-generate"
                :disabled="admin.weeklyGenerating || !admin.selectedWeeklyTemplate || admin.templates.length === 0"
                @click="admin.generateWeekly()">
          {{ admin.weeklyGenerating ? 'Generating...' : 'Generate' }}
        </button>
      </div>

      <!-- Progress indicators -->
      <div class="weekly-progress" v-show="admin.weeklyStatus.state === 'generating' || admin.weeklyStatus.state === 'complete'">
        <div v-for="(status, profileName) in admin.weeklyStatus.profile_progress" :key="profileName"
             class="weekly-progress-row">
          <span>{{ profileName }}</span>
          <span class="schedule-badge" :class="'pstate--' + status">{{ status }}</span>
        </div>
      </div>
      <div v-for="w in (admin.weeklyStatus.warnings || [])" :key="w"
           class="error-banner" style="margin-top:0.5rem; background:rgba(251,191,36,0.08); border-color:rgba(251,191,36,0.25); color:#fbbf24;">
        {{ w }}
      </div>
      <div class="error-banner" v-show="admin.weeklyStatus.state === 'error'" style="margin-top:0.5rem;">
        <strong>Error:</strong> {{ admin.weeklyStatus.error || 'Generation failed' }}
      </div>
    </section>

    <!-- Plan Viewer -->
    <section class="admin-section" v-show="admin.weeklyPlan">
      <h2 class="section-title">Weekly Plan</h2>
      <div style="display:flex; gap:0.5rem; margin-bottom:0.75rem; flex-wrap:wrap;">
        <button class="btn-generate" @click="admin.saveWeeklyPlan()"
                :disabled="admin.weeklyPlanSaving || admin.weeklyPlanSaved">
          {{ admin.weeklyPlanSaved ? 'Saved' : (admin.weeklyPlanSaving ? 'Saving...' : 'Save to Tandoor') }}
        </button>
        <button class="btn-generate btn-secondary" @click="admin.discardWeeklyPlan()">Discard Plan</button>
      </div>

      <!-- Jump-to-day pills -->
      <div class="plan-day-pills" v-show="admin.weeklyPlanDays.length >= 5">
        <a v-for="entry in admin.weeklyPlanDays" :key="'pill-' + entry.date"
           class="plan-day-pill" :href="'#plan-day-' + entry.date">
          {{ weeklyPlanDayLabel(entry.date) }}
        </a>
      </div>

      <!-- Daily swim lanes -->
      <div class="plan-lanes">
        <div v-for="entry in admin.weeklyPlanDays" :key="'day-' + entry.date"
             class="plan-day" :id="'plan-day-' + entry.date">
          <div class="plan-day-header">
            <span>{{ weeklyPlanDayLabel(entry.date) }}</span>
            <small style="color:var(--text-muted);">{{ entry.date }}</small>
          </div>
          <div class="plan-day-slots">
            <div v-for="[mtId, meal] in Object.entries(entry.data.meals || {})" :key="entry.date + '-' + mtId"
                 class="plan-slot">
              <div class="plan-slot-header">
                <span>{{ meal.meal_type_name || ('Type ' + mtId) }}</span>
                <button class="plan-slot-regen" title="Regenerate this slot"
                        :disabled="admin.weeklyRegenSlot !== null"
                        @click="admin.regenerateSlot(entry.date, Number(mtId))">
                  <span v-show="admin.weeklyRegenSlot?.date === entry.date && admin.weeklyRegenSlot?.mealTypeId === Number(mtId)">...</span>
                  <span v-show="!(admin.weeklyRegenSlot?.date === entry.date && admin.weeklyRegenSlot?.mealTypeId === Number(mtId))">&#8635;</span>
                </button>
              </div>
              <div class="plan-slot-recipes">
                <div v-for="recipe in (meal.recipes || [])" :key="recipe.id"
                     class="plan-recipe-card" @click="admin.openRecipe(recipe)">
                  <img class="plan-recipe-img" v-show="recipe.image"
                       :src="recipe.image ?? undefined" :alt="recipe.name"
                       @error="($event.target as HTMLElement).style.display='none'">
                  <span class="plan-recipe-name">{{ recipe.name }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

  </div>
</template>

<script setup lang="ts">
import { useAdminStore } from '@/stores/admin'

const admin = useAdminStore()

const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function weeklyPlanDayLabel(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  return DAY_NAMES[d.getDay()] + ' ' + (d.getMonth() + 1) + '/' + d.getDate()
}
</script>
