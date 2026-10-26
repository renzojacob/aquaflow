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

  // Add the other Calapan customers and the station's orders for today
  const station = createStationSeed()
  return {
    ...base,
    users: [...base.users, ...station.users],
    addresses: [...base.addresses, ...station.addresses],
    orders: [...base.orders, ...station.orders],
    inventory: station.inventory,
    stock_log: station.stock_log,
  }
}
