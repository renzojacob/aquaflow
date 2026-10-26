// A tiny fake database for MOCK mode.
// It lives in the browser's localStorage, so orders you place survive a page reload.
// "Reset demo data" (login + profile screens) puts the original sample data back.
import { tokenStorage } from '@/services/tokenStorage'
import { createSeed } from './seed'

const KEY = 'aquaflow.mockdb'
const SEED_VERSION = 2 // bump when seed.js or seedStation.js changes

let cache = null

function persist() {
  try {
    localStorage.setItem(KEY, JSON.stringify(cache))
  } catch {
    /* storage full or blocked: data stays in memory for this session */
  }
}

function load() {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) {
      const data = JSON.parse(raw)
      if (data.version === SEED_VERSION) return data
    }
  } catch {
    /* broken data: start fresh */
  }
  return { version: SEED_VERSION, ...createSeed() }
}

/** The database object. Change it, then call saveDb(). */
export function db() {
  if (!cache) {
    cache = load()
    persist()
  }
  return cache
}

export function saveDb() {
  persist()
}

export function resetMockDb() {
  cache = { version: SEED_VERSION, ...createSeed() }
  persist()
}

/** Copy data before giving it to a screen, so screens can't change the "database" by accident. */
export const clone = (value) => JSON.parse(JSON.stringify(value))

/** Fake network delay so loading states are visible in mock mode. */
export const mockDelay = (ms = 350) => new Promise((resolve) => setTimeout(resolve, ms))

/** Throw the same error shape http.js produces for real API errors. */
export function mockError(kind, status, message, details) {
  return Object.assign(new Error(message), { kind, status, message, details })
}

/** Mock tokens look like "mock.u_maria". The real backend reads the user from the JWT instead. */
export function currentUserId() {
  const token = tokenStorage.get()
  if (!token || !token.startsWith('mock.')) throw mockError('unauthorized', 401, 'Please log in again.')
  return token.slice(5)
}

export function currentUser() {
  const id = currentUserId()
  const user = db().users.find((u) => u.id === id)
  if (!user) throw mockError('unauthorized', 401, 'Please log in again.')
  return user
}

/** User object without the password. */
export function publicUser(u) {
  // eslint-disable-next-line no-unused-vars
  const { password, ...rest } = u
  return clone(rest)
}
