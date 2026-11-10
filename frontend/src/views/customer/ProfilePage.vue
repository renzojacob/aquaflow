<!--
  Profile: who you are and your numbers, your delivery preferences (saved to your account),
  saved addresses, appearance, log out.
-->
<script setup>
import { computed, reactive, ref } from 'vue'
import { IonContent, IonHeader, IonIcon, IonPage, IonTitle, IonToolbar, alertController, onIonViewWillEnter, useIonRouter } from '@ionic/vue'
import { callOutline, mailOutline, notificationsOutline, starOutline } from 'ionicons/icons'

import AddressFormModal from '@/components/address/AddressFormModal.vue'
import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import MapPicker from '@/components/map/MapPicker.vue'
import QuantityStepper from '@/components/form/QuantityStepper.vue'
import SectionHead from '@/components/dash/SectionHead.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import ThemePicker from '@/components/ui/ThemePicker.vue'
import { env } from '@/config/env'
import { showToast } from '@/composables/useToast'
import { resetMockDb } from '@/mocks/db'
import { deleteAddress, getOrderSettings, getPreferences, listAddresses, listAllOrders, savePreferences, setDefaultAddress } from '@/services/customerService'
import { useAuthStore } from '@/stores/auth'
import { containers, initials, peso } from '@/utils/format'
import { orderStats } from '@/utils/orderStats'

const auth = useAuthStore()
const ionRouter = useIonRouter()

const addresses = ref([])
const settings = ref(null)
const loading = ref(true)
const error = ref(null)
const modalOpen = ref(false)
const editing = ref(null)
const busyId = ref('')
const orders = ref([])
const prefs = reactive({ reminders_enabled: true, usual_quantity: 3, containers_held: 0 })
const savingPrefs = ref(false)

const stats = computed(() => orderStats(orders.value))
const defaultAddress = computed(() => addresses.value.find((a) => a.is_default) ?? null)

async function load() {
  error.value = null
  try {
    const [a, s, o, p] = await Promise.all([listAddresses(), getOrderSettings(), listAllOrders(), getPreferences()])
    addresses.value = a
    settings.value = s
    orders.value = o
    Object.assign(prefs, p)
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
onIonViewWillEnter(load)

function openNew() {
  editing.value = null
  modalOpen.value = true
}
function openEdit(a) {
  editing.value = a
  modalOpen.value = true
}
async function onSaved() {
  showToast('Address saved', 'success')
  await load()
}

async function makeDefault(a) {
  busyId.value = a.id
  try {
    await setDefaultAddress(a.id)
    await load()
  } catch (e) {
    showToast(e.message, 'danger')
  } finally {
    busyId.value = ''
  }
}

async function askDelete(a) {
  const alert = await alertController.create({
    header: `Delete "${a.label}"?`,
    message: 'Orders already placed to this address are not affected.',
    buttons: [
      { text: 'Keep', role: 'cancel' },
      {
        text: 'Delete',
        role: 'destructive',
        handler: async () => {
          busyId.value = a.id
          try {
            await deleteAddress(a.id)
            showToast('Address deleted', 'success')
            await load()
          } catch (e) {
            showToast(e.message, 'danger')
          } finally {
            busyId.value = ''
          }
        },
      },
    ],
  })
  await alert.present()
}

async function savePrefs(patch) {
  savingPrefs.value = true
  Object.assign(prefs, patch)
  try {
    Object.assign(prefs, await savePreferences(patch))
    showToast('Preferences saved', 'success')
  } catch (e) {
    showToast(e.message, 'danger')
  } finally {
    savingPrefs.value = false
  }
}

function logout() {
  auth.logout()
  ionRouter.navigate('/login', 'root', 'replace')
}

function resetDemo() {
  resetMockDb()
  auth.logout()
  ionRouter.navigate('/login', 'root', 'replace')
}
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-title>Profile</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content>
      <div class="af-container af-dash">
        <!-- Who you are -->
        <section class="me af-panel">
          <div class="me__id">
            <span class="avatar" aria-hidden="true">{{ initials(auth.user?.full_name) }}</span>
            <div class="me__text">
              <h1 class="me__name">{{ auth.user?.full_name }}</h1>
              <p v-if="auth.user?.phone"><ion-icon :icon="callOutline" aria-hidden="true" /> {{ auth.user.phone }}</p>
              <p><ion-icon :icon="mailOutline" aria-hidden="true" /> {{ auth.user?.email }}</p>
            </div>
          </div>
          <dl class="me__stats">
            <div><dt>Deliveries</dt><dd>{{ stats.allTime.delivered }}</dd></div>
            <div><dt>Containers</dt><dd>{{ stats.allTime.containers }}</dd></div>
            <div><dt>Spent</dt><dd class="af-money">{{ peso(stats.allTime.spent) }}</dd></div>
            <div><dt>At home now</dt><dd>{{ prefs.containers_held }}</dd></div>
          </dl>
        </section>

        <div class="af-bento af-bento--stretch">
          <!-- Preferences -->
          <section class="af-panel b-6" aria-labelledby="pref-title">
            <SectionHead title="Delivery preferences" sub="Saved to your account" />
            <label class="switch">
              <span class="switch__icon" aria-hidden="true"><ion-icon :icon="notificationsOutline" /></span>
              <span class="switch__text">
                <b>Refill reminders</b>
                <span>We remind you when it's about time to order again.</span>
              </span>
              <input type="checkbox" :checked="prefs.reminders_enabled" :disabled="savingPrefs" @change="savePrefs({ reminders_enabled: $event.target.checked })" />
              <i class="switch__ui" aria-hidden="true"></i>
            </label>
            <div class="usual">
              <span class="switch__icon" aria-hidden="true"><ion-icon :icon="starOutline" /></span>
              <span class="switch__text">
                <b>Your usual order</b>
                <span>
                  {{ containers(prefs.usual_quantity) }}.<template v-if="stats.usualQty && stats.usualQty !== prefs.usual_quantity"> You most often get {{ stats.usualQty }}.</template>
                  <template v-if="stats.everyDays"> You order about every {{ stats.everyDays }} days.</template>
                </span>
              </span>
              <QuantityStepper :model-value="prefs.usual_quantity" :min="1" :max="settings?.max_containers_per_order ?? 10" label="Usual number of containers" @update:model-value="(v) => savePrefs({ usual_quantity: v })" />
            </div>
          </section>

          <!-- Default address on the map -->
          <section class="af-panel b-6" aria-labelledby="home-title">
            <SectionHead title="Default delivery address" :sub="defaultAddress ? `${defaultAddress.label}, ${defaultAddress.barangay}` : 'Not set yet'" />
            <MapPicker v-if="defaultAddress && settings" :key="defaultAddress.id" :model-value="defaultAddress" :station="settings.station" readonly height="190px" :zoom="14" />
            <p v-else class="af-small">Add an address below and it becomes your default.</p>
          </section>
        </div>

        <!-- Addresses -->
        <section aria-labelledby="addr-title" class="stack">
          <SectionHead title="Saved addresses" :sub="`${addresses.length} saved`" :level="2">
            <AppButton v-if="settings" variant="secondary" size="sm" @click="openNew">Add address</AppButton>
          </SectionHead>

          <div v-if="loading" class="af-panel"><SkeletonList :rows="2" /></div>

          <div v-else-if="error" class="af-panel err" role="alert">
            <b>Couldn't load your addresses</b>
            <p>{{ error.message }}</p>
            <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
          </div>

          <div v-else-if="!addresses.length" class="af-panel">
            <EmptyState title="No address yet" message="Add where we should deliver, with a pin on the map." action-label="Add address" @action="openNew" />
          </div>

          <div v-else class="addrs">
            <article v-for="a in addresses" :key="a.id" class="addr" :class="{ 'addr--default': a.is_default }">
              <div class="addr__text">
                <div class="addr__title">
                  <b>{{ a.label }}</b>
                  <span v-if="a.is_default" class="badge">Default</span>
                </div>
                <span>{{ a.street }}, {{ a.barangay }}</span>
                <i v-if="a.landmark">{{ a.landmark }}</i>
              </div>
              <div class="addr__actions">
                <AppButton v-if="!a.is_default" variant="ghost" size="sm" :disabled="busyId === a.id" @click="makeDefault(a)">Make default</AppButton>
                <AppButton variant="secondary" size="sm" @click="openEdit(a)">Edit</AppButton>
                <AppButton variant="danger" size="sm" :disabled="busyId === a.id" @click="askDelete(a)">Delete</AppButton>
              </div>
            </article>
          </div>
        </section>

        <div class="af-bento af-bento--stretch">
          <section class="af-panel b-6">
            <SectionHead title="Appearance" sub="Pick a color theme, then light or dark" />
            <ThemePicker />
          </section>
          <section class="af-panel b-6">
            <SectionHead title="Account" />
            <AppButton variant="secondary" block @click="logout">Log out</AppButton>
            <AppButton v-if="env.useMock" variant="ghost" block @click="resetDemo">Reset demo data</AppButton>
          </section>
        </div>
      </div>

      <AddressFormModal v-if="settings" :is-open="modalOpen" :address="editing" :settings="settings" @close="modalOpen = false" @saved="onSaved" />
    </ion-content>
  </ion-page>
</template>

<style scoped>
.stack { display: grid; gap: 14px; }

/* ---------- who you are ---------- */
.me { grid-template-columns: minmax(0, 1fr); gap: 22px; background: radial-gradient(60% 120% at 0% 0%, color-mix(in srgb, var(--af-pearl) 16%, transparent), transparent 60%), var(--af-surface); }
.me__id { display: flex; align-items: center; gap: 18px; min-width: 0; }
.avatar {
  width: 84px;
  height: 84px;
  flex: none;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: linear-gradient(140deg, #b9b4ff 0%, #4fe0d2 100%);
  color: #04161d;
  font-family: var(--af-display);
  font-size: 28px;
  font-weight: 700;
  box-shadow: 0 0 0 4px var(--af-surface-solid), 0 0 0 5px color-mix(in srgb, var(--af-pearl) 50%, transparent), 0 14px 34px rgba(79, 224, 210, 0.25);
}
.me__text { display: grid; gap: 4px; min-width: 0; }
.me__name { margin: 0 0 4px; font-family: var(--af-display); font-size: clamp(24px, 3vw, 32px); font-weight: 650; letter-spacing: -0.04em; line-height: 1.05; }
.me__text p { margin: 0; display: flex; align-items: center; gap: 8px; color: var(--af-ink-2); font-size: 14px; font-weight: 600; overflow-wrap: anywhere; }
.me__stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin: 0; }
.me__stats div { display: grid; gap: 4px; padding: 12px 14px; border-radius: 16px; background: var(--af-surface-2); min-width: 0; }
.me__stats dt { font-size: 12.5px; font-weight: 700; color: var(--af-ink-2); }
.me__stats dd { margin: 0; font-family: var(--af-display); font-size: 22px; font-weight: 650; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; white-space: nowrap; }
@media (min-width: 900px) {
  .me { grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr); align-items: center; }
}
@media (max-width: 520px) {
  .me__stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .avatar { width: 64px; height: 64px; font-size: 22px; }
}

/* ---------- preferences ---------- */
.switch, .usual { display: grid; grid-template-columns: 40px minmax(0, 1fr) auto; gap: 14px; align-items: center; padding: 12px 14px; border-radius: 18px; background: var(--af-surface-2); }
.switch { cursor: pointer; position: relative; }
.switch__icon { width: 40px; height: 40px; display: grid; place-items: center; border-radius: 12px; background: var(--af-pearl-tint); color: var(--af-pearl); font-size: 19px; }
.switch__text { display: grid; gap: 3px; min-width: 0; }
.switch__text b { font-size: 15px; font-weight: 800; }
.switch__text span { font-size: 13px; font-weight: 600; color: var(--af-ink-2); line-height: 1.4; }
.switch input { position: absolute; opacity: 0; width: 1px; height: 1px; }
.switch__ui { position: relative; width: 50px; height: 30px; border-radius: 999px; background: var(--af-surface-3); border: 1px solid var(--af-line-strong); transition: background var(--af-dur) var(--af-ease); }
.switch__ui::after { content: ''; position: absolute; top: 3px; left: 3px; width: 22px; height: 22px; border-radius: 50%; background: var(--af-ink-2); transition: transform var(--af-dur) var(--af-ease), background var(--af-dur) var(--af-ease); }
.switch input:checked + .switch__ui { background: var(--af-primary); border-color: var(--af-primary); }
.switch input:checked + .switch__ui::after { transform: translateX(20px); background: var(--af-on-primary); }
.switch input:focus-visible + .switch__ui { outline: 3px solid var(--af-focus); outline-offset: 2px; }
.usual :deep(.af-step) { gap: 8px; }
.usual :deep(.af-step__btn) { width: 44px; height: 44px; font-size: 18px; }
.usual :deep(.af-step__value) { min-width: 40px; font-size: 24px; }
.usual :deep(.af-step__value small) { display: none; }
@media (max-width: 520px) {
  .usual { grid-template-columns: 40px minmax(0, 1fr); }
  .usual :deep(.af-step) { grid-column: 1 / -1; justify-content: center; }
}

/* ---------- addresses ---------- */
.addrs { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.addr { display: grid; gap: 14px; align-content: space-between; padding: 18px; border-radius: 22px; background: var(--af-surface); border: 1px solid var(--af-line); }
.addr--default { border-color: color-mix(in srgb, var(--af-primary) 45%, var(--af-line)); background: linear-gradient(160deg, var(--af-primary-tint), transparent 70%), var(--af-surface); }
.addr__text { display: grid; gap: 4px; }
.addr__text b { font-size: 16px; font-weight: 800; }
.addr__text span, .addr__text i { font-size: 14px; color: var(--af-ink-2); }
.addr__title { display: flex; align-items: center; gap: 8px; }
.badge { padding: 3px 10px; border-radius: 999px; background: var(--af-primary); color: var(--af-on-primary) !important; font-size: 12px !important; font-weight: 800; } /* beats .addr__text span */
.addr__actions { display: flex; gap: 8px; flex-wrap: wrap; }

.err { justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }
</style>
