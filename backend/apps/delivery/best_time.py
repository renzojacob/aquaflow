"""
Feature E: best time to deliver, learned per address.

The system counts successful and failed deliveries per address and period. With at least
SystemSetting.best_time_min_attempts attempts (default 4) at an address, if one period clearly
succeeds more, the order form and the planner suggest it.

  "Clearly" = its success rate is at least MIN_GAP (40 points) higher than the other period's.
  If only one period was ever tried and fewer than half of those deliveries worked, the other
  period is suggested as worth trying (basis = "untried"): that is the usual case for a
  household that always orders mornings and is never home.

Failures that have nothing to do with the time of day (wrong address, refused) are not counted.
Only the most recent RECENT attempts per address count, so a household whose routine changed
is not judged on old habits.

Example from the spec: 3 of 4 morning deliveries failed, every afternoon one worked
-> afternoon is suggested.
"""
from dataclasses import dataclass, field

from apps.station.models import SystemSetting

from .models import DeliveryAttempt

PERIODS = ("morning", "afternoon")
LABEL = {"morning": "morning", "afternoon": "afternoon"}
MIN_GAP = 0.4
RECENT = 20
NOT_ABOUT_TIME = (DeliveryAttempt.FailureReason.WRONG_ADDRESS, DeliveryAttempt.FailureReason.REFUSED)


@dataclass
class Tally:
    attempts: int = 0
    delivered: int = 0

    @property
    def rate(self):
        return self.delivered / self.attempts if self.attempts else None


@dataclass
class AddressHistory:
    by_period: dict = field(default_factory=lambda: {p: Tally() for p in PERIODS})

    @property
    def attempts(self):
        return sum(t.attempts for t in self.by_period.values())


def histories(address_ids):
    """{address_id: AddressHistory} from the newest RECENT attempts at each address. One query."""
    out = {}
    rows = (DeliveryAttempt.objects.filter(order__address_id__in=set(address_ids))
            .exclude(outcome=DeliveryAttempt.Outcome.FAILED, failure_reason__in=NOT_ABOUT_TIME)
            .order_by("order__address_id", "-server_time")
            .values_list("order__address_id", "order__period", "outcome"))
    for address_id, period, outcome in rows:
        h = out.setdefault(address_id, AddressHistory())
        if h.attempts >= RECENT or period not in h.by_period:
            continue
        t = h.by_period[period]
        t.attempts += 1
        t.delivered += outcome == DeliveryAttempt.Outcome.DELIVERED
    return out


def _of(t, period):
    return f"{t.delivered} of {t.attempts} {LABEL[period]} deliver{'y' if t.attempts == 1 else 'ies'}"


def suggestion(history, min_attempts):
    """The better period for this history, or None if there isn't a clear one."""
    if history is None or history.attempts < min_attempts:
        return None
    m, a = history.by_period["morning"], history.by_period["afternoon"]
    stats = {p: {"attempts": t.attempts, "delivered": t.delivered} for p, t in history.by_period.items()}

    if m.attempts and a.attempts:
        best, other = ("morning", "afternoon") if m.rate >= a.rate else ("afternoon", "morning")
        tb, to = history.by_period[best], history.by_period[other]
        if tb.rate - to.rate < MIN_GAP:
            return None
        return {"period": best, "basis": "compared", "stats": stats,
                "summary": f"{_of(tb, best)} worked here, but only {_of(to, other)}."}

    tried = "morning" if m.attempts else "afternoon"
    t = history.by_period[tried]
    if t.rate >= 0.5:
        return None
    untried = "afternoon" if tried == "morning" else "morning"
    return {"period": untried, "basis": "untried", "stats": stats,
            "summary": f"Only {_of(t, tried)} worked here. {LABEL[untried].capitalize()} hasn't been tried yet."}


def best_periods(address_ids):
    """{address_id: suggestion dict} for the addresses that have one. Missing = no suggestion."""
    min_attempts = SystemSetting.load().best_time_min_attempts
    out = {}
    for address_id, h in histories(address_ids).items():
        s = suggestion(h, min_attempts)
        if s:
            out[address_id] = s
    return out


def best_period(address_id):
    return best_periods([address_id]).get(address_id)
