// Owner: manage people. This is how dispatcher and rider accounts get made
// (the public sign-up page only creates customers).
// Real mode: /api/v1/owner/ (backend/apps/accounts/staff_api.py).
import { env } from '@/config/env'
import { clone, currentUser, db, mockDelay, mockError, saveDb } from '@/mocks/db'
import { http } from './http'

const API = '/api/v1/owner'

function requireOwner() {
  const me = currentUser()
  if (me.role !== 'owner') throw mockError('forbidden', 403, 'Only the owner can manage accounts.')
  return me
}

function row(u) {
  const data = db()
  const mine = data.orders.filter((o) => o.customer_id === u.id)
  const rides = data.orders.filter((o) => o.rider?.id === u.id && o.status === 'delivered')
  return {
    id: u.id,
    full_name: u.full_name,
    email: u.email,
    phone: u.phone ?? '',
    role: u.role,
    is_active: u.is_active !== false,
    date_joined: u.joined ?? null,
    last_login: null,
    orders: mine.length,
    delivered: u.role === 'rider' ? rides.length : mine.filter((o) => o.status === 'delivered').length,
  }
}

/** @param {string} [role] customer | dispatcher | rider | owner */
export async function listUsers(role) {
  if (env.useMock) {
    await mockDelay(300)
    requireOwner()
    return clone(db().users.filter((u) => !role || u.role === role).map(row))
  }
  const { data } = await http.get(`${API}/users`, { params: role ? { role } : {} })
  return data
}

/** @param {{ full_name: string, email: string, phone: string, role: string, password: string }} payload */
export async function createUser(payload) {
  if (env.useMock) {
    await mockDelay(500)
    requireOwner()
    const data = db()
    const email = payload.email.trim().toLowerCase()
    if (data.users.some((u) => u.email.toLowerCase() === email)) {
      throw mockError('validation', 400, 'An account with this email already exists.')
    }
    if (payload.password.length < 8) throw mockError('validation', 400, 'This password is too short. It must contain at least 8 characters.')
    const user = {
      id: `u_${Date.now()}`,
      role: payload.role,
      full_name: payload.full_name.trim(),
      email,
      phone: payload.phone.trim(),
      password: payload.password,
      joined: new Date().toISOString(),
    }
    data.users.push(user)
    saveDb()
    return clone(row(user))
  }
  const { data } = await http.post(`${API}/users`, payload)
  return data
}

export async function setUserActive(id, isActive) {
  if (env.useMock) {
    await mockDelay(300)
    const me = requireOwner()
    if (id === me.id) throw mockError('validation', 400, "You can't deactivate your own account.")
    const user = db().users.find((u) => u.id === id)
    if (!user) throw mockError('not_found', 404, 'Account not found.')
    user.is_active = isActive
    saveDb()
    return clone(row(user))
  }
  const { data } = await http.patch(`${API}/users/${id}`, { is_active: isActive })
  return data
}
