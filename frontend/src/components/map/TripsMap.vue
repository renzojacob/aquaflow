<!--
  TripsMap: every trip of the day in its own colour, numbered stops, and orders not planned yet in grey.
  A trip with `route_line` (roads from OpenRouteService) is drawn solid; an estimate is dotted.
  Usage: <TripsMap :station="{lat,lng}" :trips="trips" :unplanned="unplanned" :selected-id="3" />
  Colours are paired with numbers and the card list, so colour is never the only clue.
-->
<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

import { tripColor } from '@/constants/tripColors'

const props = defineProps({
  station: { type: Object, default: null },
  trips: { type: Array, default: () => [] },
  unplanned: { type: Array, default: () => [] },
  selectedId: { type: Number, default: null },
  height: { type: String, default: '420px' },
})

const el = ref(null)
let map, layer, ro

const stationIcon = L.divIcon({ className: 'tm-station', html: '<span>AF</span>', iconSize: [30, 30], iconAnchor: [15, 15] })
const stopIcon = (n, color, dim) =>
  L.divIcon({ className: 'tm-stop', html: `<span style="background:${color};opacity:${dim ? 0.55 : 1}">${n}</span>`, iconSize: [28, 28], iconAnchor: [14, 14] })

function draw(fit = true) {
  layer.clearLayers()
  const pts = []
  const home = props.station ? [props.station.lat, props.station.lng] : null
  if (home) {
    L.marker(home, { icon: stationIcon, interactive: false, keyboard: false }).addTo(layer)
    pts.push(home)
  }
  props.trips.forEach((t, i) => {
    const color = tripColor(i)
    const dim = props.selectedId != null && props.selectedId !== t.id
    const weight = props.selectedId === t.id ? 5 : 3
    if (t.route_line?.length > 1) {
      // Real roads from OpenRouteService: solid line
      L.polyline(t.route_line, { color, weight: weight + 1, opacity: dim ? 0.3 : 0.85, lineJoin: 'round' }).addTo(layer)
      for (const p of t.route_line) pts.push(p)
    } else {
      // Estimate: dotted straight lines station -> stops -> station
      const line = [...(home ? [home] : []), ...t.stops.map((s) => [s.lat, s.lng]), ...(home ? [home] : [])]
      L.polyline(line, { color, weight, opacity: dim ? 0.35 : 0.9, dashArray: '2 8', lineCap: 'round' }).addTo(layer)
    }
    for (const s of t.stops) {
      L.marker([s.lat, s.lng], { icon: stopIcon(s.sequence, color, dim), keyboard: false, title: `${t.vehicle.name} stop ${s.sequence}: ${s.customer_name}` }).addTo(layer)
      pts.push([s.lat, s.lng])
    }
  })
  for (const o of props.unplanned) {
    L.circleMarker([o.lat, o.lng], { radius: 7, color: '#5b6b72', weight: 2, fillColor: '#ffffff', fillOpacity: 0.9 })
      .bindTooltip(`${o.code} ${o.customer_name} (not planned)`).addTo(layer)
    pts.push([o.lat, o.lng])
  }
  if (fit && pts.length > 1) map.fitBounds(L.latLngBounds(pts).pad(0.2), { maxZoom: 16 })
  else if (fit && pts.length === 1) map.setView(pts[0], 15)
}

onMounted(() => {
  const c = props.station ?? { lat: 13.4108, lng: 121.1792 }
  map = L.map(el.value, { center: [c.lat, c.lng], zoom: 13, scrollWheelZoom: false })
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map)
  layer = L.layerGroup().addTo(map)
  draw()
  ro = new ResizeObserver(() => map.invalidateSize())
  ro.observe(el.value)
})

const signature = () => JSON.stringify([props.trips.map((t) => [t.id, t.stops.map((s) => s.order_id)]), props.unplanned.map((o) => o.order_id)])
watch(signature, () => draw(true))
watch(() => props.selectedId, () => draw(false))
onBeforeUnmount(() => { ro?.disconnect(); map?.remove() })
</script>

<template>
  <div class="tm" :style="{ height }">
    <div ref="el" class="tm__map" role="img" aria-label="Map of today's trips. Each trip has its own colour and numbered stops."></div>
  </div>
</template>

<style scoped>
.tm { border-radius: var(--af-r-md); overflow: hidden; border: 1px solid var(--af-line); isolation: isolate; }
.tm__map { width: 100%; height: 100%; background: var(--af-surface-2); }
:global([data-theme='dark']) .tm__map :deep(.leaflet-tile-pane) { filter: invert(1) hue-rotate(180deg) brightness(0.9) contrast(0.9) saturate(0.6); }
:deep(.tm-station) { display: grid; place-items: center; border-radius: 10px; background: #02121a; color: #4fe0d2; font: 700 10px var(--af-display); border: 2px solid #4fe0d2; box-shadow: 0 0 0 4px rgba(79, 224, 210, 0.2); }
:deep(.tm-stop span) { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 50%; color: #fff; font: 800 13px var(--af-font); border: 2px solid #fff; box-shadow: 0 3px 8px rgba(0, 0, 0, 0.4); text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5); }
</style>
