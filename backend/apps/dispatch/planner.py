"""
Trip planning: group orders into trips (one per vehicle), put each trip's stops in a
sensible order, and work out the load, distance and arrival times.

Distances and times come from OpenRouteService (routing.py) when ORS_API_KEY is set: a road
distance matrix to choose the stop order, and the road route for the trip's numbers and map line.
Without a key, or if ORS fails, they fall back to straight-line (haversine) x ROAD_FACTOR and the
trip is marked distance_is_estimate = True.

How the grouping works ("sweep" method):
  1. Stand at the station and sort the orders by compass direction, so neighbours sit together.
  2. Fill the first vehicle with orders in that order until the containers no longer fit,
     then the next vehicle, and so on. An order that doesn't fit is skipped, a later one may.
  3. Order the stops of each trip with nearest-stop-first, then a 2-opt pass that removes crossings
     (both on road distances from the ORS matrix: one request per trip).
Orders that fit no vehicle are returned with the reason, never dropped silently.
"""
from datetime import datetime, timedelta
from math import atan2, ceil, pi

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.delivery.tracking import MINUTES_PER_STOP, TRICYCLE_KMH, station_point
from apps.orders.models import Order
from apps.orders.services import PERIOD_START

from . import routing
from .models import Trip, TripChangeLog, TripStop, Vehicle

S = Order.Status
PLANNABLE = (S.CONFIRMED, S.PREPARING, S.READY)
SPEED_MPS = TRICYCLE_KMH * 1000 / 3600


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _pt(o):
    return float(o.lat), float(o.lng)


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
    """Nearest-stop-first from the station, then 2-opt on the round trip (road distances)."""
    orders = list(orders)
    if len(orders) < 2:
        return orders
    start = start or station_point()

    # One matrix for the station + every stop: index 0 is the station, order k is index k + 1
    m = routing.matrix([start] + [_pt(o) for o in orders])
    idx = {id(o): k + 1 for k, o in enumerate(orders)}
    d = lambda a, b: m.distance(a, b)

    left, here, route = orders[:], 0, []
    while left:
        nxt = min(left, key=lambda o: d(here, idx[id(o)]))
        route.append(nxt)
        left.remove(nxt)
        here = idx[id(nxt)]

    def tour_len(seq):
        pts = [0] + [idx[id(o)] for o in seq] + [0]
        return sum(d(pts[i], pts[i + 1]) for i in range(len(pts) - 1))

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
    """
    Distance (with the way back), drive+stop time, an arrival time for every stop, the road
    line for the map, and whether it's an estimate. Returns (meters, seconds, etas, line, estimate).
    """
    start = start or station_point()
    leave = timezone.make_aware(datetime.combine(day, PERIOD_START[period]))
    points = [start] + [_pt(o) for o in orders] + [start]

    road = routing.directions(points) if orders else None
    if road:
        legs, line, estimate = road["legs"], road["line"], False
    else:
        legs = [routing.straight_leg(points[i], points[i + 1]) for i in range(len(points) - 1)]
        line, estimate = None, True

    clock, dist, etas = leave, 0.0, []
    for k, (meters, secs) in enumerate(legs):
        dist += meters
        # ORS times are for a car; a loaded tricycle is never faster than TRICYCLE_KMH
        clock += timedelta(seconds=max(secs, meters / SPEED_MPS))
        if k < len(orders):                      # the last leg is the way back
            etas.append(clock)
            clock += timedelta(minutes=MINUTES_PER_STOP)
    total_s = (clock - leave).total_seconds()
    return round(dist), ceil(total_s), etas, line, estimate


def write_stops(trip, orders):
    """Replace a trip's stops with `orders` (already in delivery order) and refresh every number."""
    trip.stops.all().delete()
    _, _, after = load_profile(orders)
    dist, secs, etas, line, estimate = route_numbers(orders, trip.date, trip.period)
    TripStop.objects.bulk_create([
        TripStop(trip=trip, order=o, sequence=i + 1, expected_load_after=after[i], eta=etas[i])
        for i, o in enumerate(orders)
    ])
    trip.total_distance_m, trip.total_duration_s, trip.distance_is_estimate = dist, secs, estimate
    trip.route_line = line
    trip.save(update_fields=["total_distance_m", "total_duration_s", "distance_is_estimate",
                             "route_line", "updated_at"])


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
