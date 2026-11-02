// Turns a customer's own orders into the numbers their screens show.
// Everything here is computed from real orders: nothing is estimated or invented.
import { ORDER_STATUS } from '@/constants/orderStatus'
import { monthShort } from './format'

const sameMonth = (a, b) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth()

/** The day an order counts for: its delivery date (local), so a month's total matches the receipts. */
const dayOf = (o) => {
  const [y, m, d] = o.delivery_date.split('-').map(Number)
  return new Date(y, m - 1, d)
}

/**
 * @param {Array} orders  every order of one customer
 * @param {number} months how many months the chart covers (current month included)
 */
export function orderStats(orders, months = 6, now = new Date()) {
  const delivered = orders.filter((o) => o.status === 'delivered')

  const buckets = []
  for (let i = months - 1; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const inMonth = delivered.filter((o) => sameMonth(dayOf(o), d))
    buckets.push({
      label: monthShort(d),
      sub: d.toLocaleDateString('en-PH', { month: 'long', year: 'numeric' }),
      spent: inMonth.reduce((s, o) => s + o.total, 0),
      containers: inMonth.reduce((s, o) => s + o.quantity, 0),
      count: inMonth.length,
    })
  }

  const thisMonth = orders.filter((o) => sameMonth(dayOf(o), now) && !['cancelled', 'rejected'].includes(o.status))
  const thisMonthDelivered = thisMonth.filter((o) => o.status === 'delivered')

  // Average days between deliveries (needs 2+ deliveries)
  const dates = delivered.map(dayOf).sort((a, b) => a - b)
  let everyDays = null
  if (dates.length >= 2) everyDays = Math.round((dates.at(-1) - dates[0]) / 86_400_000 / (dates.length - 1))

  // Most used address among delivered orders
  const byAddr = {}
  for (const o of delivered) byAddr[o.address.label] = (byAddr[o.address.label] ?? 0) + 1
  const favorite = Object.entries(byAddr).sort((a, b) => b[1] - a[1])[0]?.[0] ?? null

  return {
    months: buckets,
    thisMonth: {
      count: thisMonth.length,
      delivered: thisMonthDelivered.length,
      spent: thisMonthDelivered.reduce((s, o) => s + o.total, 0),
      containers: thisMonthDelivered.reduce((s, o) => s + o.quantity, 0),
    },
    allTime: {
      orders: orders.length,
      delivered: delivered.length,
      containers: delivered.reduce((s, o) => s + o.quantity, 0),
      returned: delivered.reduce((s, o) => s + (o.empties_to_return ?? 0), 0),
      spent: delivered.reduce((s, o) => s + o.total, 0),
      cancelled: orders.filter((o) => ['cancelled', 'rejected'].includes(o.status)).length,
    },
    everyDays,
    favorite,
    usualQty: mostCommon(delivered.map((o) => o.quantity)),
  }
}

function mostCommon(list) {
  if (!list.length) return null
  const n = {}
  for (const v of list) n[v] = (n[v] ?? 0) + 1
  return Number(Object.entries(n).sort((a, b) => b[1] - a[1])[0][0])
}

/** What a customer reads for each status change in an activity feed. */
const FEED_TEXT = {
  pending: 'You placed',
  confirmed: 'The station confirmed',
  preparing: 'The station started filling',
  ready_for_pickup: 'Loaded and ready:',
  out_for_delivery: 'On the way:',
  delivered: 'Delivered:',
  rejected: 'The station could not take',
  cancelled: 'Cancelled:',
  failed_delivery: "We couldn't deliver",
}

/** Every status change across the orders, newest first: [{ id, at, status, text, code, orderId, note, tone }] */
export function activityFeed(orders, limit = 6) {
  const events = []
  for (const o of orders) {
    for (const h of o.history ?? []) {
      events.push({
        id: `${o.id}-${h.status}-${h.at}`,
        at: h.at,
        status: h.status,
        orderId: o.id,
        code: o.code,
        text: FEED_TEXT[h.status] ?? ORDER_STATUS[h.status]?.label ?? h.status,
        note: h.note ?? '',
        quantity: o.quantity,
      })
    }
  }
  return events.sort((a, b) => b.at.localeCompare(a.at)).slice(0, limit)
}
