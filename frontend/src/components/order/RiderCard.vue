<!--
  RiderCard — the person bringing the order, with a call button when we have their number.
  Usage: <RiderCard :rider="{ name, phone }" status="out_for_delivery" />
-->
<script setup>
import { computed } from 'vue'
import { IonIcon } from '@ionic/vue'
import { callOutline, chatbubbleOutline } from 'ionicons/icons'
import { initials } from '@/utils/format'

const props = defineProps({
  rider: { type: Object, required: true }, // { name, phone }
  status: { type: String, default: 'out_for_delivery' },
})
const line = computed(() =>
  props.status === 'delivered' ? 'Delivered your order' : props.status === 'failed_delivery' ? 'Tried to deliver' : 'Bringing your water now',
)
const tel = computed(() => (props.rider.phone ? props.rider.phone.replace(/\s+/g, '') : ''))
</script>

<template>
  <section class="rc" aria-label="Your rider">
    <span class="rc__avatar" aria-hidden="true">{{ initials(rider.name) }}</span>
    <div class="rc__info">
      <b class="rc__name">{{ rider.name }}</b>
      <span class="rc__line"><i v-if="status === 'out_for_delivery'" class="rc__dot" aria-hidden="true"></i>{{ line }}</span>
    </div>
    <template v-if="tel">
      <a class="rc__btn" :href="`sms:${tel}`" :aria-label="`Text ${rider.name}`"><ion-icon :icon="chatbubbleOutline" /></a>
      <a class="rc__btn rc__btn--call" :href="`tel:${tel}`" :aria-label="`Call ${rider.name}`"><ion-icon :icon="callOutline" /></a>
    </template>
  </section>
</template>

<style scoped>
.rc { display: flex; align-items: center; gap: 12px; padding: 14px 16px; border-radius: 22px; background: var(--af-surface); border: 1px solid var(--af-line); box-shadow: inset 0 1px 0 var(--af-glass-edge); }
.rc__avatar { width: 50px; height: 50px; flex: none; border-radius: 50%; display: grid; place-items: center; background: linear-gradient(140deg, #b9b4ff 0%, #4fe0d2 100%); color: #04161d; font-weight: 800; font-size: 16px; box-shadow: 0 0 0 3px var(--af-surface-solid), 0 0 0 4px color-mix(in srgb, var(--af-primary) 45%, transparent); }
.rc__info { min-width: 0; flex: 1; display: grid; gap: 3px; }
.rc__name { font-size: 16px; font-weight: 800; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rc__line { display: flex; align-items: center; gap: 7px; font-size: 13.5px; font-weight: 650; color: var(--af-ink-2); }
.rc__dot { width: 8px; height: 8px; border-radius: 50%; background: var(--af-primary); box-shadow: 0 0 8px var(--af-primary); animation: rc-pulse 1.6s ease-in-out infinite; }
@keyframes rc-pulse { 50% { opacity: 0.4; } }
.rc__btn { flex: none; width: 44px; height: 44px; display: grid; place-items: center; border-radius: 50%; background: var(--af-surface-2); color: var(--af-primary); font-size: 19px; text-decoration: none; }
.rc__btn:hover { background: var(--af-primary-tint); }
.rc__btn--call { background: var(--af-primary); color: var(--af-on-primary); }
.rc__btn--call:hover { background: var(--af-primary-hover); }
@media (prefers-reduced-motion: reduce) { .rc__dot { animation: none; } }
</style>
