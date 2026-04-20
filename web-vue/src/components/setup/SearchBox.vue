<script setup lang="ts">
import { CONST } from '@/constants'
import { ref, onUnmounted } from 'vue'

const props = defineProps<{
  endpoint: string
  debounceMs?: number
  placeholder?: string
  ariaLabel?: string
  excludeIds?: Set<number>
}>()

const emit = defineEmits<{
  select: [item: { id: number; name: string }]
  focus: []
}>()

const query = ref('')
const results = ref<Array<{ id: number; name: string }>>([])
let timerId: ReturnType<typeof setTimeout> | null = null

function onInput(value: string) {
  query.value = value
  if (timerId) clearTimeout(timerId)
  if (value.length < 2) {
    results.value = []
    return
  }
  const ms = props.debounceMs ?? CONST.KEYWORD_DEBOUNCE_MS
  timerId = setTimeout(async () => {
    try {
      const res = await fetch(`${props.endpoint}?search=${encodeURIComponent(value)}&limit=20`)
      if (res.ok) {
        const data = await res.json()
        const excluded = props.excludeIds ?? new Set<number>()
        results.value = (data.results || data).filter(
          (item: { id: number }) => !excluded.has(item.id),
        )
      }
    } catch {
      // ignore
    }
  }, ms)
}

function selectItem(item: { id: number; name: string }) {
  emit('select', item)
  query.value = ''
  results.value = []
}

function clear() {
  query.value = ''
  results.value = []
}

onUnmounted(() => {
  if (timerId) clearTimeout(timerId)
})

defineExpose({ clear })
</script>

<template>
  <div class="setup-search-box">
    <input
      type="text"
      :placeholder="placeholder ?? 'Search...'"
      :aria-label="ariaLabel ?? placeholder ?? 'Search'"
      :value="query"
      @input="onInput(($event.target as HTMLInputElement).value)"
      @focus="$emit('focus')"
    >
    <div v-if="results.length > 0" class="setup-search-results">
      <button
        v-for="item in results"
        :key="item.id"
        @click="selectItem(item)"
      >
        {{ item.name }}
      </button>
    </div>
  </div>
</template>
