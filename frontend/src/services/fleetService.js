// Owner: vehicles and the service area. Dispatchers can read both.
// Real mode: /api/v1/dispatch/ (backend/apps/dispatch/fleet_api.py).
// Reading vehicles for the planner is listVehicles() in tripService.js.
import { env } from '@/config/env'
import { mockError } from '@/mocks/db'
import { http } from './http'

const API = '/api/v1/dispatch'

function noMock() {
  throw mockError('server', null, 'This screen needs the AquaFlow server. Turn off demo mode (VITE_USE_MOCK).')
}

/** @typedef {{ id:number, name:string, plate:string, capacity:number, is_available:boolean, trip_id:number|null }} Vehicle */

/** @returns {Promise<Vehicle[]>} */
export async function fetchVehicles() {
  if (env.useMock) noMock()
  const { data } = await http.get(`${API}/vehicles`)
  return data
}

/** Create (no id) or update (id) a vehicle. @param {{id?:number,name:string,plate:string,capacity:number,is_available?:boolean}} v */
export async function saveVehicle(v) {
  if (env.useMock) noMock()
  const body = { name: v.name, plate: v.plate, capacity: Number(v.capacity), is_available: v.is_available ?? true }
  const { data } = v.id ? await http.patch(`${API}/vehicles/${v.id}`, body) : await http.post(`${API}/vehicles`, body)
  return data
}

/** Only works if the vehicle never had a trip. Otherwise switch it off. */
export async function deleteVehicle(id) {
  if (env.useMock) noMock()
  await http.delete(`${API}/vehicles/${id}`)
}

/** @returns {Promise<{name:string, lat:number, lng:number, radius_km:number, barangays:string[], is_configured:boolean}>} */
export async function getServiceArea() {
  if (env.useMock) noMock()
  const { data } = await http.get(`${API}/service-area`)
  return data
}

/** @param {{name:string, lat:number, lng:number, radius_km:number, barangays:string[]}} area */
export async function saveServiceArea(area) {
  if (env.useMock) noMock()
  const { data } = await http.put(`${API}/service-area`, area)
  return data
}
