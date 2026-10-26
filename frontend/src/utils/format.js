// Small formatting helpers so every screen shows money, dates and times the same way.

const pesoFormat = new Intl.NumberFormat('en-PH', {
  style: 'currency',
  currency: 'PHP',
  maximumFractionDigits: 0,
})

/** 90 -> "₱90" */
export function peso(amount) {
  return pesoFormat.format(amount ?? 0)
}

/** Date -> "2026-10-23" in the device's local time (Philippines on our phones). */
export function toISODate(date = new Date()) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/** Today + n days, as "YYYY-MM-DD". */
export function dateISO(offsetDays = 0) {
  const d = new Date()
  d.setDate(d.getDate() + offsetDays)
  return toISODate(d)
}

/** "2026-10-23" -> "Today" / "Tomorrow" / "Yesterday" / "Fri, Oct 23" */
export function friendlyDay(isoDate) {
  if (!isoDate) return ''
  if (isoDate === dateISO(0)) return 'Today'
  if (isoDate === dateISO(1)) return 'Tomorrow'
  if (isoDate === dateISO(-1)) return 'Yesterday'
  const [y, m, d] = isoDate.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-PH', { weekday: 'short', month: 'short', day: 'numeric' })
}

/** ISO timestamp -> "8:35 AM" */
export function timeOf(isoDateTime) {
  if (!isoDateTime) return ''
  return new Date(isoDateTime).toLocaleTimeString('en-PH', { hour: 'numeric', minute: '2-digit' })
}

/** ISO timestamp -> "Today, 8:35 AM" or "Oct 20, 8:35 AM" */
export function dateTimeOf(isoDateTime) {
  if (!isoDateTime) return ''
  const day = friendlyDay(toISODate(new Date(isoDateTime)))
  return `${day}, ${timeOf(isoDateTime)}`
}

/** "14:00" -> "2:00 PM" */
export function clockLabel(hhmm) {
  const [h, m] = hhmm.split(':').map(Number)
  const suffix = h >= 12 ? 'PM' : 'AM'
  return `${((h + 11) % 12) + 1}:${String(m).padStart(2, '0')} ${suffix}`
}

/** Delivery periods, shared by every screen. */
export const PERIODS = Object.freeze({
  morning: { label: 'Morning', hours: '8 AM – 12 NN' },
  afternoon: { label: 'Afternoon', hours: '1 PM – 5 PM' },
})

/** "Good morning" / "Good afternoon" / "Good evening" */
export function greeting(now = new Date()) {
  const h = now.getHours()
  if (h < 12) return 'Good morning'
  if (h < 18) return 'Good afternoon'
  return 'Good evening'
}

/** "Maria Santos" -> "MS" */
export function initials(name = '') {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join('')
}

/** 1 -> "1 container", 3 -> "3 containers" */
export function containers(n) {
  return `${n} ${n === 1 ? 'container' : 'containers'}`
}
