// The rider's on-phone database (IndexedDB through Dexie). Survives app restarts and no signal.
//
//   outbox  actions waiting for the server, in the order they happened (Feature B)
//           key: the idempotency key (a UUID made on the phone), so a resend is never applied twice
//   trips   downloaded trips: stops, details, coordinates and HASHED codes, per rider
//   cache   the last "today" answer from the server, to show the stop list with no signal
//
// Every row carries user_id, so two riders sharing a phone never see or send each other's data.
import Dexie from 'dexie'

export const db = new Dexie('aquaflow')

db.version(1).stores({
  outbox: '&key, user_id, seq',
  trips: '[user_id+id], user_id',
  cache: '[user_id+name]',
})

/** A UUID v4. crypto.randomUUID needs https; getRandomValues works on plain http too (LAN testing). */
export function uuid() {
  if (globalThis.crypto?.randomUUID) {
    try {
      return crypto.randomUUID()
    } catch {
      // not a secure context: fall through
    }
  }
  const b = crypto.getRandomValues(new Uint8Array(16))
  b[6] = (b[6] & 0x0f) | 0x40
  b[8] = (b[8] & 0x3f) | 0x80
  const h = Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('')
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`
}

/** One id per phone/browser, sent with every sync so the server knows which device it came from. */
export function deviceId() {
  try {
    let id = localStorage.getItem('aquaflow.device')
    if (!id) {
      id = `web-${uuid()}`
      localStorage.setItem('aquaflow.device', id)
    }
    return id
  } catch {
    return 'web-unknown'
  }
}
