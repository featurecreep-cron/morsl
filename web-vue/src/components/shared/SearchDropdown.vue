<template>
  <div class="constraint-item-search" style="position: relative;" v-click-outside="clearResults">
    <input type="text" class="drawer-input" :placeholder="placeholder"
           :value="modelValue" @input="onInput">
    <ul class="search-results-list" v-show="results.length > 0">
      <li v-for="item in results" :key="item.id" class="search-result-row"
          @click="$emit('select', item)">
        <span class="search-result-path">{{ item.path || item.name }}</span>
      </li>
    </ul>
    <small v-if="emptyMessage && modelValue.length >= 2 && results.length === 0"
           class="field-hint" style="color: var(--text-muted);">{{ emptyMessage }}</small>
  </div>
</template>

<script setup lang="ts">
export interface SearchDropdownItem {
  id: number
  name: string
  path?: string
  [key: string]: unknown
}

const props = withDefaults(defineProps<{
  modelValue: string
  results: SearchDropdownItem[]
  placeholder?: string
  emptyMessage?: string
}>(), {
  placeholder: 'Type to search...',
  emptyMessage: '',
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  search: []
  select: [item: SearchDropdownItem]
}>()

let debounceTimer: ReturnType<typeof setTimeout> | null = null

function onInput(event: Event) {
  const value = (event.target as HTMLInputElement).value
  emit('update:modelValue', value)
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    emit('search')
  }, 200)
}

function clearResults() {
  // Parent handles clearing via update:modelValue if needed
}

const vClickOutside = {
  mounted(el: HTMLElement, binding: { value: () => void }) {
    (el as HTMLElement & { _clickOutside: (e: MouseEvent) => void })._clickOutside = (e: MouseEvent) => {
      if (!el.contains(e.target as Node)) binding.value()
    }
    document.addEventListener('click', (el as HTMLElement & { _clickOutside: (e: MouseEvent) => void })._clickOutside)
  },
  unmounted(el: HTMLElement) {
    document.removeEventListener('click', (el as HTMLElement & { _clickOutside: (e: MouseEvent) => void })._clickOutside)
  },
}
</script>
