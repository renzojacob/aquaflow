"""
Feature B: apply the actions a rider's phone saved offline, exactly once each.

Results the phone acts on (POST /api/v1/rider/sync):
  applied    done. Remove it from the outbox.
  duplicate  this key was already applied earlier. Remove it from the outbox.
  conflict   applied (the server's record now matches what happened at the door) but flagged
             for the dispatcher's conflict queue. Remove it from the outbox.
  rejected   not applied. Keep it in the outbox with the error. Sending the same key again
             retries it (e.g. "deliver" rejected because "start trip" hadn't arrived yet).

Conflict rules from the spec:
  - Customer cancelled while the rider was offline, then the rider delivered: the delivery is
    KEPT (the water was handed over) and a "delivered_after_cancel" conflict is opened.
  - Order or trip reassigned to another rider: rejected, shown on the phone.
  - Actions in the wrong order (deliver before start trip): rejected, kept in the outbox.
  - Wrong code: the delivery stands, the server flags "code_mismatch".
  - Official times are the server's; the phone's time is stored as device_time.
"""
import uuid

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.dateparse import parse_datetime

from apps.delivery.models import DeliveryAttempt
from apps.delivery.services import record_attempt, record_empties
from apps.dispatch.models import Trip, TripChangeLog, TripStop
from apps.dispatch.services import start_trip
from apps.orders.models import Order, OrderStatusHistory
from apps.orders.services import _move_all
from .models import SyncAction, SyncConflict

R = SyncAction.Result
A = SyncAction.ActionType
K = SyncConflict.Kind


def apply_batch(rider, device_id, actions):
    """Apply queued phone actions in the order the phone sent them. One result per action."""
    return [apply_action(rider, device_id, a) for a in actions]


def _id(value):
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        raise ValidationError("trip_id and order_id must be whole numbers.")


def parse_action(a):
    """Check one action's shape. Returns (key, cleaned) or raises ValidationError(message)."""
    if not isinstance(a, dict):
        raise ValidationError("Each action must be an object.")
    try:
        key = uuid.UUID(str(a.get("idempotency_key")))
    except (TypeError, ValueError):
        raise ValidationError("idempotency_key must be a UUID.")
    if a.get("action_type") not in HANDLERS:
        raise ValidationError("Unknown action type. Use start_trip, deliver, fail or empties.")
    device_time = a.get("device_time")
    if isinstance(device_time, str):
        device_time = parse_datetime(device_time)
    if device_time is None:
        raise ValidationError("device_time must be an ISO date-time, e.g. 2026-11-06T09:15:00+08:00.")
    payload = a.get("payload") or {}
    if not isinstance(payload, dict):
        raise ValidationError("payload must be an object.")
    return key, {"action_type": a["action_type"], "trip_id": _id(a.get("trip_id")),
                 "order_id": _id(a.get("order_id")), "payload": payload, "device_time": device_time}


def apply_action(rider, device_id, a):
    raw_key = str(a.get("idempotency_key")) if isinstance(a, dict) else None
    try:
        key, a = parse_action(a)
    except ValidationError as e:
        return {"idempotency_key": raw_key, "result": R.REJECTED, "error": "; ".join(e.messages)}

    existing = SyncAction.objects.filter(idempotency_key=key).first()
    if existing and not (existing.result == R.REJECTED and existing.rider_id == rider.id):
        return _duplicate(existing, rider)

    trip = Trip.objects.filter(pk=a["trip_id"]).first() if a["trip_id"] else None
    order = Order.objects.filter(pk=a["order_id"]).first() if a["order_id"] else None
    fields = dict(device_id=device_id, action_type=a["action_type"], trip=trip, order=order,
                  payload=a["payload"], device_time=a["device_time"])

    try:
        with transaction.atomic():
            if existing:
                # A rejected action is being retried: lock its row so two retries can't both run
                sa = SyncAction.objects.select_for_update().get(pk=existing.pk)
                if sa.result != R.REJECTED:
                    return _duplicate(sa, rider)
                for k, v in fields.items():
                    setattr(sa, k, v)
            else:
                # Insert the key first: a concurrent replay of the same key fails right here
                sa = SyncAction.objects.create(idempotency_key=key, rider=rider, result=R.APPLIED, **fields)
            try:
                with transaction.atomic():      # savepoint: undo only the business changes
                    result, error = HANDLERS[sa.action_type](sa), ""
            except (ValidationError, IntegrityError, ValueError, TypeError) as e:
                result = R.REJECTED
                error = "; ".join(e.messages) if isinstance(e, ValidationError) else str(e)
            sa.result, sa.error = result, error
            sa.save()
    except IntegrityError:
        existing = SyncAction.objects.filter(idempotency_key=key).first()
        if existing is None:
            raise
        return _duplicate(existing, rider)

    out = {"idempotency_key": str(key), "result": sa.result, "error": sa.error}
    if sa.result == R.CONFLICT:
        out["conflicts"] = list(sa.conflicts.values_list("kind", flat=True))
    return out


# ---------- handlers ----------

def _start_trip(sa):
    start_trip(_require(sa.trip, "Trip"), sa.rider, device_time=sa.device_time)
    return R.APPLIED


def _deliver(sa):
    order, stop, kind = _check(sa, _require(sa.order, "Order"))
    if kind == K.DELIVERED_AFTER_CANCEL:
        _undo_cancel_for_delivery(order, sa)
        order.refresh_from_db()
    p = sa.payload
    no_code = bool(p.get("no_code"))   # customer couldn't find the code: allowed, flagged for review
    empties = int(p.get("empties_collected", 0))
    if not 0 <= empties <= 50:
        raise ValidationError("Empties collected must be between 0 and 50.")
    attempt = record_attempt(
        order, sa.rider, DeliveryAttempt.Outcome.DELIVERED,
        stop=stop, device_time=sa.device_time, sync_action=sa,
        empties_collected=empties, code=None if no_code else (str(p.get("code") or "").strip() or None),
        gps_lat=p.get("gps_lat"), gps_lng=p.get("gps_lng"), gps_accuracy_m=p.get("gps_accuracy_m"),
        note="Delivered offline (customer had no code)" if no_code else "Delivered offline, synced",
    )
    kinds = [kind] if kind else []
    if attempt.code_ok is False and not no_code:
        kinds.append(K.CODE_MISMATCH)
    for k in kinds:
        _conflict(sa, order, k)
    return R.CONFLICT if kinds else R.APPLIED


def _fail(sa):
    order, stop, kind = _check(sa, _require(sa.order, "Order"))
    if kind == K.DELIVERED_AFTER_CANCEL:
        raise ValidationError(f"AF-{order.pk} was cancelled by the customer. Nothing to record.")
    p = sa.payload
    extra = str(p.get("note") or "").strip()[:200]
    record_attempt(
        order, sa.rider, DeliveryAttempt.Outcome.FAILED,
        stop=stop, device_time=sa.device_time, sync_action=sa,
        failure_reason=p.get("failure_reason", ""),
        gps_lat=p.get("gps_lat"), gps_lng=p.get("gps_lng"), gps_accuracy_m=p.get("gps_accuracy_m"),
        note=f"Couldn't deliver ({p.get('failure_reason', '')}){': ' + extra if extra else ''}",
    )
    return R.APPLIED


def _empties(sa):
    count = int(sa.payload.get("count", 0))
    if count < 1:
        raise ValidationError("Empties count must be at least 1.")
    order = _require(sa.order, "Order")
    if not _was_mine(order, sa.rider):
        raise ValidationError(f"AF-{order.pk} is not one of your orders.")
    record_empties(order, sa.rider, count)
    return R.APPLIED


HANDLERS = {A.START_TRIP: _start_trip, A.DELIVER: _deliver, A.FAIL: _fail, A.EMPTIES: _empties}


# ---------- helpers ----------

def _require(obj, what):
    if obj is None:
        raise ValidationError(f"{what} not found.")
    return obj


def _was_mine(order, rider):
    """This rider carried the order: assigned to them, or on (or removed from) one of their trips."""
    return (order.assigned_rider_id == rider.id
            or TripStop.objects.filter(order=order, trip__rider=rider).exists()
            or TripChangeLog.objects.filter(order=order, trip__rider=rider).exists())


def _check(sa, order):
    """
    Lock the order and decide whether this action can be applied.
    Returns (order, stop, None) or (order, None, DELIVERED_AFTER_CANCEL); raises ValidationError
    (-> rejected, kept in the phone's outbox) for a reassigned order or an action out of order.
    """
    order = Order.objects.select_for_update().get(pk=order.pk)
    S = Order.Status
    if order.status == S.CANCELLED:
        if not _was_mine(order, sa.rider):
            raise ValidationError(f"AF-{order.pk} is not one of your orders.")
        return order, None, K.DELIVERED_AFTER_CANCEL
    if order.status in (S.DELIVERED, S.FAILED):
        raise ValidationError(f"AF-{order.pk} is already {order.status}. This action can't change it.")
    if order.status != S.OUT_FOR_DELIVERY:
        raise ValidationError(f"AF-{order.pk} isn't out for delivery yet. Sync \"start trip\" first.")

    stop = (TripStop.objects.filter(order=order, status=TripStop.Status.PENDING)
            .select_related("trip").first())
    if stop is not None and stop.trip.rider_id != sa.rider_id:
        raise ValidationError(f"AF-{order.pk} was moved to another rider. Check with the dispatcher.")
    if stop is None and order.assigned_rider_id != sa.rider_id:
        raise ValidationError(f"AF-{order.pk} was moved to another rider. Check with the dispatcher.")
    return order, stop, None


def _undo_cancel_for_delivery(order, sa):
    """
    The customer cancelled, but the rider already handed the water over (offline). Put the order
    back to out_for_delivery so the normal delivery records apply. The cancellation released the
    stock reservation, so the containers now come out of available stock.
    """
    _move_all(order, "load_out", sa.rider, -1, 0)
    Order.objects.filter(pk=order.pk).update(status=Order.Status.OUT_FOR_DELIVERY, assigned_rider=sa.rider)
    OrderStatusHistory.objects.create(
        order=order, from_status=Order.Status.CANCELLED, to_status=Order.Status.OUT_FOR_DELIVERY,
        changed_by=sa.rider, device_time=sa.device_time,
        note="Delivered offline after the customer cancelled. Kept and flagged for the dispatcher.")


def _conflict(sa, order, kind):
    SyncConflict.objects.create(sync_action=sa, order=order, kind=kind)
    Order.objects.filter(pk=order.pk).update(needs_review=True)
    return R.CONFLICT


@transaction.atomic
def resolve_conflict(conflict, by, note):
    """The dispatcher has looked at it. The order stops needing review once nothing else is open."""
    from django.utils import timezone

    conflict = SyncConflict.objects.select_for_update().get(pk=conflict.pk)
    if conflict.status == SyncConflict.Status.RESOLVED:
        raise ValidationError("This conflict is already resolved.")
    note = (note or "").strip()
    if not note:
        raise ValidationError({"note": ["Write what was done, e.g. \"Customer kept the water and paid.\""]})
    conflict.status, conflict.resolved_by = SyncConflict.Status.RESOLVED, by
    conflict.resolution_note, conflict.resolved_at = note[:255], timezone.now()
    conflict.save()

    order = conflict.order
    if order is not None and not order.sync_conflicts.filter(status=SyncConflict.Status.OPEN).exists():
        geofence = DeliveryAttempt.objects.filter(order=order, geofence_flagged=True).exists()
        if not geofence:     # a far-from-pin delivery still needs its own review
            Order.objects.filter(pk=order.pk).update(needs_review=False)
    return conflict


def _duplicate(existing, rider):
    if existing.rider_id != rider.id:
        return {"idempotency_key": str(existing.idempotency_key), "result": R.REJECTED,
                "error": "This key belongs to another rider."}
    return {"idempotency_key": str(existing.idempotency_key), "result": R.DUPLICATE,
            "original_result": existing.result, "error": existing.error}