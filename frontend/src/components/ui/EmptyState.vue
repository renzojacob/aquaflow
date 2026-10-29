<!--
  EmptyState — what a list shows when there's nothing in it yet.
  Usage: <EmptyState title="No orders yet" message="..." action-label="Order water" @action="goOrder" />
  Pass your own picture in the "icon" slot if needed.
-->
<script setup>
import AppButton from './AppButton.vue'
import LiquidFill from './LiquidFill.vue'

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
      <!-- An almost-empty 5-gallon container with ripples on the floor -->
      <span class="af-empty__art" aria-hidden="true">
        <span class="af-empty__ring"></span>
        <span class="af-empty__ring af-empty__ring--2"></span>
        <LiquidFill shape="jug" :level="0.14" :size="78" />
      </span>
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
.af-empty h3 { margin: var(--af-s3) 0 0; font-family: var(--af-display); font-size: 18px; font-weight: 600; letter-spacing: -0.015em; }
.af-empty p { margin: 0 0 var(--af-s3); color: var(--af-ink-2); font-size: 14px; line-height: 1.5; max-width: 34ch; }

.af-empty__art { position: relative; display: grid; place-items: center; width: 140px; height: 124px; }
.af-empty__art :deep(svg) { position: relative; z-index: 1; filter: drop-shadow(0 12px 18px rgba(0, 0, 0, 0.2)); animation: af-empty-bob 6s ease-in-out infinite; }
.af-empty__ring {
  position: absolute;
  left: 50%;
  bottom: 2px;
  width: 130px;
  height: 26px;
  border-radius: 50%;
  border: 1.5px solid color-mix(in srgb, var(--af-water) 60%, transparent);
  transform: translateX(-50%) scale(0.4);
  opacity: 0;
  animation: af-ripple 3.6s var(--af-ease-out) infinite;
}
.af-empty__ring--2 { animation-delay: 1.8s; }
@keyframes af-ripple {
  0% { transform: translateX(-50%) scale(0.4); opacity: 0.8; }
  100% { transform: translateX(-50%) scale(1.15); opacity: 0; }
}
@keyframes af-empty-bob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
</style>
