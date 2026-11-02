// The cart: what an order contains, in words people read.
// Every order has `items` (lines), `containers` (refills only: station containers swapped)
// and `total`. Very old orders without lines are shown as one refill line.
import { cubeOutline, iceCreamOutline, waterOutline } from 'ionicons/icons'

/** What each kind of product means, for labels and icons. */
export const KIND = Object.freeze({
  refill: { label: 'Refill', note: 'We swap it for your empty', icon: waterOutline },
  container: { label: 'New container', note: 'Yours to keep', icon: cubeOutline },
  item: { label: 'Extra', note: '', icon: iceCreamOutline },
})

/** The lines of an order (never empty). */
export function linesOf(order) {
  if (order?.items?.length) return order.items
  return [{
    product_id: null,
    name: '5-gallon refill',
    kind: 'refill',
    quantity: order?.quantity ?? 0,
    unit_price: order?.unit_price ?? 0,
    line_total: order?.total ?? 0,
  }]
}

/** Station containers swapped by this order (refills only). */
export const refillsOf = (order) => order?.containers ?? linesOf(order).filter((l) => l.kind === 'refill').reduce((s, l) => s + l.quantity, 0)

/** "3 × 5-gallon refill, 1 × Ice tube" */
export const linesText = (order) => linesOf(order).map((l) => `${l.quantity} × ${l.name}`).join(', ')

/** Short: "3 refills" / "3 refills + 2 more" / "1 new container" */
export function cartShort(order) {
  const lines = linesOf(order)
  const refills = lines.filter((l) => l.kind === 'refill').reduce((s, l) => s + l.quantity, 0)
  const others = lines.filter((l) => l.kind !== 'refill').reduce((s, l) => s + l.quantity, 0)
  if (refills && others) return `${refills} refill${refills > 1 ? 's' : ''} + ${others} more`
  if (refills) return `${refills} refill${refills > 1 ? 's' : ''}`
  if (lines.length === 1) return `${lines[0].quantity} × ${lines[0].name}`
  return `${others} item${others > 1 ? 's' : ''}`
}

/** Query string to put the same cart on the order screen: "items=3:3,7:1&address=5" */
export function reorderQuery(order) {
  const lines = linesOf(order).filter((l) => l.product_id != null)
  const items = lines.length ? `items=${lines.map((l) => `${l.product_id}:${l.quantity}`).join(',')}` : `qty=${order.quantity}`
  return `${items}&address=${order.address.id}`
}

/** Add lines/containers/total to an order that doesn't have them yet (demo data, old orders). */
export function withCart(order, productsById = {}) {
  if (order.items?.length && order.containers != null) return order
  const p = productsById.p_refill
  const items = order.items?.length
    ? order.items
    : [{ product_id: p?.id ?? 'p_refill', name: p?.name ?? '5-gallon refill', kind: 'refill', quantity: order.quantity, unit_price: order.unit_price, line_total: order.unit_price * order.quantity }]
  return { ...order, items, containers: items.filter((l) => l.kind === 'refill').reduce((s, l) => s + l.quantity, 0), total: order.total ?? items.reduce((s, l) => s + l.line_total, 0) }
}
