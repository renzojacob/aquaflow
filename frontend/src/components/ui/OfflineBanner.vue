<!--
  OfflineBanner — tells the rider whether actions are saved locally or synced.
  Phase 5 connects it to the real network status + outbox. For now it is driven by props.
  Usage:
    <OfflineBanner state="offline" :pending="3" />
    <OfflineBanner state="syncing" :done="1" :total="3" />
    <OfflineBanner state="synced" :total="3" />
-->
<script setup>
import { computed } from 'vue'
import { IonIcon } from '@ionic/vue'
import { cloudDoneOutline, cloudOfflineOutline } from 'ionicons/icons'

const props = defineProps({
  state: { type: String, required: true }, // offline | syncing | synced
  pending: { type: Number, default: 0 },
  done: { type: Number, default: 0 },
  total: { type: Number, default: 0 },
})

const text = computed(() => {
  if (props.state === 'offline') return "You're offline. Deliveries are saved on this phone."
  if (props.state === 'syncing') return 'Back online · syncing your actions…'
  return props.total === 1 ? 'Your action is synced' : `All ${props.total} actions synced`
})

const count = computed(() => {
  if (props.state === 'offline' && props.pending > 0) {
    return `${props.pending} waiting to sync`
  }
  if (props.state === 'syncing') return `${props.done} of ${props.total}`
  return ''
})
</script>

<template>
  <div class="af-banner" :class="`af-banner--${state}`" role="status">
    <ion-icon v-if="state === 'offline'" :icon="cloudOfflineOutline" aria-hidden="true" />
    <span v-else-if="state === 'syncing'" class="af-banner__spin" aria-hidden="true"></span>
    <ion-icon v-else :icon="cloudDoneOutline" aria-hidden="true" />
    <span class="af-banner__text">{{ text }}</span>
    <span v-if="count" class="af-banner__count">{{ count }}</span>
  </div>
</template>

<style scoped>
.af-banner {
  display: flex;
  align-items: center;
  gap: var(--af-s3);
  padding: 12px 16px;
  border-radius: var(--af-r-sm);
  font-size: 14px;
  font-weight: 650;
  flex-wrap: wrap;
  border: 1px solid color-mix(in srgb, currentColor 28%, transparent);
}
.af-banner ion-icon { font-size: 20px; flex: none; }
.af-banner--offline { background: var(--af-amber-tint); color: var(--af-amber-fg); }
.af-banner--syncing { background: var(--af-primary-tint); color: var(--af-primary); }
.af-banner--synced { background: var(--af-success-tint); color: var(--af-success); }
.af-banner__text { flex: 1; min-width: 160px; }
.af-banner__count {
  font-family: var(--af-mono);
  font-variant-numeric: tabular-nums;
  background: color-mix(in srgb, currentColor 14%, transparent);
  padding: 4px 10px;
  border-radius: var(--af-r-pill);
  font-size: 12px;
}
.af-banner__spin {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid currentColor;
  border-right-color: transparent;
  animation: af-rot 0.8s linear infinite;
  flex: none;
}
@keyframes af-rot { to { transform: rotate(360deg); } }
</style>
