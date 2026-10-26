<!--
  AddressFormModal — add or edit a delivery address with a map pin.
  Usage: <AddressFormModal :is-open="open" :address="editing" :settings="settings" @close="open = false" @saved="onSaved" />
-->
<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { IonButton, IonButtons, IonContent, IonFooter, IonHeader, IonIcon, IonModal, IonTitle, IonToolbar } from '@ionic/vue'
import { Geolocation } from '@capacitor/geolocation'
import { locateOutline } from 'ionicons/icons'

import AppButton from '@/components/ui/AppButton.vue'
import MapPicker from '@/components/map/MapPicker.vue'
import TextField from '@/components/form/TextField.vue'
import { BARANGAYS } from '@/constants/barangays'
import { saveAddress } from '@/services/customerService'
import { distanceKm } from '@/utils/geo'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  address: { type: Object, default: null }, // null = new address
  settings: { type: Object, required: true },
})
const emit = defineEmits(['close', 'saved'])

const LABELS = ['Home', 'Work', "Mama's house"]
const empty = () => ({ id: null, label: 'Home', barangay: '', street: '', landmark: '', lat: null, lng: null })

const form = reactive(empty())
const errors = reactive({})
const saving = ref(false)
const locating = ref(false)
const formError = ref('')

// Fill the form each time the modal opens
watch(
  () => props.isOpen,
  (open) => {
    if (!open) return
    Object.assign(form, empty(), props.address ? { ...props.address } : {})
    Object.keys(errors).forEach((k) => delete errors[k])
    formError.value = ''
  },
)

const pin = computed({
  get: () => (form.lat != null ? { lat: form.lat, lng: form.lng } : null),
  set: (v) => {
    form.lat = v.lat
    form.lng = v.lng
  },
})

const distance = computed(() => (pin.value ? distanceKm(pin.value, props.settings.station) : null))
const outside = computed(() => distance.value != null && distance.value > props.settings.service_radius_km)

function pickBarangay(name) {
  form.barangay = name
  const b = BARANGAYS.find((x) => x.name === name)
  if (b && form.lat == null) pin.value = { lat: b.lat, lng: b.lng } // rough spot; customer fine-tunes
}

async function useMyLocation() {
  locating.value = true
  formError.value = ''
  try {
    const pos = await Geolocation.getCurrentPosition({ enableHighAccuracy: true, timeout: 10000 })
    pin.value = { lat: pos.coords.latitude, lng: pos.coords.longitude }
  } catch {
    formError.value = "Couldn't get your location. Allow location access, or tap the map to place the pin."
  } finally {
    locating.value = false
  }
}

function validate() {
  Object.keys(errors).forEach((k) => delete errors[k])
  if (!form.label.trim()) errors.label = 'Give this address a name, like "Home".'
  if (!form.barangay) errors.barangay = 'Choose your barangay.'
  if (!form.street.trim()) errors.street = 'Enter your street, purok or house number.'
  if (form.landmark.trim().length < 4) errors.landmark = 'Add a landmark the rider can see, like a gate color or store.'
  if (form.lat == null) errors.pin = 'Place the pin on your house.'
  else if (outside.value) errors.pin = `This pin is ${distance.value.toFixed(1)} km away. We deliver within ${props.settings.service_radius_km} km of the station.`
  return Object.keys(errors).length === 0
}

async function submit() {
  if (!validate()) return
  saving.value = true
  formError.value = ''
  try {
    const saved = await saveAddress({ ...form })
    emit('saved', saved)
    emit('close')
  } catch (e) {
    formError.value = e.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <ion-modal :is-open="isOpen" @did-dismiss="emit('close')">
    <ion-header>
      <ion-toolbar>
        <ion-buttons slot="start">
          <ion-button @click="emit('close')">Cancel</ion-button>
        </ion-buttons>
        <ion-title>{{ form.id ? 'Edit address' : 'New address' }}</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content>
      <form class="af-addr" novalidate @submit.prevent="submit">
        <p v-if="formError" class="af-addr__alert" role="alert">{{ formError }}</p>

        <div class="af-addr__labels" role="group" aria-label="Quick names">
          <button v-for="l in LABELS" :key="l" type="button" class="af-chip" :aria-pressed="form.label === l" @click="form.label = l">
            {{ l }}
          </button>
        </div>
        <TextField v-model="form.label" label="Address name" required :error="errors.label" :maxlength="30" />

        <div class="af-field-select">
          <label for="addr-barangay">Barangay</label>
          <select id="addr-barangay" :value="form.barangay" :aria-invalid="!!errors.barangay || undefined" @change="pickBarangay($event.target.value)">
            <option value="" disabled>Choose barangay</option>
            <option v-for="b in BARANGAYS" :key="b.name" :value="b.name">{{ b.name }}</option>
          </select>
          <p v-if="errors.barangay" class="af-err">{{ errors.barangay }}</p>
        </div>

        <TextField v-model="form.street" label="Street, purok, house no." required autocomplete="street-address" :error="errors.street" />
        <TextField
          v-model="form.landmark"
          label="Landmark"
          required
          placeholder="Blue gate beside the chapel"
          hint="Something the rider can see: gate color, store, school."
          :error="errors.landmark"
        />

        <div class="af-addr__map">
          <div class="af-addr__maphead">
            <span class="af-addr__maplabel">Pin your house</span>
            <AppButton variant="ghost" size="sm" :loading="locating" @click="useMyLocation">
              <ion-icon :icon="locateOutline" aria-hidden="true" /> Use my location
            </AppButton>
          </div>
          <MapPicker v-model="pin" :station="settings.station" :radius-km="settings.service_radius_km" height="280px" />
          <p v-if="errors.pin" class="af-err">{{ errors.pin }}</p>
          <p v-else-if="distance != null" class="af-addr__dist" :class="{ 'af-addr__dist--out': outside }">
            {{ distance.toFixed(1) }} km from the station ·
            {{ outside ? 'outside our delivery area' : 'inside our delivery area' }}
          </p>
        </div>
      </form>
    </ion-content>

    <ion-footer class="ion-no-border">
      <div class="af-addr__footer">
        <AppButton block size="lg" :loading="saving" @click="submit">Save address</AppButton>
      </div>
    </ion-footer>
  </ion-modal>
</template>

<style scoped>
.af-addr { display: grid; gap: var(--af-s4); padding: var(--af-s5) var(--af-s4); max-width: 640px; margin: 0 auto; }
.af-addr__alert { margin: 0; padding: 12px 14px; border-radius: var(--af-r-sm); background: var(--af-danger-tint); color: var(--af-danger); font-weight: 600; font-size: 14px; }
.af-addr__labels { display: flex; gap: var(--af-s2); flex-wrap: wrap; }
.af-chip {
  min-height: 40px;
  padding: 0 14px;
  border-radius: var(--af-r-pill);
  border: 1.5px solid var(--af-line);
  background: var(--af-surface);
  color: var(--af-ink);
  font: 600 14px var(--af-font);
  cursor: pointer;
}
.af-chip[aria-pressed='true'] { border-color: var(--af-primary); background: var(--af-primary-tint); color: var(--af-primary); }

.af-field-select { display: grid; gap: 6px; }
.af-field-select label { font-size: 14px; font-weight: 700; }
.af-field-select select {
  min-height: 48px;
  padding: 0 12px;
  font: 500 16px var(--af-font);
  color: var(--af-ink);
  background: var(--af-surface);
  border: 1.5px solid var(--af-line);
  border-radius: var(--af-r-sm);
}
.af-field-select select:focus { outline: none; border-color: var(--af-primary); box-shadow: 0 0 0 3px var(--af-primary-tint); }

.af-addr__map { display: grid; gap: var(--af-s2); }
.af-addr__maphead { display: flex; justify-content: space-between; align-items: center; gap: var(--af-s2); flex-wrap: wrap; }
.af-addr__maplabel { font-size: 14px; font-weight: 700; }
.af-addr__dist { margin: 0; font-size: 13px; font-weight: 600; color: var(--af-success); }
.af-addr__dist--out { color: var(--af-danger); }
.af-err { margin: 0; font-size: 13px; font-weight: 600; color: var(--af-danger); }
.af-addr__footer { padding: var(--af-s3) var(--af-s4) calc(var(--af-s3) + env(safe-area-inset-bottom, 0px)); background: var(--af-surface); border-top: 1px solid var(--af-line); }
.af-addr__footer > * { max-width: 640px; margin: 0 auto; display: flex; }
</style>
