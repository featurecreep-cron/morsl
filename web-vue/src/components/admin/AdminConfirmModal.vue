<template>
  <Teleport to="body">
    <!-- Confirmation Modal -->
    <Transition name="confirm-fade">
      <div class="modal-backdrop confirm-modal-backdrop"
           v-show="admin.confirmModal.show"
           @click.self="admin.confirmModal.show = false">
        <Transition name="confirm-scale">
          <div class="confirm-modal"
               v-show="admin.confirmModal.show"
               role="dialog" aria-modal="true" aria-labelledby="admin-confirm-title">
            <h3 id="admin-confirm-title">{{ admin.confirmModal.title }}</h3>
            <p>{{ admin.confirmModal.message }}</p>
            <div class="confirm-modal-actions">
              <button class="btn-generate btn-secondary" @click="admin.confirmModal.show = false">Cancel</button>
              <button class="btn-generate btn-danger" @click="onConfirm">
                {{ admin.confirmModal.confirmText || 'Confirm' }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { useAdminStore } from '@/stores/admin'

const admin = useAdminStore()

function onConfirm() {
  admin.confirmModal.onConfirm()
  admin.confirmModal.show = false
}
</script>

<style scoped>
.confirm-fade-enter-active { transition: opacity 0.2s ease-out; }
.confirm-fade-leave-active { transition: opacity 0.2s ease-in; }
.confirm-fade-enter-from,
.confirm-fade-leave-to { opacity: 0; }

.confirm-scale-enter-active { transition: all 0.2s ease-out; }
.confirm-scale-leave-active { transition: all 0.15s ease-in; }
.confirm-scale-enter-from { opacity: 0; transform: scale(0.95); }
.confirm-scale-leave-to { opacity: 0; transform: scale(0.95); }
</style>
