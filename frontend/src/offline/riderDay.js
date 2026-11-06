// The rider's day, built so it works with no signal:
//   1. the server's "today" (or, offline, the last copy saved on the phone)
//   2. trips started on the phone but not synced yet add their downloaded stops
//   3. stops already delivered/failed on the phone (still in the outbox) move to "done"
// Also keeps downloaded trips in IndexedDB (replaces the earlier localStorage copy).
import { useAuthStore } from '@/stores/auth'
import { getToday } from '@/services/riderService'
import { db } from './db'
import { listOutbox } from './outbox'

const uid = () => useAuthStore().user?.id ?? null
const MINUTES_PER_STOP = 6

// ---------- downloaded trips ----------
export async function saveTrip(copy) {
  const user_id = uid()
  if (user_id == null) return
  await db.trips.put({ ...JSON.parse(JSON.stringify(copy)), user_id, saved_at: new Date().toISOString() })
}

export async function getTrip(id) {
  const user_id = uid()
  return user_id == null ? null : (await db.trips.get([user_id, id])) ?? null
}

export async function savedTrips() {
  const user_id = uid()
  return user_id == null ? [] : db.trips.where('user_id').equals(user_id).toArray()
}

/** Forget trips that are finished or no longer mine (keepIds = trips the server still lists). */
export async function forgetTripsExcept(keepIds) {
  const keep = new Set(keepIds)
  for (const t of await savedTrips()) {
    if (!keep.has(t.id)) await db.trips.delete([t.user_id, t.id])
  }
}

/** The downloaded stop for an order (it has code_salt + code_hash), or null. */
export async function savedStop(orderId) {
  for (const t of await savedTrips()) {
    const s = t.stops?.find((x) => x.id === orderId)
    if (s) return s
  }
  return null
}

// ---------- the day ----------
async function cachedToday() {
  const user_id = uid()
  return user_id == null ? null : (await db.cache.get([user_id, 'today'])) ?? null
}

/**
 * @returns {Promise<{ data: object, offline: boolean, savedAt: string|null }>}
 *   offline: true when the server couldn't be reached and the phone's copy is shown
 * Throws only when there's no signal AND nothing saved on the phone yet.
 */
export async function loadDay() {
  let base = null
  let offline = false
  let savedAt = null
  try {
    base = await getToday()
    const user_id = uid()
    if (user_id != null) {
      await db.cache.put({ user_id, name: 'today', data: JSON.parse(JSON.stringify(base)), saved_at: new Date().toISOString() })
    }
  } catch (e) {
    if (e?.status) throw e                 // the server answered with an error: show it
    const copy = await cachedToday()
    const trips = await savedTrips()
    if (!copy && !trips.length) throw e
    base = copy?.data ?? { stops: [], done: [], totals: {}, station: trips[0]?.station ?? null, location: null }
    savedAt = copy?.saved_at ?? null
    offline = true
  }
  return { data: await overlay(base), offline, savedAt }
}

/** Apply what's waiting in the outbox on top of the server's (or cached) day. */
export async function overlay(base) {
  const outbox = await listOutbox()
  const trips = await savedTrips()
  const handled = new Map() // order id -> deliver/fail row
  const startedHere = new Set()
  for (const r of outbox) {
    if ((r.action_type === 'deliver' || r.action_type === 'fail') && r.order_id) handled.set(r.order_id, r)
    if (r.action_type === 'start_trip' && r.status !== 'rejected') startedHere.add(r.trip_id)
  }
  const doneIds = new Set((base.done ?? []).map((d) => d.id))

  let stops = (base.stops ?? []).filter((s) => !handled.has(s.id))
  const known = new Set((base.stops ?? []).map((s) => s.id))
  let routeLine = base.route_line ?? null
  for (const t of trips) {
    if (!startedHere.has(t.id)) continue
    const extra = (t.stops ?? [])
      .filter((s) => (s.stop_status ?? 'pending') === 'pending')
      .filter((s) => !known.has(s.id) && !handled.has(s.id) && !doneIds.has(s.id))
      .sort((a, b) => a.sequence - b.sequence)
    stops = stops.concat(extra)
    routeLine = routeLine ?? t.route_line ?? null
  }

  const local = [...handled.values()].map((r) => ({
    ...(r.meta?.stop ?? { id: r.order_id, code: `AF-${r.order_id}`, customer: { name: r.meta?.customer ?? '' }, total: 0, containers: 0 }),
    outcome: r.action_type === 'deliver' ? 'delivered' : 'failed',
    at: r.device_time,
    empties_collected: r.payload?.empties_collected ?? 0,
    code_ok: null,
    failure: r.meta?.failure_text ?? '',
    geofence_flagged: false,
    waiting: r.status === 'rejected' ? 'rejected' : 'pending', // not on the server yet
    error: r.error,
  }))
  const done = [...local.sort((a, b) => b.at.localeCompare(a.at)), ...(base.done ?? []).filter((d) => !handled.has(d.id))]
  const delivered = done.filter((d) => d.outcome === 'delivered')

  const changed = local.length > 0 || stops.length !== (base.stops ?? []).length
  return {
    ...base,
    stops,
    done,
    route_line: routeLine,
    totals: {
      ...(base.totals ?? {}),
      to_collect: stops.reduce((n, s) => n + (s.total ?? 0), 0),
      on_board: stops.reduce((n, s) => n + (s.quantity ?? s.containers ?? 0), 0),
      collected: delivered.reduce((n, d) => n + (d.total ?? 0), 0),
      delivered: delivered.length,
      containers: delivered.reduce((n, d) => n + (d.containers ?? 0), 0),
      empties: delivered.reduce((n, d) => n + (d.empties_collected ?? 0), 0),
      failed: done.length - delivered.length,
      minutes_left: changed ? stops.length * (MINUTES_PER_STOP + 4) : base.totals?.minutes_left ?? 0,
    },
  }
}
