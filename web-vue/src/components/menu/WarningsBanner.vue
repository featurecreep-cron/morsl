<script setup lang="ts">
import type { RelaxedConstraint } from '@/types/api'
import { formatRelaxedConstraint } from '@/utils/formatting'

defineProps<{
  warnings: string[]
  relaxedConstraints: RelaxedConstraint[]
}>()
</script>

<template>
  <div
    v-if="warnings.length > 0 || relaxedConstraints.length > 0"
    class="warnings-bar"
  >
    <span
      v-for="(warning, idx) in warnings"
      :key="`w-${idx}`"
      class="warning-badge"
    >{{ warning }}</span>
    <span
      v-for="(rc, idx) in relaxedConstraints"
      :key="`rc-${idx}`"
      class="relaxed-badge"
    >{{ formatRelaxedConstraint(rc) }}</span>
  </div>
</template>

<style scoped>
.warnings-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: center;
  padding: 0.5rem 1rem;
}

.warning-badge {
  background: var(--warning-bg, rgba(255, 193, 7, 0.2));
  color: var(--warning-text, #ffc107);
  padding: 0.25rem 0.75rem;
  border-radius: 1rem;
  font-size: 0.8rem;
  font-family: var(--body-font);
}

.relaxed-badge {
  background: var(--info-bg, rgba(59, 130, 246, 0.15));
  color: var(--info-text, #60a5fa);
  padding: 0.25rem 0.75rem;
  border-radius: 1rem;
  font-size: 0.8rem;
  font-family: var(--body-font);
}
</style>
