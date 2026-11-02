"""
Live tracking: where a rider is, which stop comes next, how far and how long.
Used by the rider app (their stop list) and the customer's tracking map, so both agree.

ETA is an estimate: straight-line distance x ROAD_FACTOR (streets aren't straight),
at TRICYCLE_KMH (a loaded tricycle in Calapan town traffic). Shown to people as "about".
"""
from datetime import timedelta
from math import ceil

from django.utils import timezone

from apps.orders.models import Order
from apps.station.geo import haversine_m
from apps.station.models import ServiceArea, Station

from .models import RiderLocation

ROAD_FACTOR = 1.35
TRICYCLE_KMH = 18
FRESH_FOR = timedelta(minutes=10)      # older than this = "location not updated recently"
MINUTES_PER_STOP = 4                    # handing over containers + collecting cash


def station_point():
    s = Station.objects.first()
    if s:
        return float(s.lat), float(s.lng)
    a = ServiceArea.objects.first()
    if a:
        return float(a.center_lat), float(a.center_lng)
    return 13.4117, 121.1803  # Calapan City


def last_location(rider):
    """The rider's newest point, or None. Includes whether it is fresh."""
    loc = RiderLocation.objects.filter(rider=rider).first()
    if loc is None:
        return None
    return {
        "lat": float(loc.lat),
        "lng": float(loc.lng),
        "accuracy_m": loc.accuracy_m,
        "heading": loc.heading,
        "speed_mps": loc.speed_mps,
        "is_simulated": loc.is_simulated,
        "at": loc.server_time.isoformat(),
        "fresh": timezone.now() - loc.server_time <= FRESH_FOR,
    }


def drive_minutes(distance_m):
    road_m = distance_m * ROAD_FACTOR
    return max(1, ceil(road_m / (TRICYCLE_KMH * 1000 / 60)))


def route_for(rider):
    """
    The rider's orders on the road, in the order they'll likely be delivered:
    always the nearest remaining stop next, starting from where the rider is now
    (or the station if we don't know).
    Returns [(order, distance_from_previous_point_m)].
    """
    remaining = list(
        Order.objects.filter(assigned_rider=rider, status=Order.Status.OUT_FOR_DELIVERY)
        .select_related("customer", "address").prefetch_related("items__product")
    )
    loc = last_location(rider)
    here = (loc["lat"], loc["lng"]) if loc and loc["fresh"] else station_point()
    ordered = []

    # Orders on a trip follow the sequence the dispatcher approved
    from apps.dispatch.models import TripStop
    seq = dict(TripStop.objects.filter(order__in=remaining, status=TripStop.Status.PENDING,
                                       trip__rider=rider).values_list("order_id", "sequence"))
    for o in sorted((o for o in remaining if o.pk in seq), key=lambda o: seq[o.pk]):
        ordered.append((o, haversine_m(here[0], here[1], o.lat, o.lng)))
        here = (float(o.lat), float(o.lng))
    remaining = [o for o in remaining if o.pk not in seq]

    # Anything sent out directly: nearest remaining stop next
    while remaining:
        nxt = min(remaining, key=lambda o: haversine_m(here[0], here[1], o.lat, o.lng))
        dist = haversine_m(here[0], here[1], nxt.lat, nxt.lng)
        ordered.append((nxt, dist))
        remaining.remove(nxt)
        here = (float(nxt.lat), float(nxt.lng))
    return ordered


def track_payload(order):
    """What the customer's tracking map needs for one order."""
    data = {
        "status": order.status,
        "destination": {"lat": float(order.lat), "lng": float(order.lng)},
        "station": dict(zip(("lat", "lng"), station_point())),
        "rider": None,
        "location": None,
        "stops_before": None,
        "distance_m": None,
        "eta_minutes": None,
    }
    rider = order.assigned_rider
    if order.status != Order.Status.OUT_FOR_DELIVERY or rider is None:
        return data

    data["rider"] = {"name": rider.get_full_name() or rider.username, "phone": rider.phone}
    loc = last_location(rider)
    data["location"] = loc

    route = route_for(rider)
    idx = next((i for i, (o, _) in enumerate(route) if o.pk == order.pk), None)
    if idx is not None:
        data["stops_before"] = idx
        # distance along the route: each earlier stop, then this one
        total_m = sum(d for _, d in route[: idx + 1])
        data["distance_m"] = round(total_m * ROAD_FACTOR)
        data["eta_minutes"] = drive_minutes(total_m) + idx * MINUTES_PER_STOP
    return data
