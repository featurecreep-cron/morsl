<template>
  <div id="panel-generate" role="tabpanel" aria-labelledby="tab-generate">

    <!-- Generate from Profile -->
    <section class="admin-section">
      <h2 class="section-title">
        Generate Menu
      </h2>
      <small class="section-help">Pick a profile and create a new menu.</small>
      <div class="generate-row">
        <select v-model="admin.selectedProfile" :disabled="admin.status.state === 'generating'">
          <option v-for="p in admin.profiles" :key="p.name" :value="p.name"
                  :title="p.constraint_count ? 'Rules filter which recipes are eligible — keyword requirements, rating minimums, ingredient preferences, etc.' : 'No rules — this profile picks from all your recipes'">
            {{ p.name }} ({{ itemNounText(p.choices, p.item_noun || admin.settings.item_noun) }}, {{ p.constraint_count }} rules)
          </option>
        </select>
        <button class="btn-generate"
                :disabled="admin.status.state === 'generating' || !admin.selectedProfile"
                @click="admin.generateProfile()">
          {{ admin.status.state === 'generating' ? 'Generating...' : 'Generate' }}
        </button>
      </div>
    </section>

    <!-- Schedule Menu -->
    <section class="admin-section">
      <h2 class="section-title">Schedule Menu</h2>
      <small class="section-help">Automatically generate menus on a recurring schedule.</small>
      <button class="btn-generate btn-secondary" @click="admin.startNewSchedule()"
              style="margin-bottom:0.75rem; height:30px; font-size:0.85rem;">
        + Add Schedule
      </button>

      <!-- Schedule Form -->
      <ScheduleForm />

      <div v-show="admin.schedules.length === 0 && !admin.showScheduleForm" class="tag-empty">No schedules configured</div>
      <div v-for="s in admin.schedules" :key="s.id"
           class="constraint-chip schedule-chip" :class="{ 'schedule-chip--disabled': !s.enabled }">
        <span style="flex:1; display:flex; flex-wrap:wrap; align-items:center; gap:0.35rem;">
          <strong>{{ s.template || s.profile }}</strong>
          <span v-show="s.template" class="schedule-badge">Weekly</span>
          <span>{{ admin.formatScheduleDays(s.day_of_week) }} @ {{ String(s.hour).padStart(2,'0') }}:{{ String(s.minute).padStart(2,'0') }} {{ admin.settings.timezone || 'UTC' }}</span>
          <span v-show="s.create_meal_plan" class="schedule-badge">Meal Plan</span>
          <span v-show="!s.enabled" class="schedule-badge schedule-badge--off">Disabled</span>
        </span>
        <small v-show="s.last_run" class="schedule-chip-meta">Last: {{ s.last_run ? new Date(s.last_run).toLocaleString() : '' }}</small>
        <span style="display:flex; gap:0.15rem;">
          <button class="btn-chip-remove" @click.stop="admin.toggleScheduleEnabled(s)" :title="s.enabled ? 'Disable' : 'Enable'"
                  style="font-size:0.8rem;" v-html="s.enabled ? '&#10004;' : '&#10006;'"></button>
          <button class="btn-chip-remove" @click.stop="admin.editSchedule(s)" title="Edit" style="color:var(--accent-color);">&#9998;</button>
          <button class="btn-chip-remove" @click.stop="admin.deleteSchedule(s.id)" title="Delete">&times;</button>
        </span>
      </div>
    </section>

    <!-- Current Menu -->
    <section class="admin-section">
      <h2 class="section-title">Current Menu</h2>
      <div style="margin-bottom: 0.75rem;">
        <button class="btn-generate btn-secondary" @click="admin.clearMenu()"
                style="height:30px; font-size:0.85rem;">
          Clear Menu
        </button>
      </div>
      <p v-if="admin.recipes.length === 0" class="text-muted" style="opacity:0.6; font-size:0.9rem;">No menu generated.</p>
      <div class="menu-grid" v-show="admin.recipes.length > 0">
        <div v-for="recipe in admin.recipes" :key="recipe.id"
             class="menu-card" @click="admin.openRecipe(recipe)">
          <img class="menu-card-image" v-show="recipe.image"
               :src="recipe.image ?? undefined" :alt="recipe.name"
               @error="($event.target as HTMLElement).style.display='none'">
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div v-show="!recipe.image" class="menu-card-placeholder" v-html="STOCK_ICON_SVG" />
          <div class="menu-card-body">
            <h3>{{ recipe.name }}</h3>
            <div class="menu-card-meta">
              <span class="stars-interactive" @click.stop v-show="admin.settings.admin_show_ratings !== false">
                <span v-for="i in 5" :key="i" class="star-btn" @click.stop="admin.setRating(recipe.id, i)"
                      :class="{ filled: i <= Math.round(recipe.rating || 0) }">
                  {{ i <= Math.round(recipe.rating || 0) ? '\u2605' : '\u2606' }}
                </span>
              </span>
              <span v-show="admin.settings.admin_show_ingredients !== false">{{ (recipe.ingredients || []).length }} ing.</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Solver Diagnostics -->
    <section class="admin-section" v-show="(admin.warnings.length > 0 || admin.relaxedConstraints.length > 0 || admin.menuMeta.status) && admin.tierVisible('advanced')">
      <h2 class="section-title">Generation Details</h2>
      <small class="section-help">Details about the last menu generation.</small>
      <ul class="diagnostics-list">
        <li v-for="w in admin.warnings" :key="w" class="warn-item">Warning: {{ w }}</li>
        <li v-for="rc in admin.relaxedConstraints" :key="rc.label" class="relax-item">
          {{ rc.label }} adjusted by {{ rc.slack_value.toFixed(1) }} (priority: {{ (rc as Record<string, unknown>).weight }})
        </li>
        <li class="meta-item" v-show="admin.menuMeta.status">Status: {{ admin.formatSolverStatus(admin.menuMeta.status || '') }}</li>
        <li class="meta-item" v-show="admin.menuMeta.requested_count">Requested: {{ itemNounText(admin.menuMeta.requested_count || 0, admin.resolveNoun(admin.selectedProfile)) }}</li>
        <li class="meta-item" v-show="admin.menuMeta.constraint_count">Rules: {{ admin.menuMeta.constraint_count }}</li>
        <li class="meta-item" v-show="admin.menuMeta.generated_at">Generated: {{ admin.menuMeta.generated_at ? new Date(admin.menuMeta.generated_at).toLocaleString() : '' }}</li>
      </ul>
    </section>

    <!-- Error display -->
    <div class="error-banner" v-show="admin.status.state === 'error'">
      <strong>Error:</strong> {{ admin.status.error || 'An error occurred' }}
    </div>

    <!-- Generation History -->
    <section class="admin-section" v-show="admin.tierVisible('standard') && admin.historyTotal > 0">
      <h2 class="section-title">Generation History</h2>
      <small class="section-help">Previous menu generations.</small>

      <div class="history-table">
        <button v-for="h in admin.history" :key="h.id" type="button" class="history-row"
                :aria-expanded="admin.expandedHistoryId === h.id"
                @click="admin.toggleHistoryDetail(h.id)">
          <div class="history-summary">
            <span class="history-date">{{ new Date(h.generated_at).toLocaleString() }}</span>
            <span class="history-profile">{{ h.profile }}</span>
            <span class="history-recipes-count">{{ itemNounText(h.recipe_count, admin.resolveNoun(h.profile)) }}</span>
            <span class="history-status" :class="'status-' + h.status">{{ admin.formatSolverStatus(h.status) }}</span>
            <span class="history-duration">{{ (h.duration_ms / 1000).toFixed(1) }}s</span>
            <span class="history-expand" aria-hidden="true">{{ admin.expandedHistoryId === h.id ? '\u25BE' : '\u25B8' }}</span>
          </div>

          <div v-show="admin.expandedHistoryId === h.id" class="history-detail" @click.stop>
            <div v-if="h.error" class="history-detail-row" style="color:var(--error, #e74c3c);">
              <strong>Error:</strong> {{ h.error }}
            </div>
            <div class="history-detail-row" v-show="h.recipes && h.recipes.length > 0">
              <strong>Recipes:</strong> {{ (h.recipes || []).map(r => r.name).join(', ') }}
            </div>
            <div class="history-detail-row" v-show="h.constraint_count">
              <strong>Constraints:</strong> {{ h.constraint_count }} rules applied
            </div>
            <div v-if="h.relaxed_constraints.length > 0" class="history-detail-row">
              <strong>Relaxed:</strong>
              <span v-for="rc in h.relaxed_constraints" :key="rc.label" class="history-relaxed-chip">
                {{ rc.label }} ({{ rc.slack_value.toFixed(1) }})
              </span>
            </div>
            <div v-if="h.warnings.length > 0" class="history-detail-row">
              <strong>Warnings:</strong>
              <span v-for="w in h.warnings" :key="w" class="warn-item">{{ w }}</span>
            </div>
          </div>
        </button>
      </div>

      <div class="history-footer">
        <div class="history-pagination" v-show="admin.historyTotal > admin.historyPageSize">
          <button class="btn-generate btn-secondary btn-sm" @click="admin.loadHistory(admin.historyPage - 1)" :disabled="admin.historyPage === 0" aria-label="Previous page">&laquo; Prev</button>
          <span>{{ admin.historyPage + 1 }} / {{ admin.historyTotalPages }}</span>
          <button class="btn-generate btn-secondary btn-sm" @click="admin.loadHistory(admin.historyPage + 1)" :disabled="admin.historyPage + 1 >= admin.historyTotalPages" aria-label="Next page">Next &raquo;</button>
        </div>
        <button class="btn-generate btn-secondary btn-sm" @click="admin.clearHistory()">Clear History</button>
      </div>
    </section>

    <!-- Constraint Analytics -->
    <section class="admin-section" v-show="admin.tierVisible('advanced') && admin.analytics && admin.analytics.total_generations > 0">
      <h2 class="section-title">Constraint Analytics</h2>
      <small class="section-help">Usage patterns and statistics across all generated menus.</small>

      <div class="analytics-summary">
        <div class="analytics-stat">
          <div class="analytics-value">{{ admin.analytics.total_generations }}</div>
          <div class="analytics-label">Generations</div>
        </div>
        <div class="analytics-stat">
          <div class="analytics-value">{{ (admin.analytics.avg_duration_ms / 1000).toFixed(1) }}s</div>
          <div class="analytics-label">Avg Duration</div>
        </div>
        <div class="analytics-stat">
          <div class="analytics-value">{{ admin.analytics.avg_recipes_per_generation.toFixed(1) }}</div>
          <div class="analytics-label">Avg Recipes</div>
        </div>
      </div>

      <div v-if="admin.analytics.most_relaxed.length > 0" class="analytics-constraints">
        <div class="section-help" style="margin-bottom:0.5rem;">Most Frequently Relaxed Constraints</div>
        <div v-for="c in admin.analytics.most_relaxed" :key="c.label" class="analytics-constraint-row">
          <span class="analytics-constraint-label">{{ c.label }}</span>
          <span class="analytics-bar">
            <span class="analytics-bar-fill" :style="'width:' + (c.relaxation_rate * 100) + '%'"></span>
          </span>
          <span class="analytics-constraint-pct">{{ (c.relaxation_rate * 100).toFixed(0) }}%</span>
        </div>
      </div>

      <div class="analytics-profiles" v-show="Object.keys(admin.analytics.profile_counts || {}).length > 1">
        <div class="section-help" style="margin-bottom:0.5rem;">Profile Usage</div>
        <div v-for="[name, count] in Object.entries(admin.analytics.profile_counts || {})" :key="name" class="analytics-profile-row">
          <span>{{ name }}</span>
          <span>{{ count }} generations</span>
        </div>
      </div>
    </section>

  </div>
</template>

<script setup lang="ts">
import ScheduleForm from '@/components/admin/ScheduleForm.vue'
import { useAdminStore } from '@/stores/admin'
import { itemNounText } from '@/utils/formatting'
import { STOCK_ICON_SVG } from '@/utils/icons'

const admin = useAdminStore()
</script>
