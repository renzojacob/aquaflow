<!--
  AreaMap: the owner sets the station and the delivery radius.
  Click the map or drag the AF marker to move the station. The circle follows the radius.
  Dots show the barangays: filled = served, hollow = not served.
  Usage: <AreaMap v-model="station" :radius-km="5" :barangays="[{name,lat,lng,served}]" />
-->
<script setup>
import { onBeforeUnmount, onMounted, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { ref } from 'vue'

const props = defineProps({
  modelValue: { type: Object, required: true },        // { lat, lng }
  radiusKm: { type: Number, default: 5 },
  barangays: { type: Array, default: () => [] },       // [{ name, lat, lng, served }]
  height: { type: String, default: '380px' },
})
const emit = defineEmits(['update:modelValue'])

const el = ref(null)
let map, circle, marker, dots, ro
const round = (n) => Math.round(n * 1e6) / 1e6
const icon = L.divIcon({ className: 'am-station', html: '<span>AF</span>', iconSize: [34, 34], iconAnchor: [17, 17] })

function drawDots() {
  dots.clearLayers()
  for (const b of props.barangays) {
    L.circleMarker([b.lat, b.lng], {
      radius: 6, weight: 2, color: b.served ? '#007067' : '#7a8a90',
      fillColor: b.served ? '#4fe0d2' : '#ffffff', fillOpacity: b.served ? 0.9 : 0.5,
    }).bindTooltip(`${b.name}${b.served ? '' : ' (not served)'}`).addTo(dots)
  }
}

onMounted(() => {
  const c = props.modelValue
  map = L.map(el.value, { center: [c.lat, c.lng], zoom: 12, scrollWheelZoom: false })
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map)
  circle = L.circle([c.lat, c.lng], { radius: props.radiusKm * 1000, color: '#1AA6B5', weight: 2, dashArray: '6 6', fillColor: '#4FE0D2', fillOpacity: 0.08, interactive: false }).addTo(map)
  marker = L.marker([c.lat, c.lng], { icon, draggable: true, title: 'Station' }).addTo(map)
  dots = L.layerGroup().addTo(map)
  drawDots()
  marker.on('dragend', () => { const p = marker.getLatLng(); emit('update:modelValue', { lat: round(p.lat), lng: round(p.lng) }) })
  map.on('click', (e) => emit('update:modelValue', { lat: round(e.latlng.lat), lng: round(e.latlng.lng) }))
  map.fitBounds(circle.getBounds().pad(0.1))
  ro = new ResizeObserver(() => map.invalidateSize())
  ro.observe(el.value)
})

watch(() => props.modelValue, (v) => { marker?.setLatLng([v.lat, v.lng]); circle?.setLatLng([v.lat, v.lng]) }, { deep: true })
watch(() => props.radiusKm, (r) => { if (circle) { circle.setRadius(r * 1000); map.fitBounds(circle.getBounds().pad(0.1)) } })
watch(() => props.barangays, drawDots, { deep: true })
onBeforeUnmount(() => { ro?.disconnect(); map?.remove() })
</script>

<template>
  <div class="am" :style="{ height }">
    <div ref="el" class="am__map" role="application" aria-label="Map. Click to move the station, or drag the AF marker."></div>
  </div>
</template>

<style scoped>
.am { border-radius: var(--af-r-md); overflow: hidden; border: 1px solid var(--af-line); isolation: isolate; }
.am__map { width: 100%; height: 100%; background: var(--af-surface-2); }
:global([data-theme='dark']) .am__map :deep(.leaflet-tile-pane) { filter: invert(1) hue-rotate(180deg) brightness(0.9) contrast(0.9) saturate(0.6); }
:deep(.am-station) { display: grid; place-items: center; border-radius: 11px; background: #02121a; color: #4fe0d2; font: 700 11px var(--af-display); border: 2px solid #4fe0d2; box-shadow: 0 0 0 5px rgba(79, 224, 210, 0.22); cursor: grab; }
</style>
