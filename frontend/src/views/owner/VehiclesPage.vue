<!--
  Owner: vehicles. The tricycles and multicabs that carry the water.
  "Capacity" is how many 5-gallon containers fit at once. The planner never loads more than that.
  Switch a vehicle off (in repair, no driver) and the planner skips it. A vehicle with trips on
  record can't be deleted, only switched off.
-->
<script setup>
import { computed, reactive, ref } from 'vue'
import { IonContent, IonHeader, IonIcon, IonPage, IonTitle, IonToolbar, onIonViewWillEnter } from '@ionic/vue'
import { addOutline, createOutline, trashOutline } from 'ionicons/icons'

import AppButton from '@/components/ui/AppButton.vue'
import SectionHead from '@/components/dash/SectionHead.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import TextField from '@/components/form/TextField.vue'
import { showToast } from '@/composables/useToast'
import { deleteVehicle, fetchVehicles, saveVehicle } from '@/services/fleetService'
import { containers } from '@/utils/format'

const vehicles = ref([])
const loading = ref(true)
const error = ref(null)
const busyId = ref(null)

const blank = () => ({ id: null, name: '', plate: '', capacity: '', is_available: true })
const form = reactive({ ...blank(), busy: false, error: '' })
const editing = computed(() => form.id != null)
const onRoad = computed(() => vehicles.value.filter((v) => v.is_available).length)
const totalCapacity = computed(() => vehicles.value.filter((v) => v.is_available).reduce((n, v) => n + v.capacity, 0))

async function load() {
  error.value = null
  try {
    vehicles.value = await fetchVehicles()
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
onIonViewWillEnter(load)

function edit(v) {
  Object.assign(form, { ...v, capacity: String(v.capacity), busy: false, error: '' })
  document.querySelector('.vform')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
const startNew = () => Object.assign(form, { ...blank(), busy: false, error: '' })

async function submit() {
  form.error = ''
  form.busy = true
  try {
    const saved = await saveVehicle({ ...form })
    const i = vehicles.value.findIndex((v) => v.id === saved.id)
    if (i >= 0) vehicles.value[i] = saved
    else vehicles.value.push(saved)
    showToast(editing.value ? `${saved.name} saved` : `${saved.name} added. The planner can use it now.`, 'success')
    startNew()
  } catch (e) {
    form.error = e.message
  } finally {
    form.busy = false
  }
}

async function toggle(v) {
  busyId.value = v.id
  try {
    const saved = await saveVehicle({ ...v, is_available: !v.is_available })
    Object.assign(v, saved)
    showToast(saved.is_available ? `${v.name} is back in service` : `${v.name} is switched off. The planner will skip it.`, 'success')
  } catch (e) {
    showToast(e.message, 'danger')
  } finally {
    busyId.value = null
  }
}

async function remove(v) {
  busyId.value = v.id
  try {
    await deleteVehicle(v.id)
    vehicles.value = vehicles.value.filter((x) => x.id !== v.id)
    showToast(`${v.name} deleted`, 'success')
  } catch (e) {
    showToast(e.message, 'danger')
  } finally {
    busyId.value = null
  }
}
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar><ion-title>Vehicles</ion-title></ion-toolbar>
    </ion-header>
    <ion-content>
      <div class="af-container af-dash">
        <header class="top">
          <h1 class="title">Vehicles</h1>
          <p class="af-small">Tricycles and multicabs. The planner fills each one up to its capacity and never more.</p>
        </header>

        <div class="layout">
          <section class="af-panel" aria-labelledby="vlist">
            <SectionHead title="Your fleet" :sub="`${onRoad} in service · room for ${containers(totalCapacity)} at once`">
              <AppButton variant="secondary" size="sm" @click="startNew"><ion-icon :icon="addOutline" aria-hidden="true" /> New vehicle</AppButton>
            </SectionHead>
            <SkeletonList v-if="loading" :rows="3" />
            <div v-else-if="error" class="err" role="alert">
              <b>Couldn't load vehicles</b>
              <p>{{ error.message }}</p>
              <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
            </div>
            <p v-else-if="!vehicles.length" class="af-small">No vehicles yet. Add your first one on the right. The planner needs at least one.</p>
            <ul v-else class="vlist">
              <li v-for="v in vehicles" :key="v.id" class="veh" :class="{ 'veh--off': !v.is_available }">
                <span class="veh__text">
                  <b>{{ v.name }}</b>
                  <span>Plate {{ v.plate }} · {{ v.is_available ? 'In service' : 'Switched off' }}</span>
                </span>
                <span class="veh__cap"><b>{{ v.capacity }}</b> containers</span>
                <span class="veh__btns">
                  <button type="button" class="ibtn" :aria-label="`Edit ${v.name}`" @click="edit(v)"><ion-icon :icon="createOutline" /></button>
                  <AppButton :variant="v.is_available ? 'ghost' : 'secondary'" size="sm" :loading="busyId === v.id" @click="toggle(v)">
                    {{ v.is_available ? 'Switch off' : 'Switch on' }}
                  </AppButton>
                  <button type="button" class="ibtn ibtn--danger" :aria-label="`Delete ${v.name}`" :disabled="busyId === v.id" @click="remove(v)"><ion-icon :icon="trashOutline" /></button>
                </span>
              </li>
            </ul>
          </section>

          <section class="af-panel vform" aria-labelledby="vform">
            <SectionHead :title="editing ? `Edit ${form.name || 'vehicle'}` : 'Add a vehicle'" :sub="editing ? 'Changes apply to the next plan' : 'Ready for the planner as soon as you save'" />
            <form class="form" novalidate @submit.prevent="submit">
              <TextField v-model="form.name" label="Name" placeholder="Tricycle 1" required />
              <div class="two">
                <TextField v-model="form.plate" label="Plate number" placeholder="ABC 1234" required />
                <TextField v-model="form.capacity" label="Containers it carries" type="number" inputmode="numeric" required />
              </div>
              <p class="af-small">Count full containers. Empties coming back also take space, and the planner counts them.</p>
              <p v-if="form.error" class="form__err" role="alert">{{ form.error }}</p>
              <AppButton type="submit" size="lg" block :loading="form.busy">{{ editing ? 'Save changes' : 'Add vehicle' }}</AppButton>
              <AppButton v-if="editing" variant="ghost" block @click="startNew">Cancel editing</AppButton>
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
@media (min-width: 1100px) { .layout { grid-template-columns: minmax(0, 1fr) 400px; } .vform { position: sticky; top: 16px; } }
.vlist { list-style: none; margin: 0; padding: 0; display: grid; }
.veh { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; gap: 12px; align-items: center; padding: 12px 2px; border-bottom: 1px solid var(--af-line); }
.veh:last-child { border-bottom: 0; }
.veh--off { opacity: 0.55; }
.veh__text { display: grid; gap: 2px; min-width: 0; }
.veh__text b { font-size: 15px; font-weight: 800; }
.veh__text span { font-size: 13px; color: var(--af-ink-2); font-weight: 550; }
.veh__cap { font-size: 13px; color: var(--af-ink-2); font-weight: 600; white-space: nowrap; }
.veh__cap b { font-family: var(--af-display); font-size: 20px; color: var(--af-ink); margin-right: 2px; }
.veh__btns { display: flex; gap: 6px; align-items: center; }
.ibtn { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 50%; border: 0; background: var(--af-surface-2); color: var(--af-primary); font-size: 18px; cursor: pointer; }
.ibtn--danger { color: var(--af-danger); }
.form { display: grid; gap: 14px; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.form__err { margin: 0; padding: 10px 14px; border-radius: 12px; background: var(--af-danger-tint); color: var(--af-danger); font-size: 14px; font-weight: 650; }
.form .af-small { margin: 0; line-height: 1.45; }
.err { display: grid; gap: 8px; justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }
@media (max-width: 640px) { .veh { grid-template-columns: minmax(0, 1fr) auto; } .veh__btns { grid-column: 1 / -1; } }
</style>
