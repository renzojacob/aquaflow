"""
Rider API: what the rider's phone uses while delivering.
URL prefix: /api/v1/rider/

  GET  today                     my stops (nearest first), what I finished today, totals
  POST location                  a GPS point (real or demo drive)
  POST orders/<id>/deliver       {code, empties_collected, lat, lng, accuracy_m, no_code}
  POST orders/<id>/fail          {failure_reason, note, lat, lng, accuracy_m}

  GET  trips                     my approved/downloaded/out trips, today onward
  POST trips/<id>/download       the offline copy: stops, details, coordinates, HASHED codes
  POST trips/<id>/start          {device_time?}  loads the vehicle: every stop -> out for delivery

The rules live in delivery.services.record_attempt (code check, geofence, containers,
stock, per-address stats), so this file only reads the request and answers.
"""
import secrets

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsRider
from apps.dispatch import services as dispatch_services
from apps.dispatch.models import Trip, TripStop
from apps.orders.models import Order
from apps.station.models import SystemSetting

from .models import DeliveryAttempt, RiderLocation
from .services import record_attempt
from .tracking import MINUTES_PER_STOP, ROAD_FACTOR, drive_minutes, last_location, route_for, station_point

FAIL_TEXT = {
    "absent": "No one was home",
    "wrong_address": "Could not find the address",
    "refused": "Customer refused the delivery",
    "other": "Could not deliver",
}


def _num(value, name, lo, hi):
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValidationError({name: ["Send a number."]})
    if not lo <= v <= hi:
        raise ValidationError({name: [f"Must be between {lo} and {hi}."]})
    return v


def _gps(data):
    """Optional GPS fields sent with a delivery: (lat, lng, accuracy) or Nones."""
    if data.get("lat") in (None, "") or data.get("lng") in (None, ""):
        return None, None, None
    acc = data.get("accuracy_m")
    return (
        round(_num(data["lat"], "lat", -90, 90), 6),
        round(_num(data["lng"], "lng", -180, 180), 6),
        float(acc) if acc not in (None, "") else None,
    )


def stop_row(order, sequence=None, leg_m=None, eta=None):
    c = order.customer
    return {
        "id": order.id,
        "code": f"AF-{order.id}",
        "status": order.status,
        "sequence": sequence,
        "customer": {"name": c.get_full_name() or c.username, "phone": c.phone},
        "quantity": order.quantity,
        "containers": order.containers,
        "items": [{"name": i.product.name, "kind": i.product.kind, "quantity": i.quantity} for i in order.items.all()],
        "expected_empties": order.expected_empties,
        "total": float(order.total),
        "notes": order.notes,
        "period": order.period,
        "delivery_date": order.delivery_date.isoformat(),
        "address": {
            "label": order.address.label if order.address_id else "",
            "street": getattr(order.address, "street", "") or order.address_text,
            "barangay": getattr(order.address, "barangay", ""),
            "landmark": order.landmark,
            "lat": float(order.lat),
            "lng": float(order.lng),
        },
        "leg_m": round(leg_m * ROAD_FACTOR) if leg_m is not None else None,
        "eta_minutes": eta,
    }


def _my_order(request, pk):
    return get_object_or_404(
        Order.objects.select_related("customer", "address", "product"),
        pk=pk, assigned_rider=request.user,
    )


def _my_stop(order, rider):
    """The trip stop for this order, if it went out on one of my trips (None for direct dispatch)."""
    return (TripStop.objects.filter(order=order, status=TripStop.Status.PENDING, trip__rider=rider)
            .select_related("trip").first())


class TodayView(APIView):
    permission_classes = [IsRider]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        route = route_for(request.user)
        stops, minutes = [], 0
        for i, (o, leg) in enumerate(route):
            minutes += drive_minutes(leg) + (MINUTES_PER_STOP if i else 0)
            stops.append(stop_row(o, i + 1, leg, minutes))

        today = timezone.localdate()
        attempts = (
            DeliveryAttempt.objects.filter(rider=request.user, server_time__date=today)
            .select_related("order__customer", "order__address").prefetch_related("order__items__product")
            .order_by("-server_time")
        )
        done = []
        for a in attempts:
            row = stop_row(a.order)
            row.update({
                "outcome": a.outcome,
                "at": a.server_time.isoformat(),
                "empties_collected": a.empties_collected,
                "code_ok": a.code_ok,
                "distance_from_pin_m": a.distance_from_pin_m,
                "geofence_flagged": a.geofence_flagged,
                "failure": FAIL_TEXT.get(a.failure_reason, "") if a.outcome == "failed" else "",
            })
            done.append(row)
        delivered = [d for d in done if d["outcome"] == "delivered"]
        return Response({
            "stops": stops,
            "done": done,
            "totals": {
                "to_collect": sum(s["total"] for s in stops),
                "on_board": sum(s["quantity"] for s in stops),
                "collected": sum(d["total"] for d in delivered),
                "delivered": len(delivered),
                "containers": sum(d["containers"] for d in delivered),
                "empties": sum(d["empties_collected"] for d in delivered),
                "failed": len(done) - len(delivered),
                "minutes_left": minutes,
            },
            "station": dict(zip(("lat", "lng"), station_point())),
            # road line of the trip I'm on (null for a straight-line estimate or no trip)
            "route_line": (Trip.objects.filter(rider=request.user, status=Trip.Status.OUT)
                           .order_by("-updated_at")
                           .values_list("route_line", flat=True).first()),
            "location": last_location(request.user),
            "geofence_m": SystemSetting.load().geofence_threshold_m,
        })


class LocationView(APIView):
    permission_classes = [IsRider]

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        d = request.data
        when = parse_datetime(str(d.get("recorded_at") or "")) or timezone.now()
        opt = lambda k, lo, hi: _num(d[k], k, lo, hi) if d.get(k) not in (None, "") else None
        loc = RiderLocation.objects.create(
            rider=request.user,
            lat=round(_num(d.get("lat"), "lat", -90, 90), 6),
            lng=round(_num(d.get("lng"), "lng", -180, 180), 6),
            accuracy_m=opt("accuracy_m", 0, 100000),
            heading=opt("heading", 0, 360),
            speed_mps=opt("speed_mps", 0, 100),
            is_simulated=bool(d.get("is_simulated")),
            device_time=when,
        )
        # keep the table small: a rider only needs their recent trail
        old = RiderLocation.objects.filter(rider=request.user).values_list("pk", flat=True)[500:]
        if old:
            RiderLocation.objects.filter(pk__in=list(old)).delete()
        return Response({"saved_at": loc.server_time.isoformat()}, status=201)


class DeliverView(APIView):
    permission_classes = [IsRider]

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def post(self, request, pk):
        order = _my_order(request, pk)
        if order.status != Order.Status.OUT_FOR_DELIVERY:
            raise ValidationError(f"This order is '{order.status.replace('_', ' ')}', not on the road.")
        d = request.data
        code = str(d.get("code") or "").strip()
        no_code = bool(d.get("no_code"))
        if not no_code:
            if not code:
                raise ValidationError({"code": ["Ask the customer for the code in their app."]})
            if not secrets.compare_digest(code, order.confirmation_code):
                raise ValidationError({"code": ["That code doesn't match. Ask the customer to read it again from their app."]})
        try:
            empties = int(d.get("empties_collected", order.expected_empties))
        except (TypeError, ValueError):
            raise ValidationError({"empties_collected": ["Enter a whole number."]})
        if not 0 <= empties <= 50:
            raise ValidationError({"empties_collected": ["Enter how many empties you collected."]})
        lat, lng, acc = _gps(d)
        attempt = record_attempt(
            order, request.user, DeliveryAttempt.Outcome.DELIVERED, stop=_my_stop(order, request.user),
            device_time=timezone.now(), empties_collected=empties,
            code=None if no_code else code, gps_lat=lat, gps_lng=lng, gps_accuracy_m=acc,
            note="Delivered (customer had no code)" if no_code else "Delivered, code checked",
        )
        return Response({
            "status": "delivered",
            "code_ok": attempt.code_ok,
            "distance_from_pin_m": attempt.distance_from_pin_m,
            "geofence_flagged": attempt.geofence_flagged,
        })


class FailView(APIView):
    permission_classes = [IsRider]

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def post(self, request, pk):
        order = _my_order(request, pk)
        if order.status != Order.Status.OUT_FOR_DELIVERY:
            raise ValidationError(f"This order is '{order.status.replace('_', ' ')}', not on the road.")
        d = request.data
        reason = d.get("failure_reason")
        if reason not in FAIL_TEXT:
            raise ValidationError({"failure_reason": ["Pick why it couldn't be delivered."]})
        extra = str(d.get("note") or "").strip()[:200]
        lat, lng, acc = _gps(d)
        record_attempt(
            order, request.user, DeliveryAttempt.Outcome.FAILED, stop=_my_stop(order, request.user),
            device_time=timezone.now(), failure_reason=reason,
            gps_lat=lat, gps_lng=lng, gps_accuracy_m=acc,
            note=f"{FAIL_TEXT[reason]}{': ' + extra if extra else ''}",
        )
        return Response({"status": "failed"})


# ---------------------------------------------------------------------------
# Trips (Feature B): download before leaving, then start it
# ---------------------------------------------------------------------------
def _my_trip(request, pk):
    return get_object_or_404(Trip.objects.select_related("vehicle"), pk=pk, rider=request.user)


def trip_summary(trip):
    return {
        "id": trip.pk,
        "date": trip.date.isoformat(),
        "period": trip.period,
        "status": trip.status,
        "version": trip.version,
        "downloaded_version": trip.downloaded_version,
        "vehicle": {"name": trip.vehicle.name, "plate": trip.vehicle.plate,
                    "capacity": trip.vehicle.capacity_containers},
        "stop_count": trip.stops.count(),
    }


def trip_download_payload(trip):
    """
    Everything the phone needs to work with no signal. The customer's code is never sent:
    only sha256("<code_salt>:<code>") so the phone can check what the customer reads out.
    The server checks the real code again when the delivery syncs.
    """
    stops = (trip.stops.select_related("order__customer", "order__address")
             .prefetch_related("order__items__product").order_by("sequence"))
    rows = []
    for s in stops:
        row = stop_row(s.order, s.sequence)
        row.update({
            "stop_status": s.status,
            "expected_load_after": s.expected_load_after,
            "eta": s.eta.isoformat() if s.eta else None,
            "code_salt": s.order.code_salt,
            "code_hash": dispatch_services.code_hash(s.order),
        })
        rows.append(row)
    return {
        **trip_summary(trip),
        "code_hash": {"algorithm": "sha256", "input": "<code_salt>:<code>", "encoding": "hex"},
        "total_distance_m": trip.total_distance_m,
        "total_duration_s": trip.total_duration_s,
        "distance_is_estimate": trip.distance_is_estimate,
        "route_line": trip.route_line,
        "station": dict(zip(("lat", "lng"), station_point())),
        "geofence_m": SystemSetting.load().geofence_threshold_m,
        "stops": rows,
        "downloaded_at": trip.downloaded_at.isoformat() if trip.downloaded_at else None,
    }


class TripListView(APIView):
    permission_classes = [IsRider]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        trips = (Trip.objects.filter(rider=request.user, date__gte=timezone.localdate(),
                                     status__in=dispatch_services.DOWNLOADABLE)
                 .select_related("vehicle").order_by("date", "period"))
        return Response([trip_summary(t) for t in trips])


class TripDownloadView(APIView):
    permission_classes = [IsRider]

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def post(self, request, pk):
        trip = dispatch_services.mark_downloaded(_my_trip(request, pk), request.user)
        return Response(trip_download_payload(Trip.objects.select_related("vehicle").get(pk=trip.pk)))


class TripStartView(APIView):
    permission_classes = [IsRider]

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def post(self, request, pk):
        trip = _my_trip(request, pk)
        device_time = parse_datetime(str(request.data.get("device_time") or "")) or timezone.now()
        trip = dispatch_services.start_trip(trip, request.user, device_time=device_time)
        return Response(trip_summary(Trip.objects.select_related("vehicle").get(pk=trip.pk)))
