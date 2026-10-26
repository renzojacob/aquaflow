<!--
  EmptyState — what a list shows when there's nothing in it yet.
  Usage: <EmptyState title="No orders yet" message="..." action-label="Order water" @action="goOrder" />
  Pass your own picture in the "icon" slot if needed.
-->
<script setup>
import AppButton from './AppButton.vue'

defineProps({
  title: { type: String, required: true },
  message: { type: String, default: '' },
  actionLabel: { type: String, default: '' },
})
defineEmits(['action'])
</script>

<template>
  <div class="af-empty">
    <slot name="icon">
      <!-- 5-gallon container, partly filled -->
      <svg width="56" height="56" viewBox="0 0 56 56" fill="none" aria-hidden="true">
        <rect x="14" y="10" width="28" height="38" rx="8" fill="var(--af-primary-tint)" />
        <rect x="21" y="5" width="14" height="7" rx="3" fill="var(--af-water)" />
        <path d="M14 32c5-3 9 3 14 0s9-3 14 0v8a8 8 0 0 1-8 8H22a8 8 0 0 1-8-8v-8Z" fill="var(--af-water)" />
      </svg>
    </slot>
    <h3>{{ title }}</h3>
    <p v-if="message">{{ message }}</p>
    <AppButton v-if="actionLabel" @click="$emit('action')">{{ actionLabel }}</AppButton>
  </div>
</template>

<style scoped>
.af-empty {
  display: grid;
  justify-items: center;
  text-align: center;
  gap: var(--af-s2);
  padding: var(--af-s6) var(--af-s4);
}
.af-empty h3 { margin: var(--af-s2) 0 0; font-size: 17px; font-weight: 700; }
.af-empty p { margin: 0 0 var(--af-s3); color: var(--af-ink-2); font-size: 14px; max-width: 34ch; }
</style>