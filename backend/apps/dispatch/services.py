from django.core.exceptions import ValidationError
from django.db import transaction

from apps.orders.models import Order
from apps.orders.services import refill_product, transition
from .models import Trip, TripStop

S = Order.Status
PATH = [S.CONFIRMED, S.PREPARING, S.READY, S.OUT_FOR_DELIVERY]


@transaction.atomic
def start_trip(trip, rider, device_time=None):
    trip = Trip.objects.select_for_update().get(pk=trip.pk)
    if trip.rider_id != rider.id:
        raise ValidationError("This trip is assigned to another rider.")
    if trip.status not in (Trip.Status.APPROVED, Trip.Status.DOWNLOADED):
        raise ValidationError(f"Trip can't be started from '{trip.status}'.")

    stops = list(trip.stops.filter(status=TripStop.Status.PENDING).select_related("order"))
    if not stops:
        raise ValidationError("This trip has no stops left to deliver.")

    for stop in stops:
        order = stop.order
        if order.status not in PATH[:-1]:
            raise ValidationError(f"Order #{order.pk} is '{order.status}' and can't go out.")
        # Loading the vehicle means the order is ready, so walk it forward to out_for_delivery
        for nxt in PATH[PATH.index(order.status) + 1:]:
            note = f"Trip #{trip.pk} started" if nxt == S.OUT_FOR_DELIVERY else "auto on trip start"
            order = transition(order, nxt, by=rider, device_time=device_time, note=note)
        # The rider's stop list, deliver/fail and customer tracking all look at assigned_rider
        order.assigned_rider = rider
        order.save(update_fields=["assigned_rider", "updated_at"])

    trip.status = Trip.Status.OUT
    trip.save(update_fields=["status", "updated_at"])
    return trip

# ---------------------------------------------------------------------------
# Dispatcher shortcuts for running deliveries before the Rider app exists.
# They use the same transition() rules, so stock and history stay correct.
# ---------------------------------------------------------------------------
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.customers.services import record_containers
from apps.delivery.models import DeliveryAttempt
from apps.inventory.models import StockLevel
from apps.inventory.services import apply_movement


def ensure_stock_row(product):
    """apply_movement() needs a StockLevel row; create an empty one the first time."""
    StockLevel.objects.get_or_create(product=product)


@transaction.atomic
def send_out(order, by, rider_id=None):
    """Ready -> Out for delivery, optionally naming the rider who carries it."""
    stop = TripStop.objects.filter(order=order).exclude(status=TripStop.Status.FAILED).first()
    if stop is not None:
        raise ValidationError(
            f"This order is on Trip #{stop.trip_id}. It goes out when the rider starts that trip.")
    rider = None
    if rider_id:
        rider = get_user_model().objects.filter(pk=rider_id, role="rider", is_active=True).first()
        if rider is None:
            raise ValidationError({"rider_id": ["Pick an active rider."]})
    ensure_stock_row(order.product)
    order = transition(order, S.OUT_FOR_DELIVERY, by=by,
                       note=f"Sent out with {rider.get_full_name() or rider.username}" if rider else "Sent out")
    if rider:
        order.assigned_rider = rider
        order.save(update_fields=["assigned_rider", "updated_at"])
    return order


@transaction.atomic
def mark_delivered(order, by, empties_collected=None):
    """Out for delivery -> Delivered. Records containers left and empties taken back."""
    empties = order.expected_empties if empties_collected is None else int(empties_collected)
    if empties < 0 or empties > 50:
        raise ValidationError({"empties_collected": ["Enter how many empties were collected."]})
    ensure_stock_row(order.product)
    order = transition(order, S.DELIVERED, by=by, note="Delivered")
    record_containers(order.customer, delivered=order.containers, returned=empties,
                      note=f"Order #{order.pk}", order=order)
    if empties:
        ensure_stock_row(refill_product(order))
        apply_movement(refill_product(order), "empties_in", by, empty=empties, order=order)
    DeliveryAttempt.objects.create(
        order=order, rider=order.assigned_rider or by, outcome=DeliveryAttempt.Outcome.DELIVERED,
        empties_collected=empties, device_time=timezone.now(),
    )
    from apps.predictions.services import refresh_after_delivery   # local: predictions imports orders
    refresh_after_delivery(order)                                   # Feature C
    return order


@transaction.atomic
def mark_failed(order, by, reason):
    """Out for delivery -> Failed. The containers come back to ready stock."""
    if len((reason or "").strip()) < 3:
        raise ValidationError({"reason": ["Say why it could not be delivered."]})
    ensure_stock_row(order.product)
    order = transition(order, S.FAILED, by=by, note=reason.strip()[:255])
    DeliveryAttempt.objects.create(
        order=order, rider=order.assigned_rider or by, outcome=DeliveryAttempt.Outcome.FAILED,
        failure_reason=DeliveryAttempt.FailureReason.OTHER, device_time=timezone.now(),
    )
    return order


# ---------------------------------------------------------------------------
# Rider download (offline copy of an approved trip)
# ---------------------------------------------------------------------------
import hashlib

DOWNLOADABLE = (Trip.Status.APPROVED, Trip.Status.DOWNLOADED, Trip.Status.OUT)


def code_hash(order):
    """sha256("<salt>:<code>"). The phone checks what the customer reads out without ever seeing the code."""
    return hashlib.sha256(f"{order.code_salt}:{order.confirmation_code}".encode()).hexdigest()


@transaction.atomic
def mark_downloaded(trip, rider):
    """Remember which version the phone now holds, so the dispatcher can see if it is out of date."""
    trip = Trip.objects.select_for_update().get(pk=trip.pk)
    if trip.rider_id != rider.id:
        raise ValidationError("This trip is assigned to another rider.")
    if trip.status not in DOWNLOADABLE:
        raise ValidationError("This trip is not ready to download yet.")
    if trip.status == Trip.Status.APPROVED:
        trip.status = Trip.Status.DOWNLOADED
    trip.downloaded_version = trip.version
    trip.downloaded_at = timezone.now()
    trip.save(update_fields=["status", "downloaded_version", "downloaded_at", "updated_at"])
    return trip
