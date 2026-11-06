"""
Feature C: "Never Run Out" household refill prediction.

A household is one customer at one address (a customer with a home and a store is two
households). From its delivered refill orders:

  1. For each pair of deliveries in a row:
         days per container = days between the deliveries / containers in the earlier one
  2. Weighted average of the last three values, weights 3, 2, 1 (most recent counts most).
  3. Predicted run-out = last delivery date + last quantity x days per container.
  4. Needs at least three delivered orders; otherwise "not enough history yet".

Two deliveries on the same day count as one delivery of all their containers, so a
second order that day never makes a 0-day interval.

This is a statistical estimate, not trained AI. The backtest (backtest()) shows honestly
how far off it is for real households.
"""
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order

from .models import RefillPrediction, ReminderLog

log = logging.getLogger(__name__)

S = Order.Status
WEIGHTS = (3, 2, 1)            # most recent interval first
MIN_ORDERS = 3                 # delivered orders needed before we predict
REMIND_DAYS_BEFORE = 2         # reminder goes out this many days before run-out
OVERDUE_GRACE_DAYS = 7         # past run-out with no order: still expected for this long, then lapsed
OPEN_STATUSES = (S.PENDING, S.CONFIRMED, S.PREPARING, S.READY, S.OUT_FOR_DELIVERY)
CONFIRMED_STATUSES = (S.CONFIRMED, S.PREPARING, S.READY)   # hold stock (orders.services.HOLDS_RESERVATION)


# ---------------------------------------------------------------------------
# The calculation (pure: no database, easy to test and to backtest)
# ---------------------------------------------------------------------------
@dataclass
class Estimate:
    days_per_container: Decimal
    runout: date
    last_date: date
    last_quantity: int
    intervals: list = field(default_factory=list)   # [{from, to, days, containers, days_per_container}]
    weights: list = field(default_factory=list)

    def inputs(self):
        return {
            "intervals": self.intervals,
            "weights": self.weights,
            "method": f"weighted {'/'.join(map(str, WEIGHTS))} average, min {MIN_ORDERS} orders",
        }


def merge_same_day(deliveries):
    """[(date, containers)] in any order -> one entry per date, oldest first."""
    per_day = defaultdict(int)
    for d, n in deliveries:
        if n > 0:
            per_day[d] += n
    return sorted(per_day.items())


def estimate(deliveries):
    """
    deliveries: [(date, containers)], oldest first, one per date (see merge_same_day).
    Returns an Estimate, or None when there are fewer than MIN_ORDERS deliveries.
    """
    if len(deliveries) < MIN_ORDERS:
        return None
    intervals = []
    for (d0, n0), (d1, _) in zip(deliveries, deliveries[1:]):
        days = (d1 - d0).days
        intervals.append({
            "from": d0.isoformat(), "to": d1.isoformat(), "days": days, "containers": n0,
            "days_per_container": round(days / n0, 2),
        })
    recent = [Decimal(i["days"]) / Decimal(i["containers"]) for i in intervals[-len(WEIGHTS):]]
    recent.reverse()                                 # most recent first, to meet weight 3
    weights = WEIGHTS[:len(recent)]
    dpc = sum(r * w for r, w in zip(recent, weights)) / sum(weights)
    dpc = dpc.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    last_date, last_qty = deliveries[-1]
    days_left = int((last_qty * dpc).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return Estimate(
        days_per_container=dpc,
        runout=last_date + timedelta(days=days_left),
        last_date=last_date,
        last_quantity=last_qty,
        intervals=intervals[-len(WEIGHTS):],
        weights=list(weights),
    )


# ---------------------------------------------------------------------------
# Reading history from the database
# ---------------------------------------------------------------------------
def _containers(order):
    """Station containers delivered. Very old orders (before the cart) kept them in quantity."""
    if order.containers:
        return order.containers
    from apps.inventory.models import Product
    return order.quantity if order.product.kind == Product.Kind.REFILL else 0


def delivered_histories(**filters):
    """{(customer_id, address_id): [(date, containers)]} for delivered orders, merged per day."""
    raw = defaultdict(list)
    qs = (Order.objects.filter(status=S.DELIVERED, **filters)
          .select_related("product").only("customer_id", "address_id", "delivery_date",
                                          "containers", "quantity", "product__kind"))
    for o in qs:
        raw[(o.customer_id, o.address_id)].append((o.delivery_date, _containers(o)))
    return {k: merge_same_day(v) for k, v in raw.items()}


def delivered_count(customer, address):
    return len(delivered_histories(customer=customer, address=address).get((customer.pk, address.pk), []))


# ---------------------------------------------------------------------------
# Keeping one current prediction per household
# ---------------------------------------------------------------------------
@transaction.atomic
def refresh_prediction(customer, address, *, delivered_order=None):
    """
    Recompute the household's prediction. The old one stops being current (it is kept, with
    the order that actually came next, for accuracy reporting). Returns the new current
    prediction, or None when there is not enough history yet.
    """
    history = delivered_histories(customer=customer, address=address).get((customer.pk, address.pk), [])
    est = estimate(history)

    old = (RefillPrediction.objects.select_for_update()
           .filter(customer=customer, address=address, is_current=True).first())
    if old is not None:
        if delivered_order is not None and old.actual_order_id is None \
                and delivered_order.delivery_date > old.last_delivery_date:
            old.actual_order = delivered_order
        old.is_current = False
        old.save(update_fields=["is_current", "actual_order"])

    if est is None:
        return None
    return RefillPrediction.objects.create(
        customer=customer, address=address,
        predicted_runout_date=est.runout,
        days_per_container=est.days_per_container,
        last_delivery_date=est.last_date,
        last_quantity=est.last_quantity,
        inputs=est.inputs(),
    )


def refresh_after_delivery(order):
    """
    Called by delivery.services.record_attempt once an order is delivered. A problem here
    must never undo the delivery record (riders sync these from offline phones), so it runs
    in its own savepoint and only logs if something goes wrong.
    """
    try:
        with transaction.atomic():
            return refresh_prediction(order.customer, order.address, delivered_order=order)
    except Exception:  # noqa: BLE001 - logged, the delivery itself must still be saved
        log.exception("Could not refresh the refill prediction after order %s", order.pk)
        return None


def rebuild_all():
    """Recompute every household from scratch (backfill, or after fixing old orders)."""
    from apps.accounts.models import User
    from apps.customers.models import Address

    made = skipped = 0
    for customer_id, address_id in delivered_histories().keys():
        p = refresh_prediction(User(pk=customer_id), Address(pk=address_id))
        made += p is not None
        skipped += p is None
    return made, skipped


# ---------------------------------------------------------------------------
# Who still needs water (open orders, reminders, demand)
# ---------------------------------------------------------------------------
def open_households():
    """{(customer_id, address_id)} that already have an order in progress."""
    return set(Order.objects.filter(status__in=OPEN_STATUSES).values_list("customer_id", "address_id"))


def open_order_for(customer, address):
    return (Order.objects.filter(customer=customer, address=address, status__in=OPEN_STATUSES)
            .order_by("delivery_date", "id").first())


def _active_predictions():
    return (RefillPrediction.objects.filter(is_current=True, customer__is_active=True,
                                            address__is_archived=False)
            .select_related("customer", "customer__customer_profile", "address"))


def _reminders_on(user):
    profile = getattr(user, "customer_profile", None)
    return True if profile is None else profile.reminders_enabled


def usual_quantity(prediction):
    profile = getattr(prediction.customer, "customer_profile", None)
    return profile.usual_quantity if profile and profile.usual_quantity else prediction.last_quantity


# ---------------------------------------------------------------------------
# Reminders (the daily job: python manage.py send_refill_reminders)
# ---------------------------------------------------------------------------
def reorder_url(prediction):
    base = getattr(settings, "FRONTEND_URL", "").rstrip("/")
    return f"{base}/customer/home?reorder={prediction.pk}"


def due_reminders(today=None):
    """
    Current predictions whose reminder day has come: run-out is within REMIND_DAYS_BEFORE days
    and has not passed (a missed day is caught up the next morning, never after run-out).
    Skips households with reminders off or an order already in progress.
    """
    today = today or timezone.localdate()
    busy = open_households()
    qs = _active_predictions().filter(predicted_runout_date__gte=today,
                                      predicted_runout_date__lte=today + timedelta(days=REMIND_DAYS_BEFORE))
    return [p for p in qs if _reminders_on(p.customer) and (p.customer_id, p.address_id) not in busy]


@transaction.atomic
def send_reminder(prediction):
    """
    In-app reminder always; email when the customer has an address. Each channel is sent at
    most once per prediction (ReminderLog unique constraint), so running the job twice is safe.
    Returns the channels newly sent.
    """
    from apps.notifications.models import EmailLog

    sent = []
    _, created = ReminderLog.objects.get_or_create(
        prediction=prediction, channel=ReminderLog.Channel.IN_APP,
        defaults={"customer": prediction.customer})
    if created:
        sent.append(ReminderLog.Channel.IN_APP)

    user = prediction.customer
    if user.email:
        _, created = ReminderLog.objects.get_or_create(
            prediction=prediction, channel=ReminderLog.Channel.EMAIL, defaults={"customer": user})
        if created:
            EmailLog.objects.create(
                to_email=user.email, user=user, template=EmailLog.Template.REFILL_REMINDER,
                context={
                    "first_name": user.first_name or user.username,
                    "runout_date": prediction.predicted_runout_date.isoformat(),
                    "runout_day": prediction.predicted_runout_date.strftime("%A, %b %-d"),
                    "quantity": usual_quantity(prediction),
                    "address_label": prediction.address.label or "your address",
                    "reorder_url": reorder_url(prediction),
                },
            )
            sent.append(ReminderLog.Channel.EMAIL)
    return sent


def send_due_reminders(today=None, dry_run=False):
    """Returns [(prediction, channels sent)]."""
    out = []
    for p in due_reminders(today):
        out.append((p, [] if dry_run else send_reminder(p)))
    return out


# ---------------------------------------------------------------------------
# One-tap reorder
# ---------------------------------------------------------------------------
def earliest_slot(now=None):
    """(date, period) of the first delivery time customers can still order for."""
    from apps.orders.services import PERIOD_START
    now = timezone.localtime(now) if now else timezone.localtime()
    today = now.date()
    for day in (today, today + timedelta(days=1)):
        for period in (Order.Period.MORNING, Order.Period.AFTERNOON):
            if day > today or now.time() < PERIOD_START[period]:
                return day, period
    return today + timedelta(days=1), Order.Period.MORNING   # not reached: tomorrow is always open


@transaction.atomic
def reorder(customer, prediction, *, delivery_date=None, period=None):
    """Place the usual order for this household and tie it to the reminder that prompted it."""
    from apps.customers.models import Address
    from apps.orders.services import place_order

    if prediction.customer_id != customer.pk:
        raise ValidationError("Prediction not found.")
    if open_order_for(customer, prediction.address) is not None:
        raise ValidationError("You already have an order on the way to this address.")

    address = prediction.address
    if address.is_archived:
        address = (Address.objects.filter(customer=customer, is_archived=False)
                   .order_by("-is_default", "id").first())
        if address is None:
            raise ValidationError({"address": ["Add a delivery address first."]})

    if delivery_date is None or period is None:
        delivery_date, period = earliest_slot()

    order = place_order(customer, address=address, delivery_date=delivery_date, period=period,
                        quantity=usual_quantity(prediction), source=Order.Source.REMINDER_REORDER)
    ReminderLog.objects.filter(prediction=prediction, reordered_order__isnull=True) \
        .update(reordered_order=order)
    return order


# ---------------------------------------------------------------------------
# What the customer's home card shows
# ---------------------------------------------------------------------------
def customer_cards(customer, today=None):
    """One entry per saved address that has delivered orders or a prediction, soonest run-out first."""
    from apps.customers.models import Address
    from apps.orders.services import PERIOD_START, default_product

    today = today or timezone.localdate()
    profile = getattr(customer, "customer_profile", None)
    reminders_on = True if profile is None else profile.reminders_enabled
    histories = delivered_histories(customer=customer)
    preds = {p.address_id: p for p in RefillPrediction.objects.filter(customer=customer, is_current=True)}
    product = default_product()
    slot_day, slot_period = earliest_slot()

    cards = []
    for a in Address.objects.filter(customer=customer, is_archived=False).order_by("-is_default", "id"):
        count = len(histories.get((customer.pk, a.pk), []))
        p = preds.get(a.pk)
        if not count and p is None:
            continue
        open_order = open_order_for(customer, a)
        card = {
            "address": {"id": a.pk, "label": a.label, "barangay": a.barangay},
            "orders_counted": count,
            "orders_needed": MIN_ORDERS,
            "reminders_enabled": reminders_on,
            "open_order": {"id": open_order.pk, "status": open_order.status,
                           "delivery_date": open_order.delivery_date.isoformat(),
                           "period": open_order.period} if open_order else None,
        }
        if p is None:
            card["state"] = "not_enough_history"
            cards.append(card)
            continue
        qty = usual_quantity(p)
        reminder = p.reminders.order_by("sent_at").first()
        days_left = (p.predicted_runout_date - today).days
        card.update({
            "state": "ok",
            "prediction_id": p.pk,
            "predicted_runout_date": p.predicted_runout_date.isoformat(),
            "days_left": days_left,
            "remind_on": (p.predicted_runout_date - timedelta(days=REMIND_DAYS_BEFORE)).isoformat(),
            "days_per_container": float(p.days_per_container),
            "last_delivery_date": p.last_delivery_date.isoformat(),
            "last_quantity": p.last_quantity,
            "inputs": p.inputs,
            "reminder_sent_at": reminder.sent_at.isoformat() if reminder else None,
            "reorder": {
                "quantity": qty,
                "delivery_date": slot_day.isoformat(),
                "period": slot_period,
                "starts_at": PERIOD_START[slot_period].strftime("%H:%M"),
                "total": float(product.price * qty) if product else None,
            },
        })
        cards.append(card)
    cards.sort(key=lambda c: (c["state"] != "ok", c.get("days_left", 0)))
    return cards


# ---------------------------------------------------------------------------
# Station demand: confirmed orders + predicted reorders without an open order
# ---------------------------------------------------------------------------
def demand(days=7, today=None, ready_stock=None):
    """
    Per day from today: containers already confirmed, plus containers we expect households to
    reorder (their predicted run-out falls that day) when they have no order in progress, so
    nothing is counted twice. Run-outs that passed in the last OVERDUE_GRACE_DAYS days with no
    order are expected today; older ones are treated as lapsed and left out.

    Preparation suggestion: how many more containers to fill so that ready stock covers
    everything expected up to and including that day.
    """
    today = today or timezone.localdate()
    end = today + timedelta(days=days - 1)
    rows = {today + timedelta(days=i): {"confirmed": 0, "confirmed_orders": 0, "pending": 0,
                                         "predicted": 0, "households": []}
            for i in range(days)}

    for o in Order.objects.filter(delivery_date__gte=today, delivery_date__lte=end,
                                  status__in=CONFIRMED_STATUSES + (S.PENDING,)).select_related("product"):
        r = rows[o.delivery_date]
        if o.status == S.PENDING:
            r["pending"] += _containers(o)
        else:
            r["confirmed"] += _containers(o)
            r["confirmed_orders"] += 1

    busy = open_households()
    for p in _active_predictions().filter(predicted_runout_date__gte=today - timedelta(days=OVERDUE_GRACE_DAYS),
                                          predicted_runout_date__lte=end):
        if (p.customer_id, p.address_id) in busy:
            continue
        day = max(p.predicted_runout_date, today)
        r = rows[day]
        r["predicted"] += p.last_quantity
        r["households"].append({
            "prediction_id": p.pk,
            "customer": p.customer.get_full_name() or p.customer.username,
            "address": p.address.label,
            "barangay": p.address.barangay,
            "containers": p.last_quantity,
            "runout": p.predicted_runout_date.isoformat(),
            "overdue_days": max(0, (today - p.predicted_runout_date).days),
        })

    if ready_stock is None:
        ready_stock = _ready_stock()
    out, running = [], 0
    for d, r in sorted(rows.items()):
        expected = r["confirmed"] + r["predicted"]
        running += expected
        out.append({"date": d.isoformat(), **r, "expected": expected,
                    "cumulative_expected": running,
                    "prepare": max(0, running - ready_stock)})
    return {"ready_stock": ready_stock, "days": out,
            "totals": {k: sum(x[k] for x in out) for k in ("confirmed", "pending", "predicted", "expected")},
            "prepare": out[-1]["prepare"] if out else 0}


def _ready_stock():
    from apps.inventory.models import StockLevel
    from apps.orders.services import default_product
    product = default_product()
    if product is None:
        return 0
    st = StockLevel.objects.filter(product=product).first()
    return (st.filled_available + st.filled_reserved) if st else 0


# ---------------------------------------------------------------------------
# Backtest: how good would the prediction have been?
# ---------------------------------------------------------------------------
def backtest(since=None, until=None):
    """
    For every household, at every point where it had at least MIN_ORDERS deliveries, predict
    the next order using only the deliveries before it, then compare with the real date.
    error = real date - predicted date (positive: they ordered later than predicted).
    `since`/`until` limit which real next orders are scored (the history before is always used).
    """
    points = []
    per_household = []
    names = {}
    for (customer_id, address_id), history in delivered_histories().items():
        errs = []
        for k in range(MIN_ORDERS, len(history)):
            actual = history[k][0]
            if (since and actual < since) or (until and actual > until):
                continue
            est = estimate(history[:k])
            err = (actual - est.runout).days
            errs.append(err)
            points.append({"customer_id": customer_id, "address_id": address_id,
                           "predicted": est.runout.isoformat(), "actual": actual.isoformat(),
                           "error_days": err})
        if errs:
            names[(customer_id, address_id)] = None
            per_household.append({"customer_id": customer_id, "address_id": address_id,
                                  "predictions": len(errs), **_score(errs)})

    if names:
        from apps.customers.models import Address
        for a in Address.objects.filter(pk__in=[k[1] for k in names]).select_related("customer"):
            names[(a.customer_id, a.pk)] = (a.customer.get_full_name() or a.customer.username, a.label)
        for h in per_household:
            who, label = names.get((h["customer_id"], h["address_id"])) or ("", "")
            h["customer"], h["address"] = who, label

    errors = [p["error_days"] for p in points]
    buckets = defaultdict(int)
    for e in errors:
        buckets[max(-7, min(7, e))] += 1
    per_household.sort(key=lambda h: -h["mean_abs_error"])
    return {
        "predictions": len(points),
        "households": len(per_household),
        **_score(errors),
        "histogram": [{"error_days": e, "count": buckets.get(e, 0)} for e in range(-7, 8)],
        "per_household": per_household,
        "min_orders": MIN_ORDERS,
        "reminders": _reminder_stats(since, until),
    }


def _score(errors):
    if not errors:
        return {"mean_abs_error": None, "mean_error": None, "within_1_day": None}
    n = len(errors)
    return {
        "mean_abs_error": round(sum(abs(e) for e in errors) / n, 2),
        "mean_error": round(sum(errors) / n, 2),
        "within_1_day": round(sum(1 for e in errors if abs(e) <= 1) / n, 4),
    }


def _reminder_stats(since=None, until=None):
    qs = ReminderLog.objects.all()
    tz = timezone.get_current_timezone()
    if since:
        qs = qs.filter(sent_at__gte=datetime.combine(since, time.min, tzinfo=tz))
    if until:
        qs = qs.filter(sent_at__lt=datetime.combine(until + timedelta(days=1), time.min, tzinfo=tz))
    households = qs.values("prediction_id").distinct().count()
    reordered = qs.filter(reordered_order__isnull=False).values("prediction_id").distinct().count()
    return {"reminded": households, "reordered": reordered,
            "reorder_rate": round(reordered / households, 4) if households else None}

