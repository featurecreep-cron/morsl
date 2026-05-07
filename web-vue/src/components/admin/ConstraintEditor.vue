<template>
  <!-- Constraints List -->
  <div class="drawer-section">
    <div class="drawer-label-row">
      <label class="drawer-label">
        Rules
        <span class="constraint-count-badge">{{ admin.profileEditor.constraints?.length || 0 }}</span>
      </label>
      <button class="btn-toggle-all-groups"
              v-show="(admin.profileEditor.constraints?.length || 0) > 0"
              @click="admin.toggleAllGroups()">
        {{ admin.areAllGroupsCollapsed() ? 'Expand All' : 'Collapse All' }}
      </button>
    </div>

    <!-- Constraint List (grouped by type) -->
    <div class="constraint-list">
      <template v-for="(c, idx) in (admin.profileEditor.constraints || [])" :key="idx">
        <div v-show="(idx === 0 || admin.profileEditor.constraints[idx - 1]?.type !== c.type) || !admin.collapsedGroups[c.type]">
          <!-- Group header (shown before first constraint of each type) -->
          <div class="constraint-group-header"
               v-show="idx === 0 || (admin.profileEditor.constraints[idx - 1]?.type !== c.type)"
               @click="admin.toggleGroupCollapse(c.type)"
               :class="{ collapsed: admin.collapsedGroups[c.type] }">
            <span class="constraint-type-icon" v-html="constraintTypes[c.type]?.icon || '?'"></span>
            <span class="constraint-group-label">{{ constraintTypes[c.type]?.label || c.type }}</span>
            <span class="constraint-count-badge">{{ admin.countConstraintsByType(c.type) }}</span>
            <span class="constraint-expand-icon" style="margin-left:auto;">{{ admin.collapsedGroups[c.type] ? '&#9660;' : '&#9650;' }}</span>
          </div>
          <div class="constraint-item"
               v-show="!admin.collapsedGroups[c.type]"
               :class="{ expanded: admin.expandedConstraint === idx }">
            <!-- Collapsed view (summary) -->
            <div class="constraint-summary" @click="admin.toggleConstraintExpand(idx)">
              <span class="constraint-type-icon" v-html="constraintTypes[c.type]?.icon || '?'"></span>
              <span class="constraint-type-label">{{ constraintTypes[c.type]?.label || c.type }}</span>
              <span class="constraint-summary-text">{{ admin.describeConstraint(c) }}</span>
              <span class="constraint-soft-badge" v-show="admin.isConstraintSoft(c)">
                soft{{ c.weight && c.weight !== 10 ? ' (' + c.weight + ')' : '' }}
              </span>
              <span class="constraint-expand-icon">{{ admin.expandedConstraint === idx ? '\u25B2' : '\u25BC' }}</span>
            </div>

            <!-- Expanded view (edit form) -->
            <div class="constraint-details" v-show="admin.expandedConstraint === idx">
              <!-- Label -->
              <div class="constraint-field">
                <label>Label (optional)</label>
                <input type="text" class="drawer-input" v-model="c.label"
                       placeholder="e.g., 'Must have gin'">
              </div>

              <!-- Make Now help text -->
              <div class="constraint-field" v-show="c.type === 'makenow'">
                <small class="field-help">{{ constraintTypes['makenow']?.help }}</small>
              </div>

              <!-- Items (for keyword/food/book) -->
              <div class="constraint-field" v-show="c.type === 'keyword' || c.type === 'food' || c.type === 'book'">
                <label>{{ (constraintTypes[c.type]?.label || c.type) + 's' }}</label>
                <small class="field-help">{{ constraintTypes[c.type]?.help }}</small>
                <div class="constraint-items-list">
                  <span v-for="item in (c.items || [])" :key="item.id" class="constraint-item-tag">
                    <span>{{ admin.getItemDisplayName(item, c.type) }}</span>
                    <button @click="admin.removeItemFromConstraint(c, item.id)" aria-label="Remove">&times;</button>
                  </span>
                  <span class="constraint-empty" v-show="!c.items || c.items.length === 0">
                    No items selected - search below to add
                  </span>
                </div>
                <!-- Search to add items -->
                <SearchDropdown v-show="c.type === 'keyword'"
                                v-model="admin.keywordSearch"
                                :results="admin.keywordResults"
                                placeholder="Type to search keywords..."
                                @search="admin.searchKeywords()"
                                @select="(item: SearchDropdownItem) => { admin.addItemToConstraint(c, item); admin.keywordSearch = ''; admin.keywordResults = [] }" />
                <SearchDropdown v-show="c.type === 'food'"
                                v-model="admin.foodSearch"
                                :results="admin.foodResults"
                                placeholder="Type to search ingredients..."
                                @search="admin.searchFoods()"
                                @select="(item: SearchDropdownItem) => { admin.addItemToConstraint(c, item); admin.foodSearch = ''; admin.foodResults = [] }" />
              </div>

              <!-- Rating fields -->
              <div class="constraint-field" v-show="c.type === 'rating'">
                <label>Rating Range</label>
                <small class="field-help">{{ constraintTypes['rating']?.help }}</small>
                <div class="constraint-inline-row">
                  <input type="number" class="drawer-input drawer-input--small"
                         v-model.number="c.min" min="0" max="5" step="0.5" placeholder="0">
                  <span>to</span>
                  <input type="number" class="drawer-input drawer-input--small"
                         v-model.number="c.max" min="0" max="5" step="0.5" placeholder="5">
                  <span>stars</span>
                </div>
                <small class="field-hint">Leave empty for any rating. Use decimals like 4.5 for precision.</small>
              </div>

              <!-- Last Made fields (cookedon) -->
              <div class="constraint-field" v-show="c.type === 'cookedon'">
                <label>Date Filter</label>
                <small class="field-help">Filter recipes by when they were last made</small>
                <div class="constraint-inline-row">
                  <select class="drawer-select" v-model="c.date_direction" @change="admin.syncDateFields(c)">
                    <option value="within">Made within last</option>
                    <option value="older">Made more than</option>
                  </select>
                  <input type="number" class="drawer-input drawer-input--small"
                         v-model.number="c.date_days" min="1" placeholder="30"
                         @change="admin.syncDateFields(c)">
                  <span>days <span v-show="c.date_direction === 'older'">ago</span></span>
                </div>
              </div>

              <!-- Date Added fields (createdon) -->
              <div class="constraint-field" v-show="c.type === 'createdon'">
                <label>Date Filter</label>
                <small class="field-help">Filter recipes by when they were added to Tandoor</small>
                <div class="constraint-inline-row">
                  <select class="drawer-select" v-model="c.date_direction" @change="admin.syncDateFields(c)">
                    <option value="within">Added within last</option>
                    <option value="older">Added more than</option>
                  </select>
                  <input type="number" class="drawer-input drawer-input--small"
                         v-model.number="c.date_days" min="1" placeholder="30"
                         @change="admin.syncDateFields(c)">
                  <span>days <span v-show="c.date_direction === 'older'">ago</span></span>
                </div>
              </div>

              <!-- Except items (for keyword/food) -->
              <div class="constraint-field" v-show="c.type === 'keyword' || c.type === 'food'">
                <label>Exceptions</label>
                <small class="field-help">Exclude specific items even if they match the constraint above</small>
                <div class="constraint-items-list">
                  <span v-for="(item, eidx) in (c.except || [])" :key="'except-' + item.id"
                        class="constraint-item-tag constraint-item-tag--except">
                    <span>{{ admin.getItemDisplayName(item, c.type) }}</span>
                    <button @click="c.except?.splice(eidx, 1)" aria-label="Remove">&times;</button>
                  </span>
                  <span class="constraint-empty" v-show="!c.except || c.except.length === 0">
                    None
                  </span>
                </div>
              </div>

              <!-- Operator and count -->
              <div class="constraint-field">
                <label>Requirement</label>
                <div class="constraint-inline-row">
                  <select v-model="c.operator" class="drawer-select">
                    <option value=">=">At least</option>
                    <option value="<=">At most</option>
                    <option value="==">Exactly</option>
                  </select>
                  <input type="number" class="drawer-input drawer-input--small"
                         v-model.number="c.count" min="0" max="20">
                  <span>recipes</span>
                </div>
              </div>

              <!-- Soft rule toggle -->
              <div class="constraint-field constraint-options">
                <label class="drawer-checkbox">
                  <input type="checkbox" :checked="admin.isConstraintSoft(c)" @change="admin.toggleConstraintSoft(c)">
                  <span>Flexible rule</span>
                </label>
                <small>Flexible rules can be relaxed if not all requirements can be satisfied</small>
                <div v-show="admin.isConstraintSoft(c)" style="margin-top:0.5rem;">
                  <label style="font-size:0.8rem; display:flex; align-items:center; gap:0.5rem;">
                    Priority: <span style="min-width:1.5em; text-align:center;">{{ c.weight || 10 }}</span>
                    <input type="range" min="1" max="20" :value="c.weight || 10"
                           @input="c.weight = parseInt(($event.target as HTMLInputElement).value)"
                           style="flex:1; accent-color:var(--accent-color);">
                  </label>
                  <small style="opacity:0.6;">Higher = harder to relax. Low priority rules yield first.</small>
                </div>
              </div>

              <!-- Include children (per-constraint) -->
              <div class="constraint-field constraint-options" v-show="c.type === 'keyword' || c.type === 'food'">
                <label class="drawer-checkbox">
                  <input type="checkbox" v-model="c.include_children">
                  <span>Include child items</span>
                </label>
                <small>Also match recipes with sub-keywords or sub-ingredients</small>
              </div>

              <!-- Action buttons -->
              <div class="constraint-actions">
                <button class="constraint-action-btn" @click="admin.moveConstraintUp(idx)" :disabled="idx === 0" title="Move up">&uarr;</button>
                <button class="constraint-action-btn" @click="admin.moveConstraintDown(idx)" :disabled="idx === admin.profileEditor.constraints.length - 1" title="Move down">&darr;</button>
                <button class="constraint-action-btn" @click="admin.duplicateConstraint(idx)" title="Duplicate">&#10697;</button>
                <button class="constraint-action-btn constraint-action-btn--danger" @click="admin.removeConstraint(idx)" title="Delete">&#10005;</button>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Empty state -->
      <div class="constraint-empty-state" v-show="!admin.profileEditor.constraints || admin.profileEditor.constraints.length === 0">
        No rules defined. Add rules below to filter which recipes are selected.
      </div>
    </div>

    <!-- Quick Add presets + Add constraint dropdown -->
    <div style="display:flex; gap:0.5rem; flex-wrap:wrap; align-items:flex-start;">
      <div class="add-constraint-dropdown">
        <button class="btn-add-constraint btn-secondary" @click="quickAddOpen = !quickAddOpen" type="button" style="font-size:0.8rem; height:30px;">
          <span>Quick Add</span>
          <span style="font-size: 0.7em; margin-left: 0.5rem;">{{ quickAddOpen ? '\u25B2' : '\u25BC' }}</span>
        </button>
        <div class="add-constraint-menu" v-show="quickAddOpen">
          <button class="add-constraint-option" @click="admin.quickAddConstraint('theme-keywords'); quickAddOpen = false">
            <span class="add-constraint-option-icon" v-html="constraintTypes.keyword?.icon"></span>
            <span class="add-constraint-option-content"><span class="add-constraint-option-label">Theme Keywords</span><span class="add-constraint-option-desc">Require recipes with specific tags</span></span>
          </button>
          <button class="add-constraint-option" @click="admin.quickAddConstraint('avoid-keywords'); quickAddOpen = false">
            <span class="add-constraint-option-icon" v-html="constraintTypes.keyword?.icon"></span>
            <span class="add-constraint-option-content"><span class="add-constraint-option-label">Avoid Keywords</span><span class="add-constraint-option-desc">Exclude recipes with certain tags</span></span>
          </button>
          <button class="add-constraint-option" @click="admin.quickAddConstraint('include-foods'); quickAddOpen = false">
            <span class="add-constraint-option-icon" v-html="constraintTypes.food?.icon"></span>
            <span class="add-constraint-option-content"><span class="add-constraint-option-label">Include Foods</span><span class="add-constraint-option-desc">Require recipes with specific ingredients</span></span>
          </button>
          <button class="add-constraint-option" @click="admin.quickAddConstraint('avoid-foods'); quickAddOpen = false">
            <span class="add-constraint-option-icon" v-html="constraintTypes.food?.icon"></span>
            <span class="add-constraint-option-content"><span class="add-constraint-option-label">Avoid Foods</span><span class="add-constraint-option-desc">Exclude recipes with certain ingredients</span></span>
          </button>
          <button class="add-constraint-option" @click="admin.quickAddConstraint('from-books'); quickAddOpen = false">
            <span class="add-constraint-option-icon" v-html="constraintTypes.book?.icon"></span>
            <span class="add-constraint-option-content"><span class="add-constraint-option-label">From Books</span><span class="add-constraint-option-desc">Pick from specific recipe books</span></span>
          </button>
          <button class="add-constraint-option" @click="admin.quickAddConstraint('min-rating'); quickAddOpen = false">
            <span class="add-constraint-option-icon" v-html="constraintTypes.rating?.icon"></span>
            <span class="add-constraint-option-content"><span class="add-constraint-option-label">Min Rating</span><span class="add-constraint-option-desc">Only highly rated recipes</span></span>
          </button>
          <button class="add-constraint-option" @click="admin.quickAddConstraint('avoid-recent'); quickAddOpen = false">
            <span class="add-constraint-option-icon" v-html="constraintTypes.cookedon?.icon"></span>
            <span class="add-constraint-option-content"><span class="add-constraint-option-label">Avoid Recent</span><span class="add-constraint-option-desc">Skip recipes cooked in last 14 days</span></span>
          </button>
          <button class="add-constraint-option" @click="admin.quickAddConstraint('include-new'); quickAddOpen = false">
            <span class="add-constraint-option-icon" v-html="constraintTypes.createdon?.icon"></span>
            <span class="add-constraint-option-content"><span class="add-constraint-option-label">Include New</span><span class="add-constraint-option-desc">Include recipes added in last 30 days</span></span>
          </button>
        </div>
      </div>
      <div class="add-constraint-dropdown">
        <button class="btn-add-constraint" @click="addRuleOpen = !addRuleOpen" type="button">
          <span>+ Add Rule</span>
          <span style="font-size: 0.7em; margin-left: 0.5rem;">{{ addRuleOpen ? '\u25B2' : '\u25BC' }}</span>
        </button>
        <div class="add-constraint-menu" v-show="addRuleOpen">
          <button v-for="(typeInfo, typeKey) in constraintTypes" :key="typeKey"
                  class="add-constraint-option" @click="admin.addConstraint(typeKey); addRuleOpen = false">
            <span class="add-constraint-option-icon" v-html="typeInfo.icon"></span>
            <span class="add-constraint-option-content">
              <span class="add-constraint-option-label">{{ typeInfo.label }}</span>
              <span class="add-constraint-option-desc">{{ typeInfo.description }}</span>
            </span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import SearchDropdown from '@/components/shared/SearchDropdown.vue'
import type { SearchDropdownItem } from '@/components/shared/SearchDropdown.vue'
import { useAdminStore, CONSTRAINT_TYPES } from '@/stores/admin'

const admin = useAdminStore()
const constraintTypes = CONSTRAINT_TYPES

const quickAddOpen = ref(false)
const addRuleOpen = ref(false)
</script>
