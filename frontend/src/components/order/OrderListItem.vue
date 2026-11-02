<!--
  One order row in a list. The row opens the order; "Order again" (delivered orders) is its own button.
-->
<script setup>
import { computed } from 'vue'
import { IonIcon } from '@ionic/vue'
import { chevronForward, refreshOutline } from 'ionicons/icons'

import LiquidFill from '@/components/ui/LiquidFill.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { ORDER_FLOW } from '@/constants/orderStatus'
import { PERIODS, containers, friendlyDay, peso } from '@/utils/format'

const props = defineProps({
  order: { type: Object, required: true },
  canReorder: { type: Boolean, default: false },
})
defineEmits(['open', 'again'])

// The orb fills with the order's progress; finished orders are full, stopped ones nearly empty
const level = computed(() => {
  const s = props.order.status
  if (s === 'delivered') return 0.92
  if (['cancelled', 'rejected'].includes(s)) return 0.08
  return (Math.max(0, ORDER_FLOW.indexOf(s === 'failed_delivery' ? 'ready_for_pickup' : s)) + 1) / ORDER_FLOW.length
})
const tone = computed(() => (['cancelled', 'rejected'].includes(props.order.status) ? 'danger' : props.order.status === 'failed_delivery' ? 'warn' : 'water'))
</script>

<template>
  <div class="oi" :class="{ 'oi--muted': ['cancelled', 'rejected'].includes(order.status) }">
    <button type="button" class="oi__main" @click="$emit('open', order)">
      <LiquidFill class="oi__orb" shape="orb" :size="52" :level="level" :tone="tone" :text="order.quantity" :still="!['out_for_delivery'].includes(order.status)" />
      <span class="oi__text">
        <span class="oi__top">
          <b>{{ order.code }}</b>
          <StatusPill :status="order.status" />
        </span>
        <span class="oi__meta">{{ friendlyDay(order.delivery_date) }}, {{ PERIODS[order.period].label.toLowerCase() }} to {{ order.address.label }}</span>
        <span class="oi__meta">{{ containers(order.quantity) }}<template v-if="order.address.barangay">, {{ order.address.barangay }}</template></span>
      </span>
      <span class="oi__end">
        <span class="oi__total" :class="{ 'af-money': order.status === 'delivered' }">{{ peso(order.total) }}</span>
        <ion-icon :icon="chevronForward" aria-hidden="true" />
      </span>
    </button>
    <button v-if="canReorder" type="button" class="oi__again" :aria-label="`Order ${containers(order.quantity)} again, like ${order.code}`" @click="$emit('again', order)">
      <ion-icon :icon="refreshOutline" aria-hidden="true" /> Order again
    </button>
  </div>
</template>

<style scoped>
.oi {
  display: grid;
  border-radius: 20px;
  background: var(--af-surface);
  border: 1px solid var(--af-line);
  box-shadow: inset 0 1px 0 var(--af-glass-edge);
  backdrop-filter: var(--af-glass-blur);
  -webkit-backdrop-filter: var(--af-glass-blur);
  overflow: hidden;
}
.oi--muted .oi__orb { opacity: 0.6; }
.oi__main {
  width: 100%;
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr) auto;
  gap: 14px;
  align-items: center;
  padding: 14px 16px;
  border: 0;
  background: transparent;
  color: var(--af-ink);
  font-family: var(--af-font);
  text-align: left;
  cursor: pointer;
}
.oi__main:hover { background: var(--af-surface-2); }
.oi__orb { filter: drop-shadow(0 0 10px color-mix(in srgb, var(--af-water) 25%, transparent)); }
.oi__text { display: grid; gap: 4px; min-width: 0; }
.oi__top { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.oi__top b { font-size: 14.5px; font-weight: 800; font-variant-numeric: tabular-nums; }
.oi__meta { font-size: 13.5px; color: var(--af-ink-2); font-weight: 550; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.oi__end { display: flex; align-items: center; gap: 6px; color: var(--af-ink-2); }
.oi__total { font-family: var(--af-display); font-weight: 650; font-size: 17px; color: var(--af-ink); font-variant-numeric: tabular-nums; }
.oi__total.af-money { color: var(--af-sun); }
.oi__again {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 44px;
  border: 0;
  border-top: 1px solid var(--af-line);
  background: var(--af-surface-2);
  color: var(--af-primary);
  font: 750 14px var(--af-font);
  cursor: pointer;
}
.oi__again:hover { background: var(--af-primary-tint); }
@media (max-width: 400px) {
  .oi__total { font-size: 15px; }
  .oi__end ion-icon { display: none; }
}
</style>
