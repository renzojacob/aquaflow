// Pattern every service follows from now on:
//   mock mode -> return realistic fake data
//   otherwise -> call the real API through `http`
// Screens only call the service, so they don't care which one answered.
import { env } from '@/config/env'
import { mockDelay, mockHealth } from '@/mocks/health'
import { http } from './http'

/**
 * @typedef {Object} HealthResult
 * @property {import('@/types/api').HealthResponse} data
 * @property {number} latencyMs
 * @property {'mock' | 'api'} source
 */

/** @returns {Promise<HealthResult>} */
export async function checkHealth() {
  const started = performance.now()

  if (env.useMock) {
    await mockDelay()
    return { data: mockHealth(), latencyMs: Math.round(performance.now() - started), source: 'mock' }
  }

  const { data } = await http.get('/health')
  return { data, latencyMs: Math.round(performance.now() - started), source: 'api' }
}