<script setup>
import { reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useIonRouter } from '@ionic/vue'

import AppButton from '@/components/ui/AppButton.vue'
import AuthCard from '@/components/layout/AuthCard.vue'
import TextField from '@/components/form/TextField.vue'
import { env } from '@/config/env'
import { ROLE_LABEL } from '@/config/navigation'
import { showToast } from '@/composables/useToast'
import { resetMockDb } from '@/mocks/db'
import { demoAccounts } from '@/services/authService'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const ionRouter = useIonRouter()

const form = reactive({ email: '', password: '' })
const errors = reactive({ email: '', password: '' })
const formError = ref('')
const loading = ref(false)
const demos = ref(env.useMock ? demoAccounts() : [])

function validate() {
  errors.email = /^\S+@\S+\.\S+$/.test(form.email.trim()) ? '' : 'Enter a valid email address.'
  errors.password = form.password ? '' : 'Enter your password.'
  return !errors.email && !errors.password
}

async function submit() {
  formError.value = ''
  if (!validate()) return
  loading.value = true
  try {
    await auth.login(form.email, form.password)
    // Go back to the page they wanted, but only if it belongs to their role
    const wanted = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    const target = wanted.startsWith(`/${auth.role}/`) ? wanted : auth.homePath
    ionRouter.navigate(target, 'root', 'replace')
  } catch (e) {
    formError.value = e.message
  } finally {
    loading.value = false
  }
}

function useDemo(account) {
  form.email = account.email
  form.password = 'aquaflow123'
  submit()
}

function resetDemo() {
  resetMockDb()
  demos.value = demoAccounts()
  showToast('Demo data reset', 'success')
}
</script>

<template>
  <AuthCard title="Log in" subtitle="Welcome back. Log in to order water or manage deliveries.">
    <form class="af-form" novalidate @submit.prevent="submit">
      <p v-if="formError" class="af-form__alert" role="alert">{{ formError }}</p>
      <TextField v-model="form.email" label="Email" type="email" autocomplete="email" inputmode="email" required :error="errors.email" />
      <TextField v-model="form.password" label="Password" type="password" autocomplete="current-password" required :error="errors.password" />
      <div class="af-form__row">
        <router-link to="/forgot-password" class="af-link">Forgot password?</router-link>
      </div>
      <AppButton type="submit" size="lg" block :loading="loading">Log in</AppButton>
    </form>

    <p class="af-switch">New customer? <router-link to="/register" class="af-link">Create an account</router-link></p>

    <section v-if="env.useMock" class="af-demo" aria-labelledby="demo-title">
      <div class="af-demo__head">
        <h2 id="demo-title" class="af-caption">Demo accounts · mock mode</h2>
        <button type="button" class="af-link af-demo__reset" @click="resetDemo">Reset demo data</button>
      </div>
      <div class="af-demo__grid">
        <button v-for="a in demos" :key="a.id" type="button" class="af-demo__btn" :disabled="loading" @click="useDemo(a)">
          <b>{{ ROLE_LABEL[a.role] }}</b>
          <span>{{ a.full_name }}</span>
        </button>
      </div>
      <p class="af-demo__note">Password for all demo accounts: <code>aquaflow123</code></p>
    </section>
  </AuthCard>
</template>

<style scoped>
.af-form { display: grid; gap: var(--af-s4); }
.af-form__alert { margin: 0; padding: 12px 14px; border-radius: var(--af-r-sm); background: var(--af-danger-tint); color: var(--af-danger); font-weight: 600; font-size: 14px; }
.af-form__row { display: flex; justify-content: flex-end; margin-top: calc(var(--af-s2) * -1); }
.af-link { color: var(--af-primary); font-weight: 700; font-size: 14px; text-decoration: none; background: none; border: 0; padding: 4px 0; cursor: pointer; font-family: var(--af-font); }
.af-link:hover { text-decoration: underline; }
.af-switch { margin: 0; text-align: center; color: var(--af-ink-2); font-size: 14px; }

.af-demo { display: grid; gap: var(--af-s3); padding: var(--af-s4); border: 1.5px dashed var(--af-line); border-radius: var(--af-r-md); }
.af-demo__head { display: flex; justify-content: space-between; align-items: center; gap: var(--af-s2); flex-wrap: wrap; }
.af-demo__head h2 { margin: 0; }
.af-demo__reset { font-size: 13px; }
.af-demo__grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--af-s2); }
.af-demo__btn {
  display: grid;
  gap: 2px;
  text-align: left;
  min-height: 56px;
  padding: 10px 12px;
  border-radius: var(--af-r-sm);
  border: 1px solid var(--af-line);
  background: var(--af-surface);
  color: var(--af-ink);
  font-family: var(--af-font);
  cursor: pointer;
}
.af-demo__btn:hover:not(:disabled) { border-color: var(--af-primary); background: var(--af-primary-tint); }
.af-demo__btn b { font-size: 14px; }
.af-demo__btn span { font-size: 12px; color: var(--af-ink-2); }
.af-demo__note { margin: 0; font-size: 12px; color: var(--af-ink-2); }
.af-demo__note code { font-family: var(--af-mono); font-weight: 600; color: var(--af-ink); }
</style>
