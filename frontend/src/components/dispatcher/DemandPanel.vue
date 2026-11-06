<!--
  Feature C, station side: expected containers per day for the coming week.
  Expected = confirmed orders + predicted reorders from households with no order in progress
  (so nothing is counted twice). Predicted reorders are tentative: shown hatched, never planned.
  Prepare = how many more to fill so ready stock covers everything expected up to that day.
-->
<script setup>
import { computed, onMounted, ref } from 'vue'

import AppButton from '@/components/ui/AppButton.vue'
import SectionHead from '@/components/dash/SectionHead.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import { getDemand } from '@/services/refillService'
import { containers, friendlyDay } from '@/utils/format'

const props = defineProps({ days: { type: Number, default: 7 } })

const data = ref(null)
const loading = ref(true)
const error = ref(null)
const open = ref(null) // date whose households are listed

async function load() {
  loading.value = true
  error.value = null
  try {
    data.value = await getDemand(props.days)
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
onMounted(load)
defineExpose({ load })

const max = computed(() => Math.max(1, ...(data.value?.days ?? []).map((d) => d.expected + d.pending)))
const pct = (n) => `${(n / max.value) * 100}%`
const sub = computed(() => {
  const d = data.value
  if (!d) return ''
  if (!d.totals.expected) return 'Nothing expected yet'
  return d.prepare
    ? `Fill ${containers(d.prepare)} more to cover the week (${d.ready_stock} ready now)`
    : `${d.ready_stock} ready now covers everything expected`
})
</script>

<template>
  <section class="af-panel demand" aria-labelledby="demand-title">
    <SectionHead title="Coming demand" :sub="sub" />
    <SkeletonList v-if="loading" :rows="3" :avatar="false" />
    <div v-else-if="error" class="err" role="alert">
      <p>Couldn't load the forecast: {{ error.message }}</p>
      <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
    </div>
    <template v-else-if="data">
      <ul class="legend" aria-hidden="true">
        <li><i class="sw sw--conf" /> Confirmed</li>
        <li><i class="sw sw--pred" /> Likely reorders (tentative)</li>
        <li><i class="sw sw--pend" /> Waiting for confirmation</li>
      </ul>
      <ol class="rows">
        <li v-for="d in data.days" :key="d.date" class="row">
          <button
            type="button"
            class="row__btn"
            :disabled="!d.households.length"
            :aria-expanded="open === d.date"
            :aria-label="`${friendlyDay(d.date)}: ${d.confirmed} confirmed, ${d.predicted} likely, ${d.pending} waiting${d.prepare ? `, prepare ${d.prepare} more by then` : ''}`"
            @click="open = open === d.date ? null : d.date"
          >
            <span class="row__day">{{ friendlyDay(d.date) }}</span>
            <span class="row__bar" aria-hidden="true">
              <i class="seg seg--conf" :style="{ width: pct(d.confirmed) }" />
              <i class="seg seg--pred" :style="{ width: pct(d.predicted) }" />
              <i class="seg seg--pend" :style="{ width: pct(d.pending) }" />
            </span>
            <span class="row__n">
              <b>{{ d.expected }}</b>
              <span v-if="d.predicted">{{ d.confirmed }} + {{ d.predicted }} likely</span>
            </span>
            <span class="row__prep" :class="{ 'is-short': d.prepare }">{{ d.prepare ? `prepare ${d.prepare}` : 'covered' }}</span>
          </button>
          <ul v-if="open === d.date" class="hh">
            <li v-for="h in d.households" :key="h.prediction_id">
              <b>{{ h.customer }}</b>
              <span>{{ h.address }}<template v-if="h.barangay">, {{ h.barangay }}</template></span>
              <span>{{ containers(h.containers) }}<template v-if="h.overdue_days"> · ran out {{ h.overdue_days }}d ago</template></span>
            </li>
          </ul>
        </li>
      </ol>
      <p class="af-small">Likely reorders come from each household's refill prediction and only count when it has no order in progress. They are estimates: confirm stock against real orders.</p>
    </template>
  </section>
</template>

<style scoped>
.demand { display: grid; gap: 12px; }
.demand p { margin: 0; }
.legend { display: flex; flex-wrap: wrap; gap: 14px; margin: 0; padding: 0; list-style: none; font-size: 12.5px; font-weight: 700; color: var(--af-ink-2); }
.legend li { display: inline-flex; align-items: center; gap: 6px; }
.sw { width: 14px; height: 10px; border-radius: 3px; display: inline-block; }
.sw--conf, .seg--conf { background: var(--af-water-deep); }
.sw--pred, .seg--pred { background: repeating-linear-gradient(135deg, var(--af-water) 0 4px, transparent 4px 7px); box-shadow: inset 0 0 0 1px var(--af-water); }
.sw--pend, .seg--pend { background: var(--af-surface-3); }

.rows { margin: 0; padding: 0; list-style: none; display: grid; gap: 4px; }
.row__btn {
  width: 100%;
  display: grid;
  grid-template-columns: 92px 1fr auto auto;
  align-items: center;
  gap: 12px;
  padding: 8px 10px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: var(--af-ink);
  font: 650 14px var(--af-font);
  text-align: left;
  cursor: pointer;
}
.row__btn:disabled { cursor: default; }
.row__btn:not(:disabled):hover { background: var(--af-surface-2); }
.row__day { font-weight: 750; }
.row__bar { display: flex; height: 14px; border-radius: 7px; background: var(--af-surface-2); overflow: hidden; }
.seg { display: block; height: 100%; }
.row__n { display: grid; justify-items: end; line-height: 1.2; font-variant-numeric: tabular-nums; }
.row__n b { font-size: 16px; }
.row__n span { font-size: 11.5px; color: var(--af-ink-2); }
.row__prep { min-width: 82px; text-align: right; font-size: 12.5px; font-weight: 750; color: var(--af-success); }
.row__prep.is-short { color: var(--af-amber-fg); }

.hh { margin: 2px 0 8px 104px; padding: 8px 12px; list-style: none; display: grid; gap: 6px; border-radius: 12px; background: var(--af-surface-2); font-size: 13px; }
.hh li { display: grid; grid-template-columns: 1fr auto; gap: 2px 10px; }
.hh li span:nth-child(2) { color: var(--af-ink-2); grid-column: 1; }
.hh li span:last-child { grid-row: 1 / span 2; grid-column: 2; align-self: center; font-weight: 700; }

.err { display: grid; gap: 8px; justify-items: start; color: var(--af-ink-2); }

@media (max-width: 560px) {
  .row__btn { grid-template-columns: 70px 1fr auto; gap: 8px; }
  .row__prep { grid-column: 2 / span 2; text-align: left; min-width: 0; }
  .hh { margin-left: 0; }
}
</style>
