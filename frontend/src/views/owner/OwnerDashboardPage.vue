<!--
  Owner dashboard: the business at a glance, all from real orders (GET /api/v1/dispatch/summary).
  Tank (sunlit): today's sales against the best day of the last 14 days.
  Then 14-day numbers, a sales chart, today's orders by status, where orders come from,
  morning vs afternoon, delivery success, stock and people.
-->
<script setup>
import { computed, ref } from 'vue'
import {
  IonContent,
  IonHeader,
  IonIcon,
  IonPage,
  IonRefresher,
  IonRefresherContent,
  IonTitle,
  IonToolbar,
  onIonViewWillEnter,
  useIonRouter,
} from '@ionic/vue'
import {
  cashOutline,
  cubeOutline,
  documentTextOutline,
  listOutline,
  peopleOutline,
  receiptOutline,
  trophyOutline,
} from 'ionicons/icons'

import AppButton from '@/components/ui/AppButton.vue'
import AreaChart from '@/components/viz/AreaChart.vue'
import DonutChart from '@/components/viz/DonutChart.vue'
import KpiTile from '@/components/dash/KpiTile.vue'
import QuickAction from '@/components/dash/QuickAction.vue'
import RingGauge from '@/components/viz/RingGauge.vue'
import SectionHead from '@/components/dash/SectionHead.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import TankHero from '@/components/dash/TankHero.vue'
import SegmentedControl from '@/components/form/SegmentedControl.vue'
import { ORDER_STATUS } from '@/constants/orderStatus'
import { useCountUp } from '@/composables/useCountUp'
import { getSummary } from '@/services/dispatcherService'
import { useAuthStore } from '@/stores/auth'
import { containers, greeting, peso } from '@/utils/format'

const auth = useAuthStore()
const ionRouter = useIonRouter()

const range = ref('14')
const data = ref(null)
const loading = ref(true)
const error = ref(null)

async function load() {
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
async function refresh(ev) {
  await load()
  ev.target.complete()
}
function setRange(v) {
  range.value = v
  loading.value = true
  load()
}

const days = computed(() => data.value?.days ?? [])
const today = computed(() => days.value.at(-1) ?? { revenue: 0, delivered: 0, orders: 0, containers: 0 })
const best = computed(() => days.value.reduce((b, d) => (d.revenue > b.revenue ? d : b), { revenue: 0, date: '' }))
const level = computed(() => (best.value.revenue ? today.value.revenue / best.value.revenue : 0))
const todayShown = useCountUp(() => today.value.revenue)

const label = (iso) => {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-PH', { month: 'short', day: 'numeric' })
}
const weekday = (iso) => {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-PH', { weekday: 'long', month: 'long', day: 'numeric' })
}
const revenuePoints = computed(() => days.value.map((d) => ({ label: label(d.date), sub: weekday(d.date), value: d.revenue })))

// Today's orders by status (every status gets a slice; empty ones are listed faded)
const STATUS_ORDER = ['pending', 'confirmed', 'preparing', 'ready_for_pickup', 'out_for_delivery', 'delivered', 'failed_delivery', 'cancelled', 'rejected']
const ALWAYS = ['pending', 'out_for_delivery', 'delivered']
const slices = computed(() =>
  STATUS_ORDER.map((k) => ({ key: k, label: ORDER_STATUS[k].label, value: data.value?.status_today?.[k] ?? 0, color: `var(--af-st-${ORDER_STATUS[k].tone})` }))
    .filter((s) => s.value || ALWAYS.includes(s.key)),
)
const todayTotal = computed(() => Object.values(data.value?.status_today ?? {}).reduce((a, b) => a + b, 0))

const totals = computed(() => data.value?.totals ?? { orders: 0, delivered: 0, failed: 0, cancelled: 0, revenue: 0, containers: 0 })
const success = computed(() => {
  const tried = totals.value.delivered + totals.value.failed
  return tried ? totals.value.delivered / tried : 0
})
const avgOrder = computed(() => (totals.value.delivered ? totals.value.revenue / totals.value.delivered : 0))
const topMax = computed(() => Math.max(1, ...(data.value?.top_barangays ?? []).map((b) => b.orders)))
const periodShare = computed(() => {
  const p = data.value?.periods ?? { morning: 0, afternoon: 0 }
  const all = p.morning + p.afternoon
  return { ...p, m: all ? Math.round((p.morning / all) * 100) : 0, a: all ? Math.round((p.afternoon / all) * 100) : 0 }
})

const go = (path) => ionRouter.navigate(path, 'root', 'replace')
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-title>Dashboard</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content>
      <ion-refresher slot="fixed" @ion-refresh="refresh">
        <ion-refresher-content />
      </ion-refresher>

      <div class="af-container af-dash">
        <div class="top">
          <p class="hello">{{ greeting() }}, <b>{{ auth.user?.full_name?.split(' ')[0] }}</b></p>
          <SegmentedControl :model-value="range" :options="[{ value: '7', label: '7 days' }, { value: '14', label: '14 days' }, { value: '30', label: '30 days' }]" label="Period" @update:model-value="setRange" />
        </div>

        <div v-if="loading" class="af-panel"><SkeletonList :rows="5" :avatar="false" /></div>

        <div v-else-if="error" class="af-panel err" role="alert">
          <b>Couldn't load the dashboard</b>
          <p>{{ error.message }}</p>
          <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>

        <template v-else-if="data">
          <!-- ===== Today ===== -->
          <div class="af-bento af-bento--stretch">
            <TankHero class="b-8" tone="sun" :level="level" :label="`Today's sales are ${Math.round(level * 100)}% of the best day in the last ${range} days`">
              <span class="t-kicker">Collected today</span>
              <h1 class="t-money">{{ peso(todayShown) }}</h1>
              <p class="tank__soft t-sub">
                {{ today.delivered }} deliveries, {{ containers(today.containers) }}.
                <template v-if="best.revenue"> Best day in the last {{ range }} days: {{ peso(best.revenue) }} on {{ label(best.date) }}.</template>
              </p>
              <div class="t-stats">
                <div><b>{{ todayTotal }}</b><span>orders today</span></div>
                <div><b>{{ data.status_today.out_for_delivery ?? 0 }}</b><span>on the road</span></div>
                <div><b>{{ (data.status_today.pending ?? 0) + (data.status_today.confirmed ?? 0) + (data.status_today.preparing ?? 0) }}</b><span>being handled</span></div>
              </div>
            </TankHero>

            <section class="b-4 side" aria-label="Shortcuts">
              <QuickAction primary :icon="listOutline" title="Order queue" :detail="`${data.status_today.pending ?? 0} waiting to confirm`" @click="go('/owner/queue')" />
              <QuickAction :icon="cubeOutline" title="Stock" :detail="`${data.stock.available} ready to promise`" @click="go('/owner/stock')" />
              <QuickAction :icon="peopleOutline" title="Users" :detail="`${data.customers} customers, ${data.riders} riders`" tone="pearl" @click="go('/owner/users')" />
              <QuickAction :icon="documentTextOutline" title="Reports" detail="Sales by day, ready to print" tone="sun" @click="go('/owner/reports')" />
            </section>
          </div>

          <!-- ===== The period ===== -->
          <div class="kpis">
            <KpiTile :label="`Sales, last ${range} days`" :value="peso(totals.revenue)" tone="sun" :icon="cashOutline" :hint="`About ${peso(avgOrder)} per delivery`" :spark="days.map((d) => d.revenue)" />
            <KpiTile label="Orders" :value="totals.orders" :icon="receiptOutline" :hint="`${totals.cancelled} cancelled or rejected`" :spark="days.map((d) => d.orders)" />
            <KpiTile label="Containers delivered" :value="totals.containers" :icon="cubeOutline" :hint="`${totals.delivered} deliveries`" :spark="days.map((d) => d.containers)" />
            <KpiTile label="Customers" :value="data.customers" tone="pearl" :icon="peopleOutline" :hint="data.new_customers ? `${data.new_customers} joined in this period` : 'No new sign-ups in this period'" />
          </div>

          <div class="af-bento af-bento--stretch">
            <section class="af-panel b-8" aria-labelledby="rev-title">
              <SectionHead :title="`Sales, last ${range} days`" :sub="`${peso(totals.revenue)} from ${totals.delivered} deliveries`" />
              <AreaChart :points="revenuePoints" :format="peso" tone="sun" :title="`Sales per day, last ${range} days`" :height="300" />
            </section>
            <section class="af-panel b-4" aria-labelledby="st-title">
              <SectionHead title="Today's orders" :sub="todayTotal ? `${todayTotal} in total` : 'None yet today'" />
              <DonutChart :slices="slices" title="Today's orders by status" :center="String(todayTotal)" center-sub="orders" />
            </section>
          </div>

          <div class="af-bento af-bento--stretch">
            <section class="af-panel b-5" aria-labelledby="br-title">
              <SectionHead title="Where orders come from" :sub="`Top barangays, last ${range} days`" />
              <ol v-if="data.top_barangays.length" class="brgy">
                <li v-for="(b, i) in data.top_barangays" :key="b.name">
                  <span class="brgy__rank" :class="{ 'is-first': i === 0 }">
                    <ion-icon v-if="i === 0" :icon="trophyOutline" aria-hidden="true" /><template v-else>{{ i + 1 }}</template>
                  </span>
                  <span class="brgy__name">{{ b.name }}</span>
                  <span class="brgy__bar" aria-hidden="true"><i :style="{ width: `${(b.orders / topMax) * 100}%` }"></i></span>
                  <span class="brgy__n">{{ b.orders }} <small>orders</small></span>
                </li>
              </ol>
              <p v-else class="af-small">No orders in this period yet.</p>
            </section>

            <section class="af-panel b-4" aria-labelledby="sx-title">
              <SectionHead title="Delivery success" sub="Delivered on the first try or after one re-plan" />
              <div class="succ">
                <RingGauge :value="success" :size="128" tone="water" :label="`${Math.round(success * 100)}% of attempted deliveries succeeded`">
                  <b class="succ__n">{{ Math.round(success * 100) }}%</b>
                </RingGauge>
                <dl class="succ__facts">
                  <div><dt>Delivered</dt><dd>{{ totals.delivered }}</dd></div>
                  <div><dt>Failed tries</dt><dd>{{ totals.failed }}</dd></div>
                </dl>
              </div>
            </section>

            <section class="af-panel b-3" aria-labelledby="pd-title">
              <SectionHead title="Busiest time" :sub="`Last ${range} days`" />
              <div class="split">
                <div class="split__bar" aria-hidden="true">
                  <i class="split__m" :style="{ height: `${Math.max(periodShare.m, 4)}%` }"></i>
                  <i class="split__a" :style="{ height: `${Math.max(periodShare.a, 4)}%` }"></i>
                </div>
                <dl class="split__facts">
                  <div><dt><i class="key key--m" aria-hidden="true"></i>Morning</dt><dd>{{ periodShare.m }}%<small>{{ periodShare.morning }} orders</small></dd></div>
                  <div><dt><i class="key key--a" aria-hidden="true"></i>Afternoon</dt><dd>{{ periodShare.a }}%<small>{{ periodShare.afternoon }} orders</small></dd></div>
                </dl>
              </div>
            </section>
          </div>
        </template>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.top { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.hello { margin: 0; font-size: 17px; font-weight: 600; color: var(--af-ink-2); }
.hello b { color: var(--af-ink); font-weight: 800; }

.t-kicker { font-size: 14px; font-weight: 750; color: var(--af-on-sun-soft); }
.t-money { margin: 0; font-family: var(--af-display); font-size: clamp(44px, 7vw, 84px); font-weight: 650; letter-spacing: -0.05em; line-height: 0.95; color: var(--af-sun); text-shadow: 0 0 40px rgba(var(--af-sun-rgb), 0.35); font-variant-numeric: tabular-nums; }
.t-sub { margin: 0; font-size: 15px; line-height: 1.55; font-weight: 550; max-width: 46ch; }
.t-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-top: auto; max-width: 520px; }
.t-stats div { display: grid; gap: 2px; padding: 12px 14px; border-radius: 18px; background: var(--af-tank-sun-scrim); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
.t-stats b { font-family: var(--af-display); font-size: 24px; font-weight: 650; letter-spacing: -0.03em; }
.t-stats span { font-size: 12.5px; font-weight: 700; color: var(--af-on-sun-soft); }

.side { display: grid; gap: 12px; align-content: start; }
.kpis { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
@media (min-width: 1000px) { .kpis { grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; } }

.brgy { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }
.brgy li { display: grid; grid-template-columns: 30px minmax(70px, 120px) 1fr auto; gap: 12px; align-items: center; }
.brgy__rank { width: 30px; height: 30px; display: grid; place-items: center; border-radius: 10px; background: var(--af-surface-2); font-size: 13px; font-weight: 800; color: var(--af-ink-2); }
.brgy__rank.is-first { background: var(--af-sun-tint); color: var(--af-sun); font-size: 16px; }
.brgy__name { font-size: 14.5px; font-weight: 750; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.brgy__bar { height: 10px; border-radius: 6px; background: var(--af-surface-2); overflow: hidden; }
.brgy__bar i { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--af-water-deep), var(--af-primary)); }
.brgy__n { font-size: 14px; font-weight: 800; font-variant-numeric: tabular-nums; white-space: nowrap; }
.brgy__n small { font-size: 12px; font-weight: 600; color: var(--af-ink-2); }

.succ { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; }
.succ__n { font-family: var(--af-display); font-size: 28px; font-weight: 700; letter-spacing: -0.04em; }
.succ__facts { flex: 1; min-width: 120px; display: grid; gap: 8px; margin: 0; }
.succ__facts div { display: flex; justify-content: space-between; padding: 10px 12px; border-radius: 12px; background: var(--af-surface-2); }
.succ__facts dt { font-size: 13px; font-weight: 650; color: var(--af-ink-2); }
.succ__facts dd { margin: 0; font-weight: 800; font-variant-numeric: tabular-nums; }

.split { display: flex; gap: 18px; align-items: stretch; }
.split__bar { width: 56px; height: 150px; display: flex; flex-direction: column; gap: 4px; }
.split__bar i { display: block; border-radius: 10px; }
.split__m { background: var(--af-sun-glow); }
.split__a { background: var(--af-pearl); }
.split__facts { margin: 0; display: grid; align-content: space-between; gap: 12px; }
.split__facts dt { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 750; color: var(--af-ink-2); }
.key { width: 10px; height: 10px; border-radius: 3px; }
.key--m { background: var(--af-sun-glow); }
.key--a { background: var(--af-pearl); }
.split__facts dd { margin: 2px 0 0; font-family: var(--af-display); font-size: 26px; font-weight: 650; letter-spacing: -0.03em; }
.split__facts small { display: block; font-family: var(--af-font); font-size: 12.5px; font-weight: 650; letter-spacing: 0; color: var(--af-ink-2); }

.err { justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }

@media (max-width: 520px) {
  .brgy li { grid-template-columns: 30px 1fr auto; }
  .brgy__bar { grid-column: 2 / -1; grid-row: 2; }
}
</style>
