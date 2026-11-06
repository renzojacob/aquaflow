// Dispatcher / owner: the conflict queue from riders' offline syncs (Feature B).
// Real mode: /api/v1/dispatch/conflicts (backend/apps/sync/views.py).
import { env } from '@/config/env'
import { mockError } from '@/mocks/db'
import { http } from './http'

const API = '/api/v1/dispatch/conflicts'

function noMock() {
  throw mockError('server', null, 'Conflicts need the AquaFlow server. Turn off demo mode (VITE_USE_MOCK).')
}

/**
 * @typedef {Object} Conflict
 * @property {number} id
 * @property {'delivered_after_cancel'|'code_mismatch'|'reassigned'|'out_of_order'} kind
 * @property {string} title   plain-language heading
 * @property {string} help    what happened and what to check
 * @property {'open'|'resolved'} status
 * @property {string} created_at
 * @property {{id:number, code:string, status:string, customer_name:string, address:string, containers:number, total:string, cancel_reason:string}|null} order
 * @property {{type:string, label:string, rider:{id:number, name:string}, device_time:string, server_time:string, payload:object}} action
 * @property {string|null} resolved_by
 * @property {string|null} resolved_at
 * @property {string} resolution_note
 */

/** @returns {Promise<{open_count:number, conflicts: Conflict[]}>} */
export async function listConflicts(status = 'open') {
  if (env.useMock) noMock()
  const { data } = await http.get(API, { params: { status } })
  return data
}

/** Mark one as handled. A note is required. @returns {Promise<Conflict>} */
export async function resolveConflict(id, note) {
  if (env.useMock) noMock()
  const { data } = await http.post(`${API}/${id}/resolve`, { note })
  return data
}
