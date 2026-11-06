// Feature C, "Never Run Out": refill prediction for customers, demand and accuracy for staff.
// Real mode: backend/apps/predictions/views.py. Mock mode: same rules, from the mock orders.
import { env } from '@/config/env'
import { clone, currentUser, db, mockDelay, mockError } from '@/mocks/db'
import { dateISO } from '@/utils/format'
import {
  MIN_ORDERS,
  OVERDUE_GRACE_DAYS,
  REMIND_DAYS_BEFORE,
  addDays,
  backtest,
  daysBetween,
  estimate,
  histories,
  openKeys,
  OPEN_STATUSES,
} from '@/utils/refillPrediction'
import { statusFromApi, toOrder } from './adapters'
import { createOrder, getOrderSettings, periodOpen } from './customerService'
import { http } from './http'

const STAFF = '/api/v1/dispatch'
const PERIOD_START = { morning: '08:00', afternoon: '13:00' }

/**
 * @typedef {Object} RefillCard
 * @property {'ok' | 'not_enough_history'} state
 * @property {{ id: string|number, label: string, barangay: string }} address
 * @property {number} orders_counted
 * @property {number} orders_needed
 * @property {boolean} reminders_enabled
 * @property {{ id, status, delivery_date, period } | null} open_order
 * @property {string|number} [prediction_id]
 * @property {string} [predicted_runout_date]
 * @property {number} [days_left]
 * @property {string} [remind_on]
 * @property {number} [days_per_container]
 * @property {string} [last_delivery_date]
 * @property {number} [last_quantity]
 * @property {string|null} [reminder_sent_at]
 * @property {{ quantity: number, delivery_date: string, period: string, starts_at: string, total: number }} [reorder]
 */

/** My households, soonest run-out first. @returns {Promise<RefillCard[]>} */
export async function getRefillCards() {
  if (env.useMock) {
    await mockDelay(200)
    return mockCards()
  }
  const { data } = await http.get('/api/customer/refill/')
  return data.households.map((c) => ({
    ...c,
    open_order: c.open_order ? { ...c.open_order, status: statusFromApi(c.open_order.status) } : null,
  }))
}

/**
 * One-tap reorder of the usual quantity. Without a slot the server picks the earliest open one.
 * @param {RefillCard} card
 */
export async function reorderRefill(card, slot = {}) {
  if (env.useMock) {
    const me = currentUser()
    const key = String(card.prediction_id)
    if (openKeys(db().orders).has(key)) throw mockError('conflict', 409, 'You already have an order on the way to this address.')
    const qty = card.reorder.quantity
    return createOrder({
      items: [{ product_id: 'p_refill', quantity: qty }],
      address_id: card.address.id,
      delivery_date: slot.delivery_date ?? card.reorder.delivery_date,
      period: slot.period ?? card.reorder.period,
      empties_to_return: Math.min(qty, me.containers_held ?? 0),
      notes: '',
    })
  }
  const { data } = await http.post('/api/customer/refill/reorder/', { prediction: card.prediction_id, ...slot })
  return toOrder(data)
}

/** Staff: confirmed + predicted (tentative) containers per day, and what to prepare. */
export async function getDemand(days = 7) {
  if (env.useMock) {
    await mockDelay(250)
    requireStaff()
    return mockDemand(days)
  }
  const { data } = await http.get(`${STAFF}/demand`, { params: { days } })
  return data
}

/** Staff: backtest of the prediction. days = 0 means all time. */
export async function getRefillAccuracy(days = 90) {
  if (env.useMock) {
    await mockDelay(300)
    requireStaff()
    const today = dateISO(0)
    const since = days ? addDays(today, -(days - 1)) : null
    return clone({ ...backtest(db().orders, { since, until: today, names: mockNames() }), since, until: today, reminders: { reminded: 0, reordered: 0, reorder_rate: null } })
  }
  const { data } = await http.get(`${STAFF}/refill-accuracy`, { params: { days } })
  return data
}

// ---------------------------------------------------------------------------
// mock mode
// ---------------------------------------------------------------------------
function requireStaff() {
  if (!['dispatcher', 'owner'].includes(currentUser().role)) throw mockError('forbidden', 403, 'Staff only.')
}

function mockNames() {
  const data = db()
  const names = {}
  for (const a of data.addresses) {
    const u = data.users.find((x) => x.id === a.user_id)
    names[`${a.user_id}:${a.id}`] = { customer: u?.full_name ?? 'Unknown', address: a.label }
  }
  return names
}

async function mockCards() {
  const data = db()
  const me = currentUser()
  const today = dateISO(0)
  const settings = await getOrderSettings()
  const slot = ['morning', 'afternoon'].map((p) => [today, p]).find(([d, p]) => periodOpen(settings, d, p)) ?? [dateISO(1), 'morning']
  const h = histories(data.orders)
  const price = settings.products?.find((p) => p.id === 'p_refill')?.price ?? settings.price_per_container
  const cards = []
  for (const a of data.addresses.filter((x) => x.user_id === me.id).sort((x, y) => Number(y.is_default) - Number(x.is_default))) {
    const key = `${me.id}:${a.id}`
    const hist = h[key] ?? []
    if (!hist.length) continue
    const open = data.orders.find((o) => `${o.customer_id}:${o.address.id}` === key && OPEN_STATUSES.includes(o.status))
    const card = {
      address: { id: a.id, label: a.label, barangay: a.barangay },
      orders_counted: hist.length,
      orders_needed: MIN_ORDERS,
      reminders_enabled: me.reminders_enabled ?? true,
      open_order: open ? { id: open.id, status: open.status, delivery_date: open.delivery_date, period: open.period } : null,
      state: 'not_enough_history',
    }
    const est = estimate(hist)
    if (est) {
      const qty = me.usual_quantity || est.last_quantity
      Object.assign(card, {
        state: 'ok',
        prediction_id: key,
        predicted_runout_date: est.runout,
        days_left: daysBetween(today, est.runout),
        remind_on: addDays(est.runout, -REMIND_DAYS_BEFORE),
        days_per_container: est.days_per_container,
        last_delivery_date: est.last_date,
        last_quantity: est.last_quantity,
        inputs: { intervals: est.intervals, weights: est.weights },
        reminder_sent_at: null,
        reorder: { quantity: qty, delivery_date: slot[0], period: slot[1], starts_at: PERIOD_START[slot[1]], total: price * qty },
      })
    }
    cards.push(card)
  }
  return clone(cards.sort((x, y) => (x.state !== 'ok') - (y.state !== 'ok') || (x.days_left ?? 0) - (y.days_left ?? 0)))
}

function mockDemand(days) {
  const data = db()
  const today = dateISO(0)
  const end = addDays(today, days - 1)
  const rows = {}
  for (let i = 0; i < days; i++) rows[addDays(today, i)] = { confirmed: 0, confirmed_orders: 0, pending: 0, predicted: 0, households: [] }
  const containersOf = (o) => o.containers ?? o.quantity
  for (const o of data.orders) {
    const r = rows[o.delivery_date]
    if (!r) continue
    if (o.status === 'pending') r.pending += containersOf(o)
    else if (['confirmed', 'preparing', 'ready_for_pickup'].includes(o.status)) {
      r.confirmed += containersOf(o)
      r.confirmed_orders += 1
    }
  }
  const busy = openKeys(data.orders)
  const names = mockNames()
  for (const [key, h] of Object.entries(histories(data.orders))) {
    const est = estimate(h)
    if (!est || busy.has(key) || est.runout > end || est.runout < addDays(today, -OVERDUE_GRACE_DAYS)) continue
    const day = est.runout < today ? today : est.runout
    const a = data.addresses.find((x) => `${x.user_id}:${x.id}` === key)
    rows[day].predicted += est.last_quantity
    rows[day].households.push({ prediction_id: key, customer: names[key]?.customer ?? key, address: a?.label ?? '', barangay: a?.barangay ?? '', containers: est.last_quantity, runout: est.runout, overdue_days: Math.max(0, daysBetween(est.runout, today)) })
  }
  const ready = data.inventory.filled_ready
  let running = 0
  const out = Object.entries(rows).sort(([a], [b]) => a.localeCompare(b)).map(([date, r]) => {
    const expected = r.confirmed + r.predicted
    running += expected
    return { date, ...r, expected, cumulative_expected: running, prepare: Math.max(0, running - ready) }
  })
  const sum = (k) => out.reduce((s, x) => s + x[k], 0)
  return clone({ ready_stock: ready, days: out, totals: { confirmed: sum('confirmed'), pending: sum('pending'), predicted: sum('predicted'), expected: sum('expected') }, prepare: out.at(-1)?.prepare ?? 0 })
}
