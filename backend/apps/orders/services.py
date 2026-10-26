from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from apps.inventory.services import apply_movement
from .models import Order, OrderStatusHistory
from django.db.models import F
from apps.dispatch.models import Trip, TripStop, TripChangeLog

S = Order.Status

ALLOWED = {
    S.PENDING: {S.CONFIRMED, S.REJECTED, S.CANCELLED},
    S.CONFIRMED: {S.PREPARING, S.CANCELLED},
    S.PREPARING: {S.READY, S.CANCELLED},
    S.READY: {S.OUT_FOR_DELIVERY, S.CANCELLED},
    S.OUT_FOR_DELIVERY: {S.DELIVERED, S.FAILED},
    S.FAILED: {S.CONFIRMED},          # re-plan (once)
}
HOLDS_RESERVATION = {S.CONFIRMED, S.PREPARING, S.READY}


@transaction.atomic
def transition(order, to, by=None, reason="", note="", device_time=None):
    order = Order.objects.select_for_update().get(pk=order.pk)   # lock the order row
    frm = order.status
    if to not in ALLOWED.get(frm, set()):
        raise ValidationError(f"Cannot move order from '{frm}' to '{to}'.")

    q, p = order.quantity, order.product
    try:
        if to == S.CONFIRMED:
            if frm == S.FAILED:
                if order.replan_count >= 1:
                    raise ValidationError("This order was already re-planned once.")
                order.replan_count += 1
            apply_movement(p, "reserve", by, available=-q, reserved=q, order=order)
        elif to == S.CANCELLED and frm in HOLDS_RESERVATION:
            apply_movement(p, "release", by, available=q, reserved=-q, order=order)
        elif to == S.OUT_FOR_DELIVERY:
            apply_movement(p, "load_out", by, reserved=-q, order=order)
        elif to == S.FAILED:
            apply_movement(p, "return_unsold", by, available=q, order=order)
    except IntegrityError:
        raise ValidationError("Not enough stock for this order.")

    if to == S.REJECTED:
        order.rejection_reason = reason
    elif to == S.CANCELLED:
        order.cancel_reason = reason
        for stop in TripStop.objects.filter(order=order, status=TripStop.Status.PENDING):
            TripChangeLog.objects.create(trip_id=stop.trip_id, action="removed", order=order,
                                            by_user=by, before={"sequence": stop.sequence})
            Trip.objects.filter(pk=stop.trip_id).update(version=F("version") + 1)
            stop.delete()

    order.status = to
    order.save()
    OrderStatusHistory.objects.create(order=order, from_status=frm, to_status=to,
                                      changed_by=by, device_time=device_time, note=note)
    return order