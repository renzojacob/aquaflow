<!--
  Feature C, "Never Run Out": when this household is expected to run out of water,
  and a one-tap reorder of the usual quantity. Also shown when the customer opens the
  reorder link from the reminder email (`highlight`).
-->
<script setup>
import { computed, ref } from 'vue'
import { IonIcon } from '@ionic/vue'
import { alarmOutline, notificationsOffOutline, waterOutline } from 'ionicons/icons'

import AppButton from '@/components/ui/AppButton.vue'
import RingGauge from '@/components/viz/RingGauge.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { PERIODS, containers, friendlyDay, peso } from '@/utils/format'

const props = defineProps({
  card: { type: Object, required: true }, // RefillCard from refillService
  others: { type: Array, default: () => [] }, // the customer's other households, shown as one line each
  highlight: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
})
const emit = defineEmits(['reorder', 'customize', 'track', 'settings'])

const c = computed(() => props.card)
const ok = computed(() => c.value.state === 'ok')
const showDetails = ref(false)

// How full the household's water is: days left out of the days the last delivery should last
const lasts = computed(() => (ok.value ? Math.max(1, Math.round(c.value.last_quantity * c.value.days_per_container)) : 1))
const level = computed(() => (ok.value ? Math.max(0, c.value.days_left) / lasts.value : 0))
const urgent = computed(() => ok.value && c.value.days_left <= 2)

const when = computed(() => {
  const d = c.value.days_left
  if (d < 0) return `Probably ran out ${friendlyDay(c.value.predicted_runout_date).toLowerCase()}`
  if (d === 0) return 'Likely to run out today'
  if (d === 1) return 'Likely to run out tomorrow'
  return `Likely to run out ${friendlyDay(c.value.predicted_runout_date)}`
})
const rate = computed(() => {
  const dpc = c.value.days_per_container
  if (!dpc) return ''
  if (dpc >= 1) return `You use about one container every ${dpc % 1 ? dpc.toFixed(1) : dpc} day${dpc === 1 ? '' : 's'}.`
  return `You use about ${(1 / dpc).toFixed(1)} containers a day.`
})
const reminderLine = computed(() => {
  if (!c.value.reminders_enabled) return ''
  if (c.value.reminder_sent_at) return 'We sent you a reminder.'
  if (c.value.days_left > 2) return `We'll remind you ${friendlyDay(c.value.remind_on).toLowerCase() === 'tomorrow' ? 'tomorrow' : `on ${friendlyDay(c.value.remind_on)}`}.`
  return ''
})
const slot = computed(() => {
  const r = c.value.reorder
  if (!r) return ''
  return `${friendlyDay(r.delivery_date)} ${PERIODS[r.period]?.label.toLowerCase() ?? r.period}`
})
const fmt = (iso) => friendlyDay(iso)
</script>

<template>
  <section class="af-panel refill" :class="{ 'refill--hl': highlight, 'refill--urgent': urgent && !c.open_order }" aria-labelledby="refill-title">
    <div class="head">
      <h2 id="refill-title" class="title"><ion-icon :icon="waterOutline" aria-hidden="true" /> Never run out</h2>
      <span v-if="highlight" class="chip">From your reminder</span>
      <span v-else-if="ok" class="addr">{{ c.address.label }}</span>
    </div>

    <!-- Not enough history yet -->
    <div v-if="!ok" class="early">
      <ol class="dots" :aria-label="`${c.orders_counted} of ${c.orders_needed} deliveries`">
        <li v-for="i in c.orders_needed" :key="i" :class="{ on: i <= c.orders_counted }" />
      </ol>
      <p><b>Not enough history yet.</b> After {{ c.orders_needed }} deliveries to {{ c.address.label }} we can tell you when you're likely to run out, and remind you before you do.</p>
    </div>

    <!-- Prediction -->
    <template v-else>
      <div class="main">
        <RingGauge :value="level" :size="104" :tone="urgent ? 'warn' : 'water'" :label="`About ${Math.max(0, c.days_left)} of ${lasts} days of water left`">
          <b class="ring__n">{{ Math.max(0, c.days_left) }}</b>
          <span class="ring__u">{{ c.days_left === 1 ? 'day left' : 'days left' }}</span>
        </RingGauge>
        <div class="text">
          <p class="when">{{ when }}</p>
          <p class="af-small">{{ rate }} {{ reminderLine }}</p>
          <button v-if="!c.reminders_enabled" type="button" class="off" @click="emit('settings')">
            <ion-icon :icon="notificationsOffOutline" aria-hidden="true" /> Reminders are off. Turn on
          </button>
        </div>
      </div>

      <div v-if="c.open_order" class="open">
        <span class="open__text">Your next order is already coming {{ fmt(c.open_order.delivery_date).toLowerCase() }}.</span>
        <StatusPill :status="c.open_order.status" />
        <AppButton variant="secondary" size="sm" @click="emit('track', c.open_order.id)">Track</AppButton>
      </div>
      <div v-else class="actions">
        <AppButton :size="highlight || urgent ? 'lg' : 'md'" :loading="busy" @click="emit('reorder', c)">
          <ion-icon v-if="urgent" :icon="alarmOutline" aria-hidden="true" />
          Reorder {{ containers(c.reorder.quantity) }}<template v-if="c.reorder.total != null"> · {{ peso(c.reorder.total) }}</template>
        </AppButton>
        <span class="af-small slot">Arrives {{ slot.toLowerCase() }}, {{ PERIODS[c.reorder.period]?.hours }}</span>
        <AppButton variant="ghost" size="sm" @click="emit('customize', c)">Change</AppButton>
      </div>

      <button type="button" class="how" :aria-expanded="showDetails" @click="showDetails = !showDetails">
        {{ showDetails ? 'Hide' : 'How we worked this out' }}
      </button>
      <div v-if="showDetails" class="details">
        <p class="af-small">From your last deliveries: days until the next order, divided by the containers delivered. The most recent counts most (weights {{ c.inputs?.weights?.join(', ') }}).</p>
        <ul>
          <li v-for="i in c.inputs?.intervals ?? []" :key="i.from">
            <span>{{ fmt(i.from) }} → {{ fmt(i.to) }}</span>
            <span>{{ i.days }} days ÷ {{ i.containers }}</span>
            <b>{{ i.days_per_container }} d</b>
          </li>
        </ul>
        <p class="af-small">Last delivery {{ fmt(c.last_delivery_date) }}: {{ containers(c.last_quantity) }} × {{ c.days_per_container }} days. It's an estimate: if your use changes, it catches up after the next delivery.</p>
      </div>
    </template>

    <ul v-if="others.length" class="others">
      <li v-for="o in others" :key="o.address.id">
        <b>{{ o.address.label }}</b>
        <span v-if="o.state !== 'ok'">{{ o.orders_counted }} of {{ o.orders_needed }} deliveries so far</span>
        <span v-else-if="o.open_order">Order on the way</span>
        <span v-else>{{ o.days_left < 0 ? 'Probably out' : `Runs out ${fmt(o.predicted_runout_date)}` }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.refill { display: grid; gap: 14px; transition: box-shadow 0.3s ease; }
.refill--hl { box-shadow: 0 0 0 2px var(--af-primary), var(--af-shadow-2); }
.refill--urgent { box-shadow: inset 0 0 0 1px var(--af-amber); }
.head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.title { margin: 0; display: inline-flex; align-items: center; gap: 8px; font-size: 17px; font-weight: 800; color: var(--af-ink); }
.title ion-icon { color: var(--af-water-deep); }
.chip { padding: 5px 10px; border-radius: var(--af-r-pill, 999px); background: var(--af-primary-tint); color: var(--af-primary); font-size: 12.5px; font-weight: 800; }
.addr { font-size: 13px; font-weight: 700; color: var(--af-ink-2); }

.main { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; }
.ring__n { font-family: var(--af-display); font-size: 30px; font-weight: 700; letter-spacing: -0.04em; line-height: 1; }
.ring__u { font-size: 11.5px; font-weight: 700; color: var(--af-ink-2); }
.text { flex: 1; min-width: 180px; display: grid; gap: 6px; }
.when { margin: 0; font-family: var(--af-display); font-size: clamp(19px, 2.4vw, 24px); font-weight: 650; letter-spacing: -0.03em; line-height: 1.15; }
.text .af-small { margin: 0; }
.off { justify-self: start; display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border: 0; border-radius: 10px; background: var(--af-amber-tint); color: var(--af-amber-fg); font: 750 13px var(--af-font); cursor: pointer; }

.actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.slot { margin: 0; }
.open { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 10px 12px; border-radius: 14px; background: var(--af-surface-2); font-size: 14px; font-weight: 650; }
.open__text { flex: 1; min-width: 160px; }

.early { display: grid; gap: 10px; }
.early p { margin: 0; font-size: 14.5px; line-height: 1.5; color: var(--af-ink-2); }
.early b { color: var(--af-ink); }
.dots { display: flex; gap: 6px; margin: 0; padding: 0; list-style: none; }
.dots li { width: 28px; height: 8px; border-radius: 4px; background: var(--af-surface-3); }
.dots li.on { background: var(--af-water); }

.how { justify-self: start; padding: 0; border: 0; background: none; color: var(--af-primary); font: 750 13.5px var(--af-font); cursor: pointer; text-decoration: underline; text-underline-offset: 3px; }
.details { display: grid; gap: 8px; padding: 12px; border-radius: 14px; background: var(--af-surface-2); }
.details p { margin: 0; }
.details ul { margin: 0; padding: 0; list-style: none; display: grid; gap: 4px; font-size: 13.5px; font-variant-numeric: tabular-nums; }
.details li { display: grid; grid-template-columns: 1fr auto auto; gap: 12px; }
.details li span:nth-child(2) { color: var(--af-ink-2); }

.others { margin: 0; padding: 10px 0 0; list-style: none; display: grid; gap: 6px; border-top: 1px solid var(--af-line); font-size: 13.5px; }
.others li { display: flex; justify-content: space-between; gap: 10px; }
.others span { color: var(--af-ink-2); font-weight: 600; }

@media (max-width: 560px) {
  .actions > :deep(.af-btn:first-child) { flex: 1 1 100%; }
}
</style>
