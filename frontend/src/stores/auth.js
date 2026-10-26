// Who is logged in. Pinia store, shared by every screen.
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { ROLE_HOME } from '@/config/navigation'
import * as authService from '@/services/authService'
import { tokenStorage } from '@/services/tokenStorage'

const USER_KEY = 'aquaflow.user'

function readUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw && tokenStorage.get() ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  /** @type {import('vue').Ref<import('@/types/models').User | null>} */
  const user = ref(readUser())

  const isLoggedIn = computed(() => user.value !== null)
  const role = computed(() => user.value?.role ?? null)
  const homePath = computed(() => (role.value ? ROLE_HOME[role.value] : '/login'))

  function setSession({ token, user: u }) {
    tokenStorage.set(token)
    user.value = u
    try {
      localStorage.setItem(USER_KEY, JSON.stringify(u))
    } catch {
      /* ignore */
    }
  }

  async function login(email, password) {
    setSession(await authService.login(email, password))
  }

  async function register(payload) {
    setSession(await authService.register(payload))
  }

  function logout() {
    tokenStorage.clear()
    user.value = null
    try {
      localStorage.removeItem(USER_KEY)
    } catch {
      /* ignore */
    }
  }

  return { user, isLoggedIn, role, homePath, login, register, logout }
})
