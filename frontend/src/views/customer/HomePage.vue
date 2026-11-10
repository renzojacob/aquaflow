<!--
  Customer home: a dashboard of their own water.
  Tank hero (water = how far the current order has come, or containers at home),
  shortcuts, this month's numbers, spending chart, containers, recent activity, delivery windows.
  Every number comes from the customer's real orders and the station's real settings.
-->
<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
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
import { useRoute } from 'vue-router'
import {
  addCircleOutline,
  callOutline,
  calendarOutline,
  checkmarkDoneOutline,
  cubeOutline,
  locationOutline,
  partlySunnyOutline,
  receiptOutline,
  refreshOutline,
  sunnyOutline,
  walletOutline,
  waterOutline,
} from 'ionicons/icons'

import ActivityFeed from '@/components/dash/ActivityFeed.vue'
import RefillForecast from '@/components/dash/RefillForecast.vue'
import AppButton from '@/components/ui/AppButton.vue'
import BarChart from '@/components/viz/BarChart.vue'
import KpiTile from '@/components/dash/KpiTile.vue'
import LiquidFill from '@/components/ui/LiquidFill.vue'
import QuickAction from '@/components/dash/QuickAction.vue'
import RingGauge from '@/components/viz/RingGauge.vue'
import SectionHead from '@/components/dash/SectionHead.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import StatusTracker from '@/components/order/StatusTracker.vue'
import TankHero from '@/components/dash/TankHero.vue'
import { ORDER_FLOW, isActive, riderOf } from '@/constants/orderStatus'
import { cartShort, refillsOf, reorderQuery } from '@/constants/cart'
import { useCountUp } from '@/composables/useCountUp'
import { getCustomerSummary, getOrderSettings, listAddresses, listAllOrders, periodOpen, trackOrder } from '@/services/customerService'
import { getRefillCards, reorderRefill } from '@/services/refillService'
import { showToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import { PERIODS, clockLabel, containers, dateISO, duration, friendlyDay, greeting, peso } from '@/utils/format'
import { activityFeed, orderStats } from '@/utils/orderStats'

const auth = useAuthStore()
const ionRouter = useIonRouter()
const route = useRoute()

const loading = ref(true)
const error = ref(null)
const summary = ref(null)
const orders = ref([])
const settings = ref(null)
const addresses = ref([])
const refill = ref([]) // Feature C: one card per household

// ticks once a minute so "closes in 40 min" stays true
const now = ref(new Date())
let timer = null
onMounted(() => (timer = setInterval(() => (now.value = new Date()), 60_000)))
onBeforeUnmount(() => {
  clearInterval(timer)
  clearInterval(etaTimer)
})

// While the order in the tank is on the road: ask where the rider is every 10 s
const eta = ref(null)
let etaTimer = null
async function refreshEta() {
  if (hero.value?.status !== 'out_for_delivery') return (eta.value = null)
  try {
    eta.value = await trackOrder(hero.value.id)
  } catch {
    /* keep the last one */
  }
}
onMounted(() => (etaTimer = setInterval(refreshEta, 10_000)))

const firstName = computed(() => auth.user?.full_name?.split(' ')[0] ?? '')

async function load() {
  error.value = null
  try {
    const [s, all, st, a, r] = await Promise.all([
      getCustomerSummary(),
      listAllOrders(),
      getOrderSettings(),
      listAddresses(),
      getRefillCards().catch(() => []), // the prediction is a bonus: never block the home screen on it
    ])
    refill.value = r
    summary.value = s
    orders.value = all
    refreshEta()
    settings.value = st
    addresses.value = a
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

// ---------- the order in the tank ----------
const active = computed(() => orders.value.filter(isActive))
const hero = computed(() => active.value[0] ?? null)
const others = computed(() => active.value.slice(1))
const step = (o) => Math.max(0, ORDER_FLOW.indexOf(o.status === 'failed_delivery' ? 'ready_for_pickup' : o.status))
const held = computed(() => summary.value?.containers_held ?? 0)

const tankLevel = computed(() => (hero.value ? (step(hero.value) + 1) / ORDER_FLOW.length : Math.min(1, held.value / 6)))
const tankLabel = computed(() =>
  hero.value
    ? `Order progress: step ${step(hero.value) + 1} of ${ORDER_FLOW.length}`
    : `${containers(held.value)} at home`,
)

const HEADLINE = {
  pending: 'Sent to the station',
  confirmed: 'Confirmed by the station',
  preparing: 'Your containers are being filled',
  ready_for_pickup: 'Loaded and ready to go',
  failed_delivery: 'We missed you this time',
}
const headline = computed(() => {
  const o = hero.value
  if (!o) return held.value ? `${containers(held.value)} at home` : 'No water at home yet'
  if (o.status === 'out_for_delivery') {
    const r = riderOf(o)
    return r ? `${r.name.split(' ')[0]} is on the way` : 'On the way to you'
  }
  return HEADLINE[o.status] ?? 'In progress'
})
const rider = computed(() => (hero.value ? riderOf(hero.value) : null))
const showCode = computed(() => hero.value && hero.value.status !== 'pending')

// ---------- numbers ----------
const stats = computed(() => orderStats(orders.value))
const feed = computed(() =>
  activityFeed(orders.value, 6).map((e) => ({ ...e, lead: e.text, strong: e.code, tail: `· ${e.short}`, to: true })),
)
const spentShown = useCountUp(() => stats.value.thisMonth.spent)
const lastDelivered = computed(() => summary.value?.last_delivered ?? null)
const defaultAddress = computed(() => addresses.value.find((a) => a.is_default) ?? addresses.value[0] ?? null)

// ---------- delivery windows (from the station's real cutoff times) ----------
const windows = computed(() => {
  if (!settings.value) return []
  const today = dateISO(0)
  return Object.entries(PERIODS).map(([key, p]) => {
    const open = periodOpen(settings.value, today, key, now.value)
    const [h, m] = settings.value.cutoff[key].split(':').map(Number)
    const left = h * 60 + m - (now.value.getHours() * 60 + now.value.getMinutes())
    return {
      key,
      ...p,
      icon: key === 'morning' ? sunnyOutline : partlySunnyOutline,
      open,
      cutoff: clockLabel(settings.value.cutoff[key]),
      note: open ? (left <= 90 ? `Order in the next ${duration(left)}` : `Order before ${clockLabel(settings.value.cutoff[key])}`) : 'Closed for today',
    }
  })
})
const nextWindow = computed(() => {
  const w = windows.value.find((x) => x.open)
  return w ? `${w.label} today, ${w.hours}` : `Tomorrow morning, ${PERIODS.morning.hours}`
})

// ---------- Feature C: never run out ----------
// The reminder email links to /customer/home?reorder=<prediction id>: put that household first and highlight it.
const fromReminder = computed(() => (route.query.reorder != null ? String(route.query.reorder) : null))
const refillMain = computed(() => refill.value.find((c) => fromReminder.value && String(c.prediction_id) === fromReminder.value) ?? refill.value[0] ?? null)
const refillOthers = computed(() => refill.value.filter((c) => c !== refillMain.value))
const reordering = ref(false)
async function reorderNow(card) {
  reordering.value = true
  try {
    const order = await reorderRefill(card)
    showToast(`Ordered ${containers(card.reorder.quantity)}. The station will confirm it soon.`, 'success')
    if (fromReminder.value) ionRouter.replace('/customer/home')
    await load()
    go(`/customer/orders/${order.id}`)
  } catch (e) {
    showToast(e.message, 'danger')
    load()
  } finally {
    reordering.value = false
  }
}
const customizeRefill = (card) => go(`/customer/order?qty=${card.reorder.quantity}&address=${card.address.id}`)

// ---------- navigation ----------
const go = (path) => ionRouter.push(path)
function reorder() {
  const o = lastDelivered.value
  go(`/customer/order?${reorderQuery(o)}`)
}
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-title>Home</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content>
      <ion-refresher slot="fixed" @ion-refresh="refresh">
        <ion-refresher-content />
      </ion-refresher>

      <div class="af-container af-dash home">
        <p class="hello">{{ greeting() }}, <b>{{ firstName }}</b></p>

        <div v-if="loading" class="af-panel"><SkeletonList :rows="4" /></div>

        <div v-else-if="error" class="af-panel err" role="alert">
          <b>Couldn't load your home screen</b>
          <p>{{ error.message }}</p>
          <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>

        <template v-else>
          <!-- ===== Tank + shortcuts ===== -->
          <div class="af-bento af-bento--stretch">
            <TankHero class="b-8" :level="tankLevel" :label="tankLabel">
              <div class="t-top">
                <StatusPill v-if="hero" :status="hero.status" />
                <span v-else class="t-chip"><ion-icon :icon="waterOutline" aria-hidden="true" /> Your water</span>
                <span v-if="hero" class="t-code">{{ hero.code }}</span>
              </div>

              <div class="t-main">
                <h1 class="t-title">{{ headline }}</h1>
                <p v-if="eta?.eta_minutes != null" class="t-eta">
                  <template v-if="!eta.stops_before && eta.distance_m < 60">Your rider is at your door</template>
                  <template v-else>{{ eta.stops_before ? `${eta.stops_before} stop${eta.stops_before > 1 ? 's' : ''} before you. ` : '' }}About {{ duration(eta.eta_minutes) }} away</template>
                </p>
                <p v-if="hero" class="t-sub tank__soft">
                  {{ cartShort(hero) }} for {{ friendlyDay(hero.delivery_date).toLowerCase() }}, {{ PERIODS[hero.period].label.toLowerCase() }}
                  ({{ PERIODS[hero.period].hours }}) to {{ hero.address.label }}
                </p>
                <p v-else class="t-sub tank__soft">
                  The next delivery window is {{ nextWindow.toLowerCase() }}. Hand your empties to the rider when it arrives.
                </p>
              </div>

              <StatusTracker v-if="hero" :order="hero" class="t-tracker" />

              <div v-if="hero" class="t-foot">
                <div v-if="showCode" class="t-codebox">
                  <span class="tank__soft">Give this code to the rider</span>
                  <span class="t-digits" :aria-label="`Delivery code ${String(hero.delivery_code).split('').join(' ')}`">
                    <span v-for="(d, i) in String(hero.delivery_code).split('')" :key="i" aria-hidden="true">{{ d }}</span>
                  </span>
                </div>
                <div v-if="rider && hero.status === 'out_for_delivery'" class="t-rider">
                  <span class="t-avatar" aria-hidden="true">{{ rider.name.split(' ').map((p) => p[0]).slice(0, 2).join('') }}</span>
                  <span><b>{{ rider.name }}</b><span class="tank__soft">Your rider</span></span>
                  <a v-if="rider.phone" class="t-call" :href="`tel:${rider.phone}`" :aria-label="`Call ${rider.name}`"><ion-icon :icon="callOutline" /></a>
                </div>
                <AppButton variant="secondary" @click="go(`/customer/orders/${hero.id}`)">Track order</AppButton>
              </div>
              <div v-else class="t-foot">
                <AppButton size="lg" @click="go('/customer/order')">Order water</AppButton>
                <AppButton v-if="lastDelivered" variant="secondary" size="lg" @click="reorder">Order the same again</AppButton>
              </div>
            </TankHero>

            <section class="b-4 actions" aria-label="Shortcuts">
              <QuickAction primary :icon="addCircleOutline" title="Order water" :detail="`Next: ${nextWindow}`" @click="go('/customer/order')" />
              <QuickAction
                v-if="lastDelivered"
                :icon="refreshOutline"
                title="Order the same"
                :detail="`${cartShort(lastDelivered)} to ${lastDelivered.address.label}, ${peso(lastDelivered.total)}`"
                tone="sun"
                @click="reorder"
              />
              <QuickAction :icon="receiptOutline" title="My orders" :detail="active.length ? `${active.length} in progress` : `${stats.allTime.orders} so far`" @click="go('/customer/orders')" />
              <QuickAction
                :icon="locationOutline"
                title="Addresses"
                :detail="defaultAddress ? `${defaultAddress.label}, ${defaultAddress.barangay}` : 'Add where we deliver'"
                tone="pearl"
                @click="go('/customer/profile')"
              />
            </section>
          </div>

          <!-- ===== Feature C: when you'll run out ===== -->
          <RefillForecast
            v-if="refillMain"
            :card="refillMain"
            :others="refillOthers"
            :highlight="fromReminder != null && String(refillMain.prediction_id) === fromReminder"
            :busy="reordering"
            @reorder="reorderNow"
            @customize="customizeRefill"
            @track="(id) => go(`/customer/orders/${id}`)"
            @settings="go('/customer/profile')"
          />

          <!-- Other orders in progress -->
          <section v-if="others.length" class="others" aria-label="Other orders in progress">
            <button v-for="o in others" :key="o.id" type="button" class="other" @click="go(`/customer/orders/${o.id}`)">
              <LiquidFill shape="orb" :size="40" :level="(step(o) + 1) / ORDER_FLOW.length" :text="refillsOf(o) || o.quantity" />
              <span><b>{{ o.code }}</b> {{ friendlyDay(o.delivery_date) }}, {{ PERIODS[o.period].label }}</span>
              <StatusPill :status="o.status" />
            </button>
          </section>

          <!-- ===== This month ===== -->
          <div class="kpis">
            <KpiTile label="Spent this month" :value="peso(spentShown)" tone="sun" :icon="walletOutline" :hint="`${peso(stats.allTime.spent)} since you joined`" :spark="stats.months.map((m) => m.spent)" />
            <KpiTile label="Orders this month" :value="stats.thisMonth.count" :icon="calendarOutline" :hint="`${stats.thisMonth.delivered} delivered`" :spark="stats.months.map((m) => m.count)" />
            <KpiTile label="Containers at home" :value="held" :icon="cubeOutline" hint="Hand empties to the rider" />
            <KpiTile
              label="Deliveries so far"
              :value="stats.allTime.delivered"
              tone="pearl"
              :icon="checkmarkDoneOutline"
              :hint="stats.everyDays ? `About every ${stats.everyDays} days` : `${containers(stats.allTime.containers)} in total`"
            />
          </div>

          <!-- ===== Spending + containers ===== -->
          <div class="af-bento af-bento--stretch">
            <section class="af-panel b-7" aria-labelledby="spend-title">
              <SectionHead title="Spending by month" :sub="`${peso(stats.allTime.spent)} on ${containers(stats.allTime.containers)} since you joined`" />
              <BarChart :bars="stats.months.map((m) => ({ label: m.label, sub: m.sub, value: m.spent }))" :format="peso" tone="sun" title="Spending by month" :height="210" />
            </section>

            <section class="af-panel b-5 jar" aria-labelledby="jar-title">
              <SectionHead title="Your containers" sub="AquaFlow containers you're keeping" />
              <div class="jar__row">
                <RingGauge
                  :value="stats.allTime.containers ? stats.allTime.returned / stats.allTime.containers : 0"
                  :size="124"
                  tone="pearl"
                  :label="`${stats.allTime.returned} of ${stats.allTime.containers} delivered containers returned as empties`"
                >
                  <b class="jar__n">{{ held }}</b>
                  <span class="jar__u">at home</span>
                </RingGauge>
                <dl class="jar__facts">
                  <div class="af-inset"><dt>Delivered to you</dt><dd>{{ stats.allTime.containers }}</dd></div>
                  <div class="af-inset"><dt>Empties returned</dt><dd>{{ stats.allTime.returned }}</dd></div>
                </dl>
              </div>
              <p class="af-small">The ring shows how many delivered containers came back as empties. Returning them keeps refills quick.</p>
            </section>
          </div>

          <!-- ===== Activity + windows ===== -->
          <div class="af-bento af-bento--stretch">
            <section class="af-panel b-7" aria-labelledby="feed-title">
              <SectionHead title="Recent activity" action="All orders" @action="go('/customer/orders')" />
              <ActivityFeed :items="feed" empty="Your orders will show up here." @open="(it) => go(`/customer/orders/${it.orderId}`)" />
            </section>

            <section class="af-panel b-5" aria-labelledby="win-title">
              <SectionHead title="Delivery today" :sub="settings?.station?.name" />
              <ul class="wins">
                <li v-for="w in windows" :key="w.key" class="win" :class="{ 'win--closed': !w.open }">
                  <span class="win__icon" aria-hidden="true"><ion-icon :icon="w.icon" /></span>
                  <span class="win__text">
                    <b>{{ w.label }}</b>
                    <span>{{ w.hours }}</span>
                  </span>
                  <span class="win__state">{{ w.note }}</span>
                </li>
              </ul>
              <div class="price af-inset">
                <span>One 5-gallon refill</span>
                <b class="af-money">{{ peso(settings?.price_per_container) }}</b>
              </div>
              <p class="af-small">Delivered within {{ settings?.service_radius_km }} km of {{ settings?.station?.address || 'the station' }}. Pay cash when it arrives.</p>
            </section>
          </div>
        </template>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.hello { margin: 4px 0 0; font-size: 17px; font-weight: 600; color: var(--af-ink-2); }
.hello b { color: var(--af-ink); font-weight: 800; }

/* ---------- tank content ---------- */
.t-top { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.t-chip { display: inline-flex; align-items: center; gap: 6px; padding: 7px 12px; border-radius: var(--af-r-pill); background: var(--af-surface-2); font-size: 13px; font-weight: 750; }
.t-code { font-size: 13px; font-weight: 750; color: var(--af-on-deep-soft); font-variant-numeric: tabular-nums; }
.t-main { display: grid; gap: 10px; max-width: 34ch; }
.t-title {
  margin: 0;
  font-family: var(--af-display);
  font-size: clamp(30px, 4.4vw, 50px);
  line-height: 1.02;
  font-weight: 650;
  letter-spacing: -0.045em;
  text-wrap: balance;
}
.t-sub { margin: 0; font-size: 15.5px; line-height: 1.55; font-weight: 550; }
.t-eta { margin: 0; justify-self: start; padding: 8px 14px; border-radius: var(--af-r-pill); background: rgba(var(--af-deep-rgb), 0.5); color: var(--af-glow-c-hi); font-size: 15px; font-weight: 750; }
.t-tracker { padding: 14px 8px 10px; border-radius: 20px; background: rgba(var(--af-deep-rgb), 0.38); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); }
.t-tracker :deep(.af-tracker__label) { color: var(--af-on-deep-soft); }
.t-tracker :deep(.is-done .af-tracker__label) { color: var(--af-on-deep); }
.t-tracker :deep(.is-now .af-tracker__label) { color: var(--af-glow-c-hi); }
.t-foot { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-top: auto; }
.t-codebox { display: grid; gap: 6px; padding: 10px 14px; border-radius: 18px; background: rgba(var(--af-deep-rgb), 0.42); }
.t-codebox > span:first-child { font-size: 12.5px; font-weight: 700; }
.t-digits { display: flex; gap: 6px; }
.t-digits span {
  width: 38px;
  height: 46px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  font-family: var(--af-display);
  font-size: 24px;
  font-weight: 650;
  color: var(--af-glow-c-hi);
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(var(--af-glow-rgb), 0.3);
  text-shadow: 0 0 14px rgba(var(--af-glow-rgb), 0.6);
}
.t-rider { display: flex; align-items: center; gap: 10px; padding: 8px; border-radius: 18px; background: rgba(var(--af-deep-rgb), 0.42); }
.t-rider > span:nth-child(2) { display: grid; line-height: 1.25; }
.t-rider b { font-size: 14.5px; }
.t-rider .tank__soft { font-size: 12.5px; font-weight: 650; }
.t-avatar { width: 40px; height: 40px; display: grid; place-items: center; border-radius: 50%; background: linear-gradient(140deg, var(--af-accent-on-deep), var(--af-glow-c)); color: var(--af-on-glow); font-weight: 800; font-size: 14px; }
.t-call { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 50%; background: var(--af-glow-c); color: var(--af-on-glow); font-size: 19px; }

/* ---------- shortcuts ---------- */
.actions { display: grid; gap: 12px; align-content: start; }

.others { display: grid; gap: 10px; }
.other {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 14px;
  padding: 10px 14px;
  border-radius: 20px;
  border: 1px solid var(--af-line);
  background: var(--af-surface);
  color: var(--af-ink);
  font: 600 14px var(--af-font);
  text-align: left;
  cursor: pointer;
}
.other b { font-weight: 800; margin-right: 6px; }

/* ---------- KPIs: 2 per row on phones, 4 on desktop ---------- */
.kpis { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
@media (min-width: 1000px) { .kpis { grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; } }

/* ---------- containers ---------- */
.jar__row { display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
.jar__n { font-family: var(--af-display); font-size: 34px; font-weight: 700; letter-spacing: -0.04em; line-height: 1; }
.jar__u { font-size: 12px; font-weight: 700; color: var(--af-ink-2); }
.jar__facts { flex: 1; min-width: 150px; display: grid; gap: 10px; margin: 0; }
.jar__facts dt { font-size: 12.5px; font-weight: 700; color: var(--af-ink-2); }
.jar__facts dd { margin: 0; font-family: var(--af-display); font-size: 22px; font-weight: 650; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
.jar p { margin: 0; }

/* ---------- delivery windows ---------- */
.wins { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.win { display: grid; grid-template-columns: 40px 1fr auto; gap: 12px; align-items: center; padding: 10px 12px; border-radius: 16px; background: var(--af-surface-2); }
.win__icon { width: 40px; height: 40px; display: grid; place-items: center; border-radius: 12px; background: var(--af-sun-tint); color: var(--af-sun); font-size: 20px; }
.win__text { display: grid; line-height: 1.3; }
.win__text b { font-size: 15px; font-weight: 800; }
.win__text span { font-size: 13px; font-weight: 600; color: var(--af-ink-2); }
.win__state { font-size: 13px; font-weight: 750; color: var(--af-success); text-align: right; }
.win--closed .win__icon { background: var(--af-surface-3); color: var(--af-ink-2); }
.win--closed .win__state { color: var(--af-ink-2); }
.price { grid-template-columns: 1fr auto; align-items: center; }
.price span { font-size: 14px; font-weight: 700; }
.price b { font-family: var(--af-display); font-size: 22px; font-weight: 650; }

.err { justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }

@media (max-width: 560px) {
  .t-foot > :deep(.af-btn) { flex: 1 1 100%; }
  .t-digits span { width: 34px; height: 42px; font-size: 21px; }
}
</style>
