<!--
  SegmentedControl — pick one of a few options (Active / Past, Light / Dark).
  Usage: <SegmentedControl v-model="scope" :options="[{ value: 'active', label: 'Active' }]" label="Show" />
-->
<script setup>
defineProps({
  modelValue: { type: [String, Number], required: true },
  options: { type: Array, required: true }, // [{ value, label, disabled? }]
  label: { type: String, required: true },  // read by screen readers
  block: { type: Boolean, default: false }, // stretch to full width
})
defineEmits(['update:modelValue'])
</script>

<template>
  <div class="af-seg" :class="{ 'af-seg--block': block }" role="radiogroup" :aria-label="label">
    <button
      v-for="o in options"
      :key="o.value"
      type="button"
      role="radio"
      :aria-checked="modelValue === o.value"
      :disabled="o.disabled"
      @click="$emit('update:modelValue', o.value)"
    >
      {{ o.label }}
    </button>
  </div>
</template>

<style scoped>
.af-seg {
  display: inline-flex;
  background: var(--af-surface-2);
  border: 1px solid var(--af-line);
  border-radius: var(--af-r-pill);
  padding: 4px;
  gap: 2px;
}
.af-seg--block { display: flex; width: 100%; }
.af-seg--block button { flex: 1; }
.af-seg button {
  font: 700 14px var(--af-font);
  color: var(--af-ink-2);
  background: transparent;
  border: 0;
  padding: 8px 16px;
  min-height: 40px;
  border-radius: var(--af-r-pill);
  cursor: pointer;
  transition: background var(--af-dur) var(--af-ease), color var(--af-dur) var(--af-ease), box-shadow var(--af-dur) var(--af-ease);
}
.af-seg button:hover:not(:disabled):not([aria-checked='true']) { color: var(--af-ink); }
.af-seg button[aria-checked='true'] { background: var(--af-primary); color: var(--af-on-primary); box-shadow: var(--af-shadow-1); }
.af-seg button:disabled { opacity: 0.45; cursor: not-allowed; }
</style>
