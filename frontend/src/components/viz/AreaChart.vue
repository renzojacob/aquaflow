<!--
  AreaChart — a smooth line with a water-like fill under it.
  Hover (mouse) or arrow keys (keyboard) show each point's value.
  Screen readers get the same numbers as a hidden table.

  Usage:
    <AreaChart :points="[{ label: 'Mon', value: 12 }, ...]" :format="peso" title="Sales, last 14 days" />
-->
<script setup>
import { computed, ref, useId } from 'vue'

const props = defineProps({
  points: { type: Array, required: true },          // [{ label, value, sub? }]
  title: { type: String, required: true },          // for screen readers + table caption
  format: { type: Function, default: (v) => String(v) },
  height: { type: Number, default: 180 },
  tone: { type: String, default: 'water' },         // water | sun | pearl
  every: { type: Number, default: 0 },              // show every Nth x label (0 = auto)
})

const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '')
const W = 600
const pad = { t: 16, r: 8, b: 26, l: 8 }
const active = ref(-1)

const max = computed(() => Math.max(1, ...props.points.map((p) => p.value)) * 1.15)
const xs = computed(() => {
  const n = props.points.length
  return props.points.map((_, i) => pad.l + (n === 1 ? (W - pad.l - pad.r) / 2 : (i * (W - pad.l - pad.r)) / (n - 1)))
})
const ys = computed(() => props.points.map((p) => pad.t + (1 - p.value / max.value) * (props.height - pad.t - pad.b)))

/** Smooth curve through the points (Catmull-Rom turned into Bezier segments). */
const line = computed(() => {
  const x = xs.value
  const y = ys.value
  if (!x.length) return ''
  let d = `M${x[0]},${y[0]}`
  for (let i = 0; i < x.length - 1; i++) {
    const x0 = x[i - 1] ?? x[i], y0 = y[i - 1] ?? y[i]
    const x3 = x[i + 2] ?? x[i + 1], y3 = y[i + 2] ?? y[i + 1]
    const c1x = x[i] + (x[i + 1] - x0) / 6, c1y = y[i] + (y[i + 1] - y0) / 6
    const c2x = x[i + 1] - (x3 - x[i]) / 6, c2y = y[i + 1] - (y3 - y[i]) / 6
    d += ` C${c1x},${Math.min(c1y, props.height - pad.b)} ${c2x},${Math.min(c2y, props.height - pad.b)} ${x[i + 1]},${y[i + 1]}`
  }
  return d
})
const area = computed(() => `${line.value} L${xs.value.at(-1)},${props.height - pad.b} L${xs.value[0]},${props.height - pad.b} Z`)

const step = computed(() => props.every || Math.max(1, Math.ceil(props.points.length / 7)))
const grid = computed(() => [0.33, 0.66, 1].map((f) => pad.t + (1 - f / 1.15) * (props.height - pad.t - pad.b)))

/** Every Nth label, plus the last one, but never two labels crammed together at the end. */
function showLabel(i) {
  const last = props.points.length - 1
  if (i === last) return true
  return i % step.value === 0 && last - i >= Math.ceil(step.value / 2) + 1
}

function onMove(ev) {
  const rect = ev.currentTarget.getBoundingClientRect()
  const x = ((ev.clientX - rect.left) / rect.width) * W
  let best = 0
  xs.value.forEach((v, i) => {
    if (Math.abs(v - x) < Math.abs(xs.value[best] - x)) best = i
  })
  active.value = best
}
function onKey(ev) {
  const n = props.points.length
  if (ev.key === 'ArrowRight') active.value = Math.min(n - 1, active.value + 1)
  else if (ev.key === 'ArrowLeft') active.value = Math.max(0, active.value < 0 ? n - 1 : active.value - 1)
  else return
  ev.preventDefault()
}

const tip = computed(() => {
  if (active.value < 0) return null
  const p = props.points[active.value]
  return { ...p, x: (xs.value[active.value] / W) * 100, y: ys.value[active.value] }
})
</script>

<template>
  <figure class="ac" :class="`ac--${tone}`">
    <div class="ac__plot">
      <svg
        :viewBox="`0 0 ${W} ${height}`"
        preserveAspectRatio="none"
        :style="{ height: `${height}px` }"
        tabindex="0"
        role="img"
        :aria-label="`${title}. Use the left and right arrow keys to read each value.`"
        @pointermove="onMove"
        @pointerleave="active = -1"
        @keydown="onKey"
        @blur="active = -1"
      >
        <defs>
          <linearGradient :id="`ac-f-${uid}`" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" class="ac__f1" />
            <stop offset="1" class="ac__f2" />
          </linearGradient>
        </defs>
        <line v-for="(g, i) in grid" :key="i" :x1="pad.l" :x2="W - pad.r" :y1="g" :y2="g" class="ac__grid" />
        <path :d="area" :fill="`url(#ac-f-${uid})`" />
        <path :d="line" class="ac__line" vector-effect="non-scaling-stroke" />
        <line v-if="tip" :x1="xs[active]" :x2="xs[active]" :y1="pad.t" :y2="height - pad.b" class="ac__cursor" vector-effect="non-scaling-stroke" />
      </svg>
      <span v-if="tip" class="ac__dot" :style="{ left: `${tip.x}%`, top: `${tip.y}px` }" aria-hidden="true"></span>
      <div v-if="tip" class="ac__tip" :style="{ left: `clamp(60px, ${tip.x}%, calc(100% - 60px))` }" aria-live="polite">
        <b>{{ format(tip.value) }}</b>
        <span>{{ tip.sub || tip.label }}</span>
      </div>
      <div class="ac__x" aria-hidden="true">
        <span
          v-for="(p, i) in points"
          v-show="showLabel(i)"
          :key="i"
          :style="{ left: `${(xs[i] / W) * 100}%` }"
        >{{ p.label }}</span>
      </div>
    </div>
    <table class="af-sr-only">
      <caption>{{ title }}</caption>
      <tbody>
        <tr v-for="(p, i) in points" :key="i"><th scope="row">{{ p.sub || p.label }}</th><td>{{ format(p.value) }}</td></tr>
      </tbody>
    </table>
  </figure>
</template>

<style scoped>
.ac { margin: 0; }
.ac__plot { position: relative; padding-bottom: 6px; }
.ac svg { display: block; width: 100%; overflow: visible; cursor: crosshair; border-radius: 12px; }
.ac svg:focus-visible { outline: 3px solid var(--af-focus); outline-offset: 4px; }

.ac { --c: var(--af-primary); --f: var(--af-water); }
.ac--sun { --c: var(--af-chart-money); --f: var(--af-chart-money-fill); }
.ac--pearl { --c: var(--af-accent); --f: var(--af-accent); }
.ac__f1 { stop-color: var(--f); stop-opacity: 0.38; }
.ac__f2 { stop-color: var(--f); stop-opacity: 0; }
.ac__line { fill: none; stroke: var(--c); stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; }
.ac__grid { stroke: var(--af-line); stroke-width: 1; stroke-dasharray: 3 6; }
.ac__cursor { stroke: var(--af-line-strong); stroke-width: 1; }

.ac__dot {
  position: absolute;
  width: 12px;
  height: 12px;
  margin: -6px 0 0 -6px;
  border-radius: 50%;
  background: var(--c);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--c) 25%, transparent), 0 0 14px var(--c);
  pointer-events: none;
}
.ac__tip {
  position: absolute;
  top: -6px;
  transform: translate(-50%, -100%);
  display: grid;
  gap: 1px;
  padding: 8px 12px;
  border-radius: 12px;
  background: var(--af-surface-solid);
  border: 1px solid var(--af-line-strong);
  box-shadow: var(--af-shadow-2);
  white-space: nowrap;
  pointer-events: none;
  text-align: center;
  z-index: 2;
}
.ac__tip b { font-family: var(--af-display); font-size: 15px; font-weight: 600; font-variant-numeric: tabular-nums; }
.ac__tip span { font-size: 12px; color: var(--af-ink-2); font-weight: 600; }

.ac__x { position: relative; height: 18px; margin-top: -18px; }
.ac__x span { position: absolute; transform: translateX(-50%); font-size: 11.5px; font-weight: 650; color: var(--af-ink-2); white-space: nowrap; }
.ac__x span:first-child { transform: none; }
.ac__x span:last-child { transform: translateX(-100%); }
</style>
