<!--
  QuantityStepper — big − / number / + control, easy to tap with a thumb.
  Usage: <QuantityStepper v-model="qty" :min="1" :max="10" label="Containers" />
-->
<script setup>
import { IonIcon } from '@ionic/vue'
import { addOutline, removeOutline } from 'ionicons/icons'

const props = defineProps({
  modelValue: { type: Number, required: true },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 99 },
  label: { type: String, required: true },
  unit: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

function change(step) {
  const next = Math.min(props.max, Math.max(props.min, props.modelValue + step))
  emit('update:modelValue', next)
}
</script>

<template>
  <div class="af-step" role="group" :aria-label="label">
    <button type="button" class="af-step__btn" :disabled="modelValue <= min" :aria-label="`Decrease ${label}`" @click="change(-1)">
      <ion-icon :icon="removeOutline" aria-hidden="true" />
    </button>
    <output class="af-step__value" aria-live="polite">
      {{ modelValue }}<small v-if="unit">{{ unit }}</small>
    </output>
    <button type="button" class="af-step__btn" :disabled="modelValue >= max" :aria-label="`Increase ${label}`" @click="change(1)">
      <ion-icon :icon="addOutline" aria-hidden="true" />
    </button>
  </div>
</template>

<style scoped>
.af-step { display: flex; align-items: center; gap: var(--af-s4); }
.af-step__btn {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: 1.5px solid var(--af-line-strong);
  background: var(--af-surface);
  color: var(--af-primary);
  display: grid;
  place-items: center;
  font-size: 24px;
  cursor: pointer;
  transition: background var(--af-dur) var(--af-ease), border-color var(--af-dur) var(--af-ease), transform var(--af-dur-1) var(--af-ease);
}
.af-step__btn:hover:not(:disabled) { background: var(--af-primary-tint); border-color: var(--af-primary); }
.af-step__btn:active:not(:disabled) { transform: scale(0.92); }
.af-step__btn:disabled { opacity: 0.35; cursor: not-allowed; }
.af-step__value {
  min-width: 84px;
  text-align: center;
  font-family: var(--af-display);
  font-size: 44px;
  font-weight: 700;
  letter-spacing: -0.04em;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.af-step__value small { display: block; margin-top: 8px; font-family: var(--af-mono); font-size: 10px; font-weight: 600; letter-spacing: 0.14em; color: var(--af-ink-2); text-transform: uppercase; }
</style>
