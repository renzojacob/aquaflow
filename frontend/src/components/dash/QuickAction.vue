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
  background: linear-gradient(135deg, #9bf6ec 0%, #4fe0d2 45%, #22b8c8 100%);
  color: #022320;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.55), var(--af-glow);
}
.qa--primary .qa__icon { background: rgba(2, 35, 32, 0.12); color: #022320; }
.qa--primary .qa__text span { color: rgba(2, 35, 32, 0.78); }
.qa--primary:hover { background: linear-gradient(135deg, #b0f8f0 0%, #62e5d8 45%, #34c2d0 100%); }
:root:not([data-theme='dark']) .qa--primary { background: linear-gradient(135deg, #00796f 0%, #007067 45%, #005a62 100%); color: #ffffff; }
:root:not([data-theme='dark']) .qa--primary .qa__icon { background: rgba(255, 255, 255, 0.16); color: #ffffff; }
:root:not([data-theme='dark']) .qa--primary .qa__text span { color: rgba(255, 255, 255, 0.86); }
</style>
