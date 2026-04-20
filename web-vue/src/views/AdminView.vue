<script setup lang="ts">
import '@/assets/admin.css'
import { onMounted, onUnmounted, ref, provide } from 'vue'
import { useAdminStore } from '@/stores/admin'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import GenerateTab from '@/components/admin/GenerateTab.vue'
import ProfilesTab from '@/components/admin/ProfilesTab.vue'
import WeeklyTab from '@/components/admin/WeeklyTab.vue'
import SettingsTab from '@/components/admin/SettingsTab.vue'
import BrandingTab from '@/components/admin/BrandingTab.vue'
import OrdersTab from '@/components/admin/OrdersTab.vue'
import PinGate from '@/components/admin/PinGate.vue'
import ProfileDrawer from '@/components/admin/ProfileDrawer.vue'
import TemplateDrawer from '@/components/admin/TemplateDrawer.vue'
import AdminConfirmModal from '@/components/admin/AdminConfirmModal.vue'
import AdminRecipeModal from '@/components/admin/AdminRecipeModal.vue'
import AdminToasts from '@/components/admin/AdminToasts.vue'
import IconPicker from '@/components/admin/IconPicker.vue'

const admin = useAdminStore()

const iconPickerRef = ref<InstanceType<typeof IconPicker> | null>(null)
provide('iconPickerRef', iconPickerRef)

onMounted(() => {
  admin.init()
})

onUnmounted(() => {
  admin.destroy()
})

function focusNextTab(e: KeyboardEvent) {
  const tabs = Array.from(
    (e.currentTarget as HTMLElement).querySelectorAll<HTMLElement>('[role="tab"]:not([style*="display: none"])'),
  )
  const idx = tabs.indexOf(e.target as HTMLElement)
  if (idx >= 0 && idx < tabs.length - 1) tabs[idx + 1].focus()
}

function focusPrevTab(e: KeyboardEvent) {
  const tabs = Array.from(
    (e.currentTarget as HTMLElement).querySelectorAll<HTMLElement>('[role="tab"]:not([style*="display: none"])'),
  )
  const idx = tabs.indexOf(e.target as HTMLElement)
  if (idx > 0) tabs[idx - 1].focus()
}
</script>

<template>
  <!-- PIN Gate overlay -->
  <PinGate />

  <div class="admin-shell" @keydown.escape="admin.closeRecipe()">
    <!-- Header -->
    <AdminHeader v-show="admin.adminReady" />

    <main v-show="admin.adminReady" class="admin-content">
      <!-- Tab Bar -->
      <nav
        class="admin-tabs"
        role="tablist"
        @keydown.arrow-right.prevent="focusNextTab"
        @keydown.arrow-left.prevent="focusPrevTab"
      >
        <button
          id="tab-generate"
          class="admin-tab"
          :class="{ active: admin.activeTab === 'generate' }"
          role="tab"
          :aria-selected="admin.activeTab === 'generate'"
          :tabindex="admin.activeTab === 'generate' ? 0 : -1"
          aria-controls="panel-generate"
          @click="admin.activeTab = 'generate'"
        >Generate</button>

        <button
          id="tab-profiles"
          class="admin-tab"
          :class="{ active: admin.activeTab === 'profiles' }"
          role="tab"
          :aria-selected="admin.activeTab === 'profiles'"
          :tabindex="admin.activeTab === 'profiles' ? 0 : -1"
          aria-controls="panel-profiles"
          @click="admin.activeTab = 'profiles'"
        >Profiles</button>

        <button
          id="tab-weekly"
          class="admin-tab"
          :class="{ active: admin.activeTab === 'weekly' }"
          role="tab"
          :aria-selected="admin.activeTab === 'weekly'"
          :tabindex="admin.activeTab === 'weekly' ? 0 : -1"
          aria-controls="panel-weekly"
          @click="admin.activeTab = 'weekly'"
        >Weekly</button>

        <button
          id="tab-settings"
          class="admin-tab"
          :class="{ active: admin.activeTab === 'settings' }"
          role="tab"
          :aria-selected="admin.activeTab === 'settings'"
          :tabindex="admin.activeTab === 'settings' ? 0 : -1"
          aria-controls="panel-settings"
          @click="admin.activeTab = 'settings'"
        >Settings</button>

        <button
          v-show="admin.tierVisible('advanced')"
          id="tab-branding"
          class="admin-tab"
          :class="{ active: admin.activeTab === 'branding' }"
          role="tab"
          :aria-selected="admin.activeTab === 'branding'"
          :tabindex="admin.activeTab === 'branding' ? 0 : -1"
          aria-controls="panel-branding"
          @click="admin.activeTab = 'branding'"
        >Branding</button>

        <button
          v-show="admin.tierVisible('advanced') && admin.settings.orders_enabled !== false"
          id="tab-orders"
          class="admin-tab"
          :class="{ active: admin.activeTab === 'orders' }"
          role="tab"
          :aria-selected="admin.activeTab === 'orders'"
          :tabindex="admin.activeTab === 'orders' ? 0 : -1"
          aria-controls="panel-orders"
          @click="admin.activeTab = 'orders'"
        >
          Requests
          <span v-show="admin.orders.length > 0" class="tab-badge">{{ admin.orders.length }}</span>
        </button>
      </nav>

      <!-- Tab Panels -->
      <GenerateTab v-show="admin.activeTab === 'generate'" />
      <ProfilesTab v-show="admin.activeTab === 'profiles'" />
      <WeeklyTab v-show="admin.activeTab === 'weekly'" />
      <SettingsTab v-show="admin.activeTab === 'settings'" />
      <BrandingTab v-show="admin.activeTab === 'branding'" />
      <OrdersTab v-show="admin.activeTab === 'orders'" />
    </main>

    <!-- Drawers & Modals -->
    <ProfileDrawer />
    <TemplateDrawer />
    <IconPicker ref="iconPickerRef" />
    <AdminConfirmModal />
    <AdminRecipeModal />
    <AdminToasts />
  </div>
</template>

<style>
/* Admin shell layout — matches .admin-shell in admin.css */
</style>
