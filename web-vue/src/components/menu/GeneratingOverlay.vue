<script setup lang="ts">
import { computed } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { getLoadingIconHtml, STOCK_ICON_SVG } from '@/utils/icons'

defineProps<{
  visible: boolean
}>()

const settings = useSettingsStore()

const iconHtml = computed(() => {
  return getLoadingIconHtml(settings.loadingIconUrl, settings.loaded) || STOCK_ICON_SVG
})
</script>

<template>
  <Transition name="fade">
    <div v-if="visible" class="mixing-indicator">
      <!-- eslint-disable-next-line vue/no-v-html -->
      <div class="shaker-icon" v-html="iconHtml" />
    </div>
  </Transition>
</template>

<style scoped>
.mixing-indicator {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 900;
  pointer-events: none;
}

.shaker-icon {
  font-size: 3rem;
  width: 6rem;
  height: 6rem;
  display: inline-block;
  animation: shake 0.6s ease-in-out infinite;
  color: var(--accent-color);
  filter: drop-shadow(0 4px 20px rgba(0,0,0,0.5));
}

@keyframes shake {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(-15deg); }
  75% { transform: rotate(15deg); }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
