<!-- "More" tab on phones: every menu item, theme switch, log out. -->
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { IonContent, IonHeader, IonIcon, IonPage, IonTitle, IonToolbar, useIonRouter } from '@ionic/vue'
import { chevronForward } from 'ionicons/icons'

import AppButton from '@/components/ui/AppButton.vue'
import ThemeSwitch from '@/components/ui/ThemeSwitch.vue'
import { NAV, ROLE_LABEL } from '@/config/navigation'
import { useAuthStore } from '@/stores/auth'
import { initials } from '@/utils/format'

const route = useRoute()
const ionRouter = useIonRouter()
const auth = useAuthStore()

const role = computed(() => route.matched.find((r) => r.meta.role)?.meta.role)
const items = computed(() => (NAV[role.value] ?? []).filter((i) => i.sidebar !== false))

function logout() {
  auth.logout()
  ionRouter.navigate('/login', 'root', 'replace')
}
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-title>More</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content>
      <div class="af-container narrow">
        <section class="af-card me">
          <span class="avatar" aria-hidden="true">{{ initials(auth.user?.full_name) }}</span>
          <div>
            <b>{{ auth.user?.full_name }}</b>
            <p class="af-small">{{ ROLE_LABEL[auth.role] }} · {{ auth.user?.email }}</p>
          </div>
        </section>

        <nav class="af-card menu" aria-label="All screens">
          <button v-for="i in items" :key="i.name" type="button" class="menu__item" @click="ionRouter.navigate(i.href, 'root', 'replace')">
            <ion-icon :icon="i.icon" aria-hidden="true" />
            <span>{{ i.label }}</span>
            <ion-icon :icon="chevronForward" class="menu__chev" aria-hidden="true" />
          </button>
        </nav>

        <section class="af-card stack">
          <h2 class="af-h3">Appearance</h2>
          <ThemeSwitch block />
        </section>

        <AppButton variant="secondary" block @click="logout">Log out</AppButton>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.narrow { max-width: 720px; gap: var(--af-s4); }
.me { display: flex; align-items: center; gap: var(--af-s3); }
.me p { margin: 2px 0 0; }
.avatar { width: 48px; height: 48px; border-radius: 50%; display: grid; place-items: center; background: var(--af-navy); color: #fff; font-weight: 800; flex: none; }
.menu { padding: var(--af-s2); display: grid; }
.menu__item {
  display: grid;
  grid-template-columns: 24px 1fr 20px;
  align-items: center;
  gap: var(--af-s3);
  min-height: 52px;
  padding: 0 var(--af-s3);
  border: 0;
  border-radius: var(--af-r-sm);
  background: transparent;
  color: var(--af-ink);
  font: 600 15px var(--af-font);
  text-align: left;
  cursor: pointer;
}
.menu__item:hover { background: var(--af-surface-2); }
.menu__item ion-icon { font-size: 20px; color: var(--af-primary); }
.menu__chev { color: var(--af-ink-2) !important; font-size: 16px !important; }
.stack { display: grid; gap: var(--af-s3); }
.stack h2 { margin: 0; }
</style>
