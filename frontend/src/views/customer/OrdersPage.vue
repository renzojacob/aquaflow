<!--
  My orders: totals at the top, filters + search, then every order grouped by month
  (with what that month cost). Past deliveries can be ordered again in one tap.
-->
<script setup>
import { computed, ref } from 'vue'
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

import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import OrderListItem from '@/components/order/OrderListItem.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import { isActive } from '@/constants/orderStatus'
import { listAllOrders } from '@/services/customerService'
import { containers, peso } from '@/utils/format'
import { orderStats } from '@/utils/orderStats'

const ionRouter = useIonRouter()

const orders = ref([])
const loading = ref(true)
const error = ref(null)
const filter = ref('all')
const search = ref('')

async function load() {
  error.value = null
  try {
    orders.value = await listAllOrders()
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

const FILTERS = [
  { key: 'all', label: 'All', match: () => true },
  { key: 'active', label: 'In progress', match: isActive },
  { key: 'delivered', label: 'Delivered', match: (o) => o.status === 'delivered' },
  { key: 'closed', label: 'Cancelled', match: (o) => !isActive(o) && o.status !== 'delivered' },
]
const counts = computed(() => Object.fromEntries(FILTERS.map((f) => [f.key, orders.value.filter(f.match).length])))
const stats = computed(() => orderStats(orders.value))

const visible = computed(() => {
  const f = FILTERS.find((x) => x.key === filter.value)
  const q = search.value.trim().toLowerCase()
  return orders.value
    .filter(f.match)
    .filter((o) => !q || [o.code, o.address.label, o.address.barangay, o.notes].some((v) => (v ?? '').toLowerCase().includes(q)))
})

/** Group by the month of the delivery date, newest month first. */
const groups = computed(() => {
  const map = new Map()
  for (const o of visible.value) {
    const [y, m] = o.delivery_date.split('-').map(Number)
    const key = `${y}-${m}`
    if (!map.has(key)) {
      map.set(key, {
        key,
        title: new Date(y, m - 1, 1).toLocaleDateString('en-PH', { month: 'long', year: 'numeric' }),
        orders: [],
      })
    }
    map.get(key).orders.push(o)
  }
  return [...map.values()].map((g) => {
    const done = g.orders.filter((o) => o.status === 'delivered')
    return { ...g, spent: done.reduce((s, o) => s + o.total, 0), qty: done.reduce((s, o) => s + o.quantity, 0) }
  })
})

const go = (path) => ionRouter.push(path)
const again = (o) => go(`/customer/order?qty=${o.quantity}&address=${o.address.id}`)
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-title>My orders</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content>
      <ion-refresher slot="fixed" @ion-refresh="refresh">
        <ion-refresher-content />
      </ion-refresher>

      <div class="af-container af-dash af-dash--narrow">
        <header class="top">
          <h1 class="title">My orders</h1>
          <AppButton @click="go('/customer/order')">Order water</AppButton>
        </header>

        <!-- Totals -->
        <dl v-if="!loading && !error" class="sums">
          <div class="sum">
            <dt>In progress</dt>
            <dd>{{ counts.active }}</dd>
          </div>
          <div class="sum">
            <dt>Delivered</dt>
            <dd>{{ stats.allTime.delivered }}<small>{{ containers(stats.allTime.containers) }}</small></dd>
          </div>
          <div class="sum sum--money">
            <dt>Spent in total</dt>
            <dd class="af-money">{{ peso(stats.allTime.spent) }}</dd>
          </div>
        </dl>

        <!-- Filters + search -->
        <div class="tools">
          <div class="af-chips" role="tablist" aria-label="Which orders">
            <button
              v-for="f in FILTERS"
              :key="f.key"
              type="button"
              role="tab"
              class="af-chip"
              :aria-selected="filter === f.key"
              @click="filter = f.key"
            >
              {{ f.label }} <span class="af-chip__n">{{ counts[f.key] ?? 0 }}</span>
            </button>
          </div>
          <label class="search">
            <span class="af-sr-only">Search my orders</span>
            <input v-model="search" type="search" placeholder="Search code, address, note" />
          </label>
        </div>

        <div v-if="loading" class="af-panel"><SkeletonList :rows="4" /></div>

        <div v-else-if="error" class="af-panel err" role="alert">
          <b>Couldn't load your orders</b>
          <p>{{ error.message }}</p>
          <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>

        <div v-else-if="!visible.length" class="af-panel">
          <EmptyState
            :title="search ? 'No matching orders' : orders.length ? 'Nothing in this list' : 'No orders yet'"
            :message="search ? 'Try another code or address.' : orders.length ? 'Pick another filter above.' : 'Your first refill is a few taps away.'"
            :action-label="orders.length ? '' : 'Order water'"
            @action="go('/customer/order')"
          />
        </div>

        <section v-for="g in groups" v-else :key="g.key" class="month" :aria-label="g.title">
          <div class="month__head">
            <h2>{{ g.title }}</h2>
            <span v-if="g.spent" class="month__sum"><b class="af-money">{{ peso(g.spent) }}</b> for {{ containers(g.qty) }}</span>
          </div>
          <ul class="list">
            <li v-for="o in g.orders" :key="o.id">
              <OrderListItem :order="o" :can-reorder="o.status === 'delivered'" @open="go(`/customer/orders/${o.id}`)" @again="again(o)" />
            </li>
          </ul>
        </section>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.top { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.title { margin: 0; font-family: var(--af-display); font-size: clamp(26px, 3.4vw, 34px); font-weight: 650; letter-spacing: -0.04em; }

.sums { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 0; }
.sum { display: grid; gap: 6px; padding: 16px 18px; border-radius: 20px; background: var(--af-surface); border: 1px solid var(--af-line); min-width: 0; }
.sum dt { font-size: 13px; font-weight: 700; color: var(--af-ink-2); }
.sum dd { margin: 0; font-family: var(--af-display); font-size: 28px; font-weight: 650; letter-spacing: -0.035em; line-height: 1; font-variant-numeric: tabular-nums; }
.sum dd small { display: block; margin-top: 6px; font-family: var(--af-font); font-size: 12.5px; font-weight: 650; letter-spacing: 0; color: var(--af-ink-2); }
.sum--money { background: linear-gradient(160deg, var(--af-sun-tint), transparent 80%), var(--af-surface); border-color: color-mix(in srgb, var(--af-sun-glow) 30%, var(--af-line)); }

.tools { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; justify-content: space-between; }
.search { flex: 1 1 220px; display: flex; justify-content: flex-end; }
.search input {
  width: min(300px, 100%);
  min-height: 44px;
  padding: 0 16px 0 42px;
  border-radius: var(--af-r-pill);
  border: 1px solid var(--af-line-strong);
  background: var(--af-surface) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' fill='none' stroke='%238fb3ba' stroke-width='2' stroke-linecap='round' viewBox='0 0 24 24'%3E%3Ccircle cx='11' cy='11' r='7'/%3E%3Cpath d='m20 20-3.5-3.5'/%3E%3C/svg%3E") no-repeat 16px center;
  color: var(--af-ink);
  font: 550 15px var(--af-font);
}
.search input:focus { outline: none; border-color: var(--af-primary); box-shadow: 0 0 0 4px color-mix(in srgb, var(--af-primary) 18%, transparent); }

.month { display: grid; gap: 10px; }
.month__head { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; padding: 0 4px; flex-wrap: wrap; }
.month__head h2 { margin: 0; font-family: var(--af-display); font-size: 16px; font-weight: 600; letter-spacing: -0.02em; }
.month__sum { font-size: 13.5px; font-weight: 650; color: var(--af-ink-2); }
.month__sum b { font-weight: 800; }
.list { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }

.err { justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }

@media (max-width: 560px) {
  .sums { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .sum--money { grid-column: span 2; }
  .search { justify-content: stretch; }
  .search input { width: 100%; }
}
</style>
