// Data shapes shared by the app and the backend (JSDoc only, no runtime code).
// Keep these in sync with the FastAPI Pydantic schemas.

/**
 * @typedef {'customer' | 'dispatcher' | 'rider' | 'owner'} Role
 *
 * @typedef {Object} User
 * @property {string} id
 * @property {Role} role
 * @property {string} full_name
 * @property {string} email
 * @property {string} phone
 * @property {number} [containers_held]  customers only: station containers at their home
 *
 * @typedef {Object} AuthResult
 * @property {string} token   JWT (mock mode: "mock.<userId>")
 * @property {User} user
 *
 * @typedef {Object} Address
 * @property {string} id
 * @property {string} label       "Home", "Work"...
 * @property {string} barangay
 * @property {string} street
 * @property {string} landmark    what the rider can see: gate color, store, school
 * @property {number} lat
 * @property {number} lng
 * @property {boolean} [is_default]
 *
 * @typedef {'pending'|'confirmed'|'preparing'|'ready_for_pickup'|'out_for_delivery'|'delivered'|'rejected'|'cancelled'|'failed_delivery'} OrderStatus
 *
 * @typedef {Object} StatusEvent
 * @property {OrderStatus} status
 * @property {string} at      ISO timestamp
 * @property {string} [note]  reason for rejected / cancelled / failed
 *
 * @typedef {Object} Order
 * @property {string} id
 * @property {string} code               "AF-1048"
 * @property {number} quantity           5-gallon containers
 * @property {number} empties_to_return  empty containers the customer hands back
 * @property {number} unit_price
 * @property {number} total
 * @property {Address} address           copy of the address at order time
 * @property {string} delivery_date      "YYYY-MM-DD"
 * @property {'morning'|'afternoon'} period
 * @property {string} notes
 * @property {OrderStatus} status
 * @property {number} attempts           delivery attempts so far
 * @property {string} delivery_code      4 digits; customer gives it to the rider
 * @property {{code: string, rider_name: string, stops_before: number} | null} trip
 * @property {string} created_at
 * @property {StatusEvent[]} history
 *
 * @typedef {Object} OrderSettings
 * @property {number} price_per_container
 * @property {number} max_containers_per_order
 * @property {{morning: string, afternoon: string}} cutoff   "HH:MM" for same-day orders
 * @property {{name: string, address: string, lat: number, lng: number}} station
 * @property {number} service_radius_km
 */

export {}
