<!-- One order row in a list. The whole card is a button. -->
<script setup>
import { IonIcon } from '@ionic/vue'
import { chevronForward } from 'ionicons/icons'

import StatusPill from '@/components/ui/StatusPill.vue'
import { PERIODS, containers, friendlyDay, peso } from '@/utils/format'

defineProps({
  order: { type: Object, required: true },
})
defineEmits(['open'])
</script>

<template>
  <button type="button" class="af-oi" @click="$emit('open', order)">
    <span class="af-oi__qty" aria-hidden="true">{{ order.quantity }}</span>
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
  grid-template-columns: 48px minmax(0, 1fr) auto;
  gap: var(--af-s3);
  align-items: center;
  text-align: left;
  padding: var(--af-s4);
  background: var(--af-surface);
  border: 1px solid var(--af-line);
  border-radius: var(--af-r-md);
  box-shadow: var(--af-shadow-1);
  color: var(--af-ink);
  font-family: var(--af-font);
  cursor: pointer;
  transition: box-shadow var(--af-dur) var(--af-ease), transform 120ms var(--af-ease);
}
.af-oi:hover { box-shadow: var(--af-shadow-2); }
.af-oi:active { transform: scale(0.99); }
.af-oi__qty {
  width: 48px;
  height: 48px;
  border-radius: var(--af-r-sm);
  background: var(--af-primary-tint);
  color: var(--af-primary);
  display: grid;
  place-items: center;
  font-size: 20px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.af-oi__main { display: grid; gap: 4px; min-width: 0; }
.af-oi__top { display: flex; align-items: center; gap: var(--af-s2); flex-wrap: wrap; }
.af-oi__top b { font-size: 15px; }
.af-oi__meta { font-size: 13px; color: var(--af-ink-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.af-oi__end { display: flex; align-items: center; gap: 6px; color: var(--af-ink-2); }
.af-oi__total { font-weight: 800; color: var(--af-ink); font-variant-numeric: tabular-nums; }
@media (max-width: 400px) {
  .af-oi__total { display: none; }
}
</style>
