<!--
  Screens planned for a later phase. Says so plainly, shows what the screen will do,
  and points to what works today instead (so nobody hits a dead end).
  The route's meta gives the title, phase number and planned features.
-->
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { IonContent, IonHeader, IonIcon, IonPage, IonTitle, IonToolbar, useIonRouter } from '@ionic/vue'
import { arrowForward, constructOutline, ellipseOutline } from 'ionicons/icons'

import LiquidFill from '@/components/ui/LiquidFill.vue'
import { ROLE_LABEL } from '@/config/navigation'

const route = useRoute()
const ionRouter = useIonRouter()
const meta = computed(() => route.meta)
const role = computed(() => route.matched.find((r) => r.meta.role)?.meta.role)
const key = computed(() => route.path.split('/').filter(Boolean).pop())

/** What to use until this screen exists. Every link here goes to a screen that works now. */
const MEANWHILE = {
  plan: { text: 'Send each ready order out from the queue and pick the rider there.', label: 'Open the order queue', href: '/dispatcher/orders' },
  conflicts: { text: 'Riders are not offline yet, so there is nothing to resolve. Every change happens live on the queue.', label: 'Open the order queue', href: '/dispatcher/orders' },
  trip: { text: 'Until the rider app is ready, the dispatcher sends orders out and marks them delivered. Customers already see your name and number.', label: '', href: '' },
  sync: { text: 'Nothing is stored on this phone yet, so there is nothing waiting to sync.', label: '', href: '' },
  supplies: { text: 'Containers (filled, empties, on the road, with customers) are tracked on the Stock screen.', label: 'Open stock', href: '/owner/stock' },
  vehicles: { text: 'Add tricycles and multicabs in Django admin for now (Dispatch > Vehicles).', label: '', href: '' },
  products: { text: 'Change the refill price in Django admin for now (Inventory > Products). The app picks it up right away.', label: '', href: '' },
  'service-area': { text: 'Set the station location and delivery radius in Django admin for now (Station > Service areas).', label: '', href: '' },
}
const meanwhile = computed(() => MEANWHILE[key.value] ?? null)
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-title>{{ meta.title }}</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content>
      <div class="af-container af-dash af-dash--narrow">
        <section class="hero af-deep-scope">
          <div class="hero__text">
            <span class="hero__tag"><ion-icon :icon="constructOutline" aria-hidden="true" /> {{ ROLE_LABEL[role] }} screen, planned for phase {{ meta.phase }}</span>
            <h1 class="hero__title">{{ meta.title }}</h1>
            <p class="hero__sub">This screen isn't built yet. Here is what it will do, and what to use until then.</p>
          </div>
          <LiquidFill class="hero__jug" shape="jug" :size="96" :level="0.18" />
        </section>

        <section v-if="meanwhile" class="af-panel now" aria-labelledby="now-title">
          <h2 id="now-title" class="h">Use this for now</h2>
          <p>{{ meanwhile.text }}</p>
          <button v-if="meanwhile.href && (role === 'owner' || meanwhile.href.startsWith(`/${role}`))" type="button" class="now__go" @click="ionRouter.navigate(meanwhile.href, 'root', 'replace')">
            {{ meanwhile.label }} <ion-icon :icon="arrowForward" aria-hidden="true" />
          </button>
        </section>

        <section class="af-panel" aria-labelledby="plan-title">
          <h2 id="plan-title" class="h">What it will do</h2>
          <ul class="plan">
            <li v-for="item in meta.planned" :key="item">
              <ion-icon :icon="ellipseOutline" aria-hidden="true" />
              <span>{{ item }}</span>
            </li>
          </ul>
        </section>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.hero {
  position: relative;
  overflow: hidden;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 20px;
  padding: 28px;
  border-radius: 32px;
  background:
    repeating-linear-gradient(0deg, color-mix(in srgb, var(--af-on-deep-2) 6%, transparent) 0 1px, transparent 1px 28px),
    repeating-linear-gradient(90deg, color-mix(in srgb, var(--af-on-deep-2) 6%, transparent) 0 1px, transparent 1px 28px),
    radial-gradient(80% 90% at 100% 0%, color-mix(in srgb, var(--af-accent-on-deep) 20%, transparent), transparent 60%),
    linear-gradient(180deg, var(--af-tank-bg-1) 0%, var(--af-tank-bg-2) 100%);
  box-shadow: inset 0 0 0 1px var(--af-deep-line), var(--af-shadow-3);
}
.hero__text { display: grid; gap: 12px; min-width: 0; }
.hero__tag { display: inline-flex; align-items: center; gap: 8px; justify-self: start; padding: 7px 12px; border-radius: 999px; background: rgba(var(--af-sun-rgb), 0.14); color: var(--af-sun); font-size: 13px; font-weight: 750; }
.hero__title { margin: 0; font-family: var(--af-display); font-size: clamp(30px, 4.6vw, 48px); font-weight: 650; letter-spacing: -0.045em; line-height: 1; color: var(--af-on-deep); }
.hero__sub { margin: 0; font-size: 15.5px; line-height: 1.55; color: var(--af-on-deep-soft); max-width: 44ch; }
.hero__jug { flex: none; filter: drop-shadow(0 16px 24px rgba(0, 0, 0, 0.4)); }

.h { margin: 0; font-family: var(--af-display); font-size: 17px; font-weight: 600; letter-spacing: -0.02em; }
.now { background: linear-gradient(160deg, var(--af-primary-tint), transparent 70%), var(--af-surface); border-color: color-mix(in srgb, var(--af-primary) 35%, var(--af-line)); }
.now p { margin: 0; font-size: 15px; line-height: 1.55; }
.now__go { justify-self: start; display: inline-flex; align-items: center; gap: 8px; min-height: 44px; padding: 0 18px; border: 0; border-radius: 999px; background: var(--af-primary); color: var(--af-on-primary); font: 750 14.5px var(--af-font); cursor: pointer; }
.plan { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.plan li { display: grid; grid-template-columns: 20px 1fr; gap: 12px; align-items: start; padding: 12px 14px; border-radius: 16px; background: var(--af-surface-2); font-size: 15px; line-height: 1.5; }
.plan ion-icon { margin-top: 3px; color: var(--af-ink-2); font-size: 16px; }

@media (max-width: 520px) {
  .hero { padding: 22px; }
  .hero__jug { display: none; }
}
</style>
