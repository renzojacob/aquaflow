<!-- My orders: Active and Past lists. -->
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
import OrderListItem from '@/components/order/OrderListItem.vue'
import SegmentedControl from '@/components/form/SegmentedControl.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import { listOrders } from '@/services/customerService'

const ionRouter = useIonRouter()

const scope = ref('active')
const orders = ref([])
const loading = ref(true)
const error = ref(null)

const options = [
  { value: 'active', label: 'Active' },
  { value: 'past', label: 'Past' },
]

async function load() {
  loading.value = true
  error.value = null
  try {
    orders.value = await listOrders(scope.value)
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

onIonViewWillEnter(load)
watch(scope, load)

async function refresh(ev) {
  await load()
  ev.target.complete()
}

const empty = computed(() =>
  scope.value === 'active'
    ? { title: 'No active orders', message: 'Orders you place show up here until they are delivered.', action: 'Order water' }
    : { title: 'No past orders yet', message: 'Delivered and cancelled orders will appear here.', action: '' },
)
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

      <div class="af-container narrow">
        <SegmentedControl v-model="scope" :options="options" label="Which orders" block />

        <div v-if="loading" class="af-card"><SkeletonList :rows="4" /></div>

        <div v-else-if="error" class="af-card err" role="alert">
          <b>Couldn't load your orders</b>
          <p>{{ error.message }}</p>
          <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>

        <div v-else-if="!orders.length" class="af-card">
          <EmptyState :title="empty.title" :message="empty.message" :action-label="empty.action" @action="ionRouter.push('/customer/order')" />
        </div>

        <ul v-else class="list" :aria-label="`${scope} orders`">
          <li v-for="o in orders" :key="o.id">
            <OrderListItem :order="o" @open="ionRouter.push(`/customer/orders/${o.id}`)" />
          </li>
        </ul>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.narrow { max-width: 720px; gap: var(--af-s4); }
.list { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--af-s3); }
.err { display: grid; gap: var(--af-s2); justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }
</style>
