<template>
  <div id="panel-branding" role="tabpanel" aria-labelledby="tab-branding">

    <section class="admin-section">
      <h2 class="section-title">Branding</h2>
      <div v-show="!admin.settingsLoaded" class="tag-empty">Loading settings...</div>
      <div v-show="admin.settingsLoaded" class="branding-grid">
        <div class="branding-field">
          <label class="branding-label">App Name</label>
          <input type="text" class="drawer-input branding-input"
                 :value="admin.settings.app_name || ''"
                 @change="admin.saveBranding('app_name', ($event.target as HTMLInputElement).value)"
                 placeholder="Morsl">
          <small class="branding-help">Shown in the page header, browser tab title, and app install screen</small>
        </div>
        <div class="branding-field">
          <label class="branding-label">Header Tagline</label>
          <input type="text" class="drawer-input branding-input"
                 :value="admin.settings.slogan_header || ''"
                 @change="admin.saveBranding('slogan_header', ($event.target as HTMLInputElement).value)"
                 placeholder="Optional header tagline">
          <small class="branding-help">Appears below the app name on the menu page</small>
        </div>
        <div class="branding-field">
          <label class="branding-label">Footer Tagline</label>
          <input type="text" class="drawer-input branding-input"
                 :value="admin.settings.slogan_footer || ''"
                 @change="admin.saveBranding('slogan_footer', ($event.target as HTMLInputElement).value)"
                 placeholder="Optional footer tagline">
          <small class="branding-help">Appears at the bottom of the menu page</small>
        </div>
        <div class="branding-field">
          <label class="branding-label">Default Item Noun</label>
          <input type="text" class="drawer-input branding-input"
                 :value="admin.settings.item_noun || ''"
                 @change="admin.saveBranding('item_noun', ($event.target as HTMLInputElement).value)"
                 placeholder="recipe">
          <small class="branding-help">Default label for menu items (e.g. "cocktail", "recipe", "dish"). Each profile can set its own.</small>
        </div>
        <div class="branding-subheader">Images</div>

        <!-- Logo -->
        <BrandingImageField label="Logo" type="logo"
          :image-url="admin.settings.logo_url"
          :show-toggle="true"
          :show-toggle-value="admin.settings.show_logo !== false"
          help-text='Also used for the browser tab icon and loading animation when "Use logo" is enabled'
          accept=".svg,.png,.jpg,.jpeg,.webp"
          @upload="admin.uploadBranding('logo', $event)"
          @remove="admin.removeBranding('logo')"
          @toggle-show="admin.saveBranding('show_logo', $event)" />

        <!-- Favicon -->
        <BrandingImageField label="Favicon &amp; App Icons" type="favicon"
          :image-url="admin.settings.favicon_url"
          :show-use-logo="true"
          :use-logo="admin.settings.favicon_use_logo"
          :logo-url="admin.settings.logo_url"
          help-text="Creates app icons in all required sizes from your image (SVG or PNG)"
          accept=".svg,.png"
          @upload="admin.uploadBranding('favicon', $event)"
          @remove="admin.removeBranding('favicon')"
          @toggle-use-logo="admin.syncIconToLogo('favicon', $event)" />

        <!-- Loading Icon -->
        <BrandingImageField label="Loading Icon" type="loading-icon"
          :image-url="admin.settings.loading_icon_url"
          :show-use-logo="true"
          :use-logo="admin.settings.loading_icon_use_logo"
          :logo-url="admin.settings.logo_url"
          help-text="Displayed while a menu is being generated. Accepts SVG or PNG."
          accept=".svg,.png"
          @upload="admin.uploadBranding('loading-icon', $event)"
          @remove="admin.removeBranding('loading-icon')"
          @toggle-use-logo="admin.syncIconToLogo('loading-icon', $event)" />

        <div class="branding-field">
          <button class="btn-branding btn-branding--reset"
                  @click="admin.resetBranding()">Reset All to Defaults</button>
        </div>
      </div>
    </section>

    <!-- QR Codes -->
    <section class="admin-section" v-show="admin.tierVisible('standard')">
      <h2 class="section-title">QR Codes</h2>
      <small class="section-help">Generate QR codes for the menu page footer. Guests can scan to open the menu on their phone or join your WiFi.</small>
      <div v-show="admin.settingsLoaded" class="settings-grid" style="margin-top:0.75rem;">
        <!-- Menu URL -->
        <div class="settings-row" style="flex-direction:column; align-items:stretch;">
          <label class="branding-label">Menu URL</label>
          <div style="display:flex; gap:0.75rem; align-items:flex-start;">
            <div style="flex:1;">
              <input type="url" class="drawer-input"
                     :value="admin.settings.qr_menu_url || ''"
                     @change="admin.saveQrSetting('qr_menu_url', ($event.target as HTMLInputElement).value)"
                     placeholder="https://menu.example.com">
              <small class="branding-help">The URL guests will reach when they scan this QR code</small>
            </div>
            <div v-show="admin.settings.qr_menu_url" class="qr-preview" ref="qrMenuPreview"></div>
          </div>
        </div>

        <!-- WiFi QR -->
        <div class="settings-row" style="flex-direction:column; align-items:stretch;">
          <label class="branding-label">Guest WiFi</label>
          <div style="display:flex; gap:0.75rem; align-items:flex-start;">
            <div style="flex:1;">
              <div style="display:flex; gap:0.5rem; margin-bottom:0.35rem;">
                <input type="text" class="drawer-input" style="flex:2;"
                       v-model="wifiSsid"
                       @change="saveWifi()"
                       placeholder="Network name (SSID)">
                <select class="drawer-select" style="flex:0 0 auto; width:auto;"
                        v-model="wifiEncryption"
                        @change="saveWifi()">
                  <option value="WPA">WPA/WPA2</option>
                  <option value="WEP">WEP</option>
                  <option value="nopass">Open (no password)</option>
                </select>
              </div>
              <input type="text" class="drawer-input"
                     v-show="wifiEncryption !== 'nopass'"
                     v-model="wifiPassword"
                     @change="saveWifi()"
                     placeholder="WiFi password">
              <small class="branding-help">Generates a QR code that auto-connects phones to your WiFi</small>
            </div>
            <div v-show="admin.settings.qr_wifi_string" class="qr-preview" ref="qrWifiPreview"></div>
          </div>
        </div>

        <!-- Show on menu toggle -->
        <ToggleSetting label="Show on Menu Page" help="Display QR codes in the menu page footer"
                       :model-value="!!admin.settings.qr_show_on_menu"
                       @update:model-value="admin.toggleSetting('qr_show_on_menu', $event)" />
      </div>
    </section>

    <!-- Placeholder Mappings -->
    <section class="admin-section">
      <h2 class="section-title">Placeholder Mappings</h2>
      <small class="section-help">Assign icons to keywords or foods. When a recipe has no photo, the app checks its keywords (A-Z) then its foods (A-Z) and uses the first matching icon.</small>

      <!-- Keyword Mappings -->
      <div class="branding-subheader" style="margin-top:1rem;">Keyword Mappings</div>
      <div style="margin-bottom:0.5rem;">
        <div v-for="[name, icon] of sortedKeywordIcons" :key="name"
             style="display:flex; align-items:center; gap:0.5rem; padding:0.25rem 0;">
          <span style="width:24px; height:24px; display:inline-flex;" v-html="resolveIconHtml(icon)"></span>
          <span style="flex:1; color:var(--text-color,#ccc);">{{ name }}</span>
          <button type="button" class="btn-branding btn-branding--reset" style="padding:0.15rem 0.5rem; font-size:0.8rem;"
                  @click="admin.removeMapping('keyword', name)">&times;</button>
        </div>
        <div v-show="!Object.keys(admin.iconMappings.keyword_icons || {}).length" style="color:var(--text-muted,#999); font-size:0.85rem; padding:0.25rem 0;">
          No keyword mappings yet.
        </div>
      </div>
      <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:1rem;">
        <div style="flex:1; position:relative;">
          <SearchDropdown v-if="!admin.newKwName"
                          v-model="admin.mappingKwSearch"
                          :results="admin.mappingKwResults"
                          placeholder="Search keywords..."
                          @search="admin.searchMappingKeywords()"
                          @select="admin.selectMappingKeyword" />
          <div v-else style="display:flex; align-items:center; gap:0.35rem; padding:0.3rem 0.5rem; background:var(--card-bg,#1a1a1a); border-radius:6px; border:1px solid var(--card-border,rgba(255,255,255,0.1));">
            <span style="flex:1; color:var(--text-color,#e8e0d0); font-size:0.85rem;">{{ admin.newKwName }}</span>
            <button type="button" style="background:none; border:none; color:var(--text-muted,#999); cursor:pointer; padding:0 0.25rem; font-size:1rem;"
                    @click="admin.newKwName = ''">&times;</button>
          </div>
        </div>
        <button type="button" class="btn-branding" style="display:flex; align-items:center; gap:0.25rem; padding:0.3rem 0.5rem;"
                @click="pickIcon(admin.newKwIcon, (k: string) => { admin.newKwIcon = k })">
          <span v-show="admin.newKwIcon" style="width:18px; height:18px; display:inline-flex;" v-html="resolveIconHtml(admin.newKwIcon)"></span>
          <span>{{ admin.newKwIcon ? 'Change' : 'Icon' }}</span>
        </button>
        <button type="button" class="btn-branding" @click="admin.addMapping('keyword')"
                :disabled="!(admin.newKwName.trim() || admin.mappingKwSearch.trim()) || !admin.newKwIcon">Add</button>
      </div>

      <!-- Food Mappings -->
      <div class="branding-subheader">Food Mappings</div>
      <div style="margin-bottom:0.5rem;">
        <div v-for="[name, icon] of sortedFoodIcons" :key="name"
             style="display:flex; align-items:center; gap:0.5rem; padding:0.25rem 0;">
          <span style="width:24px; height:24px; display:inline-flex;" v-html="resolveIconHtml(icon)"></span>
          <span style="flex:1; color:var(--text-color,#ccc);">{{ name }}</span>
          <button type="button" class="btn-branding btn-branding--reset" style="padding:0.15rem 0.5rem; font-size:0.8rem;"
                  @click="admin.removeMapping('food', name)">&times;</button>
        </div>
        <div v-show="!Object.keys(admin.iconMappings.food_icons || {}).length" style="color:var(--text-muted,#999); font-size:0.85rem; padding:0.25rem 0;">
          No food mappings yet.
        </div>
      </div>
      <div style="display:flex; align-items:center; gap:0.5rem;">
        <div style="flex:1; position:relative;">
          <SearchDropdown v-if="!admin.newFoodName"
                          v-model="admin.mappingFoodSearch"
                          :results="admin.mappingFoodResults"
                          placeholder="Search foods..."
                          empty-message="No matching foods found."
                          @search="admin.searchMappingFoods()"
                          @select="admin.selectMappingFood" />
          <div v-else style="display:flex; align-items:center; gap:0.35rem; padding:0.3rem 0.5rem; background:var(--card-bg,#1a1a1a); border-radius:6px; border:1px solid var(--card-border,rgba(255,255,255,0.1));">
            <span style="flex:1; color:var(--text-color,#e8e0d0); font-size:0.85rem;">{{ admin.newFoodName }}</span>
            <button type="button" style="background:none; border:none; color:var(--text-muted,#999); cursor:pointer; padding:0 0.25rem; font-size:1rem;"
                    @click="admin.newFoodName = ''">&times;</button>
          </div>
        </div>
        <button type="button" class="btn-branding" style="display:flex; align-items:center; gap:0.25rem; padding:0.3rem 0.5rem;"
                @click="pickIcon(admin.newFoodIcon, (k: string) => { admin.newFoodIcon = k })">
          <span v-show="admin.newFoodIcon" style="width:18px; height:18px; display:inline-flex;" v-html="resolveIconHtml(admin.newFoodIcon)"></span>
          <span>{{ admin.newFoodIcon ? 'Change' : 'Icon' }}</span>
        </button>
        <button type="button" class="btn-branding" @click="admin.addMapping('food')"
                :disabled="!(admin.newFoodName.trim() || admin.mappingFoodSearch.trim()) || !admin.newFoodIcon">Add</button>
      </div>
    </section>

    <!-- Custom Icons -->
    <section class="admin-section">
      <h2 class="section-title">Custom Icons</h2>
      <small class="section-help">Upload SVG icons for use in profile and category cards. You can also upload directly from the icon picker when editing a profile.</small>
      <div style="margin:0.75rem 0;">
        <input type="file" accept=".svg" @change="uploadCustomIcon($event)" id="branding-icon-upload" style="display:none;">
        <label for="branding-icon-upload" class="btn-branding" style="cursor:pointer;">+ Upload SVG</label>
      </div>
      <div class="icon-picker-grid" v-show="customIcons.length > 0" style="gap:0.75rem;">
        <div v-for="icon in customIcons" :key="icon.key"
             style="position:relative; display:inline-flex; flex-direction:column; align-items:center; gap:0.25rem;">
          <div style="width:48px; height:48px; display:flex; align-items:center; justify-content:center; border:1px solid var(--border-color, #333); border-radius:8px; padding:4px;">
            <span v-html="resolveIconHtml(icon.key)" style="width:32px; height:32px; display:inline-flex;"></span>
          </div>
          <span v-show="!icon.editing" role="button" tabindex="0"
                @click="icon.editing = true; icon.newName = icon.key.replace('custom:', '')"
                @keydown.enter="icon.editing = true; icon.newName = icon.key.replace('custom:', '')"
                style="font-size:0.75rem; color:var(--text-muted, #999); max-width:80px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; cursor:pointer;"
                aria-label="Rename icon">
            {{ icon.key.replace('custom:', '') }}
          </span>
          <input v-show="icon.editing" v-model="icon.newName" type="text"
                 aria-label="New icon name"
                 @keydown.enter="renameIcon(icon)"
                 @keydown.escape="icon.editing = false"
                 style="font-size:0.75rem; width:80px; background:var(--input-bg, #1a1a1a); color:var(--text-color, #ccc); border:1px solid var(--accent-color); border-radius:4px; padding:1px 4px; text-align:center;">
          <button type="button" @click="deleteIcon(icon.key)"
                  style="position:absolute; top:-4px; right:-4px; width:18px; height:18px; border-radius:50%; border:none; background:var(--danger-color, #dc3545); color:#fff; font-size:11px; line-height:1; cursor:pointer; padding:0; display:flex; align-items:center; justify-content:center;"
                  title="Delete">&times;</button>
        </div>
      </div>
      <div v-show="customIcons.length === 0" style="color:var(--text-muted, #999); font-size:0.85rem; padding:0.5rem 0;">
        No custom icons yet. Upload an SVG to get started.
      </div>
    </section>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, inject } from 'vue'
import BrandingImageField from '@/components/admin/BrandingImageField.vue'
import ToggleSetting from '@/components/shared/ToggleSetting.vue'
import SearchDropdown from '@/components/shared/SearchDropdown.vue'
import { useAdminStore } from '@/stores/admin'
import { getIconByKey } from '@/utils/icons'
import type { IconPickerExposed } from '@/types/api'

const admin = useAdminStore()

const iconPickerRef = inject<{ value: IconPickerExposed | null }>('iconPickerRef')

// WiFi QR local state
const wifiSsid = ref(String(admin.settings.qr_wifi_ssid || ''))
const wifiPassword = ref(String(admin.settings.qr_wifi_password || ''))
const wifiEncryption = ref(String(admin.settings.qr_wifi_encryption || 'WPA'))

function saveWifi() {
  admin.saveWifiQr(wifiSsid.value, wifiPassword.value, wifiEncryption.value)
}

// Sorted icon mappings
const sortedKeywordIcons = computed(() =>
  Object.entries(admin.iconMappings.keyword_icons || {}).sort((a, b) => a[0].localeCompare(b[0]))
)
const sortedFoodIcons = computed(() =>
  Object.entries(admin.iconMappings.food_icons || {}).sort((a, b) => a[0].localeCompare(b[0]))
)

// Icon resolution
function resolveIconHtml(key: string): string {
  if (!key) return ''
  return getIconByKey(key)
}

// Icon picker bridge
function pickIcon(current: string, cb: (k: string) => void) {
  iconPickerRef?.value?.show(current, cb)
}

// Custom icons management (via IconPicker component)
interface CustomIconEntry {
  key: string
  editing: boolean
  newName: string
}

const customIcons = ref<CustomIconEntry[]>([])

function refreshCustomIcons() {
  const icons = iconPickerRef?.value?.getCustomIcons?.() || []
  customIcons.value = icons.map((i: { key: string }) => reactive({
    key: i.key,
    editing: false,
    newName: '',
  }))
}

// Refresh on mount
refreshCustomIcons()

async function uploadCustomIcon(event: Event) {
  if (iconPickerRef?.value) {
    await iconPickerRef.value.uploadCustomIcon(event)
    refreshCustomIcons()
  }
}

async function renameIcon(icon: CustomIconEntry) {
  if (iconPickerRef?.value) {
    await iconPickerRef.value.renameCustomIcon(icon.key, icon.newName)
    icon.editing = false
    refreshCustomIcons()
  }
}

async function deleteIcon(key: string) {
  if (iconPickerRef?.value) {
    await iconPickerRef.value.deleteCustomIcon(key)
    refreshCustomIcons()
  }
}
</script>
