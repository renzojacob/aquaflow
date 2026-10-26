// More Calapan customers + today's and tomorrow's orders, so the
// dispatcher has a realistic queue in mock mode.
import { dateISO } from '@/utils/format'

const CUSTOMERS = [
  { id: 'u_ana', name: 'Ana Reyes', phone: '09171230001', barangay: 'Ibaba East', street: 'P. Burgos St.', landmark: 'Sari-sari store with red awning', lat: 13.4146, lng: 121.1841 },
  { id: 'u_ben', name: 'Benjie Castillo', phone: '09171230002', barangay: 'Sta. Isabel', street: 'Purok 2', landmark: 'Beside the basketball court', lat: 13.4037, lng: 121.1752 },
  { id: 'u_carla', name: 'Carla Mendoza', phone: '09171230003', barangay: 'Lalud', street: 'Ilang-Ilang St.', landmark: 'Green house, mango tree in front', lat: 13.3982, lng: 121.1704 },
  { id: 'u_dan', name: 'Ramos Carinderia', phone: '09171230004', barangay: 'Calero', street: 'Roxas Drive', landmark: 'Ramos Carinderia sign', lat: 13.4171, lng: 121.1878 },
  { id: 'u_ella', name: 'Ella Bautista', phone: '09171230005', barangay: 'Guinobatan', street: 'Purok 5', landmark: 'White gate near the barangay hall', lat: 13.3874, lng: 121.1822 },
  { id: 'u_fe', name: 'Fe Navarro', phone: '09171230006', barangay: 'Bayanan I', street: 'Mabini Ext.', landmark: 'Across the water tank', lat: 13.3957, lng: 121.1898 },
  { id: 'u_gio', name: 'Gio Villareal', phone: '09171230007', barangay: 'Tawiran', street: 'Coastal Rd.', landmark: 'Blue boat beside the house', lat: 13.4231, lng: 121.1716 },
  { id: 'u_hana', name: 'Hana Lim', phone: '09171230008', barangay: 'Sto. Niño', street: 'Luna St.', landmark: 'Pink 2-storey house', lat: 13.4006, lng: 121.1836 },
  { id: 'u_ivan', name: 'Ivan Torres', phone: '09171230009', barangay: 'Suqui', street: 'Purok 1', landmark: 'Near Suqui chapel', lat: 13.4224, lng: 121.1893 },
  { id: 'u_jen', name: 'Jen Aquino', phone: '09171230010', barangay: 'Libis', street: 'Del Pilar St.', landmark: 'Yellow gate, corner lot', lat: 13.4176, lng: 121.1755 },
]

const FLOW = ['pending', 'confirmed', 'preparing', 'ready_for_pickup', 'out_for_delivery', 'delivered']

const minutesAgo = (m) => new Date(Date.now() - m * 60_000).toISOString()

/**
 * One order. `status` is where it is now; history is filled up to it.
 * startedMinutesAgo = when the order was placed.
 */
function makeOrder(n, c, { qty, empties, day, period, status, startedMinutesAgo, notes = '', final }) {
  const steps = FLOW.slice(0, FLOW.indexOf(status === 'rejected' || status === 'cancelled' ? 'pending' : status) + 1)
  const gap = Math.max(4, Math.floor(startedMinutesAgo / (steps.length + 1)))
  const history = steps.map((s, i) => ({ status: s, at: minutesAgo(startedMinutesAgo - i * gap), by: i === 0 ? 'customer' : 'Joy Dela Cruz' }))
  if (final) history.push({ status: final.status, at: minutesAgo(Math.max(1, startedMinutesAgo - steps.length * gap)), note: final.note, by: 'Joy Dela Cruz' })
  return {
    id: `o_${n}`,
    code: `AF-${n}`,
    customer_id: c.id,
    quantity: qty,
    empties_to_return: empties,
    unit_price: 30,
    total: qty * 30,
    address: { id: `a_${c.id}`, label: 'Home', barangay: c.barangay, street: c.street, landmark: c.landmark, lat: c.lat, lng: c.lng },
    delivery_date: dateISO(day),
    period,
    notes,
    status: final ? final.status : status,
    attempts: ['out_for_delivery', 'delivered'].includes(status) ? 1 : 0,
    delivery_code: String(2000 + ((n * 37) % 7000)),
    trip: status === 'out_for_delivery' ? { code: 'T-02', rider_name: 'Jomar Reyes', stops_before: 0 } : null,
    created_at: history[0].at,
    history,
  }
}

export function createStationSeed() {
  const [ana, ben, carla, dan, ella, fe, gio, hana, ivan, jen] = CUSTOMERS
  const users = CUSTOMERS.map((c) => ({
    id: c.id,
    role: 'customer',
    full_name: c.name,
    email: `${c.id.slice(2)}@example.com`,
    phone: c.phone,
    password: 'aquaflow123',
    containers_held: 4,
  }))
  const addresses = CUSTOMERS.map((c) => ({
    id: `a_${c.id}`,
    user_id: c.id,
    label: 'Home',
    barangay: c.barangay,
    street: c.street,
    landmark: c.landmark,
    lat: c.lat,
    lng: c.lng,
    is_default: true,
  }))

  const orders = [
    // Waiting for the dispatcher
    makeOrder(1061, ana, { qty: 4, empties: 4, day: 0, period: 'afternoon', status: 'pending', startedMinutesAgo: 25 }),
    makeOrder(1062, dan, { qty: 8, empties: 6, day: 0, period: 'afternoon', status: 'pending', startedMinutesAgo: 18, notes: 'Carinderia, deliver at the back door' }),
    makeOrder(1063, gio, { qty: 2, empties: 1, day: 0, period: 'afternoon', status: 'pending', startedMinutesAgo: 12 }),
    makeOrder(1064, ivan, { qty: 3, empties: 3, day: 0, period: 'afternoon', status: 'pending', startedMinutesAgo: 6 }),
    makeOrder(1070, jen, { qty: 5, empties: 4, day: 1, period: 'morning', status: 'pending', startedMinutesAgo: 40 }),
    makeOrder(1071, ella, { qty: 3, empties: 2, day: 1, period: 'morning', status: 'pending', startedMinutesAgo: 33 }),
    // In progress
    makeOrder(1055, ben, { qty: 3, empties: 3, day: 0, period: 'afternoon', status: 'confirmed', startedMinutesAgo: 70 }),
    makeOrder(1056, hana, { qty: 2, empties: 2, day: 0, period: 'afternoon', status: 'confirmed', startedMinutesAgo: 64 }),
    makeOrder(1052, carla, { qty: 4, empties: 3, day: 0, period: 'afternoon', status: 'preparing', startedMinutesAgo: 95 }),
    makeOrder(1050, fe, { qty: 5, empties: 5, day: 0, period: 'afternoon', status: 'ready_for_pickup', startedMinutesAgo: 120 }),
    makeOrder(1051, ella, { qty: 2, empties: 2, day: 0, period: 'afternoon', status: 'ready_for_pickup', startedMinutesAgo: 115 }),
    // On the road / done today
    makeOrder(1047, jen, { qty: 3, empties: 3, day: 0, period: 'morning', status: 'out_for_delivery', startedMinutesAgo: 150 }),
    makeOrder(1041, ana, { qty: 3, empties: 3, day: 0, period: 'morning', status: 'delivered', startedMinutesAgo: 300 }),
    makeOrder(1042, ben, { qty: 2, empties: 2, day: 0, period: 'morning', status: 'delivered', startedMinutesAgo: 290 }),
    makeOrder(1043, hana, { qty: 4, empties: 3, day: 0, period: 'morning', status: 'delivered', startedMinutesAgo: 280 }),
    makeOrder(1044, gio, { qty: 6, empties: 0, day: 0, period: 'morning', status: 'pending', startedMinutesAgo: 270, final: { status: 'rejected', note: 'Outside delivery area' } }),
    makeOrder(1045, carla, { qty: 2, empties: 2, day: 0, period: 'morning', status: 'pending', startedMinutesAgo: 260, final: { status: 'cancelled', note: 'Customer bought from a neighbor' } }),
  ]

  return {
    users,
    addresses,
    orders,
    // Station stock. "Reserved" is not stored: it is the total of confirmed,
    // preparing and ready orders, computed when needed.
    inventory: { filled_ready: 30, empty_at_station: 42, owned_total: 220 },
    stock_log: [
      { at: minutesAgo(200), type: 'refill', delta: 20, reason: 'Morning refill batch', by: 'Joy Dela Cruz' },
      { at: minutesAgo(420), type: 'correction', delta: -2, reason: 'Two containers cracked', by: 'Joy Dela Cruz' },
    ],
  }
}
