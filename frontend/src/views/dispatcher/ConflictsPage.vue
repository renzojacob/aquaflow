<!--
  Dispatcher: Conflicts. Rider actions that synced from an offline phone but clashed with what
  happened on the server meanwhile (Feature B), e.g. a delivery to a customer who had cancelled.
  The server already kept what happened at the door; the dispatcher checks it with the customer
  and writes down what was done.
-->
<script setup>
import { reactive, ref, watch } from 'vue'
import { IonContent, IonHeader, IonIcon, IonPage, IonRefresher, IonRefresherContent, IonTitle, IonToolbar, onIonViewWillEnter } from '@ionic/vue'
import { checkmarkCircleOutline, flagOutline, timeOutline } from 'ionicons/icons'

import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SectionHead from '@/components/dash/SectionHead.vue'
import SegmentedControl from '@/components/form/SegmentedControl.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import TextField from '@/components/form/TextField.vue'
import { showToast } from '@/composables/useToast'
import { listConflicts, resolveConflict } from '@/services/conflictService'
import { ago, peso, timeOf } from '@/utils/format'

const scope = ref('open')
const rows = ref([])
const openCount = ref(0)
const loading = ref(true)
const error = ref(null)
const notes = reactive({})   // conflict id -> note being typed
const busy = ref(null)
const fieldError = reactive({})

async function load() {
  error.value = null
  try {
    const r = await listConflicts(scope.value)
    rows.value = r.conflicts
    openCount.value = r.open_count
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
onIonViewWillEnter(load)
watch(scope, () => { loading.value = true; load() })
async function refresh(ev) {
  await load()
  ev.target.complete()
}

async function resolve(c) {
  fieldError[c.id] = ''
  if (!(notes[c.id] ?? '').trim()) return (fieldError[c.id] = 'Write what was done, e.g. "Customer kept the water and paid."')
  busy.value = c.id
  try {
    await resolveConflict(c.id, notes[c.id].trim())
    showToast(`${c.order?.code ?? 'Conflict'} marked as handled.`, 'success')
    await load()
  } catch (e) {
    fieldError[c.id] = e.message
  } finally {
    busy.value = null
  }
}

const late = (c) => {
  const mins = Math.round((new Date(c.action.server_time) - new Date(c.action.device_time)) / 60000)
  return mins >= 2 ? `${mins} min after it happened` : ''
}
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-title>Conflicts</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content>
      <ion-refresher slot="fixed" @ion-refresh="refresh">
        <ion-refresher-content />
      </ion-refresher>

      <div class="af-container af-dash af-dash--narrow">
        <header class="top">
          <h1 class="title">Conflicts</h1>
          <p class="af-small">Offline deliveries that clashed with a change on the server. What happened at the door is already recorded. Check it and note what you did.</p>
        </header>

        <SegmentedControl v-model="scope" label="Show" :options="[{ value: 'open', label: `Open (${openCount})` }, { value: 'resolved', label: 'Handled' }]" />

        <div v-if="loading" class="af-panel"><SkeletonList :rows="3" /></div>
        <div v-else-if="error" class="af-panel err" role="alert">
          <b>Couldn't load conflicts</b>
          <p>{{ error.message }}</p>
          <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>
        <EmptyState
          v-else-if="!rows.length"
          art="waves"
          :title="scope === 'open' ? 'No conflicts' : 'Nothing handled yet'"
          :message="scope === 'open' ? 'Riders’ offline actions all matched the server.' : 'Conflicts you handle show up here.'"
        />

        <article v-for="c in rows" v-else :key="c.id" class="af-panel card" :class="`card--${c.status}`">
          <div class="card__head">
            <span class="card__icon" aria-hidden="true"><ion-icon :icon="c.status === 'open' ? flagOutline : checkmarkCircleOutline" /></span>
            <div>
              <h2 class="card__title">{{ c.title }}</h2>
              <p class="af-small">
                <template v-if="c.order"><b>{{ c.order.code }}</b> · {{ c.order.customer_name }} · {{ c.order.address }}</template>
              </p>
            </div>
          </div>
          <p class="card__help">{{ c.help }}</p>
          <dl class="facts">
            <div><dt>Rider</dt><dd>{{ c.action.rider.name }}</dd></div>
            <div><dt>Action</dt><dd>{{ c.action.label }}</dd></div>
            <div><dt>On the phone</dt><dd>{{ timeOf(c.action.device_time) }}</dd></div>
            <div><dt>Reached server</dt><dd>{{ timeOf(c.action.server_time) }} <small v-if="late(c)">({{ late(c) }})</small></dd></div>
            <div v-if="c.order"><dt>Order</dt><dd>{{ c.order.containers }} containers · {{ peso(c.order.total) }} · now {{ c.order.status.replace(/_/g, ' ') }}</dd></div>
            <div v-if="c.action.payload.empties_collected != null"><dt>Empties</dt><dd>{{ c.action.payload.empties_collected }} collected</dd></div>
            <div v-if="c.order?.cancel_reason"><dt>Cancel reason</dt><dd>{{ c.order.cancel_reason }}</dd></div>
          </dl>

          <form v-if="c.status === 'open'" class="resolve" novalidate @submit.prevent="resolve(c)">
            <TextField v-model="notes[c.id]" label="What did you do?" required placeholder="e.g. Called the customer, kept the water and paid" :error="fieldError[c.id]" />
            <AppButton type="submit" :loading="busy === c.id">Mark as handled</AppButton>
          </form>
          <p v-else class="done">
            <ion-icon :icon="timeOutline" aria-hidden="true" />
            Handled by {{ c.resolved_by }} {{ ago(c.resolved_at) }}: “{{ c.resolution_note }}”
          </p>
        </article>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.top { display: grid; gap: 6px; }
.top p { margin: 0; }
.title { margin: 0; font-family: var(--af-display); font-size: clamp(26px, 3.4vw, 34px); font-weight: 650; letter-spacing: -0.04em; }
.card { gap: 12px; }
.card__head { display: flex; gap: 12px; align-items: flex-start; }
.card__head p { margin: 2px 0 0; overflow-wrap: anywhere; }
.card__icon { flex: none; width: 40px; height: 40px; display: grid; place-items: center; border-radius: 12px; font-size: 20px; background: var(--af-amber-tint); color: var(--af-amber-fg); }
.card--resolved .card__icon { background: var(--af-success-tint); color: var(--af-success); }
.card__title { margin: 0; font-size: 17px; font-weight: 800; }
.card__help { margin: 0; font-size: 14px; line-height: 1.5; color: var(--af-ink-2); }
.facts { margin: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 8px 16px; }
.facts div { display: grid; gap: 2px; min-width: 0; }
.facts dt { font-size: 12px; font-weight: 700; color: var(--af-ink-2); text-transform: uppercase; letter-spacing: 0.04em; }
.facts dd { margin: 0; font-size: 14px; font-weight: 650; overflow-wrap: anywhere; }
.facts small { color: var(--af-ink-2); font-weight: 600; }
.resolve { display: grid; gap: 10px; }
.done { margin: 0; display: flex; gap: 8px; align-items: flex-start; font-size: 14px; color: var(--af-ink-2); }
.done ion-icon { flex: none; margin-top: 2px; }
.err { justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }
</style>
