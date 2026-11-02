// Rider location sharing. One shared state for the whole app (keeps going between rider screens).
//
// Two ways to share:
//   live  real GPS from the phone (navigator.geolocation.watchPosition).
//         Browsers only allow GPS on https:// or on localhost. On http://192.168.x.x it is blocked.
//   demo  a "demo drive": moves the rider toward their next stop and sends those points to the
//         server exactly like real GPS, marked is_simulated so everyone can see it's a demo.
import { reactive, readonly } from 'vue'
import { sendLocation } from '@/services/riderService'
import { distanceKm } from '@/utils/geo'

const state = reactive({
  mode: 'off',        // off | live | demo
  status: 'off',      // off | asking | live | denied | insecure | unsupported | error | demo | arrived
  position: null,     // { lat, lng, accuracy_m, heading, at }
  lastSentAt: null,
  error: '',
})

let watchId = null
let timer = null
let lastSent = null
let getTarget = () => null

const meters = (a, b) => distanceKm(a, b) * 1000
const bearing = (a, b) => {
  const toRad = (d) => (d * Math.PI) / 180
  const y = Math.sin(toRad(b.lng - a.lng)) * Math.cos(toRad(b.lat))
  const x = Math.cos(toRad(a.lat)) * Math.sin(toRad(b.lat)) - Math.sin(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.cos(toRad(b.lng - a.lng))
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360
}

async function push(point, simulated, force = false) {
  state.position = { ...point, at: new Date().toISOString() }
  // Real GPS: send at most every 8 s unless the rider moved 20 m+ (saves data and battery)
  if (!force && !simulated && lastSent && Date.now() - lastSent.t < 8000 && meters(lastSent, point) < 20) return
  try {
    await sendLocation({ ...point, is_simulated: simulated })
    lastSent = { ...point, t: Date.now() }
    state.lastSentAt = new Date().toISOString()
    state.error = ''
  } catch (e) {
    state.error = e.message // keep trying on the next point
  }
}

function clearAll() {
  if (watchId !== null) navigator.geolocation?.clearWatch(watchId)
  watchId = null
  clearInterval(timer)
  timer = null
}

/** Real GPS. Returns the status it ended in. */
export function startLive() {
  clearAll()
  state.mode = 'live'
  if (!window.isSecureContext) return (state.status = 'insecure')
  if (!('geolocation' in navigator)) return (state.status = 'unsupported')
  state.status = 'asking'
  watchId = navigator.geolocation.watchPosition(
    (pos) => {
      state.status = 'live'
      const c = pos.coords
      push({ lat: c.latitude, lng: c.longitude, accuracy_m: c.accuracy, heading: Number.isFinite(c.heading) ? c.heading : undefined, speed_mps: Number.isFinite(c.speed) ? c.speed : undefined }, false, !lastSent)
    },
    (err) => {
      state.status = err.code === 1 ? 'denied' : 'error'
      state.error = err.code === 1 ? 'Location permission was blocked.' : err.message
    },
    { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 },
  )
  return state.status
}

/**
 * Demo drive: from `from` toward whatever `target()` returns (the next stop), at a sped-up
 * town pace so the customer's map visibly moves. Stops at the door and waits.
 * @param {{lat:number,lng:number}} from
 * @param {() => ({lat:number,lng:number} | null)} target
 */
export function startDemo(from, target) {
  clearAll()
  getTarget = target
  state.mode = 'demo'
  state.status = 'demo'
  let here = { ...(state.position ?? from) }
  let t = 0
  const STEP_S = 2
  const SPEED = 16 // m/s on the map (about 4x a real tricycle, so a demo doesn't take 10 minutes)
  push({ lat: here.lat, lng: here.lng, accuracy_m: 5 }, true, true)
  timer = setInterval(() => {
    const dest = getTarget()
    if (!dest) return
    const left = meters(here, dest)
    if (left < 15) {
      state.status = 'arrived'
      return push({ lat: dest.lat, lng: dest.lng, accuracy_m: 5 }, true)
    }
    state.status = 'demo'
    t += 1
    const f = Math.min(1, (SPEED * STEP_S) / left)
    // a slight sideways wobble so the path looks like streets, not a ruler
    const wobble = Math.sin(t / 3) * 0.00004 * (1 - f)
    const next = {
      lat: here.lat + (dest.lat - here.lat) * f + wobble,
      lng: here.lng + (dest.lng - here.lng) * f - wobble,
    }
    const heading = bearing(here, next)
    here = next
    push({ lat: next.lat, lng: next.lng, accuracy_m: 5, heading, speed_mps: SPEED }, true)
  }, STEP_S * 1000)
}

/** Point the demo drive at a new target (e.g. after a delivery). */
export function retarget(target) {
  getTarget = target
}

export function stopSharing() {
  clearAll()
  state.mode = 'off'
  state.status = 'off'
}

export function useRiderLocation() {
  return { location: readonly(state), startLive, startDemo, retarget, stopSharing }
}
