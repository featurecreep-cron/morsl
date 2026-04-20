<script setup lang="ts">
import { computed } from 'vue'
import { useMenuStore } from '@/stores/menu'

const menu = useMenuStore()
const isOpen = computed(() => menu.confirmModal.show)

function confirm() {
  menu.confirmModal.onConfirm()
}

function cancel() {
  menu.confirmModal.show = false
}
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="confirm-modal-backdrop modal-backdrop" @click.self="cancel">
      <div class="confirm-modal">
        <h3>{{ menu.confirmModal.title }}</h3>
        <p>{{ menu.confirmModal.message }}</p>
        <div class="confirm-modal-actions">
          <button class="btn-secondary" @click="cancel">Cancel</button>
          <button class="btn-danger" @click="confirm">{{ menu.confirmModal.confirmText }}</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.confirm-modal-backdrop {
  position: fixed;
  inset: 0;
  background: var(--overlay-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1100;
  padding: 1rem;
}

.confirm-modal {
  background: var(--modal-bg, #1a1a1a);
  border: 1px solid var(--card-border, rgba(255,255,255,0.1));
  border-radius: var(--modal-radius, 0.75rem);
  box-shadow: var(--card-shadow, none);
  padding: 1.5rem;
  max-width: 380px;
  width: 90%;
  text-align: center;
}

.confirm-modal h3 {
  font-family: var(--heading-font);
  font-size: 1.1rem;
  color: var(--accent-color);
  margin: 0 0 0.75rem;
}

.confirm-modal p {
  font-size: 0.9rem;
  color: var(--text-color);
  margin: 0 0 1.25rem;
  line-height: 1.4;
}

.confirm-modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
}

.confirm-modal-actions button {
  flex: 1;
  max-width: 160px;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  border: 1px solid var(--btn-border, rgba(255,255,255,0.15));
  font-size: 0.85rem;
  cursor: pointer;
  white-space: nowrap;
}

.btn-secondary {
  background: var(--btn-bg, rgba(255,255,255,0.08));
  color: var(--text-color);
}

.btn-danger {
  background: #dc2626;
  color: #fff;
  border-color: #dc2626;
}

.btn-danger:hover:not(:disabled) {
  background: #b91c1c;
}
</style>
