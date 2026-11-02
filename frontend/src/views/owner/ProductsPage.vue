<!--
  Owner: products & prices. Everything customers can put in their cart.
  Kinds: refill (we swap containers), new container (customer keeps it), extra (bottles, ice...).
  Change a price, switch a product off (it disappears from the order screen), add a new one.
  Old orders keep the price they were placed at.
-->
<script setup>
import { computed, reactive, ref } from 'vue'
import { IonContent, IonHeader, IonIcon, IonPage, IonTitle, IonToolbar, onIonViewWillEnter } from '@ionic/vue'
import { addOutline, createOutline } from 'ionicons/icons'

import AppButton from '@/components/ui/AppButton.vue'
import SectionHead from '@/components/dash/SectionHead.vue'
import SegmentedControl from '@/components/form/SegmentedControl.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import TextField from '@/components/form/TextField.vue'
import { KIND } from '@/constants/cart'
import { showToast } from '@/composables/useToast'
import { listProducts, saveProduct } from '@/services/ownerService'
import { peso } from '@/utils/format'

const products = ref([])
const loading = ref(true)
const error = ref(null)
const busyId = ref('')

const blank = () => ({ id: null, name: '', kind: 'item', price: '', description: '', max_per_order: 10, is_active: true })
const form = reactive({ ...blank(), busy: false, error: '' })
const editing = computed(() => form.id != null)

async function load() {
  error.value = null
  try {
    products.value = await listProducts()
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
onIonViewWillEnter(load)

function edit(p) {
  Object.assign(form, { ...p, price: String(p.price), busy: false, error: '' })
  document.querySelector('.pform')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
function startNew() {
  Object.assign(form, { ...blank(), busy: false, error: '' })
}

async function submit() {
  form.error = ''
  form.busy = true
  try {
    const saved = await saveProduct({ ...form, price: Number(form.price), max_per_order: Number(form.max_per_order) })
    const i = products.value.findIndex((p) => p.id === saved.id)
    if (i >= 0) products.value[i] = saved
    else products.value.push(saved)
    showToast(editing.value ? `${saved.name} saved` : `${saved.name} added. Customers can order it now.`, 'success')
    startNew()
  } catch (e) {
    form.error = e.message
  } finally {
    form.busy = false
  }
}

async function toggle(p) {
  busyId.value = p.id
  try {
    const saved = await saveProduct({ ...p, is_active: !p.is_active })
    Object.assign(p, saved)
    showToast(saved.is_active ? `${p.name} is on sale again` : `${p.name} is hidden from customers`, 'success')
  } catch (e) {
    showToast(e.message, 'danger')
  } finally {
    busyId.value = ''
  }
}

const kindOptions = [
  { value: 'refill', label: 'Refill' },
  { value: 'container', label: 'New container' },
  { value: 'item', label: 'Extra' },
]
const KIND_HELP = {
  refill: 'The rider brings a filled station container and takes an empty back. Counts in the customer’s containers.',
  container: 'The customer buys a new container and keeps it. Not counted as a station container.',
  item: 'Anything else: small bottles, ice, caps and seals.',
}
const onSale = computed(() => products.value.filter((p) => p.is_active).length)
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-title>Products & prices</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content>
      <div class="af-container af-dash">
        <header class="top">
          <h1 class="title">Products & prices</h1>
          <p class="af-small">What customers can put in their cart. Old orders keep the price they were placed at.</p>
        </header>

        <div class="layout">
          <section class="af-panel" aria-labelledby="list-title">
            <SectionHead title="On the order screen" :sub="`${onSale} on sale, ${products.length - onSale} hidden`">
              <AppButton variant="secondary" size="sm" @click="startNew"><ion-icon :icon="addOutline" aria-hidden="true" /> New product</AppButton>
            </SectionHead>
            <SkeletonList v-if="loading" :rows="4" />
            <div v-else-if="error" class="err" role="alert">
              <b>Couldn't load products</b>
              <p>{{ error.message }}</p>
              <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
            </div>
            <ul v-else class="plist">
              <li v-for="p in products" :key="p.id" class="prod" :class="{ 'prod--off': !p.is_active }">
                <span class="prod__icon" :class="`k-${p.kind}`" aria-hidden="true"><ion-icon :icon="KIND[p.kind]?.icon" /></span>
                <span class="prod__text">
                  <b>{{ p.name }}</b>
                  <span>{{ KIND[p.kind]?.label }}<template v-if="p.description"> · {{ p.description }}</template></span>
                  <span class="prod__meta">{{ p.sold }} sold · {{ p.available }} in stock · up to {{ p.max_per_order }} per order</span>
                </span>
                <b class="prod__price af-money">{{ peso(p.price) }}</b>
                <span class="prod__btns">
                  <button type="button" class="ibtn" :aria-label="`Edit ${p.name}`" @click="edit(p)"><ion-icon :icon="createOutline" /></button>
                  <AppButton :variant="p.is_active ? 'ghost' : 'secondary'" size="sm" :loading="busyId === p.id" @click="toggle(p)">
                    {{ p.is_active ? 'Hide' : 'Put on sale' }}
                  </AppButton>
                </span>
              </li>
            </ul>
          </section>

          <section class="af-panel pform" aria-labelledby="form-title">
            <SectionHead :title="editing ? `Edit ${form.name || 'product'}` : 'Add a product'" :sub="editing ? 'Changes show on the order screen right away' : 'Customers can order it as soon as you save'" />
            <form class="form" novalidate @submit.prevent="submit">
              <div class="field">
                <span class="field__lbl">What kind?</span>
                <SegmentedControl v-model="form.kind" block label="Kind of product" :options="kindOptions" />
                <span class="af-small">{{ KIND_HELP[form.kind] }}</span>
              </div>
              <TextField v-model="form.name" label="Name" placeholder="1-gallon bottle" required />
              <TextField v-model="form.description" label="Short description" placeholder="Sealed bottle, good for travel" :maxlength="160" />
              <div class="two">
                <TextField v-model="form.price" label="Price (₱)" type="number" inputmode="decimal" required />
                <TextField v-model="form.max_per_order" label="Max per order" type="number" inputmode="numeric" required />
              </div>
              <p v-if="form.error" class="form__err" role="alert">{{ form.error }}</p>
              <AppButton type="submit" size="lg" block :loading="form.busy">{{ editing ? 'Save changes' : 'Add product' }}</AppButton>
              <AppButton v-if="editing" variant="ghost" block @click="startNew">Cancel editing</AppButton>
            </form>
            <p class="af-small">Stock for these is counted on the Stock screen, under "Other products".</p>
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
@media (min-width: 1100px) { .layout { grid-template-columns: minmax(0, 1fr) 400px; } .pform { position: sticky; top: 16px; } }

.plist { list-style: none; margin: 0; padding: 0; display: grid; }
.prod { display: grid; grid-template-columns: 44px minmax(0, 1fr) auto auto; gap: 12px; align-items: center; padding: 12px 2px; border-bottom: 1px solid var(--af-line); }
.prod:last-child { border-bottom: 0; }
.prod--off { opacity: 0.55; }
.prod__icon { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 14px; font-size: 21px; background: var(--af-primary-tint); color: var(--af-primary); }
.prod__icon.k-container { background: var(--af-pearl-tint); color: var(--af-pearl); }
.prod__icon.k-item { background: var(--af-sun-tint); color: var(--af-sun); }
.prod__text { display: grid; gap: 2px; min-width: 0; }
.prod__text b { font-size: 15px; font-weight: 800; }
.prod__text span { font-size: 13px; color: var(--af-ink-2); font-weight: 550; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.prod__meta { font-size: 12.5px !important; }
.prod__price { font-family: var(--af-display); font-size: 18px; font-weight: 650; }
.prod__btns { display: flex; gap: 6px; align-items: center; }
.ibtn { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 50%; border: 0; background: var(--af-surface-2); color: var(--af-primary); font-size: 18px; cursor: pointer; }

.form { display: grid; gap: 14px; }
.field { display: grid; gap: 8px; }
.field__lbl { font-size: 14px; font-weight: 750; }
.field .af-small { line-height: 1.45; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.form__err { margin: 0; padding: 10px 14px; border-radius: 12px; background: var(--af-danger-tint); color: var(--af-danger); font-size: 14px; font-weight: 650; }
.af-panel > p { margin: 0; }
.err { display: grid; gap: 8px; justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }

@media (max-width: 640px) {
  .prod { grid-template-columns: 44px minmax(0, 1fr) auto; }
  .prod__btns { grid-column: 2 / -1; }
}
</style>
