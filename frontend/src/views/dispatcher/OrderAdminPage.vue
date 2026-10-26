<!-- Phone/tablet: one order on its own screen (desktop shows it beside the list instead). -->
<script setup>
import { useRoute } from 'vue-router'
import { IonBackButton, IonButtons, IonContent, IonHeader, IonPage, IonTitle, IonToolbar } from '@ionic/vue'

import OrderAdminPanel from '@/components/dispatcher/OrderAdminPanel.vue'

const route = useRoute()
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-buttons slot="start">
          <ion-back-button default-href="/dispatcher/orders" text="Queue" />
        </ion-buttons>
        <ion-title>Order</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content>
      <div class="af-container narrow">
        <div class="af-card">
          <OrderAdminPanel :order-id="String(route.params.id)" />
        </div>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.narrow { max-width: 720px; }
</style>
