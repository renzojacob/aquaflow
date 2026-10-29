<!--
  WaterLevelBar — AquaFlow's signature capacity bar.
  Used for vehicle load, station stock and supplies.
  Usage: <WaterLevelBar label="Tricycle ABC-123" :value="18" :max="20" />
  States (shown by color AND text):
    ok   = below 90%
    near = 90% to 100%  (amber, "Almost full")
    over = above 100%   (red, "Over capacity")
-->
<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, required: true },
  max: { type: Number, required: true },
  label: { type: String, default: '' },
  unit: { type: String, default: 'containers' },
  note: { type: String, default: '' }, // custom note; replaces the automatic one
  size: { type: String, default: 'md' }, // md | lg
})

const ratio = computed(() => (props.max > 0 ? props.value / props.max : 0))

const state = computed(() => {
  if (ratio.value > 1) return 'over'
  if (ratio.value >= 0.9) return 'near'
  return 'ok'
})

const fillPercent = computed(() => `${Math.min(ratio.value, 1) * 100}%`)

// One tick per container when there are few enough to count (e.g. 20 slots)
const tickWidth = computed(() => (props.max > 0 && props.max <= 40 ? `${100 / props.max}%` : null))

const autoNote = computed(() => {
  const free = props.max - props.value
  if (state.value === 'over') return `✕ Over capacity by ${props.value - props.max}`
  if (state.value === 'near') return `⚠ Almost full · ${free} ${props.unit} left`
  return `${free} ${props.unit} free`
})
</script>

<template>
  <div class="af-wl" :class="[`af-wl--${state}`, `af-wl--${size}`]">
    <div class="af-wl__row">
      <span class="af-caption">{{ label }}</span>
      <span class="af-wl__val">{{ value }} <em>/ {{ max }}</em></span>
    </div>

    <div
      class="af-wl__track"
      role="meter"
      :aria-valuemin="0"
      :aria-valuemax="max"
      :aria-valuenow="value"
      :aria-label="`${label}: ${value} of ${max} ${unit}`"
    >
      <div class="af-wl__fill" :style="{ width: fillPercent }"></div>
      <div v-if="tickWidth" class="af-wl__ticks" :style="{ '--tick': tickWidth }"></div>
    </div>

    <span class="af-wl__note">{{ note || autoNote }}</span>
  </div>
</template>

<style scoped>
.af-wl { display: grid; gap: 8px; min-width: 0; }
.af-wl__row { display: flex; justify-content: space-between; align-items: baseline; gap: var(--af-s2); }
.af-wl__val { font-family: var(--af-display); font-weight: 700; font-size: 16px; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; white-space: nowrap; }
.af-wl__val em { font-style: normal; color: var(--af-ink-2); font-weight: 500; }
.af-wl__note { font-size: 13px; font-weight: 650; color: var(--af-ink-2); }

.af-wl__track {
  position: relative;
  height: 16px;
  border-radius: var(--af-r-pill);
  background: var(--af-surface-2);
  overflow: hidden;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.12), inset 0 0 0 1px var(--af-line);
}
.af-wl--lg .af-wl__track { height: 26px; }

.af-wl__fill {
  position: absolute;
  inset: 0 auto 0 0;
  border-radius: inherit;
  overflow: hidden;
  background: linear-gradient(180deg, color-mix(in srgb, var(--af-water) 85%, #fff) 0%, var(--af-water) 45%, var(--af-water-deep) 100%);
  box-shadow: 0 0 18px color-mix(in srgb, var(--af-water) 45%, transparent);
  transition: width 600ms var(--af-ease-out);
  animation: af-fill 900ms var(--af-ease-out) both;
}
/* The meniscus: a bright curved water line at the edge of the fill */
.af-wl__fill::before {
  content: '';
  position: absolute;
  top: 1px;
  bottom: 1px;
  right: 1px;
  width: 4px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.75);
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.6);
}
/* Small ripples moving across the water surface */
.af-wl__fill::after {
  content: '';
  position: absolute;
  inset: 0 -40px 0 0;
  background: radial-gradient(10px 5px at 10px 0, rgba(255, 255, 255, 0.5) 98%, transparent 100%) 0 0 / 20px 100% repeat-x;
  opacity: 0.5;
  animation: af-wave 2.6s linear infinite;
}
@keyframes af-wave { to { transform: translateX(-20px); } }
@keyframes af-fill { from { clip-path: inset(0 100% 0 0 round 999px); } to { clip-path: inset(0 0 0 0 round 999px); } }

.af-wl__ticks {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: repeating-linear-gradient(
    90deg,
    transparent 0 calc(var(--tick) - 1px),
    color-mix(in srgb, var(--af-bg) 55%, transparent) calc(var(--tick) - 1px) var(--tick)
  );
}

.af-wl--near .af-wl__fill { background: linear-gradient(180deg, color-mix(in srgb, var(--af-amber) 80%, #fff) 0%, var(--af-amber) 50%, color-mix(in srgb, var(--af-amber) 75%, #000) 100%); box-shadow: 0 0 18px color-mix(in srgb, var(--af-amber) 40%, transparent); }
.af-wl--over .af-wl__fill { background: linear-gradient(180deg, var(--af-danger) 0%, color-mix(in srgb, var(--af-danger) 75%, #000) 100%); box-shadow: 0 0 18px color-mix(in srgb, var(--af-danger) 40%, transparent); }
.af-wl--near .af-wl__note { color: var(--af-amber-fg); }
.af-wl--over .af-wl__note { color: var(--af-danger); }
</style>
