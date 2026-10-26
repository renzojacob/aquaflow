<script setup>
import { ref } from 'vue'

import AppButton from '@/components/ui/AppButton.vue'
import AuthCard from '@/components/layout/AuthCard.vue'
import TextField from '@/components/form/TextField.vue'
import { requestPasswordReset } from '@/services/authService'

const email = ref('')
const error = ref('')
const loading = ref(false)
const sent = ref(false)

async function submit() {
  error.value = /^\S+@\S+\.\S+$/.test(email.value.trim()) ? '' : 'Enter a valid email address.'
  if (error.value) return
  loading.value = true
  try {
    await requestPasswordReset(email.value.trim())
    sent.value = true
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthCard
    :title="sent ? 'Check your email' : 'Reset password'"
    :subtitle="sent ? '' : 'Enter your account email and we\'ll send you a link to set a new password.'"
  >
    <div v-if="sent" class="af-sent" role="status">
      <p>
        If <b>{{ email }}</b> has an AquaFlow account, a reset link is on its way. The link works for 30 minutes.
      </p>
      <p class="af-muted">No email after 5 minutes? Check your spam folder, or try again.</p>
      <AppButton variant="secondary" block @click="sent = false">Try another email</AppButton>
    </div>

    <form v-else class="af-form" novalidate @submit.prevent="submit">
      <TextField v-model="email" label="Email" type="email" inputmode="email" autocomplete="email" required :error="error" />
      <AppButton type="submit" size="lg" block :loading="loading">Send reset link</AppButton>
    </form>

    <p class="af-switch"><router-link to="/login" class="af-link">Back to log in</router-link></p>
  </AuthCard>
</template>

<style scoped>
.af-form,
.af-sent { display: grid; gap: var(--af-s4); }
.af-sent p { margin: 0; line-height: 1.5; }
.af-link { color: var(--af-primary); font-weight: 700; text-decoration: none; }
.af-switch { margin: 0; text-align: center; font-size: 14px; }
</style>
