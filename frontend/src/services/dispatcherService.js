// Dispatcher (and owner) actions on orders and stock.
// Mock mode copies the backend rules so the UI behaves the same before FastAPI exists:
//   - only staff may call these (403 otherwise)
//   - status changes must follow DISPATCHER_NEXT
//   - confirming reserves ready stock; it fails if not enough is available
import { env } from '@/config/env'
import { DISPATCHER_NEXT, MAX_ATTEMPTS, RESERVING_STATUSES } from '@/constants/orderStatus'
import { clone, currentUser, db, mockDelay, mockError, saveDb } from '@/mocks/db'
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
  const ready = data.inventory.filled_ready
  return {
    filled_ready: ready,
    reserved,
    available: ready - reserved,
    empty_at_station: data.inventory.empty_at_station,
    owned_total: data.inventory.owned_total,
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
  return data
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
  return data
}

/**
 * Run one action on an order.
 * @param {string} id
 * @param {'confirm'|'reject'|'prepare'|'ready'|'cancel'|'replan'} action
 * @param {string} [reason] required for reject and cancel
 */
export async function runOrderAction(id, action, reason = '') {
  if (env.useMock) {
    await mockDelay(450)
    const me = requireStaff()
    const order = db().orders.find((o) => o.id === id)
    if (!order) throw mockError('not_found', 404, 'Order not found.')

    // Is this action allowed from the current status? (someone else may have changed it)
    const allowed = (DISPATCHER_NEXT[order.status] ?? []).some((a) => a.action === action)
    if (!allowed || (action === 'replan' && order.attempts >= MAX_ATTEMPTS)) {
      throw mockError('conflict', 409, `This order is now "${order.status.replaceAll('_', ' ')}". Refresh to see the latest.`)
    }
    if (['reject', 'cancel'].includes(action) && reason.trim().length < 3) {
      throw mockError('validation', 422, 'Give a reason. The customer will see it.')
    }
    if (action === 'confirm') {
      const { available } = stockNumbers()
      if (available < order.quantity) {
        throw mockError(
          'conflict',
          409,
          `Not enough ready stock: ${available} available, this order needs ${order.quantity}. Fill more containers on the Stock screen first.`,
        )
      }
    }

    const next = {
      confirm: 'confirmed',
      reject: 'rejected',
      prepare: 'preparing',
      ready: 'ready_for_pickup',
      cancel: 'cancelled',
      replan: 'ready_for_pickup',
    }[action]

    order.status = next
    if (action === 'replan') order.trip = null
    order.history.push({
      status: next,
      at: new Date().toISOString(),
      by: me.full_name,
      ...(reason.trim() ? { note: reason.trim() } : action === 'replan' ? { note: 'Re-planned for the next trip' } : {}),
    })
    saveDb()
    // TODO(backend): email the customer through Brevo on confirm / reject / cancel
    return withCustomer(order)
  }
  const { data } = await http.post(`${API}/orders/${id}/${action}`, { reason })
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
 * @param {{ type: 'refill' | 'correction', quantity: number, reason: string }} payload
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
    } else {
      if (payload.reason.trim().length < 3) throw mockError('validation', 422, 'Say why the count changed.')
      const { reserved } = stockNumbers()
      if (qty < reserved) {
        throw mockError('validation', 422, `${reserved} containers are already promised to confirmed orders. Count again, or cancel some orders first.`)
      }
      delta = qty - inv.filled_ready
      inv.filled_ready = qty
    }

    db().stock_log.push({
      at: new Date().toISOString(),
      type: payload.type,
      delta,
      reason: payload.reason.trim() || (payload.type === 'refill' ? 'Refill batch' : ''),
      by: me.full_name,
    })
    saveDb()
    return getStock()
  }
  const { data } = await http.post(`${API}/stock/adjust`, payload)
  return data
}
