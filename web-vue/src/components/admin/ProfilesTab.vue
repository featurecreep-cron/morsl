<template>
  <div id="panel-profiles" role="tabpanel" aria-labelledby="tab-profiles">

    <!-- Categories -->
    <section class="admin-section">
      <h2 class="section-title">Categories</h2>
      <small class="section-help">Organize profiles into tabs on the menu page. Without categories, all profiles appear as buttons. With categories, profiles are grouped under labeled tabs.</small>
      <button class="btn-generate btn-secondary" @click="admin.startNewCategory()"
              style="margin-bottom:0.75rem; height:30px; font-size:0.85rem;">
        + Add Category
      </button>

      <!-- Category Form -->
      <div v-show="admin.showCategoryForm" class="constraint-group" style="margin-bottom:1rem;">
        <div class="choices-row">
          <label>Name:</label>
          <input type="text" class="search-input" v-model="admin.categoryForm.display_name"
                 placeholder="e.g. Weeknight Dinners" style="width:200px;">
        </div>
        <div class="choices-row">
          <label>Subtitle:</label>
          <input type="text" class="search-input" v-model="admin.categoryForm.subtitle"
                 placeholder="Shown below category name">
        </div>
        <div class="choices-row">
          <label>Icon:</label>
          <button type="button" class="icon-picker-trigger" @click="pickCategoryIcon">
            <span v-show="admin.categoryForm.icon" v-html="resolveIconHtml(admin.categoryForm.icon)"
                  style="width:24px; height:24px; display:inline-flex; color:var(--accent-color);"></span>
            <span>{{ admin.categoryForm.icon || 'Choose icon\u2026' }}</span>
            <span style="margin-left:auto; font-size:0.7em;">&#9662;</span>
          </button>
        </div>
        <div style="display:flex; gap:0.5rem; margin-top:0.5rem;">
          <button class="btn-generate" @click="admin.saveCategory()" style="height:30px; font-size:0.85rem;">Save</button>
          <button class="btn-generate btn-secondary" @click="admin.showCategoryForm = false; admin.editingCategoryId = null;" style="height:30px; font-size:0.85rem;">Cancel</button>
        </div>
      </div>

      <div v-show="admin.categories.length === 0 && !admin.showCategoryForm" class="tag-empty">No categories configured</div>
      <div class="category-drag-list" ref="categoryListRef">
        <div v-for="cat in admin.categories" :key="cat.id"
             class="constraint-chip category-drag-item"
             :data-id="cat.id"
             style="justify-content:space-between; cursor:default;">
          <span style="display:flex; align-items:center; gap:0.5rem;">
            <span class="drag-handle" style="cursor:grab; opacity:0.5; font-size:1.1rem;" title="Drag to reorder">&#9776;</span>
            <span>
              <strong>{{ cat.display_name || cat.id }}</strong>
              <small v-show="cat.subtitle" style="opacity:0.6;">{{ cat.subtitle }}</small>
            </span>
          </span>
          <span>
            <button class="btn-chip-remove" @click.stop="admin.editCategory(cat)" title="Edit" style="color:var(--accent-color);">&#9998;</button>
            <button class="btn-chip-remove" @click.stop="admin.deleteCategory(cat.id)" title="Delete">&times;</button>
          </span>
        </div>
      </div>
    </section>

    <!-- Profiles -->
    <section class="admin-section">
      <h2 class="section-title">Profiles</h2>
      <small class="section-help">Each profile defines which recipes to include and how many to pick.</small>
      <div class="profile-grid">
        <!-- New Profile card -->
        <div class="profile-card profile-card--new" @click="admin.startNewProfile()">
          <div class="profile-card-icon">+</div>
          <h4>New Profile</h4>
          <p>Create a new profile</p>
        </div>
        <!-- Existing profiles -->
        <div v-for="p in admin.profiles" :key="p.name"
             class="profile-card" :class="{ 'profile-card--active': admin.editingProfile && admin.profileEditor.originalName === p.name }">
          <div class="profile-card-icon">
            <span v-show="p.icon" v-html="resolveIconHtml(p.icon || '')"
                  style="width:24px; height:24px; display:inline-flex; color:var(--accent-color);"></span>
            <span v-show="!p.icon" v-html="stockIconSvg"
                  style="width:24px; height:24px; display:inline-flex; color:var(--accent-color);"></span>
          </div>
          <h4>{{ p.name }}</h4>
          <p>{{ p.description || 'No description' }}</p>
          <div class="profile-card-stats">
            <span>{{ itemNounText(p.choices, p.item_noun || admin.settings.item_noun) }}</span>
            <span>&middot;</span>
            <span>{{ p.constraint_count }} rules</span>
          </div>
          <div class="profile-card-actions">
            <button class="profile-card-btn" @click.stop="admin.startEditProfile(p.name)">Edit</button>
            <button class="profile-card-btn profile-card-btn--danger" @click.stop="admin.deleteProfile(p.name)">Delete</button>
          </div>
        </div>
      </div>
    </section>

  </div>
</template>

<script setup lang="ts">
import { useAdminStore } from '@/stores/admin'
import { itemNounText } from '@/utils/formatting'
import { STOCK_ICON_SVG } from '@/utils/icons'

const admin = useAdminStore()
const stockIconSvg = STOCK_ICON_SVG

function resolveIconHtml(key: string): string {
  if (!key) return ''
  // Custom icons start with "custom:" — render as img from API
  if (key.startsWith('custom:')) {
    return `<img src="/api/icons/${encodeURIComponent(key)}" style="width:100%;height:100%;object-fit:contain" alt="${key}">`
  }
  // Built-in icons — use stock SVG as fallback
  return STOCK_ICON_SVG
}

function pickCategoryIcon() {
  // Icon picker integration — calls the global icon picker if available
  const w = window as unknown as { iconPicker?: { show: (current: string, cb: (k: string) => void) => void } }
  if (w.iconPicker) {
    w.iconPicker.show(admin.categoryForm.icon, (k: string) => { admin.categoryForm.icon = k })
  }
}
</script>
