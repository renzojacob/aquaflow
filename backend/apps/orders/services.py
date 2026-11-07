from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from apps.inventory.services import apply_movement
from .models import Order, OrderItem, OrderStatusHistory
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


def refill_product(order):
    """The product whose empties come back with this order (the station's container)."""
    from apps.inventory.models import Product
    if order.product.kind == Product.Kind.REFILL:
        return order.product
    return default_product() or order.product


def stock_lines(order):
    """[(product, quantity)] that this order holds in stock: one per cart line."""
    lines = [(i.product, i.quantity) for i in order.items.select_related("product")]
    return lines or [(order.product, order.quantity)]  # very old orders without lines


def _move_all(order, reason, by, sign_available, sign_reserved):
    from apps.inventory.models import StockLevel
    for product, q in stock_lines(order):
        StockLevel.objects.get_or_create(product=product)
        try:
            with transaction.atomic():
                apply_movement(product, reason, by, available=sign_available * q,
                               reserved=sign_reserved * q, order=order)
        except IntegrityError:
            raise ValidationError(f"Not enough {product.name} in stock for this order.")


@transaction.atomic
def transition(order, to, by=None, reason="", note="", device_time=None):
    order = Order.objects.select_for_update().get(pk=order.pk)   # lock the order row
    frm = order.status
    if to not in ALLOWED.get(frm, set()):
        raise ValidationError(f"Cannot move order from '{frm}' to '{to}'.")

    if to == S.CONFIRMED:
        if frm == S.FAILED:
            if order.replan_count >= 1:
                raise ValidationError("This order was already re-planned once.")
            order.replan_count += 1
        _move_all(order, "reserve", by, -1, 1)
    elif to == S.CANCELLED and frm in HOLDS_RESERVATION:
        _move_all(order, "release", by, 1, -1)
    elif to == S.OUT_FOR_DELIVERY:
        _move_all(order, "load_out", by, 0, -1)
    elif to == S.FAILED:
        _move_all(order, "return_unsold", by, 1, 0)

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

    qs = Product.objects.filter(is_active=True).order_by("sort_order", "id")
    return qs.filter(kind=Product.Kind.REFILL).first() or qs.first()


@transaction.atomic
def place_order(customer, *, address, delivery_date, period, items=None, quantity=None,
                product=None, expected_empties=None, notes="",
                source=Order.Source.MANUAL):
    """
    items: [{"product": Product, "quantity": int}, ...]  (the cart)
    Older callers may still send just quantity (+ product): that is a one-line cart.
    """
    from apps.inventory.models import Product

    if customer.role != "customer":
        raise ValidationError("Only customer accounts can place orders.")

    if not items:
        product = product or default_product()
        if product is None:
            raise ValidationError("No product is set up yet. Please contact the station.")
        items = [{"product": product, "quantity": quantity or 0}]

    # merge repeated products, check each line
    merged = {}
    for line in items:
        p, q = line["product"], int(line["quantity"] or 0)
        if q < 1:
            continue
        merged[p.pk] = (p, merged.get(p.pk, (p, 0))[1] + q)
    if not merged:
        raise ValidationError({"items": ["Add at least one item."]})
    for p, q in merged.values():
        if not getattr(p, "is_active", True):
            raise ValidationError({"items": [f"{p.name} is not available right now."]})
        limit = min(getattr(p, "max_per_order", MAX_QUANTITY) or MAX_QUANTITY, MAX_QUANTITY)
        if q > limit:
            raise ValidationError({"items": [f"Order up to {limit} of {p.name}."]})
    lines = sorted(merged.values(), key=lambda pq: (pq[0].kind != Product.Kind.REFILL, pq[0].sort_order, pq[0].pk))
    units = sum(q for _, q in lines)
    if units > 60:
        raise ValidationError({"items": ["That's too much for one trip. Split it into two orders."]})
    containers = sum(q for p, q in lines if p.kind == Product.Kind.REFILL)

    if address.customer_id != customer.pk or address.is_archived:
        raise ValidationError({"address": ["Choose one of your saved addresses."]})

    from apps.station.services import outside_area_message
    too_far = outside_area_message(address.lat, address.lng, address.barangay)
    if too_far:
        raise ValidationError({"address": [too_far]})

    today = timezone.localdate()
    if delivery_date < today or delivery_date > today + timedelta(days=MAX_DAYS_AHEAD):
        raise ValidationError({"delivery_date": ["You can order for today or tomorrow only."]})
    if delivery_date == today and timezone.localtime().time() >= PERIOD_START[period]:
        raise ValidationError(
            {"period": ["That delivery time is closed for today. Pick another time."]}
        )

    # Feature D: never promise a slot the fleet can't serve. Lock the slot first so two
    # customers can't both take the last containers; the lock ends with this transaction.
    if containers:
        from .slots import full_slot_message, lock_slot, slot_availability
        lock_slot(delivery_date, period)
        room = slot_availability(delivery_date, period, containers=containers)
        if not room.fits:
            raise ValidationError({"period": [full_slot_message(room, Order.Period(period).label)]})

    profile = CustomerProfile.objects.filter(user=customer).first()
    held = profile.containers_held if profile else 0
    if expected_empties is None:
        expected_empties = min(containers, held)
    elif expected_empties > held:
        raise ValidationError(
            {"expected_empties": [f"You can return up to {held} empty containers."]}
        )
    elif expected_empties > containers:
        raise ValidationError(
            {"expected_empties": [f"You can hand back up to {containers} empties with this order."]}
        )

    main = lines[0][0]
    order = Order.objects.create(
        customer=customer,
        address=address,
        product=main,
        quantity=units,
        containers=containers,
        total=sum(p.price * q for p, q in lines),
        expected_empties=expected_empties,
        delivery_date=delivery_date,
        period=period,
        notes=(notes or "").strip()[:255],
        source=source,
    )
    for p, q in lines:
        OrderItem.objects.create(order=order, product=p, quantity=q, unit_price=p.price)
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