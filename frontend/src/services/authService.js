// Login, register, password reset.
// Mock mode checks the fake users in mocks/seed.js.
// Real mode calls the Django REST API.
import { env } from '@/config/env'
import { db, mockDelay, mockError, publicUser, saveDb } from '@/mocks/db'
import { http } from './http'

/** @typedef {import('@/types/models').AuthResult} AuthResult */

/**
 * @param {string} email
 * @param {string} password
 * @returns {Promise<AuthResult>}
 */
export async function login(email, password) {
  if (env.useMock) {
    await mockDelay(500)
    const user = db().users.find((u) => u.email.toLowerCase() === email.trim().toLowerCase())
    if (!user || user.password !== password) {
      throw mockError('unauthorized', 401, 'Wrong email or password.')
    }
    return { token: `mock.${user.id}`, user: publicUser(user) }
  }
  // Django URLs end with "/" — without it, POST requests fail
  const { data } = await http.post('/api/auth/login/', { email: email.trim(), password })
  return data
}

/**
 * Customers create their own accounts. Staff and riders are created by the owner.
 * @param {{full_name: string, phone: string, email: string, password: string}} payload
 * @returns {Promise<AuthResult>}
 */
export async function register(payload) {
  if (env.useMock) {
    await mockDelay(600)
    const data = db()
    const email = payload.email.trim().toLowerCase()
    if (data.users.some((u) => u.email.toLowerCase() === email)) {
      throw mockError('conflict', 409, 'An account with this email already exists. Try logging in.')
    }
    const user = {
      id: `u_${Date.now()}`,
      role: 'customer',
      full_name: payload.full_name.trim(),
      email,
      phone: payload.phone,
      password: payload.password,
      containers_held: 0,
    }
    data.users.push(user)
    saveDb()
    return { token: `mock.${user.id}`, user: publicUser(user) }
  }
  const { data } = await http.post('/api/auth/register/', {
    full_name: payload.full_name.trim(),
    phone: payload.phone.trim(),
    email: payload.email.trim(),
    password: payload.password,
  })
  return data
}

/**
 * Sends a reset link by email (Brevo, from the backend).
 * Always "succeeds" so nobody can use this form to check which emails have accounts.
 * @param {string} email
 */
// eslint-disable-next-line no-unused-vars
export async function requestPasswordReset(email) {
  if (env.useMock) {
    await mockDelay(600)
    return
  }
  // TODO: call POST /api/auth/forgot-password/ once the Brevo email step is built
  return
}

/** Demo accounts shown on the login screen in mock mode. */
export function demoAccounts() {
  const ids = ['u_maria', 'u_joy', 'u_jomar', 'u_ramon']
  return db()
    .users.filter((u) => ids.includes(u.id))
    .map(publicUser)
}