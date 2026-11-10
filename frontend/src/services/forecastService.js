// Demand forecast for the owner and dispatcher: orders and containers per day, the next 7 or 14 days.
// Real mode: GET /api/v1/dispatch/forecast (backend/apps/dispatch/forecast_api.py).
// Mock mode: a SAMPLE built from a made-up weekly pattern, labelled as sample numbers in `warnings`.
import { env } from '@/config/env'
import { mockDelay } from '@/mocks/db'
import { dateISO } from '@/utils/format'

import { http } from './http'

const STAFF = '/api/v1/dispatch'

/**
 * @typedef {{ date: string, value: number, lower: number | null, upper: number | null }} ForecastDay
 * @typedef {{ method: string, label: string, chosen: boolean, mae: number | null, rmse: number | null, wape: number | null }} BacktestRow
 * @typedef {Object} ForecastBlock
 * @property {string | null} method          naive | weekday_average | holt_winters
 * @property {string | null} method_label
 * @property {boolean} enough_data
 * @property {number} history_days
 * @property {number} backtest_rounds         weeks the methods were tested on
 * @property {number | null} interval_level   0.8 = an 80% band
 * @property {ForecastDay[]} days
 * @property {BacktestRow[]} backtest
 * @typedef {Object} TripsHint
 * @property {number} vehicles
 * @property {number} average_capacity
 * @property {number} fleet_trips_per_day
 * @property {string | null} peak_date
 * @property {string[]} over_capacity_days
 * @property {string} note
 * @property {{ date: string, containers: number, trips_needed: number, riders_needed: number,
 *   busy_trips_needed: number, busy_riders_needed: number, fleet_enough: boolean }[]} days
 * @typedef {Object} Forecast
 * @property {7 | 14} days
 * @property {boolean} enough_data
 * @property {{ start: string | null, end: string | null,
 *   orders: { date: string, value: number }[], containers: { date: string, value: number }[] }} history
 * @property {ForecastBlock} orders
 * @property {ForecastBlock} containers
 * @property {string[]} warnings
 * @property {TripsHint | null} trips
 * @property {string} explanation
 */

/**
 * The forecast. `days` is 7 or 14.
 * @param {7 | 14} [days]
 * @returns {Promise<Forecast>}
 */
export async function getForecast(days = 7) {
  if (env.useMock) {
    await mockDelay(250)
    return sample(days)
  }
  const { data } = await http.get(`${STAFF}/forecast`, { params: { days } })
  return data
}

// ---------- sample for demo mode ----------

const WEEK = [14, 15, 15, 17, 24, 22, 11] // orders, Monday .. Sunday
const BOXES = 2.1
const BANDS = [3, 4]
const iso = (d) => dateISO(d)
const weekdayOf = (offset) => (new Date(iso(offset) + 'T00:00:00').getDay() + 6) % 7

function sample(days) {
  const history = Array.from({ length: 28 }, (_, i) => {
    const off = i - 28
    return { date: iso(off), value: WEEK[weekdayOf(off)] + ((i * 7) % 5) - 2 }
  })
  const block = (scale) => ({
    method: 'weekday_average',
    method_label: 'Weekday average (last 4 weeks)',
    enough_data: true,
    history_days: 84,
    horizon: days,
    backtest_rounds: 9,
    interval_level: 0.8,
    holt_winters_params: null,
    days: Array.from({ length: days }, (_, k) => {
      const v = Math.round(WEEK[weekdayOf(k)] * scale * 100) / 100
      return { date: iso(k), value: v, lower: Math.round((v - BANDS[0] * scale) * 100) / 100, upper: Math.round((v + BANDS[1] * scale) * 100) / 100 }
    }),
    backtest: [
      { method: 'naive', label: 'Naive (same as the last day)', chosen: false, mae: 4.8 * scale, rmse: 6.6 * scale, wape: 0.256 },
      { method: 'weekday_average', label: 'Weekday average (last 4 weeks)', chosen: true, mae: 2.5 * scale, rmse: 3.4 * scale, wape: 0.135 },
      { method: 'holt_winters', label: 'Holt-Winters (trend + weekly pattern)', chosen: false, mae: 3.1 * scale, rmse: 4 * scale, wape: 0.167 },
    ],
  })
  const orders = block(1)
  const boxes = block(BOXES)
  const peak = orders.days.reduce((a, b) => (b.value > a.value ? b : a))
  const tripDays = boxes.days.map((d) => {
    const t = Math.ceil(d.value / 20)
    const busy = Math.ceil(d.upper / 20)
    return { date: d.date, containers: d.value, trips_needed: t, riders_needed: Math.ceil(t / 2), busy_trips_needed: busy, busy_riders_needed: Math.ceil(busy / 2), fleet_enough: busy <= 4 }
  })
  return {
    days,
    generated_on: iso(0),
    timezone: 'Asia/Manila',
    enough_data: true,
    history: { start: history[0].date, end: history.at(-1).date, orders: history, containers: history.map((h) => ({ date: h.date, value: Math.round(h.value * BOXES) })) },
    orders,
    containers: boxes,
    warnings: ['These are SAMPLE numbers from demo mode, not your real orders.'],
    trips: {
      vehicles: 2, total_capacity: 40, average_capacity: 20, fleet_trips_per_day: 4, days: tripDays,
      peak_date: peak.date, over_capacity_days: tripDays.filter((t) => !t.fleet_enough).map((t) => t.date),
      note: 'Rough planning number from the average vehicle size. It ignores routes and distances; the Plan screen makes the real trips.',
    },
    explanation: `Expect about ${Math.round(peak.value)} orders on the busiest day in the next ${days} days. (Sample numbers for demo mode.)`,
  }
}
