<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import qrcode from 'qrcode-generator'

const settings = useSettingsStore()

const wifiRef = ref<HTMLElement | null>(null)
const menuRef = ref<HTMLElement | null>(null)

function renderQr(container: HTMLElement | null, data: string) {
  if (!container || !data) return
  const codeEl = container.querySelector('.qr-corner-code') as HTMLElement | null
  if (!codeEl) return
  try {
    const qr = qrcode(0, 'M')
    qr.addData(data)
    qr.make()
    codeEl.innerHTML = qr.createSvgTag({ cellSize: 2, margin: 1 })
  } catch {
    // skip invalid data
  }
}

function renderAll() {
  nextTick(() => {
    renderQr(wifiRef.value, settings.qrWifiString)
    renderQr(menuRef.value, settings.qrMenuUrl)
  })
}

onMounted(() => renderAll())

watch(() => [settings.qrShowOnMenu, settings.qrWifiString, settings.qrMenuUrl], () => {
  renderAll()
})
</script>

<template>
  <div
    v-if="settings.qrShowOnMenu && (settings.qrWifiString || settings.qrMenuUrl)"
    class="qr-corner"
  >
    <div v-if="settings.qrWifiString" ref="wifiRef" class="qr-corner-item">
      <div class="qr-corner-code" />
      <span class="qr-corner-label">WiFi</span>
    </div>
    <div v-if="settings.qrMenuUrl" ref="menuRef" class="qr-corner-item">
      <div class="qr-corner-code" />
      <span class="qr-corner-label">Menu</span>
    </div>
  </div>
</template>
