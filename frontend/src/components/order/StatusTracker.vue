<!--
  StatusTracker — horizontal "Foodpanda-style" order tracker:
  a row of icon dots joined by a line that fills as the order moves along.
  Usage: <StatusTracker :order="order" />
-->
<script setup>
import { computed } from 'vue'
import { IonIcon } from '@ionic/vue'
import { ORDER_FLOW, ORDER_STATUS } from '@/constants/orderStatus'

const props = defineProps({
  order: { type: Object, required: true },
})

/** How far along the happy path the order is (0..5). A failed delivery still shows "ready" done. */
const stepIndex = computed(() =>
  Math.max(0, ORDER_FLOW.indexOf(props.order.status === 'failed_delivery' ? 'ready_for_pickup' : props.order.status)),
)

const steps = computed(() =>
  ORDER_FLOW.map((key, i) => ({
    key,
    ...ORDER_STATUS[key],
    done: i <= stepIndex.value,
  })),
)

const isEndState = computed(() => ['rejected', 'cancelled'].includes(props.order.status))
</script>

<template>
  <div class="af-tracker" role="img" :aria-label="`Step ${stepIndex + 1} of ${steps.length}: ${ORDER_STATUS[order.status]?.label ?? order.status}`">
    <ol class="af-tracker__row">
      <li
        v-for="(s, i) in steps"
        :key="s.key"
        class="af-tracker__step"
        :class="{ 'is-done': s.done, 'is-now': i === stepIndex }"
      >
        <span class="af-tracker__dot" :style="{ '--d': `${i * 90}ms` }">
          <ion-icon v-if="s.icon" :icon="s.icon" aria-hidden="true" />
          <span v-else class="af-tracker__pulse" aria-hidden="true"></span>
        </span>
        <span class="af-tracker__label">{{ s.label }}</span>
        <span v-if="i < steps.length - 1" class="af-tracker__line" :class="{ 'is-filled': i < stepIndex }" aria-hidden="true"></span>
      </li>
    </ol>
    <p v-if="isEndState" class="af-tracker__end" :class="{ 'is-danger': order.status === 'rejected' }">
      {{ order.status === 'rejected' ? 'This order was rejected.' : 'This order was cancelled.' }}
    </p>
  </div>
</template>

<style scoped>
.af-tracker { container-type: inline-size; }
.af-tracker__row {
  display: flex;
  align-items: flex-start;
  list-style: none;
  margin: 0;
  padding: 0;
  gap: 0;
}
.af-tracker__step {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1 1 0;
  min-width: 0;
  text-align: center;
}
.af-tracker__dot {
  position: relative;
  z-index: 1;
  width: 36px;
  height: 36px;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--af-surface-2);
  border: 2px solid var(--af-line-strong);
  color: var(--af-ink-2);
  font-size: 17px;
  transition: background var(--af-dur) var(--af-ease), border-color var(--af-dur) var(--af-ease), color var(--af-dur) var(--af-ease), box-shadow var(--af-dur) var(--af-ease);
}
.af-tracker__step.is-done .af-tracker__dot {
  background: linear-gradient(135deg, var(--af-brand-g1), var(--af-brand-g2) 60%, var(--af-brand-g3));
  border-color: transparent;
  color: var(--af-on-brand);
}
.af-tracker__step.is-now .af-tracker__dot { box-shadow: 0 0 0 5px color-mix(in srgb, var(--af-primary) 18%, transparent); }
.af-tracker__pulse { width: 10px; height: 10px; border-radius: 50%; background: currentColor; animation: af-track-pulse 1.4s ease-in-out infinite; }
.af-tracker__step.is-done .af-tracker__pulse { animation: none; }
@keyframes af-track-pulse { 0%, 100% { opacity: 0.5; transform: scale(0.85); } 50% { opacity: 1; transform: scale(1.1); } }

.af-tracker__label {
  margin-top: 8px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.3;
  color: var(--af-ink-2);
  max-width: 68px;
}
.af-tracker__step.is-done .af-tracker__label { color: var(--af-ink); }
.af-tracker__step.is-now .af-tracker__label { color: var(--af-primary); }

.af-tracker__line {
  position: absolute;
  top: 17px;
  left: calc(50% + 24px);
  right: calc(-50% + 24px);
  height: 2px;
  background: var(--af-line-strong);
  z-index: 0;
}
.af-tracker__line.is-filled { background: linear-gradient(90deg, var(--af-brand-g2), var(--af-brand-g3)); }

.af-tracker__end { margin: var(--af-s4) 0 0; font-size: 14px; font-weight: 650; color: var(--af-ink-2); text-align: center; }
.af-tracker__end.is-danger { color: var(--af-danger); }

/* Narrow (phone, or inside the tank): 6 labels don't fit side by side.
   Show only the current step's word; the others stay readable for screen readers. */
@container (max-width: 440px) {
  .af-tracker__dot { width: 30px; height: 30px; font-size: 14px; }
  .af-tracker__line { top: 14px; left: calc(50% + 19px); right: calc(-50% + 19px); }
  .af-tracker__step:not(.is-now) .af-tracker__label {
    position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
    overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0;
  }
  .af-tracker__step.is-now .af-tracker__label { max-width: none; white-space: nowrap; font-size: 12px; }
  .af-tracker__step:first-child.is-now .af-tracker__label { align-self: flex-start; }
  .af-tracker__step:last-child.is-now .af-tracker__label { align-self: flex-end; }
}
</style>
