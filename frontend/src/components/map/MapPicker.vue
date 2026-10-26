<!--
  MapPicker — Leaflet map with a draggable water-drop pin.
  - Tap the map or drag the pin to set the location (v-model = { lat, lng }).
  - Shows the station and the delivery area circle.
  - Map colors follow light/dark theme (free CARTO tiles, OpenStreetMap data).
  Usage: <MapPicker v-model="pin" :station="settings.station" :radius-km="8" />
         <MapPicker :model-value="order.address" readonly />
-->
<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const props = defineProps({
  modelValue: { type: Object, default: null }, // { lat, lng } or null
  station: { type: Object, default: null },    // { lat, lng, name }
  radiusKm: { type: Number, default: 0 },
  readonly: { type: Boolean, default: false },
  height: { type: String, default: '260px' },
  zoom: { type: Number, default: 15 },
})
const emit = defineEmits(['update:modelValue'])

const el = ref(null)
let map = null
let pin = null
let tiles = null
let themeObserver = null
let resizeObserver = null

const CALAPAN = { lat: 13.4108, lng: 121.1792 }

// Pins drawn with HTML instead of image files (avoids Leaflet's broken-icon problem with Vite)
const pinIcon = L.divIcon({
  className: 'af-map-pin',
  html: '<svg width="34" height="44" viewBox="0 0 34 44" aria-hidden="true"><path d="M17 1C8.2 1 1 8 1 16.7 1 28.5 17 43 17 43s16-14.5 16-26.3C33 8 25.8 1 17 1Z" fill="#0A7684" stroke="#fff" stroke-width="2"/><path d="M17 8.5c3.2 4 5.6 7.1 5.6 10a5.6 5.6 0 1 1-11.2 0c0-2.9 2.4-6 5.6-10Z" fill="#fff"/></svg>',
  iconSize: [34, 44],
  iconAnchor: [17, 43],
})
const stationIcon = L.divIcon({
  className: 'af-map-station',
  html: '<span>AF</span>',
  iconSize: [30, 30],
  iconAnchor: [15, 15],
})

function tileUrl() {
  const dark = document.documentElement.dataset.theme === 'dark'
  return `https://{s}.basemaps.cartocdn.com/${dark ? 'dark_all' : 'light_all'}/{z}/{x}/{y}{r}.png`
}

function setPin(latlng, notify) {
  if (!pin) {
    pin = L.marker(latlng, { icon: pinIcon, draggable: !props.readonly, keyboard: !props.readonly, title: 'Delivery pin' }).addTo(map)
    pin.on('dragend', () => {
      const p = pin.getLatLng()
      emit('update:modelValue', { lat: round(p.lat), lng: round(p.lng) })
    })
  } else {
    pin.setLatLng(latlng)
  }
  if (notify) emit('update:modelValue', { lat: round(latlng.lat), lng: round(latlng.lng) })
}

const round = (n) => Math.round(n * 1e6) / 1e6

onMounted(() => {
  const start = props.modelValue ?? props.station ?? CALAPAN
  map = L.map(el.value, {
    center: [start.lat, start.lng],
    zoom: props.zoom,
    zoomControl: !props.readonly,
    dragging: true,
    scrollWheelZoom: false, // page scroll shouldn't zoom the map by accident
    attributionControl: true,
  })

  tiles = L.tileLayer(tileUrl(), {
    maxZoom: 19,
    subdomains: 'abcd',
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
  }).addTo(map)

  if (props.station) {
    if (props.radiusKm > 0) {
      L.circle([props.station.lat, props.station.lng], {
        radius: props.radiusKm * 1000,
        color: '#22B8C8',
        weight: 1.5,
        dashArray: '6 6',
        fillColor: '#22B8C8',
        fillOpacity: 0.06,
        interactive: false,
      }).addTo(map)
    }
    L.marker([props.station.lat, props.station.lng], { icon: stationIcon, interactive: false, keyboard: false }).addTo(map)
  }

  if (props.modelValue) setPin([props.modelValue.lat, props.modelValue.lng], false)

  if (!props.readonly) {
    map.on('click', (e) => setPin(e.latlng, true))
  }

  // Swap map tiles when the app theme changes
  themeObserver = new MutationObserver(() => tiles.setUrl(tileUrl()))
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })

  // Leaflet must re-measure when it appears inside a modal or a resized layout
  resizeObserver = new ResizeObserver(() => map.invalidateSize())
  resizeObserver.observe(el.value)
})

// When the parent changes the location (e.g. picked a barangay or "Use my location")
watch(
  () => props.modelValue,
  (v) => {
    if (!map || !v) return
    const current = pin?.getLatLng()
    if (!current || current.lat !== v.lat || current.lng !== v.lng) {
      setPin([v.lat, v.lng], false)
      map.setView([v.lat, v.lng], Math.max(map.getZoom(), 16))
    }
  },
)

onBeforeUnmount(() => {
  themeObserver?.disconnect()
  resizeObserver?.disconnect()
  map?.remove()
})
</script>

<template>
  <div class="af-map-wrap" :style="{ height }">
    <div ref="el" class="af-map" role="application" :aria-label="readonly ? 'Map of the delivery location' : 'Map. Tap to place the delivery pin, or drag the pin.'"></div>
    <p v-if="!readonly && !modelValue" class="af-map__hint">Tap the map to drop your pin</p>
  </div>
</template>

<style scoped>
.af-map-wrap { position: relative; border-radius: var(--af-r-md); overflow: hidden; border: 1px solid var(--af-line); }
.af-map { position: absolute; inset: 0; background: var(--af-surface-2); }
.af-map__hint {
  position: absolute;
  left: 50%;
  bottom: 12px;
  transform: translateX(-50%);
  z-index: 500;
  margin: 0;
  padding: 8px 14px;
  border-radius: var(--af-r-pill);
  background: var(--af-navy);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  pointer-events: none;
  white-space: nowrap;
}
:deep(.af-map-pin) { background: none; border: 0; filter: drop-shadow(0 3px 4px rgba(0, 0, 0, 0.3)); }
:deep(.af-map-station) {
  display: grid;
  place-items: center;
  border-radius: 9px;
  background: #0f2a4a;
  color: #fff;
  font: 800 11px var(--af-font);
  border: 2px solid #fff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
}
:deep(.leaflet-container) { font-family: var(--af-font); }
</style>
