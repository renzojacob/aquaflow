// Dispatcher (and owner) actions on orders and stock, plus dashboard numbers.
// Real mode: Django REST API at /api/v1/dispatch/ (see backend/apps/dispatch/api.py).
// Mock mode copies the backend rules so the UI behaves the same with no server:
//   - only staff may call these (403 otherwise)
//   - status changes must follow DISPATCHER_NEXT
//   - confirming reserves ready stock; it fails if not enough is available
import { env } from '@/config/env'
import { DISPATCHER_NEXT, MAX_ATTEMPTS, RESERVING_STATUSES } from '@/constants/orderStatus'
import { clone, currentUser, db, mockDelay, mockError, saveDb } from '@/mocks/db'
import { dateISO, toISODate } from '@/utils/format'
import { toStaffOrder } from './adapters'
import { http } from './http'

const API = '/api/v1/dispatch'

/** Staff only. In the real app the backend reads the role from the JWT. */
function requireStaff() {
  const me = currentUser()
  if (!['dispatcher', 'owner'].includes(me.role)) {
    throw mockError('forbidden', 403, "Your account isn't allowed to manage orders.")
  }
  return me
}

/** Add customer name + phone to an order for staff screens. */
function withCustomer(order) {
  const c = db().users.find((u) => u.id === order.customer_id)
  return { ...clone(order), customer: { name: c?.full_name ?? 'Unknown', phone: c?.phone ?? '' } }
}

/** Ready stock numbers. reserved = containers promised to confirmed/preparing/ready orders. */
function stockNumbers() {
  const data = db()
  const reserved = data.orders
    .filter((o) => RESERVING_STATUSES.includes(o.status))
    .reduce((sum, o) => sum + o.quantity, 0)
  const onRoad = data.orders.filter((o) => o.status === 'out_for_delivery').reduce((s, o) => s + o.quantity, 0)
  const withCustomers = data.users.filter((u) => u.role === 'customer').reduce((s, u) => s + (u.containers_held ?? 0), 0)
  const ready = data.inventory.filled_ready
  return {
    filled_ready: ready,
    reserved,
    available: ready - reserved,
    empty_at_station: data.inventory.empty_at_station,
    on_road: onRoad,
    with_customers: withCustomers,
    owned_total: ready + data.inventory.empty_at_station + onRoad + withCustomers,
  }
}

// ---------- orders ----------

/**
 * All orders for one delivery day, newest first, with customer info.
 * @param {string} deliveryDate "YYYY-MM-DD"
 */
export async function listQueue(deliveryDate) {
  if (env.useMock) {
    await mockDelay()
    requireStaff()
    return db()
      .orders.filter((o) => o.delivery_date === deliveryDate)
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
      .map(withCustomer)
  }
  const { data } = await http.get(`${API}/orders`, { params: { date: deliveryDate } })
  return data.map(toStaffOrder)
}

export async function getOrderForStaff(id) {
  if (env.useMock) {
    await mockDelay(250)
    requireStaff()
    const order = db().orders.find((o) => o.id === id)
    if (!order) throw mockError('not_found', 404, 'Order not found.')
    return withCustomer(order)
  }
  const { data } = await http.get(`${API}/orders/${id}`)
  return toStaffOrder(data)
}

const NEXT_STATUS = {
  confirm: 'confirmed',
  reject: 'rejected',
  prepare: 'preparing',
  ready: 'ready_for_pickup',
  cancel: 'cancelled',
  replan: 'confirmed',
  dispatch: 'out_for_delivery',
  deliver: 'delivered',
  fail: 'failed_delivery',
}

/**
 * Run one action on an order.
 * @param {string} id
 * @param {'confirm'|'reject'|'prepare'|'ready'|'cancel'|'replan'|'dispatch'|'deliver'|'fail'} action
 * @param {string} [reason] required for reject, cancel and fail
 * @param {{ rider_id?: string|number, empties_collected?: number }} [extra]
 */
export async function runOrderAction(id, action, reason = '', extra = {}) {
  if (env.useMock) {
    await mockDelay(450)
    const me = requireStaff()
    const data = db()
    const order = data.orders.find((o) => o.id === id)
    if (!order) throw mockError('not_found', 404, 'Order not found.')

    // Is this action allowed from the current status? (someone else may have changed it)
    const allowed = (DISPATCHER_NEXT[order.status] ?? []).some((a) => a.action === action)
    if (!allowed || (action === 'replan' && order.attempts >= MAX_ATTEMPTS)) {
      throw mockError('conflict', 409, `This order is now "${order.status.replaceAll('_', ' ')}". Refresh to see the latest.`)
    }
    if (['reject', 'cancel', 'fail'].includes(action) && reason.trim().length < 3) {
      throw mockError('validation', 422, action === 'fail' ? 'Say why it could not be delivered.' : 'Give a reason. The customer will see it.')
    }
    if (action === 'confirm' || action === 'replan') {
      const { available } = stockNumbers()
      if (available < order.quantity) {
        throw mockError(
          'conflict',
          409,
          `Not enough ready stock: ${available} available, this order needs ${order.quantity}. Fill more containers on the Stock screen first.`,
        )
      }
    }

    let note = reason.trim()
    if (action === 'dispatch') {
      const rider = extra.rider_id ? data.users.find((u) => u.id === extra.rider_id && u.role === 'rider') : null
      order.rider = rider ? { id: rider.id, name: rider.full_name, phone: rider.phone } : null
      order.trip = null
      data.inventory.filled_ready -= order.quantity // loaded onto the tricycle
      order.attempts = (order.attempts ?? 0) + 1
      note = rider ? `Sent out with ${rider.full_name}` : 'Sent out'
    }
    if (action === 'deliver') {
      const empties = Number.isInteger(extra.empties_collected) ? extra.empties_collected : order.empties_to_return
      const customer = data.users.find((u) => u.id === order.customer_id)
      if (customer) customer.containers_held = (customer.containers_held ?? 0) + order.quantity - empties
      data.inventory.empty_at_station += empties
      note = 'Delivered'
    }
    if (action === 'fail') data.inventory.filled_ready += order.quantity // came back unsold
    if (action === 'replan') note = 'Re-planned for the next trip'

    const next = NEXT_STATUS[action]
    order.status = next
    order.history.push({ status: next, at: new Date().toISOString(), by: me.full_name, ...(note ? { note } : {}) })
    saveDb()
    return withCustomer(order)
  }
  const { data } = await http.post(`${API}/orders/${id}/${action}`, { reason, ...extra })
  return toStaffOrder(data)
}

/** Active riders for the "who is bringing it?" picker. */
export async function listRiders() {
  if (env.useMock) {
    await mockDelay(150)
    requireStaff()
    const today = dateISO(0)
    return db()
      .users.filter((u) => u.role === 'rider')
      .map((r) => ({
        id: r.id,
        name: r.full_name,
        phone: r.phone,
        on_road: db().orders.filter((o) => o.status === 'out_for_delivery' && o.delivery_date === today && o.rider?.id === r.id).length,
      }))
  }
  const { data } = await http.get(`${API}/riders`)
  return data
}

// ---------- stock ----------

export async function getStock() {
  if (env.useMock) {
    await mockDelay(250)
    requireStaff()
    const log = [...db().stock_log].sort((a, b) => b.at.localeCompare(a.at))
    return { ...stockNumbers(), log: clone(log) }
  }
  const { data } = await http.get(`${API}/stock`)
  return data
}

/**
 * refill:     `quantity` empties were washed and filled -> ready stock goes up, empties go down
 * correction: physical count; `quantity` is the real number of filled containers on hand
 * receive:    `quantity` brand-new empty containers arrived at the station
 * @param {{ type: 'refill' | 'correction' | 'receive', quantity: number, reason: string }} payload
 */
export async function adjustStock(payload) {
  if (env.useMock) {
    await mockDelay(450)
    const me = requireStaff()
    const inv = db().inventory
    const qty = Number(payload.quantity)
    if (!Number.isInteger(qty) || qty < 0) throw mockError('validation', 422, 'Enter a whole number.')

    let delta
    if (payload.type === 'refill') {
      if (qty < 1) throw mockError('validation', 422, 'Enter how many containers you filled.')
      if (qty > inv.empty_at_station) {
        throw mockError('validation', 422, `Only ${inv.empty_at_station} empty containers are at the station.`)
      }
      delta = qty
      inv.filled_ready += qty
      inv.empty_at_station -= qty
    } else if (payload.type === 'receive') {
      if (qty < 1) throw mockError('validation', 422, 'Enter how many new containers arrived.')
      delta = qty
      inv.empty_at_station += qty
    } else {
      if (payload.reason.trim().length < 3) throw mockError('validation', 422, 'Say why the count changed.')
      const { reserved } = stockNumbers()
      if (qty < reserved) {
        throw mockError('validation', 422, `${reserved} containers are already promised to confirmed orders. Count again, or cancel some orders first.`)
      }
      delta = qty - inv.filled_ready
      inv.filled_ready = qty
    }

    const fallback = { refill: 'Refill batch', receive: 'New containers received' }[payload.type] ?? ''
    db().stock_log.push({
      at: new Date().toISOString(),
      type: payload.type,
      delta,
      reason: payload.reason.trim() || fallback,
      by: me.full_name,
    })
    saveDb()
    return getStock()
  }
  const { data } = await http.post(`${API}/stock/adjust`, payload)
  return data
}

// ---------- dashboard numbers ----------

/**
 * Real numbers for the dispatcher and owner dashboards (last `days` days, today included).
 * Same shape in mock and real mode.
 */
export async function getSummary(days = 14) {
  if (env.useMock) {
    await mockDelay(300)
    requireStaff()
    return mockSummary(days)
  }
  const { data } = await http.get(`${API}/summary`, { params: { days } })
  return {
    ...data,
    status_today: Object.fromEntries(
      Object.entries(data.status_today || {}).map(([k, v]) => [k === 'ready' ? 'ready_for_pickup' : k === 'failed' ? 'failed_delivery' : k, v]),
    ),
  }
}

function mockSummary(days) {
  const data = db()
  const today = new Date()
  const list = []
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    list.push({ date: toISODate(d), orders: 0, delivered: 0, containers: 0, revenue: 0 })
  }
  const byDate = Object.fromEntries(list.map((d) => [d.date, d]))
  const window = data.orders.filter((o) => byDate[o.delivery_date])
  for (const o of window) {
    const d = byDate[o.delivery_date]
    d.orders += 1
    if (o.status === 'delivered') {
      d.delivered += 1
      d.containers += o.quantity
      d.revenue += o.total
    }
  }
  const statusToday = {}
  for (const o of data.orders.filter((x) => x.delivery_date === dateISO(0))) statusToday[o.status] = (statusToday[o.status] ?? 0) + 1

  const brgy = {}
  for (const o of window.filter((x) => !['rejected', 'cancelled'].includes(x.status))) {
    const b = (brgy[o.address.barangay] ??= { name: o.address.barangay, orders: 0, containers: 0 })
    b.orders += 1
    b.containers += o.quantity
  }
  const delivered = window.filter((o) => o.status === 'delivered')
  const start = list[0].date
  const customers = data.users.filter((u) => u.role === 'customer')
  return clone({
    days: list,
    status_today: statusToday,
    top_barangays: Object.values(brgy).sort((a, b) => b.orders - a.orders).slice(0, 6),
    periods: {
      morning: window.filter((o) => o.period === 'morning').length,
      afternoon: window.filter((o) => o.period === 'afternoon').length,
    },
    totals: {
      orders: window.length,
      delivered: delivered.length,
      failed: window.filter((o) => o.status === 'failed_delivery').length,
      cancelled: window.filter((o) => ['cancelled', 'rejected'].includes(o.status)).length,
      revenue: delivered.reduce((s, o) => s + o.total, 0),
      containers: delivered.reduce((s, o) => s + o.quantity, 0),
    },
    customers: customers.length,
    new_customers: customers.filter((u) => (u.joined ?? '0000') >= start).length,
    riders: data.users.filter((u) => u.role === 'rider').length,
    stock: stockNumbers(),
  })
}

