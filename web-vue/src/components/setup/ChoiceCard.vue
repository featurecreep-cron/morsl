<script setup lang="ts">
defineProps<{
  selected: boolean
  label: string
  description: string
}>()

defineEmits<{
  select: []
}>()
</script>

<template>
  <div
    class="setup-choice-card"
    :class="{ selected }"
    role="radio"
    :aria-checked="selected"
    tabindex="0"
    @click="$emit('select')"
    @keydown.enter="$emit('select')"
    @keydown.space.prevent="$emit('select')"
  >
    <div class="setup-choice-radio">
      <div class="setup-choice-radio-dot" />
    </div>
    <div class="setup-choice-content">
      <div class="setup-choice-label">{{ label }}</div>
      <div class="setup-choice-desc">{{ description }}</div>
    </div>
  </div>
</template>
