<!--
  AppButton — the only button style in the app.
  Usage: <AppButton variant="primary" size="lg" :loading="saving" @click="save">Save</AppButton>
  Extra attributes (like @click, aria-label) pass straight to the <button>.
-->
<script setup>
const props = defineProps({
  variant: { type: String, default: 'primary' }, // primary | secondary | ghost | danger
  size: { type: String, default: 'md' },         // sm | md | lg
  block: { type: Boolean, default: false },      // full width
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  type: { type: String, default: 'button' },
})
</script>

<template>
  <button
    :type="props.type"
    class="af-btn"
    :class="[`af-btn--${props.variant}`, `af-btn--${props.size}`, { 'af-btn--block': props.block }]"
    :disabled="props.disabled || props.loading"
    :aria-busy="props.loading || undefined"
  >
    <span v-if="props.loading" class="af-btn__spin" aria-hidden="true"></span>
    <slot />
  </button>
</template>

<style scoped>
.af-btn {
  font: 700 15px/1 var(--af-font);
  border-radius: var(--af-r-sm);
  border: 1px solid transparent;
  min-height: 48px;
  padding: 0 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  white-space: nowrap;
  transition: background var(--af-dur) var(--af-ease), transform 120ms var(--af-ease),
    box-shadow var(--af-dur) var(--af-ease);
}
.af-btn:active:not(:disabled) { transform: scale(0.98); }
.af-btn:disabled { opacity: 0.55; cursor: not-allowed; }

.af-btn--primary { background: var(--af-primary); color: var(--af-on-primary); box-shadow: var(--af-shadow-1); }
.af-btn--primary:hover:not(:disabled) { background: var(--af-primary-hover); }
.af-btn--secondary { background: var(--af-surface); color: var(--af-ink); border-color: var(--af-line); }
.af-btn--secondary:hover:not(:disabled) { background: var(--af-surface-2); }
.af-btn--ghost { background: transparent; color: var(--af-primary); }
.af-btn--ghost:hover:not(:disabled) { background: var(--af-primary-tint); }
.af-btn--danger { background: var(--af-danger-tint); color: var(--af-danger); }

.af-btn--sm { min-height: 44px; padding: 0 14px; font-size: 14px; border-radius: 10px; }
.af-btn--lg { min-height: 56px; padding: 0 28px; font-size: 16px; border-radius: var(--af-r-md); }
.af-btn--block { width: 100%; }

.af-btn__spin {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid currentColor;
  border-right-color: transparent;
  animation: af-rot 0.8s linear infinite;
}
@keyframes af-rot { to { transform: rotate(360deg); } }
</style>