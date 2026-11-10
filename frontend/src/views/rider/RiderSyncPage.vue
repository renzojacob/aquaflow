<!--
  Rider: Sync. What's waiting on this phone, what the server didn't accept (and why), and the
  last actions the server recorded. "Sync now" sends the outbox; it also syncs by itself when
  the signal comes back.
-->
<script setup>
import { computed, ref, watch } from 'vue'
import { IonContent, IonHeader, IonIcon, IonPage, IonRefresher, IonRefresherContent, IonTitle, IonToolbar, onIonViewWillEnter } from '@ionic/vue'
import { alertCircleOutline, checkmarkCircleOutline, cloudOfflineOutline, cloudUploadOutline, copyOutline, flagOutline, timeOutline } from 'ionicons/icons'

import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import RiderSyncBanner from '@/components/rider/RiderSyncBanner.vue'
import SectionHead from '@/components/dash/SectionHead.vue'
import { showToast } from '@/composables/useToast'
import { env } from '@/config/env'
import { discard, listOutbox, syncNow, syncState } from '@/offline/outbox'
import { syncHistory } from '@/services/riderService'
import { ago, timeOf } from '@/utils/format'

const waiting = ref([])
const history = ref([])
const historyError = ref('')

async function load() {
  waiting.value = await listOutbox()
  try {
    history.value = await syncHistory()
    historyError.value = ''
  } catch (e) {
    historyError.value = e.status ? e.message : 'No signal. The list from the server shows when you are back online.'
  }
}
onIonViewWillEnter(load)
watch(() => syncState.version, async () => (waiting.value = await listOutbox()))
watch(() => syncState.lastSyncAt, load)

async function refresh(ev) {
  await sync()
  ev.target.complete()
}

async function sync() {
  const before = syncState.pending + syncState.rejected
  const { reached } = await syncNow()
  await load()
  if (!reached) return showToast("Can't reach the server. Your actions are safe on this phone.", 'warning')
  const left = syncState.pending + syncState.rejected
  if (!before) showToast('Nothing to sync. Everything is on the server.', 'success')
  else if (!left) showToast('All synced.', 'success')
  else showToast(`${before - left} synced. ${left} still need attention.`, 'warning')
}

async function drop(row) {
  await discard(row.key)
  showToast(`Removed "${row.meta?.label ?? row.action_type}" from this phone.`, 'info')
}

const rejected = computed(() => waiting.value.filter((r) => r.status === 'rejected'))
const pending = computed(() => waiting.value.filter((r) => r.status !== 'rejected'))

const RESULT = {
  applied: { text: 'Synced', icon: checkmarkCircleOutline, tone: 'ok' },
  duplicate: { text: 'Already synced (resent)', icon: copyOutline, tone: 'ok' },
  conflict: { text: 'Synced · sent to the station to check', icon: flagOutline, tone: 'warn' },
  rejected: { text: 'Not accepted', icon: alertCircleOutline, tone: 'bad' },
}
const CONFLICT_TEXT = {
  delivered_after_cancel: 'The customer had cancelled. Your delivery was kept.',
  code_mismatch: "The code didn't match the customer's.",
}
const orderLabel = (h) => (h.order_id ? `AF-${h.order_id}` : h.trip_id ? `Trip #${h.trip_id}` : '')
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-title>Sync</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content>
      <ion-refresher slot="fixed" @ion-refresh="refresh">
        <ion-refresher-content />
      </ion-refresher>

      <div class="af-container af-dash af-dash--narrow">
        <RiderSyncBanner />
        <header class="top">
          <h1 class="title">Sync</h1>
          <p class="af-small">
            Deliveries are saved on this phone first, then sent to the station. It happens by itself when you have signal.
          </p>
        </header>

        <EmptyState v-if="env.useMock" title="Demo mode" message="Offline sync needs the AquaFlow server. Turn off demo mode to use it." />

        <template v-else>
          <section class="af-panel status" aria-label="Sync status">
            <div class="status__row">
              <ion-icon :icon="syncState.online ? cloudUploadOutline : cloudOfflineOutline" aria-hidden="true" />
              <div>
                <b>{{ syncState.online ? 'Online' : 'No signal' }}</b>
                <span class="af-small">
                  {{ pending.length }} waiting · {{ rejected.length }} not accepted
                  <template v-if="syncState.lastSyncAt"> · last sync {{ ago(syncState.lastSyncAt) }}</template>
                </span>
              </div>
            </div>
            <AppButton block :loading="syncState.syncing" @click="sync">
              <ion-icon :icon="cloudUploadOutline" aria-hidden="true" /> Sync now
            </AppButton>
          </section>

          <section v-if="rejected.length" class="af-panel" aria-labelledby="rej-title">
            <SectionHead id="rej-title" title="Not accepted" sub="The station's server said no. Fix it, sync again, or remove it." />
            <ol class="list">
              <li v-for="r in rejected" :key="r.key" class="row row--bad">
                <span class="row__icon" aria-hidden="true"><ion-icon :icon="alertCircleOutline" /></span>
                <span class="row__text">
                  <b>{{ r.meta?.label ?? r.action_type }}</b>
                  <span v-if="r.meta?.customer">{{ r.meta.customer }}</span>
                  <span class="row__err">{{ r.error }}</span>
                  <span class="row__meta">Done on the phone at {{ timeOf(r.device_time) }} · tried {{ r.attempts }}×</span>
                </span>
                <AppButton variant="ghost" size="sm" @click="drop(r)">Remove</AppButton>
              </li>
            </ol>
          </section>

          <section class="af-panel" aria-labelledby="wait-title">
            <SectionHead id="wait-title" title="Waiting to sync" :sub="pending.length ? 'Oldest first. They go in this order.' : ''" />
            <EmptyState v-if="!pending.length" art="waves" title="Nothing waiting" message="Everything you did is on the server." />
            <ol v-else class="list">
              <li v-for="r in pending" :key="r.key" class="row">
                <span class="row__icon" aria-hidden="true"><ion-icon :icon="timeOutline" /></span>
                <span class="row__text">
                  <b>{{ r.meta?.label ?? r.action_type }}</b>
                  <span v-if="r.meta?.customer">{{ r.meta.customer }}</span>
                  <span class="row__meta">Done at {{ timeOf(r.device_time) }}</span>
                </span>
              </li>
            </ol>
          </section>

          <section class="af-panel" aria-labelledby="hist-title">
            <SectionHead id="hist-title" title="On the server" sub="Your last 50 synced actions" />
            <p v-if="historyError" class="af-small">{{ historyError }}</p>
            <EmptyState v-else-if="!history.length" art="waves" title="Nothing synced yet" message="Actions you sync show up here." />
            <ol v-else class="list">
              <li v-for="h in history" :key="h.idempotency_key" class="row" :class="`row--${RESULT[h.result]?.tone}`">
                <span class="row__icon" aria-hidden="true"><ion-icon :icon="RESULT[h.result]?.icon" /></span>
                <span class="row__text">
                  <b>{{ h.label }} <span class="row__code">{{ orderLabel(h) }}</span></b>
                  <span>{{ RESULT[h.result]?.text }}</span>
                  <span v-for="c in h.conflicts" :key="c" class="row__warn">{{ CONFLICT_TEXT[c] ?? c }}</span>
                  <span v-if="h.error" class="row__err">{{ h.error }}</span>
                  <span class="row__meta">On the phone {{ timeOf(h.device_time) }} · reached the server {{ timeOf(h.server_time) }}</span>
                </span>
              </li>
            </ol>
          </section>
        </template>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.top { display: grid; gap: 6px; }
.top p { margin: 0; }
.title { margin: 0; font-family: var(--af-display); font-size: clamp(26px, 3.4vw, 34px); font-weight: 650; letter-spacing: -0.04em; }
.status { gap: 14px; }
.status__row { display: flex; align-items: center; gap: 12px; }
.status__row > ion-icon { font-size: 28px; color: var(--af-primary); flex: none; }
.status__row b { display: block; font-size: 16px; font-weight: 800; }
.list { list-style: none; margin: 0; padding: 0; display: grid; }
.row { display: grid; grid-template-columns: 38px minmax(0, 1fr) auto; gap: 12px; align-items: start; padding: 12px 0; border-bottom: 1px solid var(--af-line); }
.row:last-child { border-bottom: 0; }
.row__icon { width: 38px; height: 38px; display: grid; place-items: center; border-radius: 12px; font-size: 19px; background: var(--af-primary-tint); color: var(--af-primary); }
.row--ok .row__icon { background: var(--af-success-tint); color: var(--af-success); }
.row--warn .row__icon { background: var(--af-amber-tint); color: var(--af-amber-fg); }
.row--bad .row__icon { background: var(--af-danger-tint); color: var(--af-danger); }
.row__text { display: grid; gap: 2px; min-width: 0; }
.row__text b { font-size: 15px; font-weight: 800; }
.row__code { font-size: 12.5px; font-weight: 700; color: var(--af-ink-2); margin-left: 4px; }
.row__text > span { font-size: 13px; color: var(--af-ink-2); font-weight: 550; overflow-wrap: anywhere; }
.row__err { color: var(--af-danger) !important; font-weight: 700 !important; }
.row__warn { color: var(--af-amber-fg) !important; font-weight: 700 !important; }
.row__meta { font-size: 12.5px !important; }
</style>
