<!-- Sparkline — tiny trend line for KPI tiles. Decorative: the tile states the number in words. -->
<script setup>
import { computed, useId } from 'vue'

const props = defineProps({
  values: { type: Array, required: true },
  tone: { type: String, default: 'water' }, // water | sun | pearl
  width: { type: Number, default: 96 },
  height: { type: Number, default: 32 },
})
const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '')
const pts = computed(() => {
  const v = props.values.length ? props.values : [0]
  const max = Math.max(1, ...v)
  const n = v.length
  return v.map((y, i) => [n === 1 ? props.width / 2 : (i * props.width) / (n - 1), 3 + (1 - y / max) * (props.height - 6)])
})
const line = computed(() => pts.value.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' '))
const area = computed(() => `${line.value} L${props.width},${props.height} L0,${props.height} Z`)
</script>

<template>
  <svg class="sp" :class="`sp--${tone}`" :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`" aria-hidden="true">
    <defs>
      <linearGradient :id="`sp-${uid}`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" class="sp__f1" />
        <stop offset="1" class="sp__f2" />
      </linearGradient>
    </defs>
    <path :d="area" :fill="`url(#sp-${uid})`" />
    <path :d="line" class="sp__line" />
    <circle :cx="pts.at(-1)[0]" :cy="pts.at(-1)[1]" r="2.6" class="sp__end" />
  </svg>
</template>

<style scoped>
.sp { flex: none; overflow: visible; --c: var(--af-primary); }
.sp--sun { --c: var(--af-chart-money); }
.sp--pearl { --c: var(--af-accent); }
.sp__f1 { stop-color: var(--c); stop-opacity: 0.3; }
.sp__f2 { stop-color: var(--c); stop-opacity: 0; }
.sp__line { fill: none; stroke: var(--c); stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.sp__end { fill: var(--c); filter: drop-shadow(0 0 4px var(--c)); }
</style>
