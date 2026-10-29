<script setup>
import { IonApp, IonRouterOutlet } from '@ionic/vue'
import OceanBackdrop from '@/components/ui/OceanBackdrop.vue'
</script>

<template>
  <ion-app>
    <!-- The living ocean behind every screen (pages are see-through glass) -->
    <OceanBackdrop class="af-app-ocean" />
    <ion-router-outlet />
  </ion-app>
</template>

<style>
.af-app-ocean { position: fixed !important; } /* overrides the component's absolute default */
</style>
