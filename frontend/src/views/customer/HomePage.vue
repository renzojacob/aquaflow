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
import EmptyState from '@/components/ui/EmptyState.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { ORDER_FLOW } from '@/constants/orderStatus'
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

      <div class="af-container">
        <header class="hello">
          <p class="af-small">{{ today }}</p>
          <h1 class="af-h1">{{ greeting() }}, {{ firstName }}</h1>
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

            <article v-for="o in summary.active_orders" :key="o.id" class="hero">
              <div class="hero__top">
                <div>
                  <p class="hero__code">{{ o.code }}</p>
                  <p class="hero__qty">{{ containers(o.quantity) }}</p>
                  <p class="hero__when">{{ friendlyDay(o.delivery_date) }} · {{ PERIODS[o.period].label }} ({{ PERIODS[o.period].hours }})</p>
                </div>
                <StatusPill :status="o.status" />
              </div>

              <div class="progress" role="img" :aria-label="`Step ${stepIndex(o) + 1} of ${ORDER_FLOW.length}`">
                <span v-for="(s, i) in ORDER_FLOW" :key="s" :class="{ on: i <= stepIndex(o) }"></span>
              </div>

              <p v-if="o.status === 'out_for_delivery' && o.trip" class="hero__note">
                {{ o.trip.rider_name.split(' ')[0] }} is
                {{ o.trip.stops_before === 0 ? 'heading to you now' : `${o.trip.stops_before} stop${o.trip.stops_before > 1 ? 's' : ''} away` }}.
                Your delivery code is <span class="af-code code">{{ o.delivery_code }}</span>
              </p>
              <p v-else-if="o.status === 'failed_delivery'" class="hero__note hero__note--warn">
                We couldn't deliver this time. The station will send it on the next trip.
              </p>

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
              <span class="af-metric">{{ summary.containers_held }}</span>
              <p class="af-small">AquaFlow containers you have now. Hand empties to the rider when your refill arrives.</p>
            </div>

            <div v-if="summary.last_delivered" class="af-card tile">
              <span class="af-caption">Order again</span>
              <p class="again">
                {{ containers(summary.last_delivered.quantity) }} to
                <b>{{ summary.last_delivered.address.label }}</b>
                <span class="af-small"> · {{ peso(summary.last_delivered.total) }}</span>
              </p>
              <AppButton block @click="reorder">Order the same</AppButton>
            </div>
          </section>
        </template>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.hello { display: grid; gap: 2px; }
.hello p, .hello h1 { margin: 0; }
.stack { display: grid; gap: var(--af-s3); }
.stack h2 { margin: 0; }

.hero {
  display: grid;
  gap: var(--af-s4);
  padding: var(--af-s5);
  border-radius: var(--af-r-lg);
  background: var(--af-surface);
  border: 1px solid var(--af-line);
  box-shadow: var(--af-shadow-2);
}
.hero__top { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--af-s3); flex-wrap: wrap; }
.hero__top p { margin: 0; }
.hero__code { font-size: 13px; font-weight: 700; color: var(--af-ink-2); }
.hero__qty { font-size: 28px; font-weight: 800; letter-spacing: -0.02em; }
.hero__when { font-size: 14px; color: var(--af-ink-2); }
.hero__note { margin: 0; font-size: 14px; line-height: 1.6; }
.hero__note--warn { color: var(--af-amber-fg); font-weight: 600; }
.code {
  display: inline-block;
  padding: 2px 8px 2px 12px;
  border-radius: 8px;
  background: var(--af-primary-tint);
  color: var(--af-primary);
  font-size: 15px;
}

.progress { display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px; }
.progress span { height: 8px; border-radius: var(--af-r-pill); background: var(--af-surface-2); }
.progress span.on { background: linear-gradient(180deg, var(--af-water), var(--af-water-deep)); }

.duo { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--af-s4); }
.tile { display: grid; gap: var(--af-s2); align-content: start; }
.tile p { margin: 0; }
.again { font-size: 17px; margin-bottom: var(--af-s2) !important; }

.err { display: grid; gap: var(--af-s2); justify-items: start; border-color: color-mix(in srgb, var(--af-danger) 40%, transparent); }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }

@media (max-width: 640px) {
  .duo { grid-template-columns: 1fr; }
}
</style>
