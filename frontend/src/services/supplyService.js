// Supplies: caps, seals, filters and anything else the station uses up.
// Real mode: /api/v1/dispatch/supplies (backend/apps/inventory/supplies_api.py).
// Every call answers with the WHOLE payload (supplies + alerts + log), so screens just replace it.
import { env } from '@/config/env'
import { mockError } from '@/mocks/db'
import { http } from './http'

const API = '/api/v1/dispatch/supplies'

function noMock() {
  throw mockError('server', null, 'Supplies need the AquaFlow server. Turn off demo mode (VITE_USE_MOCK).')
}

/**
 * @typedef {Object} Supply
 * @property {number} id
 * @property {string} name
 * @property {'piece'|'litre'|'kilo'|'set'} unit
 * @property {number} quantity
 * @property {number} used_per_refill   how much goes per filled container (0 = not automatic)
 * @property {number} reorder_level
 * @property {number} lead_time_days
 * @property {boolean} is_active
 * @property {boolean} auto             true when used_per_refill > 0
 * @property {number|null} daily_usage
 * @property {number|null} days_left
 * @property {string|null} runout_date
 * @property {'ok'|'low'|'out'} status
 * @property {string} why               why it is low or out, in plain words
 *
 * @typedef {Object} SuppliesPayload
 * @property {Supply[]} supplies
 * @property {Supply[]} alerts
 * @property {{total:number, low:number, out:number}} counts
 * @property {number} refills_per_day
 * @property {number} window_days
 * @property {Array<{at:string, supply:string, reason:string, delta:number, unit:string, note:string, by:string}>} log
 */

/** @returns {Promise<SuppliesPayload>} */
export async function getSupplies() {
  if (env.useMock) noMock()
  const { data } = await http.get(API)
  return data
}

/**
 * Add (no id) or change (id) a supply. Owner only.
 * @param {{id?:number, name:string, unit:string, quantity?:number, used_per_refill:number, reorder_level:number, lead_time_days:number, note?:string, is_active?:boolean}} s
 * @returns {Promise<SuppliesPayload>}
 */
export async function saveSupply(s) {
  if (env.useMock) noMock()
  const body = {
    name: s.name,
    unit: s.unit,
    used_per_refill: Number(s.used_per_refill) || 0,
    reorder_level: Number(s.reorder_level) || 0,
    lead_time_days: Number(s.lead_time_days) || 0,
    note: s.note ?? '',
    is_active: s.is_active ?? true,
  }
  if (!s.id && s.quantity) body.quantity = Number(s.quantity)
  const { data } = s.id ? await http.patch(`${API}/${s.id}`, body) : await http.post(API, body)
  return data
}

/** Only works if the supply was never used. Otherwise switch it off. */
export async function deleteSupply(id) {
  if (env.useMock) noMock()
  const { data } = await http.delete(`${API}/${id}`)
  return data
}

/**
 * @param {number} id
 * @param {{type:'received'|'used'|'correction', quantity:number, note?:string}} body
 * @returns {Promise<SuppliesPayload>}
 */
export async function adjustSupply(id, body) {
  if (env.useMock) noMock()
  const { data } = await http.post(`${API}/${id}/adjust`, body)
  return data
}
