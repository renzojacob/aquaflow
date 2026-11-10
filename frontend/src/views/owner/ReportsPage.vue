<!--
  Owner: reports. Sales and deliveries per day for the chosen period, as a chart and as a
  table with totals, ready to print (the sidebar and buttons are hidden on paper).
  All numbers come from real orders (GET /api/v1/dispatch/summary).
  Feature C: the refill prediction backtest sits under the sales numbers.
-->
<script setup>
import { computed, ref } from 'vue'
import { IonContent, IonHeader, IonIcon, IonPage, IonTitle, IonToolbar, onIonViewWillEnter } from '@ionic/vue'
import { printOutline } from 'ionicons/icons'

import AppButton from '@/components/ui/AppButton.vue'
import AreaChart from '@/components/viz/AreaChart.vue'
import BarChart from '@/components/viz/BarChart.vue'
import KpiTile from '@/components/dash/KpiTile.vue'
import RefillAccuracy from '@/components/dash/RefillAccuracy.vue'
import SectionHead from '@/components/dash/SectionHead.vue'
import SegmentedControl from '@/components/form/SegmentedControl.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import { getSummary } from '@/services/dispatcherService'
import { containers, peso } from '@/utils/format'

const range = ref('30')
const data = ref(null)
const loading = ref(true)
const error = ref(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    data.value = await getSummary(Number(range.value))
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
onIonViewWillEnter(load)
function setRange(v) {
  range.value = v
  load()
}

const toDate = (iso) => {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}
const days = computed(() => [...(data.value?.days ?? [])])
const totals = computed(() => data.value?.totals ?? { orders: 0, delivered: 0, revenue: 0, containers: 0, failed: 0, cancelled: 0 })

// Same weekday averages: which days of the week sell the most
const weekdays = computed(() => {
  const names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const sum = Array(7).fill(0)
  const n = Array(7).fill(0)
  for (const d of days.value) {
    const i = (toDate(d.date).getDay() + 6) % 7
    sum[i] += d.revenue
    n[i] += 1
  }
  const avg = sum.map((s, i) => (n[i] ? Math.round(s / n[i]) : 0))
  const best = avg.indexOf(Math.max(...avg))
  return { bars: names.map((label, i) => ({ label, value: avg[i], sub: `Average ${label}` })), best: names[best] }
})
const printReport = () => window.print()
const fmtDay = (iso) => toDate(iso).toLocaleDateString('en-PH', { weekday: 'short', month: 'short', day: 'numeric' })
/** Short form for the table on phones: "Nov 2" */
const fmtShort = (iso) => toDate(iso).toLocaleDateString('en-PH', { month: 'short', day: 'numeric' })
const period = computed(() => (days.value.length ? `${fmtDay(days.value[0].date)} to ${fmtDay(days.value.at(-1).date)}` : ''))
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-title>Reports</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content>
      <div class="af-container af-dash report">
        <header class="top">
          <div>
            <h1 class="title">Sales report</h1>
            <p class="af-small">{{ period }}</p>
          </div>
          <div class="no-print tools">
            <SegmentedControl :model-value="range" :options="[{ value: '7', label: '7 days' }, { value: '14', label: '14 days' }, { value: '30', label: '30 days' }]" label="Period" @update:model-value="setRange" />
            <AppButton variant="secondary" @click="printReport"><ion-icon :icon="printOutline" aria-hidden="true" /> Print</AppButton>
          </div>
        </header>

        <div v-if="loading" class="af-panel"><SkeletonList :rows="5" :avatar="false" /></div>
        <div v-else-if="error" class="af-panel err" role="alert">
          <b>Couldn't load the report</b>
          <p>{{ error.message }}</p>
          <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>

        <template v-else-if="data">
          <div class="kpis">
            <KpiTile label="Sales" :value="peso(totals.revenue)" tone="sun" :hint="`${totals.delivered} deliveries`" />
            <KpiTile label="Containers delivered" :value="totals.containers" :hint="totals.delivered ? `${(totals.containers / totals.delivered).toFixed(1)} per delivery` : ''" />
            <KpiTile label="Orders placed" :value="totals.orders" :hint="`${totals.cancelled} cancelled or rejected`" />
            <KpiTile label="Failed tries" :value="totals.failed" :tone="totals.failed ? 'warn' : 'water'" :hint="totals.failed ? 'No one home, wrong address…' : 'None in this period'" />
          </div>

          <div class="af-bento af-bento--stretch">
            <section class="af-panel b-8">
              <SectionHead title="Sales per day" />
              <AreaChart :points="days.map((d) => ({ label: fmtDay(d.date).split(', ')[1] ?? d.date, sub: fmtDay(d.date), value: d.revenue }))" :format="peso" tone="sun" title="Sales per day" :height="220" />
            </section>
            <section class="af-panel b-4">
              <SectionHead title="Best day of the week" :sub="weekdays.best ? `${weekdays.best} sells the most on average` : ''" />
              <BarChart :bars="weekdays.bars" :format="peso" tone="pearl" title="Average sales by weekday" :highlight="weekdays.bars.findIndex((b) => b.label === weekdays.best)" :height="180" />
            </section>
          </div>

          <section class="af-panel">
            <SectionHead title="Day by day" :sub="`${days.length} days`" />
            <div class="tablewrap">
              <table class="table">
                <thead>
                  <tr><th scope="col">Day</th><th scope="col">Orders</th><th scope="col">Delivered</th><th scope="col">Containers</th><th scope="col">Sales</th></tr>
                </thead>
                <tbody>
                  <tr v-for="d in [...days].reverse()" :key="d.date" :class="{ 'is-zero': !d.orders }">
                    <th scope="row"><span class="wide-only">{{ fmtDay(d.date) }}</span><span class="narrow-only">{{ fmtShort(d.date) }}</span></th>
                    <td>{{ d.orders }}</td>
                    <td>{{ d.delivered }}</td>
                    <td>{{ d.containers }}</td>
                    <td class="money">{{ peso(d.revenue) }}</td>
                  </tr>
                </tbody>
                <tfoot>
                  <tr><th scope="row">Total</th><td>{{ totals.orders }}</td><td>{{ totals.delivered }}</td><td>{{ totals.containers }}</td><td class="money">{{ peso(totals.revenue) }}</td></tr>
                </tfoot>
              </table>
            </div>
            <p class="af-small">Sales count delivered orders only, at the price on each order. {{ containers(totals.containers) }} delivered in this period.</p>
          </section>

          <RefillAccuracy />
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
.kpis { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
@media (min-width: 1000px) { .kpis { grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; } }

.tablewrap { overflow: auto; max-height: 70vh; border-radius: 16px; border: 1px solid var(--af-line); }
.table { width: 100%; border-collapse: separate; border-spacing: 0; font-variant-numeric: tabular-nums; font-size: 14.5px; }
.table th, .table td { padding: 11px 14px; text-align: right; border-bottom: 1px solid var(--af-line); white-space: nowrap; }
.table thead th { position: sticky; top: 0; z-index: 1; background: color-mix(in srgb, var(--af-surface-solid) 92%, transparent); backdrop-filter: blur(8px); text-transform: uppercase; letter-spacing: 0.06em; }
.table tbody tr:nth-child(even) td, .table tbody tr:nth-child(even) th { background: var(--af-surface-2); }
.table tbody tr:hover td, .table tbody tr:hover th { background: var(--af-brand-tint); }
.table tfoot th, .table tfoot td { position: sticky; bottom: 0; background: color-mix(in srgb, var(--af-surface-solid) 94%, transparent); backdrop-filter: blur(8px); }
.table th:first-child { text-align: left; }
.table thead th { font-size: 12.5px; font-weight: 750; color: var(--af-ink-2); }
.table tbody th { font-weight: 700; }
.table tbody tr.is-zero { color: var(--af-ink-2); }
.table .money { color: var(--af-sun); font-weight: 800; }
.table tfoot th, .table tfoot td { font-weight: 800; border-bottom: 0; border-top: 2px solid var(--af-line-strong); font-size: 15px; }
.af-panel > p { margin: 0; }
.narrow-only { display: none; }
@media (max-width: 520px) { .wide-only { display: none; } .narrow-only { display: inline; } }

.err { justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }

@media (max-width: 520px) {
  .table { font-size: 13px; }
  .table th, .table td { padding: 9px 6px; }
  .table thead th { font-size: 11.5px; }
  .table tfoot th, .table tfoot td { font-size: 13.5px; }
}

@media print {
  .no-print { display: none !important; }
}
</style>
