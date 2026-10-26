// Translates between the Django API and the shapes our screens use (see types/models.js).
// Screens never see backend field names; if the API changes, only this file changes.

// Django uses shorter names for two statuses
const STATUS_FROM_API = { ready: 'ready_for_pickup', failed: 'failed_delivery' }
const STATUS_TO_API = { ready_for_pickup: 'ready', failed_delivery: 'failed' }

export const statusFromApi = (s) => STATUS_FROM_API[s] ?? s
export const statusToApi = (s) => STATUS_TO_API[s] ?? s

const num = (v) => (v === null || v === undefined || v === '' ? null : Number(v))
// The API accepts at most 6 decimal places for coordinates
const round6 = (v) => Number(Number(v).toFixed(6))

/** API address -> app Address */
export function toAddress(a) {
  return {
    id: a.id,
    label: a.label || '',
    barangay: a.barangay || '',
    street: a.street || a.address_text || '',
    landmark: a.landmark || '',
    lat: num(a.lat),
    lng: num(a.lng),
    is_default: Boolean(a.is_default),
  }
}

/** app Address -> API body */
export function fromAddress(a) {
  return {
    label: (a.label || '').trim(),
    barangay: (a.barangay || '').trim(),
    street: (a.street || '').trim(),
    landmark: (a.landmark || '').trim(),
    lat: round6(a.lat),
    lng: round6(a.lng),
  }
}

/** API order -> app Order */
export function toOrder(o) {
  const history = (o.history || []).map((h) => ({
    status: statusFromApi(h.to_status),
    at: h.server_time,
    ...(h.note ? { note: h.note } : {}),
  }))
  return {
    id: o.id,
    code: `AF-${o.id}`,
    quantity: o.quantity,
    empties_to_return: o.expected_empties,
    unit_price: num(o.unit_price),
    total: num(o.total),
    address: {
      id: o.address,
      label: o.address_label || '',
      barangay: o.address_barangay || '',
      street: o.address_street || o.address_text || '',
      landmark: o.landmark || '',
      lat: num(o.lat),
      lng: num(o.lng),
    },
    delivery_date: o.delivery_date,
    period: o.period,
    notes: o.notes || '',
    status: statusFromApi(o.status),
    attempts: history.filter((h) => h.status === 'failed_delivery').length,
    delivery_code: o.confirmation_code,
    trip: null, // filled in when trips are connected
    created_at: o.created_at,
    history,
    rejection_reason: o.rejection_reason || '',
    cancel_reason: o.cancel_reason || '',
  }
}

/** app "new order" form -> API body */
export function toOrderPayload(p) {
  return {
    address: p.address_id,
    quantity: p.quantity,
    delivery_date: p.delivery_date,
    period: p.period,
    expected_empties: p.empties_to_return,
    notes: (p.notes || '').trim(),
  }
}