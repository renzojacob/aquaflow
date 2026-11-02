<!--
  DonutChart — share of a whole (e.g. today's orders by status). Legend lists every slice
  with its number, so color is never the only signal.
  Usage: <DonutChart :slices="[{ label: 'Delivered', value: 8, color: 'var(--af-st-delivered)' }]" title="Today's orders" />
-->
<script setup>
import { computed } from 'vue'

const props = defineProps({
  slices: { type: Array, required: true },  // [{ label, value, color }]
  title: { type: String, required: true },
  size: { type: Number, default: 132 },
  center: { type: String, default: '' },    // big text in the middle
  centerSub: { type: String, default: '' },
})

const total = computed(() => props.slices.reduce((s, x) => s + x.value, 0))
const R = 52
const C = 2 * Math.PI * R
const arcs = computed(() => {
  let acc = 0
  const gap = props.slices.filter((s) => s.value).length > 1 ? 3 : 0
  return props.slices
    .filter((s) => s.value > 0)
    .map((s) => {
      const len = (s.value / Math.max(total.value, 1)) * C
      const arc = { ...s, dash: `${Math.max(0, len - gap)} ${C}`, offset: -acc }
      acc += len
      return arc
    })
})
</script>

<template>
  <figure class="dn">
    <div class="dn__ring" :style="{ width: `${size}px`, height: `${size}px` }" role="img" :aria-label="`${title}: ${slices.map((s) => `${s.label} ${s.value}`).join(', ')}`">
      <svg viewBox="0 0 120 120" aria-hidden="true">
        <circle cx="60" cy="60" :r="R" class="dn__track" />
        <circle
          v-for="a in arcs"
          :key="a.label"
          cx="60"
          cy="60"
          :r="R"
          class="dn__arc"
          :stroke="a.color"
          :stroke-dasharray="a.dash"
          :stroke-dashoffset="a.offset"
          transform="rotate(-90 60 60)"
        />
      </svg>
      <div class="dn__mid" aria-hidden="true">
        <b>{{ center || total }}</b>
        <span v-if="centerSub">{{ centerSub }}</span>
      </div>
    </div>
    <ul class="dn__legend">
      <li v-for="s in slices" :key="s.label" :class="{ 'is-zero': !s.value }">
        <i :style="{ background: s.color }" aria-hidden="true"></i>
        <span>{{ s.label }}</span>
        <b>{{ s.value }}</b>
      </li>
    </ul>
  </figure>
</template>

<style scoped>
.dn { margin: 0; display: flex; align-items: center; gap: var(--af-s5); flex-wrap: wrap; }
.dn__ring { position: relative; flex: none; display: grid; place-items: center; }
.dn__ring svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.dn__track { fill: none; stroke: var(--af-surface-2); stroke-width: 12; }
.dn__arc { fill: none; stroke-width: 12; stroke-linecap: butt; }
.dn__mid { position: relative; display: grid; text-align: center; }
.dn__mid b { font-family: var(--af-display); font-size: 28px; font-weight: 700; letter-spacing: -0.03em; line-height: 1; font-variant-numeric: tabular-nums; }
.dn__mid span { font-size: 12px; font-weight: 650; color: var(--af-ink-2); margin-top: 4px; }
.dn__legend { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; flex: 1; min-width: 160px; }
.dn__legend li { display: grid; grid-template-columns: 10px 1fr auto; align-items: center; gap: 10px; font-size: 14px; font-weight: 650; }
.dn__legend li.is-zero { opacity: 0.5; }
.dn__legend i { width: 10px; height: 10px; border-radius: 3px; }
.dn__legend b { font-variant-numeric: tabular-nums; font-weight: 800; }
</style>
