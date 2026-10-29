<!--
  StatCard — one big number for dashboards.
  Usage: <StatCard label="Ready stock" :value="64" unit="containers" delta="Forecast needs 71" />
-->
<script setup>
import { computed } from 'vue'
import { IonIcon } from '@ionic/vue'
import { trendingDownOutline, trendingUpOutline, warningOutline } from 'ionicons/icons'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], required: true },
  unit: { type: String, default: '' },
  delta: { type: String, default: '' },      // small line under the number
  tone: { type: String, default: 'neutral' }, // neutral | up | down | warn
})

const display = computed(() =>
  typeof props.value === 'number' ? props.value.toLocaleString('en-PH') : props.value,
)

const toneIcon = computed(
  () => ({ up: trendingUpOutline, down: trendingDownOutline, warn: warningOutline })[props.tone] ?? null,
)
</script>

<template>
  <div class="af-card af-stat">
    <span class="af-caption">{{ label }}</span>
    <span class="af-stat__big">
      {{ display }}<small v-if="unit">{{ unit }}</small>
    </span>
    <span v-if="delta" class="af-stat__delta" :class="`af-stat__delta--${tone}`">
      <ion-icon v-if="toneIcon" :icon="toneIcon" aria-hidden="true" />
      {{ delta }}
    </span>
    <slot />
  </div>
</template>

<style scoped>
.af-stat { display: grid; gap: var(--af-s3); align-content: start; overflow: hidden; }
.af-stat__big {
  font-family: var(--af-display);
  font-size: 40px;
  font-weight: 700;
  letter-spacing: -0.04em;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.af-stat__big small {
  font-family: var(--af-font);
  font-size: 14px;
  font-weight: 700;
  color: var(--af-ink-2);
  letter-spacing: 0;
  margin-left: 8px;
}
.af-stat__delta { font-size: 13px; font-weight: 650; color: var(--af-ink-2); display: flex; align-items: center; gap: 6px; }
.af-stat__delta ion-icon { font-size: 16px; flex: none; }
.af-stat__delta--up { color: var(--af-success); }
.af-stat__delta--down { color: var(--af-danger); }
.af-stat__delta--warn { color: var(--af-amber-fg); }
.af-stat:has(.af-stat__delta--warn) { border-color: color-mix(in srgb, var(--af-amber) 45%, var(--af-line)); }

@media (max-width: 560px) {
  .af-stat__big { font-size: 34px; }
  .af-stat__big small { display: block; margin: 6px 0 0; }
}
</style>
