<!--
  ForecastChart — what happened (solid line), then what to expect (dashed line) with the likely
  range shaded around it. Hover (mouse) or the arrow keys (keyboard) read each day.
  Screen readers get the same numbers as a hidden table.

  Usage:
    <ForecastChart :history="[{ date: '2026-11-09', value: 15 }]"
                   :forecast="[{ date: '2026-11-10', value: 19, lower: 16, upper: 23 }]"
                   :show-band="true" title="Orders per day" unit="orders" />

  Straight segments on purpose: a forecast should not be smoothed into something prettier than it is.
  Colors come from the theme only (--af-brand for what happened, --af-accent for the forecast).
-->
<script setup>
import { computed, ref } from 'vue'

import { friendlyDay } from '@/utils/format'

const props = defineProps({
  history: { type: Array, required: true },         // [{ date, value }]
  forecast: { type: Array, required: true },        // [{ date, value, lower, upper }]
  title: { type: String, required: true },          // for screen readers + table caption
  unit: { type: String, default: '' },              // "orders", "containers"
  showBand: { type: Boolean, default: true },       // false when the band is unknown (not enough data)
  bandLabel: { type: String, default: 'Likely range' },
  height: { type: Number, default: 260 },
})

const W = 720
const pad = { t: 22, r: 10, b: 26, l: 10 }
const active = ref(-1)

const all = computed(() => [
  ...props.history.map((p) => ({ ...p, kind: 'actual' })),
  ...props.forecast.map((p) => ({ ...p, kind: 'forecast' })),
])
const n = computed(() => all.value.length)
const firstForecast = computed(() => props.history.length)
const hasBand = computed(() => props.showBand && props.forecast.some((p) => p.lower != null && p.upper != null))

/** Round the top of the scale up to a tidy number so the gridlines read well. */
function niceCeil(v) {
  if (v <= 0) return 1
  const pow = 10 ** Math.floor(Math.log10(v))
  return ([1, 2, 2.5, 5, 10].map((m) => m * pow).find((c) => c >= v)) ?? v
}
const top = computed(() => {
  const biggest = Math.max(1, ...all.value.map((p) => Math.max(p.value ?? 0, hasBand.value ? (p.upper ?? 0) : 0)))
  return niceCeil(biggest * 1.05)
})
const plotH = computed(() => props.height - pad.t - pad.b)
const x = (i) => pad.l + (n.value <= 1 ? (W - pad.l - pad.r) / 2 : (i * (W - pad.l - pad.r)) / (n.value - 1))
const y = (v) => pad.t + (1 - v / top.value) * plotH.value

const ticks = computed(() => [0.5, 1].map((f) => ({ value: top.value * f, y: y(top.value * f) })))
const pts = (list, from) => list.map((p, i) => `${x(from + i)},${y(p.value)}`)

const actualLine = computed(() => (props.history.length ? `M${pts(props.history, 0).join(' L')}` : ''))
// The dashed line starts at the last real day so the two lines meet.
const forecastLine = computed(() => {
  if (!props.forecast.length) return ''
  const start = props.history.length ? [`${x(firstForecast.value - 1)},${y(props.history.at(-1).value)}`] : []
  return `M${[...start, ...pts(props.forecast, firstForecast.value)].join(' L')}`
})
const band = computed(() => {
  if (!hasBand.value) return ''
  const f = props.forecast
  const i0 = firstForecast.value
  const anchor = props.history.length ? { x: x(i0 - 1), y: y(props.history.at(-1).value) } : null
  const up = f.map((p, i) => `${x(i0 + i)},${y(p.upper ?? p.value)}`)
  const low = f.map((p, i) => `${x(i0 + i)},${y(p.lower ?? p.value)}`).reverse()
  const a = anchor ? `${anchor.x},${anchor.y}` : null
  return `M${[a, ...up, ...low, a].filter(Boolean).join(' L')} Z`
})
const dividerX = computed(() => (props.history.length && props.forecast.length ? (x(firstForecast.value - 1) + x(firstForecast.value)) / 2 : null))

const short = (iso) => {
  const [yy, m, d] = iso.split('-').map(Number)
  return new Date(yy, m - 1, d).toLocaleDateString('en-PH', { month: 'short', day: 'numeric' })
}
const step = computed(() => Math.max(1, Math.ceil(n.value / 7)))
function showLabel(i) {
  const last = n.value - 1
  if (i === last) return true
  return i % step.value === 0 && last - i >= Math.ceil(step.value / 2) + 1
}

function onMove(ev) {
  const rect = ev.currentTarget.getBoundingClientRect()
  const px = ((ev.clientX - rect.left) / rect.width) * W
  let best = 0
  for (let i = 0; i < n.value; i++) if (Math.abs(x(i) - px) < Math.abs(x(best) - px)) best = i
  active.value = best
}
function onKey(ev) {
  if (ev.key === 'ArrowRight') active.value = Math.min(n.value - 1, active.value + 1)
  else if (ev.key === 'ArrowLeft') active.value = Math.max(0, active.value < 0 ? n.value - 1 : active.value - 1)
  else if (ev.key === 'Escape') active.value = -1
  else return
  ev.preventDefault()
}

const round = (v) => (Math.round(v * 10) / 10).toString()
const tip = computed(() => {
  const p = all.value[active.value]
  if (!p) return null
  const range = p.kind === 'forecast' && hasBand.value && p.lower != null ? `${props.bandLabel} ${round(p.lower)} to ${round(p.upper)}` : ''
  return { ...p, left: (x(active.value) / W) * 100, top: y(p.value), range, name: p.kind === 'forecast' ? 'Forecast' : 'Actual' }
})
</script>

<template>
  <figure class="fc">
    <div class="fc__plot">
      <svg
        :viewBox="`0 0 ${W} ${height}`"
        preserveAspectRatio="none"
        :style="{ height: `${height}px` }"
        tabindex="0"
        role="img"
        :aria-label="`${title}. Solid line is what happened, dashed line is the forecast. Use the left and right arrow keys to read each day.`"
        @pointermove="onMove"
        @pointerleave="active = -1"
        @keydown="onKey"
        @blur="active = -1"
      >
        <line :x1="pad.l" :x2="W - pad.r" :y1="y(0)" :y2="y(0)" class="fc__base" />
        <line v-for="t in ticks" :key="t.value" :x1="pad.l" :x2="W - pad.r" :y1="t.y" :y2="t.y" class="fc__grid" />
        <line v-if="dividerX !== null" :x1="dividerX" :x2="dividerX" :y1="pad.t - 6" :y2="y(0)" class="fc__divider" vector-effect="non-scaling-stroke" />
        <path v-if="band" :d="band" class="fc__band" />
        <path v-if="actualLine" :d="actualLine" class="fc__actual" vector-effect="non-scaling-stroke" />
        <path v-if="forecastLine" :d="forecastLine" class="fc__forecast" vector-effect="non-scaling-stroke" />
        <line v-if="tip" :x1="x(active)" :x2="x(active)" :y1="pad.t" :y2="y(0)" class="fc__cursor" vector-effect="non-scaling-stroke" />
      </svg>

      <span v-for="t in ticks" :key="t.value" class="fc__ytick" :style="{ top: `${t.y}px` }" aria-hidden="true">{{ round(t.value) }}</span>
      <span v-if="dividerX !== null" class="fc__today" :style="{ left: `${(dividerX / W) * 100}%` }" aria-hidden="true">Today ›</span>

      <span v-if="tip" class="fc__dot" :class="{ 'is-forecast': tip.kind === 'forecast' }" :style="{ left: `${tip.left}%`, top: `${tip.top}px` }" aria-hidden="true"></span>
      <div v-if="tip" class="fc__tip" :style="{ left: `clamp(80px, ${tip.left}%, calc(100% - 80px))` }" aria-live="polite">
        <b>{{ round(tip.value) }} {{ unit }}</b>
        <span>{{ friendlyDay(tip.date) }} · {{ tip.name }}</span>
        <span v-if="tip.range">{{ tip.range }}</span>
      </div>

      <div class="fc__x" aria-hidden="true">
        <span v-for="(p, i) in all" v-show="showLabel(i)" :key="p.date" :style="{ left: `${(x(i) / W) * 100}%` }">{{ short(p.date) }}</span>
      </div>
    </div>

    <ul class="fc__legend" aria-hidden="true">
      <li><i class="sw sw--actual"></i> What happened</li>
      <li><i class="sw sw--forecast"></i> Forecast</li>
      <li v-if="hasBand"><i class="sw sw--band"></i> {{ bandLabel }}</li>
    </ul>

    <table class="af-sr-only">
      <caption>{{ title }}</caption>
      <thead><tr><th scope="col">Day</th><th scope="col">Type</th><th scope="col">{{ unit || 'Value' }}</th><th v-if="hasBand" scope="col">{{ bandLabel }}</th></tr></thead>
      <tbody>
        <tr v-for="p in all" :key="p.date">
          <th scope="row">{{ friendlyDay(p.date) }}</th>
          <td>{{ p.kind === 'forecast' ? 'Forecast' : 'Actual' }}</td>
          <td>{{ round(p.value) }}</td>
          <td v-if="hasBand">{{ p.kind === 'forecast' && p.lower != null ? `${round(p.lower)} to ${round(p.upper)}` : '' }}</td>
        </tr>
      </tbody>
    </table>
  </figure>
</template>

<style scoped>
.fc { margin: 0; --a: var(--af-brand); --f: var(--af-accent); }
.fc__plot { position: relative; padding-bottom: 6px; }
.fc svg { display: block; width: 100%; overflow: visible; cursor: crosshair; border-radius: 12px; }
.fc svg:focus-visible { outline: 3px solid var(--af-focus); outline-offset: 4px; }

.fc__base { stroke: var(--af-line-strong); stroke-width: 1; }
.fc__grid { stroke: var(--af-line); stroke-width: 1; stroke-dasharray: 3 6; }
.fc__divider { stroke: var(--af-line-strong); stroke-width: 1; stroke-dasharray: 2 4; }
.fc__band { fill: color-mix(in srgb, var(--f) 20%, transparent); stroke: none; }
.fc__actual { fill: none; stroke: var(--a); stroke-width: 2.75; stroke-linecap: round; stroke-linejoin: round; }
.fc__forecast { fill: none; stroke: var(--f); stroke-width: 2.75; stroke-linecap: round; stroke-linejoin: round; stroke-dasharray: 7 6; }
.fc__cursor { stroke: var(--af-line-strong); stroke-width: 1; }

.fc__ytick { position: absolute; left: 2px; transform: translateY(-115%); font-size: 11px; font-weight: 650; color: var(--af-ink-2); font-variant-numeric: tabular-nums; pointer-events: none; }
.fc__today { position: absolute; top: -2px; transform: translateX(6px); font-size: 11px; font-weight: 750; letter-spacing: 0.04em; color: var(--af-ink-2); pointer-events: none; }

.fc__dot { position: absolute; width: 12px; height: 12px; margin: -6px 0 0 -6px; border-radius: 50%; background: var(--a); box-shadow: 0 0 0 4px color-mix(in srgb, var(--a) 25%, transparent); pointer-events: none; }
.fc__dot.is-forecast { background: var(--f); box-shadow: 0 0 0 4px color-mix(in srgb, var(--f) 25%, transparent); }
.fc__tip {
  position: absolute; top: -6px; transform: translate(-50%, -100%);
  display: grid; gap: 1px; padding: 8px 12px; border-radius: 12px;
  background: var(--af-surface-solid); border: 1px solid var(--af-line-strong); box-shadow: var(--af-shadow-2);
  white-space: nowrap; pointer-events: none; text-align: center; z-index: 2;
}
.fc__tip b { font-family: var(--af-display); font-size: 15px; font-weight: 600; font-variant-numeric: tabular-nums; }
.fc__tip span { font-size: 12px; color: var(--af-ink-2); font-weight: 600; }

.fc__x { position: relative; height: 18px; margin-top: -18px; }
.fc__x span { position: absolute; transform: translateX(-50%); font-size: 11.5px; font-weight: 650; color: var(--af-ink-2); white-space: nowrap; }
.fc__x span:first-child { transform: none; }
.fc__x span:last-child { transform: translateX(-100%); }

.fc__legend { display: flex; flex-wrap: wrap; gap: 6px 18px; margin: 10px 0 0; padding: 0; list-style: none; font-size: 13px; font-weight: 650; color: var(--af-ink-2); }
.fc__legend li { display: inline-flex; align-items: center; gap: 8px; }
.sw { display: inline-block; width: 26px; height: 0; border-top: 3px solid var(--a); border-radius: 2px; }
.sw--forecast { border-top: 3px dashed var(--f); }
.sw--band { height: 12px; border: 0; border-radius: 4px; background: color-mix(in srgb, var(--f) 20%, transparent); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--f) 45%, transparent); }
</style>
