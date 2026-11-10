<!--
  WaterArt — original inline-SVG illustrations in the theme's colors.
  kind: drop | waves | tricycle | jug (jug = the LiquidFill container)
  Decorative by default (aria-hidden). Gentle motion, still under reduced motion.
  Usage: <WaterArt kind="tricycle" :size="140" />
-->
<script setup>
import LiquidFill from './LiquidFill.vue'

defineProps({
  kind: { type: String, default: 'drop' },
  size: { type: Number, default: 140 },
})
</script>

<template>
  <span class="art" :class="`art--${kind}`" :style="{ width: `${size}px` }" aria-hidden="true">
    <!-- A single drop falling into a ring of ripples -->
    <svg v-if="kind === 'drop'" viewBox="0 0 140 140" :width="size" :height="size">
      <ellipse class="art__ripple art__ripple--1" cx="70" cy="112" rx="34" ry="8" />
      <ellipse class="art__ripple art__ripple--2" cx="70" cy="112" rx="20" ry="5" />
      <g class="art__drop">
        <path class="art__fill" d="M70 18c16 22 30 38 30 56a30 30 0 1 1-60 0c0-18 14-34 30-56Z" />
        <path class="art__shine" d="M56 70c0-8 3-16 9-24" />
        <circle class="art__shine-dot" cx="80" cy="84" r="4" />
      </g>
      <circle class="art__spark" cx="34" cy="50" r="2.5" />
      <circle class="art__spark art__spark--2" cx="108" cy="40" r="3" />
    </svg>

    <!-- Three layered waves with a sun / moon above -->
    <svg v-else-if="kind === 'waves'" viewBox="0 0 160 120" :width="size" :height="size * 0.75">
      <circle class="art__sun" cx="118" cy="38" r="16" />
      <g class="art__wave art__wave--1"><path d="M-20 76c20-12 40-12 60 0s40 12 60 0 40-12 60 0 40 12 60 0V120H-20Z" /></g>
      <g class="art__wave art__wave--2"><path d="M-20 88c20-12 40-12 60 0s40 12 60 0 40-12 60 0 40 12 60 0V120H-20Z" /></g>
      <g class="art__wave art__wave--3"><path d="M-20 100c20-12 40-12 60 0s40 12 60 0 40-12 60 0 40 12 60 0V120H-20Z" /></g>
    </svg>

    <!-- A delivery tricycle carrying containers, rolling on a wave -->
    <svg v-else-if="kind === 'tricycle'" viewBox="0 0 200 130" :width="size" :height="size * 0.65">
      <g class="art__road"><path d="M0 112c20-8 40-8 60 0s40 8 60 0 40-8 60 0 30 6 40 2" /></g>
      <g class="art__trike">
        <!-- sidecar box -->
        <rect class="art__box" x="22" y="56" width="74" height="40" rx="8" />
        <rect class="art__box-top" x="22" y="56" width="74" height="10" rx="5" />
        <!-- containers on the box -->
        <g class="art__jugs">
          <rect class="art__jug" x="30" y="30" width="16" height="26" rx="4" /><rect class="art__cap" x="34" y="25" width="8" height="6" rx="2" />
          <rect class="art__jug" x="50" y="30" width="16" height="26" rx="4" /><rect class="art__cap" x="54" y="25" width="8" height="6" rx="2" />
          <rect class="art__jug" x="70" y="30" width="16" height="26" rx="4" /><rect class="art__cap" x="74" y="25" width="8" height="6" rx="2" />
        </g>
        <!-- motorbike body -->
        <path class="art__frame" d="M100 92h30l12-22h18" />
        <path class="art__frame" d="M130 92l8-30h18M126 60h22" />
        <rect class="art__seat" x="116" y="66" width="22" height="7" rx="3.5" />
        <!-- rider -->
        <circle class="art__head" cx="152" cy="46" r="8" />
        <path class="art__body" d="M152 54c-10 0-16 8-18 18h22l6-10" />
        <!-- wheels -->
        <g class="art__wheel"><circle cx="46" cy="100" r="13" /><circle cx="46" cy="100" r="4" /></g>
        <g class="art__wheel"><circle cx="128" cy="100" r="13" /><circle cx="128" cy="100" r="4" /></g>
        <g class="art__wheel"><circle cx="172" cy="100" r="13" /><circle cx="172" cy="100" r="4" /></g>
      </g>
      <circle class="art__spark" cx="20" cy="40" r="2.5" />
      <circle class="art__spark art__spark--2" cx="188" cy="28" r="3" />
    </svg>

    <LiquidFill v-else shape="jug" :level="0.14" :size="Math.round(size * 0.56)" />
  </span>
</template>

<style scoped>
.art { display: inline-grid; place-items: center; color: var(--af-liquid); }
.art svg { display: block; overflow: visible; }

/* shared */
.art__fill { fill: url(#none), var(--af-liquid); fill: var(--af-liquid); }
.art__shine { fill: none; stroke: var(--af-liquid-hi); stroke-width: 3; stroke-linecap: round; opacity: 0.9; }
.art__shine-dot { fill: var(--af-liquid-hi); opacity: 0.8; }
.art__spark { fill: var(--af-accent); opacity: 0.8; animation: art-twinkle 3s ease-in-out infinite; }
.art__spark--2 { animation-delay: -1.4s; }
@keyframes art-twinkle { 50% { opacity: 0.2; transform: scale(0.6); } }
.art__spark { transform-box: fill-box; transform-origin: center; }

/* drop */
.art__drop { transform-box: fill-box; transform-origin: center; animation: art-bob 4s ease-in-out infinite; filter: drop-shadow(0 10px 14px color-mix(in srgb, var(--af-liquid) 35%, transparent)); }
.art__ripple { fill: none; stroke: var(--af-liquid); stroke-width: 2; opacity: 0; transform-box: fill-box; transform-origin: center; animation: art-ripple 3s var(--af-ease-out) infinite; }
.art__ripple--2 { animation-delay: 1.5s; }
@keyframes art-bob { 50% { transform: translateY(-8px); } }
@keyframes art-ripple { 0% { opacity: 0.7; transform: scale(0.4); } 100% { opacity: 0; transform: scale(1.3); } }

/* waves */
.art__sun { fill: var(--af-sun-glow); opacity: 0.9; filter: drop-shadow(0 0 14px var(--af-sun-glow)); }
.art__wave path { fill: var(--af-liquid); }
.art__wave--1 path { opacity: 0.35; }
.art__wave--2 path { opacity: 0.6; }
.art__wave--3 path { fill: var(--af-liquid-deep); }
.art__wave { animation: art-slide 7s linear infinite; }
.art__wave--2 { animation-duration: 5s; animation-direction: reverse; }
.art__wave--3 { animation-duration: 9s; }
@keyframes art-slide { to { transform: translateX(-40px); } }

/* tricycle */
.art__road path { fill: none; stroke: var(--af-liquid); stroke-width: 3; stroke-linecap: round; opacity: 0.5; stroke-dasharray: 8 10; animation: art-road 1.6s linear infinite; }
@keyframes art-road { to { stroke-dashoffset: -18; } }
.art__trike { animation: art-bump 1.2s ease-in-out infinite; }
@keyframes art-bump { 50% { transform: translateY(-2px); } }
.art__box { fill: var(--af-brand); }
.art__box-top { fill: var(--af-brand-hover); }
.art__jug { fill: var(--af-liquid); stroke: var(--af-liquid-hi); stroke-width: 1.5; }
.art__cap { fill: var(--af-deep); }
.art__frame { fill: none; stroke: var(--af-ink); stroke-width: 4; stroke-linecap: round; stroke-linejoin: round; }
.art__seat { fill: var(--af-ink); }
.art__head { fill: var(--af-sun-glow); }
.art__body { fill: none; stroke: var(--af-accent); stroke-width: 6; stroke-linecap: round; stroke-linejoin: round; }
.art__wheel circle:first-child { fill: var(--af-surface-solid); stroke: var(--af-ink); stroke-width: 4; }
.art__wheel circle:last-child { fill: var(--af-ink); }
.art__wheel { transform-box: fill-box; transform-origin: center; animation: art-spin 1.4s linear infinite; }
@keyframes art-spin { to { transform: rotate(360deg); } }

@media (prefers-reduced-motion: reduce) {
  .art * { animation: none !important; }
  .art__ripple { opacity: 0.5; transform: none; }
}
</style>
