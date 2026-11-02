<!--
  Rider: what I finished today. Cash to hand to the station, containers delivered,
  empties brought back, and every stop with its result (and a note if the station will check it).
-->
<script setup>
import { computed, ref } from 'vue'
import { IonContent, IonHeader, IonIcon, IonPage, IonRefresher, IonRefresherContent, IonTitle, IonToolbar, onIonViewWillEnter } from '@ionic/vue'
import { cashOutline, checkmarkCircleOutline, cubeOutline, refreshCircleOutline, shieldCheckmarkOutline, warningOutline } from 'ionicons/icons'

import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import KpiTile from '@/components/dash/KpiTile.vue'
import SectionHead from '@/components/dash/SectionHead.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import { getToday } from '@/services/riderService'
import { containers, peso, timeOf } from '@/utils/format'

const data = ref(null)
const loading = ref(true)
const error = ref(null)

async function load() {
  error.value = null
  try {
    data.value = await getToday()
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
const t = computed(() => data.value?.totals ?? {})
const done = computed(() => data.value?.done ?? [])
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-title>Done today</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content>
      <ion-refresher slot="fixed" @ion-refresh="refresh">
        <ion-refresher-content />
      </ion-refresher>

      <div class="af-container af-dash af-dash--narrow">
        <header class="top">
          <h1 class="title">Done today</h1>
          <p class="af-small">Hand the cash and empties to the station at the end of your trip.</p>
        </header>

        <div v-if="loading" class="af-panel"><SkeletonList :rows="4" /></div>
        <div v-else-if="error" class="af-panel err" role="alert">
          <b>Couldn't load today</b>
          <p>{{ error.message }}</p>
          <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>

        <template v-else-if="data">
          <div class="kpis">
            <KpiTile label="Cash to hand in" :value="peso(t.collected)" tone="sun" :icon="cashOutline" :hint="`From ${t.delivered} deliveries`" />
            <KpiTile label="Containers delivered" :value="t.containers" :icon="cubeOutline" />
            <KpiTile label="Empties brought back" :value="t.empties" tone="pearl" :icon="refreshCircleOutline" />
            <KpiTile label="Couldn't deliver" :value="t.failed" :tone="t.failed ? 'warn' : 'water'" :icon="warningOutline" :hint="t.failed ? 'Bring those containers back' : 'None today'" />
          </div>

          <section class="af-panel">
            <SectionHead title="Every stop" :sub="done.length ? `${done.length} today, newest first` : ''" />
            <EmptyState v-if="!done.length" title="Nothing yet today" message="Deliveries you finish show up here." />
            <ol v-else class="list">
              <li v-for="d in done" :key="`${d.id}-${d.at}`" class="row" :class="`row--${d.outcome}`">
                <span class="row__icon" aria-hidden="true"><ion-icon :icon="d.outcome === 'delivered' ? checkmarkCircleOutline : warningOutline" /></span>
                <span class="row__text">
                  <b>{{ d.customer.name }} <span class="row__code">{{ d.code }}</span></b>
                  <span>{{ d.address.street }}, {{ d.address.barangay }}</span>
                  <span v-if="d.outcome === 'delivered'" class="row__meta">
                    {{ containers(d.quantity) }}, {{ d.empties_collected }} empties back
                    <template v-if="d.code_ok"> · <ion-icon :icon="shieldCheckmarkOutline" aria-hidden="true" /> code checked</template>
                  </span>
                  <span v-else class="row__meta">{{ d.failure }}</span>
                  <span v-if="d.geofence_flagged || d.code_ok === false" class="row__flag">The station will check this one{{ d.code_ok === false ? ': no code' : ': far from the pin' }}</span>
                </span>
                <span class="row__end">
                  <b v-if="d.outcome === 'delivered'" class="af-money">{{ peso(d.total) }}</b>
                  <time :datetime="d.at">{{ timeOf(d.at) }}</time>
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
.kpis { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.list { list-style: none; margin: 0; padding: 0; display: grid; }
.row { display: grid; grid-template-columns: 38px minmax(0, 1fr) auto; gap: 12px; align-items: start; padding: 12px 0; border-bottom: 1px solid var(--af-line); }
.row:last-child { border-bottom: 0; }
.row__icon { width: 38px; height: 38px; display: grid; place-items: center; border-radius: 12px; font-size: 19px; }
.row--delivered .row__icon { background: color-mix(in srgb, var(--af-success) 14%, transparent); color: var(--af-success); }
.row--failed .row__icon { background: var(--af-amber-tint); color: var(--af-amber-fg); }
.row__text { display: grid; gap: 2px; min-width: 0; }
.row__text b { font-size: 15px; font-weight: 800; }
.row__code { font-size: 12.5px; font-weight: 700; color: var(--af-ink-2); margin-left: 4px; }
.row__text > span { font-size: 13px; color: var(--af-ink-2); font-weight: 550; }
.row__meta { display: inline-flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.row__flag { color: var(--af-amber-fg) !important; font-weight: 700 !important; }
.row__end { display: grid; justify-items: end; gap: 2px; }
.row__end b { font-family: var(--af-display); font-size: 16px; font-weight: 650; }
.row__end time { font-size: 12.5px; font-weight: 650; color: var(--af-ink-2); }
.err { justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }
</style>
