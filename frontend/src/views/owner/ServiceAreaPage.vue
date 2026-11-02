<!--
  Owner: service area. Where the station is, how far it delivers, and which barangays it serves.
  Two rules apply to every new order: the address must be inside the radius, and (if you tick
  barangays) its barangay must be on the list. Leave every barangay unticked to serve the whole circle.
  Distance is straight-line from the station.
-->
<script setup>
import { computed, ref } from 'vue'
import { IonContent, IonHeader, IonPage, IonTitle, IonToolbar, onIonViewWillEnter } from '@ionic/vue'

import AppButton from '@/components/ui/AppButton.vue'
import AreaMap from '@/components/map/AreaMap.vue'
import SectionHead from '@/components/dash/SectionHead.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import TextField from '@/components/form/TextField.vue'
import { BARANGAYS } from '@/constants/barangays'
import { showToast } from '@/composables/useToast'
import { getServiceArea, saveServiceArea } from '@/services/fleetService'

const loading = ref(true)
const error = ref(null)
const saving = ref(false)
const formError = ref('')
const dirty = ref(false)

const name = ref('AquaFlow Station')
const station = ref({ lat: 13.4117, lng: 121.1803 })
const radiusKm = ref(5)
const served = ref(new Set())

// Saved names that aren't in our built-in list still show up, so nothing is silently dropped
const allBarangays = computed(() => {
  const known = new Set(BARANGAYS.map((b) => b.name))
  const extra = [...served.value].filter((n) => !known.has(n)).map((n) => ({ name: n, lat: null, lng: null }))
  return [...BARANGAYS, ...extra]
})
const mapDots = computed(() => BARANGAYS.map((b) => ({ ...b, served: served.value.size === 0 || served.value.has(b.name) })))

async function load() {
  error.value = null
  try {
    const a = await getServiceArea()
    name.value = a.name
    station.value = { lat: a.lat, lng: a.lng }
    radiusKm.value = a.radius_km
    served.value = new Set(a.barangays)
    dirty.value = false
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
onIonViewWillEnter(load)

function toggle(n) {
  const s = new Set(served.value)
  s.has(n) ? s.delete(n) : s.add(n)
  served.value = s
  dirty.value = true
}
const setRadius = (v) => { radiusKm.value = Number(v); dirty.value = true }
const moveStation = (p) => { station.value = p; dirty.value = true }

async function save() {
  formError.value = ''
  saving.value = true
  try {
    await saveServiceArea({
      name: name.value, lat: station.value.lat, lng: station.value.lng,
      radius_km: Number(radiusKm.value), barangays: [...served.value],
    })
    dirty.value = false
    showToast('Service area saved. New orders follow it right away.', 'success')
  } catch (e) {
    formError.value = e.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar><ion-title>Service area</ion-title></ion-toolbar>
    </ion-header>
    <ion-content>
      <div class="af-container af-dash">
        <header class="top">
          <h1 class="title">Service area</h1>
          <p class="af-small">Where the station is and how far it delivers. Customers outside this area can't place an order.</p>
        </header>

        <SkeletonList v-if="loading" :rows="4" />
        <div v-else-if="error" class="af-panel err" role="alert">
          <b>Couldn't load the service area</b>
          <p>{{ error.message }}</p>
          <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>

        <div v-else class="layout">
          <section class="af-panel" aria-labelledby="map-title">
            <SectionHead title="Station and radius" sub="Click the map or drag the AF marker to move the station" />
            <AreaMap :model-value="station" :radius-km="Number(radiusKm) || 1" :barangays="mapDots" height="400px" @update:model-value="moveStation" />
            <p class="af-small coords">Station at {{ station.lat.toFixed(5) }}, {{ station.lng.toFixed(5) }}</p>
          </section>

          <section class="af-panel side">
            <SectionHead title="Rules" />
            <form class="form" novalidate @submit.prevent="save">
              <TextField :model-value="name" label="Station name" @update:model-value="(v) => { name = v; dirty = true }" />
              <label class="range">
                <span class="range__top"><b>Delivery radius</b><b class="af-money">{{ Number(radiusKm).toFixed(1) }} km</b></span>
                <input type="range" min="1" max="30" step="0.5" :value="radiusKm" aria-label="Delivery radius in kilometres" @input="setRadius($event.target.value)" />
              </label>

              <fieldset class="brgy">
                <legend>Barangays served</legend>
                <p class="af-small">
                  {{ served.size ? `${served.size} ticked. Only these can order.` : 'None ticked: the whole circle can order.' }}
                </p>
                <label v-for="b in allBarangays" :key="b.name" class="chk">
                  <input type="checkbox" :checked="served.has(b.name)" @change="toggle(b.name)" />
                  <span>{{ b.name }}</span>
                </label>
              </fieldset>

              <p v-if="formError" class="form__err" role="alert">{{ formError }}</p>
              <AppButton type="submit" size="lg" block :loading="saving" :disabled="!dirty">Save service area</AppButton>
            </form>
          </section>
        </div>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.top { display: grid; gap: 6px; }
.top p { margin: 0; }
.title { margin: 0; font-family: var(--af-display); font-size: clamp(26px, 3.4vw, 34px); font-weight: 650; letter-spacing: -0.04em; }
.layout { display: grid; gap: 16px; align-items: start; }
@media (min-width: 1000px) { .layout { grid-template-columns: minmax(0, 1fr) 380px; } .side { position: sticky; top: 16px; } }
.coords { margin: 10px 0 0; }
.form { display: grid; gap: 16px; }
.range { display: grid; gap: 8px; }
.range__top { display: flex; justify-content: space-between; font-size: 14px; }
.range input { width: 100%; accent-color: var(--af-primary); min-height: 32px; }
.brgy { border: 0; margin: 0; padding: 0; display: grid; gap: 4px; }
.brgy legend { font-size: 14px; font-weight: 750; padding: 0; margin-bottom: 4px; }
.brgy .af-small { margin: 0 0 6px; }
.chk { display: flex; gap: 10px; align-items: center; min-height: 44px; font-size: 15px; font-weight: 600; cursor: pointer; }
.chk input { width: 20px; height: 20px; accent-color: var(--af-primary); }
.form__err { margin: 0; padding: 10px 14px; border-radius: 12px; background: var(--af-danger-tint); color: var(--af-danger); font-size: 14px; font-weight: 650; }
.err { display: grid; gap: 8px; justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }
</style>
