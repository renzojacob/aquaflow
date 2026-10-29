<!--
  LiquidFill — real-looking water inside a container: two moving waves, rising bubbles,
  a glass shine. The water level glides when the value changes.
  Shapes:
    jug = a 5-gallon water container (AquaFlow's hero object)
    orb = a round glass (compact badges, stock tank)
  Usage:
    <LiquidFill :level="0.66" shape="jug" :size="160" label="Order progress: step 4 of 6" />
    <LiquidFill :level="qty / 10" shape="orb" :size="44" :text="qty" />
  level is 0..1 (values outside are clamped). If label is empty the picture is decorative.
-->
<script setup>
import { computed, useId } from 'vue'

const props = defineProps({
  level: { type: Number, default: 0.5 },
  shape: { type: String, default: 'jug' }, // jug | orb
  size: { type: Number, default: 120 },    // width in px
  label: { type: String, default: '' },    // for screen readers
  text: { type: [String, Number], default: '' }, // number shown on top (orb only)
  tone: { type: String, default: 'water' }, // water | warn | danger
  still: { type: Boolean, default: false }, // no waves/bubbles moving
})

const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '')
const ids = { clip: `lf-c-${uid}`, water: `lf-w-${uid}`, glass: `lf-g-${uid}`, shine: `lf-s-${uid}` }

const isJug = computed(() => props.shape === 'jug')
const vb = computed(() => (isJug.value ? { w: 120, h: 170 } : { w: 120, h: 120 }))
const height = computed(() => Math.round((props.size * vb.value.h) / vb.value.w))

// Where water can be: jug body from y=36 to 164, orb from 6 to 114
const range = computed(() => (isJug.value ? [34, 164] : [6, 114]))
const clamped = computed(() => Math.min(1, Math.max(0, props.level)))
const surfaceY = computed(() => {
  const [top, bottom] = range.value
  // keep a sliver of water visible at 0 and a little air at 1, so it always reads as water
  return bottom - (0.04 + clamped.value * 0.9) * (bottom - top)
})

// A long sine wave; we slide it sideways so it looks like moving water
function wave(amp, len) {
  let d = `M-240 0`
  for (let x = -240; x < 360; x += len) {
    d += ` q${len / 4} ${-amp} ${len / 2} 0 t${len / 2} 0`
  }
  return `${d} V220 H-240 Z`
}
const backWave = wave(4, 56)
const frontWave = wave(5.5, 72)

// A 5-gallon container: narrow neck, sloped shoulders, wide round body
const JUG_BODY = 'M45 30 H75 Q79 30 81 33 L97 48 Q112 57 112 74 V146 Q112 164 94 164 H26 Q8 164 8 146 V74 Q8 57 23 48 L39 33 Q41 30 45 30 Z'

const bubbles = [
  { x: 30, r: 2.4, d: 3.4, w: 0 },
  { x: 52, r: 1.6, d: 2.8, w: 1.1 },
  { x: 74, r: 2.8, d: 4.1, w: 2.0 },
  { x: 92, r: 1.4, d: 3.0, w: 0.6 },
  { x: 62, r: 1.2, d: 2.4, w: 1.7 },
]
</script>

<template>
  <svg
    class="af-lf"
    :class="[`af-lf--${tone}`, { 'af-lf--still': still }]"
    :width="size"
    :height="height"
    :viewBox="`0 0 ${vb.w} ${vb.h}`"
    :role="label ? 'img' : undefined"
    :aria-label="label || undefined"
    :aria-hidden="label ? undefined : 'true'"
    focusable="false"
  >
    <defs>
      <clipPath :id="ids.clip">
        <path v-if="isJug" :d="JUG_BODY" />
        <circle v-else cx="60" cy="60" r="54" />
      </clipPath>
      <linearGradient :id="ids.water" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" class="af-lf__w1" />
        <stop offset="0.55" class="af-lf__w2" />
        <stop offset="1" class="af-lf__w3" />
      </linearGradient>
      <linearGradient :id="ids.glass" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#ffffff" stop-opacity=".22" />
        <stop offset="1" stop-color="#ffffff" stop-opacity=".04" />
      </linearGradient>
      <linearGradient :id="ids.shine" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="#ffffff" stop-opacity="0" />
        <stop offset=".5" stop-color="#ffffff" stop-opacity=".55" />
        <stop offset="1" stop-color="#ffffff" stop-opacity="0" />
      </linearGradient>
    </defs>

    <!-- soft glow on the floor under the container -->
    <ellipse v-if="isJug" class="af-lf__floor" cx="60" cy="166" rx="46" ry="4" />

    <!-- cap + neck (jug only) -->
    <template v-if="isJug">
      <rect x="44" y="16" width="32" height="16" rx="3" class="af-lf__glass af-lf__neck" :fill="`url(#${ids.glass})`" />
      <rect x="40" y="2" width="40" height="16" rx="6" class="af-lf__cap" />
      <rect x="40" y="13" width="40" height="5" rx="2.5" class="af-lf__cap af-lf__cap--ring" />
    </template>

    <!-- empty glass body -->
    <path v-if="isJug" :d="JUG_BODY" class="af-lf__glass" :fill="`url(#${ids.glass})`" />
    <circle v-else cx="60" cy="60" r="54" class="af-lf__glass" :fill="`url(#${ids.glass})`" />

    <!-- the water -->
    <g :clip-path="`url(#${ids.clip})`">
      <g class="af-lf__level" :style="{ transform: `translateY(${surfaceY}px)` }">
        <path class="af-lf__wave af-lf__wave--back" :d="backWave" :fill="`url(#${ids.water})`" />
        <path class="af-lf__wave af-lf__wave--front" :d="frontWave" :fill="`url(#${ids.water})`" />
        <circle
          v-for="(b, i) in bubbles"
          :key="i"
          class="af-lf__bubble"
          :cx="b.x"
          :cy="isJug ? 140 : 100"
          :r="b.r"
          :style="{ animationDuration: `${b.d}s`, animationDelay: `-${b.w}s` }"
        />
      </g>
      <!-- ridges of a real 5-gallon container -->
      <template v-if="isJug">
        <path d="M8 104 H112 M8 130 H112" class="af-lf__ridge" />
      </template>
    </g>

    <!-- glass outline + vertical shine -->
    <path v-if="isJug" :d="JUG_BODY" class="af-lf__edge" />
    <circle v-else cx="60" cy="60" r="54" class="af-lf__edge" />
    <rect v-if="isJug" x="17" y="66" width="10" height="80" rx="5" :fill="`url(#${ids.shine})`" class="af-lf__shine" />
    <path v-else d="M24 46 A40 40 0 0 1 46 22" class="af-lf__orbshine" />

    <text v-if="text !== '' && !isJug" x="60" y="60" class="af-lf__text" text-anchor="middle" dominant-baseline="central">{{ text }}</text>
  </svg>
</template>

<style scoped>
.af-lf { overflow: visible; flex: none; }

/* Water colors per tone and theme */
.af-lf { --w1: #8ff7ec; --w2: #3fd6cf; --w3: #0f8ea0; --edge: rgba(190, 255, 248, 0.55); --cap: #1aa6b5; }
:root:not([data-theme='dark']) .af-lf { --w1: #6eeadf; --w2: #22b8c0; --w3: #087a85; --edge: rgba(6, 36, 43, 0.28); --cap: #007067; }
.af-lf--warn { --w1: #ffe0a8; --w2: #ffb454; --w3: #c47a12; }
.af-lf--danger { --w1: #ffc2b8; --w2: #ff8a7a; --w3: #b42318; }
.af-lf__w1 { stop-color: var(--w1); }
.af-lf__w2 { stop-color: var(--w2); }
.af-lf__w3 { stop-color: var(--w3); }

.af-lf__glass { stroke: none; }
.af-lf__edge { fill: none; stroke: var(--edge); stroke-width: 2; }
.af-lf__cap { fill: var(--cap); }
.af-lf__cap--ring { opacity: 1; fill: color-mix(in srgb, var(--cap) 70%, #000); }
.af-lf__neck { stroke: var(--edge); stroke-width: 1.5; }
.af-lf__floor { fill: var(--w2); opacity: 0.25; filter: blur(4px); }
.af-lf__ridge { fill: none; stroke: #ffffff; stroke-opacity: 0.16; stroke-width: 2; }
.af-lf__shine { opacity: 0.8; }
.af-lf__orbshine { fill: none; stroke: #ffffff; stroke-opacity: 0.55; stroke-width: 5; stroke-linecap: round; }
.af-lf__text { font-family: var(--af-display); font-weight: 700; font-size: 44px; fill: #ffffff; paint-order: stroke; stroke: rgba(2, 18, 26, 0.35); stroke-width: 4px; }
:root:not([data-theme='dark']) .af-lf__text { fill: #03262c; stroke: rgba(255, 255, 255, 0.6); }

/* Level glides to its new height */
.af-lf__level { transition: transform 900ms var(--af-ease-out); }

/* Waves slide sideways at different speeds = real-looking water */
.af-lf__wave--back { opacity: 0.55; animation: af-lf-wave 4.2s linear infinite reverse; }
.af-lf__wave--front { animation: af-lf-wave2 3s linear infinite; }
@keyframes af-lf-wave { to { transform: translateX(56px); } }
@keyframes af-lf-wave2 { to { transform: translateX(72px); } }

/* Bubbles rise to the surface and pop */
.af-lf__bubble { fill: #ffffff; fill-opacity: 0.7; animation: af-lf-bubble 3s ease-in infinite; }
@keyframes af-lf-bubble {
  0% { transform: translateY(0); opacity: 0; }
  15% { opacity: 0.9; }
  90% { opacity: 0.7; }
  100% { transform: translateY(-130px); opacity: 0; }
}

.af-lf--still .af-lf__wave, .af-lf--still .af-lf__bubble { animation: none; }
.af-lf--still .af-lf__bubble { display: none; }
</style>
