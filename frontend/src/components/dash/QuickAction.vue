<!--
  QuickAction — a big tappable shortcut (icon + what it does + one line of detail).
  Usage: <QuickAction :icon="addCircleOutline" title="Order water" detail="Arrives this afternoon" @click="go" />
-->
<script setup>
import { IonIcon } from '@ionic/vue'

defineProps({
  icon: { type: String, required: true },
  title: { type: String, required: true },
  detail: { type: String, default: '' },
  tone: { type: String, default: 'water' }, // water | sun | pearl
  primary: { type: Boolean, default: false },
})
</script>

<template>
  <button type="button" class="qa" :class="[`qa--${tone}`, { 'qa--primary': primary }]">
    <span class="qa__icon" aria-hidden="true"><ion-icon :icon="icon" /></span>
    <span class="qa__text">
      <b>{{ title }}</b>
      <span v-if="detail">{{ detail }}</span>
    </span>
  </button>
</template>

<style scoped>
.qa {
  --c: var(--af-primary);
  --t: var(--af-primary-tint);
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 76px;
  width: 100%;
  padding: 14px 16px;
  border-radius: 20px;
  border: 1px solid var(--af-line);
  background: var(--af-surface-2);
  color: var(--af-ink);
  font-family: var(--af-font);
  text-align: left;
  cursor: pointer;
  transition: border-color var(--af-dur) var(--af-ease), background var(--af-dur) var(--af-ease), transform var(--af-dur-1) var(--af-ease);
}
.qa--sun { --c: var(--af-sun); --t: var(--af-sun-tint); }
.qa--pearl { --c: var(--af-pearl); --t: var(--af-pearl-tint); }
.qa:hover { border-color: color-mix(in srgb, var(--c) 50%, var(--af-line)); background: var(--af-surface-3); }
.qa:active { transform: scale(0.98); }
.qa__icon { flex: none; width: 44px; height: 44px; display: grid; place-items: center; border-radius: 14px; background: var(--t); color: var(--c); font-size: 22px; }
.qa__text { display: grid; gap: 2px; min-width: 0; }
.qa__text b { font-size: 15px; font-weight: 800; }
.qa__text span { font-size: 13px; font-weight: 600; color: var(--af-ink-2); }

.qa--primary {
  border: 0;
  background: linear-gradient(135deg, var(--af-brand-g1) 0%, var(--af-brand-g2) 45%, var(--af-brand-g3) 100%);
  color: var(--af-on-brand);
  box-shadow: inset 0 1px 0 var(--af-btn-sheen-top), var(--af-glow);
}
.qa--primary .qa__icon { background: rgba(var(--af-on-brand-rgb), 0.14); color: var(--af-on-brand); }
.qa--primary .qa__text span { color: rgba(var(--af-on-brand-rgb), 0.82); }
.qa--primary:hover { filter: brightness(1.05); }
</style>
