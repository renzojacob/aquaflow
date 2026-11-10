<!--
  Owner: people. Everyone with an account, filtered by role, and a form to create
  dispatcher, rider or owner accounts (the public sign-up page only makes customers).
  Accounts can be turned off and on again; they are never deleted (old orders point to them).
-->
<script setup>
import { computed, reactive, ref } from 'vue'
import { IonContent, IonHeader, IonIcon, IonPage, IonTitle, IonToolbar, onIonViewWillEnter } from '@ionic/vue'
import { personAddOutline } from 'ionicons/icons'

import AppButton from '@/components/ui/AppButton.vue'
import SectionHead from '@/components/dash/SectionHead.vue'
import SegmentedControl from '@/components/form/SegmentedControl.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import TextField from '@/components/form/TextField.vue'
import { ROLE_LABEL } from '@/config/navigation'
import { showToast } from '@/composables/useToast'
import { createUser, listUsers, setUserActive } from '@/services/ownerService'
import { useAuthStore } from '@/stores/auth'
import { ago, initials } from '@/utils/format'

const auth = useAuthStore()
const users = ref([])
const loading = ref(true)
const error = ref(null)
const filter = ref('all')
const search = ref('')
const busyId = ref('')

const form = reactive({ full_name: '', email: '', phone: '', role: 'rider', password: '', busy: false, error: '' })

async function load() {
  error.value = null
  try {
    users.value = await listUsers()
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
onIonViewWillEnter(load)

const ROLES = ['customer', 'dispatcher', 'rider', 'owner']
const counts = computed(() => Object.fromEntries(['all', ...ROLES].map((r) => [r, users.value.filter((u) => r === 'all' || u.role === r).length])))
const visible = computed(() => {
  const q = search.value.trim().toLowerCase()
  return users.value
    .filter((u) => filter.value === 'all' || u.role === filter.value)
    .filter((u) => !q || [u.full_name, u.email, u.phone].some((v) => (v ?? '').toLowerCase().includes(q)))
})

async function create() {
  form.error = ''
  if (form.full_name.trim().length < 3) return (form.error = 'Enter their full name.')
  if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) return (form.error = 'Enter a valid email address.')
  if (form.password.length < 8) return (form.error = 'Use at least 8 characters for the password.')
  form.busy = true
  try {
    const u = await createUser({ full_name: form.full_name, email: form.email, phone: form.phone, role: form.role, password: form.password })
    users.value.push(u)
    showToast(`${ROLE_LABEL[u.role]} account created for ${u.full_name}. They can log in now.`, 'success')
    Object.assign(form, { full_name: '', email: '', phone: '', password: '' })
  } catch (e) {
    form.error = e.message
  } finally {
    form.busy = false
  }
}

async function toggle(u) {
  busyId.value = u.id
  try {
    const updated = await setUserActive(u.id, !u.is_active)
    Object.assign(u, updated)
    showToast(updated.is_active ? `${u.full_name} can log in again` : `${u.full_name} can no longer log in`, 'success')
  } catch (e) {
    showToast(e.message, 'danger')
  } finally {
    busyId.value = ''
  }
}

const statLine = (u) =>
  u.role === 'customer' ? `${u.orders} orders, ${u.delivered} delivered` : u.role === 'rider' ? `${u.delivered} deliveries made` : ''
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-title>Users</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content>
      <div class="af-container af-dash">
        <header class="top">
          <h1 class="title">People</h1>
          <p class="af-small">Customers sign up themselves. You create the accounts for your staff here.</p>
        </header>

        <div class="roles">
          <button v-for="r in ['all', ...ROLES]" :key="r" type="button" class="role" :class="[`role--${r}`, { 'is-on': filter === r }]" :aria-pressed="filter === r" @click="filter = r">
            <b>{{ counts[r] }}</b>
            <span>{{ r === 'all' ? 'Everyone' : `${ROLE_LABEL[r]}s` }}</span>
          </button>
        </div>

        <div class="layout">
          <!-- List -->
          <section class="af-panel" aria-labelledby="list-title">
            <SectionHead :title="filter === 'all' ? 'Everyone' : `${ROLE_LABEL[filter]}s`" :sub="`${visible.length} shown`">
              <label class="search">
                <span class="af-sr-only">Search people</span>
                <input v-model="search" type="search" placeholder="Search name, email, phone" />
              </label>
            </SectionHead>

            <SkeletonList v-if="loading" :rows="5" />
            <div v-else-if="error" class="err" role="alert">
              <b>Couldn't load people</b>
              <p>{{ error.message }}</p>
              <AppButton variant="secondary" size="sm" @click="load">Try again</AppButton>
            </div>
            <p v-else-if="!visible.length" class="af-small">No one matches.</p>
            <ul v-else class="people">
              <li v-for="u in visible" :key="u.id" class="person" :class="{ 'person--off': !u.is_active }">
                <span class="person__av" :class="`av--${u.role}`" aria-hidden="true">{{ initials(u.full_name) }}</span>
                <span class="person__text">
                  <b>{{ u.full_name }} <span v-if="u.id === auth.user?.id" class="you">You</span></b>
                  <span>{{ [u.email, u.phone].filter(Boolean).join(', ') }}</span>
                  <span v-if="statLine(u) || u.last_login" class="person__meta">{{ [statLine(u), u.last_login ? `last seen ${ago(u.last_login)}` : ''].filter(Boolean).join(', ') }}</span>
                </span>
                <span class="tag" :class="`tag--${u.role}`">{{ ROLE_LABEL[u.role] }}</span>
                <AppButton
                  v-if="u.id !== auth.user?.id"
                  :variant="u.is_active ? 'ghost' : 'secondary'"
                  size="sm"
                  :loading="busyId === u.id"
                  @click="toggle(u)"
                >
                  {{ u.is_active ? 'Turn off' : 'Turn on' }}
                </AppButton>
              </li>
            </ul>
          </section>

          <!-- Create a staff account -->
          <section class="af-panel create" aria-labelledby="new-title">
            <div class="create__icon" aria-hidden="true"><ion-icon :icon="personAddOutline" /></div>
            <SectionHead title="Add a staff account" sub="They log in with this email and password" />
            <form class="form" novalidate @submit.prevent="create">
              <div class="field">
                <span class="field__lbl" id="role-lbl">Role</span>
                <SegmentedControl v-model="form.role" block label="Role" :options="[{ value: 'rider', label: 'Rider' }, { value: 'dispatcher', label: 'Dispatcher' }, { value: 'owner', label: 'Owner' }]" />
                <span class="af-small">
                  {{ form.role === 'rider' ? 'Brings orders to customers. Shows up in the "who is bringing it?" list.' : form.role === 'dispatcher' ? 'Runs the order queue and the stock.' : 'Sees everything, including this screen.' }}
                </span>
              </div>
              <TextField v-model="form.full_name" label="Full name" autocomplete="off" required />
              <TextField v-model="form.email" label="Email" type="email" inputmode="email" autocomplete="off" required />
              <TextField v-model="form.phone" label="Mobile number" type="tel" inputmode="tel" placeholder="0917 555 0142" hint="Customers can call riders on this number." />
              <TextField v-model="form.password" label="First password" type="password" autocomplete="new-password" hint="At least 8 characters. Not a common one like admin1234." required />
              <p v-if="form.error" class="form__err" role="alert">{{ form.error }}</p>
              <AppButton type="submit" block size="lg" :loading="form.busy">Create {{ ROLE_LABEL[form.role].toLowerCase() }} account</AppButton>
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

.roles { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }
.role { display: grid; gap: 2px; padding: 14px 16px; border-radius: 20px; border: 1.5px solid var(--af-line); background: var(--af-surface); color: var(--af-ink); font-family: var(--af-font); text-align: left; cursor: pointer; }
.role b { font-family: var(--af-display); font-size: 28px; font-weight: 650; letter-spacing: -0.03em; line-height: 1; color: var(--c, var(--af-ink)); }
.role span { font-size: 13px; font-weight: 700; color: var(--af-ink-2); }
.role.is-on { border-color: var(--c, var(--af-primary)); background: color-mix(in srgb, var(--c, var(--af-primary)) 10%, var(--af-surface)); }
.role--customer { --c: var(--af-primary); }
.role--dispatcher { --c: var(--af-st-confirmed); }
.role--rider { --c: var(--af-pearl); }
.role--owner { --c: var(--af-sun); }

.layout { display: grid; gap: 16px; align-items: start; }
@media (min-width: 1100px) { .layout { grid-template-columns: minmax(0, 1fr) 380px; } .create { position: sticky; top: 16px; } }

.search input { width: min(260px, 100%); min-height: 40px; padding: 0 14px; border-radius: 999px; border: 1px solid var(--af-line-strong); background: var(--af-surface-2); color: var(--af-ink); font: 550 14px var(--af-font); }
.search input:focus { outline: none; border-color: var(--af-primary); }

.people { list-style: none; margin: 0; padding: 0; display: grid; }
.person { display: grid; grid-template-columns: 44px minmax(0, 1fr) auto auto; gap: 12px; align-items: center; padding: 12px 4px; border-bottom: 1px solid var(--af-line); }
.person:last-child { border-bottom: 0; }
.person--off { opacity: 0.55; }
.person__av { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 50%; font-weight: 800; font-size: 14px; background: var(--af-surface-3); color: var(--af-ink); }
.av--rider { background: linear-gradient(140deg, var(--af-accent-on-deep), var(--af-glow-c)); color: var(--af-on-glow); }
.av--owner { background: linear-gradient(140deg, var(--af-sun-glow), var(--af-amber)); color: var(--af-on-sun); }
.av--dispatcher { background: linear-gradient(140deg, var(--af-info), var(--af-glow-c)); color: var(--af-on-glow); }
.person__text { display: grid; gap: 2px; min-width: 0; }
.person__text b { font-size: 15px; font-weight: 800; }
.person__text > span { font-size: 13px; color: var(--af-ink-2); font-weight: 550; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.person__meta { font-size: 12.5px !important; }
.you { margin-left: 6px; padding: 2px 8px; border-radius: 999px; background: var(--af-primary-tint); color: var(--af-primary); font-size: 11.5px; font-weight: 800; }
.tag { padding: 5px 11px; border-radius: 999px; font-size: 12.5px; font-weight: 800; color: var(--c); background: color-mix(in srgb, var(--c) 14%, transparent); }
.tag--customer { --c: var(--af-primary); }
.tag--dispatcher { --c: var(--af-st-confirmed); }
.tag--rider { --c: var(--af-pearl); }
.tag--owner { --c: var(--af-sun); }

.create__icon { width: 48px; height: 48px; display: grid; place-items: center; border-radius: 16px; background: var(--af-pearl-tint); color: var(--af-pearl); font-size: 24px; }
.form { display: grid; gap: 14px; }
.field { display: grid; gap: 8px; }
.field__lbl { font-size: 14px; font-weight: 750; }
.field .af-small { line-height: 1.4; }
.form__err { margin: 0; padding: 10px 14px; border-radius: 12px; background: var(--af-danger-tint); color: var(--af-danger); font-size: 14px; font-weight: 650; }

.err { display: grid; gap: 8px; justify-items: start; }
.err b { color: var(--af-danger); }
.err p { margin: 0; color: var(--af-ink-2); }

@media (max-width: 760px) {
  .roles { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .person { grid-template-columns: 44px minmax(0, 1fr) auto; }
  .person .tag { display: none; }
}
</style>
