// Where the login token (JWT) is kept between app launches.
// localStorage is fine for this project. Trade-off to tell the panel: if an attacker
// could run JavaScript in our app (XSS), they could read it. We reduce that risk by
// never rendering user input as raw HTML (no v-html).
const KEY = 'aquaflow.accessToken'

export const tokenStorage = {
  /** @returns {string | null} */
  get() {
    try {
      return localStorage.getItem(KEY)
    } catch {
      return null
    }
  },
  /** @param {string} token */
  set(token) {
    try {
      localStorage.setItem(KEY, token)
    } catch {
      /* storage unavailable — user will need to log in again */
    }
  },
  clear() {
    try {
      localStorage.removeItem(KEY)
    } catch {
      /* ignore */
    }
  },
}