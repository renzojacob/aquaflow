"""
Dispatcher + owner: trips (one vehicle, one rider, a list of stops for one day and period).
URL prefix: /api/v1/dispatch/   (the frontend's tripService.js calls these)

  GET    trips?date=&period=        that day's trips + confirmed orders not on any trip
  POST   trips                      {date, period, vehicle_id, order_ids, rider_id?}
  GET    trips/<id>                 one trip with its change log
  PUT    trips/<id>/stops           {order_ids} replace the stops (add, remove, reorder)
  POST   trips/<id>/approve         draft -> approved (the rider can download it)
  POST   trips/<id>/assign          {rider_id?, vehicle_id?}
  DELETE trips/<id>                 draft or approved only
  POST   plan                       {date, period} one button: build draft trips for the slot

Every rule (capacity, statuses, one trip per rider/vehicle per period) is checked here,
so the screens only show the message that comes back.
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status as http
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsDispatcherOrOwner
from apps.delivery.best_time import best_periods
from apps.orders.models import Order

from . import planner
from .models import Trip, TripChangeLog, TripStop, Vehicle

User = get_user_model()
PERIODS = ("morning", "afternoon")
EDITABLE = (Trip.Status.DRAFT, Trip.Status.APPROVED, Trip.Status.DOWNLOADED)


# ---------------------------------------------------------------------------
# Shapes (match the typedefs in frontend/src/services/tripService.js)
# ---------------------------------------------------------------------------
def _name(u):
    return u.get_full_name() or u.username


def _hint(o, hints):
    """Feature E: the period that usually works at this order's address, if it isn't this one."""
    s = (hints or {}).get(o.address_id)
    if not s or s["period"] == o.period:
        return None
    return {"period": s["period"], "basis": s["basis"], "summary": s["summary"]}


def hints_for(orders):
    return best_periods(o.address_id for o in orders)


def _order_brief(o, hints=None):
    return {
        "order_id": o.pk, "code": f"AF-{o.pk}", "status": o.status, "period": o.period,
        "customer_name": _name(o.customer), "barangay": o.address.barangay,
        "address": o.address_text, "lat": float(o.lat), "lng": float(o.lng),
        "containers": o.containers, "expected_empties": o.expected_empties,
        "better_period": _hint(o, hints),
    }


def trip_payload(trip, with_log=False):
    trip = Trip.objects.select_related("vehicle", "rider").get(pk=trip.pk)
    stops = (trip.stops.select_related("order__customer", "order__address").order_by("sequence"))
    orders = [s.order for s in stops]
    hints = hints_for(orders)
    departure, peak, _ = planner.load_profile(orders)
    data = {
        "id": trip.pk, "date": trip.date.isoformat(), "period": trip.period,
        "status": trip.status, "version": trip.version,
        "vehicle": {"id": trip.vehicle_id, "name": trip.vehicle.name, "plate": trip.vehicle.plate,
                    "capacity": trip.vehicle.capacity_containers},
        "rider": ({"id": trip.rider_id, "name": _name(trip.rider), "phone": trip.rider.phone}
                  if trip.rider_id else None),
        "load": {"departure": departure, "peak": peak, "capacity": trip.vehicle.capacity_containers},
        "total_distance_m": trip.total_distance_m, "total_duration_s": trip.total_duration_s,
        "distance_is_estimate": trip.distance_is_estimate,
        "route_line": trip.route_line,             # [[lat, lng], ...] on the roads, or null
        "phone_out_of_date": trip.status == Trip.Status.DOWNLOADED and trip.downloaded_version != trip.version,
        "stops": [{
            "sequence": s.sequence, "status": s.status, "order_id": s.order_id,
            "code": f"AF-{s.order_id}", "order_status": s.order.status,
            "customer_name": _name(s.order.customer), "barangay": s.order.address.barangay,
            "address": s.order.address_text, "lat": float(s.order.lat), "lng": float(s.order.lng),
            "containers": s.order.containers, "expected_empties": s.order.expected_empties,
            "expected_load_after": s.expected_load_after,
            "eta": s.eta.isoformat() if s.eta else None,
            "better_period": _hint(s.order, hints),
        } for s in stops],
    }
    if with_log:
        data["change_log"] = [{
            "at": c.created_at.isoformat(), "action": c.action, "order_id": c.order_id,
            "by": _name(c.by_user) if c.by_user else None,
        } for c in trip.change_log.select_related("by_user")[:50]]
    return data


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def _slot(data):
    day = parse_date(str(data.get("date") or ""))
    period = data.get("period")
    if day is None:
        raise ValidationError({"date": ["Pick a date."]})
    if period not in PERIODS:
        raise ValidationError({"period": ["Use morning or afternoon."]})
    return day, period


def _vehicle(vid, trip=None, day=None, period=None):
    v = Vehicle.objects.filter(pk=vid).first()
    if v is None:
        raise ValidationError({"vehicle_id": ["Pick a vehicle."]})
    if not v.is_available and (trip is None or trip.vehicle_id != v.pk):
        raise ValidationError({"vehicle_id": [f"{v.name} is switched off. Turn it on in Vehicles first."]})
    clash = Trip.objects.filter(date=day or trip.date, period=period or trip.period, vehicle=v)
    if trip:
        clash = clash.exclude(pk=trip.pk)
    if clash.exists():
        raise ValidationError({"vehicle_id": [f"{v.name} already has a trip for this time."]})
    return v


def _rider(rid, trip=None, day=None, period=None):
    r = User.objects.filter(pk=rid, role="rider", is_active=True).first()
    if r is None:
        raise ValidationError({"rider_id": ["Pick an active rider."]})
    clash = Trip.objects.filter(date=day or trip.date, period=period or trip.period, rider=r)
    if trip:
        clash = clash.exclude(pk=trip.pk)
    if clash.exists():
        raise ValidationError({"rider_id": [f"{_name(r)} already has a trip for this time."]})
    return r


def _orders_for(trip_slot, order_ids, trip=None):
    """The orders in the order given. Each must be plannable, in this slot, and not on another trip."""
    day, period = trip_slot
    ids = []
    for i in order_ids or []:
        try:
            i = int(i)
        except (TypeError, ValueError):
            raise ValidationError({"order_ids": ["Order numbers must be whole numbers."]})
        if i not in ids:
            ids.append(i)
    found = {o.pk: o for o in Order.objects.filter(pk__in=ids)
             .select_related("customer", "address").prefetch_related("items__product")}
    out = []
    for i in ids:
        o = found.get(i)
        if o is None:
            raise ValidationError({"order_ids": [f"Order AF-{i} does not exist."]})
        if o.status not in planner.PLANNABLE:
            raise ValidationError({"order_ids": [f"AF-{i} is '{o.status}'. Confirm it first, then plan it."]})
        if o.delivery_date != day or o.period != period:
            raise ValidationError({"order_ids": [f"AF-{i} is for another day or time."]})
        busy = TripStop.objects.filter(order=o).exclude(status=TripStop.Status.FAILED)
        if trip:
            busy = busy.exclude(trip=trip)
        if busy.exists():
            raise ValidationError({"order_ids": [f"AF-{i} is already on another trip."]})
        out.append(o)
    return out


def _log(trip, action, order, by, before=None, after=None):
    TripChangeLog.objects.create(trip=trip, action=action, order=order, by_user=by,
                                 before=before, after=after)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------
class TripListCreateView(APIView):
    permission_classes = [IsDispatcherOrOwner]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        day = parse_date(request.query_params.get("date", "")) or timezone.localdate()
        period = request.query_params.get("period") or None
        if period and period not in PERIODS:
            raise ValidationError({"period": ["Use morning or afternoon."]})
        trips = Trip.objects.filter(date=day)
        if period:
            trips = trips.filter(period=period)
        unplanned = list(planner.unplanned_orders(day, period))
        hints = hints_for(unplanned)
        return Response({
            "trips": [trip_payload(t) for t in trips.order_by("period", "vehicle__name")],
            "unplanned": [_order_brief(o, hints) for o in unplanned],
        })

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self, request):
        d = request.data
        day, period = _slot(d)
        vehicle = _vehicle(d.get("vehicle_id"), day=day, period=period)
        rider = _rider(d["rider_id"], day=day, period=period) if d.get("rider_id") else None
        orders = _orders_for((day, period), d.get("order_ids"))
        if not orders:
            raise ValidationError({"order_ids": ["Choose at least one order."]})
        msg = planner.capacity_error(vehicle, orders)
        if msg:
            raise ValidationError({"order_ids": [msg]})
        trip = Trip.objects.create(date=day, period=period, vehicle=vehicle, rider=rider,
                                   created_by=request.user)
        planner.write_stops(trip, orders)          # keeps the order the dispatcher chose
        for o in orders:
            _log(trip, TripChangeLog.Action.PLANNED, o, request.user, after={"vehicle": vehicle.name})
        return Response(trip_payload(trip, with_log=True), status=http.HTTP_201_CREATED)


class TripDetailView(APIView):
    permission_classes = [IsDispatcherOrOwner]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, pk):
        return Response(trip_payload(get_object_or_404(Trip, pk=pk), with_log=True))

    @extend_schema(responses=None)
    @transaction.atomic
    def delete(self, request, pk):
        trip = get_object_or_404(Trip.objects.select_for_update(), pk=pk)
        if trip.status not in (Trip.Status.DRAFT, Trip.Status.APPROVED):
            raise ValidationError("A trip that already left, or that the rider downloaded, can't be deleted.")
        trip.delete()
        return Response(status=http.HTTP_204_NO_CONTENT)


class TripStopsView(APIView):
    permission_classes = [IsDispatcherOrOwner]

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def put(self, request, pk):
        trip = get_object_or_404(Trip.objects.select_for_update().select_related("vehicle"), pk=pk)
        if trip.status not in EDITABLE:
            raise ValidationError("This trip already left. Its stops can't change.")
        orders = _orders_for((trip.date, trip.period), request.data.get("order_ids"), trip=trip)
        if not orders:
            raise ValidationError({"order_ids": ["A trip needs at least one stop. Delete the trip instead."]})
        msg = planner.capacity_error(trip.vehicle, orders)
        if msg:
            raise ValidationError({"order_ids": [msg]})

        before = list(trip.stops.order_by("sequence").values_list("order_id", flat=True))
        after = [o.pk for o in orders]
        if before == after:
            return Response(trip_payload(trip, with_log=True))
        planner.write_stops(trip, orders)
        for oid in after:
            if oid not in before:
                _log(trip, TripChangeLog.Action.MOVED_IN, Order.objects.get(pk=oid), request.user)
        for oid in before:
            if oid not in after:
                _log(trip, TripChangeLog.Action.MOVED_OUT, Order.objects.filter(pk=oid).first(), request.user)
        if [i for i in before if i in after] != [i for i in after if i in before]:
            _log(trip, TripChangeLog.Action.REORDERED, None, request.user,
                 before={"order_ids": before}, after={"order_ids": after})
        planner.bump_version(trip)
        return Response(trip_payload(trip, with_log=True))


class TripApproveView(APIView):
    permission_classes = [IsDispatcherOrOwner]

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self, request, pk):
        trip = get_object_or_404(Trip.objects.select_for_update().select_related("vehicle"), pk=pk)
        if trip.status != Trip.Status.DRAFT:
            raise ValidationError(f"Only a draft trip can be approved. This one is '{trip.status}'.")
        if trip.rider_id is None:
            raise ValidationError("Choose a rider before approving.")
        stops = list(trip.stops.select_related("order"))
        if not stops:
            raise ValidationError("This trip has no stops.")
        bad = [s.order for s in stops if s.order.status not in planner.PLANNABLE]
        if bad:
            raise ValidationError(f"AF-{bad[0].pk} is '{bad[0].status}' now. Remove it from the trip first.")
        msg = planner.capacity_error(trip.vehicle, [s.order for s in stops])
        if msg:
            raise ValidationError(msg)
        trip.status = Trip.Status.APPROVED
        trip.save(update_fields=["status", "updated_at"])
        planner.bump_version(trip)
        return Response(trip_payload(trip, with_log=True))


class TripAssignView(APIView):
    permission_classes = [IsDispatcherOrOwner]

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self, request, pk):
        trip = get_object_or_404(Trip.objects.select_for_update().select_related("vehicle"), pk=pk)
        if trip.status not in EDITABLE:
            raise ValidationError("This trip already left. Rider and vehicle can't change.")
        d, changed = request.data, False
        if d.get("vehicle_id") and int(d["vehicle_id"]) != trip.vehicle_id:
            v = _vehicle(d["vehicle_id"], trip=trip)
            msg = planner.capacity_error(v, [s.order for s in trip.stops.select_related("order")])
            if msg:
                raise ValidationError({"vehicle_id": [msg]})
            trip.vehicle, changed = v, True
        if d.get("rider_id") and int(d["rider_id"]) != (trip.rider_id or 0):
            trip.rider, changed = _rider(d["rider_id"], trip=trip), True
        if changed:
            trip.save()
            planner.bump_version(trip)
        return Response(trip_payload(trip, with_log=True))


class PlanSlotView(APIView):
    """The one button: build draft trips for a day and period."""

    permission_classes = [IsDispatcherOrOwner]

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        day, period = _slot(request.data)
        trips, leftovers = planner.plan_slot(day, period, request.user)
        hints = hints_for([o for o, _ in leftovers])
        return Response({
            "trips": [trip_payload(t) for t in trips],
            "not_fitted": [{**_order_brief(o, hints), "reason": why} for o, why in leftovers],
        }, status=http.HTTP_201_CREATED)
