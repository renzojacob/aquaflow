<!--
  Order water. The quantity sits in a tank whose water rises as containers are added;
  a receipt beside the form (desktop) or a bar under it (phone) keeps the total in view.
  Ordering rules are unchanged: one product, a quantity, an address, a day + time window.
-->
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
import { addOutline, bagHandleOutline, cashOutline, checkmarkCircle, navigateCircleOutline, partlySunnyOutline, removeOutline, ribbonOutline, sunnyOutline, timeOutline } from 'ionicons/icons'
import { KIND } from '@/constants/cart'

import AddressFormModal from '@/components/address/AddressFormModal.vue'
import AppButton from '@/components/ui/AppButton.vue'
import MapPicker from '@/components/map/MapPicker.vue'
import TankHero from '@/components/dash/TankHero.vue'
import QuantityStepper from '@/components/form/QuantityStepper.vue'
import SegmentedControl from '@/components/form/SegmentedControl.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import TextField from '@/components/form/TextField.vue'
import { showToast } from '@/composables/useToast'
import {
  createOrder,
  getCustomerSummary,
  getOrderSettings,
  getSlotAvailability,
  listAddresses,
  periodOpen,
} from '@/services/customerService'
import { PERIODS, clockLabel, containers, dateISO, duration, friendlyDay, peso } from '@/utils/format'

const route = useRoute()
/** Owner-typed descriptions may lack a full stop; add one so the next sentence reads right. */
const sentence = (t) => (t ? (/[.!?]$/.test(t.trim()) ? t.trim() : `${t.trim()}.`) : '')
const ionRouter = useIonRouter()

const loading = ref(true)
const loadError = ref(null)
const settings = ref(null)
const addresses = ref([])
const held = ref(0)

const form = reactive({ quantity: 3, address_id: '', day: 'today', period: 'morning', empties: 0, notes: '' })
const extras = reactive({}) // product id -> how many (everything except the main refill)
const submitting = ref(false)
const submitError = ref('')
const addrOpen = ref(false)

const deliveryDate = computed(() => dateISO(form.day === 'today' ? 0 : 1))
// ---------- the catalog and the cart ----------
// main = the first refill (its quantity is form.quantity, in the tank). Everything else is an "extra".
const products = computed(() => settings.value?.products ?? [])
const main = computed(
  () =>
    products.value.find((p) => p.kind === 'refill') ??
    (settings.value ? { id: null, name: '5-gallon refill', kind: 'refill', price: settings.value.price_per_container, max_per_order: settings.value.max_containers_per_order, description: '' } : null),
)
const others = computed(() => products.value.filter((p) => p.id !== main.value?.id))
const cart = computed(() => {
  const lines = []
  if (main.value && form.quantity > 0) lines.push({ ...main.value, quantity: form.quantity })
  for (const p of others.value) if (extras[p.id] > 0) lines.push({ ...p, quantity: extras[p.id] })
  return lines.map((l) => ({ product_id: l.id, name: l.name, kind: l.kind, quantity: l.quantity, unit_price: l.price, line_total: l.price * l.quantity }))
})
const total = computed(() => cart.value.reduce((s, l) => s + l.line_total, 0))
const units = computed(() => cart.value.reduce((s, l) => s + l.quantity, 0))
const refills = computed(() => cart.value.filter((l) => l.kind === 'refill').reduce((s, l) => s + l.quantity, 0))

// ---------- room left per delivery time (Feature D) ----------
// A hint for choosing: the server checks again when the order is placed.
const slots = ref({}) // 'YYYY-MM-DD|period' -> SlotAvailability
const nearbyM = ref(1000)
const bestTime = ref(null) // Feature E: the period that usually works at this address
const nearbyLabel = computed(() => (nearbyM.value >= 1000 ? `${+(nearbyM.value / 1000).toFixed(1)} km` : `${nearbyM.value} m`))
let slotTimer = null
let slotRequest = 0 // only the newest answer counts if the customer taps quickly
async function loadSlots() {
  const mine = ++slotRequest
  try {
    const r = await getSlotAvailability({ address_id: form.address_id, quantity: refills.value })
    if (mine !== slotRequest) return
    slots.value = Object.fromEntries(r.slots.map((s) => [`${s.date}|${s.period}`, s]))
    nearbyM.value = r.nearby_radius_m ?? 1000
    bestTime.value = r.best_time ?? null
  } catch {
    if (mine === slotRequest) slots.value = {} // unknown: don't block, the server still decides
  }
}
watch(
  () => [form.address_id, refills.value],
  () => {
    if (loading.value) return
    clearTimeout(slotTimer)
    slotTimer = setTimeout(loadSlots, 250)
  },
)

/** Can this day + time be picked? Closed by the clock, or no room for this many containers. */
function slotState(date, period) {
  const timeOpen = settings.value ? periodOpen(settings.value, date, period) : true
  const room = slots.value[`${date}|${period}`] ?? null
  const noRoom = !!(room?.limited && !room.fits)
  return { timeOpen, noRoom, room, open: timeOpen && !noRoom }
}

const periodOptions = computed(() =>
  Object.entries(PERIODS).map(([value, p]) => {
    const st = slotState(deliveryDate.value, value)
    return {
      value,
      ...p,
      icon: value === 'morning' ? sunnyOutline : partlySunnyOutline,
      ...st,
      cutoff: settings.value?.cutoff[value],
    }
  }),
)
const todayClosed = computed(() => (settings.value ? !Object.keys(PERIODS).some((p) => slotState(dateISO(0), p).open) : false))
const nothingOpen = computed(
  () => settings.value && ![0, 1].some((d) => Object.keys(PERIODS).some((p) => slotState(dateISO(d), p).open)),
)
const dayOptions = computed(() => [
  { value: 'today', label: 'Today', disabled: todayClosed.value },
  { value: 'tomorrow', label: 'Tomorrow' },
])

// ---------- best time to deliver (Feature E) ----------
// A suggestion only: the customer's choice stands. Shown when they pick the other time.
const bestOption = computed(() => (bestTime.value ? periodOptions.value.find((p) => p.value === bestTime.value.period) : null))
const bestNudge = computed(() => {
  const b = bestTime.value
  if (!b || form.period === b.period || !selectedAddress.value) return null
  const best = PERIODS[b.period].label
  const other = PERIODS[form.period].label.toLowerCase()
  const tb = b.stats[b.period]
  const to = b.stats[form.period]
  const where = selectedAddress.value.label || 'this address'
  const text =
    b.basis === 'compared'
      ? `${best} usually works best at ${where}: ${tb.delivered} of ${tb.attempts} ${best.toLowerCase()} deliveries reached you, but only ${to.delivered} of ${to.attempts} ${other} ones.`
      : `${PERIODS[form.period].label} deliveries often miss you at ${where} (${to.delivered} of ${to.attempts} reached you). ${best} might work better.`
  return { text, best, canSwitch: !!bestOption.value?.open }
})

/** What the badge on a time button says about room left. */
function roomNote(p) {
  const r = p.room
  if (!r?.limited) return null
  if (r.remaining === 0) return { text: 'Fully booked', tone: 'closed' }
  if (p.noRoom) return { text: `Only ${containers(r.remaining)} left`, tone: 'closed' }
  if (r.almost_full) return { text: `${containers(r.remaining)} left`, tone: 'soon' }
  return null
}

// Keep the choice valid: if the picked time closed or filled up, move to the next open one
watch([deliveryDate, settings, slots], () => {
  if (!settings.value) return
  if (form.day === 'today' && todayClosed.value) form.day = 'tomorrow'
  if (!slotState(deliveryDate.value, form.period).open) {
    form.period = periodOptions.value.find((p) => p.open)?.value ?? form.period
  }
})

// Can't return more empties than you have, or more than you're ordering
const maxEmpties = computed(() => Math.min(held.value, refills.value))
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
    held.value = Math.max(0, summary.containers_held ?? 0)

    // Pre-fill from "Order again": ?items=<id>:<qty>,<id>:<qty>&address=..  (or the older ?qty=3)
    const qty = Number(route.query.qty)
    if (qty >= 1 && qty <= s.max_containers_per_order) form.quantity = qty
    if (route.query.items) {
      const mainId = String((s.products ?? []).find((p) => p.kind === 'refill')?.id)
      form.quantity = 0
      for (const part of String(route.query.items).split(',')) {
        const [id, q] = part.split(':')
        const p = (s.products ?? []).find((x) => String(x.id) === id && x.is_active !== false)
        if (!p || !(Number(q) > 0)) continue
        const n = Math.min(Number(q), p.max_per_order)
        if (String(p.id) === mainId) form.quantity = n
        else extras[p.id] = n
      }
    }
    const wanted = a.find((x) => String(x.id) === String(route.query.address))
    form.address_id = wanted?.id ?? a.find((x) => x.is_default)?.id ?? a[0]?.id ?? ''
    form.empties = Math.min(held.value, refills.value)
    await loadSlots()
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
  if (!cart.value.length) {
    submitError.value = 'Add at least one item to your order.'
    return
  }
  submitting.value = true
  try {
    const order = await createOrder({
      quantity: form.quantity,
      items: main.value?.id != null ? cart.value.map((l) => ({ product_id: l.product_id, quantity: l.quantity })) : undefined,
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
    loadSlots() // someone may have just taken the last room: refresh the badges
  } finally {
    submitting.value = false
  }
}

// ---------- what the receipt and the tank show ----------
const selectedAddress = computed(() => addresses.value.find((a) => a.id === form.address_id) ?? null)
const period = computed(() => PERIODS[form.period])

/** "closes in 40 min" for today's windows (real cutoff times from the station) */
function closesIn(p) {
  if (!settings.value || form.day !== 'today') return ''
  const [h, m] = settings.value.cutoff[p].split(':').map(Number)
  const left = h * 60 + m - (new Date().getHours() * 60 + new Date().getMinutes())
  return left > 0 && left <= 120 ? `Closes in ${duration(left)}` : ''
}

// One tap adds a common note for the rider
const NOTE_CHIPS = ['Please knock loudly', 'Leave at the gate', 'Call when you are near', 'Carry it inside, please']
function addNote(text) {
  if (form.notes.includes(text)) return
  form.notes = [form.notes.trim(), text].filter(Boolean).join('. ').slice(0, 200)
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
      <div class="af-container af-dash">
        <div v-if="loading" class="af-panel"><SkeletonList :rows="4" :avatar="false" /></div>

        <div v-else-if="loadError" class="af-panel err" role="alert">
          <b>Couldn't open the order form</b>
          <p>{{ loadError.message }}</p>
          <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>

        <div v-else class="layout">
          <form class="form" novalidate @submit.prevent="submit">
            <p v-if="submitError" class="alert" role="alert">{{ submitError }}</p>

            <!-- 1. How many: the water rises as you add containers -->
            <TankHero compact :level="form.quantity / main.max_per_order" :label="`${form.quantity} × ${main.name} selected`" :marks="false">
              <div class="prod">
                <div class="prod__text">
                  <h1 id="q-title" class="prod__name">{{ main.name }}</h1>
                  <p class="tank__soft">{{ sentence(main.description) || 'Purified drinking water in a sealed AquaFlow container.' }} We swap it for your empty.</p>
                  <p class="prod__price"><b>{{ peso(main.price) }}</b> <span class="tank__soft">each</span></p>
                </div>
                <div class="prod__qty">
                  <QuantityStepper v-model="form.quantity" :min="others.length ? 0 : 1" :max="main.max_per_order" :label="`Number of ${main.name}`" unit="containers" />
                  <span class="tank__soft prod__max">Up to {{ main.max_per_order }} per order</span>
                </div>
              </div>
            </TankHero>

            <!-- 1b. Everything else the station sells -->
            <section v-if="others.length" class="af-panel" aria-labelledby="x-title">
              <div class="head">
                <h2 id="x-title" class="h">Add to your order</h2>
                <span class="af-small">Same trip, no extra delivery fee</span>
              </div>
              <ul class="shop">
                <li v-for="p in others" :key="p.id" class="shop__item" :class="{ 'is-in': extras[p.id] > 0 }">
                  <span class="shop__icon" :class="`k-${p.kind}`" aria-hidden="true"><ion-icon :icon="KIND[p.kind]?.icon" /></span>
                  <span class="shop__text">
                    <b>{{ p.name }}</b>
                    <span>{{ p.description || KIND[p.kind]?.note }}</span>
                    <span class="shop__price af-money">{{ peso(p.price) }}</span>
                  </span>
                  <span class="shop__qty">
                    <button v-if="extras[p.id] > 0" type="button" class="mini" :aria-label="`One less ${p.name}`" @click="extras[p.id]--"><ion-icon :icon="removeOutline" /></button>
                    <output v-if="extras[p.id] > 0" class="mini__n" aria-live="polite">{{ extras[p.id] }}</output>
                    <button
                      type="button"
                      class="mini mini--add"
                      :disabled="(extras[p.id] ?? 0) >= p.max_per_order"
                      :aria-label="`Add one ${p.name}`"
                      @click="extras[p.id] = (extras[p.id] ?? 0) + 1"
                    >
                      <ion-icon :icon="addOutline" />
                    </button>
                  </span>
                </li>
              </ul>
            </section>

            <!-- 2. Where -->
            <section class="af-panel" aria-labelledby="a-title">
              <div class="head">
                <h2 id="a-title" class="h">Deliver to</h2>
                <AppButton variant="ghost" size="sm" @click="addrOpen = true"><ion-icon :icon="addOutline" aria-hidden="true" /> New address</AppButton>
              </div>
              <div v-if="addresses.length" class="addrs" role="radiogroup" aria-labelledby="a-title">
                <button
                  v-for="a in addresses"
                  :key="a.id"
                  type="button"
                  role="radio"
                  class="addr"
                  :aria-checked="form.address_id === a.id"
                  @click="form.address_id = a.id"
                >
                  <span class="addr__top">
                    <b>{{ a.label }}</b>
                    <ion-icon v-if="form.address_id === a.id" :icon="checkmarkCircle" class="addr__tick" aria-hidden="true" />
                  </span>
                  <span>{{ a.street }}, {{ a.barangay }}</span>
                  <i v-if="a.landmark">{{ a.landmark }}</i>
                </button>
              </div>
              <p v-else class="af-small">Add the address where we should deliver. You'll drop a pin on the map.</p>
              <MapPicker v-if="selectedAddress" :key="selectedAddress.id" :model-value="selectedAddress" :station="settings.station" readonly height="170px" :zoom="14" />
            </section>

            <!-- 3. When -->
            <section class="af-panel" aria-labelledby="w-title">
              <div class="head">
                <h2 id="w-title" class="h">When</h2>
                <SegmentedControl v-model="form.day" :options="dayOptions" label="Delivery day" />
              </div>
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
                  <span class="period__icon" aria-hidden="true"><ion-icon :icon="p.icon" /></span>
                  <span class="period__text">
                    <b>{{ p.label }}</b>
                    <span>{{ p.hours }}</span>
                  </span>
                  <span v-if="!p.timeOpen" class="period__note period__note--closed">Closed for today</span>
                  <span v-else-if="roomNote(p)" class="period__note" :class="`period__note--${roomNote(p).tone}`">{{ roomNote(p).text }}</span>
                  <span v-else-if="closesIn(p.value)" class="period__note period__note--soon"><ion-icon :icon="timeOutline" aria-hidden="true" /> {{ closesIn(p.value) }}</span>
                  <span v-if="p.open && (p.room?.delivery_nearby || bestTime?.period === p.value)" class="period__chips">
                    <span v-if="bestTime?.period === p.value" class="period__best">
                      <ion-icon :icon="ribbonOutline" aria-hidden="true" /> {{ bestTime.basis === 'compared' ? 'Usually works best' : 'Worth a try' }}
                    </span>
                    <span v-if="p.room?.delivery_nearby" class="period__near">
                      <ion-icon :icon="navigateCircleOutline" aria-hidden="true" /> Delivery nearby
                    </span>
                  </span>
                </button>
              </div>
              <div v-if="bestNudge" class="best-nudge" role="status">
                <ion-icon :icon="ribbonOutline" aria-hidden="true" />
                <p>{{ bestNudge.text }}</p>
                <AppButton v-if="bestNudge.canSwitch" variant="secondary" size="sm" @click="form.period = bestTime.period">Switch to {{ bestNudge.best.toLowerCase() }}</AppButton>
              </div>
              <p v-if="nothingOpen" class="alert" role="status">
                Every delivery time for today and tomorrow is full for {{ containers(refills) }}. Try fewer containers, or check again later.
              </p>
              <p v-else-if="periodOptions.some((p) => p.open && p.room?.delivery_nearby)" class="af-small near-hint">
                <b>Delivery nearby</b> means a rider is already coming within {{ nearbyLabel }} of you then.
              </p>
              <p class="af-small">
                Same-day orders: morning before {{ clockLabel(settings.cutoff.morning) }}, afternoon before {{ clockLabel(settings.cutoff.afternoon) }}.
              </p>
            </section>

            <!-- 4. Empties + 5. Note -->
            <div class="duo">
              <section class="af-panel" aria-labelledby="e-title">
                <h2 id="e-title" class="h">Empties to hand back</h2>
                <QuantityStepper v-model="form.empties" :min="0" :max="maxEmpties" label="Empty containers to return" unit="empties" />
                <p class="af-small">You have {{ containers(held) }} at home. Telling us lets the rider save room on the tricycle.</p>
              </section>

              <section class="af-panel" aria-labelledby="n-title">
                <h2 id="n-title" class="h">Note for the rider</h2>
                <div class="chips" role="group" aria-label="Quick notes">
                  <button v-for="c in NOTE_CHIPS" :key="c" type="button" class="af-chip" :aria-pressed="form.notes.includes(c)" @click="addNote(c)">{{ c }}</button>
                </div>
                <TextField v-model="form.notes" label="Note" multiline :maxlength="200" placeholder="Example: blue gate, the dog is friendly." />
              </section>
            </div>
          </form>

          <!-- Receipt (desktop: sticky beside the form) -->
          <aside class="receipt af-panel" aria-labelledby="r-title">
            <h2 id="r-title" class="h">Your order</h2>
            <dl class="lines">
              <div v-for="l in cart" :key="l.product_id ?? 'main'"><dt>{{ l.quantity }} × {{ l.name }}</dt><dd>{{ peso(l.line_total) }}</dd></div>
              <div v-if="!cart.length"><dt>Your cart is empty</dt><dd></dd></div>
              <div><dt>Delivery</dt><dd>Free</dd></div>
              <div><dt>Empties you'll hand back</dt><dd>{{ form.empties }}</dd></div>
            </dl>
            <hr class="af-hairline" />
            <div class="total">
              <span>Total</span>
              <b class="af-money">{{ peso(total) }}</b>
            </div>
            <div class="facts">
              <div class="af-inset">
                <span class="fact__k">When</span>
                <span class="fact__v">{{ friendlyDay(deliveryDate) }}, {{ period.label.toLowerCase() }} ({{ period.hours }})</span>
              </div>
              <div class="af-inset">
                <span class="fact__k">Where</span>
                <span class="fact__v">{{ selectedAddress ? `${selectedAddress.label}, ${selectedAddress.barangay}` : 'Choose an address' }}</span>
              </div>
              <div class="af-inset pay">
                <ion-icon :icon="cashOutline" aria-hidden="true" />
                <span class="fact__v">Pay cash to the rider when it arrives</span>
              </div>
            </div>
            <AppButton size="lg" block :loading="submitting" @click="submit">Place order</AppButton>
          </aside>
        </div>
      </div>

      <AddressFormModal v-if="settings" :is-open="addrOpen" :settings="settings" @close="addrOpen = false" @saved="onAddressSaved" />
    </ion-content>

    <!-- Phone/tablet: the total stays in view -->
    <ion-footer v-if="!loading && !loadError" class="ion-no-border foot">
      <div class="bar">
        <span class="bar__bag" aria-hidden="true">
          <ion-icon :icon="bagHandleOutline" />
          <span class="bar__badge">{{ units }}</span>
        </span>
        <div class="bar__sum">
          <b class="af-money">{{ peso(total) }}</b>
          <span>{{ friendlyDay(deliveryDate) }}, {{ period.label.toLowerCase() }}</span>
        </div>
        <AppButton size="lg" :loading="submitting" @click="submit">Place order</AppButton>
      </div>
    </ion-footer>
  </ion-page>
</template>

<style scoped>
.layout { display: grid; gap: 20px; align-items: start; }
.form { display: grid; gap: 16px; min-width: 0; }
.h { margin: 0; font-family: var(--af-display); font-size: 17px; font-weight: 600; letter-spacing: -0.02em; }
.head { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.alert { margin: 0; padding: 12px 16px; border-radius: 14px; background: var(--af-danger-tint); color: var(--af-danger); border: 1px solid color-mix(in srgb, var(--af-danger) 30%, transparent); font-weight: 650; font-size: 14px; }

/* ---------- product in the tank ---------- */
.prod { display: flex; justify-content: space-between; align-items: flex-end; gap: 20px 32px; flex-wrap: wrap; }
.prod__text { display: grid; gap: 8px; max-width: 30ch; }
.prod__text p { margin: 0; font-size: 14.5px; line-height: 1.5; }
.prod__name { margin: 0; font-family: var(--af-display); font-size: clamp(28px, 4vw, 40px); font-weight: 650; letter-spacing: -0.045em; line-height: 1; }
.prod__price b { font-family: var(--af-display); font-size: 26px; font-weight: 650; color: #ffd58a; letter-spacing: -0.02em; }
.prod__qty { display: grid; justify-items: center; gap: 8px; padding: 12px 16px; border-radius: 22px; background: rgba(2, 18, 26, 0.42); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); }
.prod__qty :deep(.af-step__btn) { background: rgba(255, 255, 255, 0.08); border-color: rgba(230, 244, 246, 0.3); color: #7ff0e4; }
.prod__qty :deep(.af-step__value small) { color: #cfe6ea; }
.prod__max { font-size: 12.5px; font-weight: 650; }

/* ---------- addresses ---------- */
.addrs { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 10px; }
.addr {
  display: grid;
  gap: 3px;
  align-content: start;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1.5px solid var(--af-line);
  background: var(--af-surface-2);
  color: var(--af-ink);
  font: 550 14px/1.4 var(--af-font);
  text-align: left;
  cursor: pointer;
  transition: border-color var(--af-dur) var(--af-ease), background var(--af-dur) var(--af-ease);
}
.addr:hover { border-color: color-mix(in srgb, var(--af-primary) 45%, var(--af-line)); }
.addr[aria-checked='true'] { border-color: var(--af-primary); background: var(--af-primary-tint); }
.addr__top { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.addr__top b { font-size: 15.5px; font-weight: 800; }
.addr__tick { color: var(--af-primary); font-size: 20px; }
.addr > span:not(.addr__top), .addr i { color: var(--af-ink-2); font-size: 13.5px; }

/* ---------- time windows ---------- */
.periods { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.period {
  display: grid;
  grid-template-columns: 42px 1fr;
  gap: 4px 12px;
  align-items: center;
  padding: 14px;
  border-radius: 18px;
  border: 1.5px solid var(--af-line);
  background: var(--af-surface-2);
  color: var(--af-ink);
  font-family: var(--af-font);
  text-align: left;
  cursor: pointer;
  transition: border-color var(--af-dur) var(--af-ease), background var(--af-dur) var(--af-ease);
}
.period__icon { grid-row: span 2; width: 42px; height: 42px; display: grid; place-items: center; border-radius: 14px; background: var(--af-sun-tint); color: var(--af-sun); font-size: 22px; }
.period__text { display: grid; line-height: 1.3; }
.period__text b { font-size: 16px; font-weight: 800; }
.period__text span { font-size: 13px; font-weight: 600; color: var(--af-ink-2); font-variant-numeric: tabular-nums; }
.period__note { grid-column: 2; display: inline-flex; align-items: center; gap: 4px; font-size: 12.5px; font-weight: 750; }
.period__note--soon { color: var(--af-amber-fg); }
.period__note--closed { color: var(--af-danger); }
.period__chips { grid-column: 2; display: flex; flex-wrap: wrap; gap: 6px; }
.period__best {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--af-sun-tint);
  color: var(--af-amber-fg);
  font-size: 12px;
  font-weight: 750;
}
.period__best ion-icon { font-size: 15px; }
.best-nudge {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 8px 10px;
  align-items: start;
  padding: 12px 14px;
  border-radius: 14px;
  background: var(--af-sun-tint);
  border: 1px solid color-mix(in srgb, var(--af-sun) 35%, transparent);
}
.best-nudge > ion-icon { font-size: 20px; color: var(--af-amber-fg); margin-top: 1px; }
.best-nudge p { margin: 0; font-size: 14px; font-weight: 600; line-height: 1.45; color: var(--af-ink); }
.best-nudge :deep(.af-btn) { grid-column: 2; justify-self: start; }
.period__near {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--af-success-tint);
  color: var(--af-success);
  font-size: 12px;
  font-weight: 750;
}
.period__near ion-icon { font-size: 15px; }
.near-hint b { color: var(--af-success); }
.period:hover:not(:disabled) { border-color: color-mix(in srgb, var(--af-primary) 45%, var(--af-line)); }
.period[aria-checked='true'] { border-color: var(--af-primary); background: var(--af-primary-tint); }
.period:disabled { opacity: 0.55; cursor: not-allowed; }
.af-panel > p { margin: 0; }

.duo { display: grid; gap: 16px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }

/* ---------- receipt ---------- */
.receipt { display: none; }

/* ---------- add-ons ---------- */
.shop { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 10px; }
.shop__item { display: grid; grid-template-columns: 44px minmax(0, 1fr) auto; gap: 12px; align-items: center; padding: 12px 12px 12px 14px; border-radius: 18px; border: 1.5px solid var(--af-line); background: var(--af-surface-2); transition: border-color var(--af-dur) var(--af-ease), background var(--af-dur) var(--af-ease); }
.shop__item.is-in { border-color: var(--af-primary); background: var(--af-primary-tint); }
.shop__icon { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 14px; font-size: 21px; background: var(--af-primary-tint); color: var(--af-primary); }
.shop__icon.k-container { background: var(--af-pearl-tint); color: var(--af-pearl); }
.shop__icon.k-item { background: var(--af-sun-tint); color: var(--af-sun); }
.shop__text { display: grid; gap: 1px; min-width: 0; }
.shop__text b { font-size: 14.5px; font-weight: 800; }
.shop__text span { font-size: 12.5px; font-weight: 600; color: var(--af-ink-2); line-height: 1.35; }
.shop__text .shop__price { font-family: var(--af-display); font-size: 15px; font-weight: 650; color: var(--af-sun); margin-top: 2px; }
.shop__qty { display: flex; align-items: center; gap: 6px; }
.mini { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 50%; border: 1.5px solid var(--af-line-strong); background: var(--af-surface); color: var(--af-primary); font-size: 19px; cursor: pointer; }
.mini--add { background: var(--af-primary); border-color: var(--af-primary); color: var(--af-on-primary); }
.mini:disabled { opacity: 0.35; cursor: not-allowed; }
.mini__n { min-width: 20px; text-align: center; font-family: var(--af-display); font-size: 18px; font-weight: 650; font-variant-numeric: tabular-nums; }
.lines { margin: 0; display: grid; gap: 10px; }
.lines div { display: flex; justify-content: space-between; gap: 12px; font-size: 14.5px; }
.lines dt { color: var(--af-ink-2); font-weight: 600; }
.lines dd { margin: 0; font-weight: 750; font-variant-numeric: tabular-nums; }
.total { display: flex; justify-content: space-between; align-items: baseline; }
.total span { font-size: 15px; font-weight: 800; }
.total b { font-family: var(--af-display); font-size: 34px; font-weight: 650; letter-spacing: -0.04em; }
.facts { display: grid; gap: 8px; }
.fact__k { font-size: 12.5px; font-weight: 700; color: var(--af-ink-2); }
.fact__v { font-size: 14px; font-weight: 650; line-height: 1.4; }
.pay { grid-template-columns: auto 1fr; align-items: center; gap: 10px; }
.pay ion-icon { font-size: 20px; color: var(--af-sun); }

/* ---------- bottom bar (phone/tablet) ---------- */
.bar {
  display: flex;
  align-items: center;
  gap: 14px;
  max-width: 860px;
  margin: 0 auto;
  padding: 12px 16px calc(12px + env(safe-area-inset-bottom, 0px));
  background: color-mix(in srgb, var(--af-surface-solid) 90%, transparent);
  border-top: 1px solid var(--af-line);
  backdrop-filter: saturate(160%) blur(16px);
  -webkit-backdrop-filter: saturate(160%) blur(16px);
}
.bar__bag { position: relative; flex: none; width: 44px; height: 44px; display: grid; place-items: center; border-radius: 50%; background: var(--af-primary-tint); color: var(--af-primary); font-size: 19px; }
.bar__badge { position: absolute; top: -4px; right: -4px; min-width: 18px; height: 18px; padding: 0 4px; display: grid; place-items: center; border-radius: 999px; background: var(--af-primary); color: var(--af-on-primary); font-size: 10px; font-weight: 800; box-shadow: 0 0 0 2px var(--af-surface-solid); }
.bar__sum { display: grid; gap: 2px; margin-right: auto; min-width: 0; }
.bar__sum b { font-family: var(--af-display); font-size: 24px; font-weight: 650; letter-spacing: -0.03em; }
.bar__sum span { font-size: 13px; font-weight: 600; color: var(--af-ink-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.err { justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }

@media (min-width: 760px) {
  .duo { grid-template-columns: repeat(2, minmax(0, 1fr)); align-items: stretch; }
  .bar { margin-bottom: 16px; border: 1px solid var(--af-line); border-radius: 24px; box-shadow: var(--af-shadow-3); }
}
@media (min-width: 1100px) {
  .layout { grid-template-columns: minmax(0, 1fr) 360px; }
  .receipt { display: grid; position: sticky; top: 16px; }
  .foot { display: none; }
}
@media (max-width: 420px) {
  .periods { grid-template-columns: 1fr; }
  .bar__sum span { display: none; }
}
</style>
