<!--
  Feature C accuracy check (owner reports). Backtest: for each household, predict every next
  order from the earlier orders only, then compare with the real date.
  Error = real date - predicted date (positive: they ordered later than predicted).
-->
<script setup>
import { computed, onMounted, ref } from 'vue'

import AppButton from '@/components/ui/AppButton.vue'
import BarChart from '@/components/viz/BarChart.vue'
import KpiTile from '@/components/dash/KpiTile.vue'
import SectionHead from '@/components/dash/SectionHead.vue'
import SegmentedControl from '@/components/form/SegmentedControl.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import { getRefillAccuracy } from '@/services/refillService'

const range = ref('90')
const data = ref(null)
const loading = ref(true)
const error = ref(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    data.value = await getRefillAccuracy(Number(range.value))
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
onMounted(load)
defineExpose({ load })
function setRange(v) {
  range.value = v
  load()
}

const pct = (x) => (x == null ? '–' : `${Math.round(x * 100)}%`)
const days = (x) => (x == null ? '–' : `${x.toFixed(1)}`)
const bias = computed(() => {
  const m = data.value?.mean_error
  if (m == null) return ''
  if (Math.abs(m) < 0.5) return 'No lean either way'
  return m > 0 ? `Orders come ${m.toFixed(1)} days later than predicted on average` : `Orders come ${Math.abs(m).toFixed(1)} days earlier than predicted on average`
})
const bars = computed(() =>
  (data.value?.histogram ?? []).map((b) => ({
    label: b.error_days === -7 ? '≤-7' : b.error_days === 7 ? '≥7' : b.error_days > 0 ? `+${b.error_days}` : String(b.error_days),
    sub: b.error_days === 0 ? 'Exactly on the predicted day' : `${Math.abs(b.error_days)} day${Math.abs(b.error_days) === 1 ? '' : 's'} ${b.error_days > 0 ? 'later' : 'earlier'}`,
    value: b.count,
  })),
)
const hardest = computed(() => (data.value?.per_household ?? []).slice(0, 5))
const reminders = computed(() => data.value?.reminders ?? null)
</script>

<template>
  <section class="af-panel acc" aria-labelledby="acc-title">
    <div class="acc__top">
      <SectionHead title="Refill prediction accuracy" :sub="data ? `${data.predictions} predictions checked across ${data.households} households` : ''" />
      <SegmentedControl class="no-print" :model-value="range" :options="[{ value: '30', label: '30 days' }, { value: '90', label: '90 days' }, { value: '0', label: 'All time' }]" label="Accuracy period" @update:model-value="setRange" />
    </div>

    <SkeletonList v-if="loading" :rows="3" :avatar="false" />
    <div v-else-if="error" class="err" role="alert">
      <p>Couldn't load the accuracy check: {{ error.message }}</p>
      <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
    </div>
    <p v-else-if="data && !data.predictions" class="af-small">
      Nothing to check yet. A household needs {{ data.min_orders + 1 }} delivered orders before one of its predictions can be compared with what really happened.
    </p>

    <template v-else-if="data">
      <div class="kpis">
        <KpiTile label="Average error" :value="days(data.mean_abs_error)" unit="days" :hint="bias" />
        <KpiTile label="Within ±1 day" :value="pct(data.within_1_day)" tone="pearl" hint="Share of predictions this close" />
        <KpiTile
          v-if="reminders"
          label="Reorders from reminders"
          :value="pct(reminders.reorder_rate)"
          tone="sun"
          :hint="reminders.reminded ? `${reminders.reordered} of ${reminders.reminded} reminded households` : 'No reminders sent in this period'"
        />
      </div>

      <div class="af-bento af-bento--stretch">
        <div class="b-7">
          <BarChart :bars="bars" title="How far off the predictions were (days)" :highlight="7" :height="190" />
          <p class="af-small">Days between the predicted and the real order. Bars right of 0: the household ordered later than predicted.</p>
        </div>
        <div class="b-5">
          <h3 class="h3">Hardest to predict</h3>
          <ul class="hard">
            <li v-for="h in hardest" :key="`${h.customer_id ?? h.key}-${h.address_id ?? ''}`">
              <span><b>{{ h.customer }}</b> {{ h.address }}</span>
              <span>{{ days(h.mean_abs_error) }} d off · {{ pct(h.within_1_day) }} close</span>
            </li>
          </ul>
        </div>
      </div>
      <p class="af-small">This is a statistical estimate, not trained AI: households that buy irregularly are predicted less accurately, and this check shows that as it is.</p>
    </template>
  </section>
</template>

<style scoped>
.acc { display: grid; gap: 14px; }
.acc p { margin: 0; }
.acc__top { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }
.h3 { margin: 0 0 8px; font-size: 14px; font-weight: 800; }
.hard { margin: 0; padding: 0; list-style: none; display: grid; gap: 8px; font-size: 13.5px; }
.hard li { display: grid; gap: 2px; padding: 8px 10px; border-radius: 12px; background: var(--af-surface-2); }
.hard li span:last-child { color: var(--af-ink-2); font-weight: 650; font-variant-numeric: tabular-nums; }
.err { display: grid; gap: 8px; justify-items: start; color: var(--af-ink-2); }
</style>
