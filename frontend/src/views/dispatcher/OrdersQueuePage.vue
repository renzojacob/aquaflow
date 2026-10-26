<!--
  Dispatcher order queue.
  Desktop (>= 1100px): list on the left, selected order on the right.
  Phone/tablet: list only; tapping an order opens its own page.
-->
<script setup>
import { computed, ref, watch } from 'vue'
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
import OrderAdminPanel from '@/components/dispatcher/OrderAdminPanel.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import QueueRow from '@/components/dispatcher/QueueRow.vue'
import SegmentedControl from '@/components/form/SegmentedControl.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import WaterLevelBar from '@/components/ui/WaterLevelBar.vue'
import { MAX_ATTEMPTS } from '@/constants/orderStatus'
import { useMediaQuery } from '@/composables/useMediaQuery'
import { showToast } from '@/composables/useToast'
import { getStock, listQueue, runOrderAction } from '@/services/dispatcherService'
import { dateISO, friendlyDay } from '@/utils/format'

const ionRouter = useIonRouter()
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
  orders.value.filter((o) => ['confirmed', 'preparing'].includes(o.status)).reduce((s, o) => s + o.quantity, 0),
)

async function load() {
  error.value = null
  try {
    const [q, s] = await Promise.all([listQueue(date.value), getStock()])
    orders.value = q
    stock.value = s
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
  else ionRouter.push(`/dispatcher/orders/${order.id}`)
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

      <div class="af-container wide">
        <PageHeader
          crumb="Dispatcher"
          title="Order queue"
          :subtitle="`${friendlyDay(date)} · ${counts.pending ?? 0} pending · ${toPrepare} containers to prepare`"
        >
          <template #actions>
            <SegmentedControl v-model="day" :options="dayOptions" label="Delivery day" />
          </template>
        </PageHeader>

        <!-- Stock strip -->
        <section v-if="stock" class="af-card stock">
          <WaterLevelBar
            label="Ready stock promised to orders"
            :value="stock.reserved"
            :max="Math.max(stock.filled_ready, 1)"
            :note="stock.available > 0 ? `${stock.available} filled containers free to confirm new orders` : 'No free stock. Fill more containers before confirming.'"
          />
          <AppButton variant="secondary" size="sm" @click="ionRouter.navigate('/dispatcher/stock', 'root', 'replace')">Manage stock</AppButton>
        </section>

        <!-- Tabs + search -->
        <div class="tools">
          <div class="tabs" role="tablist" aria-label="Order status">
            <button
              v-for="t in TABS"
              :key="t.key"
              type="button"
              role="tab"
              class="tab"
              :aria-selected="tab === t.key"
              @click="tab = t.key"
            >
              {{ t.label }} <span class="tab__n">{{ counts[t.key] ?? 0 }}</span>
            </button>
          </div>
          <label class="search">
            <span class="af-sr-only">Search orders</span>
            <input v-model="search" type="search" placeholder="Search name, code, barangay" />
          </label>
        </div>

        <div v-if="loading" class="af-card"><SkeletonList :rows="5" /></div>

        <div v-else-if="error" class="af-card err" role="alert">
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
          <div v-else class="af-card">
            <EmptyState
              :title="search ? 'No matching orders' : `No ${TABS.find((t) => t.key === tab).label.toLowerCase()} orders`"
              :message="search ? 'Try another name, code or barangay.' : `Nothing here for ${friendlyDay(date).toLowerCase()}.`"
            />
          </div>

          <aside v-if="wide" class="af-card detail" aria-label="Selected order">
            <OrderAdminPanel v-if="selectedId" :order-id="selectedId" @changed="load" />
            <p v-else class="af-small">Select an order to see its details.</p>
          </aside>
        </div>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.wide { max-width: 1320px; gap: var(--af-s4); }
.stock { display: flex; align-items: center; gap: var(--af-s5); padding: var(--af-s4) var(--af-s5); flex-wrap: wrap; }
.stock > :first-child { flex: 1; min-width: 240px; }

.tools { display: flex; gap: var(--af-s3); align-items: center; flex-wrap: wrap; justify-content: space-between; }
.tabs { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 2px; max-width: 100%; min-width: 0; scrollbar-width: none; }
.tab {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 14px;
  border-radius: var(--af-r-pill);
  border: 1.5px solid var(--af-line);
  background: var(--af-surface);
  color: var(--af-ink-2);
  font: 700 14px var(--af-font);
  cursor: pointer;
}
.tab[aria-selected='true'] { border-color: var(--af-navy); background: var(--af-navy); color: #fff; }
.tab__n { min-width: 22px; padding: 1px 7px; border-radius: var(--af-r-pill); background: var(--af-surface-2); color: var(--af-ink); font-size: 12px; font-variant-numeric: tabular-nums; }
.tab[aria-selected='true'] .tab__n { background: rgba(255, 255, 255, 0.18); color: #fff; }
.search input {
  width: min(320px, 100%);
  min-height: 44px;
  padding: 0 14px;
  border-radius: var(--af-r-sm);
  border: 1.5px solid var(--af-line);
  background: var(--af-surface);
  color: var(--af-ink);
  font: 500 15px var(--af-font);
}
.search input:focus { outline: none; border-color: var(--af-primary); box-shadow: 0 0 0 3px var(--af-primary-tint); }
.search { flex: 1 1 220px; display: flex; justify-content: flex-end; }

.split { display: grid; gap: var(--af-s4); }
.split--wide { grid-template-columns: minmax(360px, 440px) minmax(0, 1fr); align-items: start; }
.list { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--af-s2); }
.detail { position: sticky; top: var(--af-s4); }

.err { display: grid; gap: var(--af-s2); justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }

@media (max-width: 640px) {
  .search { justify-content: stretch; }
  .search input { width: 100%; }
}
</style>
