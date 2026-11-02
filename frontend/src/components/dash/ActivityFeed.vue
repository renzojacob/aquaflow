<!--
  ActivityFeed — what happened, newest first. Each row: a status-colored mark, a sentence, the time.
  Items: [{ id, at, status, lead, strong, tail?, note?, to? }]  ("to" makes the row a link)
-->
<script setup>
import { IonIcon } from '@ionic/vue'
import { ORDER_STATUS } from '@/constants/orderStatus'
import { ago } from '@/utils/format'

defineProps({
  items: { type: Array, required: true },
  empty: { type: String, default: 'Nothing has happened yet.' },
})
defineEmits(['open'])
</script>

<template>
  <ol v-if="items.length" class="feed">
    <li v-for="it in items" :key="it.id" class="feed__item" :class="`feed--${ORDER_STATUS[it.status]?.tone ?? 'pending'}`">
      <span class="feed__mark" aria-hidden="true">
        <ion-icon v-if="ORDER_STATUS[it.status]?.icon" :icon="ORDER_STATUS[it.status].icon" />
        <i v-else></i>
      </span>
      <component :is="it.to ? 'button' : 'div'" :type="it.to ? 'button' : undefined" class="feed__body" @click="it.to && $emit('open', it)">
        <span class="feed__text">{{ it.lead }} <b>{{ it.strong }}</b><template v-if="it.tail"> {{ it.tail }}</template></span>
        <span v-if="it.note" class="feed__note">{{ it.note }}</span>
      </component>
      <time class="feed__time" :datetime="it.at">{{ ago(it.at) }}</time>
    </li>
  </ol>
  <p v-else class="feed__empty">{{ empty }}</p>
</template>

<style scoped>
.feed { list-style: none; margin: 0; padding: 0; display: grid; }
.feed__item { position: relative; display: grid; grid-template-columns: 34px minmax(0, 1fr) auto; gap: 12px; align-items: start; padding: 10px 0; }
/* the thread joining one event to the next */
.feed__item:not(:last-child)::before { content: ''; position: absolute; left: 16px; top: 44px; bottom: -8px; width: 2px; border-radius: 2px; background: var(--af-line); }
.feed__mark { width: 34px; height: 34px; display: grid; place-items: center; border-radius: 12px; background: var(--t); color: var(--c); font-size: 16px; }
.feed__mark i { width: 8px; height: 8px; border-radius: 50%; background: var(--c); box-shadow: 0 0 8px var(--c); }
.feed__body { display: grid; gap: 3px; min-width: 0; padding: 6px 0 0; border: 0; background: none; color: inherit; font: inherit; text-align: left; }
button.feed__body { cursor: pointer; border-radius: 8px; }
button.feed__body:hover .feed__text b { text-decoration: underline; text-underline-offset: 3px; }
.feed__text { font-size: 14.5px; line-height: 1.45; font-weight: 550; }
.feed__text b { font-weight: 800; }
.feed__note { font-size: 13px; color: var(--af-ink-2); font-style: italic; }
.feed__time { padding-top: 7px; font-size: 12.5px; font-weight: 650; color: var(--af-ink-2); white-space: nowrap; font-variant-numeric: tabular-nums; }
.feed__empty { margin: 0; font-size: 14px; color: var(--af-ink-2); }

.feed--pending { --c: var(--af-st-pending); --t: var(--af-st-pending-t); }
.feed--confirmed { --c: var(--af-st-confirmed); --t: var(--af-st-confirmed-t); }
.feed--preparing { --c: var(--af-st-preparing); --t: var(--af-st-preparing-t); }
.feed--ready { --c: var(--af-st-ready); --t: var(--af-st-ready-t); }
.feed--out { --c: var(--af-st-out); --t: var(--af-st-out-t); }
.feed--delivered { --c: var(--af-st-delivered); --t: var(--af-st-delivered-t); }
.feed--rejected { --c: var(--af-st-rejected); --t: var(--af-st-rejected-t); }
.feed--cancelled { --c: var(--af-st-cancelled); --t: var(--af-st-cancelled-t); }
.feed--failed { --c: var(--af-st-failed); --t: var(--af-st-failed-t); }
</style>
