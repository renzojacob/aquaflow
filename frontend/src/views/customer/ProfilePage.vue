<!-- Profile: account info, saved addresses, theme, log out. -->
<script setup>
import { ref } from 'vue'
import { IonContent, IonHeader, IonPage, IonTitle, IonToolbar, alertController, onIonViewWillEnter, useIonRouter } from '@ionic/vue'

import AddressFormModal from '@/components/address/AddressFormModal.vue'
import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import ThemeSwitch from '@/components/ui/ThemeSwitch.vue'
import { env } from '@/config/env'
import { showToast } from '@/composables/useToast'
import { resetMockDb } from '@/mocks/db'
import { deleteAddress, getOrderSettings, listAddresses, setDefaultAddress } from '@/services/customerService'
import { useAuthStore } from '@/stores/auth'
import { initials } from '@/utils/format'

const auth = useAuthStore()
const ionRouter = useIonRouter()

const addresses = ref([])
const settings = ref(null)
const loading = ref(true)
const error = ref(null)
const modalOpen = ref(false)
const editing = ref(null)
const busyId = ref('')

async function load() {
  error.value = null
  try {
    const [a, s] = await Promise.all([listAddresses(), getOrderSettings()])
    addresses.value = a
    settings.value = s
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
      <div class="af-container narrow">
        <!-- Account -->
        <section class="af-card me">
          <span class="avatar" aria-hidden="true">{{ initials(auth.user?.full_name) }}</span>
          <div class="me__text">
            <h1 class="af-h2">{{ auth.user?.full_name }}</h1>
            <p>{{ auth.user?.phone }}</p>
            <p>{{ auth.user?.email }}</p>
          </div>
        </section>

        <!-- Addresses -->
        <section aria-labelledby="addr-title" class="stack">
          <div class="row">
            <h2 id="addr-title" class="af-h3">Saved addresses</h2>
            <AppButton v-if="settings" variant="ghost" size="sm" @click="openNew">Add address</AppButton>
          </div>

          <div v-if="loading" class="af-card"><SkeletonList :rows="2" /></div>

          <div v-else-if="error" class="af-card err" role="alert">
            <b>Couldn't load your addresses</b>
            <p>{{ error.message }}</p>
            <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
          </div>

          <div v-else-if="!addresses.length" class="af-card">
            <EmptyState title="No address yet" message="Add where we should deliver, with a pin on the map." action-label="Add address" @action="openNew" />
          </div>

          <article v-for="a in addresses" v-else :key="a.id" class="af-card addr">
            <div class="addr__text">
              <div class="addr__title">
                <b>{{ a.label }}</b>
                <span v-if="a.is_default" class="badge">Default</span>
              </div>
              <span>{{ a.street }}, {{ a.barangay }}</span>
              <i>{{ a.landmark }}</i>
            </div>
            <div class="addr__actions">
              <AppButton v-if="!a.is_default" variant="ghost" size="sm" :disabled="busyId === a.id" @click="makeDefault(a)">Set as default</AppButton>
              <AppButton variant="secondary" size="sm" @click="openEdit(a)">Edit</AppButton>
              <AppButton variant="danger" size="sm" :disabled="busyId === a.id" @click="askDelete(a)">Delete</AppButton>
            </div>
          </article>
        </section>

        <!-- Appearance -->
        <section class="af-card stack">
          <h2 class="af-h3">Appearance</h2>
          <ThemeSwitch block />
        </section>

        <!-- Session -->
        <section class="stack">
          <AppButton variant="secondary" block @click="logout">Log out</AppButton>
          <AppButton v-if="env.useMock" variant="ghost" block @click="resetDemo">Reset demo data</AppButton>
        </section>
      </div>

      <AddressFormModal v-if="settings" :is-open="modalOpen" :address="editing" :settings="settings" @close="modalOpen = false" @saved="onSaved" />
    </ion-content>
  </ion-page>
</template>

<style scoped>
.narrow { max-width: 720px; gap: var(--af-s5); }
.stack { display: grid; gap: var(--af-s3); }
.stack h2 { margin: 0; }
.row { display: flex; justify-content: space-between; align-items: center; gap: var(--af-s2); }

.me { display: flex; align-items: center; gap: var(--af-s4); overflow: hidden; }
.me__text { display: grid; gap: 2px; min-width: 0; }
.me__text h1 { margin: 0 0 6px; }
.me__text p { margin: 0; color: var(--af-ink-2); font-size: 14px; overflow-wrap: anywhere; }
.avatar {
  width: 72px;
  height: 72px;
  flex: none;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: linear-gradient(140deg, #4fe0d2 0%, #1aa6b5 100%);
  color: #022320;
  font-family: var(--af-display);
  font-size: 24px;
  font-weight: 700;
  box-shadow: 0 0 0 4px var(--af-surface), 0 0 0 5px color-mix(in srgb, var(--af-primary) 40%, transparent), 0 10px 28px rgba(26, 166, 181, 0.3);
}

.addr { display: grid; gap: var(--af-s3); padding: var(--af-s4) var(--af-s5); }
.addr__text { display: grid; gap: 4px; }
.addr__text b { font-size: 16px; font-weight: 800; }
.addr__text span, .addr__text i { font-size: 14px; color: var(--af-ink-2); }
.addr__title { display: flex; align-items: center; gap: var(--af-s2); }
.badge { padding: 3px 9px; border-radius: var(--af-r-pill); background: var(--af-primary-tint); color: var(--af-primary) !important; font-family: var(--af-mono); font-size: 10px !important; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; } /* beats .addr__text span */
.addr__actions { display: flex; gap: var(--af-s2); flex-wrap: wrap; }

.err { display: grid; gap: var(--af-s2); justify-items: start; border-color: color-mix(in srgb, var(--af-danger) 40%, var(--af-line)); }
.err b { color: var(--af-danger); font-weight: 800; }
.err p { margin: 0; color: var(--af-ink-2); }
</style>
