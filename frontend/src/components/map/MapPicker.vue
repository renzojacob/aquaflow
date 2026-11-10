<!--
  MapPicker — Leaflet map with a draggable water-drop pin.
  - Tap the map or drag the pin to set the location (v-model = { lat, lng }).
  - Shows the station and the delivery area circle.
  - Free OpenStreetMap tiles (no API key). Dark theme recolors the same tiles with a CSS filter.
  Usage: <MapPicker v-model="pin" :station="settings.station" :radius-km="8" />
         <MapPicker :model-value="order.address" readonly />
-->
<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { mapColors, pinSvg } from '@/theme/mapTheme'

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
let resizeObserver = null

const CALAPAN = { lat: 13.4108, lng: 121.1792 }

// Pins drawn with HTML instead of image files (avoids Leaflet's broken-icon problem with Vite)
const pinIcon = () => L.divIcon({ className: 'af-map-pin', html: pinSvg(), iconSize: [34, 44], iconAnchor: [17, 43] })
const stationIcon = L.divIcon({
  className: 'af-map-station',
  html: '<span>AF</span>',
  iconSize: [30, 30],
  iconAnchor: [15, 15],
})

// OpenStreetMap's own free tiles: no API key needed (CARTO now requires one).
// Please keep the attribution visible: it is the condition for using them.
const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'

function setPin(latlng, notify) {
  if (!pin) {
    pin = L.marker(latlng, { icon: pinIcon(), draggable: !props.readonly, keyboard: !props.readonly, title: 'Delivery pin' }).addTo(map)
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

  tiles = L.tileLayer(TILE_URL, {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map)

  if (props.station) {
    if (props.radiusKm > 0) {
      L.circle([props.station.lat, props.station.lng], {
        radius: props.radiusKm * 1000,
        color: mapColors().route,
        weight: 1.5,
        dashArray: '6 6',
        fillColor: mapColors().glow,
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
.af-map-wrap { position: relative; border-radius: var(--af-r-md); overflow: hidden; border: 1px solid var(--af-line); box-shadow: var(--af-shadow-1); isolation: isolate; }
.af-map-wrap { height: 260px; }
/* Fill the box with width/height, not position: Leaflet may set its own position
   on the element (it does when it measures before styles load, e.g. inside a modal). */
.af-map { width: 100%; height: 100%; background: var(--af-surface-2); }
.af-map__hint {
  position: absolute;
  left: 50%;
  bottom: 12px;
  transform: translateX(-50%);
  z-index: 500;
  margin: 0;
  padding: 10px 16px;
  border-radius: var(--af-r-pill);
  background: color-mix(in srgb, var(--af-deep) 88%, transparent);
  color: var(--af-on-deep);
  border: 1px solid rgba(var(--af-glow-rgb), 0.3);
  font-size: 13px;
  font-weight: 750;
  pointer-events: none;
  white-space: nowrap;
  backdrop-filter: blur(8px);
}
:deep(.af-map-pin) { background: none; border: 0; filter: drop-shadow(0 4px 8px rgba(var(--af-deep-rgb), 0.45)) drop-shadow(0 0 6px rgba(var(--af-glow-rgb), 0.45)); }
:deep(.af-map-station) {
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: var(--af-deep);
  color: var(--af-glow-c);
  font: 700 10px var(--af-display);
  border: 2px solid var(--af-glow-c);
  box-shadow: 0 0 0 4px rgba(var(--af-glow-rgb), 0.2), 0 4px 10px rgba(0, 0, 0, 0.35);
}
</style>
