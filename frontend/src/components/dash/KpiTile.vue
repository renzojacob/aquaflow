<!--
  KpiTile — one number that matters, with what it means underneath.
  tone="sun" is for money (sales, spending); the number turns sunlit amber.
  Usage:
    <KpiTile label="Spent this month" :value="peso(270)" hint="3 deliveries" tone="sun" :icon="walletOutline" :spark="[...]" />
-->
<script setup>
import { IonIcon } from '@ionic/vue'
import Sparkline from '@/components/viz/Sparkline.vue'

defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  unit: { type: String, default: '' },
  hint: { type: String, default: '' },
  icon: { type: String, default: '' },
  tone: { type: String, default: 'water' },   // water | sun | pearl | warn | danger
  spark: { type: Array, default: () => [] },
})
</script>

<template>
  <div class="kpi" :class="`kpi--${tone}`">
    <div class="kpi__top">
      <span v-if="icon" class="kpi__icon" aria-hidden="true"><ion-icon :icon="icon" /></span>
      <span class="kpi__label">{{ label }}</span>
    </div>
    <div class="kpi__row">
      <span class="kpi__value">{{ value }}<small v-if="unit">{{ unit }}</small></span>
      <Sparkline v-if="spark.length > 1" :values="spark" :tone="tone === 'sun' ? 'sun' : tone === 'pearl' ? 'pearl' : 'water'" />
    </div>
    <p v-if="hint" class="kpi__hint">{{ hint }}</p>
    <slot />
  </div>
</template>

<style scoped>
.kpi {
  --c: var(--af-primary);
  --t: var(--af-primary-tint);
  position: relative;
  display: grid;
  gap: 10px;
  align-content: start;
  min-width: 0;
  padding: 18px 20px;
  border-radius: 22px;
  background: var(--af-surface);
  border: 1px solid var(--af-line);
  box-shadow: inset 0 1px 0 var(--af-glass-edge);
  backdrop-filter: var(--af-glass-blur);
  -webkit-backdrop-filter: var(--af-glass-blur);
}
.kpi--sun { --c: var(--af-sun); --t: var(--af-sun-tint); }
.kpi--pearl { --c: var(--af-pearl); --t: var(--af-pearl-tint); }
.kpi--warn { --c: var(--af-amber-fg); --t: var(--af-amber-tint); border-color: color-mix(in srgb, var(--af-amber) 40%, var(--af-line)); }
.kpi--danger { --c: var(--af-danger); --t: var(--af-danger-tint); }

.kpi__top { display: flex; align-items: center; gap: 10px; min-width: 0; }
.kpi__icon { flex: none; width: 32px; height: 32px; display: grid; place-items: center; border-radius: 10px; background: var(--t); color: var(--c); font-size: 17px; }
.kpi__label { font-size: 13.5px; font-weight: 700; color: var(--af-ink-2); line-height: 1.3; }
.kpi__row { display: flex; align-items: flex-end; justify-content: space-between; gap: 10px; min-width: 0; }
.kpi__value {
  font-family: var(--af-display);
  font-size: 30px;
  font-weight: 650;
  letter-spacing: -0.035em;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.kpi--sun .kpi__value, .kpi--pearl .kpi__value { color: var(--c); }
.kpi__value small { font-family: var(--af-font); font-size: 13px; font-weight: 700; letter-spacing: 0; color: var(--af-ink-2); margin-left: 6px; }
.kpi__hint { margin: 0; font-size: 13px; font-weight: 600; color: var(--af-ink-2); line-height: 1.4; }
.kpi--warn .kpi__hint, .kpi--danger .kpi__hint { color: var(--c); }

@media (max-width: 420px) {
  .kpi { padding: 16px; }
  .kpi__value { font-size: 26px; }
  .kpi :deep(.sp) { display: none; }
}
</style>
