<!-- Order water: quantity, address, day + time, empties, notes. -->
<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  IonContent,
  IonFooter,
  IonHeader,
  IonIcon,
  IonPage,
  IonTitle,
  IonToolbar,
  onIonViewWillEnter,
  useIonRouter,
} from '@ionic/vue'
import { addOutline, partlySunnyOutline, sunnyOutline } from 'ionicons/icons'

import AddressFormModal from '@/components/address/AddressFormModal.vue'
import AppButton from '@/components/ui/AppButton.vue'
import LiquidFill from '@/components/ui/LiquidFill.vue'
import QuantityStepper from '@/components/form/QuantityStepper.vue'
import SegmentedControl from '@/components/form/SegmentedControl.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import TextField from '@/components/form/TextField.vue'
import { showToast } from '@/composables/useToast'
import {
  createOrder,
  getCustomerSummary,
  getOrderSettings,
  listAddresses,
  periodOpen,
} from '@/services/customerService'
import { PERIODS, clockLabel, containers, dateISO, peso } from '@/utils/format'

const route = useRoute()
const ionRouter = useIonRouter()

const loading = ref(true)
const loadError = ref(null)
const settings = ref(null)
const addresses = ref([])
const held = ref(0)

const form = reactive({ quantity: 3, address_id: '', day: 'today', period: 'morning', empties: 0, notes: '' })
const submitting = ref(false)
const submitError = ref('')
const addrOpen = ref(false)

const deliveryDate = computed(() => dateISO(form.day === 'today' ? 0 : 1))
const total = computed(() => (settings.value ? form.quantity * settings.value.price_per_container : 0))

const periodOptions = computed(() =>
  Object.entries(PERIODS).map(([value, p]) => ({
    value,
    ...p,
    icon: value === 'morning' ? sunnyOutline : partlySunnyOutline,
    open: settings.value ? periodOpen(settings.value, deliveryDate.value, value) : true,
    cutoff: settings.value?.cutoff[value],
  })),
)
const todayClosed = computed(() =>
  settings.value ? !Object.keys(PERIODS).some((p) => periodOpen(settings.value, dateISO(0), p)) : false,
)
const dayOptions = computed(() => [
  { value: 'today', label: 'Today', disabled: todayClosed.value },
  { value: 'tomorrow', label: 'Tomorrow' },
])

// Keep the choice valid: if the picked time closed, move to the next open one
watch([deliveryDate, settings], () => {
  if (!settings.value) return
  if (form.day === 'today' && todayClosed.value) form.day = 'tomorrow'
  if (!periodOpen(settings.value, deliveryDate.value, form.period)) {
    form.period = periodOptions.value.find((p) => p.open)?.value ?? 'morning'
  }
})

// Can't return more empties than you have, or more than you're ordering
const maxEmpties = computed(() => Math.min(held.value, form.quantity))
watch(maxEmpties, (m) => {
  if (form.empties > m) form.empties = m
})

async function load() {
  loading.value = true
  loadError.value = null
  try {
    const [s, a, summary] = await Promise.all([getOrderSettings(), listAddresses(), getCustomerSummary()])
    settings.value = s
    addresses.value = a
    held.value = summary.containers_held

    // Pre-fill from "Order again" (?qty=3&address=a_x)
    const qty = Number(route.query.qty)
    if (qty >= 1 && qty <= s.max_containers_per_order) form.quantity = qty
    const wanted = a.find((x) => x.id === route.query.address)
    form.address_id = wanted?.id ?? a.find((x) => x.is_default)?.id ?? a[0]?.id ?? ''
    form.empties = Math.min(held.value, form.quantity)
  } catch (e) {
    loadError.value = e
  } finally {
    loading.value = false
  }
}
onIonViewWillEnter(load)

function onAddressSaved(addr) {
  addresses.value.push(addr)
  form.address_id = addr.id
  showToast('Address saved', 'success')
}

async function submit() {
  submitError.value = ''
  if (!form.address_id) {
    submitError.value = 'Add a delivery address first.'
    return
  }
  submitting.value = true
  try {
    const order = await createOrder({
      quantity: form.quantity,
      address_id: form.address_id,
      delivery_date: deliveryDate.value,
      period: form.period,
      empties_to_return: form.empties,
      notes: form.notes,
    })
    showToast(`Order ${order.code} placed. We'll confirm it soon.`, 'success')
    form.notes = ''
    ionRouter.navigate(`/customer/orders/${order.id}`, 'forward', 'push')
  } catch (e) {
    submitError.value = e.message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-title>Order water</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content>
      <div class="af-container narrow">
        <div v-if="loading" class="af-card"><SkeletonList :rows="4" :avatar="false" /></div>

        <div v-else-if="loadError" class="af-card err" role="alert">
          <b>Couldn't open the order form</b>
          <p>{{ loadError.message }}</p>
          <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>

        <form v-else class="stack" novalidate @submit.prevent="submit">
          <p v-if="submitError" class="alert" role="alert">{{ submitError }}</p>

          <!-- 1. Quantity -->
          <section class="af-card block" aria-labelledby="q-title">
            <div class="block__head">
              <h2 id="q-title" class="af-h3">How many containers?</h2>
              <span class="af-small">5 gallons · {{ peso(settings.price_per_container) }} each</span>
            </div>
            <div class="qty">
              <LiquidFill :level="form.quantity / settings.max_containers_per_order" shape="jug" :size="96" class="qty__jug" />
              <QuantityStepper v-model="form.quantity" :min="1" :max="settings.max_containers_per_order" label="Number of containers" unit="containers" />
            </div>
          </section>

          <!-- 2. Address -->
          <section class="af-card block" aria-labelledby="a-title">
            <h2 id="a-title" class="af-h3">Deliver to</h2>
            <div class="choices" role="radiogroup" aria-labelledby="a-title">
              <button
                v-for="a in addresses"
                :key="a.id"
                type="button"
                role="radio"
                class="choice"
                :aria-checked="form.address_id === a.id"
                @click="form.address_id = a.id"
              >
                <span class="choice__radio" aria-hidden="true"></span>
                <span class="choice__text">
                  <b>{{ a.label }}</b>
                  <span>{{ a.street }}, {{ a.barangay }}</span>
                  <span class="choice__mark">{{ a.landmark }}</span>
                </span>
              </button>
            </div>
            <AppButton variant="ghost" @click="addrOpen = true">
              <ion-icon :icon="addOutline" aria-hidden="true" /> Add a new address
            </AppButton>
          </section>

          <!-- 3. When -->
          <section class="af-card block" aria-labelledby="w-title">
            <h2 id="w-title" class="af-h3">When</h2>
            <SegmentedControl v-model="form.day" :options="dayOptions" label="Delivery day" block />
            <div class="periods" role="radiogroup" aria-label="Delivery time">
              <button
                v-for="p in periodOptions"
                :key="p.value"
                type="button"
                role="radio"
                class="period"
                :aria-checked="form.period === p.value"
                :disabled="!p.open"
                @click="form.period = p.value"
              >
                <ion-icon :icon="p.icon" aria-hidden="true" />
                <b>{{ p.label }}</b>
                <span>{{ p.hours }}</span>
                <span v-if="!p.open" class="period__closed">Closed for today</span>
              </button>
            </div>
            <p class="af-small">
              Same-day orders: morning before {{ clockLabel(settings.cutoff.morning) }}, afternoon before {{ clockLabel(settings.cutoff.afternoon) }}.
            </p>
          </section>

          <!-- 4. Empties -->
          <section class="af-card block" aria-labelledby="e-title">
            <div class="block__head">
              <h2 id="e-title" class="af-h3">Empty containers to return</h2>
              <span class="af-small">You have {{ containers(held) }} at home</span>
            </div>
            <QuantityStepper v-model="form.empties" :min="0" :max="maxEmpties" label="Empty containers to return" unit="empties" />
            <p class="af-small">This helps us save space on the tricycle for your empties.</p>
          </section>

          <!-- 5. Notes -->
          <section class="af-card block">
            <TextField v-model="form.notes" label="Note for the rider" multiline :maxlength="200" placeholder="Example: Please knock loudly, the doorbell is broken." />
          </section>
        </form>
      </div>

      <AddressFormModal v-if="settings" :is-open="addrOpen" :settings="settings" @close="addrOpen = false" @saved="onAddressSaved" />
    </ion-content>

    <ion-footer v-if="!loading && !loadError" class="ion-no-border">
      <div class="bar">
        <div class="bar__sum">
          <b>{{ peso(total) }}</b>
          <span>{{ containers(form.quantity) }} · cash on delivery</span>
        </div>
        <AppButton size="lg" :loading="submitting" @click="submit">Place order</AppButton>
      </div>
    </ion-footer>
  </ion-page>
</template>

<style scoped>
.narrow { max-width: 720px; }
.stack { display: grid; gap: var(--af-s4); }
.alert { margin: 0; padding: 12px 16px; border-radius: var(--af-r-sm); background: var(--af-danger-tint); color: var(--af-danger); border: 1px solid color-mix(in srgb, var(--af-danger) 30%, transparent); font-weight: 650; font-size: 14px; }
.block { display: grid; gap: var(--af-s4); }
.block h2 { margin: 0; }
.block p { margin: 0; }
.block__head { display: flex; justify-content: space-between; align-items: baseline; gap: var(--af-s2); flex-wrap: wrap; }
.qty { display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: var(--af-s4) var(--af-s6); padding: var(--af-s2) 0; }
.qty__jug { filter: drop-shadow(0 14px 20px rgba(0, 0, 0, 0.25)) drop-shadow(0 0 16px color-mix(in srgb, var(--af-water) 40%, transparent)); }
@media (max-width: 400px) { .qty { gap: var(--af-s3); } .qty__jug { width: 64px; height: auto; } }

.choices { display: grid; gap: var(--af-s2); }
.choice {
  display: grid;
  grid-template-columns: 22px 1fr;
  gap: var(--af-s3);
  align-items: start;
  text-align: left;
  padding: var(--af-s4);
  border-radius: var(--af-r-md);
  border: 1.5px solid var(--af-line);
  background: var(--af-surface);
  color: var(--af-ink);
  font-family: var(--af-font);
  cursor: pointer;
  transition: border-color var(--af-dur) var(--af-ease), background var(--af-dur) var(--af-ease), box-shadow var(--af-dur) var(--af-ease);
}
.choice:hover { border-color: color-mix(in srgb, var(--af-primary) 45%, var(--af-line)); }
.choice[aria-checked='true'] { border-color: var(--af-primary); background: var(--af-primary-tint); box-shadow: 0 0 0 4px color-mix(in srgb, var(--af-primary) 12%, transparent); }
.choice__radio { width: 22px; height: 22px; border-radius: 50%; border: 2px solid var(--af-line-strong); margin-top: 1px; display: grid; place-items: center; transition: border-color var(--af-dur) var(--af-ease); }
.choice[aria-checked='true'] .choice__radio { border-color: var(--af-primary); }
.choice[aria-checked='true'] .choice__radio::after { content: ''; width: 10px; height: 10px; border-radius: 50%; background: var(--af-primary); box-shadow: 0 0 8px var(--af-primary); }
.choice__text { display: grid; gap: 2px; min-width: 0; }
.choice__text b { font-size: 15px; font-weight: 800; }
.choice__text span { font-size: 14px; color: var(--af-ink-2); }
.choice__mark { font-style: italic; }

.periods { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--af-s3); }
.period {
  display: grid;
  gap: 2px;
  justify-items: start;
  text-align: left;
  padding: var(--af-s4);
  border-radius: var(--af-r-md);
  border: 1.5px solid var(--af-line);
  background: var(--af-surface);
  color: var(--af-ink);
  font-family: var(--af-font);
  cursor: pointer;
  transition: border-color var(--af-dur) var(--af-ease), background var(--af-dur) var(--af-ease), box-shadow var(--af-dur) var(--af-ease);
}
.period ion-icon { font-size: 26px; color: var(--af-primary); margin-bottom: 6px; }
.period b { font-size: 16px; font-weight: 800; }
.period span { font-size: 13px; color: var(--af-ink-2); font-variant-numeric: tabular-nums; }
.period:hover:not(:disabled) { border-color: color-mix(in srgb, var(--af-primary) 45%, var(--af-line)); }
.period[aria-checked='true'] { border-color: var(--af-primary); background: var(--af-primary-tint); box-shadow: 0 0 0 4px color-mix(in srgb, var(--af-primary) 12%, transparent); }
.period:disabled { opacity: 0.5; cursor: not-allowed; }
.period__closed { color: var(--af-danger) !important; font-weight: 750; } /* beats .period span */

/* Sticky summary bar: floats above the content like the tab bar */
.bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--af-s4);
  max-width: 720px;
  margin: 0 auto;
  padding: var(--af-s3) var(--af-s4) calc(var(--af-s3) + env(safe-area-inset-bottom, 0px));
  background: color-mix(in srgb, var(--af-surface) 92%, transparent);
  border-top: 1px solid var(--af-line);
  backdrop-filter: saturate(160%) blur(16px);
  -webkit-backdrop-filter: saturate(160%) blur(16px);
}
.bar__sum { display: grid; gap: 2px; }
.bar__sum b { font-family: var(--af-display); font-size: 26px; font-weight: 700; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }
.bar__sum span { font-size: 13px; color: var(--af-ink-2); }
@media (min-width: 760px) {
  .bar { margin-bottom: var(--af-s4); border: 1px solid var(--af-line); border-radius: var(--af-r-lg); box-shadow: var(--af-shadow-3); padding: var(--af-s3) var(--af-s3) var(--af-s3) var(--af-s5); }
}

.err { display: grid; gap: var(--af-s2); justify-items: start; border-color: color-mix(in srgb, var(--af-danger) 40%, var(--af-line)); }
.err b { color: var(--af-danger); font-weight: 800; }
.err p { margin: 0; color: var(--af-ink-2); }
</style>
