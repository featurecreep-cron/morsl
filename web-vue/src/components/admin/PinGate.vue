<template>
  <Teleport to="body">
    <!-- PIN Gate overlay (blocks admin until PIN verified) -->
    <Transition name="pin-fade">
      <div class="pin-gate-backdrop" v-show="admin.showPinGate">
        <div class="pin-gate-modal"
             role="dialog" aria-modal="true" aria-labelledby="admin-pin-title">
          <h2 id="admin-pin-title" class="pin-gate-title">Admin Access</h2>
          <p class="pin-gate-subtitle">Enter PIN to continue</p>
          <form @submit.prevent="admin.submitPin()">
            <div class="pin-gate-input-wrap">
              <input :type="admin.showPinText ? 'tel' : 'password'" class="pin-gate-input"
                     v-model="admin.pinInput"
                     placeholder="PIN"
                     maxlength="4"
                     pattern="[0-9]*"
                     autocomplete="off"
                     inputmode="numeric"
                     ref="pinGateInput"
                     @input="onPinInput">
              <button type="button" class="pin-gate-show-toggle"
                      @click="admin.showPinText = !admin.showPinText"
                      :title="admin.showPinText ? 'Hide PIN' : 'Show PIN'"
                      tabindex="-1">
                <span v-show="!admin.showPinText">&#128065;</span>
                <span v-show="admin.showPinText">&#128064;</span>
              </button>
            </div>
            <p class="pin-gate-error" v-show="admin.pinError">{{ admin.pinError }}</p>
            <button type="submit" class="pin-gate-submit">Unlock</button>
          </form>
          <button class="pin-gate-back" @click="window.location.href = '/'">Back to menu</button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useAdminStore } from '@/stores/admin'

const admin = useAdminStore()
const pinGateInput = ref<HTMLInputElement | null>(null)

function onPinInput() {
  if (admin.pinInput.length >= 4) admin.submitPin()
}

// Auto-focus the PIN input when the gate appears
watch(() => admin.showPinGate, (show) => {
  if (show) {
    setTimeout(() => pinGateInput.value?.focus(), 100)
  }
})
</script>

<style scoped>
.pin-fade-enter-active { transition: opacity 0.2s ease-out; }
.pin-fade-leave-active { transition: opacity 0.2s ease-in; }
.pin-fade-enter-from,
.pin-fade-leave-to { opacity: 0; }
</style>
