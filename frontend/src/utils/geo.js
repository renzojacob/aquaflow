// Distance between two map points in kilometers (haversine formula).
// Used to check if an address is inside the station's delivery area.
export function distanceKm(a, b) {
  const R = 6371
  const toRad = (deg) => (deg * Math.PI) / 180
  const dLat = toRad(b.lat - a.lat)
  const dLng = toRad(b.lng - a.lng)
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(h))
}

/** true if `point` is within `area.radiusKm` of `area` (center). */
export function insideArea(point, area) {
  if (!point || !area) return false
  return distanceKm(point, area) <= area.radiusKm
}
