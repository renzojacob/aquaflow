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
  position: relative;
  font: 750 15px/1 var(--af-font);
  letter-spacing: 0.005em;
  border-radius: var(--af-r-pill);
  border: 1px solid transparent;
  min-height: 48px;
  padding: 0 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  white-space: nowrap;
  -webkit-tap-highlight-color: transparent;
  transition: background var(--af-dur) var(--af-ease), color var(--af-dur) var(--af-ease),
    border-color var(--af-dur) var(--af-ease), box-shadow var(--af-dur) var(--af-ease),
    transform var(--af-dur-1) var(--af-ease);
}
.af-btn:active:not(:disabled) { transform: scale(0.97); }
.af-btn:disabled { opacity: 0.5; cursor: not-allowed; box-shadow: none; }
.af-btn :deep(ion-icon) { font-size: 18px; }

/* Primary: liquid mint gradient with a light sweep on hover */
.af-btn--primary {
  --g1: #9bf6ec;
  --g2: #4fe0d2;
  --g3: #22b8c8;
  overflow: hidden;
  isolation: isolate;
  background: linear-gradient(135deg, var(--g1) 0%, var(--g2) 45%, var(--g3) 100%);
  color: var(--af-on-primary);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.55), inset 0 -2px 0 rgba(0, 0, 0, 0.12), var(--af-glow);
}
:root:not([data-theme='dark']) .af-btn--primary { --g1: #00796f; --g2: #007067; --g3: #005a62; box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.25), inset 0 -2px 0 rgba(0, 0, 0, 0.18), var(--af-glow); }
.af-btn--primary::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: -60%;
  width: 45%;
  z-index: -1;
  background: linear-gradient(100deg, transparent, rgba(255, 255, 255, 0.45), transparent);
  transform: skewX(-20deg) translateX(0);
  transition: transform 700ms var(--af-ease-out);
}
.af-btn--primary:hover:not(:disabled)::after { transform: skewX(-20deg) translateX(420%); }
.af-btn--primary:hover:not(:disabled) { filter: brightness(1.05); }
.af-btn--primary .af-btn__spin, .af-btn--primary :slotted(*) { position: relative; }
/* Small buttons repeat in lists: keep them calm, no glow */
.af-btn--sm.af-btn--primary { box-shadow: var(--af-shadow-1); }

/* Secondary: frosted glass */
.af-btn--secondary {
  background: var(--af-surface);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: inset 0 1px 0 var(--af-glass-edge);
  color: var(--af-ink);
  border-color: var(--af-line-strong);
}
.af-btn--secondary:hover:not(:disabled) { background: var(--af-surface-2); border-color: var(--af-primary); }

/* Ghost: text button with a soft hover */
.af-btn--ghost { background: transparent; color: var(--af-primary); padding: 0 14px; }
.af-btn--ghost:hover:not(:disabled) { background: var(--af-primary-tint); }

/* Danger: tinted, never loud */
.af-btn--danger { background: var(--af-danger-tint); color: var(--af-danger); border-color: color-mix(in srgb, var(--af-danger) 30%, transparent); }
.af-btn--danger:hover:not(:disabled) { border-color: var(--af-danger); }

.af-btn--sm { min-height: 44px; padding: 0 16px; font-size: 14px; }
.af-btn--lg { min-height: 56px; padding: 0 30px; font-size: 16px; }
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
