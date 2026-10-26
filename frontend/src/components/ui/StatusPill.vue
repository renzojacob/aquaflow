<!--
  StatusPill — shows an order status with its color, icon AND word.
  Usage: <StatusPill status="out_for_delivery" />
-->
<script setup>
import { computed } from 'vue'
import { IonIcon } from '@ionic/vue'
import { ORDER_STATUS } from '@/constants/orderStatus'

const props = defineProps({
  status: { type: String, required: true }, // a key from ORDER_STATUS
})

const info = computed(
  () => ORDER_STATUS[props.status] ?? { label: props.status, tone: 'pending', icon: null },
)
</script>

<template>
  <span class="af-pill" :class="`af-pill--${info.tone}`">
    <span v-if="info.live" class="af-pill__live" aria-hidden="true"></span>
    <ion-icon v-else-if="info.icon" :icon="info.icon" aria-hidden="true" />
    {{ info.label }}
  </span>
</template>

<style scoped>
.af-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font: 700 13px/1 var(--af-font);
  padding: 7px 12px 7px 10px;
  border-radius: var(--af-r-pill);
  color: var(--c);
  background: var(--t);
  white-space: nowrap;
}
.af-pill ion-icon { font-size: 15px; flex: none; }

.af-pill__live { width: 8px; height: 8px; border-radius: 50%; background: var(--c); position: relative; flex: none; }
.af-pill__live::after {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 2px solid var(--c);
  opacity: 0;
  animation: af-ping 1.6s var(--af-ease) infinite;
}
@keyframes af-ping {
  0% { transform: scale(0.5); opacity: 0.8; }
  100% { transform: scale(1.6); opacity: 0; }
}

.af-pill--pending { --c: var(--af-st-pending); --t: var(--af-st-pending-t); }
.af-pill--confirmed { --c: var(--af-st-confirmed); --t: var(--af-st-confirmed-t); }
.af-pill--preparing { --c: var(--af-st-preparing); --t: var(--af-st-preparing-t); }
.af-pill--ready { --c: var(--af-st-ready); --t: var(--af-st-ready-t); }
.af-pill--out { --c: var(--af-st-out); --t: var(--af-st-out-t); }
.af-pill--delivered { --c: var(--af-st-delivered); --t: var(--af-st-delivered-t); }
.af-pill--rejected { --c: var(--af-st-rejected); --t: var(--af-st-rejected-t); }
.af-pill--cancelled { --c: var(--af-st-cancelled); --t: var(--af-st-cancelled-t); }
.af-pill--failed { --c: var(--af-st-failed); --t: var(--af-st-failed-t); }
</style>