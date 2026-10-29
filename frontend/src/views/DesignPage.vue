<!--
  /design — living style guide. Shows every token and base component
  in the current theme. Use it to check the look before building screens.
-->
<script setup>
import { ref } from 'vue'
import { IonContent, IonHeader, IonPage, IonTitle, IonToolbar } from '@ionic/vue'

import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import OfflineBanner from '@/components/ui/OfflineBanner.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SkeletonList from '@/components/ui/SkeletonList.vue'
import StatCard from '@/components/ui/StatCard.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import WaterLevelBar from '@/components/ui/WaterLevelBar.vue'
import { useTheme } from '@/composables/useTheme'
import { ORDER_STATUS } from '@/constants/orderStatus'

const { preference, setTheme } = useTheme()
const themes = [
  { value: 'system', label: 'System' },
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
]

const colors = [
  { token: '--af-deep', name: 'Deep water', use: 'hero cards, sidebar' },
  { token: '--af-primary', name: 'Mint primary', use: 'actions' },
  { token: '--af-water', name: 'Water', use: 'fills, progress' },
  { token: '--af-amber', name: 'Amber', use: 'warnings only' },
  { token: '--af-bg', name: 'Ground', use: 'page background' },
  { token: '--af-surface', name: 'Surface', use: 'cards' },
  { token: '--af-ink', name: 'Ink', use: 'text' },
  { token: '--af-danger', name: 'Danger', use: 'errors, failed' },
]

const typeScale = [
  { cls: 'af-display', spec: 'Display · Unbounded 40 · 700', text: 'Plan Deliveries' },
  { cls: 'af-h1', spec: 'H1 · Unbounded 30 · 600', text: "Today's orders" },
  { cls: 'af-h2', spec: 'H2 · Unbounded 22 · 600', text: 'Trip T-02 · Morning' },
  { cls: 'af-h3', spec: 'H3 · Manrope 18 · 800', text: 'Stop 2 of 6 · Santos Store' },
  { cls: 'af-body', spec: 'Body · Manrope 16 · 500', text: "Your order of 3 containers is being prepared. We'll notify you when the rider leaves." },
  { cls: 'af-small', spec: 'Small · Manrope 14', text: 'Landmark: blue gate beside the chapel, Camilmil' },
  { cls: 'af-caption', spec: 'Caption · Mono 11 caps', text: 'Containers on hand' },
  { cls: 'af-metric', spec: 'Metric · Unbounded 52 · tabular', text: '1,284' },
  { cls: 'af-code af-h2', spec: 'Code · mono', text: '4827' },
]

// Interactive demo: change the load and watch the bar change state
const load = ref(18)
const loading = ref(false)
function fakeSave() {
  loading.value = true
  setTimeout(() => (loading.value = false), 1500)
}
</script>

<template>
  <ion-page>
    <ion-header class="ion-no-border">
      <ion-toolbar>
        <ion-title>AquaFlow · Design system</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content>
      <div class="af-container">
        <PageHeader crumb="Phase 1" title="Design system" subtitle="Tokens and base components in the current theme">
          <template #actions>
            <div class="seg" role="group" aria-label="Theme">
              <button
                v-for="t in themes"
                :key="t.value"
                type="button"
                :aria-pressed="preference === t.value"
                @click="setTheme(t.value)"
              >
                {{ t.label }}
              </button>
            </div>
          </template>
        </PageHeader>

        <!-- Color -->
        <section>
          <h2 class="af-h3 sec-title">Color</h2>
          <div class="grid g4">
            <div v-for="c in colors" :key="c.token" class="af-card sw">
              <div class="chip" :style="{ background: `var(${c.token})` }"></div>
              <b>{{ c.name }}</b>
              <code>{{ c.token }} · {{ c.use }}</code>
            </div>
          </div>
        </section>

        <!-- Type -->
        <section>
          <h2 class="af-h3 sec-title">Typography</h2>
          <div class="af-card">
            <div v-for="t in typeScale" :key="t.spec" class="type-row">
              <span class="spec">{{ t.spec }}</span>
              <span :class="t.cls">{{ t.text }}</span>
            </div>
          </div>
        </section>

        <!-- Status pills -->
        <section>
          <h2 class="af-h3 sec-title">StatusPill</h2>
          <div class="af-card pills">
            <StatusPill v-for="(info, key) in ORDER_STATUS" :key="key" :status="key" />
          </div>
        </section>

        <!-- Water level -->
        <section>
          <h2 class="af-h3 sec-title">WaterLevelBar</h2>
          <div class="grid g3">
            <div class="af-card"><WaterLevelBar label="Tricycle ABC-123" :value="12" :max="20" /></div>
            <div class="af-card"><WaterLevelBar label="Tricycle ABC-123" :value="19" :max="20" /></div>
            <div class="af-card">
              <WaterLevelBar label="Multicab XYZ-987" :value="22" :max="20" note="✕ Over capacity by 2 · move an order to another trip" />
            </div>
          </div>
          <div class="af-card demo">
            <WaterLevelBar label="Try it: load now" :value="load" :max="20" size="lg" />
            <div class="demo__btns">
              <AppButton variant="secondary" size="sm" aria-label="Remove one container" @click="load = Math.max(0, load - 1)">− 1</AppButton>
              <AppButton variant="secondary" size="sm" aria-label="Add one container" @click="load = load + 1">+ 1</AppButton>
            </div>
          </div>
        </section>

        <!-- Buttons -->
        <section>
          <h2 class="af-h3 sec-title">AppButton</h2>
          <div class="af-card stack">
            <div class="row">
              <AppButton>Plan Deliveries</AppButton>
              <AppButton variant="secondary">Edit trip</AppButton>
              <AppButton variant="ghost">View history</AppButton>
              <AppButton variant="danger">Reject order</AppButton>
              <AppButton :loading="loading" @click="fakeSave">{{ loading ? 'Saving…' : 'Click to test loading' }}</AppButton>
            </div>
            <div class="row">
              <AppButton size="sm" variant="secondary">Small</AppButton>
              <AppButton variant="secondary">Default</AppButton>
              <AppButton size="lg">Mark as delivered</AppButton>
            </div>
          </div>
        </section>

        <!-- Stat cards -->
        <section>
          <h2 class="af-h3 sec-title">StatCard</h2>
          <div class="grid g4">
            <StatCard label="Orders today" :value="48" delta="12% vs last Friday" tone="up" />
            <StatCard label="Ready stock" :value="64" unit="containers" delta="Forecast needs 71" />
            <StatCard label="Supply left" :value="3" unit="days" delta="Restock caps by Monday" tone="warn" />
            <StatCard label="On-time rate" :value="96" unit="%" delta="2 pts this week" tone="up" />
          </div>
        </section>

        <!-- States -->
        <section>
          <h2 class="af-h3 sec-title">OfflineBanner, EmptyState, SkeletonList</h2>
          <div class="stack">
            <OfflineBanner state="offline" :pending="3" />
            <OfflineBanner state="syncing" :done="1" :total="3" />
            <OfflineBanner state="synced" :total="3" />
          </div>
          <div class="grid g2" style="margin-top: 16px">
            <div class="af-card">
              <EmptyState
                title="No orders yet"
                message="Order your first 5-gallon refill and we'll deliver it this morning or afternoon."
                action-label="Order water"
              />
            </div>
            <div class="af-card"><SkeletonList :rows="4" /></div>
          </div>
        </section>
      </div>
    </ion-content>
  </ion-page>
</template>

<style scoped>
.sec-title { margin: 0 0 var(--af-s4); }
.grid { display: grid; gap: var(--af-s4); }
.g2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.g3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.g4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.stack { display: grid; gap: var(--af-s3); }
.row { display: flex; flex-wrap: wrap; gap: var(--af-s3); align-items: center; }
.pills { display: flex; flex-wrap: wrap; gap: var(--af-s2); }

.sw { display: grid; gap: var(--af-s2); padding: var(--af-s4); }
.chip { height: 64px; border-radius: var(--af-r-sm); border: 1px solid var(--af-line); }
.sw b { font-size: 14px; }
.sw code { font: 500 12px var(--af-mono); color: var(--af-ink-2); overflow-wrap: anywhere; }

.type-row {
  display: grid;
  grid-template-columns: 160px minmax(0, 1fr);
  gap: var(--af-s4);
  align-items: baseline;
  padding-block: var(--af-s3);
  border-top: 1px solid var(--af-line);
}
.type-row:first-child { border-top: 0; }
.spec { font: 500 12px/1.4 var(--af-mono); color: var(--af-ink-2); }

.demo { margin-top: var(--af-s4); display: grid; gap: var(--af-s4); }
.demo__btns { display: flex; gap: var(--af-s2); }

.seg { display: inline-flex; background: var(--af-surface-2); border-radius: var(--af-r-pill); padding: 4px; gap: 2px; }
.seg button {
  font: 600 13px var(--af-font);
  color: var(--af-ink-2);
  background: transparent;
  border: 0;
  padding: 8px 14px;
  min-height: 40px;
  border-radius: var(--af-r-pill);
  cursor: pointer;
}
.seg button[aria-pressed='true'] { background: var(--af-surface); color: var(--af-ink); box-shadow: var(--af-shadow-1); }

@media (max-width: 900px) {
  .g3 { grid-template-columns: 1fr; }
  .g4 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 560px) {
  .g2, .g4 { grid-template-columns: 1fr; }
  .type-row { grid-template-columns: 1fr; gap: 4px; }
}
</style>