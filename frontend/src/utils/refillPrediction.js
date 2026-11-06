// Feature C, "Never Run Out": the same calculation as backend/apps/predictions/services.py.
// Real mode never uses this (the server computes everything); mock mode does, so the
// screens behave the same without a backend.
//
//   days per container = days between two deliveries / containers in the earlier one
//   weighted average of the last three values, weights 3, 2, 1 (most recent counts most)
//   run-out = last delivery date + last quantity x days per container
//   needs at least 3 delivered orders
import { refillsOf } from '@/constants/cart'

export const WEIGHTS = [3, 2, 1]
export const MIN_ORDERS = 3
export const REMIND_DAYS_BEFORE = 2
export const OVERDUE_GRACE_DAYS = 7
export const OPEN_STATUSES = ['pending', 'confirmed', 'preparing', 'ready_for_pickup', 'out_for_delivery']

const DAY = 86_400_000
const toDay = (iso) => {
  const [y, m, d] = iso.split('-').map(Number)
  return Date.UTC(y, m - 1, d)
}
const fromDay = (t) => new Date(t).toISOString().slice(0, 10)
export const addDays = (iso, n) => fromDay(toDay(iso) + n * DAY)
export const daysBetween = (a, b) => Math.round((toDay(b) - toDay(a)) / DAY)
const halfUp = (x) => Math.floor(x + 0.5 + 1e-9)

/** [[date, containers]] in any order -> one per date, oldest first, refills only. */
export function mergeSameDay(deliveries) {
  const per = {}
  for (const [d, n] of deliveries) if (n > 0) per[d] = (per[d] ?? 0) + n
  return Object.entries(per).sort(([a], [b]) => a.localeCompare(b))
}

/** @returns {{ days_per_container: number, runout: string, last_date: string, last_quantity: number, intervals: object[], weights: number[] } | null} */
export function estimate(deliveries) {
  if (deliveries.length < MIN_ORDERS) return null
  const intervals = []
  for (let i = 1; i < deliveries.length; i++) {
    const [d0, n0] = deliveries[i - 1]
    const days = daysBetween(d0, deliveries[i][0])
    intervals.push({ from: d0, to: deliveries[i][0], days, containers: n0, days_per_container: Math.round((days / n0) * 100) / 100 })
  }
  const recent = intervals.slice(-WEIGHTS.length).map((i) => i.days / i.containers).reverse()
  const weights = WEIGHTS.slice(0, recent.length)
  const dpc = Math.round((recent.reduce((s, r, i) => s + r * weights[i], 0) / weights.reduce((a, b) => a + b, 0)) * 100) / 100
  const [lastDate, lastQty] = deliveries.at(-1)
  return {
    days_per_container: dpc,
    runout: addDays(lastDate, halfUp(lastQty * dpc)),
    last_date: lastDate,
    last_quantity: lastQty,
    intervals: intervals.slice(-WEIGHTS.length),
    weights,
  }
}

/** Mock orders -> { "customerId:addressId": [[date, containers]] } of delivered refills. */
export function histories(orders) {
  const raw = {}
  for (const o of orders) {
    if (o.status !== 'delivered') continue
    ;(raw[`${o.customer_id}:${o.address.id}`] ??= []).push([o.delivery_date, refillsOf(o)])
  }
  return Object.fromEntries(Object.entries(raw).map(([k, v]) => [k, mergeSameDay(v)]))
}

export const openKeys = (orders) => new Set(orders.filter((o) => OPEN_STATUSES.includes(o.status)).map((o) => `${o.customer_id}:${o.address.id}`))

/** Backtest: predict each next order from the earlier ones only, compare with the real date. */
export function backtest(orders, { since = null, until = null, names = {} } = {}) {
  const points = []
  const perHousehold = []
  for (const [key, h] of Object.entries(histories(orders))) {
    const errs = []
    for (let k = MIN_ORDERS; k < h.length; k++) {
      const actual = h[k][0]
      if ((since && actual < since) || (until && actual > until)) continue
      errs.push(daysBetween(estimate(h.slice(0, k)).runout, actual))
    }
    points.push(...errs)
    if (errs.length) perHousehold.push({ key, ...(names[key] ?? { customer: key, address: '' }), predictions: errs.length, ...score(errs) })
  }
  const buckets = {}
  for (const e of points) {
    const b = Math.max(-7, Math.min(7, e))
    buckets[b] = (buckets[b] ?? 0) + 1
  }
  return {
    predictions: points.length,
    households: perHousehold.length,
    ...score(points),
    histogram: Array.from({ length: 15 }, (_, i) => ({ error_days: i - 7, count: buckets[i - 7] ?? 0 })),
    per_household: perHousehold.sort((a, b) => b.mean_abs_error - a.mean_abs_error),
    min_orders: MIN_ORDERS,
  }
}

function score(errors) {
  if (!errors.length) return { mean_abs_error: null, mean_error: null, within_1_day: null }
  const n = errors.length
  return {
    mean_abs_error: Math.round((errors.reduce((s, e) => s + Math.abs(e), 0) / n) * 100) / 100,
    mean_error: Math.round((errors.reduce((s, e) => s + e, 0) / n) * 100) / 100,
    within_1_day: Math.round((errors.filter((e) => Math.abs(e) <= 1).length / n) * 10000) / 10000,
  }
}
