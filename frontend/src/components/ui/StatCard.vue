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
.af-stat { display: grid; gap: var(--af-s2); align-content: start; }
.af-stat__big {
  font-size: 40px;
  font-weight: 800;
  letter-spacing: -0.03em;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.af-stat__big small {
  font-size: 16px;
  font-weight: 600;
  color: var(--af-ink-2);
  letter-spacing: 0;
  margin-left: 6px;
}
.af-stat__delta { font-size: 13px; font-weight: 600; color: var(--af-ink-2); display: flex; align-items: center; gap: 6px; }
.af-stat__delta ion-icon { font-size: 16px; }
.af-stat__delta--up { color: var(--af-success); }
.af-stat__delta--down { color: var(--af-danger); }
.af-stat__delta--warn { color: var(--af-amber-fg); }

@media (max-width: 560px) {
  .af-stat__big { font-size: 34px; }
}
</style>