<!--
  Dispatcher command center.
  Top: a tank whose water = share of today's orders that are finished, with the day's pipeline;
  stock + riders beside it; four numbers that need attention.
  Below: the queue. Desktop (>= 1100px): list left, selected order right. Phone: tap to open.
-->
<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  IonContent,
  IonHeader,
  IonPage,
  IonRefresher,
  IonRefresherContent,
  IonTitle,
  IonToolbar,
  onIonViewWillEnter,
  useIonRouter,
} from '@ionic/vue'

import { IonIcon } from '@ionic/vue'
import { alertCircleOutline, bicycleOutline, cashOutline, cubeOutline, waterOutline } from 'ionicons/icons'
import AppButton from '@/components/ui/AppButton.vue'
import KpiTile from '@/components/dash/KpiTile.vue'
import RingGauge from '@/components/viz/RingGauge.vue'
import SectionHead from '@/components/dash/SectionHead.vue'
import TankHero from '@/components/dash/TankHero.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import OrderAdminPanel from '@/components/dispatcher/OrderAdminPanel.vue'
import QueueRow from '@/components/dispatcher/QueueRow.vue'
import SegmentedControl from '@/components/form/SegmentedControl.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import { MAX_ATTEMPTS } from '@/constants/orderStatus'
import { refillsOf } from '@/constants/cart'
import { useMediaQuery } from '@/composables/useMediaQuery'
import { showToast } from '@/composables/useToast'
import { getStock, getSummary, listQueue, listRiders, runOrderAction } from '@/services/dispatcherService'
import { ago, containers, dateISO, friendlyDay, initials, peso } from '@/utils/format'

const ionRouter = useIonRouter()
const route = useRoute()
// The owner sees this same screen at /owner/queue
const base = computed(() => (route.path.startsWith('/owner') ? '/owner' : '/dispatcher'))
const wide = useMediaQuery('(min-width: 1100px)')

const day = ref('today')
const tab = ref('pending')
const search = ref('')
const orders = ref([])
const stock = ref(null)
const loading = ref(true)
const error = ref(null)
const selectedId = ref('')
const quickBusy = ref('')
const riders = ref([])
const summary = ref(null)

const date = computed(() => dateISO(day.value === 'today' ? 0 : 1))

// Status tabs. "Ready" also holds failed deliveries waiting to be re-planned.
const TABS = [
  { key: 'pending', label: 'Pending', match: (o) => o.status === 'pending' },
  { key: 'confirmed', label: 'Confirmed', match: (o) => o.status === 'confirmed' },
  { key: 'preparing', label: 'Preparing', match: (o) => o.status === 'preparing' },
  {
    key: 'ready',
    label: 'Ready',
    match: (o) => o.status === 'ready_for_pickup' || (o.status === 'failed_delivery' && o.attempts < MAX_ATTEMPTS),
  },
  { key: 'out', label: 'On the road', match: (o) => o.status === 'out_for_delivery' },
  {
    key: 'closed',
    label: 'Closed',
    match: (o) => ['delivered', 'rejected', 'cancelled'].includes(o.status) || (o.status === 'failed_delivery' && o.attempts >= MAX_ATTEMPTS),
  },
]

const counts = computed(() => Object.fromEntries(TABS.map((t) => [t.key, orders.value.filter(t.match).length])))

const visible = computed(() => {
  const t = TABS.find((x) => x.key === tab.value)
  const q = search.value.trim().toLowerCase()
  return orders.value
    .filter(t.match)
    .filter((o) => !q || [o.code, o.customer.name, o.address.barangay].some((v) => v.toLowerCase().includes(q)))
    // Oldest first inside a tab: first come, first served
    .sort((a, b) => a.created_at.localeCompare(b.created_at))
})

const toPrepare = computed(() =>
  orders.value.filter((o) => ['confirmed', 'preparing'].includes(o.status)).reduce((s, o) => s + refillsOf(o), 0),
)

async function load() {
  error.value = null
  try {
    const [q, s, r, sum] = await Promise.all([listQueue(date.value), getStock(), listRiders(), getSummary(7)])
    orders.value = q
    stock.value = s
    riders.value = r
    summary.value = sum
    // Keep the selection valid on desktop
    if (wide.value && !visible.value.some((o) => o.id === selectedId.value)) {
      selectedId.value = visible.value[0]?.id ?? ''
    }
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

onIonViewWillEnter(load)
watch(day, () => {
  loading.value = true
  load()
})
watch(tab, () => {
  if (wide.value) selectedId.value = visible.value[0]?.id ?? ''
})

async function refresh(ev) {
  await load()
  ev.target.complete()
}

function open(order) {
  if (wide.value) selectedId.value = order.id
  else ionRouter.push(base.value === '/owner' ? `/owner/queue/${order.id}` : `/dispatcher/orders/${order.id}`)
}

async function quickConfirm(order) {
  quickBusy.value = order.id
  try {
    await runOrderAction(order.id, 'confirm')
    showToast(`${order.code} confirmed`, 'success')
  } catch (e) {
    showToast(e.message, 'danger')
  } finally {
    quickBusy.value = ''
    await load()
  }
}

// ---------- the day at a glance ----------
const live = computed(() => orders.value.filter((o) => !['rejected', 'cancelled'].includes(o.status)))
const finished = computed(() => live.value.filter((o) => o.status === 'delivered' || (o.status === 'failed_delivery' && o.attempts >= MAX_ATTEMPTS)))
const doneShare = computed(() => (live.value.length ? finished.value.length / live.value.length : 0))
const qtyOf = (list) => list.reduce((s, o) => s + refillsOf(o), 0)
const onRoad = computed(() => orders.value.filter((o) => o.status === 'out_for_delivery'))
const collected = computed(() => orders.value.filter((o) => o.status === 'delivered').reduce((s, o) => s + o.total, 0))
const toCollect = computed(() => onRoad.value.reduce((s, o) => s + o.total, 0))
const pipeline = computed(() => [
  { key: 'pending', label: 'To confirm', n: counts.value.pending ?? 0 },
  { key: 'confirmed', label: 'To fill', n: (counts.value.confirmed ?? 0) + (counts.value.preparing ?? 0) },
  { key: 'ready', label: 'Ready to go', n: counts.value.ready ?? 0 },
  { key: 'out', label: 'On the road', n: counts.value.out ?? 0 },
  { key: 'closed', label: 'Done', n: finished.value.length },
])
const headline = computed(() => {
  const p = counts.value.pending ?? 0
  if (!live.value.length) return `No orders for ${friendlyDay(date.value).toLowerCase()} yet`
  if (p) return `${p} order${p > 1 ? 's' : ''} waiting for you`
  if (finished.value.length === live.value.length) return 'Every order is done'
  return `${live.value.length - finished.value.length} order${live.value.length - finished.value.length > 1 ? 's' : ''} still moving`
})
const spark = computed(() => (summary.value?.days ?? []).map((d) => d.orders))
const sparkMoney = computed(() => (summary.value?.days ?? []).map((d) => d.revenue))

const dayOptions = [
  { value: 'today', label: 'Today' },
  { value: 'tomorrow', label: 'Tomorrow' },
]
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-title>Orders</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content>
      <ion-refresher slot="fixed" @ion-refresh="refresh">
        <ion-refresher-content />
      </ion-refresher>

      <div class="af-container af-dash cc">
        <!-- ===== The day ===== -->
        <div class="af-bento af-bento--stretch">
          <TankHero class="b-8" :level="doneShare" :label="`${finished.length} of ${live.length} orders finished for ${friendlyDay(date).toLowerCase()}`">
            <div class="t-top">
              <span class="t-day">{{ friendlyDay(date) }}'s orders</span>
              <SegmentedControl v-model="day" :options="dayOptions" label="Delivery day" />
            </div>
            <h1 class="t-title">{{ headline }}</h1>
            <p class="tank__soft t-sub">
              {{ finished.length }} of {{ live.length }} finished. {{ containers(qtyOf(live)) }} in total for {{ friendlyDay(date).toLowerCase() }}.
            </p>
            <ol class="pipe" aria-label="Orders by step">
              <li v-for="p in pipeline" :key="p.key">
                <button type="button" class="pipe__step" :class="{ 'is-on': tab === p.key, 'is-hot': p.key === 'pending' && p.n }" @click="tab = p.key">
                  <b>{{ p.n }}</b>
                  <span>{{ p.label }}</span>
                </button>
              </li>
            </ol>
          </TankHero>

          <aside class="b-4 side">
            <!-- Stock -->
            <section v-if="stock" class="af-panel stockp" aria-labelledby="st-title">
              <SectionHead title="Ready stock" action="Manage" @action="ionRouter.navigate(`${base}/stock`, 'root', 'replace')" />
              <div class="stockp__row">
                <RingGauge
                  :value="stock.filled_ready ? stock.available / stock.filled_ready : 0"
                  :size="104"
                  :tone="stock.available <= 5 ? 'warn' : 'water'"
                  :label="`${stock.available} of ${stock.filled_ready} filled containers are free to promise`"
                >
                  <b class="stockp__n">{{ stock.available }}</b>
                  <span class="stockp__u">free</span>
                </RingGauge>
                <dl class="stockp__facts">
                  <div><dt>Filled</dt><dd>{{ stock.filled_ready }}</dd></div>
                  <div><dt>Promised</dt><dd>{{ stock.reserved }}</dd></div>
                  <div><dt>Empties</dt><dd>{{ stock.empty_at_station }}</dd></div>
                </dl>
              </div>
              <p v-if="stock.available <= 5" class="warn"><ion-icon :icon="alertCircleOutline" aria-hidden="true" /> Running low. Fill more before confirming big orders.</p>
            </section>

            <!-- Riders -->
            <section class="af-panel" aria-labelledby="rd-title">
              <SectionHead title="Riders" :sub="riders.length ? `${riders.filter((r) => !r.on_road).length} free now` : 'None yet'" />
              <ul v-if="riders.length" class="riders">
                <li v-for="r in riders" :key="r.id">
                  <span class="riders__av" aria-hidden="true">{{ initials(r.name) }}</span>
                  <span class="riders__name">{{ r.name }}<small v-if="r.location?.fresh">{{ r.location.is_simulated ? 'Demo drive' : 'Sharing location' }}, {{ ago(r.location.at) }}</small><small v-else-if="r.location">Last seen {{ ago(r.location.at) }}</small></span>
                  <span class="riders__state" :class="{ 'is-out': r.on_road }">
                    <ion-icon :icon="bicycleOutline" aria-hidden="true" /> {{ r.on_road ? `${r.on_road} out` : 'Free' }}
                  </span>
                </li>
              </ul>
              <p v-else class="af-small">The owner adds riders on the Users screen.</p>
            </section>
          </aside>
        </div>

        <!-- ===== Numbers that need attention ===== -->
        <div class="kpis">
          <KpiTile label="Waiting to confirm" :value="counts.pending ?? 0" :tone="counts.pending ? 'warn' : 'water'" :icon="alertCircleOutline" :hint="counts.pending ? 'Oldest first below' : 'All caught up'" />
          <KpiTile label="Containers to fill" :value="toPrepare" :icon="waterOutline" :hint="`${(counts.confirmed ?? 0) + (counts.preparing ?? 0)} orders confirmed or filling`" />
          <KpiTile label="On the road" :value="qtyOf(onRoad)" unit="containers" :icon="cubeOutline" tone="pearl" :hint="toCollect ? `${peso(toCollect)} to collect` : 'Nothing out now'" :spark="spark" />
          <KpiTile label="Collected" :value="peso(collected)" tone="sun" :icon="cashOutline" :hint="`From ${finished.length} delivered orders`" :spark="sparkMoney" />
        </div>

        <!-- ===== Queue ===== -->
        <div class="tools">
          <div class="af-chips" role="tablist" aria-label="Order status">
            <button
              v-for="t in TABS"
              :key="t.key"
              type="button"
              role="tab"
              class="af-chip"
              :aria-selected="tab === t.key"
              @click="tab = t.key"
            >
              {{ t.label }} <span class="af-chip__n">{{ counts[t.key] ?? 0 }}</span>
            </button>
          </div>
          <label class="search">
            <span class="af-sr-only">Search orders</span>
            <input v-model="search" type="search" placeholder="Search name, code, barangay" />
          </label>
        </div>

        <div v-if="loading" class="af-panel"><SkeletonList :rows="5" /></div>

        <div v-else-if="error" class="af-panel err" role="alert">
          <b>Couldn't load the queue</b>
          <p>{{ error.message }}</p>
          <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>

        <div v-else class="split" :class="{ 'split--wide': wide }">
          <ul v-if="visible.length" class="list" aria-label="Orders">
            <li v-for="o in visible" :key="o.id">
              <QueueRow :order="o" :selected="wide && o.id === selectedId" :busy="quickBusy === o.id" @open="open" @quick-confirm="quickConfirm" />
            </li>
          </ul>
          <div v-else class="af-panel">
            <EmptyState
              art="drop"
              :title="search ? 'No matching orders' : `No ${TABS.find((t) => t.key === tab).label.toLowerCase()} orders`"
              :message="search ? 'Try another name, code or barangay.' : `Nothing here for ${friendlyDay(date).toLowerCase()}.`"
            />
          </div>

          <aside v-if="wide" class="af-panel detail" aria-label="Selected order">
            <OrderAdminPanel v-if="selectedId" :order-id="selectedId" @changed="load" />
            <p v-else class="af-small">Select an order to see its details.</p>
          </aside>
        </div>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.cc { max-width: 1320px; }

/* ---------- tank ---------- */
.t-top { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.t-day { font-size: 14px; font-weight: 750; color: var(--af-on-deep-soft); }
.t-top :deep(.af-seg) { background: rgba(var(--af-deep-rgb), 0.45); }
.t-title { margin: 0; font-family: var(--af-display); font-size: clamp(28px, 4vw, 46px); font-weight: 650; letter-spacing: -0.045em; line-height: 1.02; max-width: 18ch; }
.t-sub { margin: 0; font-size: 15px; font-weight: 550; }
.pipe { list-style: none; margin: 6px 0 0; padding: 0; display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; }
.pipe__step {
  width: 100%;
  display: grid;
  gap: 2px;
  padding: 12px 10px;
  border-radius: 18px;
  border: 1px solid color-mix(in srgb, var(--af-on-deep) 14%, transparent);
  background: rgba(var(--af-deep-rgb), 0.42);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  color: var(--af-on-deep);
  font-family: var(--af-font);
  text-align: left;
  cursor: pointer;
}
.pipe__step b { font-family: var(--af-display); font-size: 26px; font-weight: 650; letter-spacing: -0.03em; line-height: 1; font-variant-numeric: tabular-nums; }
.pipe__step span { font-size: 12.5px; font-weight: 700; color: var(--af-on-deep-soft); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pipe__step.is-on { border-color: var(--af-glow-c-hi); box-shadow: inset 0 0 0 1px var(--af-glow-c-hi); }
.pipe__step.is-hot b { color: var(--af-sun); }

/* ---------- side ---------- */
.side { display: grid; gap: 16px; align-content: start; }
.stockp__row { display: flex; align-items: center; gap: 18px; }
.stockp__n { font-family: var(--af-display); font-size: 28px; font-weight: 700; letter-spacing: -0.04em; line-height: 1; }
.stockp__u { font-size: 12px; font-weight: 700; color: var(--af-ink-2); }
.stockp__facts { flex: 1; display: grid; gap: 8px; margin: 0; }
.stockp__facts div { display: flex; justify-content: space-between; gap: 8px; padding: 8px 12px; border-radius: 12px; background: var(--af-surface-2); }
.stockp__facts dt { font-size: 13px; font-weight: 650; color: var(--af-ink-2); }
.stockp__facts dd { margin: 0; font-weight: 800; font-variant-numeric: tabular-nums; }
.warn { margin: 0; display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-radius: 14px; background: var(--af-amber-tint); color: var(--af-amber-fg); font-size: 13.5px; font-weight: 700; }
.riders { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.riders li { display: grid; grid-template-columns: 36px 1fr auto; gap: 10px; align-items: center; }
.riders__av { width: 36px; height: 36px; display: grid; place-items: center; border-radius: 50%; background: linear-gradient(140deg, var(--af-accent-on-deep), var(--af-glow-c)); color: var(--af-on-glow); font-size: 13px; font-weight: 800; }
.riders__name { display: grid; font-size: 14.5px; font-weight: 750; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.riders__name small { font-size: 12px; font-weight: 600; color: var(--af-ink-2); overflow: hidden; text-overflow: ellipsis; }
.riders__state { display: inline-flex; align-items: center; gap: 5px; padding: 5px 10px; border-radius: 999px; background: color-mix(in srgb, var(--af-success) 14%, transparent); color: var(--af-success); font-size: 12.5px; font-weight: 750; }
.riders__state.is-out { background: var(--af-pearl-tint); color: var(--af-pearl); }

.kpis { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
@media (min-width: 1000px) { .kpis { grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; } }

/* ---------- queue ---------- */
.tools { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; justify-content: space-between; }
.search { position: relative; flex: 1 1 220px; display: flex; justify-content: flex-end; }
.search input {
  width: min(340px, 100%);
  min-height: 44px;
  padding: 0 16px 0 42px;
  border-radius: var(--af-r-pill);
  border: 1px solid var(--af-line-strong);
  background: var(--af-surface) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' fill='none' stroke='%238fb3ba' stroke-width='2' stroke-linecap='round' viewBox='0 0 24 24'%3E%3Ccircle cx='11' cy='11' r='7'/%3E%3Cpath d='m20 20-3.5-3.5'/%3E%3C/svg%3E") no-repeat 16px center;
  color: var(--af-ink);
  font: 550 15px var(--af-font);
}
.search input:focus { outline: none; border-color: var(--af-primary); box-shadow: 0 0 0 4px color-mix(in srgb, var(--af-primary) 18%, transparent); }

.split { display: grid; gap: 16px; }
.split--wide { grid-template-columns: minmax(360px, 440px) minmax(0, 1fr); align-items: start; }
.list { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.detail { position: sticky; top: 16px; border-radius: 28px; }

.err { justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }

@media (max-width: 640px) {
  .pipe { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .pipe li:nth-child(n + 4) { grid-column: span 1; }
  .search { justify-content: stretch; }
  .search input { width: 100%; }
}
</style>
