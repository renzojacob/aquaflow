"""
Trip planning: group orders into trips (one per vehicle), put each trip's stops in a
sensible order, and work out the load, distance and arrival times.

No paid map service is used. Distances are straight-line (haversine) x ROAD_FACTOR, so every
trip is marked distance_is_estimate = True. Good enough for a small city; say so in the manuscript.

How the grouping works ("sweep" method):
  1. Stand at the station and sort the orders by compass direction, so neighbours sit together.
  2. Fill the first vehicle with orders in that order until the containers no longer fit,
     then the next vehicle, and so on. An order that doesn't fit is skipped, a later one may.
  3. Order the stops of each trip with nearest-stop-first, then a 2-opt pass that removes crossings.
Orders that fit no vehicle are returned with the reason, never dropped silently.
"""
from datetime import datetime, timedelta
from math import atan2, ceil, pi

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.delivery.tracking import MINUTES_PER_STOP, ROAD_FACTOR, TRICYCLE_KMH, station_point
from apps.orders.models import Order
from apps.orders.services import PERIOD_START
from apps.station.geo import haversine_m

from .models import Trip, TripChangeLog, TripStop, Vehicle

S = Order.Status
PLANNABLE = (S.CONFIRMED, S.PREPARING, S.READY)
SPEED_MPS = TRICYCLE_KMH * 1000 / 3600


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _pt(o):
    return float(o.lat), float(o.lng)


def _road_m(a, b):
    return haversine_m(a[0], a[1], b[0], b[1]) * ROAD_FACTOR


def unplanned_orders(day, period=None):
    """Orders that can go on a trip but are not on one yet."""
    on_trip = TripStop.objects.exclude(status=TripStop.Status.FAILED).values("order_id")
    qs = (Order.objects.filter(delivery_date=day, status__in=PLANNABLE)
          .exclude(pk__in=on_trip)
          .select_related("customer", "address").prefetch_related("items__product")
          .order_by("period", "id"))
    return qs.filter(period=period) if period else qs


# ---------------------------------------------------------------------------
# Load and route numbers
# ---------------------------------------------------------------------------
def load_profile(orders):
    """
    Containers on the vehicle, in delivery order.
    Full containers leave at the start; each stop hands over `containers` and takes back
    `expected_empties`. Returns (departure, peak, [on_board_after_each_stop]).
    """
    departure = sum(o.containers for o in orders)
    on_board, peak, after = departure, departure, []
    for o in orders:
        on_board = on_board - o.containers + o.expected_empties
        after.append(on_board)
        peak = max(peak, on_board)
    return departure, peak, after


def capacity_error(vehicle, orders):
    """None if the load fits, otherwise a plain-English message for the dispatcher."""
    _, peak, _ = load_profile(orders)
    if peak > vehicle.capacity_containers:
        return (f"{vehicle.name} holds {vehicle.capacity_containers} containers but this trip "
                f"needs {peak}. Remove an order or pick a bigger vehicle.")
    return None


def best_sequence(orders, start=None):
    """Nearest-stop-first from the station, then 2-opt on the round trip."""
    orders = list(orders)
    if len(orders) < 2:
        return orders
    start = start or station_point()

    left, here, route = orders[:], start, []
    while left:
        nxt = min(left, key=lambda o: _road_m(here, _pt(o)))
        route.append(nxt)
        left.remove(nxt)
        here = _pt(nxt)

    def tour_len(seq):
        pts = [start] + [_pt(o) for o in seq] + [start]
        return sum(_road_m(pts[i], pts[i + 1]) for i in range(len(pts) - 1))

    best, best_len, improved = route, tour_len(route), len(route) > 2
    while improved:
        improved = False
        for i in range(len(best) - 1):
            for j in range(i + 1, len(best)):
                cand = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                cand_len = tour_len(cand)
                if cand_len + 1 < best_len:
                    best, best_len, improved = cand, cand_len, True
    return best


def route_numbers(orders, day, period, start=None):
    """Distance (with the way back), drive+stop time, and an arrival time for every stop."""
    start = start or station_point()
    leave = timezone.make_aware(datetime.combine(day, PERIOD_START[period]))
    here, clock, dist, etas = start, leave, 0.0, []
    for o in orders:
        leg = _road_m(here, _pt(o))
        dist += leg
        clock += timedelta(seconds=leg / SPEED_MPS)
        etas.append(clock)
        clock += timedelta(minutes=MINUTES_PER_STOP)
        here = _pt(o)
    back = _road_m(here, start) if orders else 0
    dist += back
    total_s = (clock - leave).total_seconds() + back / SPEED_MPS
    return round(dist), ceil(total_s), etas


def write_stops(trip, orders):
    """Replace a trip's stops with `orders` (already in delivery order) and refresh every number."""
    trip.stops.all().delete()
    _, _, after = load_profile(orders)
    dist, secs, etas = route_numbers(orders, trip.date, trip.period)
    TripStop.objects.bulk_create([
        TripStop(trip=trip, order=o, sequence=i + 1, expected_load_after=after[i], eta=etas[i])
        for i, o in enumerate(orders)
    ])
    trip.total_distance_m, trip.total_duration_s, trip.distance_is_estimate = dist, secs, True
    trip.save(update_fields=["total_distance_m", "total_duration_s", "distance_is_estimate", "updated_at"])


def bump_version(trip):
    Trip.objects.filter(pk=trip.pk).update(version=F("version") + 1)
    trip.refresh_from_db()


# ---------------------------------------------------------------------------
# One button: plan the whole slot
# ---------------------------------------------------------------------------
def _sweep_order(orders, start):
    """Sort by compass direction from the station, cutting the circle at its biggest gap."""
    if len(orders) < 2:
        return list(orders)
    ang = sorted(((atan2(float(o.lat) - start[0], float(o.lng) - start[1]), o) for o in orders),
                 key=lambda t: t[0])
    gaps = [(ang[(i + 1) % len(ang)][0] - ang[i][0]) % (2 * pi) for i in range(len(ang))]
    cut = (gaps.index(max(gaps)) + 1) % len(ang)
    return [o for _, o in ang[cut:] + ang[:cut]]


@transaction.atomic
def plan_slot(day, period, by):
    """
    Build draft trips for the day and period. Old drafts are replaced; approved, downloaded and
    running trips are never touched. Returns (new_trips, [(order, reason)]).
    """
    old = Trip.objects.filter(date=day, period=period, status=Trip.Status.DRAFT)
    kept_vehicles = list(Trip.objects.filter(date=day, period=period).exclude(status=Trip.Status.DRAFT)
                         .values_list("vehicle_id", flat=True))
    old.delete()

    start = station_point()
    queue = _sweep_order(list(unplanned_orders(day, period)), start)
    vehicles = list(Vehicle.objects.filter(is_available=True).exclude(pk__in=kept_vehicles)
                    .order_by("-capacity_containers", "id"))
    biggest = max((v.capacity_containers for v in vehicles), default=0)

    leftovers, trips = [], []
    for v in vehicles:
        if not queue:
            break
        load, picked = 0, []
        for o in list(queue):
            if load + o.containers <= v.capacity_containers:
                picked.append(o)
                load += o.containers
                queue.remove(o)
        if not picked:
            continue
        trip = Trip.objects.create(date=day, period=period, vehicle=v, created_by=by)
        ordered = best_sequence(picked, start)
        write_stops(trip, ordered)
        for o in ordered:
            TripChangeLog.objects.create(trip=trip, action=TripChangeLog.Action.PLANNED, order=o,
                                         by_user=by, after={"vehicle": v.name})
        trips.append(trip)

    for o in queue:
        if not vehicles and not kept_vehicles:
            why = "No vehicle is available. Add one on the Vehicles screen."
        elif o.containers > biggest:
            why = f"Needs {o.containers} containers, but the biggest free vehicle holds {biggest}."
        else:
            why = "All vehicles are full for this time. Add a vehicle or move the order to another time."
        leftovers.append((o, why))
    return trips, leftovers
