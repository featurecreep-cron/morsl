<script setup lang="ts">
defineProps<{
  step: number
  totalSteps?: number
}>()
</script>

<template>
  <div class="setup-progress">
    <div v-for="s in (totalSteps ?? 6)" :key="s" class="setup-progress-step">
      <div
        class="setup-progress-dot"
        :class="{ active: step === s, done: step > s }"
      >
        {{ step > s ? '\u2713' : s }}
      </div>
      <div
        v-if="s < (totalSteps ?? 6)"
        class="setup-progress-line"
        :class="{ done: step > s }"
      />
    </div>
  </div>
</template>
