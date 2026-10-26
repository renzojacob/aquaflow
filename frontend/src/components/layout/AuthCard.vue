<!-- Shared frame for Login, Register and Forgot password screens. -->
<script setup>
import { IonContent, IonPage } from '@ionic/vue'
import AppLogo from '@/components/ui/AppLogo.vue'

defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
})
</script>

<template>
  <ion-page>
    <ion-content>
      <div class="af-auth">
        <!-- Brand panel (desktop) -->
        <section class="af-auth__brand" aria-hidden="true">
          <AppLogo inverse :size="40" />
          <div class="af-auth__pitch">
            <p class="af-auth__big">Water before you run out.</p>
            <p class="af-auth__small">Order 5-gallon refills in Calapan City. Track your rider. Pay cash on delivery.</p>
          </div>
          <svg class="af-auth__waves" viewBox="0 0 600 160" preserveAspectRatio="none">
            <path d="M0 60c75-30 150 30 225 0s150-30 225 0 112 22 150 10v90H0Z" fill="rgba(34,184,200,0.35)" />
            <path d="M0 95c80-26 160 26 240 0s160-26 240 0 90 18 120 8v57H0Z" fill="rgba(34,184,200,0.55)" />
          </svg>
        </section>

        <!-- Form panel -->
        <section class="af-auth__panel">
          <div class="af-auth__inner">
            <div class="af-auth__mobilelogo"><AppLogo :size="40" /></div>
            <header>
              <h1 class="af-h1">{{ title }}</h1>
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
.af-auth { min-height: 100%; display: grid; grid-template-columns: 1fr; background: var(--af-bg); }
.af-auth__brand {
  display: none;
  position: relative;
  overflow: hidden;
  padding: var(--af-s7);
  background: linear-gradient(160deg, #0f2a4a 0%, #0b2240 55%, #0a3a52 100%);
  color: #fff;
  flex-direction: column;
  justify-content: space-between;
}
.af-auth__pitch { position: relative; z-index: 1; max-width: 26ch; }
.af-auth__big { margin: 0 0 var(--af-s3); font-size: 44px; line-height: 1.05; font-weight: 800; letter-spacing: -0.03em; }
.af-auth__small { margin: 0; color: #b9c8da; font-size: 17px; line-height: 1.5; }
.af-auth__waves { position: absolute; left: 0; right: 0; bottom: 0; width: 100%; height: 160px; }

.af-auth__panel { display: grid; place-items: center; padding: var(--af-s6) var(--af-s4) var(--af-s7); }
.af-auth__inner { width: 100%; max-width: 420px; display: grid; gap: var(--af-s5); }
.af-auth__inner header { display: grid; gap: var(--af-s2); }
.af-auth__inner h1 { margin: 0; }
.af-auth__sub { margin: 0; color: var(--af-ink-2); font-size: 15px; }

@media (min-width: 992px) {
  .af-auth { grid-template-columns: minmax(380px, 5fr) 6fr; min-height: 100vh; }
  .af-auth__brand { display: flex; }
  .af-auth__mobilelogo { display: none; }
}
</style>
