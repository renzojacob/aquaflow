from django.core.exceptions import ValidationError
from django.db import transaction

from apps.orders.models import Order
from apps.orders.services import transition
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

    for stop in trip.stops.filter(status=TripStop.Status.PENDING).select_related("order"):
        order = stop.order
        if order.status not in PATH[:-1]:
            raise ValidationError(f"Order #{order.pk} is '{order.status}' and can't go out.")
        # Loading the vehicle means the order is ready, so walk it forward to out_for_delivery
        for nxt in PATH[PATH.index(order.status) + 1:]:
            note = "" if nxt == S.OUT_FOR_DELIVERY else "auto on trip start"
            order = transition(order, nxt, by=rider, device_time=device_time, note=note)

    trip.status = Trip.Status.OUT
    trip.save(update_fields=["status", "updated_at"])
    return trip