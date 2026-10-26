import secrets
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from apps.customers.services import record_containers
from apps.dispatch.models import Trip, TripStop
from apps.inventory.services import apply_movement
from apps.orders.models import Order
from apps.orders.services import transition
from apps.predictions.models import AddressPeriodStats
from apps.station.geo import haversine_m
from apps.station.models import SystemSetting
from .models import DeliveryAttempt

O = DeliveryAttempt.Outcome


@transaction.atomic
def record_attempt(order, rider, outcome, *, device_time, stop=None,
                   empties_collected=0, failure_reason="", code=None,
                   gps_lat=None, gps_lng=None, gps_accuracy_m=None, sync_action=None):
    if outcome == O.FAILED and failure_reason not in DeliveryAttempt.FailureReason.values:
        raise ValidationError("A failed attempt needs a valid failure reason.")
    order = Order.objects.select_for_update().get(pk=order.pk)

    # Feature F: how far was the rider from the customer's pin?
    distance = None
    if gps_lat is not None and gps_lng is not None:
        distance = round(haversine_m(gps_lat, gps_lng, order.lat, order.lng))
    flagged = distance is None or distance > SystemSetting.load().geofence_threshold_m

    # Server-side code check (the offline check on the phone is convenience only)
    code_ok = None
    if outcome == O.DELIVERED:
        code_ok = code is not None and secrets.compare_digest(str(code), order.confirmation_code)

    # Order lifecycle, container balance, stock
    if outcome == O.DELIVERED:
        order = transition(order, Order.Status.DELIVERED, by=rider, device_time=device_time)
        record_containers(order.customer, delivered=order.quantity,
                          returned=empties_collected, order=order)
        if empties_collected:
            apply_movement(order.product, "empties_in", rider, empty=empties_collected,
                           order=order, trip=stop.trip if stop else None)
    else:
        order = transition(order, Order.Status.FAILED, by=rider,
                           device_time=device_time, note=failure_reason)

    if flagged or code_ok is False:
        Order.objects.filter(pk=order.pk).update(needs_review=True)

    attempt = DeliveryAttempt.objects.create(
        order=order, trip_stop=stop, rider=rider, outcome=outcome,
        failure_reason=failure_reason if outcome == O.FAILED else "",
        empties_collected=empties_collected, code_ok=code_ok,
        gps_lat=gps_lat, gps_lng=gps_lng, gps_accuracy_m=gps_accuracy_m,
        distance_from_pin_m=distance, geofence_flagged=flagged,
        device_time=device_time, sync_action=sync_action,
    )

    # Feature E: success/failure per address and period
    field = "successes" if outcome == O.DELIVERED else "failures"
    stats, _ = AddressPeriodStats.objects.get_or_create(address_id=order.address_id,
                                                        period=order.period)
    AddressPeriodStats.objects.filter(pk=stats.pk).update(**{field: F(field) + 1})

    if stop is not None:
        stop.status = TripStop.Status.DONE if outcome == O.DELIVERED else TripStop.Status.FAILED
        stop.save(update_fields=["status"])
        _complete_trip_if_done(stop.trip_id)

    # Later: refresh the refill prediction (#4) and queue the "delivered" email
    return attempt


@transaction.atomic
def record_empties(order, rider, count):
    """Empties picked up separately from a delivery."""
    record_containers(order.customer, returned=count, order=order, note="empties pickup")
    apply_movement(order.product, "empties_in", rider, empty=count, order=order,
                   note="empties pickup")


def _complete_trip_if_done(trip_id):
    if not TripStop.objects.filter(trip_id=trip_id, status=TripStop.Status.PENDING).exists():
        Trip.objects.filter(pk=trip_id, status=Trip.Status.OUT).update(status=Trip.Status.COMPLETED)