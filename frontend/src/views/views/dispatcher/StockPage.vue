<!-- Stock: ready containers, what's promised, refill batches and count corrections. -->
<script setup>
import { reactive, ref } from 'vue'
import { IonContent, IonHeader, IonPage, IonTitle, IonToolbar, onIonViewWillEnter } from '@ionic/vue'

import AppButton from '@/components/ui/AppButton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import QuantityStepper from '@/components/form/QuantityStepper.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import StatCard from '@/components/ui/StatCard.vue'
import TextField from '@/components/form/TextField.vue'
import WaterLevelBar from '@/components/ui/WaterLevelBar.vue'
import { showToast } from '@/composables/useToast'
import { adjustStock, getStock } from '@/services/dispatcherService'
import { dateTimeOf } from '@/utils/format'

const stock = ref(null)
const loading = ref(true)
const error = ref(null)

const refill = reactive({ quantity: 10, reason: '', busy: false, error: '' })
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

async function saveRefill() {
  refill.busy = true
  refill.error = ''
  try {
    stock.value = await adjustStock({ type: 'refill', quantity: refill.quantity, reason: refill.reason })
    showToast(`${refill.quantity} filled containers added`, 'success')
    refill.reason = ''
  } catch (e) {
    refill.error = e.message
  } finally {
    refill.busy = false
  }
}

async function saveCount() {
  count.error = ''
  if (count.quantity === '' || Number.isNaN(Number(count.quantity))) {
    count.error = 'Enter the number you counted.'
    return
  }
  count.busy = true
  try {
    stock.value = await adjustStock({ type: 'correction', quantity: Number(count.quantity), reason: count.reason })
    showToast('Stock count corrected', 'success')
    count.quantity = ''
    count.reason = ''
  } catch (e) {
    count.error = e.message
  } finally {
    count.busy = false
  }
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
      <div class="af-container wide">
        <PageHeader crumb="Dispatcher" title="Stock" subtitle="Filled 5-gallon containers ready to go out" />

        <div v-if="loading" class="af-card"><SkeletonList :rows="4" :avatar="false" /></div>

        <div v-else-if="error" class="af-card err" role="alert">
          <b>Couldn't load stock</b>
          <p>{{ error.message }}</p>
          <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>

        <template v-else-if="stock">
          <div class="stats">
            <StatCard label="Filled & ready" :value="stock.filled_ready" unit="containers" />
            <StatCard label="Promised to orders" :value="stock.reserved" unit="containers" delta="Confirmed, preparing, ready" />
            <StatCard
              label="Free to confirm"
              :value="stock.available"
              unit="containers"
              :tone="stock.available <= 5 ? 'warn' : 'neutral'"
              :delta="stock.available <= 5 ? 'Running low: fill more soon' : 'Can be promised to new orders'"
            />
            <StatCard label="Empties at station" :value="stock.empty_at_station" unit="containers" delta="Waiting to be washed and filled" />
          </div>

          <section class="af-card">
            <WaterLevelBar label="Ready stock promised to orders" :value="stock.reserved" :max="Math.max(stock.filled_ready, 1)" size="lg" />
          </section>

          <div class="forms">
            <!-- Refill -->
            <form class="af-card form" novalidate @submit.prevent="saveRefill">
              <h2 class="af-h3">Record a refill batch</h2>
              <p class="af-small">Empties you washed and filled. Moves them from "empties" to "filled & ready".</p>
              <QuantityStepper v-model="refill.quantity" :min="1" :max="Math.max(stock.empty_at_station, 1)" label="Containers filled" unit="filled" />
              <TextField v-model="refill.reason" label="Note" placeholder="Afternoon batch" />
              <p v-if="refill.error" class="form__err" role="alert">{{ refill.error }}</p>
              <AppButton type="submit" :loading="refill.busy" :disabled="stock.empty_at_station === 0">Add to ready stock</AppButton>
            </form>

            <!-- Correction -->
            <form class="af-card form" novalidate @submit.prevent="saveCount">
              <h2 class="af-h3">Correct the count</h2>
              <p class="af-small">After a physical count. Enter how many filled containers are really on hand.</p>
              <TextField v-model="count.quantity" label="Filled containers counted" type="number" inputmode="numeric" required />
              <TextField v-model="count.reason" label="Reason" required placeholder="Two containers cracked" />
              <p v-if="count.error" class="form__err" role="alert">{{ count.error }}</p>
              <AppButton type="submit" variant="secondary" :loading="count.busy">Save count</AppButton>
            </form>
          </div>

          <!-- History -->
          <section class="af-card">
            <h2 class="af-h3 hist-title">Stock history</h2>
            <p v-if="!stock.log.length" class="af-small">No changes yet.</p>
            <ul v-else class="log">
              <li v-for="(l, i) in stock.log" :key="i">
                <span class="log__delta" :class="l.delta >= 0 ? 'log__delta--up' : 'log__delta--down'">
                  {{ l.delta >= 0 ? '+' : '−' }}{{ Math.abs(l.delta) }}
                </span>
                <span class="log__text">
                  <b>{{ l.type === 'refill' ? 'Refill batch' : 'Count correction' }}</b>
                  <span>{{ l.reason }} · {{ l.by }} · {{ dateTimeOf(l.at) }}</span>
                </span>
              </li>
            </ul>
          </section>
        </template>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.wide { max-width: 1180px; gap: var(--af-s4); }
.stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--af-s4); }
.forms { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--af-s4); }
.form { display: grid; gap: var(--af-s3); align-content: start; justify-items: start; }
.form > :deep(.af-field) { width: 100%; }
.form h2, .form p { margin: 0; }
.form__err { color: var(--af-danger); font-weight: 600; font-size: 14px; }
.hist-title { margin: 0 0 var(--af-s3); }
.log { list-style: none; margin: 0; padding: 0; display: grid; }
.log li { display: grid; grid-template-columns: 56px 1fr; gap: var(--af-s3); align-items: center; padding: var(--af-s3) 0; border-top: 1px solid var(--af-line); }
.log li:first-child { border-top: 0; }
.log__delta { font-weight: 800; font-size: 18px; font-variant-numeric: tabular-nums; text-align: right; }
.log__delta--up { color: var(--af-success); }
.log__delta--down { color: var(--af-danger); }
.log__text { display: grid; gap: 2px; min-width: 0; }
.log__text span { font-size: 13px; color: var(--af-ink-2); }
.err { display: grid; gap: var(--af-s2); justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }

@media (max-width: 900px) {
  .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .forms { grid-template-columns: 1fr; }
}
@media (max-width: 480px) {
  .stats { grid-template-columns: 1fr; }
}
</style>
