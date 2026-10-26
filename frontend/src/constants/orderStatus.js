// Order statuses. The keys MUST match the backend's status values exactly.
// Each status has one label, one color tone, one icon, and a customer-friendly
// timeline sentence. Color is never the only signal: the pill always shows the word too.
import {
  banOutline,
  checkmarkCircleOutline,
  checkmarkOutline,
  closeOutline,
  cubeOutline,
  timeOutline,
  warningOutline,
  waterOutline,
} from 'ionicons/icons'

export const ORDER_STATUS = Object.freeze({
  pending: { label: 'Pending', tone: 'pending', icon: timeOutline, timeline: 'Order placed' },
  confirmed: { label: 'Confirmed', tone: 'confirmed', icon: checkmarkOutline, timeline: 'Confirmed by the station' },
  preparing: { label: 'Preparing', tone: 'preparing', icon: waterOutline, timeline: 'Containers being filled' },
  ready_for_pickup: { label: 'Ready for Pickup', tone: 'ready', icon: cubeOutline, timeline: 'Loaded and ready' },
  out_for_delivery: { label: 'Out for Delivery', tone: 'out', icon: null, live: true, timeline: 'Out for delivery' },
  delivered: { label: 'Delivered', tone: 'delivered', icon: checkmarkCircleOutline, timeline: 'Delivered' },
  rejected: { label: 'Rejected', tone: 'rejected', icon: banOutline, timeline: 'Rejected by the station' },
  cancelled: { label: 'Cancelled', tone: 'cancelled', icon: closeOutline, timeline: 'Cancelled' },
  failed_delivery: { label: 'Failed Delivery', tone: 'failed', icon: warningOutline, timeline: 'Delivery attempt failed' },
})

/** The happy path, in order. */
export const ORDER_FLOW = ['pending', 'confirmed', 'preparing', 'ready_for_pickup', 'out_for_delivery', 'delivered']

/** Statuses that end an order for good. */
export const FINAL_STATUSES = ['delivered', 'rejected', 'cancelled']

/** A failed delivery is re-planned once. After the 2nd failed attempt the order is closed. */
export const MAX_ATTEMPTS = 2

/** Is this order still in progress? */
export function isActive(order) {
  if (FINAL_STATUSES.includes(order.status)) return false
  if (order.status === 'failed_delivery' && order.attempts >= MAX_ATTEMPTS) return false
  return true
}

/** Customers may cancel only before the containers are being prepared. */
export const CUSTOMER_CANCELLABLE = ['pending', 'confirmed']

/** Staff may cancel any time before the order leaves the station. */
export const STAFF_CANCELLABLE = ['confirmed', 'preparing', 'ready_for_pickup', 'failed_delivery']

/** Orders that hold ready stock (reserved on confirm, released when they leave or are cancelled). */
export const RESERVING_STATUSES = ['confirmed', 'preparing', 'ready_for_pickup']

/**
 * What the dispatcher can do next, by status.
 * The backend enforces the same table; the app only uses it to show buttons.
 */
export const DISPATCHER_NEXT = Object.freeze({
  pending: [
    { action: 'confirm', label: 'Confirm order', variant: 'primary' },
    { action: 'reject', label: 'Reject', variant: 'danger' },
  ],
  confirmed: [
    { action: 'prepare', label: 'Start preparing', variant: 'primary' },
    { action: 'cancel', label: 'Cancel order', variant: 'danger' },
  ],
  preparing: [
    { action: 'ready', label: 'Mark ready for pickup', variant: 'primary' },
    { action: 'cancel', label: 'Cancel order', variant: 'danger' },
  ],
  ready_for_pickup: [{ action: 'cancel', label: 'Cancel order', variant: 'danger' }],
  failed_delivery: [
    { action: 'replan', label: 'Re-plan for next trip', variant: 'primary' },
    { action: 'cancel', label: 'Cancel order', variant: 'danger' },
  ],
})
