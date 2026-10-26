from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from apps.inventory.services import apply_movement
from .models import Order, OrderStatusHistory
from django.db.models import F
from apps.dispatch.models import Trip, TripStop, TripChangeLog
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import CustomerProfile

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

# ---------------------------------------------------------------------------
# Customer-facing services
# ---------------------------------------------------------------------------

MAX_QUANTITY = 20
MAX_DAYS_AHEAD = 1
PERIOD_START = {
    Order.Period.MORNING: time(8, 0),
    Order.Period.AFTERNOON: time(13, 0),
}
CUSTOMER_CANCELLABLE = {S.PENDING, S.CONFIRMED}

def default_product():
    """The station sells one main product (the 5-gallon refill): use the first active one."""
    from apps.inventory.models import Product

    qs = Product.objects.order_by("id")
    if hasattr(Product, "is_active"):
        qs = qs.filter(is_active=True)
    return qs.first()


@transaction.atomic
def place_order(customer, *, address, quantity, delivery_date, period,
                product=None, expected_empties=None, notes="",
                source=Order.Source.MANUAL):
    if customer.role != "customer":
        raise ValidationError("Only customer accounts can place orders.")

    product = product or default_product()
    if product is None:
        raise ValidationError("No product is set up yet. Please contact the station.")
    if not getattr(product, "is_active", True):
        raise ValidationError({"product": ["This product is not available."]})

    if address.customer_id != customer.pk or address.is_archived:
        raise ValidationError({"address": ["Choose one of your saved addresses."]})

    if quantity < 1 or quantity > MAX_QUANTITY:
        raise ValidationError({"quantity": [f"Order between 1 and {MAX_QUANTITY} containers."]})

    today = timezone.localdate()
    if delivery_date < today or delivery_date > today + timedelta(days=MAX_DAYS_AHEAD):
        raise ValidationError({"delivery_date": ["You can order for today or tomorrow only."]})
    if delivery_date == today and timezone.localtime().time() >= PERIOD_START[period]:
        raise ValidationError(
            {"period": ["That delivery time is closed for today. Pick another time."]}
        )

    # TODO (#3, Feature D): reject the order here if the slot is full.

    profile = CustomerProfile.objects.filter(user=customer).first()
    held = profile.containers_held if profile else 0
    if expected_empties is None:
        expected_empties = min(quantity, held)
    elif expected_empties > held:
        raise ValidationError(
            {"expected_empties": [f"You can return up to {held} empty containers."]}
        )

    order = Order.objects.create(
        customer=customer,
        address=address,
        product=product,
        quantity=quantity,
        expected_empties=expected_empties,
        delivery_date=delivery_date,
        period=period,
        notes=(notes or "").strip()[:255],
        source=source,
    )
    OrderStatusHistory.objects.create(
        order=order, from_status="", to_status=order.status,
        changed_by=customer, note="Order placed",
    )
    return order


@transaction.atomic
def cancel_by_customer(customer, order, reason=""):
    order = Order.objects.select_for_update().get(pk=order.pk, customer=customer)
    if order.status not in CUSTOMER_CANCELLABLE:
        raise ValidationError(
            "This order can no longer be cancelled. Please contact the station."
        )
    return transition(
        order, S.CANCELLED, by=customer,
        reason=reason or "Cancelled by customer", note="Cancelled by customer",
    )