<!--
  TEMPORARY Phase 0 screen: proves the app runs and mock mode works.
  Later it also proves frontend <-> backend <-> database are connected.
  Plain styling on purpose — the design system comes in Phase 1.
-->
<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import {
  IonButton,
  IonCard,
  IonCardContent,
  IonContent,
  IonHeader,
  IonPage,
  IonSkeletonText,
  IonTitle,
  IonToolbar,
} from '@ionic/vue'
import { Capacitor } from '@capacitor/core'
import { Network } from '@capacitor/network'

import { env } from '@/config/env'
import { checkHealth } from '@/services/healthService'

const loading = ref(true)
/** @type {import('vue').Ref<import('@/services/healthService').HealthResult | null>} */
const result = ref(null)
/** @type {import('vue').Ref<import('@/types/api').ApiError | null>} */
const error = ref(null)
const online = ref(null)
const platform = Capacitor.getPlatform() // 'web' | 'android' | 'ios'
let networkListener = null

async function runCheck() {
  loading.value = true
  error.value = null
  try {
    result.value = await checkHealth()
  } catch (e) {
    result.value = null
    error.value = e
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  // Also proves the @capacitor/network plugin is installed correctly.
  online.value = (await Network.getStatus()).connected
  networkListener = await Network.addListener('networkStatusChange', (s) => {
    online.value = s.connected
  })
  await runCheck()
})

onBeforeUnmount(() => {
  networkListener?.remove()
})
</script>

<template>
  <ion-page>
    <ion-header>
      <ion-toolbar>
        <ion-title>AquaFlow · Connection check</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content class="ion-padding">
      <ion-card>
        <ion-card-content>
          <dl class="facts">
            <dt>Platform</dt><dd>{{ platform }}</dd>
            <dt>Build mode</dt><dd>{{ env.mode }}</dd>
            <dt>Data source</dt><dd>{{ env.useMock ? 'MOCK data' : 'Real API' }}</dd>
            <dt>API URL</dt><dd class="mono">{{ env.apiBaseUrl }}</dd>
            <dt>Device network</dt><dd>{{ online === null ? '…' : online ? 'Online' : 'Offline' }}</dd>
          </dl>
        </ion-card-content>
      </ion-card>

      <ion-card>
        <ion-card-content aria-live="polite">
          <div v-if="loading">
            <ion-skeleton-text :animated="true" style="width: 60%; height: 20px" />
            <ion-skeleton-text :animated="true" style="width: 85%" />
            <ion-skeleton-text :animated="true" style="width: 40%" />
          </div>

          <div v-else-if="error">
            <p class="headline">✕ API not reachable</p>
            <p>{{ error.message }} <span class="muted">({{ error.kind }})</span></p>
            <ul class="tips">
              <li>Is uvicorn running with <span class="mono">--host 0.0.0.0</span>?</li>
              <li v-if="platform === 'android'">Emulator uses 10.0.2.2. Real phone uses your PC's Wi-Fi IP, same Wi-Fi.</li>
              <li v-if="platform === 'android'">Windows Firewall must allow port 8000 (Private network).</li>
              <li>Does <span class="mono">{{ env.apiBaseUrl }}/health</span> open in a browser?</li>
            </ul>
          </div>

          <div v-else-if="result">
            <p class="headline">{{ result.data.status === 'ok' ? '✓ Connected' : '! API up, database down' }}</p>
            <dl class="facts">
              <dt>API</dt><dd>{{ result.data.app }} v{{ result.data.version }} ({{ result.data.environment }})</dd>
              <dt>Database</dt><dd>{{ result.data.database === 'up' ? 'PostgreSQL reachable' : 'PostgreSQL NOT reachable' }}</dd>
              <template v-if="result.data.database_error">
                <dt>DB error</dt><dd class="mono small">{{ result.data.database_error }}</dd>
              </template>
              <dt>Round trip</dt><dd>{{ result.latencyMs }} ms</dd>
              <dt>Server time</dt><dd>{{ new Date(result.data.server_time).toLocaleString() }}</dd>
            </dl>
          </div>

          <ion-button expand="block" class="retry" :disabled="loading" @click="runCheck">Check again</ion-button>
        </ion-card-content>
      </ion-card>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.facts { display: grid; grid-template-columns: max-content 1fr; gap: 6px 16px; margin: 0; }
dt { font-weight: 600; }
dd { margin: 0; overflow-wrap: anywhere; }
.headline { font-size: 1.15rem; font-weight: 700; margin: 0 0 12px; }
.mono { font-family: ui-monospace, Consolas, monospace; }
.small { font-size: 0.8rem; }
.muted { opacity: 0.7; }
.tips { padding-left: 18px; margin: 8px 0 0; }
.retry { margin-top: 16px; min-height: 44px; }
</style>