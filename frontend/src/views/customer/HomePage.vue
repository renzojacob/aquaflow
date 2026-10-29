<!-- Customer home: active orders, containers at home, quick re-order. -->
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
import CausticLayer from '@/components/ui/CausticLayer.vue'
import LiquidFill from '@/components/ui/LiquidFill.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { ORDER_FLOW, ORDER_STATUS } from '@/constants/orderStatus'
import { getCustomerSummary } from '@/services/customerService'
import { useAuthStore } from '@/stores/auth'
import { PERIODS, containers, friendlyDay, greeting, peso } from '@/utils/format'

const auth = useAuthStore()
const ionRouter = useIonRouter()

const loading = ref(true)
const error = ref(null)
const summary = ref(null)

const firstName = computed(() => auth.user?.full_name.split(' ')[0] ?? '')
const today = new Date().toLocaleDateString('en-PH', { weekday: 'long', month: 'long', day: 'numeric' })

async function load() {
  error.value = null
  try {
    summary.value = await getCustomerSummary()
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

// Ionic keeps pages alive between tabs, so reload every time the page is shown
onIonViewWillEnter(load)

async function refresh(ev) {
  await load()
  ev.target.complete()
}

/** How far along the happy path the order is (0..5) */
const stepIndex = (o) => Math.max(0, ORDER_FLOW.indexOf(o.status === 'failed_delivery' ? 'ready_for_pickup' : o.status))

function reorder() {
  const o = summary.value.last_delivered
  ionRouter.push(`/customer/order?qty=${o.quantity}&address=${o.address.id}`)
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

      <div class="af-container home">
        <header class="hello">
          <p class="af-caption">{{ today }}</p>
          <h1 class="af-h1">{{ greeting() }}, <span class="hello__name">{{ firstName }}</span></h1>
        </header>

        <!-- Loading -->
        <div v-if="loading" class="af-card"><SkeletonList :rows="3" /></div>

        <!-- Error -->
        <div v-else-if="error" class="af-card err" role="alert">
          <b>Couldn't load your orders</b>
          <p>{{ error.message }}</p>
          <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>

        <template v-else-if="summary">
          <!-- Active orders -->
          <section aria-labelledby="active-title" class="stack">
            <h2 id="active-title" class="af-caption">On the way</h2>

            <article v-for="o in summary.active_orders" :key="o.id" class="hero af-hero-surface af-glow-edge af-deep-scope">
              <CausticLayer />
              <div class="hero__top">
                <StatusPill :status="o.status" />
                <span class="hero__code">{{ o.code }}</span>
              </div>

              <div class="hero__body">
                <div class="hero__info">
                  <div class="hero__qty">
                    <span class="hero__n af-shimmer">{{ o.quantity }}</span>
                    <span class="hero__unit">
                      {{ o.quantity === 1 ? 'container' : 'containers' }}
                      <small>{{ friendlyDay(o.delivery_date) }} · {{ PERIODS[o.period].label }}</small>
                      <small>{{ PERIODS[o.period].hours }}</small>
                    </span>
                  </div>
                  <span class="af-sr-only">{{ containers(o.quantity) }}</span>

                  <div class="progress-wrap">
                    <div class="progress" role="img" :aria-label="`Step ${stepIndex(o) + 1} of ${ORDER_FLOW.length}`">
                      <span
                        v-for="(s, i) in ORDER_FLOW"
                        :key="s"
                        :class="{ on: i <= stepIndex(o), now: i === stepIndex(o) }"
                        :style="{ '--d': `${i * 90}ms` }"
                      ></span>
                    </div>
                    <p class="progress__label" aria-hidden="true">
                      Step {{ stepIndex(o) + 1 }} of {{ ORDER_FLOW.length }} · {{ ORDER_STATUS[ORDER_FLOW[stepIndex(o)]].timeline }}
                    </p>
                  </div>
                </div>

                <!-- The container fills up as the order moves along -->
                <div class="hero__jug">
                  <span class="hero__halo" aria-hidden="true"></span>
                  <LiquidFill :level="(stepIndex(o) + 1) / ORDER_FLOW.length" shape="jug" :size="120" class="hero__jugsvg" />
                </div>
              </div>

              <p v-if="o.status === 'out_for_delivery' && o.trip" class="hero__note">
                {{ o.trip.rider_name.split(' ')[0] }} is
                <b>{{ o.trip.stops_before === 0 ? 'heading to you now' : `${o.trip.stops_before} stop${o.trip.stops_before > 1 ? 's' : ''} away` }}</b>.
                Give this code when your water arrives.
              </p>
              <p v-else-if="o.status === 'failed_delivery'" class="hero__note hero__note--warn">
                We couldn't deliver this time. The station will send it on the next trip.
              </p>

              <div v-if="o.status === 'out_for_delivery' && o.trip" class="hero__codebox">
                <span class="af-caption">Delivery code</span>
                <span class="hero__digits" :aria-label="`Delivery code ${String(o.delivery_code).split('').join(' ')}`">
                  <span v-for="(d, i) in String(o.delivery_code).split('')" :key="i" class="hero__digit" aria-hidden="true" :style="{ '--d': `${300 + i * 80}ms` }">{{ d }}</span>
                </span>
              </div>

              <AppButton variant="secondary" block @click="ionRouter.push(`/customer/orders/${o.id}`)">Track order</AppButton>
            </article>

            <div v-if="!summary.active_orders.length" class="af-card">
              <EmptyState
                title="No active order"
                message="Running low? Order now and we'll deliver this morning or afternoon."
                action-label="Order water"
                @action="ionRouter.push('/customer/order')"
              />
            </div>
          </section>

          <!-- Containers + reorder -->
          <section class="duo">
            <div class="af-card tile">
              <span class="af-caption">Containers at your home</span>
              <div class="tile__row">
                <span class="af-metric">{{ summary.containers_held }}</span>
                <span class="jugs" aria-hidden="true">
                  <LiquidFill v-for="n in Math.min(summary.containers_held, 4)" :key="n" shape="jug" :size="30" :level="0.78" still />
                </span>
              </div>
              <p class="af-small">AquaFlow containers you have now. Hand empties to the rider when your refill arrives.</p>
            </div>

            <div v-if="summary.last_delivered" class="af-card tile">
              <span class="af-caption">Order again</span>
              <p class="again">
                {{ containers(summary.last_delivered.quantity) }} to
                <b>{{ summary.last_delivered.address.label }}</b>
              </p>
              <span class="again__price">{{ peso(summary.last_delivered.total) }}</span>
              <AppButton block @click="reorder">Order the same</AppButton>
            </div>
          </section>
        </template>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.home { max-width: 980px; }
.hello { display: grid; gap: 10px; }
.hello p, .hello h1 { margin: 0; }
.hello h1 { font-size: clamp(28px, 4vw, 40px); }
.hello__name { background: linear-gradient(120deg, var(--af-primary), color-mix(in srgb, var(--af-primary) 55%, #7aa8ff)); -webkit-background-clip: text; background-clip: text; color: transparent; }
.stack { display: grid; gap: var(--af-s3); }
.stack h2 { margin: 0; }

/* ---------- Active order: the deep-water hero ---------- */
.hero { display: grid; gap: var(--af-s5); padding: var(--af-s5); }
.hero__top { display: flex; justify-content: space-between; align-items: center; gap: var(--af-s3); flex-wrap: wrap; }
.hero__code { font-family: var(--af-mono); font-size: 12px; font-weight: 600; letter-spacing: 0.1em; color: var(--af-ink-2); }
.hero__body { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: var(--af-s4); align-items: center; }
.hero__info { display: grid; gap: var(--af-s5); min-width: 0; }
.hero__qty { display: flex; align-items: flex-end; gap: var(--af-s3); }
.hero__n {
  font-family: var(--af-display);
  font-size: 96px;
  line-height: 0.8;
  font-weight: 700;
  letter-spacing: -0.07em;
  font-variant-numeric: tabular-nums;
  filter: drop-shadow(0 0 24px rgba(79, 224, 210, 0.35));
}
:root:not([data-theme='dark']) .hero__n {
  background-image: linear-gradient(100deg, #ffffff 0%, #ffffff 35%, #9ff7ee 50%, #ffffff 65%, #ffffff 100%); /* hero stays deep in light mode */
}
.hero__unit { display: grid; gap: 2px; padding-bottom: 2px; font-size: 18px; font-weight: 800; }
.hero__unit small { font-size: 13px; font-weight: 600; color: var(--af-ink-2); }

.hero__jug { position: relative; display: grid; place-items: center; width: 92px; }
.hero__jugsvg { position: relative; z-index: 1; width: 82px; height: auto; animation: af-bob 6s ease-in-out infinite; filter: drop-shadow(0 16px 24px rgba(0, 0, 0, 0.4)) drop-shadow(0 0 18px rgba(79, 224, 210, 0.35)); }
.hero__halo { position: absolute; inset: -25%; border-radius: 50%; background: radial-gradient(closest-side, rgba(79, 224, 210, 0.3), transparent 70%); }
@keyframes af-bob { 0%, 100% { transform: translateY(0) rotate(-1.5deg); } 50% { transform: translateY(-7px) rotate(1.5deg); } }

.hero__note { margin: 0; font-size: 15px; line-height: 1.55; }
.hero__note b { color: var(--af-primary); }
.hero__note--warn { color: var(--af-amber-fg); font-weight: 650; }

.hero__codebox { display: flex; justify-content: space-between; align-items: center; gap: var(--af-s3); flex-wrap: wrap; }
.hero__digits { display: flex; gap: 8px; }
.hero__digit {
  width: 46px;
  height: 58px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  font-family: var(--af-mono);
  font-size: 28px;
  font-weight: 600;
  color: var(--af-primary);
  text-shadow: 0 0 16px rgba(79, 224, 210, 0.6);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.02));
  border: 1px solid rgba(79, 224, 210, 0.3);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.14), 0 8px 18px rgba(0, 0, 0, 0.25);
  animation: af-digit 520ms var(--af-ease-out) var(--d) both;
}
@keyframes af-digit { from { opacity: 0; transform: translateY(10px) rotateX(60deg); } to { opacity: 1; transform: none; } }

/* Progress: six glowing segments that fill one after another */
.progress-wrap { display: grid; gap: 10px; }
.progress { display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px; }
.progress span { position: relative; height: 6px; border-radius: var(--af-r-pill); background: rgba(255, 255, 255, 0.1); overflow: hidden; }
.progress span.on::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(90deg, #8ff7ec, #4fe0d2);
  transform-origin: left;
  animation: af-seg 480ms var(--af-ease-out) var(--d) both;
}
.progress span.now { box-shadow: 0 0 14px rgba(79, 224, 210, 0.8); }
@keyframes af-seg { from { transform: scaleX(0); } to { transform: scaleX(1); } }
.progress__label { margin: 0; font-size: 13px; font-weight: 650; color: var(--af-ink-2); }

/* ---------- Tiles ---------- */
.duo { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--af-s4); }
.tile { display: grid; gap: var(--af-s3); align-content: start; }
.tile p { margin: 0; }
.tile__row { display: flex; align-items: flex-end; justify-content: space-between; gap: var(--af-s3); }
.jugs { display: flex; gap: 8px; padding-bottom: 4px; }
.again { font-size: 16px; line-height: 1.45; }
.again__price { font-family: var(--af-display); font-size: 32px; font-weight: 700; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; margin-bottom: var(--af-s2); }

.err { display: grid; gap: var(--af-s2); justify-items: start; border-color: color-mix(in srgb, var(--af-danger) 40%, transparent); }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }

@media (min-width: 768px) {
  .hero { padding: var(--af-s6); }
  .hero__n { font-size: 132px; }
  .hero__jug { width: 170px; }
  .hero__jugsvg { width: 150px; }
  .hero__digit { width: 54px; height: 66px; font-size: 32px; }
}
@media (max-width: 380px) {
  .hero__n { font-size: 80px; }
  .hero__jug { width: 76px; }
  .hero__jugsvg { width: 70px; }
  .hero__digit { width: 40px; height: 52px; font-size: 24px; }
}
@media (max-width: 640px) {
  .duo { grid-template-columns: 1fr; }
}
</style>
