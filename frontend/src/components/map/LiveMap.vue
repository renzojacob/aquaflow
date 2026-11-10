<!--
  LiveMap — the station, the stops and a moving rider, for live tracking.
  The rider marker glides from one GPS point to the next (no jumping), points the way
  it's heading, and the dashed line shows the way still to go.
  With `route` (the trip's road path from OpenRouteService) the roads are drawn as a solid line
  and the dashed line only joins the rider to the next stop.
  Usage:
    <LiveMap :station="{lat,lng}" :stops="[{ id, lat, lng, seq, mine }]" :rider="{ lat, lng, heading, is_simulated }" :route="[[lat, lng], ...]" />
-->
<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { mapColors, pinSvg } from '@/theme/mapTheme'

const props = defineProps({
  station: { type: Object, default: null },
  stops: { type: Array, default: () => [] },      // [{ id, lat, lng, seq?, mine? }]
  rider: { type: Object, default: null },          // { lat, lng, heading?, is_simulated? }
  height: { type: String, default: '320px' },
  label: { type: String, default: 'Live delivery map' },
  route: { type: Array, default: null },           // [[lat, lng], ...] road path, or null
})

const el = ref(null)
let map = null
let tiles = null
let riderMarker = null
let line = null
let road = null
let stopLayer = null
let resizeObserver = null
let anim = null
let fitted = false

// OpenStreetMap's free tiles (no API key). Dark theme recolors them with a CSS filter.
const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'

const stationIcon = L.divIcon({ className: 'lm-station', html: '<span>AF</span>', iconSize: [30, 30], iconAnchor: [15, 15] })
const stopIcon = (s) =>
  L.divIcon({
    className: `lm-stop${s.mine ? ' lm-stop--mine' : ''}`,
    html: s.mine
      ? pinSvg(36, 46)
      : `<span>${s.seq ?? ''}</span>`,
    iconSize: s.mine ? [36, 46] : [30, 30],
    iconAnchor: s.mine ? [18, 45] : [15, 15],
  })
const riderIcon = (heading, simulated) =>
  L.divIcon({
    className: 'lm-rider',
    html: `<span class="lm-rider__pulse"></span><span class="lm-rider__dot${simulated ? ' is-sim' : ''}"><svg width="22" height="22" viewBox="0 0 24 24" style="transform:rotate(${Math.round(heading ?? 0)}deg)"><path d="M12 3l6 16-6-3.5L6 19z" fill="currentColor"/></svg></span>`,
    iconSize: [44, 44],
    iconAnchor: [22, 22],
  })

function drawStops() {
  stopLayer.clearLayers()
  for (const s of props.stops) L.marker([s.lat, s.lng], { icon: stopIcon(s), keyboard: false, interactive: false }).addTo(stopLayer)
}

function drawRoad() {
  road?.remove()
  road = props.route?.length > 1
    ? L.polyline(props.route, { color: mapColors().route, weight: 5, opacity: 0.75, lineJoin: 'round', interactive: false }).addTo(map)
    : null
}

function drawLine(from) {
  // On the roads already drawn, only show "you -> next stop"; without them, the whole way
  const ahead = road ? props.stops.slice(0, 1) : props.stops
  const pts = [from ? [from.lat, from.lng] : null, ...ahead.map((s) => [s.lat, s.lng])].filter(Boolean)
  if (line) line.setLatLngs(pts)
  else line = L.polyline(pts, { color: mapColors().path, weight: 3, opacity: 0.85, dashArray: '2 9', lineCap: 'round' }).addTo(map)
}

function fit() {
  const pts = [...props.stops.map((s) => [s.lat, s.lng])]
  if (props.rider) pts.push([props.rider.lat, props.rider.lng])
  else if (props.station) pts.push([props.station.lat, props.station.lng])
  if (pts.length > 1) map.fitBounds(L.latLngBounds(pts).pad(0.25), { maxZoom: 17 })
  else if (pts.length === 1) map.setView(pts[0], 16)
  fitted = true
}

/** Glide the rider from where they are drawn now to the new point. */
function moveRider(to) {
  if (!to) return
  const icon = riderIcon(to.heading, to.is_simulated)
  if (!riderMarker) {
    riderMarker = L.marker([to.lat, to.lng], { icon, keyboard: false, interactive: false, zIndexOffset: 1000 }).addTo(map)
    drawLine(to)
    return
  }
  riderMarker.setIcon(icon)
  cancelAnimationFrame(anim)
  const from = riderMarker.getLatLng()
  const t0 = performance.now()
  const D = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 1400
  const step = (t) => {
    const p = D ? Math.min(1, (t - t0) / D) : 1
    const e = 1 - Math.pow(1 - p, 3)
    const cur = { lat: from.lat + (to.lat - from.lat) * e, lng: from.lng + (to.lng - from.lng) * e }
    riderMarker.setLatLng([cur.lat, cur.lng])
    drawLine(cur)
    if (p < 1) anim = requestAnimationFrame(step)
    else if (!map.getBounds().pad(-0.1).contains([to.lat, to.lng])) map.panTo([to.lat, to.lng])
  }
  anim = requestAnimationFrame(step)
}

onMounted(() => {
  const start = props.rider ?? props.stops[0] ?? props.station ?? { lat: 13.4108, lng: 121.1792 }
  map = L.map(el.value, { center: [start.lat, start.lng], zoom: 15, scrollWheelZoom: false, attributionControl: true })
  tiles = L.tileLayer(TILE_URL, { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' }).addTo(map)
  if (props.station) L.marker([props.station.lat, props.station.lng], { icon: stationIcon, interactive: false, keyboard: false }).addTo(map)
  drawRoad()
  stopLayer = L.layerGroup().addTo(map)
  drawStops()
  if (props.rider) moveRider(props.rider)
  else drawLine(props.station)
  fit()
  resizeObserver = new ResizeObserver(() => map.invalidateSize())
  resizeObserver.observe(el.value)
})

watch(() => props.rider && `${props.rider.lat},${props.rider.lng},${props.rider.heading}`, () => {
  const first = !riderMarker
  moveRider(props.rider)
  if (first && !fitted) fit()
})
watch(() => props.route, () => {
  drawRoad()
  drawLine(riderMarker?.getLatLng() ?? props.station)
})
watch(() => props.stops.map((s) => `${s.id}:${s.seq}`).join('|'), () => {
  drawStops()
  drawLine(riderMarker?.getLatLng() ?? props.station)
  fit()
})

onBeforeUnmount(() => {
  cancelAnimationFrame(anim)
  resizeObserver?.disconnect()
  map?.remove()
})
</script>

<template>
  <div class="lm" :style="{ height }">
    <div ref="el" class="lm__map" role="img" :aria-label="label"></div>
    <slot />
  </div>
</template>

<style scoped>
.lm { position: relative; border-radius: inherit; overflow: hidden; isolation: isolate; }
.lm__map { width: 100%; height: 100%; background: var(--af-surface-2); }
:deep(.lm-station) { display: grid; place-items: center; border-radius: 10px; background: var(--af-deep); color: var(--af-glow-c); font: 700 10px var(--af-display); border: 2px solid var(--af-glow-c); box-shadow: 0 0 0 4px rgba(var(--af-glow-rgb), 0.2); }
:deep(.lm-stop) { display: grid; place-items: center; border-radius: 50%; background: var(--af-deep); color: var(--af-on-deep); font: 800 13px var(--af-font); border: 2px solid var(--af-map-stop-ring); box-shadow: 0 4px 10px rgba(0, 0, 0, 0.35); }
:deep(.lm-stop--mine) { background: none; border: 0; border-radius: 0; box-shadow: none; filter: drop-shadow(0 4px 8px rgba(var(--af-deep-rgb), 0.45)) drop-shadow(0 0 6px rgba(var(--af-glow-rgb), 0.45)); }
:deep(.lm-rider) { position: relative; }
:deep(.lm-rider__pulse) { position: absolute; inset: 0; border-radius: 50%; background: rgba(var(--af-glow-rgb), 0.25); animation: lm-pulse 2s ease-out infinite; }
:deep(.lm-rider__dot) { position: absolute; inset: 7px; display: grid; place-items: center; border-radius: 50%; background: var(--af-glow-c); color: var(--af-on-glow); border: 3px solid var(--af-surface-solid); box-shadow: 0 4px 14px rgba(var(--af-deep-rgb), 0.45); }
:deep(.lm-rider__dot.is-sim) { background: var(--af-accent-on-deep); }
@keyframes lm-pulse { 0% { transform: scale(0.6); opacity: 1; } 100% { transform: scale(1.6); opacity: 0; } }
@media (prefers-reduced-motion: reduce) { :deep(.lm-rider__pulse) { animation: none; } }
</style>
