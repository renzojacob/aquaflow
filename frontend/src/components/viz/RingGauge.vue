<!--
  RingGauge — a circular meter. The middle shows whatever you put in the slot.
  Usage: <RingGauge :value="0.72" :size="120" label="72% of today's orders delivered"><b>72%</b></RingGauge>
-->
<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, required: true },  // 0..1
  size: { type: Number, default: 112 },
  stroke: { type: Number, default: 10 },
  label: { type: String, required: true },
  tone: { type: String, default: 'water' }, // water | sun | pearl | warn
})
const r = computed(() => (props.size - props.stroke) / 2)
const c = computed(() => 2 * Math.PI * r.value)
const v = computed(() => Math.min(1, Math.max(0, props.value)))
</script>

<template>
  <div class="rg" :class="`rg--${tone}`" :style="{ width: `${size}px`, height: `${size}px` }" role="img" :aria-label="label">
    <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`" aria-hidden="true">
      <circle :cx="size / 2" :cy="size / 2" :r="r" class="rg__track" :stroke-width="stroke" />
      <circle
        :cx="size / 2"
        :cy="size / 2"
        :r="r"
        class="rg__bar"
        :stroke-width="stroke"
        :stroke-dasharray="c"
        :stroke-dashoffset="c * (1 - v)"
        :transform="`rotate(-90 ${size / 2} ${size / 2})`"
      />
    </svg>
    <div class="rg__mid" aria-hidden="true"><slot /></div>
  </div>
</template>

<style scoped>
.rg { position: relative; flex: none; display: grid; place-items: center; }
.rg { --c: var(--af-primary); }
.rg--sun { --c: var(--af-chart-money); }
.rg--pearl { --c: var(--af-accent); }
.rg--warn { --c: var(--af-amber); }
.rg svg { position: absolute; inset: 0; }
.rg__track { fill: none; stroke: var(--af-surface-3); }
.rg__bar {
  fill: none;
  stroke: var(--c);
  stroke-linecap: round;
  filter: drop-shadow(0 0 6px color-mix(in srgb, var(--c) 55%, transparent));
  transition: stroke-dashoffset 1200ms cubic-bezier(0.22, 1, 0.36, 1);
}
.rg__mid { position: relative; display: grid; place-items: center; text-align: center; line-height: 1.1; }
@media (prefers-reduced-motion: reduce) { .rg__bar { transition: none; } }
</style>
