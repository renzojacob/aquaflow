import uuid
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.dateparse import parse_datetime

from apps.delivery.models import DeliveryAttempt
from apps.delivery.services import record_attempt, record_empties
from apps.dispatch.models import Trip, TripStop
from apps.dispatch.services import start_trip
from apps.orders.models import Order
from .models import SyncAction, SyncConflict

R = SyncAction.Result
A = SyncAction.ActionType
K = SyncConflict.Kind


def apply_batch(rider, device_id, actions):
    """Apply queued phone actions in the order the phone sent them. One result per action."""
    return [apply_action(rider, device_id, a) for a in actions]


def apply_action(rider, device_id, a):
    key = uuid.UUID(str(a["idempotency_key"]))
    if a.get("action_type") not in HANDLERS:
        return {"idempotency_key": str(key), "result": R.REJECTED, "error": "Unknown action type."}

    existing = SyncAction.objects.filter(idempotency_key=key).first()
    if existing:
        return _duplicate(existing, rider)

    device_time = a["device_time"]
    if isinstance(device_time, str):
        device_time = parse_datetime(device_time)
    trip = Trip.objects.filter(pk=a["trip_id"]).first() if a.get("trip_id") else None
    order = Order.objects.filter(pk=a["order_id"]).first() if a.get("order_id") else None

    try:
        with transaction.atomic():
            # Insert the key first: a concurrent replay of the same key fails right here
            sa = SyncAction.objects.create(
                idempotency_key=key, rider=rider, device_id=device_id,
                action_type=a["action_type"], trip=trip, order=order,
                payload=a.get("payload") or {}, device_time=device_time, result=R.APPLIED,
            )
            try:
                with transaction.atomic():      # savepoint: undo only the business changes
                    result, error = HANDLERS[sa.action_type](sa), ""
            except (ValidationError, IntegrityError, ValueError, TypeError) as e:
                result = R.REJECTED
                error = "; ".join(e.messages) if isinstance(e, ValidationError) else str(e)
            sa.result, sa.error = result, error
            sa.save(update_fields=["result", "error"])
    except IntegrityError:
        existing = SyncAction.objects.filter(idempotency_key=key).first()
        if existing is None:
            raise
        return _duplicate(existing, rider)

    return {"idempotency_key": str(key), "result": sa.result, "error": sa.error}


# ---------- handlers ----------

def _start_trip(sa):
    start_trip(_require(sa.trip, "Trip"), sa.rider, device_time=sa.device_time)
    return R.APPLIED


def _deliver(sa):
    order, stop, kind = _check(sa, _require(sa.order, "Order"))
    if kind:
        return _conflict(sa, order, kind)
    p = sa.payload
    attempt = record_attempt(
        order, sa.rider, DeliveryAttempt.Outcome.DELIVERED,
        stop=stop, device_time=sa.device_time, sync_action=sa,
        empties_collected=int(p.get("empties_collected", 0)), code=p.get("code"),
        gps_lat=p.get("gps_lat"), gps_lng=p.get("gps_lng"), gps_accuracy_m=p.get("gps_accuracy_m"),
    )
    if attempt.code_ok is False:
        return _conflict(sa, order, K.CODE_MISMATCH)
    return R.APPLIED


def _fail(sa):
    order, stop, kind = _check(sa, _require(sa.order, "Order"))
    if kind:
        return _conflict(sa, order, kind)
    p = sa.payload
    record_attempt(
        order, sa.rider, DeliveryAttempt.Outcome.FAILED,
        stop=stop, device_time=sa.device_time, sync_action=sa,
        failure_reason=p.get("failure_reason", ""),
        gps_lat=p.get("gps_lat"), gps_lng=p.get("gps_lng"), gps_accuracy_m=p.get("gps_accuracy_m"),
    )
    return R.APPLIED


def _empties(sa):
    count = int(sa.payload.get("count", 0))
    if count < 1:
        raise ValidationError("Empties count must be at least 1.")
    record_empties(_require(sa.order, "Order"), sa.rider, count)
    return R.APPLIED


HANDLERS = {A.START_TRIP: _start_trip, A.DELIVER: _deliver, A.FAIL: _fail, A.EMPTIES: _empties}


# ---------- helpers ----------

def _require(obj, what):
    if obj is None:
        raise ValidationError(f"{what} not found.")
    return obj


def _check(sa, order):
    """Lock the order and decide whether this action still makes sense."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    stop = (TripStop.objects.filter(order=order, status=TripStop.Status.PENDING)
            .select_related("trip").first())
    if order.status != Order.Status.OUT_FOR_DELIVERY:
        if order.status == Order.Status.CANCELLED and sa.action_type == A.DELIVER:
            return order, stop, K.DELIVERED_AFTER_CANCEL
        return order, stop, K.OUT_OF_ORDER
    if stop is None or stop.trip.rider_id != sa.rider_id:
        return order, stop, K.REASSIGNED
    return order, stop, None


def _conflict(sa, order, kind):
    SyncConflict.objects.create(sync_action=sa, order=order, kind=kind)
    Order.objects.filter(pk=order.pk).update(needs_review=True)
    return R.CONFLICT


def _duplicate(existing, rider):
    if existing.rider_id != rider.id:
        return {"idempotency_key": str(existing.idempotency_key), "result": R.REJECTED,
                "error": "This key belongs to another rider."}
    return {"idempotency_key": str(existing.idempotency_key), "result": R.DUPLICATE,
            "original_result": existing.result, "error": existing.error}