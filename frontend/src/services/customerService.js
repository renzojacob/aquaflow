// Everything the customer screens need.
// Each function: mock mode -> fake data, real mode -> FastAPI.
// The backend must enforce the same rules (it is the real security);
// the mock copies them so the UI behaves the same before the backend exists.
import { env } from '@/config/env'
import { CUSTOMER_CANCELLABLE, isActive } from '@/constants/orderStatus'
import { clone, currentUser, db, mockDelay, mockError, saveDb } from '@/mocks/db'
import { dateISO } from '@/utils/format'
import { insideArea } from '@/utils/geo'
import { http } from './http'

/** @typedef {import('@/types/models').Order} Order */
/** @typedef {import('@/types/models').Address} Address */
/** @typedef {import('@/types/models').OrderSettings} OrderSettings */

const API = '/api/v1'

// ---------- helpers ----------
const newestFirst = (a, b) => b.created_at.localeCompare(a.created_at)

function serviceArea(settings) {
  return { lat: settings.station.lat, lng: settings.station.lng, radiusKm: settings.service_radius_km }
}

/** Is ordering for this day + period still open? cutoff is "HH:MM". */
export function periodOpen(settings, deliveryDate, period, now = new Date()) {
  if (deliveryDate !== dateISO(0)) return true
  const [h, m] = settings.cutoff[period].split(':').map(Number)
  return now.getHours() * 60 + now.getMinutes() < h * 60 + m
}

// ---------- settings ----------
/** @returns {Promise<OrderSettings>} */
export async function getOrderSettings() {
  if (env.useMock) {
    await mockDelay(150)
    return clone(db().settings)
  }
  const { data } = await http.get(`${API}/settings/public`)
  return data
}

// ---------- home ----------
/**
 * @returns {Promise<{ containers_held: number, active_orders: Order[], last_delivered: Order | null }>}
 */
export async function getCustomerSummary() {
  if (env.useMock) {
    await mockDelay()
    const me = currentUser()
    const mine = db().orders.filter((o) => o.customer_id === me.id).sort(newestFirst)
    return clone({
      containers_held: me.containers_held ?? 0,
      active_orders: mine.filter(isActive),
      last_delivered: mine.find((o) => o.status === 'delivered') ?? null,
    })
  }
  const { data } = await http.get(`${API}/customer/summary`)
  return data
}

// ---------- orders ----------
/**
 * @param {'active' | 'past'} scope
 * @returns {Promise<Order[]>}
 */
export async function listOrders(scope) {
  if (env.useMock) {
    await mockDelay()
    const me = currentUser()
    const mine = db().orders.filter((o) => o.customer_id === me.id).sort(newestFirst)
    return clone(mine.filter((o) => (scope === 'active' ? isActive(o) : !isActive(o))))
  }
  const { data } = await http.get(`${API}/orders`, { params: { scope } })
  return data
}

/** @returns {Promise<Order>} */
export async function getOrder(id) {
  if (env.useMock) {
    await mockDelay()
    const me = currentUser()
    const order = db().orders.find((o) => o.id === id)
    // Another customer's order looks exactly like a missing one (don't leak that it exists)
    if (!order || order.customer_id !== me.id) throw mockError('not_found', 404, 'Order not found.')
    return clone(order)
  }
  const { data } = await http.get(`${API}/orders/${id}`)
  return data
}

/**
 * @param {{ quantity: number, address_id: string, delivery_date: string,
 *           period: 'morning' | 'afternoon', empties_to_return: number, notes: string }} payload
 * @returns {Promise<Order>}
 */
export async function createOrder(payload) {
  if (env.useMock) {
    await mockDelay(700)
    const data = db()
    const me = currentUser()
    const s = data.settings
    const address = data.addresses.find((a) => a.id === payload.address_id && a.user_id === me.id)

    if (!Number.isInteger(payload.quantity) || payload.quantity < 1 || payload.quantity > s.max_containers_per_order) {
      throw mockError('validation', 422, `Order between 1 and ${s.max_containers_per_order} containers.`)
    }
    if (!address) throw mockError('validation', 422, 'Choose a delivery address.')
    if (!insideArea(address, serviceArea(s))) {
      throw mockError('validation', 422, 'This address is outside our delivery area.')
    }
    if (payload.delivery_date < dateISO(0) || payload.delivery_date > dateISO(1)) {
      throw mockError('validation', 422, 'You can order for today or tomorrow only.')
    }
    if (!periodOpen(s, payload.delivery_date, payload.period)) {
      throw mockError('validation', 422, 'That delivery time is closed for today. Pick another time.')
    }
    if (payload.empties_to_return < 0 || payload.empties_to_return > (me.containers_held ?? 0)) {
      throw mockError('validation', 422, `You can return up to ${me.containers_held ?? 0} empty containers.`)
    }

    data.counters.order += 1
    const now = new Date().toISOString()
    const order = {
      id: `o_${data.counters.order}`,
      code: `AF-${data.counters.order}`,
      customer_id: me.id,
      quantity: payload.quantity,
      empties_to_return: payload.empties_to_return,
      unit_price: s.price_per_container,
      total: payload.quantity * s.price_per_container,
      address: {
        id: address.id,
        label: address.label,
        barangay: address.barangay,
        street: address.street,
        landmark: address.landmark,
        lat: address.lat,
        lng: address.lng,
      },
      delivery_date: payload.delivery_date,
      period: payload.period,
      notes: payload.notes.trim(),
      status: 'pending',
      attempts: 0,
      delivery_code: String(Math.floor(1000 + Math.random() * 9000)),
      trip: null,
      created_at: now,
      history: [{ status: 'pending', at: now }],
    }
    data.orders.push(order)
    saveDb()
    return clone(order)
  }
  const { data } = await http.post(`${API}/orders`, payload)
  return data
}

/** Customer cancel: allowed only while Pending or Confirmed. */
export async function cancelOrder(id, reason = '') {
  if (env.useMock) {
    await mockDelay(500)
    const me = currentUser()
    const order = db().orders.find((o) => o.id === id && o.customer_id === me.id)
    if (!order) throw mockError('not_found', 404, 'Order not found.')
    if (!CUSTOMER_CANCELLABLE.includes(order.status)) {
      throw mockError('conflict', 409, 'This order is already being prepared, so it can no longer be cancelled. Please call the station.')
    }
    const now = new Date().toISOString()
    order.status = 'cancelled'
    order.history.push({ status: 'cancelled', at: now, note: reason.trim() || 'Cancelled by customer' })
    saveDb()
    return clone(order)
  }
  const { data } = await http.post(`${API}/orders/${id}/cancel`, { reason })
  return data
}

// ---------- addresses ----------
/** @returns {Promise<Address[]>} */
export async function listAddresses() {
  if (env.useMock) {
    await mockDelay(200)
    const me = currentUser()
    const mine = db().addresses.filter((a) => a.user_id === me.id)
    return clone(mine.sort((a, b) => Number(b.is_default) - Number(a.is_default)))
  }
  const { data } = await http.get(`${API}/addresses`)
  return data
}

/**
 * Create (no id) or update (with id) an address.
 * @param {Address} address
 * @returns {Promise<Address>}
 */
export async function saveAddress(address) {
  if (env.useMock) {
    await mockDelay(400)
    const data = db()
    const me = currentUser()
    if (!insideArea(address, serviceArea(data.settings))) {
      throw mockError('validation', 422, 'This pin is outside our delivery area.')
    }
    const mine = data.addresses.filter((a) => a.user_id === me.id)
    const fields = {
      label: address.label.trim(),
      barangay: address.barangay.trim(),
      street: address.street.trim(),
      landmark: address.landmark.trim(),
      lat: address.lat,
      lng: address.lng,
    }
    let saved
    if (address.id) {
      saved = mine.find((a) => a.id === address.id)
      if (!saved) throw mockError('not_found', 404, 'Address not found.')
      Object.assign(saved, fields)
    } else {
      data.counters.address += 1
      saved = { id: `a_${data.counters.address}`, user_id: me.id, ...fields, is_default: mine.length === 0 }
      data.addresses.push(saved)
    }
    saveDb()
    return clone(saved)
  }
  const { data } = address.id
    ? await http.patch(`${API}/addresses/${address.id}`, address)
    : await http.post(`${API}/addresses`, address)
  return data
}

export async function setDefaultAddress(id) {
  if (env.useMock) {
    await mockDelay(250)
    const me = currentUser()
    db().addresses
      .filter((a) => a.user_id === me.id)
      .forEach((a) => {
        a.is_default = a.id === id
      })
    saveDb()
    return
  }
  await http.post(`${API}/addresses/${id}/default`)
}

export async function deleteAddress(id) {
  if (env.useMock) {
    await mockDelay(300)
    const data = db()
    const me = currentUser()
    const mine = data.addresses.filter((a) => a.user_id === me.id)
    if (mine.length <= 1) throw mockError('conflict', 409, 'Keep at least one address so we know where to deliver.')
    const target = mine.find((a) => a.id === id)
    if (!target) throw mockError('not_found', 404, 'Address not found.')
    data.addresses = data.addresses.filter((a) => a.id !== id)
    if (target.is_default) {
      const next = data.addresses.find((a) => a.user_id === me.id)
      if (next) next.is_default = true
    }
    saveDb()
    return
  }
  await http.delete(`${API}/addresses/${id}`)
}
