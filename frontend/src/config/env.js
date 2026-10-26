// One place to read environment settings, already parsed.
// Everything else imports `env` instead of touching import.meta.env directly.
export const env = Object.freeze({
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, ''),
  useMock: import.meta.env.VITE_USE_MOCK === 'true',
  mode: import.meta.env.MODE,
})