// One colour per trip on the map and on its card. They are the theme's chart series
// (--af-chart-1..6), so every brand and mode gets its own set. All are dark enough for
// white numbers in light mode and light enough for dark numbers in dark mode.
import { cssVar } from '@/theme/mapTheme'

const FALLBACK = ['#0b5bd3', '#6d3fe0', '#c2410c', '#0e7490', '#be185d', '#4d7c0f']

/** @param {number} index position of the trip in today's list */
export const tripColor = (index) => {
  const i = index % FALLBACK.length
  return cssVar(`--af-chart-${i + 1}`, FALLBACK[i])
}
