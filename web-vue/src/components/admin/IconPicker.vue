<template>
  <Teleport to="body">
    <!-- Backdrop -->
    <Transition name="icon-picker-backdrop">
      <div v-show="isOpen" class="icon-picker-overlay" @click="close"></div>
    </Transition>

    <!-- Drawer -->
    <Transition name="icon-picker-slide">
      <div v-show="isOpen" class="icon-picker-drawer" role="dialog" aria-modal="true" aria-label="Icon Picker">
        <!-- Header with search -->
        <div class="icon-picker-header">
          <input type="text" v-model="searchQuery" class="icon-picker-search"
                 placeholder="Search icons..." ref="searchInput">
          <button class="icon-picker-close" @click="close" aria-label="Close">&times;</button>
        </div>

        <!-- Clear selection -->
        <button class="icon-picker-clear" @click="pick('')">Clear icon selection</button>

        <!-- Tabs -->
        <div class="icon-picker-tabs" v-show="!isSearching">
          <button v-for="tab in tabs" :key="tab"
                  class="icon-picker-tab" :class="{ active: activeTab === tab }"
                  @click="activeTab = tab">
            {{ tab }}
          </button>
        </div>

        <!-- Body -->
        <div class="icon-picker-body">
          <!-- Search results -->
          <template v-if="isSearching">
            <div class="icon-picker-grid">
              <button v-for="key in filteredIcons" :key="key"
                      class="icon-picker-item" :class="{ active: key === currentIcon }"
                      @click="pick(key)" :title="key">
                <span v-html="resolveIconHtml(key)" style="width:28px; height:28px; display:inline-flex;"></span>
                <span class="icon-picker-item-label">{{ formatLabel(key) }}</span>
              </button>
            </div>
          </template>

          <!-- Tab content -->
          <template v-else-if="activeTab === 'Custom'">
            <div class="icon-picker-custom-upload">
              <input type="file" accept=".svg" @change="uploadIcon($event)" id="icon-picker-upload" style="display:none;">
              <label for="icon-picker-upload" class="icon-picker-upload-btn">+ Upload SVG</label>
            </div>
            <div class="icon-picker-grid">
              <button v-for="icon in customIcons" :key="icon.key"
                      class="icon-picker-item" :class="{ active: icon.key === currentIcon }"
                      @click="pick(icon.key)" :title="icon.key">
                <span v-html="resolveCustomIconHtml(icon.key)" style="width:28px; height:28px; display:inline-flex;"></span>
                <span class="icon-picker-item-label">{{ icon.key.replace('custom:', '') }}</span>
              </button>
            </div>
            <div v-show="customIcons.length === 0" style="color:var(--text-muted,#999); font-size:0.85rem; padding:1rem 0; text-align:center;">
              No custom icons yet.
            </div>
          </template>

          <!-- Category groups -->
          <template v-else>
            <div v-for="group in tabGroupEntries" :key="group.name" class="icon-picker-group">
              <div v-show="!group.solo" class="icon-picker-group-label">{{ group.name }}</div>
              <div class="icon-picker-grid">
                <button v-for="key in group.icons" :key="key"
                        class="icon-picker-item" :class="{ active: key === currentIcon }"
                        @click="pick(key)" :title="key">
                  <span v-html="resolveIconHtml(key)" style="width:28px; height:28px; display:inline-flex;"></span>
                  <span class="icon-picker-item-label">{{ formatLabel(key) }}</span>
                </button>
              </div>
            </div>
          </template>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { getIconByKey, getAllIconKeys, getIconCategories } from '@/utils/icons'

// State
const isOpen = ref(false)
const activeTab = ref('')
const currentIcon = ref('')
const searchQuery = ref('')
const searchInput = ref<HTMLInputElement | null>(null)

interface CustomIcon {
  key: string
  name: string
}

const customIcons = ref<CustomIcon[]>([])

// Callback for selection
let onSelectCallback: ((key: string) => void) | null = null

// Tabs: icon categories + Custom
const tabs = computed(() => {
  const categories = getIconCategories()
  const names = categories.map(c => c.name)
  names.push('Custom')
  return names
})

// Current tab's group entries
const tabGroupEntries = computed(() => {
  if (activeTab.value === 'Custom') return []
  const categories = getIconCategories()
  const category = categories.find(c => c.name === activeTab.value)
  if (!category) return []
  // Return as single group matching the tab
  return [{ name: category.name, icons: category.keys, solo: true }]
})

// Search filtering
const isSearching = computed(() => searchQuery.value.length > 0)

const filteredIcons = computed(() => {
  if (!searchQuery.value) return []
  const q = searchQuery.value.toLowerCase()
  return getAllIconKeys().filter(k => k.toLowerCase().includes(q))
})

// Public method: open the picker
function show(currentValue: string, onSelect: (key: string) => void) {
  currentIcon.value = currentValue || ''
  onSelectCallback = onSelect
  searchQuery.value = ''
  activeTab.value = tabs.value[0] || ''
  isOpen.value = true
  loadCustomIcons()
  nextTick(() => {
    searchInput.value?.focus()
  })
}

function pick(key: string) {
  if (onSelectCallback) onSelectCallback(key)
  isOpen.value = false
}

function close() {
  isOpen.value = false
}

// Icon rendering
function resolveIconHtml(key: string): string {
  if (!key) return ''
  if (key.startsWith('custom:')) {
    return resolveCustomIconHtml(key)
  }
  const svg = getIconByKey(key)
  return svg || ''
}

function resolveCustomIconHtml(key: string): string {
  return getIconByKey(key)
}

function formatLabel(key: string): string {
  if (key.startsWith('custom:')) return key.replace('custom:', '')
  // Strip category prefix if present (e.g. "protein:chicken" -> "chicken")
  const parts = key.split(':')
  return parts[parts.length - 1].replace(/[-_]/g, ' ')
}

// Custom icons CRUD
async function loadCustomIcons() {
  try {
    const resp = await fetch('/api/custom-icons')
    if (!resp.ok) return
    const list = await resp.json()
    customIcons.value = list
  } catch {
    // Custom icons not available
  }
}

async function uploadIcon(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  try {
    const resp = await fetch('/api/custom-icons', { method: 'POST', body: formData })
    if (resp.ok) {
      await loadCustomIcons()
    }
  } catch (e) {
    console.error('Upload failed:', e)
  }
  input.value = ''
}

// Public API for custom icon management (used by BrandingTab)
async function renameCustomIcon(key: string, newName: string): Promise<{ key: string } | null> {
  const oldName = key.replace('custom:', '')
  try {
    const resp = await fetch(`/api/custom-icons/${oldName}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName }),
    })
    if (resp.ok) {
      const result = await resp.json()
      await loadCustomIcons()
      return result
    } else {
      const err = await resp.json()
      console.error('Rename failed:', err.detail)
    }
  } catch (e) {
    console.error('Rename failed:', e)
  }
  return null
}

async function deleteCustomIcon(key: string) {
  const name = key.replace('custom:', '')
  try {
    const resp = await fetch(`/api/custom-icons/${name}`, { method: 'DELETE' })
    if (resp.ok) {
      customIcons.value = customIcons.value.filter(c => c.key !== key)
    }
  } catch (e) {
    console.error('Delete failed:', e)
  }
}

async function uploadCustomIcon(event: Event) {
  await uploadIcon(event)
}

function getCustomIcons() {
  return customIcons.value
}

// Expose public methods
defineExpose({
  show,
  close,
  renameCustomIcon,
  deleteCustomIcon,
  uploadCustomIcon,
  loadCustomIcons,
  getCustomIcons,
  customIcons,
})
</script>

<style scoped>
.icon-picker-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1001;
}

.icon-picker-drawer {
  position: fixed;
  top: 0;
  right: 0;
  width: 420px;
  max-width: 95vw;
  height: 100vh;
  background: var(--modal-bg, #1a1a1a);
  border-left: 1px solid var(--card-border, rgba(255, 255, 255, 0.1));
  z-index: 1002;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.icon-picker-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--card-border, rgba(255, 255, 255, 0.1));
}

.icon-picker-search {
  flex: 1;
  padding: 0.4rem 0.6rem;
  background: var(--bg-color, #0d0d0d);
  color: var(--text-color, #e8e0d0);
  border: 1px solid var(--card-border, rgba(255, 255, 255, 0.15));
  border-radius: 6px;
  font-size: 0.85rem;
  font-family: var(--body-font, sans-serif);
  outline: none;
}

.icon-picker-search:focus {
  border-color: var(--accent-color, #d4a847);
}

.icon-picker-close {
  background: none;
  border: none;
  color: var(--text-muted, rgba(255, 255, 255, 0.5));
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0 0.25rem;
  line-height: 1;
}

.icon-picker-close:hover {
  color: var(--text-color, #e8e0d0);
}

.icon-picker-clear {
  display: block;
  width: calc(100% - 2rem);
  margin: 0.5rem 1rem 0.3rem;
  padding: 0.3rem 0.5rem;
  background: none;
  border: 1px dashed var(--card-border, rgba(255, 255, 255, 0.15));
  border-radius: 4px;
  color: var(--text-muted, rgba(255, 255, 255, 0.5));
  font-size: 0.75rem;
  cursor: pointer;
  text-align: center;
}

.icon-picker-clear:hover {
  border-color: var(--accent-color, #d4a847);
  color: var(--text-color, #e8e0d0);
}

.icon-picker-tabs {
  display: flex;
  overflow-x: auto;
  gap: 0;
  padding: 0 1rem;
  border-bottom: 1px solid var(--card-border, rgba(255, 255, 255, 0.1));
  position: sticky;
  top: 0;
  background: var(--modal-bg, #1a1a1a);
  z-index: 1;
  -webkit-overflow-scrolling: touch;
}

.icon-picker-tab {
  flex: 0 0 auto;
  padding: 0.45rem 0.7rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-muted, rgba(255, 255, 255, 0.5));
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  cursor: pointer;
  white-space: nowrap;
  transition: color 0.15s, border-color 0.15s;
  font-family: var(--body-font, sans-serif);
}

.icon-picker-tab:hover {
  color: var(--text-color, #e8e0d0);
}

.icon-picker-tab.active {
  color: var(--accent-color, #d4a847);
  border-bottom-color: var(--accent-color, #d4a847);
}

.icon-picker-body {
  overflow-y: auto;
  flex: 1;
  padding: 1rem;
}

.icon-picker-group {
  margin-bottom: 0.5rem;
}

.icon-picker-group-label {
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted, rgba(255, 255, 255, 0.4));
  padding: 0.3rem 0.3rem 0.15rem;
  border-bottom: 1px solid var(--card-border, rgba(255, 255, 255, 0.08));
  margin-bottom: 0.25rem;
}

.icon-picker-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 0.15rem 0;
}

.icon-picker-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 64px;
  padding: 4px 2px 2px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid transparent;
  border-radius: 4px;
  color: var(--accent-color, #d4a847);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  gap: 2px;
}

.icon-picker-item:hover {
  border-color: var(--accent-color, #d4a847);
  background: rgba(212, 168, 71, 0.1);
}

.icon-picker-item.active {
  border-color: var(--accent-color, #d4a847);
  background: rgba(212, 168, 71, 0.2);
}

.icon-picker-item-label {
  font-size: 0.6rem;
  line-height: 1;
  color: var(--text-muted, rgba(255, 255, 255, 0.5));
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--body-font, sans-serif);
}

.icon-picker-custom-upload {
  margin-bottom: 0.75rem;
}

.icon-picker-upload-btn {
  display: inline-block;
  padding: 0.3rem 0.7rem;
  background: var(--surface-hover, rgba(255, 255, 255, 0.08));
  border: 1px solid var(--card-border, rgba(255, 255, 255, 0.15));
  border-radius: 6px;
  color: var(--text-color, #e8e0d0);
  font-size: 0.8rem;
  cursor: pointer;
  transition: border-color 0.15s;
}

.icon-picker-upload-btn:hover {
  border-color: var(--accent-color, #d4a847);
}

/* Transitions */
.icon-picker-backdrop-enter-active { transition: opacity 0.2s ease-out; }
.icon-picker-backdrop-leave-active { transition: opacity 0.2s ease-in; }
.icon-picker-backdrop-enter-from,
.icon-picker-backdrop-leave-to { opacity: 0; }

.icon-picker-slide-enter-active { transition: transform 0.25s ease-out; }
.icon-picker-slide-leave-active { transition: transform 0.2s ease-in; }
.icon-picker-slide-enter-from { transform: translateX(100%); }
.icon-picker-slide-leave-to { transform: translateX(100%); }
</style>
