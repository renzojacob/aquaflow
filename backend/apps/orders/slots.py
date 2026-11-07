"""
Feature D: neighborhood batching and slot capacity.

When a customer picks a delivery period, they see how much room is left in it, and whether a
trip is already planned near their pin ("Delivery nearby"). place_order() uses the same numbers,
so nobody is promised a slot the fleet can't serve.

  capacity   = containers the fleet carries in one period. A vehicle makes at most one trip per
               period (unique constraint on Trip), so this is the sum of vehicle capacities:
               vehicles switched on, plus any switched-off vehicle that already has a trip there.
  booked     = containers on orders for that day and period that still need the trip
               (pending counts: a slot is held from the moment the customer orders).
  remaining  = capacity - booked, never below 0.
  nearby     = a stop on a not-yet-departed trip in that period within nearby_radius_m
               (SystemSetting, default 1 km) of the pin, on a trip that still has room.

If the owner has not added any vehicle yet, capacity is unknown: nothing is blocked
(limited = False), the same way an unset service area blocks nothing.
"""
from dataclasses import asdict, dataclass

from django.db import connection
from django.db.models import Q, Sum

from apps.dispatch.models import Trip, TripStop, Vehicle
from apps.station.geo import haversine_m
from apps.station.models import SystemSetting

from .models import Order

S = Order.Status

# Orders that no longer need room on the trip. A failed delivery went back to stock; if the
# dispatcher re-plans it, it becomes confirmed again and counts again.
NOT_BOOKED = (S.REJECTED, S.CANCELLED, S.FAILED)

# Trips a new order can still join. Out/completed trips have already left the station.
JOINABLE = (Trip.Status.DRAFT, Trip.Status.APPROVED, Trip.Status.DOWNLOADED)

# Shown as "almost full" when this little room is left (or less than 20% of capacity).
ALMOST_FULL_CONTAINERS = 5


@dataclass
class SlotAvailability:
    date: str
    period: str
    limited: bool            # False = no vehicles set up yet, so capacity isn't checked
    capacity: int | None
    booked: int
    remaining: int | None
    full: bool
    almost_full: bool
    fits: bool               # does the requested quantity fit?
    delivery_nearby: bool

    def as_dict(self):
        return asdict(self)


def lock_slot(day, period):
    """
    Serialize bookings for one day + period until the transaction ends, so two customers
    can't both take the last containers. A Postgres advisory lock: other slots aren't blocked.
    """
    key = day.toordinal() * 2 + (1 if period == Order.Period.AFTERNOON else 0)
    with connection.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(%s, %s)", [0xAF10, key])


def fleet_capacity(day, period):
    """Containers the fleet can carry in this period, or None if no vehicle exists yet."""
    if not Vehicle.objects.exists():
        return None
    with_trip = Trip.objects.filter(date=day, period=period).values("vehicle_id")
    total = (Vehicle.objects.filter(Q(is_available=True) | Q(pk__in=with_trip))
             .aggregate(n=Sum("capacity_containers"))["n"])
    return total or 0


def booked_containers(day, period, exclude_order=None):
    qs = Order.objects.filter(delivery_date=day, period=period).exclude(status__in=NOT_BOOKED)
    if exclude_order is not None:
        qs = qs.exclude(pk=exclude_order.pk)
    return qs.aggregate(n=Sum("containers"))["n"] or 0


def delivery_nearby(day, period, lat, lng, containers=1, radius_m=None):
    """True if a trip that hasn't left yet stops within radius_m of (lat, lng) and has room."""
    if lat is None or lng is None:
        return False
    radius_m = radius_m if radius_m is not None else SystemSetting.load().nearby_radius_m
    stops = (TripStop.objects.filter(trip__date=day, trip__period=period, trip__status__in=JOINABLE)
             .exclude(status=TripStop.Status.FAILED)
             .select_related("trip__vehicle", "order"))
    load, room_needed, near = {}, max(containers, 1), set()
    for s in stops:
        t = s.trip
        load[t.pk] = load.get(t.pk, 0) + s.order.containers
        if t.pk not in near and haversine_m(lat, lng, s.order.lat, s.order.lng) <= radius_m:
            near.add(t.pk)
    for trip_id in near:
        cap = next(s.trip.vehicle.capacity_containers for s in stops if s.trip_id == trip_id)
        if cap - load[trip_id] >= room_needed:
            return True
    return False


def slot_availability(day, period, *, lat=None, lng=None, containers=0, exclude_order=None):
    capacity = fleet_capacity(day, period)
    booked = booked_containers(day, period, exclude_order)
    if capacity is None:
        remaining, full, almost, fits = None, False, False, True
    else:
        remaining = max(capacity - booked, 0)
        full = remaining == 0
        almost = not full and remaining <= max(ALMOST_FULL_CONTAINERS, capacity // 5)
        fits = containers <= remaining
    return SlotAvailability(
        date=day.isoformat(), period=period, limited=capacity is not None,
        capacity=capacity, booked=booked, remaining=remaining, full=full, almost_full=almost,
        fits=fits, delivery_nearby=delivery_nearby(day, period, lat, lng, containers or 1),
    )


def full_slot_message(availability, period_label):
    if availability.remaining == 0:
        return f"{period_label} is fully booked for that day. Please pick another time."
    left = availability.remaining
    return (f"Only {left} container{'s' if left != 1 else ''} left for {period_label.lower()}. "
            f"Order {left} or fewer, or pick another time.")
