<!--
  Placeholder for screens built in later phases.
  The route's meta gives the title, phase number and what the screen will contain,
  so the whole app can be clicked through now.
-->
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { IonContent, IonHeader, IonPage, IonTitle, IonToolbar } from '@ionic/vue'

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
        <section class="af-card soon">
          <svg width="56" height="56" viewBox="0 0 56 56" fill="none" aria-hidden="true">
            <rect x="14" y="10" width="28" height="38" rx="8" fill="var(--af-primary-tint)" />
            <rect x="21" y="5" width="14" height="7" rx="3" fill="var(--af-water)" />
            <path d="M14 38c5-3 9 3 14 0s9-3 14 0v2a8 8 0 0 1-8 8H22a8 8 0 0 1-8-8v-2Z" fill="var(--af-water)" />
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
.soon { display: grid; gap: var(--af-s2); justify-items: start; }
.soon h2, .soon p { margin: 0; }
.soon ul { margin: 0; padding-left: 20px; display: grid; gap: 6px; line-height: 1.5; }
</style>
