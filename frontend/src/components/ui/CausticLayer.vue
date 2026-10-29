<!--
  CausticLayer — AquaFlow's signature: the net of light you see at the bottom of a pool.
  Put it inside any element with position: relative + overflow: hidden.
  Use it ONLY on hero surfaces (login panel, active-order card, empty states). Restraint is the point.
  Usage: <CausticLayer />   or   <CausticLayer :strength="0.6" still />
  - Pure inline SVG, no images. Drifts slowly with transform only (cheap on phones).
  - Stops moving when the OS asks for reduced motion (global rule in global.css).
-->
<script setup>
defineProps({
  strength: { type: Number, default: 1 }, // multiplies --af-caustic-opacity
  still: { type: Boolean, default: false }, // no drifting
})
</script>

<template>
  <svg
    class="af-caustic"
    :class="{ 'af-caustic--still': still }"
    :style="{ '--k': strength }"
    viewBox="0 0 400 400"
    preserveAspectRatio="xMidYMid slice"
    aria-hidden="true"
    focusable="false"
  >
    <!-- soft wide glow under the sharp lines -->
    <g class="af-caustic__glow">
      <path d="M-20 70 C40 34 84 112 140 70 S236 26 286 86 S374 124 430 64" />
      <path d="M-20 196 C50 160 104 232 168 186 S262 150 312 204 S384 232 430 186" />
      <path d="M-20 318 C60 290 112 350 176 308 S286 280 330 330 S396 348 430 312" />
    </g>
    <!-- the light net -->
    <g class="af-caustic__net">
      <path d="M-20 70 C40 34 84 112 140 70 S236 26 286 86 S374 124 430 64" />
      <path d="M-20 196 C50 160 104 232 168 186 S262 150 312 204 S384 232 430 186" />
      <path d="M-20 318 C60 290 112 350 176 308 S286 280 330 330 S396 348 430 312" />
      <path d="M72 -20 C44 40 112 86 84 146 S28 232 80 284 S118 376 90 420" />
      <path d="M214 -20 C186 56 262 92 232 160 S172 246 226 292 S256 380 236 420" />
      <path d="M346 -20 C318 48 380 104 352 164 S300 238 352 300 S378 384 360 420" />
      <path d="M120 120 C150 104 176 140 204 124" />
      <path d="M250 250 C282 236 300 270 330 252" />
      <path d="M40 252 C66 236 92 268 118 250" />
    </g>
  </svg>
</template>

<style scoped>
.af-caustic {
  position: absolute;
  inset: -8%;
  width: 116%;
  height: 116%;
  pointer-events: none;
  opacity: calc(var(--af-caustic-opacity) * var(--k, 1));
}
.af-caustic g { fill: none; stroke: var(--af-caustic); stroke-linecap: round; }
.af-caustic__glow { stroke-width: 14; opacity: 0.35; filter: blur(6px); animation: af-drift-a 26s ease-in-out infinite alternate; }
.af-caustic__net { stroke-width: 1.8; animation: af-drift-b 34s ease-in-out infinite alternate; }
.af-caustic--still g { animation: none; }

@keyframes af-drift-a {
  from { transform: translate(0, 0) scale(1); }
  to { transform: translate(-14px, 10px) scale(1.04); }
}
@keyframes af-drift-b {
  from { transform: translate(0, 0) rotate(0deg); }
  to { transform: translate(12px, -8px) rotate(1.5deg); }
}
</style>
