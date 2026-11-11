// One place to read environment settings, already parsed.
// Everything else imports `env` instead of touching import.meta.env directly.

// The server address baked in when the app was built (VITE_API_BASE_URL).
const strip = (url) => url.trim().replace(/\/+$/, '')
export const builtInApiBase = strip(import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000')

// An address saved on THIS device wins over the built-in one, so the same APK works on any Wi-Fi
// without a rebuild. It is set from the login screen ("Server address"). Empty means "use the built-in one".
export const API_BASE_KEY = 'af_api_base'

/** The address saved on this device, or '' if none (or if the browser blocks storage). */
export function savedApiBase() {
  try {
    const v = (localStorage.getItem(API_BASE_KEY) || '').trim()
    return /^https?:\/\//i.test(v) ? strip(v) : ''
  } catch {
    return ''
  }
}

/**
 * Save the address, or clear it when `url` is empty. Returns false (and saves nothing) when the text
 * is not an http:// or https:// address. The app must be reloaded for the change to take effect.
 */
export function saveApiBase(url) {
  const v = (url || '').trim()
  try {
    if (!v) {
      localStorage.removeItem(API_BASE_KEY)
      return true
    }
    if (!/^https?:\/\/\S+$/i.test(v)) return false
    localStorage.setItem(API_BASE_KEY, strip(v))
    return true
  } catch {
    return false
  }
}

export const env = Object.freeze({
  apiBaseUrl: savedApiBase() || builtInApiBase,
  useMock: import.meta.env.VITE_USE_MOCK === 'true',
  mode: import.meta.env.MODE,
})
