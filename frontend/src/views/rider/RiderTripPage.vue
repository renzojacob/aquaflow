<!--
  Rider: today's deliveries.
  Trips the station approved for me: download each one (an offline copy with hashed codes),
  then start it when the vehicle is loaded, so its stops go out for delivery.
  Tank (water = share of today's stops done), location sharing (real GPS or demo drive),
  the NEXT stop as a big card (navigate, call, deliver with the customer's code, or report a problem),
  a live map of all stops, then the rest of the stops in trip order.
-->
<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  IonContent,
  IonHeader,
  IonIcon,
  IonModal,
  IonPage,
  IonRefresher,
  IonRefresherContent,
  IonTitle,
  IonToolbar,
  onIonViewWillEnter,
} from '@ionic/vue'
import {
  callOutline,
  cashOutline,
  chatboxEllipsesOutline,
  cubeOutline,
  downloadOutline,
  locateOutline,
  navigateOutline,
  playOutline,
  stopCircleOutline,
  warningOutline,
} from 'ionicons/icons'

import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import LiveMap from '@/components/map/LiveMap.vue'
import QuantityStepper from '@/components/form/QuantityStepper.vue'
import SectionHead from '@/components/dash/SectionHead.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import TankHero from '@/components/dash/TankHero.vue'
import TextField from '@/components/form/TextField.vue'
import { showToast } from '@/composables/useToast'
import { useRiderLocation } from '@/composables/useRiderLocation'
import { env } from '@/config/env'
import {
  FAIL_REASONS,
  checkCodeOffline,
  deliver,
  downloadTrip,
  fail,
  forgetSavedTrip,
  getSavedTrip,
  getToday,
  listMyTrips,
  startTrip,
} from '@/services/riderService'
import { PERIODS, ago, containers, dateISO, duration, friendlyDay, peso } from '@/utils/format'

const { location, startLive, startDemo, retarget, stopSharing } = useRiderLocation()

const data = ref(null)
const loading = ref(true)
const error = ref(null)

// ---------- trips (download, then start) ----------
const trips = ref([])        // approved / downloaded / out trips for me
const saved = ref({})        // trip id -> the copy kept on this phone
const tripBusy = reactive({}) // trip id -> true while downloading

function readSaved() {
  const map = {}
  for (const tr of trips.value) {
    const copy = getSavedTrip(tr.id)
    if (copy) map[tr.id] = copy
  }
  saved.value = map
}

/** Drop copies of trips that are finished or no longer mine. */
function forgetOldCopies() {
  const keep = new Set(trips.value.map((tr) => String(tr.id)))
  try {
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const key = localStorage.key(i)
      const id = key?.startsWith('aquaflow.trip.') ? key.slice('aquaflow.trip.'.length) : null
      if (id && !keep.has(id)) forgetSavedTrip(id)
    }
  } catch {
    // storage blocked: nothing to clean
  }
}

async function loadTrips() {
  if (env.useMock) return (trips.value = []) // trips need the real server
  try {
    trips.value = await listMyTrips()
    forgetOldCopies()
  } catch {
    // no signal: keep the last list; the saved copies still work
  }
  readSaved()
}

const waiting = computed(() => trips.value.filter((tr) => tr.status !== 'out'))
const isCurrent = (tr) => saved.value[tr.id]?.version === tr.version // this phone has the latest version
const isChanged = (tr) => !!saved.value[tr.id] && !isCurrent(tr)
const tripLabel = (tr) => `${friendlyDay(tr.date)} ${PERIODS[tr.period]?.label.toLowerCase() ?? tr.period}`
const tripContainers = (tr) => (saved.value[tr.id]?.stops ?? []).reduce((n, s) => n + (s.containers ?? 0), 0)

async function download(tr) {
  tripBusy[tr.id] = true
  try {
    const copy = await downloadTrip(tr.id)
    saved.value = { ...saved.value, [tr.id]: copy }
    trips.value = trips.value.map((x) => (x.id === tr.id ? { ...x, status: copy.status, version: copy.version } : x))
    showToast(`Trip downloaded: ${copy.stops.length} stop${copy.stops.length === 1 ? '' : 's'}. The list works without signal now.`, 'success')
  } catch (e) {
    showToast(e.message, 'danger')
  } finally {
    tripBusy[tr.id] = false
  }
}

const ssheet = reactive({ open: false, trip: null, busy: false, error: '' })
function openStart(tr) {
  Object.assign(ssheet, { open: true, trip: tr, busy: false, error: '' })
}
async function confirmStart() {
  ssheet.busy = true
  ssheet.error = ''
  try {
    await startTrip(ssheet.trip.id)
    ssheet.open = false
    showToast('Trip started. Customers can now see you are on the way.', 'success')
    await load()
  } catch (e) {
    ssheet.error = e.message
  } finally {
    ssheet.busy = false
  }
}

/** The downloaded stop for an order (has code_salt + code_hash), or null. */
function savedStop(orderId) {
  for (const copy of Object.values(saved.value)) {
    const s = copy?.stops?.find((x) => x.id === orderId)
    if (s) return s
  }
  return null
}

async function load() {
  error.value = null
  try {
    const [today] = await Promise.all([getToday(), loadTrips()])
    data.value = today
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
// New orders can be sent out to me at any time: check every 20 s
let poll = null
onMounted(() => (poll = setInterval(load, 20_000)))
onBeforeUnmount(() => clearInterval(poll))

const stops = computed(() => data.value?.stops ?? [])
const next = computed(() => stops.value[0] ?? null)
const t = computed(() => data.value?.totals ?? {})
const doneShare = computed(() => {
  const all = (t.value.delivered ?? 0) + (t.value.failed ?? 0) + stops.value.length
  return all ? ((t.value.delivered ?? 0) + (t.value.failed ?? 0)) / all : 0
})

// ---------- location sharing ----------
const target = () => (next.value ? { lat: next.value.address.lat, lng: next.value.address.lng } : null)
watch(next, () => retarget(target))
function shareLive() {
  const s = startLive()
  if (s === 'insecure') showToast('This page is not https, so the phone blocks GPS. Use the demo drive, or open the https link.', 'warning')
}
function demo() {
  startDemo(data.value?.location?.fresh ? data.value.location : data.value?.station, target)
}
const STATUS = {
  off: { text: 'Not sharing your location', tone: 'off' },
  asking: { text: 'Waiting for GPS…', tone: 'warn' },
  live: { text: 'Sharing your live location', tone: 'on' },
  demo: { text: 'Demo drive: moving to the next stop', tone: 'demo' },
  arrived: { text: 'Demo drive: at the door', tone: 'demo' },
  denied: { text: 'Location blocked. Allow it in the browser settings.', tone: 'bad' },
  insecure: { text: 'GPS needs an https link on phones', tone: 'bad' },
  unsupported: { text: 'This browser has no GPS', tone: 'bad' },
  error: { text: "Can't get GPS right now", tone: 'bad' },
}
const share = computed(() => STATUS[location.status] ?? STATUS.off)
const riderPoint = computed(() => location.position ?? (data.value?.location?.fresh ? data.value.location : null))
const mapStops = computed(() => stops.value.map((s) => ({ id: s.id, lat: s.address.lat, lng: s.address.lng, seq: s.sequence })))

const mapsUrl = (s) => `https://www.google.com/maps/dir/?api=1&destination=${s.address.lat},${s.address.lng}&travelmode=driving`
const tel = (p) => `tel:${(p || '').replace(/\s+/g, '')}`

// ---------- deliver ----------
const dsheet = reactive({ open: false, order: null, code: '', empties: 0, noCode: false, busy: false, error: '' })
function openDeliver(o) {
  Object.assign(dsheet, { open: true, order: o, code: '', empties: o.expected_empties, noCode: false, busy: false, error: '' })
}
const gps = () => (location.position ? { lat: location.position.lat, lng: location.position.lng, accuracy_m: location.position.accuracy_m } : {})
async function confirmDeliver() {
  dsheet.error = ''
  if (!dsheet.noCode && !dsheet.code.trim()) return (dsheet.error = 'Type the code from the customer’s app.')
  dsheet.busy = true
  try {
    // Check against the downloaded hash first, so a wrong code is caught even with no signal.
    // The server checks the real code again either way.
    if (!dsheet.noCode && (await checkCodeOffline(savedStop(dsheet.order.id), dsheet.code)) === false) {
      dsheet.error = "That code doesn't match. Ask the customer to read it again from their app."
      return
    }
    const r = await deliver(dsheet.order.id, {
      ...(dsheet.noCode ? { no_code: true } : { code: dsheet.code.trim() }),
      empties_collected: dsheet.empties,
      ...gps(),
    })
    dsheet.open = false
    showToast(
      r.geofence_flagged ? `${dsheet.order.code} delivered. Marked for a check: you were far from the pin.` : `${dsheet.order.code} delivered. Collect ${peso(dsheet.order.total)}.`,
      r.geofence_flagged ? 'warning' : 'success',
    )
    await load()
  } catch (e) {
    dsheet.error = e.message
  } finally {
    dsheet.busy = false
  }
}

// ---------- couldn't deliver ----------
const fsheet = reactive({ open: false, order: null, reason: 'absent', note: '', busy: false, error: '' })
function openFail(o) {
  Object.assign(fsheet, { open: true, order: o, reason: 'absent', note: '', busy: false, error: '' })
}
async function confirmFail() {
  fsheet.busy = true
  fsheet.error = ''
  try {
    await fail(fsheet.order.id, { failure_reason: fsheet.reason, note: fsheet.note, ...gps() })
    fsheet.open = false
    showToast(`${fsheet.order.code} goes back to the station.`, 'success')
    await load()
  } catch (e) {
    fsheet.error = e.message
  } finally {
    fsheet.busy = false
  }
}
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-title>Deliveries</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content>
      <ion-refresher slot="fixed" @ion-refresh="refresh">
        <ion-refresher-content />
      </ion-refresher>

      <div class="af-container af-dash">
        <div v-if="loading" class="af-panel"><SkeletonList :rows="4" /></div>
        <div v-else-if="error" class="af-panel err" role="alert">
          <b>Couldn't load your deliveries</b>
          <p>{{ error.message }}</p>
          <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>

        <template v-else-if="data">
          <!-- ===== Trips to download / start ===== -->
          <section v-if="waiting.length" class="af-panel trips" aria-label="Your trips">
            <SectionHead title="Your trips" sub="Download before you leave. Start when the vehicle is loaded." />
            <article v-for="tr in waiting" :key="tr.id" class="trip">
              <div class="trip__head">
                <b>{{ tripLabel(tr) }}</b>
                <span class="trip__badge" :class="isCurrent(tr) ? 'is-ready' : isChanged(tr) ? 'is-changed' : ''">
                  {{ isCurrent(tr) ? 'On this phone' : isChanged(tr) ? 'Changed' : 'Not downloaded' }}
                </span>
              </div>
              <p class="trip__meta">Trip #{{ tr.id }} · {{ tr.vehicle.name }} ({{ tr.vehicle.plate }}) · {{ tr.stop_count }} stop{{ tr.stop_count === 1 ? '' : 's' }}</p>
              <p v-if="isChanged(tr)" class="trip__warn" role="status">The station changed this trip. Download it again before you start.</p>
              <ol v-if="isCurrent(tr)" class="trip__stops">
                <li v-for="s in saved[tr.id].stops" :key="s.id">
                  <span class="trip__seq" aria-hidden="true">{{ s.sequence }}</span>
                  <span><b>{{ s.customer.name }}</b> {{ s.address.barangay }} · {{ containers(s.containers) }}</span>
                </li>
              </ol>
              <AppButton v-if="!isCurrent(tr)" block :loading="!!tripBusy[tr.id]" @click="download(tr)">
                <ion-icon :icon="downloadOutline" aria-hidden="true" /> {{ isChanged(tr) ? 'Download again' : 'Download trip' }}
              </AppButton>
              <AppButton v-else block @click="openStart(tr)"><ion-icon :icon="playOutline" aria-hidden="true" /> Start trip</AppButton>
            </article>
          </section>

          <div class="af-bento af-bento--stretch">
            <!-- ===== The day ===== -->
            <TankHero class="b-7" compact :level="doneShare" :label="`${t.delivered + t.failed} of ${t.delivered + t.failed + stops.length} stops done today`">
              <span class="t-kicker">Today</span>
              <h1 class="t-title">{{ stops.length ? `${stops.length} stop${stops.length > 1 ? 's' : ''} to go` : 'No stops right now' }}</h1>
              <p class="tank__soft t-sub">
                <template v-if="stops.length">{{ containers(t.on_board) }} on board. Collect {{ peso(t.to_collect) }}. About {{ duration(t.minutes_left) }} of driving and handing over.</template>
                <template v-else-if="waiting.length">Download and start your trip above to load its stops.</template>
                <template v-else>When the station sends an order out with you, it shows up here.</template>
              </p>
              <div class="share" :class="`share--${share.tone}`">
                <span class="share__dot" aria-hidden="true"></span>
                <span class="share__text" role="status">
                  {{ share.text }}
                  <small v-if="location.lastSentAt">Sent {{ ago(location.lastSentAt) }}</small>
                </span>
                <div class="share__btns">
                  <button v-if="location.mode !== 'live'" type="button" class="sbtn sbtn--main" @click="shareLive"><ion-icon :icon="locateOutline" aria-hidden="true" /> Share live location</button>
                  <button v-if="location.mode !== 'demo' && stops.length" type="button" class="sbtn" @click="demo"><ion-icon :icon="playOutline" aria-hidden="true" /> Demo drive</button>
                  <button v-if="location.mode !== 'off'" type="button" class="sbtn" @click="stopSharing"><ion-icon :icon="stopCircleOutline" aria-hidden="true" /> Stop</button>
                </div>
              </div>
            </TankHero>

            <!-- ===== Next stop ===== -->
            <section v-if="next" class="af-panel b-5 next" aria-labelledby="next-title">
              <div class="next__top">
                <span class="next__seq">Next stop</span>
                <span class="next__eta">{{ next.leg_m < 60 ? "You're here" : `About ${duration(next.eta_minutes)}, ${(next.leg_m / 1000).toFixed(1)} km` }}</span>
              </div>
              <h2 id="next-title" class="next__name">{{ next.customer.name }}</h2>
              <p class="next__addr">{{ next.address.street }}, {{ next.address.barangay }}<i v-if="next.address.landmark"> · {{ next.address.landmark }}</i></p>
              <dl class="next__facts">
                <div><dt><ion-icon :icon="cubeOutline" aria-hidden="true" /> Refills</dt><dd>{{ next.containers }}</dd></div>
                <div><dt>Empties back</dt><dd>{{ next.expected_empties }}</dd></div>
                <div class="money"><dt><ion-icon :icon="cashOutline" aria-hidden="true" /> Collect</dt><dd>{{ peso(next.total) }}</dd></div>
              </dl>
              <ul class="next__load" aria-label="What to bring">
                <li v-for="l in next.items" :key="l.name"><b>{{ l.quantity }} ×</b> {{ l.name }}</li>
              </ul>
              <p v-if="next.notes" class="next__note"><ion-icon :icon="chatboxEllipsesOutline" aria-hidden="true" /> “{{ next.notes }}”</p>
              <div class="next__btns">
                <a class="nbtn" :href="mapsUrl(next)" target="_blank" rel="noopener"><ion-icon :icon="navigateOutline" aria-hidden="true" /> Navigate</a>
                <a v-if="next.customer.phone" class="nbtn" :href="tel(next.customer.phone)"><ion-icon :icon="callOutline" aria-hidden="true" /> Call</a>
              </div>
              <AppButton size="lg" block @click="openDeliver(next)">Deliver: enter the customer's code</AppButton>
              <AppButton variant="ghost" block @click="openFail(next)"><ion-icon :icon="warningOutline" aria-hidden="true" /> Couldn't deliver</AppButton>
            </section>
            <section v-else class="af-panel b-5">
              <EmptyState title="Nothing to deliver" :message="t.delivered ? `You delivered ${t.delivered} today. Nice work.` : 'Wait for the station to send an order out with you.'" />
            </section>
          </div>

          <!-- ===== Map ===== -->
          <section v-if="stops.length" class="mapcard" aria-label="Map of your stops">
            <LiveMap :station="data.station" :stops="mapStops" :rider="riderPoint" :route="data.route_line" height="360px" label="Map of your stops, numbered in order" />
          </section>

          <!-- ===== All stops ===== -->
          <section v-if="stops.length > 1" class="af-panel" aria-labelledby="all-title">
            <SectionHead title="After that" :sub="`${stops.length - 1} more, in order`" />
            <ol class="stops">
              <li v-for="s in stops.slice(1)" :key="s.id" class="stop">
                <span class="stop__seq" aria-hidden="true">{{ s.sequence }}</span>
                <span class="stop__text">
                  <b>{{ s.customer.name }}</b>
                  <span>{{ s.address.street }}, {{ s.address.barangay }}</span>
                  <span class="stop__meta">{{ s.items.map((l) => `${l.quantity} ${l.name}`).join(', ') }}, collect {{ peso(s.total) }}, {{ PERIODS[s.period].label.toLowerCase() }}</span>
                </span>
                <span class="stop__eta">~{{ duration(s.eta_minutes) }}</span>
                <span class="stop__btns">
                  <a class="ibtn" :href="mapsUrl(s)" target="_blank" rel="noopener" :aria-label="`Navigate to ${s.customer.name}`"><ion-icon :icon="navigateOutline" /></a>
                  <button type="button" class="ibtn ibtn--go" :aria-label="`Deliver to ${s.customer.name}`" @click="openDeliver(s)"><ion-icon :icon="cubeOutline" /></button>
                </span>
              </li>
            </ol>
          </section>
        </template>
      </div>

      <!-- Deliver sheet -->
      <ion-modal :is-open="dsheet.open" :breakpoints="[0, 0.85, 1]" :initial-breakpoint="0.85" @did-dismiss="dsheet.open = false">
        <ion-content>
          <form v-if="dsheet.order" class="sheet" novalidate @submit.prevent="confirmDeliver">
            <header>
              <h2 class="af-h2">Deliver {{ dsheet.order.code }}</h2>
              <p class="af-small">{{ dsheet.order.customer.name }}: {{ dsheet.order.items.map((l) => `${l.quantity} × ${l.name}`).join(', ') }}. Collect <b class="af-money">{{ peso(dsheet.order.total) }}</b> in cash.</p>
            </header>
            <template v-if="!dsheet.noCode">
              <TextField v-model="dsheet.code" label="Customer's delivery code" inputmode="numeric" autocomplete="one-time-code" placeholder="The digits in their app" required :error="dsheet.error" />
              <button type="button" class="link" @click="dsheet.noCode = true">The customer can't find the code</button>
            </template>
            <div v-else class="nocode">
              <b>Deliver without the code</b>
              <span>Allowed, but the station will check this delivery later.</span>
              <button type="button" class="link" @click="dsheet.noCode = false">I have the code after all</button>
            </div>
            <div class="emp">
              <span class="lbl">Empty containers you collected</span>
              <QuantityStepper v-model="dsheet.empties" :min="0" :max="50" label="Empty containers collected" unit="empties" />
            </div>
            <p v-if="dsheet.error && dsheet.noCode" class="err-line" role="alert">{{ dsheet.error }}</p>
            <AppButton type="submit" size="lg" block :loading="dsheet.busy">Mark as delivered</AppButton>
          </form>
        </ion-content>
      </ion-modal>

      <!-- Start trip sheet -->
      <ion-modal :is-open="ssheet.open" :breakpoints="[0, 0.6, 1]" :initial-breakpoint="0.6" @did-dismiss="ssheet.open = false">
        <ion-content>
          <form v-if="ssheet.trip" class="sheet" novalidate @submit.prevent="confirmStart">
            <header>
              <h2 class="af-h2">Start trip #{{ ssheet.trip.id }}?</h2>
              <p class="af-small">
                Load {{ containers(tripContainers(ssheet.trip)) }} for {{ ssheet.trip.stop_count }} stop{{ ssheet.trip.stop_count === 1 ? '' : 's' }}.
                Every stop becomes “out for delivery” and the customers can follow you on the map.
              </p>
            </header>
            <p v-if="ssheet.trip.date !== dateISO(0)" class="trip__warn" role="status">This trip is for {{ tripLabel(ssheet.trip) }}, not today. Start it only if the station told you to.</p>
            <p v-if="ssheet.error" class="err-line" role="alert">{{ ssheet.error }}</p>
            <AppButton type="submit" size="lg" block :loading="ssheet.busy">The vehicle is loaded. Start.</AppButton>
            <AppButton variant="ghost" block @click="ssheet.open = false">Not yet</AppButton>
          </form>
        </ion-content>
      </ion-modal>

      <!-- Couldn't deliver sheet -->
      <ion-modal :is-open="fsheet.open" :breakpoints="[0, 0.75, 1]" :initial-breakpoint="0.75" @did-dismiss="fsheet.open = false">
        <ion-content>
          <form v-if="fsheet.order" class="sheet" novalidate @submit.prevent="confirmFail">
            <header>
              <h2 class="af-h2">Couldn't deliver {{ fsheet.order.code }}?</h2>
              <p class="af-small">Bring the containers back. The station can send it again once.</p>
            </header>
            <div class="reasons" role="radiogroup" aria-label="What happened">
              <button v-for="r in FAIL_REASONS" :key="r.value" type="button" role="radio" class="af-chip" :aria-checked="fsheet.reason === r.value" :aria-pressed="fsheet.reason === r.value" @click="fsheet.reason = r.value">{{ r.label }}</button>
            </div>
            <TextField v-model="fsheet.note" label="Anything else?" :maxlength="200" placeholder="Gate locked, called twice" />
            <p v-if="fsheet.error" class="err-line" role="alert">{{ fsheet.error }}</p>
            <AppButton type="submit" variant="danger" size="lg" block :loading="fsheet.busy">Report: couldn't deliver</AppButton>
          </form>
        </ion-content>
      </ion-modal>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.t-kicker { font-size: 14px; font-weight: 750; color: #cfe6ea; }
.t-title { margin: 0; font-family: var(--af-display); font-size: clamp(30px, 4.4vw, 46px); font-weight: 650; letter-spacing: -0.045em; line-height: 1; }
.t-sub { margin: 0; font-size: 15px; line-height: 1.55; font-weight: 550; max-width: 46ch; }

.share { display: grid; grid-template-columns: auto 1fr; gap: 10px 12px; align-items: center; margin-top: auto; padding: 12px 14px; border-radius: 18px; background: rgba(2, 18, 26, 0.5); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
.share__dot { width: 10px; height: 10px; border-radius: 50%; background: #8fb3ba; }
.share--on .share__dot { background: #6fe3a5; box-shadow: 0 0 0 4px rgba(111, 227, 165, 0.25); animation: sh-pulse 1.6s ease-in-out infinite; }
.share--demo .share__dot { background: #b9b4ff; box-shadow: 0 0 0 4px rgba(185, 180, 255, 0.25); animation: sh-pulse 1.6s ease-in-out infinite; }
.share--bad .share__dot, .share--warn .share__dot { background: #ffb454; }
@keyframes sh-pulse { 50% { opacity: 0.45; } }
.share__text { display: grid; font-size: 14px; font-weight: 750; color: #e6f4f6; }
.share__text small { font-size: 12px; font-weight: 600; color: #cfe6ea; }
.share__btns { grid-column: 1 / -1; display: flex; gap: 8px; flex-wrap: wrap; }
.sbtn { display: inline-flex; align-items: center; gap: 6px; min-height: 44px; padding: 0 14px; border-radius: 999px; border: 1px solid rgba(230, 244, 246, 0.25); background: rgba(255, 255, 255, 0.06); color: #e6f4f6; font: 750 13.5px var(--af-font); cursor: pointer; }
.sbtn--main { background: #4fe0d2; border-color: #4fe0d2; color: #022320; }

.next { gap: 12px; border-color: color-mix(in srgb, var(--af-primary) 40%, var(--af-line)); }
.next__top { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
.next__seq { padding: 5px 12px; border-radius: 999px; background: var(--af-primary); color: var(--af-on-primary); font-size: 13px; font-weight: 800; }
.next__eta { font-size: 13.5px; font-weight: 750; color: var(--af-ink-2); }
.next__name { margin: 0; font-family: var(--af-display); font-size: 26px; font-weight: 650; letter-spacing: -0.035em; line-height: 1.1; }
.next__addr { margin: 0; font-size: 15px; line-height: 1.5; color: var(--af-ink-2); font-weight: 600; }
.next__facts { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin: 0; }
.next__facts div { display: grid; gap: 2px; padding: 10px 12px; border-radius: 14px; background: var(--af-surface-2); }
.next__facts dt { display: flex; align-items: center; gap: 5px; font-size: 12.5px; font-weight: 700; color: var(--af-ink-2); }
.next__facts dd { margin: 0; font-family: var(--af-display); font-size: 22px; font-weight: 650; letter-spacing: -0.03em; }
.next__facts .money { background: var(--af-sun-tint); }
.next__facts .money dd { color: var(--af-sun); }
.next__load { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 6px; }
.next__load li { padding: 6px 12px; border-radius: 999px; background: var(--af-surface-2); font-size: 13.5px; font-weight: 650; }
.next__load b { font-weight: 800; }
.next__note { margin: 0; display: flex; gap: 8px; padding: 10px 12px; border-radius: 14px; background: var(--af-amber-tint); font-size: 14px; line-height: 1.45; }
.next__note ion-icon { flex: none; color: var(--af-amber-fg); margin-top: 2px; }
.next__btns { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.nbtn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 48px; border-radius: 999px; background: var(--af-surface-2); border: 1px solid var(--af-line-strong); color: var(--af-ink); font: 750 14.5px var(--af-font); text-decoration: none; }
.nbtn ion-icon { color: var(--af-primary); font-size: 18px; }

.trips { gap: 12px; margin-bottom: 16px; }
.trip { display: grid; gap: 10px; padding: 14px; border-radius: 20px; background: var(--af-surface-2); border: 1px solid var(--af-line); }
.trip__head { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
.trip__head b { font-size: 16px; font-weight: 800; }
.trip__badge { padding: 4px 10px; border-radius: 999px; background: var(--af-pearl-tint); color: var(--af-pearl); font-size: 12.5px; font-weight: 800; }
.trip__badge.is-ready { background: var(--af-primary-tint); color: var(--af-primary); }
.trip__badge.is-changed { background: var(--af-amber-tint); color: var(--af-amber-fg); }
.trip__meta { margin: 0; font-size: 13.5px; font-weight: 600; color: var(--af-ink-2); }
.trip__warn { margin: 0; padding: 10px 12px; border-radius: 14px; background: var(--af-amber-tint); color: var(--af-amber-fg); font-size: 14px; font-weight: 650; line-height: 1.45; }
.trip__stops { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.trip__stops li { display: flex; align-items: center; gap: 10px; font-size: 14px; color: var(--af-ink-2); min-width: 0; }
.trip__stops li > span:last-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.trip__stops b { color: var(--af-ink); font-weight: 750; }
.trip__seq { flex: none; width: 26px; height: 26px; display: grid; place-items: center; border-radius: 50%; background: var(--af-pearl-tint); color: var(--af-pearl); font-size: 13px; font-weight: 800; }

.mapcard { border-radius: 28px; overflow: hidden; border: 1px solid var(--af-line); box-shadow: var(--af-shadow-2); }

.stops { list-style: none; margin: 0; padding: 0; display: grid; }
.stop { display: grid; grid-template-columns: 34px minmax(0, 1fr) auto auto; gap: 12px; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--af-line); }
.stop:last-child { border-bottom: 0; }
.stop__seq { width: 34px; height: 34px; display: grid; place-items: center; border-radius: 50%; background: var(--af-pearl-tint); color: var(--af-pearl); font-weight: 800; }
.stop__text { display: grid; gap: 2px; min-width: 0; }
.stop__text b { font-size: 15px; font-weight: 800; }
.stop__text span { font-size: 13px; color: var(--af-ink-2); font-weight: 550; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.stop__eta { font-size: 13px; font-weight: 750; color: var(--af-ink-2); white-space: nowrap; }
.stop__btns { display: flex; gap: 6px; }
.ibtn { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 50%; border: 0; background: var(--af-surface-2); color: var(--af-primary); font-size: 18px; cursor: pointer; text-decoration: none; }
.ibtn--go { background: var(--af-primary-tint); }

.sheet { display: grid; gap: 16px; padding: 32px 16px; max-width: 520px; margin: 0 auto; }
.sheet header { display: grid; gap: 6px; }
.sheet h2, .sheet p { margin: 0; }
.link { justify-self: start; min-height: 40px; padding: 0; border: 0; background: none; color: var(--af-primary); font: 750 14px var(--af-font); text-decoration: underline; text-underline-offset: 3px; cursor: pointer; }
.nocode { display: grid; gap: 4px; padding: 14px; border-radius: 16px; background: var(--af-amber-tint); }
.nocode b { color: var(--af-amber-fg); }
.nocode span { font-size: 14px; }
.emp { display: grid; justify-items: center; gap: 10px; padding: 14px; border-radius: 18px; background: var(--af-surface-2); }
.lbl { font-size: 14px; font-weight: 800; }
.reasons { display: flex; flex-wrap: wrap; gap: 8px; }
.err-line { padding: 10px 14px; border-radius: 12px; background: var(--af-danger-tint); color: var(--af-danger); font-size: 14px; font-weight: 650; }

.err { justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }

@media (max-width: 520px) {
  .stop { grid-template-columns: 34px minmax(0, 1fr) auto; }
  .stop__eta { display: none; }
}
@media (prefers-reduced-motion: reduce) { .share__dot { animation: none !important; } }
</style>
