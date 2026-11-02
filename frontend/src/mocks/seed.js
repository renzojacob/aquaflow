// Fake but realistic Calapan data for MOCK mode (VITE_USE_MOCK=true).
// Times are made relative to "now", so the demo always looks current.
// Bump SEED_VERSION in db.js whenever this file changes, so browsers reload it.
import { dateISO } from '@/utils/format'
import { createStationSeed } from './seedStation'

const minutesAgo = (m) => new Date(Date.now() - m * 60_000).toISOString()
const daysAgo = (d, hour = 9, minute = 0) => {
  const t = new Date()
  t.setDate(t.getDate() - d)
  t.setHours(hour, minute, 0, 0)
  return t.toISOString()
}

export function createSeed() {
  const nowPeriod = new Date().getHours() < 12 ? 'morning' : 'afternoon'

  const home = {
    id: 'a_maria_home',
    user_id: 'u_maria',
    label: 'Home',
    barangay: 'Camilmil',
    street: 'Purok 3, Mabini St.',
    landmark: 'Blue gate beside the chapel',
    lat: 13.4057,
    lng: 121.1849,
    is_default: true,
  }
  const mother = {
    id: 'a_maria_mother',
    user_id: 'u_maria',
    label: "Mama's house",
    barangay: 'Lalud',
    street: 'Rizal St.',
    landmark: 'Across Lalud Elementary School',
    lat: 13.3993,
    lng: 121.1719,
    is_default: false,
  }
  const snap = (a) => ({ id: a.id, label: a.label, barangay: a.barangay, street: a.street, landmark: a.landmark, lat: a.lat, lng: a.lng })

  const base = {
    settings: {
      price_per_container: 30,
      max_containers_per_order: 10,
      // Orders for TODAY must be placed before these times (24h "HH:MM")
      cutoff: { morning: '09:00', afternoon: '14:00' },
      station: {
        name: 'AquaFlow Refilling Station',
        address: 'J.P. Rizal St., San Vicente Central, Calapan City',
        lat: 13.4108,
        lng: 121.1792,
      },
      service_radius_km: 8,
      // What customers can put in the cart (Owner > Products & prices edits these)
      products: [
        { id: 'p_refill', name: '5-gallon refill', kind: 'refill', price: 30, description: 'Round container, purified water', max_per_order: 10, sort_order: 1, is_active: true },
        { id: 'p_slim', name: '5-gallon slim refill', kind: 'refill', price: 35, description: 'Slim container with a faucet', max_per_order: 10, sort_order: 2, is_active: true },
        { id: 'p_jug', name: 'New 5-gallon container', kind: 'container', price: 250, description: 'Filled, sealed, yours to keep', max_per_order: 3, sort_order: 3, is_active: true },
        { id: 'p_gallon', name: '1-gallon bottle', kind: 'item', price: 15, description: 'Sealed bottle, good for travel', max_per_order: 10, sort_order: 4, is_active: true },
        { id: 'p_ice', name: 'Tube ice, 1 kg', kind: 'item', price: 25, description: 'Made with purified water', max_per_order: 6, sort_order: 5, is_active: true },
      ],
    },

    // MOCK ONLY: real passwords are hashed in the backend and never sent to the app.
    users: [
      { id: 'u_maria', role: 'customer', full_name: 'Maria Santos', email: 'maria@aquaflow.test', phone: '09175550142', password: 'aquaflow123', containers_held: 3 },
      { id: 'u_joy', role: 'dispatcher', full_name: 'Joy Dela Cruz', email: 'joy@aquaflow.test', phone: '09185550111', password: 'aquaflow123' },
      { id: 'u_jomar', role: 'rider', full_name: 'Jomar Reyes', email: 'jomar@aquaflow.test', phone: '09195550123', password: 'aquaflow123' },
      { id: 'u_ramon', role: 'owner', full_name: 'Ramon Villanueva', email: 'owner@aquaflow.test', phone: '09205550100', password: 'aquaflow123' },
    ],

    addresses: [home, mother],

    orders: [
      {
        id: 'o_1048',
        code: 'AF-1048',
        customer_id: 'u_maria',
        quantity: 3,
        empties_to_return: 2,
        unit_price: 30,
        total: 90,
        address: snap(home),
        delivery_date: dateISO(0),
        period: nowPeriod,
        notes: '',
        status: 'out_for_delivery',
        attempts: 1,
        delivery_code: '4827',
        trip: { code: 'T-02', rider_name: 'Jomar Reyes', stops_before: 1 },
        rider: { id: 'u_jomar', name: 'Jomar Reyes', phone: '09195550123' },
        created_at: minutesAgo(70),
        history: [
          { status: 'pending', at: minutesAgo(70) },
          { status: 'confirmed', at: minutesAgo(62) },
          { status: 'preparing', at: minutesAgo(48) },
          { status: 'ready_for_pickup', at: minutesAgo(30) },
          { status: 'out_for_delivery', at: minutesAgo(18) },
        ],
      },
      {
        id: 'o_1031',
        code: 'AF-1031',
        customer_id: 'u_maria',
        quantity: 3,
        empties_to_return: 3,
        unit_price: 30,
        total: 90,
        address: snap(home),
        delivery_date: dateISO(-3),
        period: 'morning',
        notes: '',
        status: 'delivered',
        attempts: 1,
        delivery_code: '1290',
        trip: null,
        created_at: daysAgo(3, 7, 40),
        history: [
          { status: 'pending', at: daysAgo(3, 7, 40) },
          { status: 'confirmed', at: daysAgo(3, 7, 52) },
          { status: 'preparing', at: daysAgo(3, 8, 10) },
          { status: 'ready_for_pickup', at: daysAgo(3, 8, 30) },
          { status: 'out_for_delivery', at: daysAgo(3, 8, 45) },
          { status: 'delivered', at: daysAgo(3, 9, 12) },
        ],
      },
      {
        id: 'o_1019',
        code: 'AF-1019',
        customer_id: 'u_maria',
        quantity: 2,
        empties_to_return: 0,
        unit_price: 30,
        total: 60,
        address: snap(mother),
        delivery_date: dateISO(-8),
        period: 'afternoon',
        notes: 'For Mama, please knock loudly',
        status: 'delivered',
        attempts: 1,
        delivery_code: '5531',
        trip: null,
        created_at: daysAgo(8, 11, 5),
        history: [
          { status: 'pending', at: daysAgo(8, 11, 5) },
          { status: 'confirmed', at: daysAgo(8, 11, 20) },
          { status: 'preparing', at: daysAgo(8, 12, 40) },
          { status: 'ready_for_pickup', at: daysAgo(8, 13, 5) },
          { status: 'out_for_delivery', at: daysAgo(8, 13, 20) },
          { status: 'delivered', at: daysAgo(8, 14, 2) },
        ],
      },
      {
        id: 'o_1012',
        code: 'AF-1012',
        customer_id: 'u_maria',
        quantity: 4,
        empties_to_return: 3,
        unit_price: 30,
        total: 120,
        address: snap(home),
        delivery_date: dateISO(-12),
        period: 'morning',
        notes: '',
        status: 'cancelled',
        attempts: 0,
        delivery_code: '7745',
        trip: null,
        created_at: daysAgo(12, 7, 15),
        history: [
          { status: 'pending', at: daysAgo(12, 7, 15) },
          { status: 'cancelled', at: daysAgo(12, 7, 21), note: 'Ordered twice by mistake' },
        ],
      },
      {
        id: 'o_1004',
        code: 'AF-1004',
        customer_id: 'u_maria',
        quantity: 3,
        empties_to_return: 2,
        unit_price: 30,
        total: 90,
        address: snap(home),
        delivery_date: dateISO(-16),
        period: 'afternoon',
        notes: '',
        status: 'delivered',
        attempts: 2,
        delivery_code: '3018',
        trip: null,
        created_at: daysAgo(17, 16, 0),
        history: [
          { status: 'pending', at: daysAgo(17, 16, 0) },
          { status: 'confirmed', at: daysAgo(17, 16, 10) },
          { status: 'preparing', at: daysAgo(16, 12, 30) },
          { status: 'ready_for_pickup', at: daysAgo(16, 13, 0) },
          { status: 'out_for_delivery', at: daysAgo(16, 13, 15) },
          { status: 'failed_delivery', at: daysAgo(16, 13, 50), note: 'No one was home' },
          { status: 'ready_for_pickup', at: daysAgo(16, 14, 30), note: 'Re-planned for the next trip' },
          { status: 'out_for_delivery', at: daysAgo(16, 15, 0) },
          { status: 'delivered', at: daysAgo(16, 15, 25) },
        ],
      },
    ],

    counters: { order: 1071, address: 10 },
  }

  // Older deliveries for Maria (2-3 months back) so her spending chart has a trend
  const olderDays = [24, 31, 39, 46, 53, 61, 68, 77, 85]
  olderDays.forEach((d, i) => {
    const qty = [3, 2, 3, 4, 3, 2, 3, 3, 2][i]
    const id = 990 - i
    base.orders.push({
      id: `o_${id}`,
      code: `AF-${id}`,
      customer_id: 'u_maria',
      quantity: qty,
      empties_to_return: qty - 1,
      unit_price: 30,
      total: qty * 30,
      address: snap(i % 4 === 3 ? mother : home),
      delivery_date: dateISO(-d),
      period: i % 3 === 0 ? 'afternoon' : 'morning',
      notes: '',
      status: 'delivered',
      attempts: 1,
      delivery_code: String(1100 + id),
      trip: null,
      rider: { id: 'u_jomar', name: 'Jomar Reyes', phone: '09195550123' },
      created_at: daysAgo(d, 7, 30),
      history: [
        { status: 'pending', at: daysAgo(d, 7, 30) },
        { status: 'confirmed', at: daysAgo(d, 7, 45) },
        { status: 'preparing', at: daysAgo(d, 8, 5) },
        { status: 'ready_for_pickup', at: daysAgo(d, 8, 25) },
        { status: 'out_for_delivery', at: daysAgo(d, 8, 40) },
        { status: 'delivered', at: daysAgo(d, 9, 10) },
      ],
    })
  })

  // Add the other Calapan customers and the station's orders for today
  const station = createStationSeed()
  const byId = Object.fromEntries(base.settings.products.map((p) => [p.id, p]))
  // A few demo orders with mixed carts, so lines show up everywhere
  const extras = { o_1048: [['p_ice', 2]], o_1061: [['p_jug', 1]], o_1062: [['p_gallon', 6], ['p_ice', 3]], o_1050: [['p_ice', 1]] }
  const withLines = (o) => {
    const items = [{ product_id: 'p_refill', name: byId.p_refill.name, kind: 'refill', quantity: o.quantity, unit_price: o.unit_price, line_total: o.unit_price * o.quantity }]
    for (const [pid, q] of extras[o.id] ?? []) items.push({ product_id: pid, name: byId[pid].name, kind: byId[pid].kind, quantity: q, unit_price: byId[pid].price, line_total: byId[pid].price * q })
    const total = items.reduce((s, l) => s + l.line_total, 0)
    return { ...o, items, containers: o.quantity, quantity: items.reduce((s, l) => s + l.quantity, 0), total }
  }
  return {
    ...base,
    users: [...base.users, ...station.users],
    addresses: [...base.addresses, ...station.addresses],
    orders: [...base.orders, ...station.orders].map(withLines),
    inventory: { ...station.inventory, others: { p_slim: 12, p_jug: 8, p_gallon: 40, p_ice: 15 } },
    stock_log: station.stock_log,
  }
}
