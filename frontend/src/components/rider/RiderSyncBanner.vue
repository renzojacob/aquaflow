<!--
  RiderSyncBanner — OfflineBanner connected to the real outbox (offline/outbox.js).
  Shows: offline with N waiting · syncing x of y · "all synced" for a moment · actions not accepted.
  Shows nothing when online with an empty outbox. Tapping it opens the Sync screen.
-->
<script setup>
import { computed } from 'vue'
import { useIonRouter } from '@ionic/vue'

import OfflineBanner from '@/components/ui/OfflineBanner.vue'
import { env } from '@/config/env'
import { syncState } from '@/offline/outbox'

const router = useIonRouter()

const view = computed(() => {
  if (env.useMock) return null
  if (syncState.syncing) return { state: 'syncing', done: syncState.progress.done, total: syncState.progress.total }
  if (!syncState.online) return { state: 'offline', pending: syncState.pending + syncState.rejected }
  if (syncState.rejected) return { state: 'attention', pending: syncState.rejected }
  if (syncState.justSynced) return { state: 'synced', total: syncState.justSynced }
  if (syncState.pending) return { state: 'offline', pending: syncState.pending }
  return null
})
</script>

<template>
  <button v-if="view" type="button" class="sync-banner" aria-label="Open the Sync screen" @click="router.push('/rider/sync')">
    <OfflineBanner v-bind="view" />
  </button>
</template>

<style scoped>
.sync-banner { all: unset; display: block; width: 100%; margin-bottom: 12px; cursor: pointer; }
.sync-banner:focus-visible { outline: 3px solid var(--af-primary); outline-offset: 3px; border-radius: var(--af-r-sm); }
</style>
