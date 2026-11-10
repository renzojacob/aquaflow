<!--
  BarChart — vertical bars shaped like water columns (rounded tops, filled from the bottom).
  The tallest bar and the current/last bar are highlighted.
  Usage: <BarChart :bars="[{ label: 'Jun', value: 240, sub: 'June 2026' }]" :format="peso" title="Spending by month" />
-->
<script setup>
import { computed } from 'vue'

const props = defineProps({
  bars: { type: Array, required: true },           // [{ label, value, sub? }]
  title: { type: String, required: true },
  format: { type: Function, default: (v) => String(v) },
  height: { type: Number, default: 160 },
  tone: { type: String, default: 'water' },        // water | sun | pearl
  highlight: { type: Number, default: -1 },        // index to light up (default: last)
})

const max = computed(() => Math.max(1, ...props.bars.map((b) => b.value)))
const hi = computed(() => (props.highlight >= 0 ? props.highlight : props.bars.length - 1))
</script>

<template>
  <figure class="bc" :class="`bc--${tone}`">
    <div class="bc__plot" :style="{ height: `${height}px` }" role="img" :aria-label="`${title}: ${bars.map((b) => `${b.sub || b.label} ${format(b.value)}`).join(', ')}`">
      <div v-for="(b, i) in bars" :key="i" class="bc__col" :class="{ 'is-hi': i === hi, 'is-zero': !b.value }">
        <span class="bc__val" aria-hidden="true">{{ b.value ? format(b.value) : '' }}</span>
        <span class="bc__bar" :style="{ height: `${Math.max(b.value ? 6 : 2, (b.value / max) * 100)}%`, '--i': i }"></span>
      </div>
    </div>
    <div class="bc__x" aria-hidden="true">
      <span v-for="(b, i) in bars" :key="i" :class="{ 'is-hi': i === hi }">{{ b.label }}</span>
    </div>
  </figure>
</template>

<style scoped>
.bc { margin: 0; }
.bc { --c: var(--af-water); --c2: var(--af-water-deep); }
.bc--sun { --c: var(--af-chart-money-fill); --c2: var(--af-chart-money); }
.bc--pearl { --c: var(--af-accent); --c2: color-mix(in srgb, var(--af-accent) 55%, var(--af-deep)); }
.bc__plot {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(0, 1fr);
  gap: clamp(4px, 1.4vw, 12px);
  align-items: end;
  padding-top: 24px;
  border-bottom: 1px solid var(--af-line);
}
.bc__col { position: relative; height: 100%; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; min-width: 0; }
.bc__bar {
  width: 100%;
  max-width: 44px;
  border-radius: 10px 10px 3px 3px;
  background: linear-gradient(180deg, color-mix(in srgb, var(--c) 55%, transparent) 0%, color-mix(in srgb, var(--c2) 30%, transparent) 100%);
  box-shadow: inset 0 2px 0 color-mix(in srgb, var(--c) 70%, transparent);
  transform-origin: bottom;
  animation: bc-rise 900ms cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: calc(var(--i) * 40ms);
}
.bc__col.is-hi .bc__bar {
  background: linear-gradient(180deg, var(--c) 0%, var(--c2) 100%);
  box-shadow: inset 0 2px 0 rgba(255, 255, 255, 0.5), 0 0 22px color-mix(in srgb, var(--c) 45%, transparent);
}
.bc__col.is-zero .bc__bar { background: var(--af-line); box-shadow: none; }
@keyframes bc-rise { from { transform: scaleY(0); } to { transform: scaleY(1); } }

.bc__val {
  position: absolute;
  top: -2px;
  font-size: 11px;
  font-weight: 750;
  color: var(--af-ink-2);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  opacity: 0;
  transition: opacity var(--af-dur) var(--af-ease);
}
.bc__col.is-hi .bc__val, .bc__col:hover .bc__val { opacity: 1; color: var(--af-ink); }

.bc__x { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); gap: clamp(4px, 1.4vw, 12px); margin-top: 8px; }
.bc__x span { text-align: center; font-size: 11.5px; font-weight: 650; color: var(--af-ink-2); overflow: hidden; text-overflow: clip; white-space: nowrap; }
.bc__x span.is-hi { color: var(--af-ink); font-weight: 800; }

@media (prefers-reduced-motion: reduce) { .bc__bar { animation: none; } }
</style>
