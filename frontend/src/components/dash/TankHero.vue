<!--
  TankHero — AquaFlow's signature hero. The panel IS a water tank:
  the water rises to `level` (0..1) when the page opens, then rests with a slow wave.
  The level always means something real (order progress, today's work done, stock ready...).

  Usage:
    <TankHero :level="0.66" label="Order progress: 4 of 6 steps">
      <h1>...</h1>
    </TankHero>

  Text sits on deep water in BOTH themes (always light text). Contrast checked:
  #e6f4f6 on the water 6.4:1, .tank__soft (#cfe6ea) 5.6:1.
-->
<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import CausticLayer from '@/components/ui/CausticLayer.vue'

const props = defineProps({
  level: { type: Number, default: 0.5 },
  label: { type: String, default: '' },        // screen-reader meaning of the water level
  tone: { type: String, default: 'water' },    // water | sun (money) | warn
  compact: { type: Boolean, default: false },
  marks: { type: Boolean, default: true },     // the 25/50/75% ticks on the right edge
})

const shown = ref(0)
const clamped = computed(() => Math.min(1, Math.max(0, props.level)))

onMounted(() => {
  // one orchestrated moment: the water rises after the first paint
  requestAnimationFrame(() => requestAnimationFrame(() => (shown.value = clamped.value)))
})
watch(clamped, (v) => (shown.value = v))

// Keep a sliver of water at 0 and some air at 1, so it always reads as a tank
const height = computed(() => `${8 + shown.value * 78}%`)

// One period of a wave, repeated; we slide it by exactly one period so the loop is seamless
function wave(amp, len, width = 2400) {
  let d = `M0 ${amp}`
  for (let x = 0; x < width; x += len) d += ` q${len / 4} ${-amp} ${len / 2} 0 t${len / 2} 0`
  return `${d} V80 H0 Z`
}
const back = wave(9, 300)
const front = wave(7, 240)
</script>

<template>
  <section class="tank af-deep-scope" :class="[`tank--${tone}`, { 'tank--compact': compact }]">
    <div class="tank__sky" aria-hidden="true"></div>

    <div class="tank__water" :style="{ height }" :role="label ? 'img' : undefined" :aria-label="label || undefined">
      <svg class="tank__wave tank__wave--back" viewBox="0 0 1200 80" preserveAspectRatio="none" aria-hidden="true">
        <path :d="back" />
      </svg>
      <svg class="tank__wave tank__wave--front" viewBox="0 0 1200 80" preserveAspectRatio="none" aria-hidden="true">
        <path :d="front" />
      </svg>
      <div class="tank__body" aria-hidden="true">
        <CausticLayer :strength="0.9" />
        <span v-for="n in 6" :key="n" class="tank__bubble" :style="{ '--x': `${8 + n * 14}%`, '--d': `${5 + (n % 3) * 2}s`, '--w': `${n * 0.9}s` }"></span>
      </div>
    </div>

    <div v-if="marks" class="tank__marks" aria-hidden="true">
      <span style="--m: 0.25"></span><span style="--m: 0.5"></span><span style="--m: 0.75"></span>
    </div>

    <div class="tank__content">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.tank {
  --surface-a: rgba(108, 236, 222, 0.55);
  --water-top: #1d7f86;
  --water-bottom: #0b3d47;
  position: relative;
  isolation: isolate;
  overflow: hidden;
  min-height: 300px;
  border-radius: 32px;
  background:
    radial-gradient(70% 90% at 85% -10%, rgba(185, 180, 255, 0.22) 0%, transparent 60%),
    radial-gradient(60% 70% at 0% 0%, rgba(79, 224, 210, 0.16) 0%, transparent 55%),
    linear-gradient(180deg, #072a33 0%, #04161d 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.12),
    inset 0 0 0 1px rgba(159, 195, 201, 0.14),
    0 30px 80px -20px rgba(2, 18, 26, 0.6);
  color: #e6f4f6;
}
.tank--compact { min-height: 220px; border-radius: 28px; }
.tank--sun { --surface-a: rgba(255, 220, 150, 0.6); --water-top: #86601a; --water-bottom: #2e2208; } /* light text on #86601a: 5.0:1 */
.tank--warn { --surface-a: rgba(255, 190, 110, 0.5); --water-top: #7a4f1d; --water-bottom: #2e1c0a; }

/* light from above, refracting into soft pearl + seafoam */
.tank__sky {
  position: absolute;
  inset: 0;
  z-index: 0;
  background:
    linear-gradient(105deg, transparent 20%, rgba(255, 255, 255, 0.05) 32%, transparent 44%),
    linear-gradient(75deg, transparent 52%, rgba(185, 180, 255, 0.06) 60%, transparent 70%);
  pointer-events: none;
}

.tank__water {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1;
  height: 8%;
  transition: height 1600ms cubic-bezier(0.22, 1, 0.36, 1);
}
.tank__body {
  position: absolute;
  inset: 22px 0 0;
  overflow: hidden;
  background: linear-gradient(180deg, var(--water-top) 0%, var(--water-bottom) 100%);
}
.tank__body :deep(.af-caustic) { --af-caustic: #bffcf3; opacity: 0.16; }

.tank__wave { position: absolute; left: 0; top: 0; width: 200%; height: 30px; }
.tank__wave path { fill: var(--water-top); }
.tank__wave--back { top: -4px; opacity: 0.55; animation: tank-slide 14s linear infinite reverse; }
.tank__wave--back path { fill: color-mix(in srgb, var(--water-top) 70%, #7fe9df); }
.tank__wave--front { animation: tank-slide 9s linear infinite; filter: drop-shadow(0 -1px 0 var(--surface-a)); }
@keyframes tank-slide { to { transform: translateX(-50%); } }

.tank__bubble {
  position: absolute;
  left: var(--x);
  bottom: -10px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  border: 1px solid rgba(220, 255, 250, 0.55);
  background: rgba(220, 255, 250, 0.12);
  animation: tank-bubble var(--d) ease-in infinite;
  animation-delay: calc(var(--w) * -1);
}
@keyframes tank-bubble {
  0% { transform: translate(0, 0); opacity: 0; }
  15% { opacity: 1; }
  100% { transform: translate(10px, -260px); opacity: 0; }
}

.tank__marks { position: absolute; right: 18px; top: 0; bottom: 0; width: 14px; z-index: 2; pointer-events: none; }
.tank__marks span {
  position: absolute;
  right: 0;
  bottom: calc(8% + var(--m) * 78%);
  width: 14px;
  height: 1.5px;
  border-radius: 2px;
  background: rgba(230, 244, 246, 0.35);
}
.tank__marks span:nth-child(2) { width: 22px; }

.tank__content {
  position: relative;
  z-index: 3;
  height: 100%;
  padding: 28px;
  display: grid;
  gap: 18px;
  align-content: start;
}
.tank--compact .tank__content { padding: 22px; }
.tank__content :deep(.tank__soft) { color: #cfe6ea; }

@media (min-width: 768px) {
  .tank__content { padding: 36px 40px; }
  .tank--compact .tank__content { padding: 28px 32px; }
}

@media (prefers-reduced-motion: reduce) {
  .tank__water { transition: none; }
  .tank__wave, .tank__bubble { animation: none; }
  .tank__bubble { display: none; }
}
</style>
