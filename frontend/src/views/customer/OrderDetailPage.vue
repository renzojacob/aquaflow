<!-- One order: delivery code, timeline, details, map, cancel. -->
<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  IonBackButton,
  IonButtons,
  IonContent,
  IonHeader,
  IonPage,
  IonTitle,
  IonToolbar,
  alertController,
  onIonViewWillEnter,
} from '@ionic/vue'

import AppButton from '@/components/ui/AppButton.vue'
import MapPicker from '@/components/map/MapPicker.vue'
import OrderTimeline from '@/components/order/OrderTimeline.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { CUSTOMER_CANCELLABLE, isActive } from '@/constants/orderStatus'
import { showToast } from '@/composables/useToast'
import { cancelOrder, getOrder } from '@/services/customerService'
import { PERIODS, containers, dateTimeOf, friendlyDay, peso } from '@/utils/format'

const route = useRoute()

const order = ref(null)
const loading = ref(true)
const error = ref(null)
const cancelling = ref(false)

async function load() {
  loading.value = !order.value
  error.value = null
  try {
    order.value = await getOrder(route.params.id)
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
onIonViewWillEnter(load)

const active = computed(() => order.value && isActive(order.value))
const showCode = computed(() => active.value && order.value.status !== 'pending')
const canCancel = computed(() => order.value && CUSTOMER_CANCELLABLE.includes(order.value.status))

async function askCancel() {
  const alert = await alertController.create({
    header: `Cancel ${order.value.code}?`,
    message: 'The station will not deliver this order.',
    inputs: [{ name: 'reason', type: 'textarea', placeholder: 'Reason (optional)' }],
    buttons: [
      { text: 'Keep order', role: 'cancel' },
      { text: 'Cancel order', role: 'destructive', handler: (data) => doCancel(data?.reason ?? '') },
    ],
  })
  await alert.present()
}

async function doCancel(reason) {
  cancelling.value = true
  try {
    order.value = await cancelOrder(order.value.id, reason)
    showToast(`Order ${order.value.code} cancelled`, 'success')
  } catch (e) {
    showToast(e.message, 'danger')
    await load() // status may have changed meanwhile
  } finally {
    cancelling.value = false
  }
}
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-buttons slot="start">
          <ion-back-button default-href="/customer/orders" text="Orders" />
        </ion-buttons>
        <ion-title>{{ order?.code ?? 'Order' }}</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content>
      <div class="af-container narrow">
        <div v-if="loading" class="af-card"><SkeletonList :rows="5" :avatar="false" /></div>

        <div v-else-if="error" class="af-card err" role="alert">
          <b>{{ error.kind === 'not_found' ? 'Order not found' : "Couldn't load this order" }}</b>
          <p>{{ error.message }}</p>
          <AppButton v-if="error.kind !== 'not_found'" variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>

        <template v-else-if="order">
          <!-- Summary -->
          <header class="head">
            <div>
              <p class="af-small">Placed {{ dateTimeOf(order.created_at) }}</p>
              <h1 class="af-h2">{{ containers(order.quantity) }} · {{ peso(order.total) }}</h1>
            </div>
            <StatusPill :status="order.status" />
          </header>

          <!-- Delivery code -->
          <section v-if="showCode" class="codecard" aria-labelledby="code-title">
            <div>
              <h2 id="code-title" class="af-caption codecard__label">Delivery code</h2>
              <p class="codecard__help">Give this code to the rider when your water arrives. It proves you received it.</p>
            </div>
            <p class="codecard__code af-code" :aria-label="`Delivery code ${order.delivery_code.split('').join(' ')}`">{{ order.delivery_code }}</p>
          </section>

          <p v-if="order.status === 'out_for_delivery' && order.trip" class="notice">
            {{ order.trip.rider_name }} (trip {{ order.trip.code }}) is
            {{ order.trip.stops_before === 0 ? 'heading to you now.' : `${order.trip.stops_before} stop${order.trip.stops_before > 1 ? 's' : ''} away.` }}
          </p>
          <p v-if="order.status === 'failed_delivery' && active" class="notice notice--warn">
            We couldn't deliver on this try. The station will send it on the next trip. Need help? Call the station.
          </p>

          <!-- Timeline -->
          <section class="af-card" aria-labelledby="tl-title">
            <h2 id="tl-title" class="af-h3 sec">Progress</h2>
            <OrderTimeline :order="order" />
          </section>

          <!-- Details -->
          <section class="af-card" aria-labelledby="d-title">
            <h2 id="d-title" class="af-h3 sec">Details</h2>
            <dl class="dl">
              <dt>Containers</dt>
              <dd>{{ containers(order.quantity) }} × {{ peso(order.unit_price) }}</dd>
              <dt>Empties to return</dt>
              <dd>{{ order.empties_to_return }}</dd>
              <dt>When</dt>
              <dd>{{ friendlyDay(order.delivery_date) }}, {{ PERIODS[order.period].label }} ({{ PERIODS[order.period].hours }})</dd>
              <dt>Deliver to</dt>
              <dd>
                <b>{{ order.address.label }}</b><br />
                {{ order.address.street }}, {{ order.address.barangay }}<br />
                <i>{{ order.address.landmark }}</i>
              </dd>
              <template v-if="order.notes">
                <dt>Note</dt>
                <dd>{{ order.notes }}</dd>
              </template>
              <dt>Total</dt>
              <dd><b>{{ peso(order.total) }}</b> · cash on delivery</dd>
            </dl>
            <MapPicker :model-value="order.address" readonly height="200px" :zoom="16" />
          </section>

          <div v-if="canCancel" class="cancel">
            <AppButton variant="danger" block :loading="cancelling" @click="askCancel">Cancel order</AppButton>
            <p class="af-small">You can cancel until the station starts preparing your containers.</p>
          </div>
        </template>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.narrow { max-width: 720px; gap: var(--af-s4); }
.head { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--af-s3); flex-wrap: wrap; }
.head p, .head h1 { margin: 0; }
.sec { margin: 0 0 var(--af-s4); }

.codecard {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--af-s4);
  flex-wrap: wrap;
  padding: var(--af-s5);
  border-radius: var(--af-r-lg);
  background: var(--af-navy);
  color: #fff;
}
.codecard h2, .codecard p { margin: 0; }
.codecard__label { color: #9fd9e0; }
.codecard__help { margin-top: 4px !important; color: #b9c8da; font-size: 14px; max-width: 34ch; }
.codecard__code { font-size: 40px; color: #fff; line-height: 1; }

.notice { margin: 0; padding: 12px 16px; border-radius: var(--af-r-sm); background: var(--af-primary-tint); color: var(--af-primary); font-weight: 600; font-size: 14px; }
.notice--warn { background: var(--af-amber-tint); color: var(--af-amber-fg); }

.dl { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 10px var(--af-s5); margin: 0 0 var(--af-s4); }
.dl dt { font-size: 14px; color: var(--af-ink-2); font-weight: 600; }
.dl dd { margin: 0; font-size: 15px; line-height: 1.5; font-variant-numeric: tabular-nums; }

.cancel { display: grid; gap: var(--af-s2); text-align: center; }
.cancel p { margin: 0; }

.err { display: grid; gap: var(--af-s2); justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }

@media (max-width: 480px) {
  .dl { grid-template-columns: 1fr; gap: 2px; }
  .dl dd { margin-bottom: var(--af-s2); }
}
</style>
