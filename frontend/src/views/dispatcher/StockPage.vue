<!--
  Stock: the station as a tank (water = filled containers among everything at the station),
  where every container is right now, and the three things staff record:
  refill batches, new containers received, and count corrections. Then the full history.
-->
<script setup>
import { computed, reactive, ref } from 'vue'
import { IonContent, IonHeader, IonIcon, IonPage, IonTitle, IonToolbar, onIonViewWillEnter } from '@ionic/vue'
import {
  arrowForwardOutline,
  bicycleOutline,
  businessOutline,
  homeOutline,
  refreshCircleOutline,
  waterOutline,
} from 'ionicons/icons'

import AppButton from '@/components/ui/AppButton.vue'
import QuantityStepper from '@/components/form/QuantityStepper.vue'
import SectionHead from '@/components/dash/SectionHead.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import TankHero from '@/components/dash/TankHero.vue'
import TextField from '@/components/form/TextField.vue'
import WaterLevelBar from '@/components/ui/WaterLevelBar.vue'
import { showToast } from '@/composables/useToast'
import { adjustStock, getStock } from '@/services/dispatcherService'
import { ago, containers } from '@/utils/format'

const stock = ref(null)
const loading = ref(true)
const error = ref(null)
const tab = ref('refill')

const refill = reactive({ quantity: 10, reason: '', busy: false, error: '' })
const receive = reactive({ quantity: 10, reason: '', busy: false, error: '' })
const count = reactive({ quantity: '', reason: '', busy: false, error: '' })

async function load() {
  error.value = null
  try {
    stock.value = await getStock()
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
onIonViewWillEnter(load)

async function save(form, payload, done) {
  form.busy = true
  form.error = ''
  try {
    stock.value = await adjustStock(payload)
    showToast(done, 'success')
    form.reason = ''
    if ('quantity' in form && payload.type === 'correction') form.quantity = ''
  } catch (e) {
    form.error = e.message
  } finally {
    form.busy = false
  }
}
const saveRefill = () => save(refill, { type: 'refill', quantity: refill.quantity, reason: refill.reason }, `${containers(refill.quantity)} added to ready stock`)
const saveReceive = () => save(receive, { type: 'receive', quantity: receive.quantity, reason: receive.reason }, `${containers(receive.quantity)} received`)
function saveCount() {
  count.error = ''
  if (count.quantity === '' || Number.isNaN(Number(count.quantity))) {
    count.error = 'Enter the number you counted.'
    return
  }
  save(count, { type: 'correction', quantity: Number(count.quantity), reason: count.reason }, 'Stock count corrected')
}

// ---------- where every container is ----------
const atStation = computed(() => (stock.value ? stock.value.filled_ready + stock.value.empty_at_station : 0))
const tankLevel = computed(() => (atStation.value ? stock.value.filled_ready / atStation.value : 0))
const flow = computed(() => {
  const s = stock.value
  if (!s) return []
  return [
    { key: 'filled', label: 'Filled at the station', n: s.filled_ready, icon: waterOutline, note: `${s.available} free, ${s.reserved} promised` },
    { key: 'road', label: 'On the road', n: s.on_road ?? 0, icon: bicycleOutline, note: 'Out with riders now' },
    { key: 'home', label: 'With customers', n: s.with_customers ?? 0, icon: homeOutline, note: 'In homes and stores' },
    { key: 'empty', label: 'Empties at the station', n: s.empty_at_station, icon: refreshCircleOutline, note: 'Waiting to be washed' },
  ]
})
const share = (n) => (stock.value?.owned_total ? Math.round((n / stock.value.owned_total) * 100) : 0)

const LOG = {
  refill: { label: 'Refill batch', tone: 'water' },
  correction: { label: 'Count correction', tone: 'warn' },
  receive: { label: 'New containers', tone: 'pearl' },
  reserve: { label: 'Promised to an order', tone: 'muted' },
  release: { label: 'Released from an order', tone: 'muted' },
  load_out: { label: 'Loaded for delivery', tone: 'muted' },
  return_unsold: { label: 'Came back undelivered', tone: 'warn' },
  empties_in: { label: 'Empties collected', tone: 'pearl' },
}
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-title>Stock</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content>
      <div class="af-container af-dash">
        <div v-if="loading" class="af-panel"><SkeletonList :rows="4" :avatar="false" /></div>

        <div v-else-if="error" class="af-panel err" role="alert">
          <b>Couldn't load stock</b>
          <p>{{ error.message }}</p>
          <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>

        <template v-else-if="stock">
          <div class="af-bento af-bento--stretch">
            <TankHero
              class="b-7"
              :level="tankLevel"
              :tone="stock.available <= 5 ? 'warn' : 'water'"
              :label="`${stock.filled_ready} of ${atStation} containers at the station are filled`"
            >
              <span class="t-kicker">The station right now</span>
              <h1 class="t-title">{{ stock.available }} ready to promise</h1>
              <p class="tank__soft t-sub">
                {{ stock.filled_ready }} filled, {{ stock.reserved }} of them already promised to orders. {{ stock.empty_at_station }} empties waiting to be washed and filled.
              </p>
              <div class="t-bar">
                <WaterLevelBar label="Filled containers promised to orders" :value="stock.reserved" :max="Math.max(stock.filled_ready, 1)" size="lg" />
              </div>
            </TankHero>

            <!-- Record -->
            <section class="af-panel b-5" aria-labelledby="rec-title">
              <SectionHead title="Record a change" />
              <div class="af-chips" role="tablist" aria-label="What happened">
                <button type="button" role="tab" class="af-chip" :aria-selected="tab === 'refill'" @click="tab = 'refill'">Filled empties</button>
                <button type="button" role="tab" class="af-chip" :aria-selected="tab === 'receive'" @click="tab = 'receive'">New containers</button>
                <button type="button" role="tab" class="af-chip" :aria-selected="tab === 'count'" @click="tab = 'count'">Count</button>
              </div>

              <form v-if="tab === 'refill'" class="form" novalidate @submit.prevent="saveRefill">
                <p class="af-small">Empties you washed and filled move to ready stock.</p>
                <QuantityStepper v-model="refill.quantity" :min="1" :max="Math.max(stock.empty_at_station, 1)" label="Containers filled" unit="filled" />
                <TextField v-model="refill.reason" label="Note" placeholder="Afternoon batch" />
                <p v-if="refill.error" class="form__err" role="alert">{{ refill.error }}</p>
                <AppButton type="submit" block :loading="refill.busy" :disabled="stock.empty_at_station === 0">Add {{ containers(refill.quantity) }} to ready stock</AppButton>
              </form>

              <form v-else-if="tab === 'receive'" class="form" novalidate @submit.prevent="saveReceive">
                <p class="af-small">Brand-new empty containers the station bought. They join the empties.</p>
                <QuantityStepper v-model="receive.quantity" :min="1" :max="500" label="New containers received" unit="received" />
                <TextField v-model="receive.reason" label="Note" placeholder="From the supplier in Calapan" />
                <p v-if="receive.error" class="form__err" role="alert">{{ receive.error }}</p>
                <AppButton type="submit" block :loading="receive.busy">Add {{ containers(receive.quantity) }}</AppButton>
              </form>

              <form v-else class="form" novalidate @submit.prevent="saveCount">
                <p class="af-small">After a physical count: how many filled containers are really on hand?</p>
                <TextField v-model="count.quantity" label="Filled containers counted" type="number" inputmode="numeric" required />
                <TextField v-model="count.reason" label="Why it changed" required placeholder="Two containers cracked" />
                <p v-if="count.error" class="form__err" role="alert">{{ count.error }}</p>
                <AppButton type="submit" variant="secondary" block :loading="count.busy">Save count</AppButton>
              </form>
            </section>
          </div>

          <!-- Where every container is -->
          <section class="af-panel" aria-labelledby="flow-title">
            <SectionHead title="Where every container is" :sub="`${containers(stock.owned_total)} owned by the station`" />
            <ol class="flow">
              <li v-for="(f, i) in flow" :key="f.key" class="flow__step" :class="`flow--${f.key}`">
                <span class="flow__icon" aria-hidden="true"><ion-icon :icon="f.icon" /></span>
                <b class="flow__n">{{ f.n }}</b>
                <span class="flow__label">{{ f.label }}</span>
                <span class="flow__note">{{ f.note }}</span>
                <span class="flow__bar" aria-hidden="true"><i :style="{ width: `${share(f.n)}%` }"></i></span>
                <span class="flow__pct">{{ share(f.n) }}% of all containers</span>
                <ion-icon v-if="i < flow.length - 1" :icon="arrowForwardOutline" class="flow__arrow" aria-hidden="true" />
              </li>
            </ol>
            <p class="af-small loop"><ion-icon :icon="businessOutline" aria-hidden="true" /> Containers go around: filled at the station, delivered, kept by customers, then handed back as empties to be filled again.</p>
          </section>

          <!-- History -->
          <section class="af-panel" aria-labelledby="hist-title">
            <SectionHead title="Stock history" :sub="stock.log.length ? `Last ${stock.log.length} changes` : ''" />
            <p v-if="!stock.log.length" class="af-small">No changes yet.</p>
            <ul v-else class="log">
              <li v-for="(l, i) in stock.log" :key="i" :class="`log--${LOG[l.type]?.tone ?? 'muted'}`">
                <span class="log__delta">{{ l.delta >= 0 ? '+' : '−' }}{{ Math.abs(l.delta) }}</span>
                <span class="log__text">
                  <b>{{ LOG[l.type]?.label ?? l.type }}</b>
                  <span>{{ [l.reason, l.by].filter(Boolean).join(', ') }}</span>
                </span>
                <time class="log__time" :datetime="l.at">{{ ago(l.at) }}</time>
              </li>
            </ul>
          </section>
        </template>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
/* ---------- tank ---------- */
.t-kicker { font-size: 14px; font-weight: 750; color: #cfe6ea; }
.t-title { margin: 0; font-family: var(--af-display); font-size: clamp(30px, 4.4vw, 52px); font-weight: 650; letter-spacing: -0.045em; line-height: 1; max-width: 14ch; }
.t-sub { margin: 0; font-size: 15px; line-height: 1.55; font-weight: 550; max-width: 46ch; }
.t-bar { margin-top: auto; padding: 14px 16px; border-radius: 18px; background: rgba(2, 18, 26, 0.42); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
.t-bar :deep(*) { --af-ink-2: #cfe6ea; }

/* ---------- record ---------- */
.form { display: grid; gap: 14px; }
.form p { margin: 0; }
.form :deep(.af-step) { justify-content: center; }
.form__err { padding: 10px 14px; border-radius: 12px; background: var(--af-danger-tint); color: var(--af-danger); font-size: 14px; font-weight: 650; }

/* ---------- flow ---------- */
.flow { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.flow__step { position: relative; display: grid; gap: 6px; align-content: start; padding: 16px; border-radius: 20px; background: var(--af-surface-2); min-width: 0; }
.flow__icon { width: 38px; height: 38px; display: grid; place-items: center; border-radius: 12px; background: var(--t); color: var(--c); font-size: 19px; }
.flow__n { font-family: var(--af-display); font-size: 32px; font-weight: 650; letter-spacing: -0.04em; line-height: 1; font-variant-numeric: tabular-nums; }
.flow__label { font-size: 14px; font-weight: 800; }
.flow__note, .flow__pct { font-size: 12.5px; font-weight: 600; color: var(--af-ink-2); }
.flow__bar { height: 6px; border-radius: 6px; background: var(--af-surface-3); overflow: hidden; margin-top: 4px; }
.flow__bar i { display: block; height: 100%; border-radius: inherit; background: var(--c); }
.flow__arrow { position: absolute; right: -11px; top: 26px; z-index: 1; width: 14px; height: 14px; padding: 2px; border-radius: 50%; background: var(--af-surface-solid); color: var(--af-ink-2); }
.flow--filled { --c: var(--af-primary); --t: var(--af-primary-tint); }
.flow--road { --c: var(--af-pearl); --t: var(--af-pearl-tint); }
.flow--home { --c: var(--af-sun); --t: var(--af-sun-tint); }
.flow--empty { --c: var(--af-ink-2); --t: var(--af-surface-3); }
.loop { margin: 0; display: flex; gap: 8px; align-items: flex-start; }
.loop ion-icon { flex: none; font-size: 18px; margin-top: 1px; }

/* ---------- history ---------- */
.log { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }
.log li { display: grid; grid-template-columns: 58px minmax(0, 1fr) auto; gap: 12px; align-items: center; padding: 10px 6px; border-bottom: 1px solid var(--af-line); }
.log li:last-child { border-bottom: 0; }
.log__delta { justify-self: start; min-width: 48px; padding: 6px 8px; border-radius: 10px; background: var(--t); color: var(--c); font-family: var(--af-display); font-size: 14px; font-weight: 650; text-align: center; font-variant-numeric: tabular-nums; }
.log__text { display: grid; gap: 2px; min-width: 0; }
.log__text b { font-size: 14.5px; font-weight: 800; }
.log__text span { font-size: 13px; color: var(--af-ink-2); font-weight: 550; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.log__time { font-size: 12.5px; font-weight: 650; color: var(--af-ink-2); white-space: nowrap; }
.log--water { --c: var(--af-primary); --t: var(--af-primary-tint); }
.log--warn { --c: var(--af-amber-fg); --t: var(--af-amber-tint); }
.log--pearl { --c: var(--af-pearl); --t: var(--af-pearl-tint); }
.log--muted { --c: var(--af-ink-2); --t: var(--af-surface-2); }

.err { justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }

@media (max-width: 900px) {
  .flow { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .flow__arrow { display: none; }
}
</style>
