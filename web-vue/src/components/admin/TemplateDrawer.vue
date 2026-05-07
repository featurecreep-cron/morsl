<template>
  <Teleport to="body">
    <!-- Template Editor Backdrop -->
    <Transition name="drawer-backdrop">
      <div class="drawer-backdrop"
           v-show="admin.editingTemplate"
           @click="admin.cancelEditTemplate()">
      </div>
    </Transition>

    <!-- Template Editor Drawer -->
    <Transition name="drawer-slide">
      <div class="profile-drawer"
           :class="{ open: admin.editingTemplate }"
           v-show="admin.editingTemplate"
           role="dialog" aria-modal="true" aria-labelledby="template-drawer-title">
        <div class="drawer-header">
          <h3 id="template-drawer-title">{{ admin.isNewTemplate ? 'New Template' : 'Edit Template' }}</h3>
          <button class="drawer-close" @click="admin.cancelEditTemplate()" aria-label="Close">&times;</button>
        </div>

        <div class="drawer-body">
          <div class="drawer-section">
            <label class="drawer-label">Name</label>
            <input type="text" v-model="admin.templateEditor.name" :disabled="!admin.isNewTemplate"
                   class="drawer-input" placeholder="e.g. weeknight-dinners">
          </div>
          <div class="drawer-section">
            <label class="drawer-label">Description</label>
            <input type="text" v-model="admin.templateEditor.description"
                   class="drawer-input" placeholder="Optional description">
          </div>
          <div class="drawer-section">
            <ToggleSetting label="Deduplicate Recipes" help="Avoid the same recipe on different days" v-model="admin.templateEditor.deduplicate" style="border:none; padding:0;" />
          </div>

          <!-- Slots -->
          <div class="drawer-section">
            <label class="drawer-label">
              Slots
              <span class="constraint-count-badge">{{ admin.templateEditor.slots?.length || 0 }}</span>
            </label>
            <div class="constraint-list">
              <div v-for="(slot, sIdx) in (admin.templateEditor.slots || [])" :key="sIdx"
                   class="template-slot-card" :class="{ expanded: admin.expandedSlot === sIdx }">
                <div class="template-slot-header" @click="admin.toggleSlotExpand(sIdx)">
                  <span>{{ (slot.meal_type_name || 'Meal Type ' + slot.meal_type_id) + ' \u2014 ' + slot.profile }}</span>
                  <span style="font-size:0.75rem; color:var(--text-muted);">{{ slot.days.length }} days, {{ itemNounText(slot.recipes_per_day, admin.resolveNoun(slot.profile)) }}/day</span>
                  <span class="constraint-expand-icon">{{ admin.expandedSlot === sIdx ? '\u25B2' : '\u25BC' }}</span>
                </div>
                <div class="template-slot-detail" v-show="admin.expandedSlot === sIdx">
                  <div class="constraint-field">
                    <label>Days</label>
                    <div class="schedule-day-picker">
                      <button v-for="d in scheduleDays" :key="'slot-' + sIdx + '-' + d.key"
                              type="button" class="schedule-day-btn"
                              :class="{ active: slot.days.includes(d.key) }"
                              @click="admin.toggleSlotDay(sIdx, d.key)">
                        {{ d.label }}
                      </button>
                    </div>
                  </div>
                  <div class="constraint-field">
                    <label>Meal Type</label>
                    <select class="drawer-select" v-model.number="slot.meal_type_id"
                            @change="slot.meal_type_name = admin.mealTypes.find(m => m.id === slot.meal_type_id)?.name || ''">
                      <option v-for="mt in admin.mealTypes" :key="mt.id" :value="mt.id">{{ mt.name }}</option>
                    </select>
                  </div>
                  <div class="constraint-field">
                    <label>Profile</label>
                    <select class="drawer-select" v-model="slot.profile">
                      <option v-for="p in admin.profiles" :key="p.name" :value="p.name">{{ p.name }}</option>
                    </select>
                  </div>
                  <div class="constraint-field">
                    <label>Recipes Per Day</label>
                    <input type="number" class="drawer-input drawer-input--small"
                           v-model.number="slot.recipes_per_day" min="1" max="10">
                  </div>
                  <div class="constraint-actions">
                    <button class="constraint-action-btn constraint-action-btn--danger" @click="admin.removeSlot(sIdx)" title="Remove slot">Remove</button>
                  </div>
                </div>
              </div>
              <div class="constraint-empty-state" v-show="!admin.templateEditor.slots || admin.templateEditor.slots.length === 0">
                No slots defined. Add slots to configure which meals appear on which days.
              </div>
            </div>
            <button class="btn-add-constraint" @click="admin.addSlot()" type="button" style="margin-top:0.5rem;">
              + Add Slot
            </button>
          </div>
        </div>

        <div class="drawer-footer">
          <button class="btn-generate" @click="admin.saveTemplate()" :disabled="admin.templateSaving" style="margin-left:auto;">
            {{ admin.templateSaving ? 'Saving...' : 'Save Template' }}
          </button>
          <button class="btn-generate btn-secondary" @click="admin.cancelEditTemplate()">Cancel</button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import ToggleSetting from '@/components/shared/ToggleSetting.vue'
import { useAdminStore, SCHEDULE_DAYS } from '@/stores/admin'
import { itemNounText } from '@/utils/formatting'

const admin = useAdminStore()
const scheduleDays = SCHEDULE_DAYS
</script>

<style scoped>
.drawer-backdrop-enter-active { transition: opacity 0.2s ease-out; }
.drawer-backdrop-leave-active { transition: opacity 0.2s ease-in; }
.drawer-backdrop-enter-from,
.drawer-backdrop-leave-to { opacity: 0; }

.drawer-slide-enter-active { transition: transform 0.3s ease-out; }
.drawer-slide-leave-active { transition: transform 0.2s ease-in; }
.drawer-slide-enter-from { transform: translateX(100%); }
.drawer-slide-leave-to { transform: translateX(100%); }
</style>
