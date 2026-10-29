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
      <aside class="af-side af-deep-scope" aria-label="Main menu">
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
.af-shell { position: absolute; inset: 0; display: flex; }
.af-shell__main { position: relative; flex: 1; min-width: 0; }

/* ---------- Sidebar (desktop only): deep water in both themes ---------- */
.af-side {
  display: none;
  position: relative;
  width: 272px;
  flex: none;
  flex-direction: column;
  gap: var(--af-s6);
  padding: var(--af-s5) var(--af-s4) calc(var(--af-s4) + env(safe-area-inset-bottom, 0px));
  background:
    radial-gradient(140% 50% at 0% 0%, rgba(79, 224, 210, 0.16) 0%, transparent 60%),
    linear-gradient(180deg, rgba(6, 48, 58, 0.82) 0%, rgba(2, 18, 26, 0.9) 100%);
  backdrop-filter: blur(24px) saturate(150%);
  -webkit-backdrop-filter: blur(24px) saturate(150%);
  color: var(--af-on-deep);
  border-right: 1px solid rgba(159, 195, 201, 0.14);
  box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.04), 12px 0 40px rgba(2, 18, 26, 0.25);
  overflow-y: auto;
}
.af-side__brand { padding: var(--af-s1) var(--af-s2); }
.af-side__nav { display: grid; gap: 4px; }
.af-side__link {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--af-s3);
  min-height: 46px;
  padding: 0 var(--af-s3);
  border: 0;
  border-radius: var(--af-r-sm);
  background: transparent;
  color: var(--af-on-deep-2);
  font: 650 15px var(--af-font);
  text-align: left;
  cursor: pointer;
  transition: background var(--af-dur) var(--af-ease), color var(--af-dur) var(--af-ease);
}
.af-side__link ion-icon { font-size: 20px; flex: none; }
.af-side__link:hover { background: rgba(255, 255, 255, 0.05); color: var(--af-on-deep); }
.af-side__link[aria-current='page'] {
  background: linear-gradient(90deg, rgba(79, 224, 210, 0.16), rgba(79, 224, 210, 0.04));
  color: var(--af-on-deep);
  font-weight: 800;
}
.af-side__link[aria-current='page'] ion-icon { color: var(--af-mint); }
/* the glowing water line marking the current page */
.af-side__link[aria-current='page']::before {
  content: '';
  position: absolute;
  left: -16px;
  top: 10px;
  bottom: 10px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--af-mint);
  box-shadow: 0 0 12px var(--af-mint);
}
.af-side__foot { margin-top: auto; display: grid; gap: var(--af-s4); }
.af-side__user { display: flex; align-items: center; gap: var(--af-s3); padding: var(--af-s3); border-radius: var(--af-r-md); background: rgba(255, 255, 255, 0.05); border: 1px solid var(--af-deep-line); }
.af-side__who { display: grid; min-width: 0; flex: 1; }
.af-side__who b { font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.af-side__who span { font-family: var(--af-mono); font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--af-on-deep-2); margin-top: 2px; }
.af-side__logout {
  width: 44px;
  height: 44px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: var(--af-on-deep-2);
  display: grid;
  place-items: center;
  font-size: 20px;
  cursor: pointer;
  transition: background var(--af-dur) var(--af-ease), color var(--af-dur) var(--af-ease);
}
.af-side__logout:hover { background: rgba(255, 138, 122, 0.14); color: #ff8a7a; }

.af-avatar {
  width: 40px;
  height: 40px;
  flex: none;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: linear-gradient(140deg, #4fe0d2 0%, #1aa6b5 100%);
  color: #022320;
  font-weight: 800;
  font-size: 14px;
}

/* ---------- Bottom tab bar (phone/tablet): a floating glass bar ---------- */
.af-tabbar {
  --background: transparent;
  --border: 0;
  background: linear-gradient(180deg, color-mix(in srgb, #ffffff 6%, transparent), transparent), color-mix(in srgb, var(--af-surface-solid) 72%, transparent);
  --color: var(--af-ink-2);
  --color-selected: var(--af-ink);
  height: 68px;
  margin: 0 12px calc(12px + env(safe-area-inset-bottom, 0px));
  padding-bottom: 0;
  border-radius: 24px;
  border: 1px solid var(--af-line);
  box-shadow: inset 0 1px 0 var(--af-glass-edge), var(--af-shadow-3);
  backdrop-filter: blur(24px) saturate(170%);
  -webkit-backdrop-filter: blur(24px) saturate(170%);
  overflow: hidden;
}
.af-tabbar ion-tab-button { --ripple-color: var(--af-primary); --padding-top: 6px; --padding-bottom: 6px; --padding-start: 2px; --padding-end: 2px; flex: 1 1 0; min-width: 0; max-width: none; font-weight: 700; }
.af-tabbar ion-icon {
  font-size: 22px;
  box-sizing: content-box;
  padding: 4px 14px;
  border-radius: var(--af-r-pill);
  transition: background var(--af-dur) var(--af-ease), color var(--af-dur) var(--af-ease);
}
.af-tabbar ion-tab-button.tab-selected ion-icon {
  background: linear-gradient(135deg, color-mix(in srgb, var(--af-primary) 30%, transparent), color-mix(in srgb, var(--af-primary) 12%, transparent));
  color: var(--af-primary);
  box-shadow: 0 0 18px color-mix(in srgb, var(--af-primary) 35%, transparent), inset 0 0 0 1px color-mix(in srgb, var(--af-primary) 35%, transparent);
}
.af-tabbar ion-label { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; font-weight: 750; margin-top: 2px; }
.af-tabbar ion-tab-button.tab-selected ion-label { font-weight: 800; }

@media (min-width: 992px) {
  .af-side { display: flex; }
  .af-tabbar { display: none; }
}
</style>
