<script setup>
import { reactive, ref } from 'vue'
import { useIonRouter } from '@ionic/vue'

import AppButton from '@/components/ui/AppButton.vue'
import AuthCard from '@/components/layout/AuthCard.vue'
import TextField from '@/components/form/TextField.vue'
import { showToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const ionRouter = useIonRouter()

const form = reactive({ full_name: '', phone: '', email: '', password: '', confirm: '' })
const errors = reactive({})
const formError = ref('')
const loading = ref(false)

/** "0917 555 0142" -> "09175550142" */
const cleanPhone = (p) => p.replace(/[\s-]/g, '')

function validate() {
  Object.keys(errors).forEach((k) => delete errors[k])
  if (form.full_name.trim().length < 3) errors.full_name = 'Enter your full name.'
  if (!/^09\d{9}$/.test(cleanPhone(form.phone))) errors.phone = 'Use an 11-digit mobile number that starts with 09.'
  if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) errors.email = 'Enter a valid email address.'
  if (form.password.length < 8) errors.password = 'Use at least 8 characters.'
  if (form.confirm !== form.password) errors.confirm = "Passwords don't match."
  return Object.keys(errors).length === 0
}

async function submit() {
  formError.value = ''
  if (!validate()) return
  loading.value = true
  try {
    await auth.register({
      full_name: form.full_name,
      phone: cleanPhone(form.phone),
      email: form.email,
      password: form.password,
    })
    showToast('Account created. Add your address to order water.', 'success')
    ionRouter.navigate('/customer/profile', 'root', 'replace')
  } catch (e) {
    formError.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthCard title="Create account" subtitle="For households and stores ordering water. Staff accounts are created by the owner.">
    <form class="af-form" novalidate @submit.prevent="submit">
      <p v-if="formError" class="af-form__alert" role="alert">{{ formError }}</p>
      <TextField v-model="form.full_name" label="Full name" autocomplete="name" required :error="errors.full_name" />
      <TextField
        v-model="form.phone"
        label="Mobile number"
        type="tel"
        inputmode="tel"
        autocomplete="tel"
        placeholder="0917 555 0142"
        hint="The rider calls this number if they can't find your house."
        required
        :error="errors.phone"
      />
      <TextField v-model="form.email" label="Email" type="email" inputmode="email" autocomplete="email" required :error="errors.email" />
      <TextField v-model="form.password" label="Password" type="password" autocomplete="new-password" hint="At least 8 characters." required :error="errors.password" />
      <TextField v-model="form.confirm" label="Confirm password" type="password" autocomplete="new-password" required :error="errors.confirm" />
      <AppButton type="submit" size="lg" block :loading="loading">Create account</AppButton>
    </form>
    <p class="af-switch">Already have an account? <router-link to="/login" class="af-link">Log in</router-link></p>
  </AuthCard>
</template>

<style scoped>
.af-form { display: grid; gap: var(--af-s4); }
.af-form__alert {
  margin: 0;
  padding: 12px 16px;
  border-radius: var(--af-r-sm);
  background: var(--af-danger-tint);
  color: var(--af-danger);
  border: 1px solid color-mix(in srgb, var(--af-danger) 30%, transparent);
  font-weight: 650;
  font-size: 14px;
  line-height: 1.45;
  animation: af-shake 360ms var(--af-ease);
}
@keyframes af-shake { 20%, 60% { transform: translateX(-4px); } 40%, 80% { transform: translateX(4px); } }
.af-link { color: var(--af-primary); font-weight: 750; font-size: 14px; text-decoration: none; background: none; border: 0; padding: 4px 0; cursor: pointer; font-family: var(--af-font); text-underline-offset: 3px; }
.af-link:hover { text-decoration: underline; }
.af-switch { margin: 0; text-align: center; color: var(--af-ink-2); font-size: 14px; }
</style>
