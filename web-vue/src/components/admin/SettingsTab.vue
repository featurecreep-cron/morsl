<template>
  <div id="panel-settings" role="tabpanel" aria-labelledby="tab-settings">

    <!-- Appearance -->
    <section class="admin-section">
      <h2 class="section-title">Appearance</h2>
      <div v-show="admin.settingsLoaded" class="settings-grid">
        <div class="settings-row">
          <div class="settings-label">
            Theme
            <small>Visual theme for the menu</small>
          </div>
          <select class="drawer-select"
                  :value="admin.settings.theme || 'cast-iron'"
                  @change="admin.changeTheme(($event.target as HTMLSelectElement).value)">
            <option v-for="[key, info] in sortedThemes" :key="key"
                    :value="key" :selected="key === (admin.settings.theme || 'cast-iron')">
              {{ info.label }}
            </option>
          </select>
        </div>
      </div>
    </section>

    <!-- Requests -->
    <section class="admin-section" v-show="admin.tierVisible('advanced')">
      <h2 class="section-title">Requests</h2>
      <div v-show="admin.settingsLoaded" class="settings-grid">
        <ToggleSetting label="Requests Enabled" help="Show request buttons on the menu page"
                       :model-value="admin.settings.orders_enabled !== false"
                       @update:model-value="admin.toggleSetting('orders_enabled', $event)" />
        <ToggleSetting v-show="admin.settings.orders_enabled !== false"
                       label="Save Requests to Tandoor" help="Save requests to Tandoor as meal plan entries"
                       :model-value="admin.settings.save_orders_to_tandoor !== false"
                       @update:model-value="admin.toggleSetting('save_orders_to_tandoor', $event)" />
        <div class="settings-row" v-show="admin.settings.orders_enabled !== false && admin.settings.save_orders_to_tandoor !== false" style="border-top:none; padding-top:0;">
          <div class="settings-label">
            Request Meal Type
            <small>Meal type used when saving requests to Tandoor</small>
          </div>
          <div style="display:flex; flex-wrap:wrap; gap:0.5rem; align-items:center;">
            <select class="drawer-select"
                    :value="admin.settings.order_meal_type_id || ''"
                    @change="admin.toggleSetting('order_meal_type_id', ($event.target as HTMLSelectElement).value ? Number(($event.target as HTMLSelectElement).value) : null)">
              <option value="" disabled v-show="!admin.mealTypes.length">No meal types found</option>
              <option v-for="mt in admin.mealTypes" :key="mt.id" :value="mt.id">{{ mt.name }}</option>
            </select>
            <button class="btn-generate btn-secondary"
                    v-show="!admin.showNewMealType"
                    @click="admin.showNewMealType = true"
                    style="height:30px; font-size:0.8rem; padding:0 0.75rem;">+ New</button>
            <div v-show="admin.showNewMealType" style="display:flex; gap:0.25rem; align-items:center;">
              <input type="text" class="drawer-input" v-model="admin.newMealTypeName"
                     placeholder="Type name" style="width:140px; height:30px; font-size:0.85rem;"
                     @keydown.enter="admin.createMealType()" @keydown.escape="admin.showNewMealType = false">
              <button class="btn-generate" @click="admin.createMealType()"
                      style="height:30px; font-size:0.8rem; padding:0 0.75rem;">Save</button>
              <button class="btn-generate btn-secondary" @click="admin.showNewMealType = false; admin.newMealTypeName = ''"
                      style="height:30px; font-size:0.8rem; padding:0 0.5rem;">Cancel</button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Menu Card Display -->
    <section class="admin-section" v-show="admin.tierVisible('standard')">
      <h2 class="section-title">Menu Card Display</h2>
      <small class="section-help">Controls what customers see on the menu page.</small>
      <div v-show="admin.settingsLoaded" class="settings-grid">
        <ToggleSetting label="Show Ratings" help="Display star ratings on menu cards"
                       :model-value="admin.settings.show_ratings !== false"
                       @update:model-value="admin.toggleSetting('show_ratings', $event)" />
        <ToggleSetting label="Show Ingredients" help="Display ingredient lists on menu cards"
                       :model-value="admin.settings.show_ingredients !== false"
                       @update:model-value="admin.toggleSetting('show_ingredients', $event)" />
        <ToggleSetting label="Show Descriptions" help="Display recipe descriptions on menu cards"
                       :model-value="admin.settings.show_descriptions !== false"
                       @update:model-value="admin.toggleSetting('show_descriptions', $event)" />
        <ToggleSetting label="Show Instructions" help="Display cooking instructions in the recipe popup"
                       :model-value="admin.settings.show_instructions === true"
                       @update:model-value="admin.toggleSetting('show_instructions', $event)" />
        <ToggleSetting label="Enable Rating" help="Let users rate recipes from the menu page"
                       :model-value="admin.settings.ratings_enabled !== false"
                       @update:model-value="admin.toggleSetting('ratings_enabled', $event)" />
      </div>
    </section>

    <!-- Admin Card Display -->
    <section class="admin-section" v-show="admin.tierVisible('standard')">
      <h2 class="section-title">Admin Card Display</h2>
      <small class="section-help">Controls what you see on admin recipe cards.</small>
      <div v-show="admin.settingsLoaded" class="settings-grid">
        <ToggleSetting label="Show Ratings" help="Display star ratings on admin cards"
                       :model-value="admin.settings.admin_show_ratings !== false"
                       @update:model-value="admin.toggleSetting('admin_show_ratings', $event)" />
        <ToggleSetting label="Show Ingredients" help="Display ingredient count on admin cards"
                       :model-value="admin.settings.admin_show_ingredients !== false"
                       @update:model-value="admin.toggleSetting('admin_show_ingredients', $event)" />
        <ToggleSetting label="Show Descriptions" help="Display recipe descriptions in admin modal"
                       :model-value="admin.settings.admin_show_descriptions !== false"
                       @update:model-value="admin.toggleSetting('admin_show_descriptions', $event)" />
        <ToggleSetting label="Show Instructions" help="Display cooking instructions in admin modal"
                       :model-value="admin.settings.admin_show_instructions !== false"
                       @update:model-value="admin.toggleSetting('admin_show_instructions', $event)" />
      </div>
    </section>

    <!-- Tandoor Integration -->
    <section class="admin-section" v-show="admin.tierVisible('standard')">
      <h2 class="section-title">Tandoor Integration</h2>
      <div v-show="!admin.settingsLoaded" class="tag-empty">Loading settings...</div>
      <div v-show="admin.settingsLoaded" class="settings-grid">
        <!-- Tandoor Connection -->
        <div class="settings-row" style="flex-direction:column; align-items:stretch; gap:0.5rem;">
          <div class="settings-label">
            Tandoor Connection
            <small v-show="admin.credEnvLocked">Credentials are set via environment variables and cannot be changed here.</small>
            <small v-show="!admin.credEnvLocked">URL and API token for your Tandoor instance.</small>
          </div>
          <div v-show="!admin.credEditing && !admin.credEnvLocked" style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
            <span style="font-size:0.85rem; color:var(--text-muted);">{{ admin.settings.tandoor_url || 'Not configured' }}</span>
            <span v-show="admin.settings.has_tandoor_token" style="font-size:0.75rem; color:var(--accent);">&#10003; Token saved</span>
            <button class="btn btn-sm" @click="startCredEdit" style="margin-left:auto;">Change</button>
          </div>
          <div v-show="admin.credEnvLocked" style="display:flex; align-items:center; gap:0.5rem;">
            <span style="font-size:0.85rem; color:var(--text-muted);">{{ admin.settings.tandoor_url || 'Set via TANDOOR_URL' }}</span>
            <span style="font-size:0.75rem; color:var(--accent);">&#10003; ENV</span>
          </div>
          <div v-show="admin.credEditing" style="display:flex; flex-direction:column; gap:0.5rem;">
            <input type="url" class="drawer-input" v-model="admin.credUrl" placeholder="https://tandoor.example.com" style="width:100%;">
            <input type="password" class="drawer-input" v-model="admin.credToken" placeholder="API token (leave blank to keep current)" style="width:100%;">
            <div v-show="admin.credTestResult" style="font-size:0.85rem; padding:0.3rem 0;"
                 :style="admin.credTestResult?.success ? 'color:var(--accent)' : 'color:var(--error, #e74c3c)'">
              <span v-show="admin.credTestResult?.success">&#10003; Connection successful</span>
              <span v-show="admin.credTestResult && !admin.credTestResult.success">&#10007; {{ admin.credTestResult?.error || 'Connection failed' }}</span>
            </div>
            <p v-show="admin.credError" style="font-size:0.85rem; color:var(--error, #e74c3c);">{{ admin.credError }}</p>
            <div style="display:flex; gap:0.5rem;">
              <button class="btn btn-sm" :disabled="!admin.credUrl || admin.credTesting" @click="admin.testCredentials()">
                <span v-show="!admin.credTesting">Test Connection</span>
                <span v-show="admin.credTesting">Testing...</span>
              </button>
              <button class="btn btn-sm btn-primary" :disabled="!admin.credTestResult?.success || admin.credSaving" @click="admin.saveCredentials()">
                <span v-show="!admin.credSaving">Save</span>
                <span v-show="admin.credSaving">Saving...</span>
              </button>
              <button class="btn btn-sm" @click="admin.credEditing = false">Cancel</button>
            </div>
          </div>
        </div>
        <ToggleSetting label="Save to Tandoor Meal Plans" help="Add a &quot;Save to Meal Plan&quot; button on the menu page for saving generated menus to Tandoor"
                       :model-value="admin.settings.meal_plan_enabled !== false"
                       @update:model-value="admin.toggleSetting('meal_plan_enabled', $event)" />
        <div class="settings-row">
          <div class="settings-label">
            API Cache
            <small>How long to cache data from Tandoor. Lower values show fresher data but make more requests.</small>
          </div>
          <!-- Preset dropdown (Standard/Advanced) -->
          <select v-show="!admin.tierVisible('advanced')" class="drawer-input"
                  :value="admin.settings.api_cache_minutes ?? 240"
                  @change="admin.toggleSetting('api_cache_minutes', Number(($event.target as HTMLSelectElement).value))"
                  style="width:140px;">
            <option value="15">15 minutes</option>
            <option value="60">1 hour</option>
            <option value="240">4 hours</option>
            <option value="720">12 hours</option>
            <option value="1440">24 hours</option>
          </select>
          <!-- Raw number (Expert) -->
          <div v-show="admin.tierVisible('advanced')" style="display:flex; align-items:center; gap:0.4rem;">
            <input type="number" class="drawer-input drawer-input--small"
                   :value="admin.settings.api_cache_minutes ?? 240" min="0"
                   @change="admin.toggleSetting('api_cache_minutes', Number(($event.target as HTMLInputElement).value))"
                   style="width:80px;">
            <span style="font-size:0.8rem; color:var(--text-muted);">min</span>
          </div>
        </div>
        <ToggleSetting label="Save Ratings to Tandoor" help="Send ratings back to Tandoor when users rate recipes"
                       :model-value="admin.settings.save_ratings_to_tandoor !== false"
                       @update:model-value="admin.toggleSetting('save_ratings_to_tandoor', $event)" />
        <div class="settings-row">
          <div class="settings-label">
            Timezone
            <small>Controls when scheduled menus fire. Set via the <code>TZ</code> environment variable in your Docker Compose file.</small>
          </div>
          <span class="drawer-input" style="width:220px; opacity:0.7; cursor:default;">{{ admin.settings.timezone || 'UTC' }}</span>
        </div>
      </div>
    </section>

    <!-- Advanced Tuning -->
    <section class="admin-section" v-show="admin.tierVisible('advanced')">
      <h2 class="section-title">Advanced Tuning</h2>
      <div v-show="!admin.settingsLoaded" class="tag-empty">Loading settings...</div>
      <div v-show="admin.settingsLoaded" class="settings-grid">
        <div class="settings-row">
          <label class="settings-label" for="setting-menu-poll">
            Menu Poll Interval
            <small>How often (in seconds) the menu page refreshes to check for new menus</small>
          </label>
          <input type="number" id="setting-menu-poll"
                 class="drawer-input drawer-input--small"
                 :value="admin.settings.menu_poll_seconds ?? 60" min="10" max="300"
                 @change="admin.toggleSetting('menu_poll_seconds',
                     Math.max(10, Math.min(300, Number(($event.target as HTMLInputElement).value) || 60)))">
        </div>
        <div class="settings-row">
          <label class="settings-label" for="setting-toast">
            Toast Duration
            <small>How long (in seconds) to show confirmation messages</small>
          </label>
          <input type="number" id="setting-toast"
                 class="drawer-input drawer-input--small"
                 :value="admin.settings.toast_seconds ?? 2" min="1" max="10"
                 @change="admin.toggleSetting('toast_seconds',
                     Math.max(1, Math.min(10, Number(($event.target as HTMLInputElement).value) || 2)))">
        </div>
        <div class="settings-row">
          <label class="settings-label" for="setting-max-discover">
            Max Discover Generations
            <small>How many menu generations to keep in the history carousel</small>
          </label>
          <input type="number" id="setting-max-discover"
                 class="drawer-input drawer-input--small"
                 :value="admin.settings.max_discover_generations ?? 10" min="1" max="50"
                 @change="admin.toggleSetting('max_discover_generations',
                     Math.max(1, Math.min(50, Number(($event.target as HTMLInputElement).value) || 10)))">
        </div>
        <div class="settings-row">
          <label class="settings-label" for="setting-max-previous">
            Max Previous Recipes
            <small>Number of recently shown recipes to track for the 'previously seen' section</small>
          </label>
          <input type="number" id="setting-max-previous"
                 class="drawer-input drawer-input--small"
                 :value="admin.settings.max_previous_recipes ?? 50" min="10" max="200"
                 @change="admin.toggleSetting('max_previous_recipes',
                     Math.max(10, Math.min(200, Number(($event.target as HTMLInputElement).value) || 50)))">
        </div>
      </div>
    </section>

    <!-- Security & Kiosk -->
    <section class="admin-section">
      <h2 class="section-title">Security &amp; Kiosk</h2>
      <div v-show="!admin.settingsLoaded" class="tag-empty">Loading settings...</div>
      <div v-show="admin.settingsLoaded" class="settings-grid">
        <ToggleSetting label="Require PIN for Admin" help="Require a PIN to access the admin page"
                       :model-value="!!admin.settings.admin_pin_enabled"
                       @update:model-value="admin.toggleSetting('admin_pin_enabled', $event)" />
        <ToggleSetting v-show="admin.tierVisible('standard')"
                       label="Enable Kiosk Mode" help="Restrict the menu page for unattended display (hides navigation, prevents changes)"
                       :model-value="!!admin.settings.kiosk_enabled"
                       @update:model-value="admin.toggleSetting('kiosk_enabled', $event)" />
        <div class="settings-row" v-show="admin.tierVisible('standard') && admin.settings.kiosk_enabled">
          <div class="settings-label">
            Admin Access Method
            <small>How to reach the admin panel from the menu page</small>
          </div>
          <select class="drawer-select"
                  :value="admin.settings.kiosk_gesture || 'menu'"
                  @change="admin.toggleSetting('kiosk_gesture', ($event.target as HTMLSelectElement).value)">
            <option value="menu">Menu (hamburger visible)</option>
            <option value="double-tap">Double Tap header</option>
            <option value="long-press">Long Press header</option>
            <option value="swipe-up">Swipe Up from bottom</option>
          </select>
        </div>
        <ToggleSetting v-show="admin.tierVisible('standard') && admin.settings.kiosk_enabled"
                       label="Kiosk PIN" help="Require the PIN when using the kiosk gesture to access admin"
                       :model-value="!!admin.settings.kiosk_pin_enabled"
                       @update:model-value="admin.toggleSetting('kiosk_pin_enabled', $event)" />
        <div class="settings-row" v-show="admin.settings.admin_pin_enabled || (admin.settings.kiosk_enabled && admin.settings.kiosk_pin_enabled)">
          <div class="settings-label">
            PIN Code
            <small v-show="admin.settings.has_pin" style="color: var(--success-text, #6b9e5a);">PIN is set</small>
            <small v-show="!admin.settings.has_pin" style="color: var(--warning-text, #ffc107);">No PIN set &mdash; admin access is unrestricted</small>
          </div>
          <div style="display:flex; gap:0.5rem; align-items:center;">
            <input type="password" class="drawer-input" style="max-width:160px; letter-spacing:0.2em; text-align:center;"
                   :placeholder="admin.settings.has_pin ? '••••' : 'Enter PIN'"
                   @change="admin.toggleSetting('pin', ($event.target as HTMLInputElement).value); ($event.target as HTMLInputElement).value = ''"
                   autocomplete="off">
            <button type="button" class="btn-branding" v-show="admin.settings.has_pin"
                    @click="admin.toggleSetting('pin', '')"
                    style="white-space:nowrap;">Clear</button>
          </div>
        </div>
        <div class="settings-row" v-show="admin.settings.admin_pin_enabled || (admin.settings.kiosk_enabled && admin.settings.kiosk_pin_enabled)">
          <div class="settings-label">
            PIN Session Timeout
            <small>How long the PIN stays valid after entry</small>
          </div>
          <select class="drawer-select"
                  :value="admin.settings.pin_timeout ?? 0"
                  @change="admin.toggleSetting('pin_timeout', parseInt(($event.target as HTMLSelectElement).value))">
            <option value="0">Every visit (immediate)</option>
            <option value="30">30 seconds</option>
            <option value="60">1 minute</option>
            <option value="300">5 minutes</option>
          </select>
        </div>
      </div>
    </section>

    <!-- Factory Reset -->
    <section class="admin-section" v-show="admin.tierVisible('standard')">
      <h2 class="section-title">Factory Reset</h2>
      <small class="section-help">Erase all profiles, categories, schedules, history, branding, and settings. Returns the app to first-run state.</small>
      <div style="margin-top: 0.75rem;">
        <button class="btn-generate btn-danger" @click="admin.factoryReset()">Reset Everything</button>
      </div>
    </section>

  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ToggleSetting from '@/components/shared/ToggleSetting.vue'
import { useAdminStore } from '@/stores/admin'

const admin = useAdminStore()

const sortedThemes = computed(() =>
  Object.entries(admin.themeRegistry).sort((a, b) => a[1].label.localeCompare(b[1].label))
)

function startCredEdit() {
  admin.credEditing = true
  admin.credUrl = admin.settings.tandoor_url || ''
  admin.credToken = ''
  admin.credTestResult = null
  admin.credError = ''
}
</script>
