<!-- AquaFlow logo: a mint water drop with a light ripple, on deep water + name. -->
<script setup>
defineProps({
  size: { type: Number, default: 36 },
  showName: { type: Boolean, default: true },
  inverse: { type: Boolean, default: false }, // light text, for deep backgrounds
})
</script>

<template>
  <span class="af-logo" :class="{ 'af-logo--inverse': inverse }">
    <span class="af-logo__mark" :style="{ width: `${size}px`, height: `${size}px` }" aria-hidden="true">
      <svg :width="size * 0.6" :height="size * 0.6" viewBox="0 0 24 24" fill="none">
        <path d="M12 2.2c3.7 4.7 6.7 8.4 6.7 11.9a6.7 6.7 0 1 1-13.4 0C5.3 10.6 8.3 6.9 12 2.2Z" fill="#4FE0D2" />
        <path d="M6.4 14.6c1.7-1 3.2.9 5.6 0s4-1 5.6 0" stroke="#02121A" stroke-width="1.6" stroke-linecap="round" opacity=".55" />
        <path d="M9.3 9.6c.6-1 1.2-1.9 1.9-2.8" stroke="#FFFFFF" stroke-width="1.6" stroke-linecap="round" opacity=".8" />
      </svg>
    </span>
    <span v-if="showName" class="af-logo__name">AquaFlow</span>
  </span>
</template>

<style scoped>
.af-logo { display: inline-flex; align-items: center; gap: 10px; }
.af-logo__mark {
  display: grid;
  place-items: center;
  border-radius: 32%;
  background: radial-gradient(120% 120% at 30% 20%, #0f3a46 0%, #02121a 70%);
  box-shadow: inset 0 0 0 1px rgba(79, 224, 210, 0.22), 0 6px 18px rgba(2, 18, 26, 0.35);
  flex: none;
}
.af-logo__name { font-family: var(--af-display); font-weight: 600; font-size: 17px; letter-spacing: -0.02em; color: var(--af-ink); }
.af-logo--inverse .af-logo__name { color: var(--af-on-deep); }
</style>
