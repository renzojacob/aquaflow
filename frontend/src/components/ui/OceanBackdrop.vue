<!--
  OceanBackdrop — the living world behind every screen.
  Layers (back to front): depth gradient · drifting aurora light · rays from the surface ·
  caustic light net · rising particles · film grain.
  Everything is CSS gradients + inline SVG (no images), animated only with transform/opacity.
  Every color is a theme token (--af-bd-*, --af-aur-*, --af-ray, --af-particle), so the same
  scene reads as deep water (Ocean), a sunlit canopy (Forest) or a glowing horizon (Sunset).
  Turns still when the OS asks for reduced motion (global rule in global.css).
  Usage: <OceanBackdrop />  (fills its positioned parent)   <OceanBackdrop intense />  (login scene)
-->
<script setup>
import CausticLayer from './CausticLayer.vue'

defineProps({
  intense: { type: Boolean, default: false }, // stronger rays + more particles, for the login scene
})

// Fixed (not random) so the screen looks the same on every render
const particles = [
  { l: 6, s: 3, d: 19, w: 0 },
  { l: 14, s: 2, d: 23, w: 6 },
  { l: 22, s: 4, d: 17, w: 11 },
  { l: 31, s: 2, d: 25, w: 3 },
  { l: 39, s: 3, d: 21, w: 14 },
  { l: 47, s: 2, d: 27, w: 8 },
  { l: 55, s: 5, d: 18, w: 1 },
  { l: 63, s: 2, d: 24, w: 12 },
  { l: 70, s: 3, d: 20, w: 5 },
  { l: 78, s: 2, d: 26, w: 16 },
  { l: 86, s: 4, d: 22, w: 9 },
  { l: 93, s: 2, d: 28, w: 2 },
].map((p) => ({
  left: `${p.l}%`,
  width: `${p.s}px`,
  height: `${p.s}px`,
  animationDuration: `${p.d}s`,
  animationDelay: `-${p.w}s`,
}))
</script>

<template>
  <div class="af-ocean" :class="{ 'af-ocean--intense': intense }" aria-hidden="true">
    <div class="af-ocean__depth"></div>
    <div class="af-ocean__aurora af-ocean__aurora--1"></div>
    <div class="af-ocean__aurora af-ocean__aurora--2"></div>
    <div class="af-ocean__aurora af-ocean__aurora--3"></div>
    <div class="af-ocean__rays">
      <span></span><span></span><span></span><span></span><span></span>
    </div>
    <div class="af-ocean__net"><CausticLayer :strength="intense ? 1.1 : 0.55" /></div>
    <span v-for="(p, i) in particles" :key="i" class="af-ocean__p" :class="{ 'af-ocean__p--extra': i % 2 && !intense }" :style="p"></span>
    <div class="af-ocean__grain"></div>
  </div>
</template>

<style scoped>
.af-ocean {
  --ray: var(--af-ray);
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

/* 1. Depth: lighter near the surface, darker as we go down */
.af-ocean__depth {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(140% 70% at 50% -10%, var(--af-bd-glow) 0%, transparent 60%),
    linear-gradient(180deg, var(--af-bd-top) 0%, var(--af-bd-mid) 45%, var(--af-bd-bot) 100%);
}

/* 2. Aurora: big soft lights drifting slowly */
.af-ocean__aurora {
  position: absolute;
  width: 70vmax;
  height: 70vmax;
  border-radius: 50%;
  will-change: transform;
}
.af-ocean__aurora--1 { top: -30vmax; left: -20vmax; background: radial-gradient(closest-side, var(--af-aur-1), transparent); animation: af-aur-1 28s ease-in-out infinite alternate; }
.af-ocean__aurora--2 { top: 10vmax; right: -30vmax; background: radial-gradient(closest-side, var(--af-aur-2), transparent); animation: af-aur-2 34s ease-in-out infinite alternate; }
.af-ocean__aurora--3 { bottom: -40vmax; left: 10vmax; background: radial-gradient(closest-side, var(--af-aur-3), transparent); animation: af-aur-1 40s ease-in-out infinite alternate-reverse; }
@keyframes af-aur-1 { to { transform: translate(12vmax, 8vmax) scale(1.15); } }
@keyframes af-aur-2 { to { transform: translate(-10vmax, 6vmax) scale(0.9); } }

/* 3. Light rays falling from the surface */
.af-ocean__rays { position: absolute; inset: -10% -20% 20%; }
.af-ocean__rays span {
  position: absolute;
  top: 0;
  height: 100%;
  width: 9%;
  background: linear-gradient(180deg, var(--ray) 0%, transparent 85%);
  transform-origin: top center;
  animation: af-ray 11s ease-in-out infinite alternate;
}
.af-ocean__rays span:nth-child(1) { left: 12%; width: 6%; transform: rotate(14deg); animation-duration: 9s; }
.af-ocean__rays span:nth-child(2) { left: 30%; width: 11%; transform: rotate(10deg); animation-duration: 13s; animation-delay: -4s; }
.af-ocean__rays span:nth-child(3) { left: 50%; width: 5%; transform: rotate(6deg); animation-duration: 8s; animation-delay: -2s; }
.af-ocean__rays span:nth-child(4) { left: 64%; width: 12%; transform: rotate(2deg); animation-duration: 12s; animation-delay: -6s; }
.af-ocean__rays span:nth-child(5) { left: 84%; width: 7%; transform: rotate(-3deg); animation-duration: 10s; animation-delay: -1s; }
@keyframes af-ray {
  0% { opacity: 0.35; }
  100% { opacity: 1; }
}

/* 4. The caustic net, only near the top */
.af-ocean__net {
  position: absolute;
  inset: 0 0 45% 0;
  -webkit-mask: linear-gradient(180deg, #000 0%, transparent 100%);
  mask: linear-gradient(180deg, #000 0%, transparent 100%);
}

/* 5. Particles drifting up like tiny bubbles (or pollen, or embers) */
.af-ocean__p {
  position: absolute;
  bottom: -10px;
  border-radius: 50%;
  background: var(--af-particle);
  box-shadow: 0 0 6px var(--af-particle);
  opacity: 0;
  animation-name: af-rise-p;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
}
.af-ocean__p--extra { display: none; }
@keyframes af-rise-p {
  0% { transform: translate3d(0, 0, 0); opacity: 0; }
  10% { opacity: 0.7; }
  50% { transform: translate3d(14px, -55vh, 0); }
  90% { opacity: 0.4; }
  100% { transform: translate3d(-8px, -110vh, 0); opacity: 0; }
}

/* 6. Film grain: makes gradients feel rich instead of flat */
.af-ocean__grain {
  position: absolute;
  inset: 0;
  opacity: 0.07;
  mix-blend-mode: overlay;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

.af-ocean--intense .af-ocean__rays span { width: 12%; }
.af-ocean--intense { --ray: var(--af-ray-intense); }

/* ---------- Lighter backdrop: phones ---------- */
@media (max-width: 991px) {
  .af-ocean .af-ocean__rays {
    display: none;
  }
  .af-ocean .af-ocean__grain {
    display: none;
  }
  .af-ocean .af-ocean__aurora {
    animation: none;
    will-change: auto;
  }
  .af-ocean span.af-ocean__p:nth-of-type(n + 5) {
    display: none;
  }
  .af-ocean .af-ocean__net :deep(.af-caustic__glow) {
    display: none;
  }
  .af-ocean .af-ocean__net :deep(.af-caustic__net) {
    animation: none;
  }
}
</style>

<style>
/* ---------- Lighter backdrop: installed Android app (html.af-native) ----------
   The same lighter rules as the phone block above, for any screen width inside the app.
   A separate, unscoped block on purpose: :global() in a scoped block loses the descendant selectors. */
html.af-native .af-ocean .af-ocean__rays {
  display: none;
}
html.af-native .af-ocean .af-ocean__grain {
  display: none;
}
html.af-native .af-ocean .af-ocean__aurora {
  animation: none;
  will-change: auto;
}
html.af-native .af-ocean span.af-ocean__p:nth-of-type(n + 5) {
  display: none;
}
html.af-native .af-ocean .af-ocean__net .af-caustic__glow {
  display: none;
}
html.af-native .af-ocean .af-ocean__net .af-caustic__net {
  animation: none;
}
</style>
