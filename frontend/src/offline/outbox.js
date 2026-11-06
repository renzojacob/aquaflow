// Feature B outbox: every rider action (start trip, delivered, couldn't deliver, empties) is saved
// on the phone FIRST, then sent to POST /api/v1/rider/sync. Works the same with or without signal.
//
//   enqueue()    save an action (UUID key + the phone's time). Never needs the network.
//   syncNow()    send everything waiting, oldest first. Safe to call any time, from anywhere.
//   startAutoSync()  sync on app start, when the network comes back (@capacitor/network),
//                    and every 30 s while something is waiting.
//
// What the server answers decides what happens to each action:
//   applied / duplicate / conflict  -> done, removed from the outbox
//   rejected                        -> kept with the server's error; sent again on the next sync
//                                      (e.g. "deliver" that arrived before "start trip"), or the
//                                      rider can discard it on the Sync screen.
import { reactive } from 'vue'
import { Network } from '@capacitor/network'

import { env } from '@/config/env'
import { http } from '@/services/http'
import { useAuthStore } from '@/stores/auth'
import { db, deviceId, uuid } from './db'

const SYNC_URL = '/api/v1/rider/sync'
const BATCH = 100
const RETRY_MS = 30_000

/** Shared, reactive sync status for the banner, the Sync screen and the stop list. */
export const syncState = reactive({
  online: typeof navigator === 'undefined' ? true : navigator.onLine !== false,
  syncing: false,
  pending: 0,        // waiting, never answered yet
  rejected: 0,       // answered "rejected": needs the rider's attention
  lastSyncAt: null,  // ISO time of the last sync that reached the server
  justSynced: 0,     // how many actions the last sync cleared (banner shows it for a moment)
  progress: { done: 0, total: 0 },
  version: 0,        // bumps whenever the outbox changes, so screens can re-read it
})

let pinia = null
const me = () => {
  if (env.useMock) return null
  const auth = useAuthStore(pinia ?? undefined)
  return auth.role === 'rider' ? auth.user?.id ?? null : null
}

async function rows(userId = me()) {
  if (userId == null) return []
  return db.outbox.where('user_id').equals(userId).sortBy('seq')
}

async function recount() {
  const all = await rows()
  syncState.pending = all.filter((r) => r.status !== 'rejected').length
  syncState.rejected = all.filter((r) => r.status === 'rejected').length
  syncState.version++
}

/** IndexedDB can only store plain data: drop Vue proxies, functions and undefined. */
const plain = (v) => JSON.parse(JSON.stringify(v ?? {}))

let seqCounter = 0
/**
 * Save one action on the phone.
 * @param {{ action_type: 'start_trip'|'deliver'|'fail'|'empties', trip_id?: number, order_id?: number,
 *           payload?: object, meta?: object }} a  meta is for display only (label, order code, customer)
 * @returns {Promise<object>} the saved row (has .key)
 */
export async function enqueue(a) {
  const userId = me()
  if (userId == null) throw new Error('Log in as a rider first.')
  const row = {
    key: uuid(),
    user_id: userId,
    seq: Date.now() * 1000 + (seqCounter++ % 1000), // keeps the order even within one millisecond
    action_type: a.action_type,
    trip_id: a.trip_id ?? null,
    order_id: a.order_id ?? null,
    payload: plain(a.payload),
    device_time: new Date().toISOString(),
    status: 'pending',
    error: '',
    attempts: 0,
    meta: plain(a.meta),
  }
  await db.outbox.add(row)
  await recount()
  return row
}

/** Everything in my outbox, oldest first. */
export const listOutbox = () => rows()

/** Remove an action the rider gave up on (only offered for rejected ones). */
export async function discard(key) {
  await db.outbox.delete(key)
  await recount()
}

const toAction = (r) => ({
  idempotency_key: r.key,
  action_type: r.action_type,
  trip_id: r.trip_id,
  order_id: r.order_id,
  payload: r.payload,
  device_time: r.device_time,
})

let running = null
/**
 * Send everything waiting. Returns { results: Map(key -> server result), reached: boolean }.
 * Calls made while a sync is running wait for it and get its result.
 */
export function syncNow() {
  if (running) return running
  running = (async () => {
    const results = new Map()
    const userId = me()
    const todo = await rows(userId)
    if (!todo.length) return { results, reached: true }

    syncState.syncing = true
    syncState.progress = { done: 0, total: todo.length }
    let cleared = 0
    let reached = false
    try {
      for (let i = 0; i < todo.length; i += BATCH) {
        const chunk = todo.slice(i, i + BATCH)
        const { data } = await http.post(SYNC_URL, { device_id: deviceId(), actions: chunk.map(toAction) })
        reached = true
        for (const r of data.results) {
          results.set(r.idempotency_key, r)
          const row = chunk.find((x) => x.key === r.idempotency_key)
          if (!row) continue
          if (r.result === 'rejected') {
            await db.outbox.update(row.key, { status: 'rejected', error: r.error || 'Not accepted.', attempts: row.attempts + 1 })
          } else {
            await db.outbox.delete(row.key)
            cleared++
          }
        }
        syncState.progress.done = Math.min(todo.length, i + chunk.length)
      }
      syncState.online = true
      syncState.lastSyncAt = new Date().toISOString()
      if (cleared) {
        syncState.justSynced = cleared
        setTimeout(() => (syncState.justSynced = 0), 4000)
      }
    } catch (e) {
      // No answer at all = no signal (or server down): keep everything for later
      if (!e?.status) syncState.online = false
    } finally {
      syncState.syncing = false
      await recount()
    }
    return { results, reached }
  })().finally(() => (running = null))
  return running
}

let started = false
/** Call once at app start (main.js). Harmless for customers, staff and demo mode. */
export async function startAutoSync(appPinia) {
  if (started) return
  started = true
  pinia = appPinia
  try {
    syncState.online = (await Network.getStatus()).connected
    Network.addListener('networkStatusChange', (s) => {
      syncState.online = s.connected
      if (s.connected) syncNow()
    })
  } catch {
    // plugin unavailable: rely on sync results and the timer
  }
  await recount().catch(() => {})
  syncNow()
  // Retry on a timer only while something has never been answered. Rejected actions are re-sent
  // with every sync anyway, but don't keep the phone calling the server on their own.
  setInterval(() => {
    if (syncState.pending > 0) syncNow()
  }, RETRY_MS)
}

/** Re-read counts (e.g. after logging in as another rider). */
export const refreshOutbox = () => recount()
