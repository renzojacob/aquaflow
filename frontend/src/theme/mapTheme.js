// Map colors come from the active theme (CSS custom properties), read when a map is drawn.
// Leaflet draws SVG with inline attributes, so it cannot use var(--af-...) directly.
const FALLBACK = {
  route: '#0a8fc2',
  path: '#0b5bd3',
  stopRing: '#6d3fe0',
  deep: '#0a1a3f',
  glow: '#38e1ff',
  muted: '#4a5a78',
  surface: '#ffffff',
}

/** One CSS custom property from <html>, trimmed. */
export function cssVar(name, fallback = '') {
  if (typeof document === 'undefined') return fallback
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

/** The colors a map needs right now. */
export function mapColors() {
  return {
    route: cssVar('--af-map-route', FALLBACK.route),       // real roads
    path: cssVar('--af-map-path', FALLBACK.path),          // dotted estimate, "you -> next stop"
    stopRing: cssVar('--af-map-stop-ring', FALLBACK.stopRing),
    deep: cssVar('--af-deep', FALLBACK.deep),              // marker body
    glow: cssVar('--af-glow-c', FALLBACK.glow),            // marker accent
    muted: cssVar('--af-ink-2', FALLBACK.muted),           // not served / not planned
    surface: cssVar('--af-surface-solid', FALLBACK.surface),
  }
}

/** The water-drop pin as inline SVG, in the theme's colors. */
export function pinSvg(width = 34, height = 44) {
  const c = mapColors()
  return (
    `<svg width="${width}" height="${height}" viewBox="0 0 34 44" aria-hidden="true">` +
    `<path d="M17 1C8.2 1 1 8 1 16.7 1 28.5 17 43 17 43s16-14.5 16-26.3C33 8 25.8 1 17 1Z" fill="${c.deep}" stroke="${c.glow}" stroke-width="2"/>` +
    `<path d="M17 8.5c3.2 4 5.6 7.1 5.6 10a5.6 5.6 0 1 1-11.2 0c0-2.9 2.4-6 5.6-10Z" fill="${c.glow}"/></svg>`
  )
}
