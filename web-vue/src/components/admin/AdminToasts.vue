<template>
  <Teleport to="body">
    <!-- Reload prompt toast -->
    <Transition name="toast-slide">
      <div class="reload-toast"
           role="alert" aria-live="assertive" aria-atomic="true"
           v-show="admin.reloadToastShow"
           style="position:fixed; bottom:1.5rem; left:50%; transform:translateX(-50%); z-index:1100; background:var(--card-bg, #1a1a1a); border:1px solid var(--border-color, #333); border-radius:8px; padding:0.75rem 1rem; display:flex; align-items:center; gap:0.75rem; box-shadow:0 4px 12px rgba(0,0,0,0.4); max-width:90vw;">
        <span style="font-size:0.9rem;">{{ admin.reloadToastMsg }}</span>
        <button class="btn-generate" @click="reload()" style="height:28px; font-size:0.8rem; padding:0 0.75rem; white-space:nowrap;">Reload</button>
        <button @click="admin.dismissReloadPrompt()" aria-label="Dismiss" style="background:none; border:none; color:var(--text-muted, #999); cursor:pointer; font-size:1.2rem; padding:0 0.25rem;">&times;</button>
      </div>
    </Transition>

    <!-- Error toast -->
    <Transition name="toast-slide">
      <div class="reload-toast"
           role="alert" aria-live="assertive" aria-atomic="true"
           v-show="admin.errorShow"
           style="position:fixed; bottom:4.5rem; left:50%; transform:translateX(-50%); z-index:1100; background:var(--card-bg, #1a1a1a); border:1px solid #dc3545; border-radius:8px; padding:0.75rem 1rem; display:flex; align-items:center; gap:0.75rem; box-shadow:0 4px 12px rgba(0,0,0,0.4); max-width:90vw;">
        <span style="font-size:0.9rem; color:#dc3545;">{{ admin.errorMsg }}</span>
        <button @click="admin.dismissError()" aria-label="Dismiss error" style="background:none; border:none; color:var(--text-muted, #999); cursor:pointer; font-size:1.2rem; padding:0 0.25rem;">&times;</button>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { useAdminStore } from '@/stores/admin'

const admin = useAdminStore()

function reload() {
  window.location.reload()
}
</script>

<style scoped>
.toast-slide-enter-active { transition: all 0.3s ease-out; }
.toast-slide-leave-active { transition: all 0.2s ease-in; }
.toast-slide-enter-from { opacity: 0; transform: translateX(-50%) translateY(1rem); }
.toast-slide-leave-to { opacity: 0; transform: translateX(-50%) translateY(1rem); }
</style>
