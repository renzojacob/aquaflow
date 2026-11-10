<!--
  Owner: supplies. Caps, seals, filters and anything else the station uses up
  (containers themselves live on the Stock screen).

  "Used per container" is the clever part: set it to 1 for caps and the app takes 10 caps off
  the shelf every time the dispatcher records a batch of 10 filled containers. Days left then
  comes from what was really used in the last 30 days, and the station is warned before a
  delivery would arrive too late.
-->
<script setup>
import { computed, reactive, ref } from 'vue'
import { IonContent, IonHeader, IonIcon, IonPage, IonTitle, IonToolbar, onIonViewWillEnter } from '@ionic/vue'
import { addOutline, alertCircleOutline, createOutline, trashOutline } from 'ionicons/icons'

import AppButton from '@/components/ui/AppButton.vue'
import SectionHead from '@/components/dash/SectionHead.vue'
import SegmentedControl from '@/components/form/SegmentedControl.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import TextField from '@/components/form/TextField.vue'
import { showToast } from '@/composables/useToast'
import { adjustSupply, deleteSupply, getSupplies, saveSupply } from '@/services/supplyService'
import { ago } from '@/utils/format'

const data = ref(null)
const loading = ref(true)
const error = ref(null)
const busyId = ref(null)
const openId = ref(null)            // which supply has its "record a change" panel open

const blank = () => ({ id: null, name: '', unit: 'piece', quantity: '', used_per_refill: '', reorder_level: '', lead_time_days: 3, note: '', is_active: true })
const form = reactive({ ...blank(), busy: false, error: '' })
const editing = computed(() => form.id != null)

const move = reactive({ type: 'received', quantity: '', note: '', busy: false, error: '' })

const supplies = computed(() => data.value?.supplies ?? [])
const alerts = computed(() => data.value?.alerts ?? [])
const counts = computed(() => data.value?.counts ?? { total: 0, low: 0, out: 0 })

const UNITS = [
  { value: 'piece', label: 'Pieces' },
  { value: 'litre', label: 'Litres' },
  { value: 'kilo', label: 'Kilos' },
  { value: 'set', label: 'Sets' },
]
const UNIT_SHORT = { piece: 'pcs', litre: 'L', kilo: 'kg', set: 'sets' }
const MOVES = [
  { value: 'received', label: 'Delivery arrived' },
  { value: 'used', label: 'Used by hand' },
  { value: 'correction', label: 'Counted the shelf' },
]
const REASON_LABEL = { received: 'received', used: 'used', correction: 'count' }

const amount = (n, unit) => `${Number(n).toLocaleString('en-PH', { maximumFractionDigits: 2 })} ${UNIT_SHORT[unit] ?? ''}`.trim()
const daysLabel = (s) => (s.days_left == null ? 'Usage not known yet' : s.days_left < 1 ? 'Less than a day left' : `About ${Math.round(s.days_left)} day${Math.round(s.days_left) === 1 ? '' : 's'} left`)
// The bar shows how much of a "full shelf" is left. A full shelf = enough for 30 days,
// or twice the restock level when nothing is used automatically.
const barPct = (s) => {
  const full = s.daily_usage ? s.daily_usage * 30 : s.reorder_level * 2
  if (!full) return s.quantity > 0 ? 100 : 0
  return Math.max(2, Math.min(100, Math.round((s.quantity / full) * 100)))
}

async function load() {
  error.value = null
  try {
    data.value = await getSupplies()
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
onIonViewWillEnter(load)

function edit(s) {
  Object.assign(form, { ...s, quantity: '', used_per_refill: String(s.used_per_refill || ''), reorder_level: String(s.reorder_level || ''), busy: false, error: '' })
  document.querySelector('.sform')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
const startNew = () => Object.assign(form, { ...blank(), busy: false, error: '' })

async function submit() {
  form.error = ''
  form.busy = true
  try {
    data.value = await saveSupply({ ...form })
    showToast(editing.value ? `${form.name} saved` : `${form.name} added`, 'success')
    startNew()
  } catch (e) {
    form.error = e.message
  } finally {
    form.busy = false
  }
}

async function run(id, fn, okMessage) {
  busyId.value = id
  try {
    data.value = await fn()
    if (okMessage) showToast(okMessage, 'success')
  } catch (e) {
    showToast(e.message, 'danger')
  } finally {
    busyId.value = null
  }
}
const toggle = (s) => run(s.id, () => saveSupply({ ...s, is_active: !s.is_active }), s.is_active ? `${s.name} switched off` : `${s.name} switched on`)
const remove = (s) => run(s.id, () => deleteSupply(s.id), `${s.name} deleted`)

function openMove(s) {
  openId.value = openId.value === s.id ? null : s.id
  Object.assign(move, { type: 'received', quantity: '', note: '', busy: false, error: '' })
}

async function submitMove(s) {
  move.error = ''
  move.busy = true
  try {
    data.value = await adjustSupply(s.id, { type: move.type, quantity: Number(move.quantity), note: move.note })
    showToast(`${s.name} updated`, 'success')
    openId.value = null
  } catch (e) {
    move.error = e.message
  } finally {
    move.busy = false
  }
}
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar><ion-title>Supplies</ion-title></ion-toolbar>
    </ion-header>
    <ion-content>
      <div class="af-container af-dash">
        <header class="top">
          <h1 class="title">Supplies</h1>
          <p class="af-small">Caps, seals, filters and anything else the station uses up. Containers are on the Stock screen.</p>
        </header>

        <SkeletonList v-if="loading" :rows="4" />
        <div v-else-if="error" class="af-panel err" role="alert">
          <b>Couldn't load supplies</b>
          <p>{{ error.message }}</p>
          <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
        </div>

        <template v-else>
          <section v-if="alerts.length" class="af-panel warn" role="alert" aria-label="Supplies to restock">
            <SectionHead :title="`Order ${alerts.length === 1 ? 'this' : 'these'} now`" :sub="`${counts.out} out, ${counts.low} running low`" />
            <ul class="plain">
              <li v-for="a in alerts" :key="a.id" class="alert">
                <ion-icon :icon="alertCircleOutline" aria-hidden="true" />
                <span><b>{{ a.name }}</b> — {{ amount(a.quantity, a.unit) }} left. {{ a.why }}</span>
              </li>
            </ul>
          </section>

          <div class="layout">
            <section class="af-panel" aria-labelledby="slist">
              <SectionHead
                title="On the shelf"
                :sub="`${counts.total} supplies · about ${data.refills_per_day} containers filled a day`"
              >
                <AppButton variant="secondary" size="sm" @click="startNew"><ion-icon :icon="addOutline" aria-hidden="true" /> New supply</AppButton>
              </SectionHead>

              <p v-if="!supplies.length" class="af-small">
                Nothing yet. Add your first supply on the right — for example "Bottle caps", pieces, 1 used per container.
              </p>

              <ul v-else class="slist">
                <li v-for="s in supplies" :key="s.id" class="sup" :class="[`sup--${s.status}`, { 'sup--off': !s.is_active }]">
                  <div class="sup__row">
                    <span class="sup__text">
                      <b>{{ s.name }}</b>
                      <span>
                        {{ daysLabel(s) }}<template v-if="s.runout_date && s.status !== 'out'"> · runs out about {{ s.runout_date }}</template>
                        <template v-if="!s.is_active"> · switched off</template>
                      </span>
                      <span class="sup__meta">
                        <template v-if="s.auto">{{ s.used_per_refill }} {{ UNIT_SHORT[s.unit] }} per container, taken off automatically</template>
                        <template v-else>Not counted per container — record what you use</template>
                        <template v-if="s.reorder_level"> · restock at {{ amount(s.reorder_level, s.unit) }}</template>
                      </span>
                    </span>
                    <span class="sup__qty">
                      <b>{{ amount(s.quantity, s.unit) }}</b>
                      <span class="pill" :class="`pill--${s.status}`">{{ s.status === 'ok' ? 'OK' : s.status === 'low' ? 'Order now' : 'Out' }}</span>
                    </span>
                  </div>

                  <div class="bar" role="meter" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="barPct(s)" :aria-label="`${s.name} left`">
                    <span :style="{ width: barPct(s) + '%' }"></span>
                  </div>

                  <div class="sup__btns">
                    <AppButton size="sm" :disabled="busyId === s.id" @click="openMove(s)">{{ openId === s.id ? 'Close' : 'Record a change' }}</AppButton>
                    <button type="button" class="ibtn" :aria-label="`Edit ${s.name}`" @click="edit(s)"><ion-icon :icon="createOutline" /></button>
                    <AppButton variant="ghost" size="sm" :loading="busyId === s.id" @click="toggle(s)">{{ s.is_active ? 'Switch off' : 'Switch on' }}</AppButton>
                    <button type="button" class="ibtn ibtn--danger" :aria-label="`Delete ${s.name}`" :disabled="busyId === s.id" @click="remove(s)"><ion-icon :icon="trashOutline" /></button>
                  </div>

                  <form v-if="openId === s.id" class="move" novalidate @submit.prevent="submitMove(s)">
                    <SegmentedControl v-model="move.type" block label="What happened" :options="MOVES" />
                    <TextField
                      v-model="move.quantity"
                      :label="move.type === 'correction' ? `How many ${UNIT_SHORT[s.unit]} are really there?` : `How many ${UNIT_SHORT[s.unit]}?`"
                      type="number"
                      inputmode="decimal"
                      required
                    />
                    <TextField v-model="move.note" :label="move.type === 'correction' ? 'Why did the count change?' : 'Note (optional)'" :placeholder="move.type === 'received' ? 'Supplier delivery' : ''" />
                    <p v-if="move.error" class="form__err" role="alert">{{ move.error }}</p>
                    <AppButton type="submit" block :loading="move.busy">Save</AppButton>
                  </form>
                </li>
              </ul>
            </section>

            <section class="af-panel sform" aria-labelledby="sform">
              <SectionHead :title="editing ? `Edit ${form.name || 'supply'}` : 'Add a supply'" :sub="editing ? 'Change the amount on the shelf with Record a change' : 'Caps, seals, filters, cleaning solution…'" />
              <form class="form" novalidate @submit.prevent="submit">
                <TextField v-model="form.name" label="Name" placeholder="Bottle caps" required />
                <div class="field">
                  <span class="field__lbl">Measured in</span>
                  <SegmentedControl v-model="form.unit" block label="Unit" :options="UNITS" />
                </div>
                <TextField v-if="!editing" v-model="form.quantity" label="How many do you have now?" type="number" inputmode="decimal" />
                <div class="two">
                  <TextField v-model="form.used_per_refill" label="Used per container" type="number" inputmode="decimal" />
                  <TextField v-model="form.reorder_level" label="Restock level" type="number" inputmode="decimal" />
                </div>
                <p class="af-small">
                  Used per container: 1 for caps and seals. A filter that lasts 2000 containers is 0.0005.
                  Put 0 for things you only record by hand. The app subtracts this every time a refill batch is recorded.
                </p>
                <TextField v-model="form.lead_time_days" label="Days for a delivery to arrive" type="number" inputmode="numeric" />
                <p class="af-small">You are warned while there is still more than this many days left.</p>
                <TextField v-model="form.note" label="Note (optional)" placeholder="Supplier: Calapan Plastics" :maxlength="160" />
                <p v-if="form.error" class="form__err" role="alert">{{ form.error }}</p>
                <AppButton type="submit" size="lg" block :loading="form.busy">{{ editing ? 'Save changes' : 'Add supply' }}</AppButton>
                <AppButton v-if="editing" variant="ghost" block @click="startNew">Cancel editing</AppButton>
              </form>
            </section>
          </div>

          <section v-if="data.log.length" class="af-panel" aria-labelledby="log">
            <SectionHead title="History" :sub="`Every change, newest first`" />
            <ul class="log">
              <li v-for="(m, i) in data.log" :key="i">
                <b :class="m.delta < 0 ? 'out' : 'in'">{{ m.delta > 0 ? '+' : '' }}{{ m.delta }}</b>
                <span>{{ m.supply }} · {{ REASON_LABEL[m.reason] }}<template v-if="m.note"> · {{ m.note }}</template></span>
                <span class="log__who">{{ m.by }} · {{ ago(m.at) }}</span>
              </li>
            </ul>
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
.layout { display: grid; gap: 16px; align-items: start; }
@media (min-width: 1100px) { .layout { grid-template-columns: minmax(0, 1fr) 400px; } .sform { position: sticky; top: 16px; } }

.slist { list-style: none; margin: 0; padding: 0; display: grid; }
.sup { display: grid; gap: 10px; padding: 14px 2px; border-bottom: 1px solid var(--af-line); }
.sup:last-child { border-bottom: 0; }
.sup--off { opacity: 0.55; }
.sup__row { display: flex; gap: 12px; align-items: flex-start; }
.sup__text { display: grid; gap: 2px; min-width: 0; flex: 1; }
.sup__text b { font-size: 15px; font-weight: 800; }
.sup__text span { font-size: 13px; color: var(--af-ink-2); font-weight: 550; }
.sup__meta { font-size: 12.5px !important; }
.sup__qty { display: grid; gap: 4px; justify-items: end; text-align: right; white-space: nowrap; }
.sup__qty b { font-family: var(--af-display); font-size: 19px; font-weight: 650; }
.pill { font-size: 11.5px; font-weight: 800; padding: 2px 9px; border-radius: 99px; background: var(--af-success-tint); color: var(--af-success); }
.pill--low { background: var(--af-sun-tint); color: var(--af-ink); }
.pill--out { background: var(--af-danger-tint); color: var(--af-danger); }
.bar { height: 8px; border-radius: 99px; background: var(--af-surface-2); overflow: hidden; }
.bar span { display: block; height: 100%; border-radius: 99px; background: var(--af-primary); transition: width 0.4s ease; }
.sup--low .bar span { background: var(--af-sun); }
.sup--out .bar span { background: var(--af-danger); }
.sup__btns { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.ibtn { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 50%; border: 0; background: var(--af-surface-2); color: var(--af-primary); font-size: 18px; cursor: pointer; }
.ibtn--danger { color: var(--af-danger); }
.move { display: grid; gap: 12px; padding: 14px; border-radius: var(--af-r-md); background: var(--af-surface-2); }

.form { display: grid; gap: 14px; }
.form .af-small { margin: 0; line-height: 1.45; }
.field { display: grid; gap: 8px; }
.field__lbl { font-size: 14px; font-weight: 750; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.form__err { margin: 0; padding: 10px 14px; border-radius: 12px; background: var(--af-danger-tint); color: var(--af-danger); font-size: 14px; font-weight: 650; }

.warn { border-color: var(--af-danger); }
.plain { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.alert { display: flex; gap: 10px; align-items: flex-start; font-size: 14px; }
.alert ion-icon { color: var(--af-danger); font-size: 20px; flex: none; margin-top: 1px; }
.log { list-style: none; margin: 0; padding: 0; display: grid; }
.log li { display: grid; grid-template-columns: 64px minmax(0, 1fr) auto; gap: 10px; align-items: center; padding: 9px 0; border-bottom: 1px solid var(--af-line); font-size: 13.5px; }
.log li:last-child { border-bottom: 0; }
.log b { font-family: var(--af-display); font-size: 15px; }
.log b.out { color: var(--af-danger); }
.log b.in { color: var(--af-success); }
.log__who { color: var(--af-ink-2); font-size: 12.5px; white-space: nowrap; }
.err { display: grid; gap: 8px; justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }

@media (max-width: 640px) {
  .log li { grid-template-columns: 56px minmax(0, 1fr); }
  .log__who { grid-column: 2; }
}
</style>
