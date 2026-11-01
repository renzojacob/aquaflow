<!--
  PromoBanner — Foodpanda-style promo strip for the home screen.
  Shows real, true facts about the service (not a fake discount code —
  there's no voucher system yet; this becomes the real promo banner in Phase C).
-->
<script setup>
import { IonIcon } from '@ionic/vue'
import { flashOutline } from 'ionicons/icons'
</script>

<template>
  <div class="af-promo af-glow-edge" role="note">
    <span class="af-promo__icon" aria-hidden="true"><ion-icon :icon="flashOutline" /></span>
    <div class="af-promo__text">
      <b>Order before the cutoff, get it today</b>
      <span>Morning or afternoon delivery · cash on delivery · right to your door</span>
    </div>
  </div>
</template>

<style scoped>
.af-promo {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--af-s4);
  padding: var(--af-s4) var(--af-s5);
  border-radius: var(--af-r-lg);
  overflow: hidden;
  isolation: isolate;
  background:
    radial-gradient(120% 140% at 0% 0%, rgba(79, 224, 210, 0.22) 0%, transparent 55%),
    linear-gradient(120deg, #0a3440 0%, #052832 55%, #02121a 100%);
  color: #e6f4f6;
  box-shadow: var(--af-shadow-2);
}
.af-promo__icon {
  flex: none;
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: rgba(79, 224, 210, 0.16);
  color: #4fe0d2;
  font-size: 20px;
  box-shadow: 0 0 18px rgba(79, 224, 210, 0.3);
}
.af-promo__text { display: grid; gap: 2px; min-width: 0; }
.af-promo__text b { font-size: 15px; font-weight: 800; letter-spacing: -0.01em; }
.af-promo__text span { font-size: 13px; color: #9fc3c9; line-height: 1.4; }
</style>
