<!--
  RiderCard — "your rider" card shown once an order is out for delivery,
  the way a food-delivery app shows the courier assigned to your order.

  NOTE for Phase D: the backend doesn't expose a rider phone/photo to the
  customer yet (only order.trip.rider_name). The "Call rider" button is
  wired to the STATION phone for now, which is real. Swap `riderPhone`
  for a real number once the backend adds it.
-->
<script setup>
import { computed } from 'vue'
import { IonIcon } from '@ionic/vue'
import { callOutline } from 'ionicons/icons'
import { initials } from '@/utils/format'

const props = defineProps({
  trip: { type: Object, required: true },     // { rider_name, code, stops_before }
  stationPhone: { type: String, default: '' }, // optional, honest fallback
})

const etaText = computed(() =>
  props.trip.stops_before === 0
    ? 'Heading to you now'
    : `${props.trip.stops_before} stop${props.trip.stops_before > 1 ? 's' : ''} away`,
)
const telHref = computed(() => (props.stationPhone ? `tel:${props.stationPhone.replace(/\s+/g, '')}` : ''))
</script>

<template>
  <section class="af-rider af-card" aria-labelledby="rider-title">
    <span class="af-rider__avatar" aria-hidden="true">{{ initials(trip.rider_name) }}</span>
    <div class="af-rider__info">
      <h2 id="rider-title" class="af-rider__name">{{ trip.rider_name }}</h2>
      <p class="af-rider__meta">
        <span class="af-rider__dot" aria-hidden="true"></span>
        <b>{{ etaText }}</b> · trip {{ trip.code }}
      </p>
    </div>
    <a v-if="telHref" class="af-rider__call" :href="telHref" aria-label="Call the station about your rider">
      <ion-icon :icon="callOutline" aria-hidden="true" />
    </a>
  </section>
</template>

<style scoped>
.af-rider { display: flex; align-items: center; gap: var(--af-s3); padding: var(--af-s4); }
.af-rider__avatar {
  width: 48px;
  height: 48px;
  flex: none;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: linear-gradient(140deg, #4fe0d2 0%, #1aa6b5 100%);
  color: #022320;
  font-weight: 800;
  font-size: 15px;
}
.af-rider__info { min-width: 0; flex: 1; display: grid; gap: 3px; }
.af-rider__name { margin: 0; font-size: 15px; font-weight: 800; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.af-rider__meta { margin: 0; display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--af-ink-2); }
.af-rider__meta b { color: var(--af-primary); font-weight: 750; }
.af-rider__dot { width: 7px; height: 7px; border-radius: 50%; background: var(--af-primary); box-shadow: 0 0 6px var(--af-primary); flex: none; animation: af-rider-pulse 1.6s ease-in-out infinite; }
@keyframes af-rider-pulse { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }
.af-rider__call {
  flex: none;
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--af-primary-tint);
  color: var(--af-primary);
  font-size: 19px;
  text-decoration: none;
  transition: background var(--af-dur) var(--af-ease);
}
.af-rider__call:hover { background: color-mix(in srgb, var(--af-primary) 26%, transparent); }
</style>
