// Theme = a brand (Ocean / Forest / Sunset) + a mode (Light / Dark / Auto).
// We set <html data-brand="..." data-theme="light|dark"> and the CSS in theme/ reacts.
// The saved choice is applied before first paint by a tiny inline script in index.html;
// this module keeps it in sync afterwards (Auto follows the device live).
import { computed, ref } from 'vue'

export const KEY = 'aquaflow.theme'

export const BRANDS = Object.freeze([
  { id: 'ocean', name: 'Ocean', tagline: 'Deep blues, aqua light', swatch: ['#0a1a3f', '#0b5bd3', '#38e1ff'] },
  { id: 'forest', name: 'Forest', tagline: 'Pine green, fresh mint', swatch: ['#06281f', '#1b7a4a', '#5ee6a8'] },
  { id: 'sunset', name: 'Sunset', tagline: 'Warm coral, soft violet', swatch: ['#2a1230', '#c2410c', '#ff9b7a'] },
])
export const MODES = Object.freeze([
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
  { value: 'auto', label: 'Auto' },
])

const BRAND_IDS = BRANDS.map((b) => b.id)
export const DEFAULT_BRAND = 'ocean'
export const DEFAULT_MODE = 'dark'

const media = window.matchMedia('(prefers-color-scheme: dark)')
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)')

/** Read what index.html already applied (or what's saved), with the old string format migrated. */
function readSaved() {
  let brand = DEFAULT_BRAND
  let mode = DEFAULT_MODE
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) {
      try {
        const v = JSON.parse(raw)
        if (v && typeof v === 'object') {
          if (BRAND_IDS.includes(v.brand)) brand = v.brand
          if (['light', 'dark', 'auto'].includes(v.mode)) mode = v.mode
        }
      } catch {
        // before the brand system we saved just 'light' | 'dark' | 'system'
        if (raw === 'light' || raw === 'dark') mode = raw
      }
    }
  } catch {
    /* storage blocked */
  }
  return { brand, mode }
}

const saved = readSaved()
const brand = ref(saved.brand)
const mode = ref(saved.mode)
const systemDark = ref(media.matches)

/** 'light' | 'dark': what is on screen right now */
const resolved = computed(() => (mode.value === 'auto' ? (systemDark.value ? 'dark' : 'light') : mode.value))

function persist() {
  try {
    localStorage.setItem(KEY, JSON.stringify({ brand: brand.value, mode: mode.value }))
  } catch {
    /* storage blocked: theme still applies for this session */
  }
}

let fadeTimer = 0
function apply({ animate = false } = {}) {
  const html = document.documentElement
  if (animate && !reduceMotion.matches) {
    html.classList.add('af-theming')
    clearTimeout(fadeTimer)
    fadeTimer = setTimeout(() => html.classList.remove('af-theming'), 420)
  }
  html.dataset.brand = brand.value
  html.dataset.theme = resolved.value
  // Browser chrome (address bar on phones) follows the page background
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) {
    const color = getComputedStyle(html).getPropertyValue('--af-meta-color').trim()
    if (color) meta.setAttribute('content', color)
  }
}

/** Call once in main.js, before the app mounts. */
export function initTheme() {
  // ?brand=forest&mode=dark lets anyone preview a look from a link (saved, like the picker)
  const q = new URLSearchParams(window.location.search)
  const qb = q.get('brand') ?? q.get('theme')
  const qm = q.get('mode')
  let fromQuery = false
  if (BRAND_IDS.includes(qb)) (brand.value = qb), (fromQuery = true)
  if (['light', 'dark', 'auto'].includes(qm)) (mode.value = qm), (fromQuery = true)
  if (fromQuery) persist()
  apply()
  media.addEventListener('change', (e) => {
    systemDark.value = e.matches
    if (mode.value === 'auto') apply({ animate: true })
  })
}

export function useTheme() {
  /** @param {'ocean' | 'forest' | 'sunset'} id */
  function setBrand(id) {
    if (!BRAND_IDS.includes(id) || id === brand.value) return
    brand.value = id
    persist()
    apply({ animate: true })
  }
  /** @param {'light' | 'dark' | 'auto'} value */
  function setMode(value) {
    if (!['light', 'dark', 'auto'].includes(value) || value === mode.value) return
    mode.value = value
    persist()
    apply({ animate: true })
  }
  /** Older API: 'system' | 'light' | 'dark' */
  function setTheme(value) {
    setMode(value === 'system' ? 'auto' : value)
  }
  const preference = computed(() => (mode.value === 'auto' ? 'system' : mode.value))
  return { brand, mode, resolved, setBrand, setMode, setTheme, preference, BRANDS, MODES }
}
