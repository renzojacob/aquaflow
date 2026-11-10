<!--
  Forecasting: how many orders and containers to expect each day, for the owner and the dispatcher.
  Numbers come from GET /api/v1/dispatch/forecast. Three methods are tested on the shop's own
  history; the most accurate one makes the forecast. Nothing here is a promise: the shaded band is
  the range the day is likely (8 times in 10) to land in.
-->
<script setup>
import { computed, ref } from 'vue'
import { IonContent, IonHeader, IonIcon, IonPage, IonTitle, IonToolbar, onIonViewWillEnter, useIonRouter } from '@ionic/vue'
import { alertCircle, informationCircleOutline, warningOutline } from 'ionicons/icons'

import SectionHead from '@/components/dash/SectionHead.vue'
import SegmentedControl from '@/components/form/SegmentedControl.vue'
import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import ForecastChart from '@/components/viz/ForecastChart.vue'
import { getForecast } from '@/services/forecastService'
import { useAuthStore } from '@/stores/auth'
import { friendlyDay } from '@/utils/format'

const auth = useAuthStore()
const ionRouter = useIonRouter()

const days = ref('7')
const metric = ref('orders')
const data = ref(null)
const loading = ref(true)
const error = ref(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    data.value = await getForecast(Number(days.value))
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
onIonViewWillEnter(load)
function setDays(v) {
  days.value = v
  load()
}

const block = computed(() => data.value?.[metric.value] ?? null)
const history = computed(() => data.value?.history?.[metric.value] ?? [])
const unit = computed(() => (metric.value === 'orders' ? 'orders' : 'containers'))
const isEmpty = computed(() => !!data.value && (!data.value.orders.days.length || data.value.orders.history_days === 0))
const shortHistory = computed(() => !!data.value && !isEmpty.value && !data.value.enough_data)

// Fake or sample numbers must never pass for real results: they get their own loud banner.
const isDemo = (w) => /\b(DEMO|SAMPLE)\b/.test(w)
const demoWarnings = computed(() => (data.value?.warnings ?? []).filter(isDemo))
const otherWarnings = computed(() => (data.value?.warnings ?? []).filter((w) => !isDemo(w)))

const chosen = computed(() => block.value?.backtest?.find((r) => r.chosen) ?? null)
const offBy = computed(() => (chosen.value?.wape == null ? null : Math.round(chosen.value.wape * 100)))
const rows = computed(() => block.value?.backtest ?? [])

const METHOD_TEXT = {
  naive: 'Assumes tomorrow looks like the last day. A simple yardstick the others must beat.',
  weekday_average: 'Averages the same weekday over the last 4 weeks, so a normal Friday is judged against recent Fridays.',
  holt_winters: 'Follows the weekly pattern and also the overall direction, up or down. Best when business is clearly growing or shrinking.',
}
const pct = (v) => (v == null ? '–' : `${(v * 100).toFixed(1)}%`)
const num = (v) => (v == null ? '–' : v.toFixed(1))

// Preparation
const trips = computed(() => data.value?.trips ?? null)
const peak = computed(() => trips.value?.days?.find((d) => d.date === trips.value.peak_date) ?? null)
const overDays = computed(() => trips.value?.over_capacity_days ?? [])
const canAddVehicles = computed(() => auth.role === 'owner')
const goVehicles = () => ionRouter.push('/owner/vehicles')
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`

const chartTitle = computed(() => `${metric.value === 'orders' ? 'Orders' : 'Containers'} per day: last ${history.value.length} days and the next ${days.value}`)
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-title>Forecasting</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content>
      <div class="af-container af-dash fc">
        <header class="top">
          <div>
            <h1 class="title">Forecasting</h1>
            <p class="af-small">What to expect in the coming days, so you can plan riders, vehicles and supplies.</p>
          </div>
          <div class="tools">
            <SegmentedControl :model-value="metric" :options="[{ value: 'orders', label: 'Orders' }, { value: 'containers', label: 'Containers' }]" label="Show" @update:model-value="metric = $event" />
            <SegmentedControl :model-value="days" :options="[{ value: '7', label: '7 days' }, { value: '14', label: '14 days' }]" label="Forecast length" @update:model-value="setDays" />
          </div>
        </header>

        <!-- Loading -->
        <template v-if="loading">
          <div class="af-panel" aria-busy="true"><SkeletonList :rows="3" :avatar="false" /></div>
          <div class="af-panel" aria-busy="true"><div class="skel-chart" /><SkeletonList :rows="1" :avatar="false" /></div>
          <div class="pair"><div class="af-panel"><SkeletonList :rows="3" :avatar="false" /></div><div class="af-panel"><SkeletonList :rows="3" :avatar="false" /></div></div>
        </template>

        <!-- Error -->
        <div v-else-if="error" class="af-panel err" role="alert">
          <b>Couldn't load the forecast</b>
          <p>{{ error.message }}</p>
          <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>

        <!-- Nothing ordered yet -->
        <div v-else-if="isEmpty" class="af-panel">
          <EmptyState art="waves" title="Nothing to forecast yet" message="The forecast learns from past orders. Once customers have ordered for a few weeks, this page shows what to expect each day." />
        </div>

        <template v-else-if="data">
          <!-- DEMO / SAMPLE data: impossible to miss -->
          <div v-for="w in demoWarnings" :key="w" class="demo" role="alert">
            <ion-icon :icon="alertCircle" aria-hidden="true" />
            <div>
              <b>DEMO DATA. NOT REAL RESULTS.</b>
              <p>{{ w }}</p>
            </div>
          </div>

          <div v-if="otherWarnings.length" class="warn" role="status">
            <ion-icon :icon="warningOutline" aria-hidden="true" />
            <ul>
              <li v-for="w in otherWarnings" :key="w">{{ w }}</li>
            </ul>
          </div>

          <!-- Not enough history -->
          <div v-if="shortHistory" class="short" role="status">
            <ion-icon :icon="informationCircleOutline" aria-hidden="true" />
            <div>
              <b>Not enough history yet</b>
              <p>A tested forecast needs at least 28 days of orders. There {{ data.orders.history_days === 1 ? 'is' : 'are' }} {{ plural(data.orders.history_days, 'day') }} so far, so the dashed line is a rough weekday average with no likely range. It will sharpen as orders come in.</p>
            </div>
          </div>

          <!-- Plain-English summary -->
          <section class="af-panel summary" aria-labelledby="fc-summary">
            <p id="fc-summary" class="af-eyebrow">In plain words</p>
            <p class="summary__text">{{ data.explanation }}</p>
          </section>

          <!-- Chart -->
          <section class="af-panel" aria-labelledby="fc-chart">
            <SectionHead
              id="fc-chart"
              :title="metric === 'orders' ? 'Orders per day' : 'Containers per day'"
              :sub="`Last ${history.length} days, then the next ${days}`"
            />
            <ForecastChart
              :history="history"
              :forecast="block.days"
              :show-band="data.enough_data"
              :title="chartTitle"
              :unit="unit"
              :height="280"
              :band-label="`Likely range (${Math.round((block.interval_level ?? 0.8) * 100)}%)`"
            />
          </section>

          <div class="pair">
            <!-- How accurate -->
            <section class="af-panel" aria-labelledby="fc-method">
              <SectionHead id="fc-method" title="How reliable is it?" />
              <template v-if="data.enough_data && chosen">
                <p class="method__name">{{ block.method_label }}</p>
                <p class="method__big">
                  <template v-if="offBy !== null">Off by about <b>{{ offBy }}%</b></template>
                  <template v-else>Accuracy can't be measured yet</template>
                </p>
                <p class="af-small">
                  Tested on {{ plural(block.backtest_rounds, 'past week') }}: each week was forecast using only the days before it, then compared with what really happened. This method scored best.
                </p>
              </template>
              <p v-else class="af-small">There is no accuracy score yet. It needs at least 28 days of orders so past weeks can be forecast and checked.</p>
            </section>

            <!-- Preparation -->
            <section class="af-panel" aria-labelledby="fc-prep">
              <SectionHead id="fc-prep" title="Preparation" :sub="peak ? `Busiest day: ${friendlyDay(peak.date)}` : ''" />
              <template v-if="trips && peak">
                <div class="prep">
                  <div><b>{{ peak.trips_needed }}</b><span>{{ peak.trips_needed === 1 ? 'trip' : 'trips' }}</span></div>
                  <div><b>{{ peak.riders_needed }}</b><span>{{ peak.riders_needed === 1 ? 'rider' : 'riders' }}</span></div>
                  <div><b>{{ Math.round(peak.containers) }}</b><span>containers</span></div>
                </div>
                <p class="af-small" v-if="peak.busy_trips_needed > peak.trips_needed">
                  If it turns out busy: up to {{ plural(peak.busy_trips_needed, 'trip') }} and {{ plural(peak.busy_riders_needed, 'rider') }}.
                </p>
                <p v-if="overDays.length" class="flag" role="alert">
                  <ion-icon :icon="warningOutline" aria-hidden="true" />
                  <span>Your {{ plural(trips.vehicles, 'available vehicle') }} can make {{ trips.fleet_trips_per_day }} trips a day. That may not be enough on {{ overDays.map(friendlyDay).join(', ') }}.</span>
                </p>
                <p v-else class="ok">
                  <span>Your {{ plural(trips.vehicles, 'available vehicle') }} ({{ trips.fleet_trips_per_day }} trips a day) should cover every day shown.</span>
                </p>
                <p class="af-small note">{{ trips.note }}</p>
              </template>
              <template v-else>
                <p class="af-small">No vehicle is switched on, so trips can't be estimated.</p>
                <AppButton v-if="canAddVehicles" variant="secondary" size="sm" @click="goVehicles">Set up vehicles</AppButton>
              </template>
            </section>
          </div>

          <!-- Method comparison -->
          <section v-if="data.enough_data && rows.length" class="af-panel" aria-labelledby="fc-table">
            <SectionHead id="fc-table" title="The three methods compared" sub="Lower is better. Errors are in the same units as the chart." />
            <div class="tablewrap" tabindex="0" role="region" aria-label="Method comparison table, scrolls sideways on small screens">
              <table class="table">
                <thead>
                  <tr>
                    <th scope="col">Method</th>
                    <th scope="col"><abbr title="Mean absolute error: the typical miss, in orders or containers">MAE</abbr></th>
                    <th scope="col"><abbr title="Root mean squared error: like MAE but punishes big misses more">RMSE</abbr></th>
                    <th scope="col"><abbr title="Weighted absolute percentage error: total miss as a share of total volume">WAPE</abbr></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="r in rows" :key="r.method" :class="{ 'is-chosen': r.chosen }">
                    <th scope="row">
                      <span class="mname">{{ r.label }}<span v-if="r.chosen" class="badge">Used for the forecast</span></span>
                      <span class="mtext">{{ METHOD_TEXT[r.method] }}</span>
                    </th>
                    <td>{{ num(r.mae) }}</td>
                    <td>{{ num(r.rmse) }}</td>
                    <td>{{ pct(r.wape) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </template>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.top { display: flex; justify-content: space-between; align-items: flex-end; gap: 12px; flex-wrap: wrap; }
.top p { margin: 4px 0 0; }
.title { margin: 0; font-family: var(--af-display); font-size: clamp(26px, 3.4vw, 34px); font-weight: 650; letter-spacing: -0.04em; }
.tools { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }

.pair { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; }
@media (min-width: 992px) { .pair { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.af-panel > p { margin: 0; }

/* Banners */
.demo, .warn, .short {
  display: flex; gap: 14px; align-items: flex-start; padding: 16px 18px; border-radius: var(--af-r-md, 16px);
  border: 1px solid var(--af-line-strong); color: var(--af-ink);
}
.demo ion-icon, .warn ion-icon, .short ion-icon { flex: none; font-size: 26px; margin-top: 1px; }
.demo p, .short p { margin: 4px 0 0; color: var(--af-ink); font-size: 15px; }
.demo { background: var(--af-danger-tint); border: 2px solid var(--af-danger); }
.demo ion-icon { color: var(--af-danger); font-size: 32px; }
.demo b { display: block; color: var(--af-danger); font-family: var(--af-display); font-size: clamp(16px, 2.4vw, 20px); letter-spacing: 0.03em; }
.warn { background: var(--af-amber-tint); border-color: var(--af-amber-fg); }
.warn ion-icon { color: var(--af-amber-fg); }
.warn ul { margin: 0; padding: 0; list-style: none; display: grid; gap: 6px; font-size: 15px; }
.short { background: var(--af-brand-tint); border-color: var(--af-brand); }
.short ion-icon { color: var(--af-brand); }
.short b { font-weight: 750; }

/* Summary */
.summary { border: 1px solid var(--af-brand); background: color-mix(in srgb, var(--af-brand) 7%, var(--af-surface)); }
.summary .af-eyebrow { margin: 0 0 8px; }
.summary__text { margin: 0; font-family: var(--af-display); font-size: clamp(18px, 2.6vw, 24px); line-height: 1.35; font-weight: 550; letter-spacing: -0.02em; color: var(--af-ink); }

/* Method card */
.method__name { font-weight: 700; color: var(--af-ink-2); }
.method__big { font-family: var(--af-display); font-size: clamp(22px, 3vw, 30px); letter-spacing: -0.03em; margin: 2px 0 8px !important; }
.method__big b { color: var(--af-brand); }

/* Preparation */
.prep { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-bottom: 10px; }
.prep div { display: grid; justify-items: start; padding: 12px 14px; border-radius: 14px; background: var(--af-surface-2); border: 1px solid var(--af-line); }
.prep b { font-family: var(--af-display); font-size: clamp(24px, 3.4vw, 34px); line-height: 1.1; font-variant-numeric: tabular-nums; }
.prep span { font-size: 13px; font-weight: 650; color: var(--af-ink-2); }
.flag { display: flex; gap: 10px; align-items: flex-start; margin: 10px 0 0 !important; padding: 12px 14px; border-radius: 12px; background: var(--af-danger-tint); border: 1px solid var(--af-danger); color: var(--af-ink); font-weight: 650; font-size: 14.5px; }
.flag ion-icon { flex: none; font-size: 20px; color: var(--af-danger); margin-top: 1px; }
.ok { margin: 10px 0 0 !important; font-size: 14.5px; font-weight: 650; color: var(--af-success); }
.note { margin-top: 10px !important; padding-top: 10px; border-top: 1px dashed var(--af-line-strong); }

/* Comparison table */
.tablewrap { overflow: auto; border-radius: 16px; border: 1px solid var(--af-line); }
.tablewrap:focus-visible { outline: 3px solid var(--af-focus); outline-offset: 2px; }
.table { width: 100%; border-collapse: separate; border-spacing: 0; font-variant-numeric: tabular-nums; font-size: 14.5px; }
.table th, .table td { padding: 12px 14px; text-align: right; border-bottom: 1px solid var(--af-line); }
.table tbody tr:last-child th, .table tbody tr:last-child td { border-bottom: 0; }
.table thead th { font-size: 12.5px; font-weight: 750; color: var(--af-ink-2); text-transform: uppercase; letter-spacing: 0.06em; background: var(--af-surface-2); }
.table abbr { text-decoration: underline dotted; cursor: help; }
.table th:first-child { text-align: left; min-width: 230px; }
.table tbody th { font-weight: 600; }
.table tbody tr:nth-child(even) td, .table tbody tr:nth-child(even) th { background: var(--af-surface-2); }
.table tbody tr.is-chosen td, .table tbody tr.is-chosen th { background: var(--af-brand-tint); box-shadow: inset 0 1px 0 var(--af-brand), inset 0 -1px 0 var(--af-brand); }
.table tbody tr.is-chosen td { font-weight: 800; }
.mname { display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: center; font-weight: 750; }
.mtext { display: block; margin-top: 3px; font-size: 13px; font-weight: 500; color: var(--af-ink-2); line-height: 1.4; }
.badge { padding: 2px 9px; border-radius: 999px; font-size: 11.5px; font-weight: 750; background: var(--af-brand); color: var(--af-on-brand); letter-spacing: 0.02em; }

/* Loading + error */
.skel-chart { height: 240px; border-radius: 16px; background: var(--af-surface-2); border: 1px solid var(--af-line); animation: fc-pulse 1.4s ease-in-out infinite; }
@keyframes fc-pulse { 50% { opacity: 0.55; } }
@media (prefers-reduced-motion: reduce) { .skel-chart { animation: none; } }
.err { justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }

@media (max-width: 520px) {
  .table { font-size: 13px; }
  .table th, .table td { padding: 10px 8px; }
  .table th:first-child { min-width: 190px; }
  .prep { gap: 8px; }
  .prep div { padding: 10px; }
}
</style>
