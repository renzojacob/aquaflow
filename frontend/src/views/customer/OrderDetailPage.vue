<!--
  One order. While it's in progress: a tank (water = progress) with the status in words,
  the tracker, the delivery code and the rider. Beside it: the map, the receipt, the address.
  Below: the full history. Cancel (early) or order again (after delivery).
-->
<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  IonBackButton,
  IonButtons,
  IonContent,
  IonHeader,
  IonIcon,
  IonPage,
  IonTitle,
  IonToolbar,
  alertController,
  onIonViewWillEnter,
  onIonViewWillLeave,
  useIonRouter,
} from '@ionic/vue'
import { cashOutline, chatboxEllipsesOutline, locationOutline, refreshOutline, timeOutline } from 'ionicons/icons'

import AppButton from '@/components/ui/AppButton.vue'
import LiveMap from '@/components/map/LiveMap.vue'
import MapPicker from '@/components/map/MapPicker.vue'
import OrderTimeline from '@/components/order/OrderTimeline.vue'
import RiderCard from '@/components/order/RiderCard.vue'
import SectionHead from '@/components/dash/SectionHead.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import StatusTracker from '@/components/order/StatusTracker.vue'
import TankHero from '@/components/dash/TankHero.vue'
import { CUSTOMER_CANCELLABLE, ORDER_FLOW, isActive, riderOf } from '@/constants/orderStatus'
import { showToast } from '@/composables/useToast'
import { cancelOrder, getOrder, getOrderSettings, trackOrder } from '@/services/customerService'
import { PERIODS, ago, containers, dateTimeOf, duration, friendlyDay, peso } from '@/utils/format'

const route = useRoute()
const ionRouter = useIonRouter()

const order = ref(null)
const settings = ref(null)
const loading = ref(true)
const error = ref(null)
const cancelling = ref(false)

async function load() {
  loading.value = !order.value
  error.value = null
  try {
    const [o, s] = await Promise.all([getOrder(route.params.id), settings.value ?? getOrderSettings()])
    order.value = o
    settings.value = s
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
const rider = computed(() => (order.value ? riderOf(order.value) : null))

// ---------- live tracking (while out for delivery) ----------
const track = ref(null)
let poll = null
async function pollTrack() {
  try {
    const t = await trackOrder(order.value.id)
    track.value = t
    // the rider may have delivered it meanwhile: reload the order once
    if (t.status !== 'out_for_delivery' && order.value.status === 'out_for_delivery') await load()
  } catch {
    /* keep the last known position; try again on the next tick */
  }
}
function stopTrack() {
  clearInterval(poll)
  poll = null
}
function syncTracking() {
  stopTrack()
  if (order.value?.status === 'out_for_delivery') {
    pollTrack()
    poll = setInterval(pollTrack, 5000)
  } else track.value = null
}
watch(() => order.value?.status, syncTracking)
// Ionic keeps this page alive when you leave it: restart tracking every time it is shown
onIonViewWillEnter(() => {
  if (order.value) syncTracking()
})
onIonViewWillLeave(stopTrack)
onBeforeUnmount(stopTrack)
const live = computed(() => track.value?.location ?? null)
const etaLine = computed(() => {
  const t = track.value
  if (!t || t.eta_minutes == null) return ''
  if (!t.stops_before && t.distance_m < 60) return 'Your rider is at your door.'
  const before = t.stops_before ? `${t.stops_before} stop${t.stops_before > 1 ? 's' : ''} before you. ` : ''
  return `${before}About ${duration(t.eta_minutes)} away, ${(t.distance_m / 1000).toFixed(1)} km.`
})
const step = computed(() =>
  order.value ? Math.max(0, ORDER_FLOW.indexOf(order.value.status === 'failed_delivery' ? 'ready_for_pickup' : order.value.status)) : 0,
)

const SENTENCE = {
  pending: ['Sent to the station', 'They usually confirm within a few minutes.'],
  confirmed: ['Confirmed', 'Your containers are reserved and will be filled soon.'],
  preparing: ['Being filled', 'Your containers are being washed and filled now.'],
  ready_for_pickup: ['Loaded and ready', 'It leaves with the next delivery trip.'],
  out_for_delivery: ['On the way', 'Have your empties and the code ready.'],
  delivered: ['Delivered', 'Thank you for ordering with AquaFlow.'],
  failed_delivery: ['We missed you', 'The station will send it on the next trip.'],
  cancelled: ['Cancelled', ''],
  rejected: ['Not accepted', ''],
}
const words = computed(() => SENTENCE[order.value?.status] ?? ['', ''])
const endReason = computed(() => {
  const o = order.value
  if (!o) return ''
  if (o.status === 'rejected') return o.rejection_reason || o.history.at(-1)?.note || ''
  if (o.status === 'cancelled') return o.cancel_reason || o.history.at(-1)?.note || ''
  return ''
})
const deliveredAt = computed(() => order.value?.history.findLast?.((h) => h.status === 'delivered')?.at ?? null)

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

const again = () => ionRouter.push(`/customer/order?qty=${order.value.quantity}&address=${order.value.address.id}`)
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
      <div class="af-container af-dash">
        <div v-if="loading" class="af-panel"><SkeletonList :rows="5" :avatar="false" /></div>

        <div v-else-if="error" class="af-panel err" role="alert">
          <b>{{ error.kind === 'not_found' ? 'Order not found' : "Couldn't load this order" }}</b>
          <p>{{ error.message }}</p>
          <AppButton v-if="error.kind !== 'not_found'" variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>

        <template v-else-if="order">
          <div class="af-bento af-bento--stretch">
            <!-- Left: the tank (in progress) or a summary header (finished) -->
            <TankHero
              v-if="active"
              class="b-7"
              :level="(step + 1) / ORDER_FLOW.length"
              :label="`Step ${step + 1} of ${ORDER_FLOW.length}`"
              :tone="order.status === 'failed_delivery' ? 'warn' : 'water'"
            >
              <div class="t-top">
                <StatusPill :status="order.status" />
                <span class="t-code">{{ order.code }}</span>
              </div>
              <div class="t-main">
                <h1 class="t-title">{{ words[0] }}</h1>
                <p v-if="etaLine" class="t-eta">{{ etaLine }}</p>
                <p class="tank__soft t-sub">{{ words[1] }}</p>
              </div>
              <StatusTracker :order="order" class="t-tracker" />
              <div v-if="showCode" class="t-codebox">
                <span class="tank__soft">Delivery code. Give it to the rider when the water arrives.</span>
                <span class="t-digits" :aria-label="`Delivery code ${String(order.delivery_code).split('').join(' ')}`">
                  <span v-for="(d, i) in String(order.delivery_code).split('')" :key="i" aria-hidden="true">{{ d }}</span>
                </span>
              </div>
            </TankHero>

            <section v-else class="b-7 done af-panel" :class="`done--${order.status}`">
              <div class="t-top">
                <StatusPill :status="order.status" />
                <span class="af-small">{{ order.code }}</span>
              </div>
              <h1 class="done__title">{{ words[0] }}</h1>
              <p v-if="order.status === 'delivered'" class="done__sub">
                {{ containers(order.quantity) }} delivered to {{ order.address.label }}<template v-if="deliveredAt"> on {{ dateTimeOf(deliveredAt) }}</template>.
              </p>
              <p v-else-if="endReason" class="done__sub">Reason: {{ endReason }}</p>
              <div class="done__actions">
                <AppButton size="lg" @click="again"><ion-icon :icon="refreshOutline" aria-hidden="true" /> Order this again</AppButton>
              </div>
            </section>

            <!-- Right: map + rider -->
            <div class="b-5 side">
              <RiderCard v-if="rider && ['out_for_delivery', 'delivered', 'failed_delivery'].includes(order.status)" :rider="rider" :status="order.status" />
              <div class="mapcard">
                <LiveMap
                  v-if="order.status === 'out_for_delivery'"
                  :station="track?.station ?? settings?.station"
                  :stops="[{ id: order.id, lat: order.address.lat, lng: order.address.lng, mine: true }]"
                  :rider="live && live.fresh ? live : null"
                  height="100%"
                  :label="`Live map: your rider and your address. ${etaLine}`"
                />
                <MapPicker v-else :model-value="order.address" :station="settings?.station" readonly height="100%" :zoom="14" />
                <div v-if="order.status === 'out_for_delivery'" class="mapcard__live" role="status">
                  <span class="mapcard__dot" :class="{ 'is-off': !live?.fresh, 'is-sim': live?.is_simulated }" aria-hidden="true"></span>
                  <template v-if="live?.fresh">{{ live.is_simulated ? 'Demo drive' : 'Live' }}, updated {{ ago(live.at) }}</template>
                  <template v-else>Waiting for the rider's location</template>
                </div>
                <div class="mapcard__label">
                  <ion-icon :icon="locationOutline" aria-hidden="true" />
                  <span><b>{{ order.address.label }}</b> {{ order.address.street }}, {{ order.address.barangay }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="af-bento af-bento--stretch">
            <!-- Receipt -->
            <section class="af-panel b-4" aria-labelledby="r-title">
              <SectionHead title="Receipt" :sub="`Placed ${dateTimeOf(order.created_at)}`" />
              <dl class="lines">
                <div><dt>{{ order.quantity }} × 5-gallon refill</dt><dd>{{ peso(order.unit_price * order.quantity) }}</dd></div>
                <div><dt>Delivery</dt><dd>Free</dd></div>
                <div><dt>Empties to hand back</dt><dd>{{ order.empties_to_return }}</dd></div>
              </dl>
              <hr class="af-hairline" />
              <div class="total"><span>Total</span><b class="af-money">{{ peso(order.total) }}</b></div>
              <div class="af-inset pay">
                <ion-icon :icon="cashOutline" aria-hidden="true" />
                <span>{{ order.status === 'delivered' ? 'Paid in cash on delivery' : 'Pay cash to the rider' }}</span>
              </div>
            </section>

            <!-- Delivery details -->
            <section class="af-panel b-4" aria-labelledby="d-title">
              <SectionHead title="Delivery" />
              <div class="detail">
                <span class="detail__icon" aria-hidden="true"><ion-icon :icon="timeOutline" /></span>
                <span><b>{{ friendlyDay(order.delivery_date) }}, {{ PERIODS[order.period].label.toLowerCase() }}</b><span>{{ PERIODS[order.period].hours }}</span></span>
              </div>
              <div class="detail">
                <span class="detail__icon" aria-hidden="true"><ion-icon :icon="locationOutline" /></span>
                <span><b>{{ order.address.label }}</b><span>{{ order.address.street }}, {{ order.address.barangay }}</span><i v-if="order.address.landmark">{{ order.address.landmark }}</i></span>
              </div>
              <div v-if="order.notes" class="detail">
                <span class="detail__icon" aria-hidden="true"><ion-icon :icon="chatboxEllipsesOutline" /></span>
                <span><b>Your note</b><span>{{ order.notes }}</span></span>
              </div>
              <div v-if="canCancel" class="cancel">
                <AppButton variant="danger" block :loading="cancelling" @click="askCancel">Cancel order</AppButton>
                <p class="af-small">You can cancel until the station starts filling your containers.</p>
              </div>
            </section>

            <!-- History -->
            <section class="af-panel b-4" aria-labelledby="h-title">
              <SectionHead title="History" />
              <OrderTimeline :order="order" />
            </section>
          </div>
        </template>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
/* ---------- tank content ---------- */
.t-top { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.t-code { font-size: 13px; font-weight: 750; color: #cfe6ea; }
.t-main { display: grid; gap: 8px; }
.t-title { margin: 0; font-family: var(--af-display); font-size: clamp(32px, 4.6vw, 54px); font-weight: 650; letter-spacing: -0.045em; line-height: 1; }
.t-sub { margin: 0; font-size: 15.5px; font-weight: 550; line-height: 1.5; max-width: 40ch; }
.t-tracker { padding: 14px 8px 10px; border-radius: 20px; background: rgba(2, 18, 26, 0.38); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); }
.t-tracker :deep(.af-tracker__label) { color: #cfe6ea; }
.t-tracker :deep(.is-done .af-tracker__label) { color: #e6f4f6; }
.t-tracker :deep(.is-now .af-tracker__label) { color: #7ff0e4; }
.t-codebox { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; padding: 12px 14px; border-radius: 18px; background: rgba(2, 18, 26, 0.42); }
.t-codebox > span:first-child { font-size: 13px; font-weight: 650; max-width: 26ch; line-height: 1.4; }
.t-digits { display: flex; gap: 6px; }
.t-digits span { width: 42px; height: 52px; display: grid; place-items: center; border-radius: 13px; font-family: var(--af-display); font-size: 26px; font-weight: 650; color: #7ff0e4; background: rgba(255, 255, 255, 0.07); border: 1px solid rgba(127, 240, 228, 0.3); text-shadow: 0 0 14px rgba(79, 224, 210, 0.6); }

/* ---------- finished order header ---------- */
.done { align-content: start; gap: 14px; }
.done__title { margin: 0; font-family: var(--af-display); font-size: clamp(30px, 4vw, 46px); font-weight: 650; letter-spacing: -0.045em; line-height: 1; }
.done__sub { margin: 0; font-size: 15.5px; line-height: 1.5; color: var(--af-ink-2); font-weight: 550; }
.done--delivered { background: linear-gradient(160deg, color-mix(in srgb, var(--af-success) 14%, transparent), transparent 60%), var(--af-surface); }
.done--cancelled, .done--rejected { background: linear-gradient(160deg, var(--af-danger-tint), transparent 60%), var(--af-surface); }
.done__actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 6px; }

/* ---------- map + rider ---------- */
.side { display: grid; gap: 14px; grid-template-rows: auto 1fr; min-height: 300px; }
.mapcard { position: relative; min-height: 240px; border-radius: 28px; overflow: hidden; border: 1px solid var(--af-line); }
.mapcard :deep(.af-map-wrap) { position: absolute; inset: 0; height: 100% !important; border: 0; border-radius: 0; }
.mapcard__label { position: absolute; left: 12px; right: 12px; bottom: 12px; z-index: 500; display: flex; align-items: center; gap: 8px; padding: 10px 14px; border-radius: 16px; background: color-mix(in srgb, var(--af-surface-solid) 92%, transparent); backdrop-filter: blur(10px); font-size: 13.5px; font-weight: 550; box-shadow: var(--af-shadow-2); }
.mapcard__label ion-icon { color: var(--af-primary); font-size: 18px; flex: none; }
.mapcard :deep(.lm) { position: absolute; inset: 0; height: 100% !important; }
.mapcard__live { position: absolute; top: 12px; right: 12px; z-index: 500; display: inline-flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 999px; background: color-mix(in srgb, var(--af-surface-solid) 92%, transparent); box-shadow: var(--af-shadow-2); font-size: 13px; font-weight: 750; }
.mapcard__dot { width: 9px; height: 9px; border-radius: 50%; background: var(--af-success); box-shadow: 0 0 0 4px color-mix(in srgb, var(--af-success) 25%, transparent); }
.mapcard__dot.is-sim { background: var(--af-pearl); box-shadow: 0 0 0 4px color-mix(in srgb, var(--af-pearl) 25%, transparent); }
.mapcard__dot.is-off { background: var(--af-ink-2); box-shadow: none; }
.t-eta { margin: 0; justify-self: start; padding: 8px 14px; border-radius: 999px; background: rgba(2, 18, 26, 0.5); color: #7ff0e4; font-size: 15px; font-weight: 750; }
.mapcard__label span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mapcard__label b { margin-right: 4px; }

/* ---------- receipt + details ---------- */
.lines { margin: 0; display: grid; gap: 10px; }
.lines div { display: flex; justify-content: space-between; gap: 12px; font-size: 14.5px; }
.lines dt { color: var(--af-ink-2); font-weight: 600; }
.lines dd { margin: 0; font-weight: 750; font-variant-numeric: tabular-nums; }
.total { display: flex; justify-content: space-between; align-items: baseline; }
.total span { font-weight: 800; }
.total b { font-family: var(--af-display); font-size: 32px; font-weight: 650; letter-spacing: -0.04em; }
.pay { grid-template-columns: auto 1fr; align-items: center; gap: 10px; font-size: 14px; font-weight: 650; }
.pay ion-icon { font-size: 20px; color: var(--af-sun); }

.detail { display: grid; grid-template-columns: 38px 1fr; gap: 12px; align-items: start; }
.detail__icon { width: 38px; height: 38px; display: grid; place-items: center; border-radius: 12px; background: var(--af-primary-tint); color: var(--af-primary); font-size: 18px; }
.detail > span:last-child { display: grid; gap: 2px; font-size: 14px; line-height: 1.45; padding-top: 2px; }
.detail b { font-weight: 800; }
.detail span span, .detail i { color: var(--af-ink-2); }
.cancel { display: grid; gap: 8px; margin-top: 4px; }
.cancel p { margin: 0; text-align: center; }

.err { justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }

@media (max-width: 560px) {
  .t-digits span { width: 36px; height: 46px; font-size: 22px; }
}
</style>
