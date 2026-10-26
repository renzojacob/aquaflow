<!-- AquaFlow logo: water-drop mark + name. -->
<script setup>
defineProps({
  size: { type: Number, default: 36 },
  showName: { type: Boolean, default: true },
  inverse: { type: Boolean, default: false }, // white text, for dark backgrounds
})
</script>

<template>
  <span class="af-logo" :class="{ 'af-logo--inverse': inverse }">
    <span class="af-logo__mark" :style="{ width: `${size}px`, height: `${size}px` }" aria-hidden="true">
      <svg :width="size * 0.56" :height="size * 0.56" viewBox="0 0 24 24" fill="none">
        <path d="M12 2.5c3.6 4.6 6.5 8.2 6.5 11.6a6.5 6.5 0 1 1-13 0C5.5 10.7 8.4 7.1 12 2.5Z" fill="#22B8C8" />
        <path d="M8.6 14.6c.5 1.7 1.9 2.8 3.6 2.9" stroke="#fff" stroke-width="1.8" stroke-linecap="round" />
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
  border-radius: 30%;
  background: var(--af-navy);
  flex: none;
}
.af-logo__name { font-weight: 800; font-size: 18px; letter-spacing: -0.01em; color: var(--af-ink); }
.af-logo--inverse .af-logo__name { color: #fff; }
</style>
