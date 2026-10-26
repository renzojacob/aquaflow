<!--
  OrderTimeline — the story of one order, top to bottom.
  Done steps fill with water. The current step glows. Future steps are grey.
  Failed attempts, rejections and cancellations show in red with their reason.
-->
<script setup>
import { computed } from 'vue'
import { IonIcon } from '@ionic/vue'
import { alertCircleOutline, checkmarkOutline, closeOutline } from 'ionicons/icons'

import { ORDER_FLOW, ORDER_STATUS, isActive } from '@/constants/orderStatus'
import { dateTimeOf } from '@/utils/format'

const props = defineProps({
  order: { type: Object, required: true },
  staff: { type: Boolean, default: false }, // staff view: shows who did each step, hides the delivery code
})

const BAD = ['rejected', 'cancelled', 'failed_delivery']

const steps = computed(() => {
  const o = props.order
  const active = isActive(o)

  // 1) What already happened
  const done = o.history.map((h, i) => ({
    key: `h${i}`,
    title: ORDER_STATUS[h.status]?.timeline ?? h.status,
    detail: [dateTimeOf(h.at), props.staff && h.by ? `by ${h.by}` : '', h.note].filter(Boolean).join(' · '),
    state: BAD.includes(h.status) ? 'bad' : 'done',
  }))
  if (active && done.length) {
    const last = done[done.length - 1]
    if (last.state === 'done') last.state = 'now'
  }

  // 2) What is still to come (only for active orders)
  let future = []
  if (active) {
    const from = o.status === 'failed_delivery' ? ORDER_FLOW.indexOf('preparing') : ORDER_FLOW.indexOf(o.status)
    future = ORDER_FLOW.slice(from + 1).map((s) => ({
      key: `f${s}`,
      title: ORDER_STATUS[s].timeline,
      detail: s === 'delivered' && !props.staff ? `Give code ${o.delivery_code} to the rider` : '',
      state: 'todo',
    }))
  }
  return [...done, ...future]
})
</script>

<template>
  <ol class="af-tl">
    <li v-for="s in steps" :key="s.key" :class="`af-tl--${s.state}`">
      <span class="af-tl__dot" aria-hidden="true">
        <ion-icon v-if="s.state === 'done'" :icon="checkmarkOutline" />
        <ion-icon v-else-if="s.state === 'bad'" :icon="s.title.includes('failed') ? alertCircleOutline : closeOutline" />
      </span>
      <div class="af-tl__text">
        <b>{{ s.title }}</b>
        <span v-if="s.detail">{{ s.detail }}</span>
        <span v-if="s.state === 'now'" class="af-sr-only">(current step)</span>
      </div>
    </li>
  </ol>
</template>

<style scoped>
.af-tl { list-style: none; margin: 0; padding: 0; display: grid; }
.af-tl li { display: grid; grid-template-columns: 28px 1fr; gap: var(--af-s3); position: relative; padding-bottom: var(--af-s5); }
.af-tl li:last-child { padding-bottom: 0; }
.af-tl li::before {
  content: '';
  position: absolute;
  left: 13px;
  top: 30px;
  bottom: 2px;
  width: 2px;
  border-radius: 2px;
  background: var(--af-line);
}
.af-tl li:last-child::before { display: none; }
.af-tl--done::before { background: var(--af-water) !important; }

.af-tl__dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 15px;
  background: var(--af-surface-2);
  color: var(--af-ink-2);
  border: 2px solid var(--af-line);
  z-index: 1;
}
.af-tl--done .af-tl__dot { background: var(--af-water); border-color: var(--af-water); color: #fff; }
.af-tl--now .af-tl__dot { background: var(--af-primary); border-color: var(--af-primary); box-shadow: 0 0 0 5px var(--af-primary-tint); }
.af-tl--now .af-tl__dot::after { content: ''; width: 8px; height: 8px; border-radius: 50%; background: var(--af-on-primary); }
.af-tl--bad .af-tl__dot { background: var(--af-danger-tint); border-color: var(--af-danger); color: var(--af-danger); }

.af-tl__text { display: grid; gap: 2px; padding-top: 3px; min-width: 0; }
.af-tl__text b { font-size: 15px; }
.af-tl__text span { font-size: 13px; color: var(--af-ink-2); font-variant-numeric: tabular-nums; }
.af-tl--todo b { color: var(--af-ink-2); font-weight: 600; }
.af-tl--bad b { color: var(--af-danger); }
</style>
