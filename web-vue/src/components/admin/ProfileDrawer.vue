<template>
  <Teleport to="body">
    <!-- Profile Editor Backdrop -->
    <Transition name="drawer-backdrop">
      <div class="drawer-backdrop"
           v-show="admin.editingProfile"
           @click="admin.cancelEditProfile()">
      </div>
    </Transition>

    <!-- Profile Editor Drawer -->
    <Transition name="drawer-slide">
      <div class="profile-drawer"
           :class="{ open: admin.editingProfile }"
           v-show="admin.editingProfile"
           role="dialog" aria-modal="true" aria-labelledby="profile-drawer-title">
        <div class="drawer-header">
          <h3 id="profile-drawer-title">{{ admin.isNewProfile ? 'New Profile' : 'Edit Profile' }}</h3>
          <button class="drawer-close" @click="admin.cancelEditProfile()" aria-label="Close">&times;</button>
        </div>

        <div class="drawer-body">
          <div class="drawer-section">
            <label class="drawer-label">Name</label>
            <input type="text" v-model="admin.profileEditor.name"
                   class="drawer-input" placeholder="profile-name">
            <small v-show="!admin.isNewProfile && admin.profileEditor.name !== admin.profileEditor.originalName"
                   class="drawer-rename-hint">
              Renaming from "{{ admin.profileEditor.originalName }}"
            </small>
          </div>

          <!-- Advanced: Default Profile / Show on Menu -->
          <div class="drawer-section" v-show="admin.tierVisible('standard')">
            <ToggleSetting label="Default Profile" help="This profile will be pre-selected when generating and shown first on the menu page" v-model="admin.profileEditor.default" />
            <ToggleSetting label="Show on Menu" help="Display this profile on the customer menu page" v-model="admin.profileEditor.show_on_menu" />
          </div>

          <div class="drawer-section">
            <label class="drawer-label">Description</label>
            <input type="text" v-model="admin.profileEditor.description"
                   class="drawer-input" placeholder="Optional description">
          </div>

          <!-- Advanced: Item Noun -->
          <div class="drawer-section" v-show="admin.tierVisible('standard')">
            <label class="drawer-label">Item Noun</label>
            <input type="text" v-model="admin.profileEditor.item_noun"
                   class="drawer-input" placeholder="recipe">
            <small style="color:var(--text-muted);font-size:0.75rem;">Singular noun for items (e.g. "cocktail", "dessert"). Empty uses global default.</small>
          </div>

          <div class="drawer-section">
            <label class="drawer-label">Icon</label>
            <button type="button" class="icon-picker-trigger" @click="pickProfileIcon">
              <span v-show="admin.profileEditor.icon" v-html="resolveIconHtml(admin.profileEditor.icon || '')"
                    style="width:24px; height:24px; display:inline-flex; color:var(--accent-color);"></span>
              <span>{{ admin.profileEditor.icon || 'Choose icon\u2026' }}</span>
              <span style="margin-left:auto; font-size:0.7em;">&#9662;</span>
            </button>
          </div>

          <!-- Advanced: Category -->
          <div class="drawer-section" v-show="admin.tierVisible('standard')">
            <label class="drawer-label">Category</label>
            <select v-model="admin.profileEditor.category" class="drawer-input">
              <option value="">None</option>
              <option v-for="cat in admin.categories" :key="cat.id" :value="cat.id">
                {{ cat.display_name || cat.id }}
              </option>
            </select>
            <small class="drawer-help">Controls where this profile appears in the menu page navigation.</small>
          </div>

          <div class="drawer-section drawer-row">
            <div>
              <label class="drawer-label">Recipes</label>
              <input type="number" class="drawer-input drawer-input--small"
                     v-model.number="admin.profileEditor.choices" min="1" max="20"
                     title="Target number of recipes to select">
            </div>
            <!-- Advanced: Min Recipes -->
            <div v-show="admin.tierVisible('standard')">
              <label class="drawer-label">Min</label>
              <input type="number" class="drawer-input drawer-input--small"
                     v-model.number="admin.profileEditor.min_choices" min="0" max="20"
                     placeholder="-"
                     title="Minimum acceptable if target can't be reached">
            </div>
          </div>
          <small class="drawer-help">
            <strong>Recipes:</strong> How many recipes to pick.
            <span v-show="admin.tierVisible('standard')"><strong>Min:</strong> Accept fewer if rules are too strict.</span>
          </small>

          <!-- Custom Filters (Tandoor saved searches) -->
          <div class="drawer-section" v-show="admin.tierVisible('advanced')">
            <label class="drawer-label">Saved Filters</label>
            <small class="drawer-help">Limit the recipe pool to results from Tandoor saved searches. Leave empty to use all recipes.</small>
            <div v-if="admin.customFilters.length > 0">
              <div class="constraint-items-list" style="margin-bottom:0.5rem;">
                <span v-for="fid in admin.profileEditor.filters" :key="fid" class="constraint-item-tag">
                  <span>{{ admin.customFilters.find(f => f.id === fid)?.name || ('#' + fid) }}</span>
                  <button @click="admin.profileEditor.filters = admin.profileEditor.filters.filter((id: number) => id !== fid)" aria-label="Remove">&times;</button>
                </span>
              </div>
              <select class="drawer-select" @change="onFilterAdd($event)">
                <option value="">Add a saved filter...</option>
                <option v-for="cf in admin.customFilters.filter(f => !admin.profileEditor.filters.includes(f.id))" :key="cf.id" :value="cf.id">
                  {{ cf.name }}
                </option>
              </select>
            </div>
            <small v-else class="drawer-help" style="font-style:italic;">No saved filters in Tandoor</small>
          </div>

          <ConstraintEditor />
        </div>

        <div class="drawer-footer">
          <button class="btn-generate btn-secondary" v-show="admin.tierVisible('standard')" @click="admin.previewProfile()" :disabled="admin.profilePreviewing" style="flex:0 0 auto; padding:0 1rem;">
            {{ admin.profilePreviewing ? '...' : 'Test Profile' }}
          </button>
          <span class="preview-result" v-show="admin.tierVisible('standard') && admin.previewResult !== null">
            {{ typeof admin.previewResult === 'number' ? admin.previewResult + ' recipes match' : admin.previewResult }}
          </span>
          <button class="btn-generate" @click="admin.saveProfile()" :disabled="admin.profileSaving" style="margin-left:auto;">
            {{ admin.profileSaving ? 'Saving...' : 'Save Profile' }}
          </button>
          <button class="btn-generate btn-secondary" @click="admin.cancelEditProfile()">Cancel</button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { inject } from 'vue'
import ToggleSetting from '@/components/shared/ToggleSetting.vue'
import ConstraintEditor from '@/components/admin/ConstraintEditor.vue'
import { useAdminStore } from '@/stores/admin'
import { getIconByKey } from '@/utils/icons'
import type { IconPickerExposed } from '@/types/api'

const admin = useAdminStore()

const iconPickerRef = inject<{ value: IconPickerExposed | null }>('iconPickerRef')

function resolveIconHtml(key: string): string {
  if (!key) return ''
  return getIconByKey(key)
}

function pickProfileIcon() {
  iconPickerRef?.value?.show(admin.profileEditor.icon || '', (k: string) => { admin.profileEditor.icon = k })
}

function onFilterAdd(event: Event) {
  const target = event.target as HTMLSelectElement
  if (target.value) {
    const id = Number(target.value)
    if (!admin.profileEditor.filters.includes(id)) {
      admin.profileEditor.filters.push(id)
    }
    target.value = ''
  }
}
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
