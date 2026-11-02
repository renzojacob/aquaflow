// What the rider's phone uses while delivering.
// Real mode: /api/v1/rider/ (backend/apps/delivery/rider_api.py).
// Mock mode copies the same rules: only my orders, the code must match, nearest stop first.
import { env } from '@/config/env'
import { clone, currentUser, db, mockDelay, mockError, saveDb } from '@/mocks/db'
import { distanceKm } from '@/utils/geo'
import { http } from './http'

const API = '/api/v1/rider'

// Same estimate as the backend (delivery/tracking.py)
export const ROAD_FACTOR = 1.35
export const TRICYCLE_KMH = 18
export const MINUTES_PER_STOP = 4
export const driveMinutes = (straightM) => Math.max(1, Math.ceil((straightM * ROAD_FACTOR) / ((TRICYCLE_KMH * 1000) / 60)))

const FAIL_TEXT = {
  absent: 'No one was home',
  wrong_address: 'Could not find the address',
  refused: 'Customer refused the delivery',
  other: 'Could not deliver',
}
export const FAIL_REASONS = Object.entries(FAIL_TEXT).map(([value, label]) => ({ value, label }))

// ---------- mock helpers ----------
function requireRider() {
  const me = currentUser()
  if (me.role !== 'rider') throw mockError('forbidden', 403, 'Only riders can use this screen.')
  return me
}
const meters = (a, b) => distanceKm(a, b) * 1000
function mockLastLocation(riderId) {
  const loc = (db().rider_locations ?? {})[riderId]
  if (!loc) return null
  return { ...loc, fresh: Date.now() - new Date(loc.at).getTime() <= 10 * 60_000 }
}
function mockStation() {
  const s = db().settings.station
  return { lat: s.lat, lng: s.lng }
}
/** Nearest stop first, starting from the rider (or the station). Same idea as the backend. */
export function mockRoute(riderId) {
  const remaining = db().orders.filter((o) => o.status === 'out_for_delivery' && o.rider?.id === riderId)
  const loc = mockLastLocation(riderId)
  let here = loc?.fresh ? loc : mockStation()
  const out = []
  while (remaining.length) {
    remaining.sort((a, b) => meters(here, a.address) - meters(here, b.address))
    const next = remaining.shift()
    out.push({ order: next, leg: meters(here, next.address) })
    here = next.address
  }
  return out
}
function row(o, extra = {}) {
  const c = db().users.find((u) => u.id === o.customer_id)
  return {
    id: o.id,
    code: o.code,
    status: o.status,
    customer: { name: c?.full_name ?? 'Customer', phone: c?.phone ?? '' },
    quantity: o.quantity,
    expected_empties: o.empties_to_return,
    total: o.total,
    notes: o.notes,
    period: o.period,
    delivery_date: o.delivery_date,
    address: { ...o.address },
    ...extra,
  }
}

// ---------- API ----------

/** My stops (nearest first), what I finished today, and totals. */
export async function getToday() {
  if (env.useMock) {
    await mockDelay(250)
    const me = requireRider()
    let minutes = 0
    const stops = mockRoute(me.id).map(({ order, leg }, i) => {
      minutes += driveMinutes(leg) + (i ? MINUTES_PER_STOP : 0)
      return row(order, { sequence: i + 1, leg_m: Math.round(leg * ROAD_FACTOR), eta_minutes: minutes })
    })
    const today = new Date().toDateString()
    const done = (db().rider_attempts ?? [])
      .filter((a) => a.rider_id === me.id && new Date(a.at).toDateString() === today)
      .sort((a, b) => b.at.localeCompare(a.at))
      .map((a) => {
        const o = db().orders.find((x) => x.id === a.order_id)
        return row(o, { outcome: a.outcome, at: a.at, empties_collected: a.empties, code_ok: a.code_ok, failure: a.failure ?? '', geofence_flagged: a.flagged })
      })
    const delivered = done.filter((d) => d.outcome === 'delivered')
    return clone({
      stops,
      done,
      totals: {
        to_collect: stops.reduce((s, x) => s + x.total, 0),
        on_board: stops.reduce((s, x) => s + x.quantity, 0),
        collected: delivered.reduce((s, x) => s + x.total, 0),
        delivered: delivered.length,
        containers: delivered.reduce((s, x) => s + x.quantity, 0),
        empties: delivered.reduce((s, x) => s + x.empties_collected, 0),
        failed: done.length - delivered.length,
        minutes_left: minutes,
      },
      station: mockStation(),
      location: mockLastLocation(me.id),
      geofence_m: 150,
    })
  }
  const { data } = await http.get(`${API}/today`)
  return data
}

/**
 * Send one GPS point.
 * @param {{ lat: number, lng: number, accuracy_m?: number, heading?: number, speed_mps?: number, is_simulated?: boolean }} p
 */
export async function sendLocation(p) {
  if (env.useMock) {
    const me = requireRider()
    const data = db()
    data.rider_locations = data.rider_locations ?? {}
    data.rider_locations[me.id] = { lat: p.lat, lng: p.lng, accuracy_m: p.accuracy_m ?? null, heading: p.heading ?? null, is_simulated: !!p.is_simulated, at: new Date().toISOString() }
    saveDb()
    return
  }
  await http.post(`${API}/location`, { ...p, recorded_at: new Date().toISOString() })
}

/**
 * @param {string|number} id
 * @param {{ code?: string, no_code?: boolean, empties_collected: number, lat?: number, lng?: number, accuracy_m?: number }} payload
 */
export async function deliver(id, payload) {
  if (env.useMock) {
    await mockDelay(500)
    const me = requireRider()
    const o = db().orders.find((x) => x.id === id && x.rider?.id === me.id)
    if (!o) throw mockError('not_found', 404, 'Not one of your orders.')
    if (o.status !== 'out_for_delivery') throw mockError('validation', 400, 'This order is not on the road.')
    if (!payload.no_code && String(payload.code ?? '').trim() !== String(o.delivery_code)) {
      throw mockError('validation', 400, "That code doesn't match. Ask the customer to read it again from their app.")
    }
    const dist = payload.lat != null ? meters(payload, o.address) : null
    const flagged = dist == null || dist > 150
    o.status = 'delivered'
    o.history.push({ status: 'delivered', at: new Date().toISOString(), by: me.full_name, note: payload.no_code ? 'Delivered (customer had no code)' : 'Delivered, code checked' })
    const c = db().users.find((u) => u.id === o.customer_id)
    if (c) c.containers_held = (c.containers_held ?? 0) + o.quantity - payload.empties_collected
    db().inventory.empty_at_station += payload.empties_collected
    ;(db().rider_attempts ??= []).push({ rider_id: me.id, order_id: o.id, outcome: 'delivered', at: new Date().toISOString(), empties: payload.empties_collected, code_ok: !payload.no_code, flagged })
    saveDb()
    return { status: 'delivered', code_ok: !payload.no_code, distance_from_pin_m: dist == null ? null : Math.round(dist), geofence_flagged: flagged }
  }
  const { data } = await http.post(`${API}/orders/${id}/deliver`, payload)
  return data
}

/** @param {{ failure_reason: string, note?: string, lat?: number, lng?: number }} payload */
export async function fail(id, payload) {
  if (env.useMock) {
    await mockDelay(450)
    const me = requireRider()
    const o = db().orders.find((x) => x.id === id && x.rider?.id === me.id)
    if (!o) throw mockError('not_found', 404, 'Not one of your orders.')
    if (!FAIL_TEXT[payload.failure_reason]) throw mockError('validation', 400, "Pick why it couldn't be delivered.")
    const note = `${FAIL_TEXT[payload.failure_reason]}${payload.note ? `: ${payload.note}` : ''}`
    o.status = 'failed_delivery'
    o.history.push({ status: 'failed_delivery', at: new Date().toISOString(), by: me.full_name, note })
    db().inventory.filled_ready += o.quantity
    ;(db().rider_attempts ??= []).push({ rider_id: me.id, order_id: o.id, outcome: 'failed', at: new Date().toISOString(), empties: 0, failure: FAIL_TEXT[payload.failure_reason] })
    saveDb()
    return { status: 'failed' }
  }
  const { data } = await http.post(`${API}/orders/${id}/fail`, payload)
  return data
}
