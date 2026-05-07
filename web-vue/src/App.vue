<script setup lang="ts">
import { onMounted } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { useProfilesStore } from '@/stores/profiles'
import { useTheme } from '@/composables/useTheme'
import { preloadCustomIcons } from '@/utils/icons'

const settings = useSettingsStore()
const profiles = useProfilesStore()

// Initialize theme system
useTheme()

onMounted(async () => {
  await Promise.all([settings.load(), profiles.load(), preloadCustomIcons()])
})
</script>

<template>
  <router-view />
</template>
