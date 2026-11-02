// Dispatcher (and owner) trips: build one from confirmed orders, approve it, name the rider.
// Real mode: /api/v1/dispatch/ (backend/apps/dispatch/trips_api.py).
// The server checks capacity, statuses and "one trip per rider/vehicle per period" on every call,
// so screens just show the error message it returns.
import { env } from '@/config/env'
import { mockError } from '@/mocks/db'
import { http } from './http'

const API = '/api/v1/dispatch'

/** Trips need the real backend (capacity check, change log). Demo mode says so clearly. */
function noMock() {
  throw mockError('server', null, 'Trips need the AquaFlow server. Turn off demo mode (VITE_USE_MOCK).')
}

/**
 * @typedef {Object} TripStop
 * @property {number} sequence
 * @property {'pending'|'done'|'failed'} status
 * @property {number} order_id
 * @property {string} code            "AF-12" (order number, not the customer's code)
 * @property {string} order_status
 * @property {string} customer_name
 * @property {string} barangay
 * @property {string} address
 * @property {number} lat
 * @property {number} lng
 * @property {number} containers
 * @property {number} expected_empties
 * @property {number|null} expected_load_after
 * @property {string|null} eta         ISO time
 *
 * @typedef {Object} Trip
 * @property {number} id
 * @property {string} date
 * @property {'morning'|'afternoon'} period
 * @property {'draft'|'approved'|'downloaded'|'out'|'completed'} status
 * @property {number} version
 * @property {{id:number, name:string, plate:string, capacity:number}} vehicle
 * @property {{id:number, name:string, phone:string}|null} rider
 * @property {{departure:number, peak:number, capacity:number}} load   for the load bar, e.g. 18/20
 * @property {number} total_distance_m
 * @property {number} total_duration_s
 * @property {boolean} distance_is_estimate
 * @property {boolean} phone_out_of_date  rider must download again
 * @property {TripStop[]} stops
 * @property {Array<{at:string, action:string, order_id:number|null, by:string|null}>} [change_log]
 */

/** Vehicles, and which one already has a trip in that slot (trip_id). */
export async function listVehicles(date, period) {
  if (env.useMock) noMock()
  const { data } = await http.get(`${API}/vehicles`, { params: { date, period } })
  return data
}

/**
 * That day's trips plus confirmed orders that aren't on any trip yet.
 * @returns {Promise<{trips: Trip[], unplanned: Array<{order_id:number, code:string, status:string, period:string, customer_name:string, barangay:string, lat:number, lng:number, containers:number, expected_empties:number}>}>}
 */
export async function listTrips(date, period) {
  if (env.useMock) noMock()
  const { data } = await http.get(`${API}/trips`, { params: { date, period } })
  return data
}

/** @returns {Promise<Trip>} with change_log */
export async function getTrip(id) {
  if (env.useMock) noMock()
  const { data } = await http.get(`${API}/trips/${id}`)
  return data
}

/**
 * New draft trip. Stops keep the order of orderIds.
 * @param {{ date: string, period: 'morning'|'afternoon', vehicleId: number, orderIds: number[], riderId?: number }} p
 * @returns {Promise<Trip>}
 */
export async function createTrip({ date, period, vehicleId, orderIds, riderId }) {
  if (env.useMock) noMock()
  const body = { date, period, vehicle_id: vehicleId, order_ids: orderIds }
  if (riderId) body.rider_id = riderId
  const { data } = await http.post(`${API}/trips`, body)
  return data
}

/** Replace a draft trip's stops (add, remove or reorder). @returns {Promise<Trip>} */
export async function setTripStops(id, orderIds) {
  if (env.useMock) noMock()
  const { data } = await http.put(`${API}/trips/${id}/stops`, { order_ids: orderIds })
  return data
}

/** Draft -> approved: the rider can now download it. @returns {Promise<Trip>} */
export async function approveTrip(id) {
  if (env.useMock) noMock()
  const { data } = await http.post(`${API}/trips/${id}/approve`)
  return data
}

/**
 * Name or change the rider and/or vehicle (until the trip leaves).
 * @param {{ riderId?: number, vehicleId?: number }} p
 * @returns {Promise<Trip>}
 */
export async function assignTrip(id, { riderId, vehicleId } = {}) {
  if (env.useMock) noMock()
  const body = {}
  if (riderId) body.rider_id = riderId
  if (vehicleId) body.vehicle_id = vehicleId
  const { data } = await http.post(`${API}/trips/${id}/assign`, body)
  return data
}

/** Draft or approved only. The orders go back to "unplanned". */
export async function deleteTrip(id) {
  if (env.useMock) noMock()
  await http.delete(`${API}/trips/${id}`)
}

/**
 * The one button: build draft trips for the day and period. Old drafts are replaced;
 * approved, downloaded and running trips are never touched.
 * @returns {Promise<{trips: Trip[], not_fitted: Array<{order_id:number, code:string, customer_name:string, barangay:string, containers:number, reason:string}>}>}
 */
export async function planSlot(date, period) {
  if (env.useMock) noMock()
  const { data } = await http.post(`${API}/plan`, { date, period })
  return data
}
