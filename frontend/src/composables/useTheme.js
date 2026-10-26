// Light / Dark / System theme switch.
// We always set <html data-theme="light|dark">, and variables.css reacts to it.
// "System" follows the phone/PC setting and updates live when it changes.
import { ref } from 'vue'

const KEY = 'aquaflow.theme'
const media = window.matchMedia('(prefers-color-scheme: dark)')

function readSaved() {
  try {
    return localStorage.getItem(KEY) || 'system'
  } catch {
    return 'system'
  }
}

/** @type {import('vue').Ref<'system' | 'light' | 'dark'>} */
const preference = ref(readSaved())

function apply() {
  const dark = preference.value === 'dark' || (preference.value === 'system' && media.matches)
  document.documentElement.dataset.theme = dark ? 'dark' : 'light'
}

/** Call once in main.js, before the app mounts (prevents a light/dark flash). */
export function initTheme() {
  apply()
  media.addEventListener('change', () => {
    if (preference.value === 'system') apply()
  })
}

export function useTheme() {
  /** @param {'system' | 'light' | 'dark'} value */
  function setTheme(value) {
    preference.value = value
    try {
      localStorage.setItem(KEY, value)
    } catch {
      /* storage blocked: theme still applies for this session */
    }
    apply()
  }
  return { preference, setTheme }
}