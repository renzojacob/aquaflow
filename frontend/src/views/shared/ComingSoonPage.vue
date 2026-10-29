<!--
  Placeholder for screens built in later phases.
  The route's meta gives the title, phase number and what the screen will contain,
  so the whole app can be clicked through now.
-->
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { IonContent, IonHeader, IonPage, IonTitle, IonToolbar } from '@ionic/vue'

import CausticLayer from '@/components/ui/CausticLayer.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { ROLE_LABEL } from '@/config/navigation'

const route = useRoute()
const meta = computed(() => route.meta)
const role = computed(() => route.matched.find((r) => r.meta.role)?.meta.role)
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-title>{{ meta.title }}</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content>
      <div class="af-container narrow">
        <PageHeader :crumb="ROLE_LABEL[role]" :title="meta.title" :subtitle="`Built in Phase ${meta.phase}`" />
        <section class="soon af-deep-scope af-glow-edge">
          <CausticLayer />
          <svg width="64" height="76" viewBox="0 0 64 76" fill="none" aria-hidden="true">
            <rect x="24" y="2" width="16" height="9" rx="4" fill="var(--af-water-deep)" />
            <rect x="6" y="9" width="52" height="64" rx="18" fill="rgba(255,255,255,.06)" stroke="var(--af-line-strong)" stroke-width="2" />
            <path d="M7 54 C7 49 18 52 32 52 C46 52 57 49 57 54 L57 56 Q57 72 41 72 L23 72 Q7 72 7 56 Z" fill="var(--af-water)" />
            <path d="M7 54 C7 49 18 52 32 52 C46 52 57 49 57 54" stroke="#fff" stroke-opacity=".6" stroke-width="2" />
          </svg>
          <h2 class="af-h3">This screen is still being filled</h2>
          <p class="af-small">It will contain:</p>
          <ul>
            <li v-for="item in meta.planned" :key="item">{{ item }}</li>
          </ul>
        </section>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.narrow { max-width: 720px; }
.soon { position: relative; overflow: hidden; isolation: isolate; display: grid; gap: var(--af-s3); justify-items: start; padding: var(--af-s6) var(--af-s5); border-radius: var(--af-r-lg); background: linear-gradient(160deg, #0a3440 0%, #052832 45%, #02121a 100%); border: 1px solid rgba(79, 224, 210, 0.18); box-shadow: var(--af-shadow-3); }
.soon > :not(.af-caustic) { position: relative; z-index: 1; }
.soon h2, .soon p { margin: 0; }
.soon h2 { font-family: var(--af-display); font-size: 22px; font-weight: 600; letter-spacing: -0.02em; }
.soon ul { margin: 0; padding: 0; list-style: none; display: grid; gap: 10px; width: 100%; }
.soon li { position: relative; padding: 12px 14px 12px 40px; border-radius: var(--af-r-sm); background: rgba(255, 255, 255, 0.05); border: 1px solid var(--af-line); line-height: 1.45; font-size: 15px; }
.soon li::before { content: ''; position: absolute; left: 16px; top: 18px; width: 10px; height: 10px; border-radius: 50%; border: 2px solid var(--af-primary); box-shadow: 0 0 8px color-mix(in srgb, var(--af-primary) 60%, transparent); }
</style>
