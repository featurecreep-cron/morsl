<script setup lang="ts">
defineProps<{
  visible: boolean
  message: string
  variant?: 'default' | 'success'
  dismissible?: boolean
}>()

const emit = defineEmits<{
  dismiss: []
}>()
</script>

<template>
  <Teleport to="body">
    <Transition name="toast">
      <div
        v-if="visible"
        class="order-toast"
        :class="{ 'order-status-ready': variant === 'success' }"
      >
        <span class="order-toast-icon">
          {{ variant === 'success' ? '\u2713' : '\u2139' }}
        </span>
        <span class="order-toast-text">{{ message }}</span>
        <button
          v-if="dismissible"
          class="order-toast-dismiss"
          @click="emit('dismiss')"
        >&times;</button>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.order-toast {
  position: fixed;
  bottom: 5rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background: var(--accent-color, #d4a847);
  color: var(--bg-color, #0d0d0d);
  border-radius: 2rem;
  font-family: var(--body-font);
  font-size: 0.9rem;
  font-weight: 600;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

.order-toast-icon { font-size: 1.1rem; }
.order-toast-text { white-space: nowrap; }

.order-status-ready {
  background: var(--success-bg, #22c55e);
  color: var(--bg-color, #0d0d0d);
}

.order-toast-dismiss {
  background: none;
  border: none;
  color: inherit;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0 0.25rem;
  margin-left: 0.25rem;
  opacity: 0.7;
}

.order-toast-dismiss:hover { opacity: 1; }

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(1rem);
}
</style>
