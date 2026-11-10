<!--
  Dispatcher: plan deliveries.
  Pick a day and time, press "Plan deliveries", and the day's confirmed orders are grouped into one
  trip per vehicle (never more containers than the vehicle holds). Then you adjust: reorder stops,
  move an order to another trip, pick the rider, and approve. An approved trip can be downloaded by
  the rider. Orders that fit no vehicle are listed with the reason, never dropped.
  Distances and arrival times come from OpenRouteService road routes when the server has an
  ORS_API_KEY; otherwise they are estimates (straight-line x 1.35 at tricycle speed).
-->
<script setup>
import { computed, ref, watch } from 'vue'
import { IonContent, IonHeader, IonIcon, IonPage, IonTitle, IonToolbar, onIonViewWillEnter } from '@ionic/vue'
import { arrowDownOutline, arrowUpOutline, closeOutline } from 'ionicons/icons'

import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SectionHead from '@/components/dash/SectionHead.vue'
import SegmentedControl from '@/components/form/SegmentedControl.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import TripsMap from '@/components/map/TripsMap.vue'
import { tripColor } from '@/constants/tripColors'
import { showToast } from '@/composables/useToast'
import { listRiders } from '@/services/dispatcherService'
import { getDemand } from '@/services/refillService'
import { getServiceArea } from '@/services/fleetService'
import { approveTrip, assignTrip, createTrip, deleteTrip, listTrips, listVehicles, planSlot, setTripStops } from '@/services/tripService'
import { containers, dateISO, duration, friendlyDay, PERIODS, timeOf } from '@/utils/format'

const day = ref(dateISO(0))
const period = ref('morning')
const trips = ref([])
const unplanned = ref([])
const vehicles = ref([])
const riders = ref([])
const station = ref(null)
const notFitted = ref([])
const loading = ref(true)
const error = ref(null)
const planning = ref(false)
const busy = ref(null) // key of the thing being changed: "trip:3", "order:7"
const selectedId = ref(null)
const likely = ref(null) // Feature C: predicted reorders for this day (tentative, never planned)

const dayOptions = computed(() => [
  { value: dateISO(0), label: 'Today' },
  { value: dateISO(1), label: 'Tomorrow' },
])
const periodOptions = Object.entries(PERIODS).map(([value, p]) => ({ value, label: p.label }))
const STATUS = {
  draft: 'Draft',
  approved: 'Approved',
  downloaded: 'On the rider’s phone',
  out: 'On the road',
  completed: 'Done',
}
const editable = (t) => ['draft', 'approved', 'downloaded'].includes(t.status)
const editableTrips = computed(() => trips.value.filter(editable))
const freeVehicles = computed(() => vehicles.value.filter((v) => v.is_available && !v.trip_id))
const ridersFree = (t) => riders.value.filter((r) => r.id === t.rider?.id || !trips.value.some((x) => x.rider?.id === r.id))
const km = (m) => `${(m / 1000).toFixed(1)} km`

async function load() {
  error.value = null
  try {
    const [t, v, r, a] = await Promise.all([listTrips(day.value, period.value), listVehicles(day.value, period.value), listRiders(), getServiceArea()])
    trips.value = t.trips
    unplanned.value = t.unplanned
    vehicles.value = v
    riders.value = r
    station.value = { lat: a.lat, lng: a.lng }
    getDemand(2)
      .then((d) => (likely.value = d.days.find((x) => x.date === day.value) ?? null))
      .catch(() => (likely.value = null))
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
onIonViewWillEnter(load)
watch([day, period], () => { notFitted.value = []; selectedId.value = null; loading.value = true; load() })

/** Run one change, then refresh everything so the screen always matches the server. */
async function run(key, fn, okMessage) {
  busy.value = key
  try {
    await fn()
    if (okMessage) showToast(okMessage, 'success')
  } catch (e) {
    showToast(e.message, 'danger')
  } finally {
    busy.value = null
    await load()
  }
}

async function plan() {
  planning.value = true
  try {
    const r = await planSlot(day.value, period.value)
    notFitted.value = r.not_fitted
    const n = r.trips.length
    showToast(n ? `${n} ${n === 1 ? 'trip' : 'trips'} planned. Check them, pick riders, then approve.` : 'Nothing to plan for this time.', n ? 'success' : 'info')
  } catch (e) {
    showToast(e.message, 'danger')
  } finally {
    planning.value = false
    await load()
  }
}

const idsOf = (t) => t.stops.map((s) => s.order_id)
function moveStop(t, i, dir) {
  const ids = idsOf(t)
  const j = i + dir
  if (j < 0 || j >= ids.length) return
  ;[ids[i], ids[j]] = [ids[j], ids[i]]
  run(`trip:${t.id}`, () => setTripStops(t.id, ids))
}
const removeStop = (t, s) => run(`trip:${t.id}`, () => setTripStops(t.id, idsOf(t).filter((id) => id !== s.order_id)), `${s.code} is unplanned again`)
const setRider = (t, riderId) => riderId && run(`trip:${t.id}`, () => assignTrip(t.id, { riderId: Number(riderId) }))
const approve = (t) => run(`trip:${t.id}`, () => approveTrip(t.id), `Approved. ${t.rider?.name ?? 'The rider'} can download it.`)
const removeTrip = (t) => run(`trip:${t.id}`, () => deleteTrip(t.id), 'Trip deleted. Its orders are unplanned again.')

/** Move a stop to another trip: take it out of the first, then add it to the second. Undo if the second refuses. */
function moveTo(t, s, targetId) {
  if (!targetId) return
  const target = trips.value.find((x) => x.id === Number(targetId))
  run(`trip:${t.id}`, async () => {
    const left = idsOf(t).filter((id) => id !== s.order_id)
    if (!left.length) throw new Error('A trip needs at least one stop. Delete the trip instead.')
    await setTripStops(t.id, left)
    try {
      await setTripStops(target.id, [...idsOf(target), s.order_id])
    } catch (e) {
      await setTripStops(t.id, idsOf(t))
      throw e
    }
  }, `${s.code} moved to ${target.vehicle.name}`)
}

/** An unplanned order goes onto a trip ("t:3") or starts a new trip with a free vehicle ("v:2"). */
function addOrder(o, choice) {
  if (!choice) return
  const [kind, id] = choice.split(':')
  if (kind === 't') {
    const t = trips.value.find((x) => x.id === Number(id))
    run(`order:${o.order_id}`, () => setTripStops(t.id, [...idsOf(t), o.order_id]), `${o.code} added to ${t.vehicle.name}`)
  } else {
    run(`order:${o.order_id}`, () => createTrip({ date: day.value, period: period.value, vehicleId: Number(id), orderIds: [o.order_id] }), `${o.code} has a new trip`)
  }
}

const load_pct = (t) => Math.min(100, Math.round((t.load.peak / Math.max(1, t.load.capacity)) * 100))
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar><ion-title>Plan deliveries</ion-title></ion-toolbar>
    </ion-header>
    <ion-content>
      <div class="af-container af-dash">
        <header class="top">
          <h1 class="title">Plan deliveries</h1>
          <p class="af-small">One trip per vehicle. Solid lines follow the roads; dotted lines and “estimate” mean straight-line distances.</p>
        </header>

        <section class="af-panel bar-controls" aria-label="Day and time">
          <SegmentedControl v-model="day" label="Day" :options="dayOptions" />
          <SegmentedControl v-model="period" label="Delivery time" :options="periodOptions" />
          <AppButton :loading="planning" @click="plan">Plan deliveries</AppButton>
        </section>
        <p class="af-small note">Planning replaces draft trips for {{ friendlyDay(day).toLowerCase() }}’s {{ period }}. Approved trips are never touched.</p>

        <SkeletonList v-if="loading" :rows="4" />
        <div v-else-if="error" class="af-panel err" role="alert">
          <b>Couldn't load the plan</b>
          <p>{{ error.message }}</p>
          <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>

        <div v-else class="layout">
          <div class="col">
            <section v-if="notFitted.length" class="af-panel warn" role="alert" aria-label="Orders that did not fit">
              <SectionHead :title="`${notFitted.length} ${notFitted.length === 1 ? 'order' : 'orders'} did not fit`" sub="Add a vehicle, switch one on, or move them to another time" />
              <ul class="plain">
                <li v-for="o in notFitted" :key="o.order_id"><b>{{ o.code }}</b> {{ o.customer_name }} · {{ containers(o.containers) }}<br /><span class="af-small">{{ o.reason }}</span></li>
              </ul>
            </section>

            <EmptyState
              v-if="!trips.length && !unplanned.length"
              art="tricycle"
              title="Nothing to plan"
              :message="`No confirmed orders for ${friendlyDay(day).toLowerCase()}’s ${period}. Confirm orders on the Orders screen first.`"
            />

            <article
              v-for="(t, i) in trips"
              :key="t.id"
              class="af-panel trip"
              :class="{ 'trip--sel': selectedId === t.id }"
              :aria-label="`Trip ${i + 1}: ${t.vehicle.name}`"
              @click="selectedId = selectedId === t.id ? null : t.id"
            >
              <header class="trip__head">
                <span class="dot" :style="{ background: tripColor(i) }" aria-hidden="true"></span>
                <div class="trip__title">
                  <b>{{ t.vehicle.name }}</b>
                  <span class="af-small">{{ t.vehicle.plate }} · {{ STATUS[t.status] }}</span>
                </div>
                <span class="trip__stats af-small">{{ km(t.total_distance_m) }} · {{ duration(t.total_duration_s / 60) }}<template v-if="t.distance_is_estimate"> (estimate)</template></span>
              </header>

              <div class="load">
                <div class="load__top"><span>Load</span><b>{{ t.load.peak }} of {{ t.load.capacity }} containers</b></div>
                <div class="load__bar" role="meter" aria-valuemin="0" :aria-valuemax="t.load.capacity" :aria-valuenow="t.load.peak" :aria-label="`${t.vehicle.name} load`">
                  <span :style="{ width: load_pct(t) + '%', background: tripColor(i) }"></span>
                </div>
              </div>

              <p v-if="t.phone_out_of_date" class="stale" role="status">This trip changed after the rider downloaded it. The rider must download it again.</p>

              <label class="rider" @click.stop>
                <span>Rider</span>
                <select :value="t.rider?.id ?? ''" :disabled="!editable(t) || busy === `trip:${t.id}`" @change="setRider(t, $event.target.value)">
                  <option value="" disabled>Choose a rider…</option>
                  <option v-for="r in ridersFree(t)" :key="r.id" :value="r.id">{{ r.name }}</option>
                </select>
              </label>

              <ol class="stops">
                <li v-for="(s, k) in t.stops" :key="s.order_id" class="stop" :class="{ 'stop--done': s.status !== 'pending' }" @click.stop>
                  <span class="stop__n" :style="{ background: tripColor(i) }">{{ s.sequence }}</span>
                  <span class="stop__text">
                    <b>{{ s.code }} · {{ s.customer_name }}</b>
                    <span>{{ s.barangay || s.address }} · {{ containers(s.containers) }}<template v-if="s.eta"> · about {{ timeOf(s.eta) }}</template></span>
                  </span>
                  <span v-if="editable(t)" class="stop__btns">
                    <button type="button" class="ibtn" :disabled="k === 0 || busy === `trip:${t.id}`" :aria-label="`Move ${s.code} earlier`" @click="moveStop(t, k, -1)"><ion-icon :icon="arrowUpOutline" /></button>
                    <button type="button" class="ibtn" :disabled="k === t.stops.length - 1 || busy === `trip:${t.id}`" :aria-label="`Move ${s.code} later`" @click="moveStop(t, k, 1)"><ion-icon :icon="arrowDownOutline" /></button>
                    <button type="button" class="ibtn" :disabled="busy === `trip:${t.id}`" :aria-label="`Take ${s.code} off this trip`" @click="removeStop(t, s)"><ion-icon :icon="closeOutline" /></button>
                    <select v-if="editableTrips.length > 1" class="mini" :aria-label="`Move ${s.code} to another trip`" :disabled="busy === `trip:${t.id}`" @change="moveTo(t, s, $event.target.value); $event.target.value = ''">
                      <option value="">Move to…</option>
                      <option v-for="o in editableTrips.filter((x) => x.id !== t.id)" :key="o.id" :value="o.id">{{ o.vehicle.name }}</option>
                    </select>
                  </span>
                </li>
              </ol>

              <footer v-if="t.status === 'draft' || t.status === 'approved'" class="trip__foot" @click.stop>
                <AppButton v-if="t.status === 'draft'" size="sm" :loading="busy === `trip:${t.id}`" :disabled="!t.rider" @click="approve(t)">Approve trip</AppButton>
                <span v-if="t.status === 'draft' && !t.rider" class="af-small">Choose a rider to approve.</span>
                <AppButton variant="ghost" size="sm" :disabled="busy === `trip:${t.id}`" @click="removeTrip(t)">Delete trip</AppButton>
              </footer>
            </article>

            <section v-if="unplanned.length" class="af-panel" aria-labelledby="unp">
              <SectionHead title="Not on a trip yet" :sub="`${unplanned.length} confirmed ${unplanned.length === 1 ? 'order' : 'orders'}`" />
              <ul class="plain">
                <li v-for="o in unplanned" :key="o.order_id" class="unp">
                  <span class="stop__text">
                    <b>{{ o.code }} · {{ o.customer_name }}</b>
                    <span>{{ o.barangay || o.address }} · {{ containers(o.containers) }}</span>
                  </span>
                  <select class="mini" :aria-label="`Add ${o.code} to a trip`" :disabled="busy === `order:${o.order_id}` || (!editableTrips.length && !freeVehicles.length)" @change="addOrder(o, $event.target.value); $event.target.value = ''">
                    <option value="">Add to…</option>
                    <option v-for="t in editableTrips" :key="`t${t.id}`" :value="`t:${t.id}`">Trip: {{ t.vehicle.name }}</option>
                    <option v-for="v in freeVehicles" :key="`v${v.id}`" :value="`v:${v.id}`">New trip: {{ v.name }}</option>
                  </select>
                </li>
              </ul>
              <p v-if="!vehicles.length" class="af-small">No vehicles are set up. Ask the owner to add them on the Vehicles screen.</p>
            </section>

            <section v-if="likely?.households.length" class="af-panel tentative" aria-labelledby="likely-title">
              <SectionHead
                title="Likely to reorder (tentative)"
                :sub="`${containers(likely.predicted)} predicted for ${friendlyDay(day).toLowerCase()}. Not orders yet, so they can't go on a trip.`"
              />
              <ul class="plain">
                <li v-for="h in likely.households" :key="h.prediction_id" class="unp">
                  <span class="stop__text">
                    <b>{{ h.customer }}</b>
                    <span>{{ h.barangay || h.address }} · {{ containers(h.containers) }}<template v-if="h.overdue_days"> · ran out {{ h.overdue_days }}d ago</template></span>
                  </span>
                </li>
              </ul>
            </section>
          </div>

          <aside class="map" aria-label="Map">
            <TripsMap :station="station" :trips="trips" :unplanned="unplanned" :selected-id="selectedId" height="460px" />
            <p class="af-small">Tap a trip to highlight it. Grey rings are orders not on a trip.</p>
          </aside>
        </div>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.top { display: grid; gap: 6px; }
.top p { margin: 0; }
.title { margin: 0; font-family: var(--af-display); font-size: clamp(26px, 3.4vw, 34px); font-weight: 650; letter-spacing: -0.04em; }
.bar-controls { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
.bar-controls > :last-child { margin-left: auto; }
.note { margin: -6px 0 0; }
.layout { display: grid; gap: 16px; align-items: start; }
@media (min-width: 1100px) { .layout { grid-template-columns: minmax(0, 1fr) 460px; } .map { position: sticky; top: 16px; } }
.col { display: grid; gap: 14px; min-width: 0; }
.map { display: grid; gap: 8px; }
.map p { margin: 0; }

.trip { display: grid; gap: 14px; cursor: pointer; }
.trip--sel { outline: 2px solid var(--af-primary); outline-offset: 2px; }
.trip__head { display: flex; gap: 12px; align-items: center; }
.dot { width: 14px; height: 14px; border-radius: 50%; flex: none; }
.trip__title { display: grid; min-width: 0; flex: 1; }
.trip__title b { font-size: 17px; font-weight: 800; }
.trip__stats { white-space: nowrap; }
.load { display: grid; gap: 6px; }
.load__top { display: flex; justify-content: space-between; font-size: 13.5px; font-weight: 600; color: var(--af-ink-2); }
.load__top b { color: var(--af-ink); }
.load__bar { height: 10px; border-radius: 99px; background: var(--af-surface-2); overflow: hidden; }
.load__bar span { display: block; height: 100%; border-radius: 99px; transition: width 0.4s ease; }
.stale { margin: 0; padding: 10px 14px; border-radius: 12px; background: var(--af-sun-tint); color: var(--af-ink); font-size: 14px; font-weight: 650; }
.rider { display: flex; gap: 10px; align-items: center; font-size: 14px; font-weight: 700; }
select { min-height: 44px; border-radius: 12px; border: 1px solid var(--af-line); background: var(--af-surface); color: var(--af-ink); font: 600 14px var(--af-font); padding: 0 10px; }
.rider select { flex: 1; max-width: 280px; }
.mini { min-height: 40px; max-width: 150px; }

.stops { list-style: none; margin: 0; padding: 0; display: grid; }
.stop, .unp { display: grid; grid-template-columns: 30px minmax(0, 1fr) auto; gap: 10px; align-items: center; padding: 10px 0; border-top: 1px solid var(--af-line); }
.unp { grid-template-columns: minmax(0, 1fr) auto; }
.stop--done { opacity: 0.55; }
.stop__n { width: 28px; height: 28px; display: grid; place-items: center; border-radius: 50%; color: #fff; font: 800 13px var(--af-font); text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4); }
.stop__text { display: grid; gap: 2px; min-width: 0; }
.stop__text b { font-size: 14.5px; font-weight: 800; }
.stop__text span { font-size: 13px; color: var(--af-ink-2); font-weight: 550; }
.stop__btns { display: flex; gap: 4px; align-items: center; flex-wrap: wrap; justify-content: flex-end; }
.ibtn { width: 40px; height: 40px; display: grid; place-items: center; border-radius: 50%; border: 0; background: var(--af-surface-2); color: var(--af-primary); font-size: 17px; cursor: pointer; }
.ibtn:disabled { opacity: 0.35; cursor: default; }
.trip__foot { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.plain { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.warn { border-color: var(--af-danger); }
.err { display: grid; gap: 8px; justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }
@media (max-width: 640px) {
  .stop { grid-template-columns: 30px minmax(0, 1fr); }
  .stop__btns { grid-column: 1 / -1; justify-content: flex-start; }
  .bar-controls > :last-child { margin-left: 0; width: 100%; }
}
.tentative { border: 1px dashed var(--af-line-strong); }
.tentative .stop__text b { font-weight: 700; }
</style>
