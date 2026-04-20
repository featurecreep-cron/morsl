<template>
  <div class="branding-field">
    <label class="branding-label">{{ label }}</label>
    <div class="branding-image-row">
      <div class="branding-cell-preview">
        <!-- Logo: two states (default / custom) -->
        <template v-if="!showUseLogo">
          <div v-show="!imageUrl" class="branding-preview" :class="previewClass"></div>
          <div v-show="imageUrl" class="branding-preview" :class="previewClass"></div>
        </template>
        <!-- Favicon / Loading Icon: three states (default / custom / use-logo) -->
        <template v-else>
          <div v-show="!imageUrl && !useLogo" class="branding-preview" :class="previewClass"></div>
          <div v-show="imageUrl && !useLogo" class="branding-preview" :class="previewClass"></div>
          <div v-show="useLogo && logoUrl" class="branding-preview" :class="previewClass"></div>
        </template>
      </div>
      <div class="branding-cell-actions">
        <button v-show="!showUseLogo || !useLogo" class="btn-branding" @click="fileInput?.click()">Upload</button>
        <input type="file" :accept="accept" @change="$emit('upload', $event)" ref="fileInput" hidden>
        <button v-show="imageUrl && (!showUseLogo || !useLogo)" class="btn-branding btn-branding--reset"
                @click="$emit('remove')">Remove</button>
      </div>
      <div class="branding-cell-toggle">
        <!-- "Show in header" toggle (logo only) -->
        <span v-if="showToggle && imageUrl" class="branding-toggle-inline">
          <label class="toggle-switch-sm">
            <input type="checkbox"
                   :checked="showToggleValue"
                   @change="$emit('toggle-show', ($event.target as HTMLInputElement).checked)">
            <span class="toggle-track-sm"></span>
          </label>
          <span class="branding-toggle-label">Show in header</span>
        </span>
        <!-- "Use logo" toggle (favicon / loading icon) -->
        <span v-if="showUseLogo" class="branding-toggle-inline">
          <label class="toggle-switch-sm" :class="{ 'toggle-disabled': !logoUrl }">
            <input type="checkbox"
                   :checked="useLogo"
                   :disabled="!logoUrl"
                   @change="$emit('toggle-use-logo', ($event.target as HTMLInputElement).checked)">
            <span class="toggle-track-sm"></span>
          </label>
          <span class="branding-toggle-label"
                :title="!logoUrl ? 'Upload a logo first' : ''">Use logo</span>
        </span>
      </div>
    </div>
    <small class="branding-help">{{ helpText }}</small>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = withDefaults(defineProps<{
  label: string
  type: string
  imageUrl: string
  useLogo?: boolean
  logoUrl?: string
  showUseLogo?: boolean
  showToggle?: boolean
  showToggleValue?: boolean
  helpText?: string
  accept?: string
}>(), {
  useLogo: false,
  logoUrl: '',
  showUseLogo: false,
  showToggle: false,
  showToggleValue: false,
  helpText: '',
  accept: '.svg,.png,.jpg,.jpeg,.webp',
})

defineEmits<{
  upload: [event: Event]
  remove: []
  'toggle-use-logo': [checked: boolean]
  'toggle-show': [checked: boolean]
}>()

const fileInput = ref<HTMLInputElement | null>(null)

const previewClass = computed(() =>
  props.type === 'logo' ? 'branding-preview--logo' : undefined
)
</script>
