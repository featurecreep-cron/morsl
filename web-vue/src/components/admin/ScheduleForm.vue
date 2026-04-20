<template>
  <div v-show="admin.showScheduleForm" class="schedule-form">
    <div class="branding-subheader">Schedule</div>
    <div class="settings-row" v-show="admin.templates.length > 0">
      <div class="settings-label">Type</div>
      <div class="schedule-type-toggle">
        <button type="button" class="schedule-type-btn"
                :class="{ active: admin.scheduleForm.mode === 'profile' }"
                @click="admin.scheduleForm.mode = 'profile'">Profile</button>
        <button type="button" class="schedule-type-btn"
                :class="{ active: admin.scheduleForm.mode === 'template' }"
                @click="admin.scheduleForm.mode = 'template'">Template</button>
      </div>
    </div>
    <small class="section-help" v-show="admin.scheduleForm.mode === 'profile'" style="padding:0.25rem 0.75rem;">Generate a menu from one profile, repeated on the days you select.</small>
    <small class="section-help" v-show="admin.scheduleForm.mode === 'template'" style="padding:0.25rem 0.75rem;">Repeat a weekly template to automatically create multi-day meal plans. Create and edit templates on the Weekly tab.</small>
    <div class="settings-row" v-show="admin.scheduleForm.mode === 'profile'">
      <div class="settings-label">Profile</div>
      <select class="drawer-select" v-model="admin.scheduleForm.profile">
        <option v-for="p in admin.profiles" :key="p.name" :value="p.name">{{ p.name }}</option>
      </select>
    </div>
    <div class="settings-row" v-show="admin.scheduleForm.mode === 'template'">
      <div class="settings-label">Template</div>
      <select class="drawer-select" v-model="admin.scheduleForm.template">
        <option v-for="t in admin.templates" :key="t.name" :value="t.name">{{ t.name }}</option>
      </select>
    </div>
    <div class="settings-row" v-show="admin.scheduleForm.mode === 'profile'">
      <div class="settings-label">Days</div>
      <div class="schedule-day-picker">
        <button v-for="d in SCHEDULE_DAYS" :key="d.key" type="button"
                class="schedule-day-btn"
                :class="{ active: admin.scheduleForm._selectedDays.includes(d.key) }"
                @click="admin.toggleScheduleDay(d.key)">
          {{ d.label }}
        </button>
      </div>
    </div>
    <div class="settings-row">
      <div class="settings-label">Time</div>
      <div class="schedule-time-group">
        <input type="number" class="drawer-input drawer-input--small"
               v-model.number="admin.scheduleForm.hour" min="0" max="23">
        <span class="schedule-time-sep">:</span>
        <input type="number" class="drawer-input drawer-input--small"
               v-model.number="admin.scheduleForm.minute" min="0" max="59">
        <span class="schedule-time-hint">24h</span>
      </div>
    </div>
    <div class="schedule-preview">
      Runs {{ admin.formatScheduleDays(admin.scheduleForm.day_of_week) }} at {{ String(admin.scheduleForm.hour).padStart(2,'0') }}:{{ String(admin.scheduleForm.minute).padStart(2,'0') }} ({{ admin.settings.timezone || 'UTC' }})
    </div>
    <!-- Advanced: schedule options -->
    <div v-show="admin.tierVisible('standard')">
      <div class="branding-subheader">Options</div>
      <ToggleSetting label="Enabled" v-model="admin.scheduleForm.enabled" />
      <ToggleSetting label="Clear existing menus" v-model="admin.scheduleForm.clear_before_generate" />
      <div class="settings-hint">Remove other shelves when this schedule generates</div>
    </div>
    <!-- Advanced: meal plan integration -->
    <div v-show="admin.tierVisible('standard')">
      <div class="branding-subheader">Meal Plan</div>
      <ToggleSetting label="Save to Meal Plan" v-model="admin.scheduleForm.create_meal_plan" />
      <div v-show="admin.scheduleForm.create_meal_plan" class="schedule-subgroup">
        <div class="settings-row">
          <div class="settings-label">Meal Type</div>
          <select class="drawer-select" v-model.number="admin.scheduleForm.meal_plan_type">
            <option :value="null">-- select --</option>
            <option v-for="mt in admin.mealTypes" :key="mt.id" :value="mt.id">{{ mt.name }}</option>
          </select>
        </div>
        <div class="settings-row">
          <div class="settings-label">
            Uncooked Meal Cleanup
            <small>Automatically remove uncooked meal plans older than this many days (0 = off)</small>
          </div>
          <input type="number" class="drawer-input drawer-input--small"
                 v-model.number="admin.scheduleForm.cleanup_uncooked_days"
                 min="0" max="30">
        </div>
      </div>
    </div>
    <div class="schedule-form-actions">
      <button class="btn-generate" @click="admin.saveSchedule()">Save</button>
      <button class="btn-generate btn-secondary" @click="admin.showScheduleForm = false; admin.editingScheduleId = null;">Cancel</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import ToggleSetting from '@/components/shared/ToggleSetting.vue'
import { useAdminStore, SCHEDULE_DAYS } from '@/stores/admin'

const admin = useAdminStore()
</script>
