"""
Supplies: caps, seals, filters and anything else the station uses up.

Two ways the amount goes down:
  automatic   when the dispatcher records a refill batch (containers washed and filled),
              every supply with used_per_refill > 0 goes down by  batch x used_per_refill.
              That is the moment caps and seals are actually used.
  by hand     "used" for anything else, "received" when a delivery arrives,
              "correction" after a physical count.

"Days left" uses what was really used in the last 30 days, not a guess: total used / 30.
A supply that has never been used yet falls back to its used_per_refill times the average
number of containers filled per day. If neither is known, days left is unknown (None) and
only the reorder level can raise an alert.
"""
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import StockMovement, Supply, SupplyMovement

WINDOW_DAYS = 30
ZERO = Decimal("0")
Q2 = Decimal("0.01")


def _round(value):
    return Decimal(value).quantize(Q2, rounding=ROUND_HALF_UP)


@transaction.atomic
def apply_supply_movement(supply, delta, reason, by=None, note=""):
    """Change one supply by `delta` (+ in, - out) and write the log line. Never goes below 0."""
    supply = Supply.objects.select_for_update().get(pk=supply.pk)
    delta = _round(delta)
    if supply.quantity + delta < ZERO:
        # Using more than the records show: take it to 0 and log what really happened in the note.
        delta = -supply.quantity
        note = (note + " (count reached zero)").strip()
    supply.quantity = supply.quantity + delta
    supply.save(update_fields=["quantity", "updated_at"])
    return SupplyMovement.objects.create(supply=supply, delta=delta, reason=reason, by_user=by, note=note[:200])


@transaction.atomic
def consume_for_refills(containers_filled, by=None, note=""):
    """
    Called when a refill batch is recorded. Takes caps, seals, filter life and so on
    off the shelf. Returns the supplies that are low or out AFTER the batch.
    """
    if containers_filled <= 0:
        return []
    note = note or f"Filled {containers_filled} containers"
    touched = []
    for supply in Supply.objects.filter(is_active=True, used_per_refill__gt=0):
        used = _round(supply.used_per_refill * containers_filled)
        if used <= ZERO:
            continue
        apply_supply_movement(supply, -used, SupplyMovement.Reason.USED, by=by, note=note)
        supply.refresh_from_db()
        touched.append(supply)
    return [s for s in touched if status_of(s, daily_usage(s))[0] != "ok"]


def daily_usage(supply, days=WINDOW_DAYS, refills_per_day=None):
    """How much of this supply is used in an average day. None when nothing is known."""
    since = timezone.now() - timedelta(days=days)
    used = (supply.movements.filter(reason=SupplyMovement.Reason.USED, created_at__gte=since)
            .aggregate(n=Sum("delta"))["n"] or ZERO)
    if used < ZERO:
        return _round(-used / days)
    if supply.used_per_refill > 0:
        if refills_per_day is None:
            refills_per_day = average_refills_per_day(days)
        if refills_per_day:
            return _round(supply.used_per_refill * Decimal(str(refills_per_day)))
    return None


def average_refills_per_day(days=WINDOW_DAYS):
    """Containers filled per day lately, from the refill batches in the stock log."""
    since = timezone.now() - timedelta(days=days)
    filled = (StockMovement.objects.filter(reason=StockMovement.Reason.REFILL, created_at__gte=since)
              .aggregate(n=Sum("d_available"))["n"] or 0)
    return filled / days if filled else 0


def days_left(supply, usage):
    if not usage or usage <= ZERO:
        return None
    return float(supply.quantity / usage)


def status_of(supply, usage):
    """-> (status, why). ok | low | out"""
    if supply.quantity <= ZERO:
        return "out", f"{supply.name} has run out."
    left = days_left(supply, usage)
    if supply.reorder_level > 0 and supply.quantity <= supply.reorder_level:
        return "low", f"At or below the restock level of {float(supply.reorder_level):g}."
    if left is not None and left <= supply.lead_time_days:
        return "low", (f"About {left:.0f} day{'s' if round(left) != 1 else ''} left, and a delivery "
                       f"takes {supply.lead_time_days}. Order now.")
    return "ok", ""


def supply_row(supply, refills_per_day=None):
    usage = daily_usage(supply, refills_per_day=refills_per_day)
    left = days_left(supply, usage)
    status, why = status_of(supply, usage)
    return {
        "id": supply.pk, "name": supply.name, "unit": supply.unit,
        "quantity": float(supply.quantity), "used_per_refill": float(supply.used_per_refill),
        "reorder_level": float(supply.reorder_level), "lead_time_days": supply.lead_time_days,
        "is_active": supply.is_active, "note": supply.note,
        "daily_usage": float(usage) if usage is not None else None,
        "days_left": round(left, 1) if left is not None else None,
        "runout_date": (timezone.localdate() + timedelta(days=int(left))).isoformat() if left is not None else None,
        "status": status, "why": why,
        "auto": supply.used_per_refill > 0,
    }


def supplies_payload(include_inactive=True, log_limit=30):
    refills = average_refills_per_day()
    qs = Supply.objects.all() if include_inactive else Supply.objects.filter(is_active=True)
    rows = [supply_row(s, refills_per_day=refills) for s in qs]
    active = [r for r in rows if r["is_active"]]
    log = [{
        "at": m.created_at.isoformat(), "supply": m.supply.name, "reason": m.reason,
        "delta": float(m.delta), "unit": m.supply.unit, "note": m.note,
        "by": (m.by_user.get_full_name() or m.by_user.username) if m.by_user else "System",
    } for m in SupplyMovement.objects.select_related("supply", "by_user")[:log_limit]]
    return {
        "supplies": rows,
        "alerts": [r for r in active if r["status"] != "ok"],
        "counts": {
            "total": len(active),
            "low": sum(1 for r in active if r["status"] == "low"),
            "out": sum(1 for r in active if r["status"] == "out"),
        },
        "refills_per_day": round(refills, 1),
        "window_days": WINDOW_DAYS,
        "log": log,
    }


def clean_supply(data, instance=None):
    """Read and check what the owner typed. Raises ValidationError with plain messages."""
    def _dec(key, default, lo, hi, label):
        raw = data.get(key, getattr(instance, key, default) if instance else default)
        try:
            value = Decimal(str(raw))
        except Exception:
            raise ValidationError({key: [f"Enter a number for {label}."]})
        if not (Decimal(str(lo)) <= value <= Decimal(str(hi))):
            raise ValidationError({key: [f"{label} must be between {lo} and {hi}."]})
        return _round(value)

    name = str(data.get("name", instance.name if instance else "")).strip()
    if len(name) < 2:
        raise ValidationError({"name": ["Give the supply a name, like Bottle caps."]})
    if Supply.objects.filter(name__iexact=name).exclude(pk=getattr(instance, "pk", None)).exists():
        raise ValidationError({"name": ["You already have a supply with this name."]})
    unit = data.get("unit", instance.unit if instance else Supply.Unit.PIECE)
    if unit not in Supply.Unit.values:
        raise ValidationError({"unit": ["Choose piece, litre, kilo or set."]})
    try:
        lead = int(data.get("lead_time_days", instance.lead_time_days if instance else 3))
        if not 0 <= lead <= 90:
            raise ValueError
    except (TypeError, ValueError):
        raise ValidationError({"lead_time_days": ["Enter how many days a delivery takes (0 to 90)."]})
    return {
        "name": name, "unit": unit, "lead_time_days": lead,
        "used_per_refill": _dec("used_per_refill", 0, 0, 100, "Used per container"),
        "reorder_level": _dec("reorder_level", 0, 0, 10 ** 7, "Restock level"),
        "note": str(data.get("note", instance.note if instance else ""))[:160],
        "is_active": bool(data.get("is_active", instance.is_active if instance else True)),
    }
