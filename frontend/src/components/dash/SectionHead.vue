<!--
  SectionHead — the title over a group on a dashboard, with an optional action on the right.
  Usage: <SectionHead title="Recent orders" action="See all" @action="go" />
-->
<script setup>
import { IonIcon } from '@ionic/vue'
import { chevronForward } from 'ionicons/icons'

defineProps({
  title: { type: String, required: true },
  sub: { type: String, default: '' },
  action: { type: String, default: '' },
  level: { type: Number, default: 2 },
})
defineEmits(['action'])
</script>

<template>
  <div class="sh">
    <div class="sh__text">
      <component :is="`h${level}`" class="sh__title">{{ title }}</component>
      <p v-if="sub" class="sh__sub">{{ sub }}</p>
    </div>
    <button v-if="action" type="button" class="sh__act" @click="$emit('action')">
      {{ action }} <ion-icon :icon="chevronForward" aria-hidden="true" />
    </button>
    <slot />
  </div>
</template>

<style scoped>
.sh { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.sh__text { min-width: 0; }
.sh__title { margin: 0; font-family: var(--af-display); font-size: 17px; font-weight: 600; letter-spacing: -0.02em; line-height: 1.25; }
.sh__sub { margin: 4px 0 0; font-size: 13.5px; font-weight: 600; color: var(--af-ink-2); }
.sh__act {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 40px;
  padding: 0 4px 0 12px;
  border: 0;
  border-radius: var(--af-r-pill);
  background: transparent;
  color: var(--af-primary);
  font: 750 14px var(--af-font);
  cursor: pointer;
}
.sh__act:hover { background: var(--af-primary-tint); }
.sh__act ion-icon { font-size: 16px; }
</style>
