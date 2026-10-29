<!--
  SkeletonList — grey shimmering rows shown while a list loads.
  We never show a blank screen with only a spinner.
  Usage: <SkeletonList :rows="5" />
-->
<script setup>
defineProps({
  rows: { type: Number, default: 4 },
  avatar: { type: Boolean, default: true },
})

// Slightly different line widths so it looks like real content
const widths = [
  ['72%', '45%'],
  ['60%', '35%'],
  ['78%', '52%'],
  ['55%', '40%'],
]
</script>

<template>
  <div class="af-sk" role="status" aria-busy="true">
    <span class="af-sr-only">Loading…</span>
    <div v-for="i in rows" :key="i" class="af-sk__item" :class="{ 'af-sk__item--noavatar': !avatar }">
      <div v-if="avatar" class="af-sk__b af-sk__avatar"></div>
      <div class="af-sk__lines">
        <div class="af-sk__b" :style="{ height: '14px', width: widths[(i - 1) % 4][0] }"></div>
        <div class="af-sk__b" :style="{ height: '12px', width: widths[(i - 1) % 4][1] }"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.af-sk { display: grid; gap: var(--af-s4); }
.af-sk__item { display: grid; grid-template-columns: 44px 1fr; gap: var(--af-s3); align-items: center; }
.af-sk__item--noavatar { grid-template-columns: 1fr; }
.af-sk__avatar { width: 44px; height: 44px; border-radius: var(--af-r-sm); }
.af-sk__lines { display: grid; gap: 10px; }
.af-sk__b {
  border-radius: 8px;
  background: linear-gradient(
    100deg,
    var(--af-surface-2) 0%,
    var(--af-surface-2) 35%,
    color-mix(in srgb, var(--af-primary) 14%, var(--af-surface-2)) 50%,
    var(--af-surface-2) 65%,
    var(--af-surface-2) 100%
  );
  background-size: 250% 100%;
  animation: af-shimmer 1.6s ease-in-out infinite;
}
@keyframes af-shimmer {
  0% { background-position: 100% 0; }
  100% { background-position: -50% 0; }
}
</style>
