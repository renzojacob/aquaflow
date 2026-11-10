<!--
  Shared frame for Login, Register and Forgot password screens.
  The signature scene: a gradient mesh that breathes, light rays and a caustic net from the
  backdrop, three layered waves rolling at the horizon, and a glowing 5-gallon container
  floating above them. Every color is a theme token, so Ocean, Forest and Sunset each get
  their own sky. The form sits on a frosted-glass panel.
  Phone: scene on top, glass sheet below. Desktop (>= 992px): scene fills the screen,
  glass panel floats on the right.
-->
<script setup>
import { IonContent, IonPage } from '@ionic/vue'
import AppLogo from '@/components/ui/AppLogo.vue'
import LiquidFill from '@/components/ui/LiquidFill.vue'
import OceanBackdrop from '@/components/ui/OceanBackdrop.vue'

defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
})
</script>

<template>
  <ion-page>
    <ion-content>
      <div class="af-auth">
        <OceanBackdrop intense />
        <!-- gradient mesh: three soft lights that drift -->
        <div class="af-auth__mesh" aria-hidden="true"><i></i><i></i><i></i></div>
        <!-- the horizon: three waves -->
        <svg class="af-auth__waves" viewBox="0 0 1440 320" preserveAspectRatio="none" aria-hidden="true">
          <path class="w w1" d="M0 160c120-40 240-40 360 0s240 40 360 0 240-40 360 0 240 40 360 0 120-20 240-20V320H0Z" />
          <path class="w w2" d="M0 200c120-40 240-40 360 0s240 40 360 0 240-40 360 0 240 40 360 0 120-20 240-20V320H0Z" />
          <path class="w w3" d="M0 240c120-40 240-40 360 0s240 40 360 0 240-40 360 0 240 40 360 0 120-20 240-20V320H0Z" />
        </svg>

        <!-- Brand scene (decoration only; the form below has its own title) -->
        <section class="af-auth__brand" aria-hidden="true">
          <AppLogo :size="40" class="af-auth__logo" />

          <div class="af-auth__stage">
            <div class="af-auth__pitch">
              <p class="af-auth__eyebrow af-eyebrow">Water refills for Calapan City</p>
              <p class="af-auth__big af-shimmer">Water before you run out.</p>
              <p class="af-auth__small">Order 5-gallon refills in seconds. Watch your rider come to you. Pay cash at your door.</p>
            </div>
            <div class="af-auth__jug">
              <span class="af-auth__halo"></span>
              <LiquidFill :level="0.72" shape="jug" :size="120" class="af-auth__jugsvg" />
              <span class="af-auth__ripple"></span>
              <span class="af-auth__ripple af-auth__ripple--2"></span>
            </div>
          </div>

          <ul class="af-auth__facts">
            <li><b>2×</b><span>deliveries a day</span></li>
            <li><b>8 km</b><span>service area</span></li>
            <li><b>Live</b><span>rider tracking</span></li>
          </ul>
        </section>

        <!-- Form on frosted glass -->
        <section class="af-auth__panel">
          <div class="af-auth__inner af-glow-edge">
            <header>
              <h1 class="af-auth__title">{{ title }}</h1>
              <p v-if="subtitle" class="af-auth__sub">{{ subtitle }}</p>
            </header>
            <slot />
          </div>
        </section>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.af-auth {
  position: relative;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  isolation: isolate;
}

/* ---------- Gradient mesh ---------- */
.af-auth__mesh { position: absolute; inset: 0; z-index: 0; pointer-events: none; filter: blur(40px) saturate(130%); opacity: 0.9; }
.af-auth__mesh i { position: absolute; border-radius: 50%; width: 60vmax; height: 60vmax; will-change: transform; }
.af-auth__mesh i:nth-child(1) { left: -20vmax; top: -25vmax; background: radial-gradient(closest-side, rgba(var(--af-brand-rgb), 0.45), transparent); animation: af-mesh-a 22s ease-in-out infinite alternate; }
.af-auth__mesh i:nth-child(2) { right: -25vmax; top: -10vmax; background: radial-gradient(closest-side, rgba(var(--af-accent-rgb), 0.38), transparent); animation: af-mesh-b 26s ease-in-out infinite alternate; }
.af-auth__mesh i:nth-child(3) { left: 10vmax; bottom: -35vmax; background: radial-gradient(closest-side, rgba(var(--af-liquid-rgb), 0.4), transparent); animation: af-mesh-a 30s ease-in-out infinite alternate-reverse; }
@keyframes af-mesh-a { to { transform: translate(10vmax, 8vmax) scale(1.15); } }
@keyframes af-mesh-b { to { transform: translate(-12vmax, 10vmax) scale(0.9); } }

/* ---------- Waves at the horizon ---------- */
.af-auth__waves { position: absolute; left: -10%; right: -10%; bottom: -2px; width: 120%; height: 34%; z-index: 0; pointer-events: none; }
.af-auth__waves .w { fill: var(--af-liquid); transform-origin: center bottom; }
.af-auth__waves .w1 { opacity: 0.16; animation: af-wave-x 14s ease-in-out infinite alternate; }
.af-auth__waves .w2 { opacity: 0.26; animation: af-wave-x 10s ease-in-out infinite alternate-reverse; }
.af-auth__waves .w3 { fill: var(--af-liquid-deep); opacity: 0.42; animation: af-wave-x 8s ease-in-out infinite alternate; }
@keyframes af-wave-x { to { transform: translateX(-6%); } }

/* ---------- Brand scene ---------- */
.af-auth__brand {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: var(--af-s5);
  padding: calc(var(--af-s5) + env(safe-area-inset-top, 0px)) var(--af-s5) var(--af-s5);
}
.af-auth__logo { animation: af-in var(--af-dur-3) var(--af-ease-out) both; }
.af-auth__stage { display: flex; align-items: center; justify-content: space-between; gap: var(--af-s3); }
.af-auth__pitch { min-width: 0; animation: af-in 600ms var(--af-ease-out) 80ms both; }
.af-auth__eyebrow { display: none; margin: 0 0 var(--af-s4); }
.af-auth__big {
  margin: 0;
  font-family: var(--af-display);
  font-size: 32px;
  line-height: 1.02;
  font-weight: 700;
  letter-spacing: -0.04em;
  text-wrap: balance;
}
.af-auth__small { display: none; margin: var(--af-s5) 0 0; color: var(--af-ink-2); font-size: 18px; line-height: 1.6; max-width: 400px; }

/* The floating container */
.af-auth__jug { position: relative; flex: none; display: grid; place-items: center; width: 96px; animation: af-in 700ms var(--af-ease-out) 160ms both; }
.af-auth__jugsvg { width: 84px; height: auto; position: relative; z-index: 1; animation: af-float 6s ease-in-out infinite; filter: drop-shadow(0 18px 30px rgba(var(--af-deep-rgb), 0.45)) drop-shadow(0 0 22px rgba(var(--af-liquid-rgb), 0.45)); }
.af-auth__halo {
  position: absolute;
  inset: -30%;
  border-radius: 50%;
  background: radial-gradient(closest-side, rgba(var(--af-liquid-rgb), 0.38), transparent 70%);
  animation: af-pulse 6s ease-in-out infinite;
}
.af-auth__ripple {
  position: absolute;
  left: 50%;
  bottom: -6px;
  width: 120%;
  height: 22px;
  border-radius: 50%;
  border: 1.5px solid color-mix(in srgb, var(--af-liquid) 55%, transparent);
  transform: translateX(-50%) scale(0.5);
  opacity: 0;
  animation: af-ripple-out 4s var(--af-ease-out) infinite;
}
.af-auth__ripple--2 { animation-delay: 2s; }
@keyframes af-float { 0%, 100% { transform: translateY(0) rotate(-2deg); } 50% { transform: translateY(-10px) rotate(2deg); } }
@keyframes af-pulse { 0%, 100% { opacity: 0.6; transform: scale(0.95); } 50% { opacity: 1; transform: scale(1.05); } }
@keyframes af-ripple-out { 0% { opacity: 0.8; transform: translateX(-50%) scale(0.4); } 100% { opacity: 0; transform: translateX(-50%) scale(1.3); } }

.af-auth__facts { display: none; }

/* ---------- Glass form panel ---------- */
.af-auth__panel {
  position: relative;
  z-index: 1;
  flex: 1;
  display: grid;
  justify-items: center;
  align-content: start;
  padding: 0 var(--af-s3) calc(var(--af-s5) + env(safe-area-inset-bottom, 0px));
}
.af-auth__inner {
  position: relative;
  width: 100%;
  max-width: 460px;
  box-sizing: border-box;
  display: grid;
  gap: var(--af-s5);
  padding: var(--af-s6) var(--af-s5);
  border-radius: var(--af-r-lg);
  background:
    linear-gradient(180deg, var(--af-glass-sheen) 0%, transparent 30%),
    var(--af-surface);
  backdrop-filter: blur(28px) saturate(160%);
  -webkit-backdrop-filter: blur(28px) saturate(160%);
  box-shadow: inset 0 1px 0 var(--af-glass-edge), 0 40px 80px rgba(var(--af-deep-rgb), 0.35);
  animation: af-in 500ms var(--af-ease-out) 140ms both;
}
.af-auth__inner header { display: grid; gap: var(--af-s2); }
.af-auth__title { margin: 0; font-family: var(--af-display); font-size: 28px; line-height: 1.1; font-weight: 600; letter-spacing: -0.03em; }
.af-auth__sub { margin: 0; color: var(--af-ink-2); font-size: 15px; line-height: 1.5; }

@keyframes af-in {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: none; }
}

/* ---------- Desktop: cinematic split ---------- */
@media (min-width: 992px) {
  .af-auth { flex-direction: row; min-height: 100vh; }
  .af-auth__waves { height: 42%; }
  .af-auth__brand {
    flex: 1 1 56%;
    justify-content: space-between;
    padding: var(--af-s7) var(--af-s7) var(--af-s6);
  }
  .af-auth__stage { flex-direction: row; align-items: center; gap: var(--af-s6); }
  .af-auth__eyebrow, .af-auth__small { display: block; }
  .af-auth__big { font-size: clamp(52px, 5.4vw, 84px); }
  .af-auth__jug { width: clamp(180px, 18vw, 260px); }
  .af-auth__jugsvg { width: 100%; }
  .af-auth__ripple { bottom: -14px; height: 40px; }
  .af-auth__facts {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--af-s4);
    max-width: 560px;
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .af-auth__facts li {
    display: grid;
    gap: 4px;
    padding: var(--af-s4);
    border-radius: var(--af-r-md);
    background: var(--af-surface);
    border: 1px solid var(--af-line);
    box-shadow: inset 0 1px 0 var(--af-glass-edge);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
  }
  .af-auth__facts b { font-family: var(--af-display); font-size: 24px; font-weight: 600; color: var(--af-brand); letter-spacing: -0.02em; }
  .af-auth__facts span { font-size: 13px; color: var(--af-ink-2); }

  .af-auth__panel {
    flex: 0 0 auto;
    width: min(560px, 44vw);
    align-content: center;
    padding: var(--af-s6) var(--af-s6) var(--af-s6) 0;
  }
  .af-auth__inner { padding: var(--af-s7) var(--af-s6); }
  .af-auth__title { font-size: 34px; }
}

@media (prefers-reduced-motion: reduce) {
  .af-auth__mesh i, .af-auth__waves .w { animation: none; }
}
</style>
