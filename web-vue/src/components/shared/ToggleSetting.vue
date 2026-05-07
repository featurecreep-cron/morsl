<template>
  <div class="settings-row">
    <div class="settings-label">
      {{ label }}
      <small v-if="help">{{ help }}</small>
    </div>
    <label class="toggle-switch">
      <input type="checkbox" :checked="modelValue" @change="$emit('update:modelValue', ($event.target as HTMLInputElement).checked)">
      <span class="toggle-track"></span>
    </label>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  modelValue: boolean
  help?: string
}>()

defineEmits<{
  'update:modelValue': [value: boolean]
}>()
</script>
