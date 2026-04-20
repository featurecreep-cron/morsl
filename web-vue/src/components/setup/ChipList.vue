<script setup lang="ts">
defineProps<{
  items: Array<{ id: number; name: string }>
  variant?: 'default' | 'exclude'
}>()

defineEmits<{
  remove: [index: number]
}>()
</script>

<template>
  <div v-if="items.length > 0" class="setup-chips">
    <span
      v-for="(item, idx) in items"
      :key="item.id"
      class="setup-chip"
      :class="{ exclude: variant === 'exclude' }"
    >
      <span>{{ item.name }}</span>
      <button
        :aria-label="'Remove ' + item.name"
        @click="$emit('remove', idx)"
      >
        &times;
      </button>
    </span>
  </div>
</template>
