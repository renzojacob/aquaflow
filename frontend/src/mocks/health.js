/** Small fake delay so mock mode still shows loading states. */
export const mockDelay = (ms = 450) => new Promise((resolve) => setTimeout(resolve, ms))

/** @returns {import('@/types/api').HealthResponse} */
export function mockHealth() {
  return {
    status: 'ok',
    app: 'AquaFlow API (mock)',
    version: '0.1.0',
    environment: 'mock',
    database: 'up',
    database_error: null,
    server_time: new Date().toISOString(),
  }
}