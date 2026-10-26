<!--
  RoleShell — the frame around every logged-in screen.
  Phone/tablet (< 992px): bottom tab bar.
  Desktop (>= 992px): sidebar on the left, no tab bar.
  The menu items come from config/navigation.js for the user's role.
-->
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  IonIcon,
  IonLabel,
  IonPage,
  IonRouterOutlet,
  IonTabBar,
  IonTabButton,
  IonTabs,
  useIonRouter,
} from '@ionic/vue'
import { logOutOutline } from 'ionicons/icons'

import AppLogo from '@/components/ui/AppLogo.vue'
import ThemeSwitch from '@/components/ui/ThemeSwitch.vue'
import { NAV, ROLE_LABEL } from '@/config/navigation'
import { useAuthStore } from '@/stores/auth'
import { initials } from '@/utils/format'

const route = useRoute()
const ionRouter = useIonRouter()
const auth = useAuthStore()

// The role comes from the route (/customer, /rider ...), set in router meta
const role = computed(() => route.matched.find((r) => r.meta.role)?.meta.role ?? auth.role)
const items = computed(() => NAV[role.value] ?? [])
const tabs = computed(() => items.value.filter((i) => i.tab))
const sideItems = computed(() => items.value.filter((i) => i.sidebar !== false))

const isActive = (href) => route.path === href || route.path.startsWith(`${href}/`)

function go(href) {
  ionRouter.navigate(href, 'root', 'replace')
}

function logout() {
  auth.logout()
  ionRouter.navigate('/login', 'root', 'replace')
}
</script>

<template>
  <ion-page>
    <div class="af-shell">
      <!-- Desktop sidebar -->
      <aside class="af-side" aria-label="Main menu">
        <div class="af-side__brand"><AppLogo /></div>

        <nav class="af-side__nav">
          <button
            v-for="item in sideItems"
            :key="item.name"
            type="button"
            class="af-side__link"
            :aria-current="isActive(item.href) ? 'page' : undefined"
            @click="go(item.href)"
          >
            <ion-icon :icon="item.icon" aria-hidden="true" />
            {{ item.label }}
          </button>
        </nav>

        <div class="af-side__foot">
          <ThemeSwitch block />
          <div class="af-side__user">
            <span class="af-avatar" aria-hidden="true">{{ initials(auth.user?.full_name) }}</span>
            <span class="af-side__who">
              <b>{{ auth.user?.full_name }}</b>
              <span>{{ ROLE_LABEL[auth.role] }}</span>
            </span>
            <button type="button" class="af-side__logout" aria-label="Log out" @click="logout">
              <ion-icon :icon="logOutOutline" aria-hidden="true" />
            </button>
          </div>
        </div>
      </aside>

      <!-- Screens + mobile tab bar -->
      <div class="af-shell__main">
        <ion-tabs>
          <ion-router-outlet></ion-router-outlet>
          <ion-tab-bar slot="bottom" class="af-tabbar">
            <ion-tab-button v-for="t in tabs" :key="t.name" :tab="t.name" :href="t.href">
              <ion-icon :icon="t.icon" aria-hidden="true" />
              <ion-label>{{ t.label }}</ion-label>
            </ion-tab-button>
          </ion-tab-bar>
        </ion-tabs>
      </div>
    </div>
  </ion-page>
</template>

<style scoped>
.af-shell { position: absolute; inset: 0; display: flex; background: var(--af-bg); }
.af-shell__main { position: relative; flex: 1; min-width: 0; }

/* ---------- Sidebar (desktop only) ---------- */
.af-side {
  display: none;
  width: 264px;
  flex: none;
  flex-direction: column;
  gap: var(--af-s5);
  padding: var(--af-s5) var(--af-s4) calc(var(--af-s4) + env(safe-area-inset-bottom, 0px));
  background: var(--af-surface);
  border-right: 1px solid var(--af-line);
  overflow-y: auto;
}
.af-side__brand { padding: 0 var(--af-s2); }
.af-side__nav { display: grid; gap: 4px; }
.af-side__link {
  display: flex;
  align-items: center;
  gap: var(--af-s3);
  min-height: 44px;
  padding: 0 var(--af-s3);
  border: 0;
  border-radius: var(--af-r-sm);
  background: transparent;
  color: var(--af-ink-2);
  font: 600 15px var(--af-font);
  text-align: left;
  cursor: pointer;
  transition: background var(--af-dur) var(--af-ease), color var(--af-dur) var(--af-ease);
}
.af-side__link ion-icon { font-size: 20px; }
.af-side__link:hover { background: var(--af-surface-2); color: var(--af-ink); }
.af-side__link[aria-current='page'] { background: var(--af-primary-tint); color: var(--af-primary); }
.af-side__foot { margin-top: auto; display: grid; gap: var(--af-s4); }
.af-side__user { display: flex; align-items: center; gap: var(--af-s3); padding: var(--af-s3); border-radius: var(--af-r-md); background: var(--af-surface-2); }
.af-side__who { display: grid; min-width: 0; flex: 1; }
.af-side__who b { font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.af-side__who span { font-size: 12px; color: var(--af-ink-2); }
.af-side__logout {
  width: 40px;
  height: 40px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--af-ink-2);
  display: grid;
  place-items: center;
  font-size: 20px;
  cursor: pointer;
}
.af-side__logout:hover { background: var(--af-danger-tint); color: var(--af-danger); }

.af-avatar {
  width: 40px;
  height: 40px;
  flex: none;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--af-navy);
  color: #fff;
  font-weight: 800;
  font-size: 14px;
}

/* ---------- Bottom tab bar (phone/tablet) ---------- */
.af-tabbar {
  --background: var(--af-surface);
  --border: 1px solid var(--af-line);
  --color: var(--af-ink-2);
  --color-selected: var(--af-primary);
  height: 64px;
}
.af-tabbar ion-tab-button { --ripple-color: var(--af-primary); font-weight: 700; }
.af-tabbar ion-icon { font-size: 22px; }
.af-tabbar ion-label { font-size: 11px; font-weight: 700; margin-top: 2px; }

@media (min-width: 992px) {
  .af-side { display: flex; }
  .af-tabbar { display: none; }
}
</style>
