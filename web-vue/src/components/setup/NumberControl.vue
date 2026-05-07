<script setup lang="ts">
const props = defineProps<{
  modelValue: number
  min?: number
  max?: number
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number]
  increment: []
  decrement: []
}>()

function onInput(e: Event) {
  const val = Math.max(props.min ?? 1, +(e.target as HTMLInputElement).value)
  emit('update:modelValue', val)
}
</script>

<template>
  <div class="setup-number-control">
    <button
      :disabled="modelValue <= (min ?? 1)"
      @click="$emit('decrement')"
    >
      &minus;
    </button>
    <input
      type="number"
      :value="modelValue"
      :min="min ?? 1"
      :max="max ?? 50"
      @input="onInput"
    >
    <button
      :disabled="modelValue >= (max ?? 50)"
      @click="$emit('increment')"
    >
      +
    </button>
  </div>
</template>
