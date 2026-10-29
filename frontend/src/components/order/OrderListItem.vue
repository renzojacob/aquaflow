<!-- One order row in a list. The whole card is a button. -->
<script setup>
import { IonIcon } from '@ionic/vue'
import { chevronForward } from 'ionicons/icons'

import LiquidFill from '@/components/ui/LiquidFill.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { PERIODS, containers, friendlyDay, peso } from '@/utils/format'

defineProps({
  order: { type: Object, required: true },
})
defineEmits(['open'])
</script>

<template>
  <button type="button" class="af-oi af-spot" @click="$emit('open', order)">
    <LiquidFill class="af-oi__qty" shape="orb" :size="52" :level="Math.min(order.quantity / 10, 1)" :text="order.quantity" />
    <span class="af-oi__main">
      <span class="af-oi__top">
        <b>{{ order.code }}</b>
        <StatusPill :status="order.status" />
      </span>
      <span class="af-oi__meta">
        {{ containers(order.quantity) }} · {{ friendlyDay(order.delivery_date) }}, {{ PERIODS[order.period].label }}
      </span>
      <span class="af-oi__meta">{{ order.address.label }} · {{ order.address.barangay }}</span>
    </span>
    <span class="af-oi__end">
      <span class="af-oi__total">{{ peso(order.total) }}</span>
      <ion-icon :icon="chevronForward" aria-hidden="true" />
    </span>
  </button>
</template>

<style scoped>
.af-oi {
  width: 100%;
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr) auto;
  gap: var(--af-s4);
  align-items: center;
  text-align: left;
  padding: var(--af-s4);
  background: var(--af-surface);
  border: 1px solid var(--af-line);
  border-radius: var(--af-r-md);
  box-shadow: inset 0 1px 0 var(--af-glass-edge), var(--af-shadow-1);
  backdrop-filter: var(--af-glass-blur);
  -webkit-backdrop-filter: var(--af-glass-blur);
  color: var(--af-ink);
  font-family: var(--af-font);
  cursor: pointer;
  transition: box-shadow var(--af-dur) var(--af-ease), border-color var(--af-dur) var(--af-ease), transform var(--af-dur-1) var(--af-ease);
}
.af-oi:hover { box-shadow: var(--af-shadow-2); border-color: color-mix(in srgb, var(--af-primary) 40%, var(--af-line)); }
.af-oi:active { transform: scale(0.99); }
.af-oi__qty { filter: drop-shadow(0 0 10px color-mix(in srgb, var(--af-water) 30%, transparent)); }
.af-oi__main { display: grid; gap: 4px; min-width: 0; }
.af-oi__top { display: flex; align-items: center; gap: var(--af-s2); flex-wrap: wrap; }
.af-oi__top b { font-family: var(--af-mono); font-size: 13px; font-weight: 600; letter-spacing: 0.04em; }
.af-oi__meta { font-size: 13px; color: var(--af-ink-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.af-oi__end { display: flex; align-items: center; gap: 6px; color: var(--af-ink-2); }
.af-oi__total { font-family: var(--af-display); font-weight: 600; font-size: 16px; color: var(--af-ink); font-variant-numeric: tabular-nums; }
@media (max-width: 400px) {
  .af-oi__total { display: none; }
}
</style>
