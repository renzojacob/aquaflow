"""
Demand forecasting: how many orders (and containers) to expect each day.

Plain Python on purpose (no numpy): the series is one number per day, a few hundred values at most.

Three methods are compared on the shop's own history with a rolling-origin backtest, and the one
with the lowest WAPE is used for the forecast:

  naive            every day is the same as the last day we saw
  weekday_average  the average of the same weekday over the last 4 weeks
  holt_winters     additive level + trend + weekly (period 7) seasonality, with its smoothing
                   parameters picked by a small grid search on a validation window

Backtest: start with 3 weeks of history, forecast the next 7 days, compare with what happened, then
grow the history by a week and repeat. Errors from every round are pooled into MAE, RMSE and WAPE.
Smoothing parameters for Holt-Winters are re-picked inside every round from that round's history
only, so the backtest never peeks at the days it is scored on.

The prediction interval comes from the chosen method's own backtest errors (see `interval_offsets`).

Days are counted by delivery_date (a local Manila date). Rejected, cancelled and failed orders are
not demand and are left out. Today is left out of the history because it is still filling up, so the
first forecast day is today.

With fewer than 4 weeks of history the backtest would mean little: the result says so
(`enough_data = False`) and falls back to the weekday average, with no interval.
"""
import math
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from itertools import product

PERIOD = 7                 # a week
MIN_DAYS = 28              # below this: "not enough data"
MIN_TRAIN = 21             # first backtest round trains on 3 weeks
HORIZON = 7                # every backtest round forecasts one week ahead
VALIDATION = 14            # days held out to choose Holt-Winters parameters
WEEKDAY_WEEKS = 4
INTERVAL_LOW, INTERVAL_HIGH = 0.10, 0.90      # an 80% interval
MIN_RESIDUALS = 10         # fewer backtest errors than this: use a normal-theory band instead
Z_80 = 1.2816

ALPHAS = (0.1, 0.3, 0.5)   # level smoothing
BETAS = (0.0, 0.05, 0.1)   # trend smoothing
GAMMAS = (0.1, 0.3, 0.5)   # weekly pattern smoothing
DEFAULT_PARAMS = (0.3, 0.05, 0.3)


# ---------------------------------------------------------------- data


@dataclass
class DailySeries:
    start: date | None
    orders: list = field(default_factory=list)
    containers: list = field(default_factory=list)

    def __len__(self):
        return len(self.orders)

    def dates(self):
        return [self.start + timedelta(days=i) for i in range(len(self.orders))]


def load_daily_series(today=None):
    """One row per day, first valid order through yesterday, empty days filled with 0."""
    from django.db.models import Count, Sum
    from django.utils import timezone

    from apps.orders.models import Order
    from apps.orders.slots import NOT_BOOKED

    today = today or timezone.localdate()
    rows = (Order.objects.exclude(status__in=NOT_BOOKED)
            .filter(delivery_date__lt=today)
            .order_by()                      # Order has a default ordering that would split the groups
            .values("delivery_date")
            .annotate(n=Count("id"), boxes=Sum("containers")))
    by_day = {r["delivery_date"]: r for r in rows}
    if not by_day:
        return DailySeries(start=None)
    start, end = min(by_day), today - timedelta(days=1)
    series = DailySeries(start=start)
    for i in range((end - start).days + 1):
        row = by_day.get(start + timedelta(days=i))
        series.orders.append(row["n"] if row else 0)
        series.containers.append(int(row["boxes"] or 0) if row else 0)
    return series


# ---------------------------------------------------------------- the three methods
# Each takes the history `y` (one number per day, oldest first) and returns the next `h` days.
# Weekday is the position in the list modulo 7, so no dates are needed here.


def naive(y, h):
    return [float(y[-1])] * h


def weekday_average(y, h, weeks=WEEKDAY_WEEKS):
    n, out = len(y), []
    for k in range(h):
        first = k // PERIOD + 1               # nearest earlier same-weekday that is already history
        picks = [y[n + k - PERIOD * j] for j in range(first, first + weeks) if n + k - PERIOD * j >= 0]
        out.append(sum(picks) / len(picks) if picks else (sum(y) / len(y) if y else 0.0))
    return out


def _hw_fit(y, alpha, beta, gamma):
    """Run additive Holt-Winters over y. Needs at least two full weeks."""
    m = PERIOD
    trend = (sum(y[m:2 * m]) - sum(y[:m])) / (m * m)       # average change per day between week 1 and 2
    level = sum(y[:m]) / m + trend * (m - 1) / 2            # level at the END of week 1
    season = [y[i] - (level + trend * (i - (m - 1))) for i in range(m)]
    for t in range(m, len(y)):
        s = season[t % m]
        last_level = level
        level = alpha * (y[t] - s) + (1 - alpha) * (level + trend)
        trend = beta * (level - last_level) + (1 - beta) * trend
        season[t % m] = gamma * (y[t] - level) + (1 - gamma) * s
    return level, trend, season


def _hw_predict(state, n, h):
    level, trend, season = state
    return [max(0.0, level + (k + 1) * trend + season[(n + k) % PERIOD]) for k in range(h)]


def holt_winters_params(y):
    """Grid-search (alpha, beta, gamma) on a validation window cut off the end of y."""
    n = len(y)
    hold = VALIDATION if n - VALIDATION >= 2 * PERIOD else PERIOD
    if n - hold < 2 * PERIOD:
        return DEFAULT_PARAMS
    train, val = y[:-hold], y[-hold:]
    best, best_err = DEFAULT_PARAMS, math.inf
    for params in product(ALPHAS, BETAS, GAMMAS):
        pred = _hw_predict(_hw_fit(train, *params), len(train), hold)
        err = sum(abs(a - p) for a, p in zip(val, pred))
        if err < best_err - 1e-12:
            best, best_err = params, err
    return best


def holt_winters(y, h):
    if len(y) < 2 * PERIOD:                                  # not enough for a seasonal start
        return weekday_average(y, h)
    state = _hw_fit(y, *holt_winters_params(y))
    return _hw_predict(state, len(y), h)


METHODS = {"naive": naive, "weekday_average": weekday_average, "holt_winters": holt_winters}
LABELS = {"naive": "Naive (same as the last day)",
          "weekday_average": "Weekday average (last 4 weeks)",
          "holt_winters": "Holt-Winters (trend + weekly pattern)"}


# ---------------------------------------------------------------- scoring


def error_metrics(actual, predicted):
    """MAE, RMSE and WAPE (None when every actual is 0, since WAPE divides by their total)."""
    n = len(actual)
    if n == 0:
        return {"mae": None, "rmse": None, "wape": None}
    errs = [a - p for a, p in zip(actual, predicted)]
    total = sum(actual)
    return {"mae": sum(abs(e) for e in errs) / n,
            "rmse": math.sqrt(sum(e * e for e in errs) / n),
            "wape": sum(abs(e) for e in errs) / total if total > 0 else None}


def backtest(y):
    """
    Rolling-origin, expanding window. Returns {method: {"actual": [...], "predicted": [...]}}
    with the pooled results of every round, oldest round first.
    """
    pooled = {name: {"actual": [], "predicted": []} for name in METHODS}
    origin = MIN_TRAIN
    while origin + HORIZON <= len(y):
        history, actual = y[:origin], y[origin:origin + HORIZON]
        for name, fn in METHODS.items():
            pooled[name]["actual"].extend(actual)
            pooled[name]["predicted"].extend(fn(history, HORIZON))
        origin += HORIZON
    return pooled


def choose_method(table):
    """Lowest WAPE wins; a tie goes to the simpler method (the order of METHODS)."""
    order = list(METHODS)
    ranked = sorted(order, key=lambda m: (math.inf if table[m]["wape"] is None else round(table[m]["wape"], 9),
                                          order.index(m)))
    return ranked[0]


def _quantile(sorted_values, q):
    """Nearest-rank quantile."""
    return sorted_values[max(0, math.ceil(q * len(sorted_values)) - 1)]


def interval_offsets(actual, predicted):
    """(low, high) amounts to add to a one-week-ahead forecast: the 10th and 90th percentile of the
    chosen method's backtest errors. They always bracket 0 so the band contains the forecast."""
    residuals = sorted(a - p for a, p in zip(actual, predicted))
    if len(residuals) >= MIN_RESIDUALS:
        return min(_quantile(residuals, INTERVAL_LOW), 0.0), max(_quantile(residuals, INTERVAL_HIGH), 0.0)
    rmse = error_metrics(actual, predicted)["rmse"]
    if rmse is None:
        return 0.0, 0.0
    return -Z_80 * rmse, Z_80 * rmse


# ---------------------------------------------------------------- data quality


def data_quality(y):
    """Plain-language warnings about the history that the forecast is built on."""
    warnings, n = [], len(y)
    if n == 0:
        return ["There are no orders yet, so there is nothing to forecast from."]
    if n < MIN_DAYS:
        warnings.append(f"Only {n} days of history. At least {MIN_DAYS} (4 weeks) are needed for a "
                        "reliable forecast, so the weekday average is shown instead.")
    zeros = sum(1 for v in y if v == 0)
    if zeros / n > 0.4:
        warnings.append(f"{zeros} of {n} days had no orders. Forecasts for a shop this quiet are rough.")
    tail = 0
    for v in reversed(y):
        if v != 0:
            break
        tail += 1
    if tail >= 3:
        warnings.append(f"No orders in the last {tail} days. If the service was paused, the forecast "
                        "will be too low.")
    if n >= PERIOD * 2:
        ordered = sorted(y)
        med = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
        mad = sorted(abs(v - med) for v in y)[n // 2]
        if mad > 0:
            odd = sum(1 for v in y if 0.6745 * abs(v - med) / mad > 3.5)
            if odd == 1:
                warnings.append("1 unusual day in the history (a storm, a holiday, a one-off bulk order). "
                                "It can pull the forecast.")
            elif odd > 1:
                warnings.append(f"{odd} unusually busy or quiet days in the history (storms, holidays, "
                                "one-off bulk orders). They can pull the forecast.")
    if n >= MIN_DAYS and sum(y) / n < 2:
        warnings.append("Fewer than 2 orders a day on average. Small numbers swing a lot, so expect wide bands.")
    return warnings


# ---------------------------------------------------------------- the forecast


@dataclass
class ForecastDay:
    date: str
    value: float
    lower: float | None
    upper: float | None


@dataclass
class Forecast:
    enough_data: bool
    method: str | None
    method_label: str | None
    history_days: int
    horizon: int
    days: list = field(default_factory=list)          # ForecastDay
    backtest: list = field(default_factory=list)      # one row per method
    backtest_rounds: int = 0
    interval_level: float | None = None
    holt_winters_params: dict | None = None
    warnings: list = field(default_factory=list)

    def as_dict(self):
        return asdict(self)


def forecast_series(y, start, horizon=HORIZON):
    """
    y: one number per day, oldest first, with `start` the date of y[0]; the first forecast day is the
    day after y ends. Returns a Forecast.
    """
    n = len(y)
    out = Forecast(enough_data=n >= MIN_DAYS, method=None, method_label=None,
                   history_days=n, horizon=horizon, warnings=data_quality(y))
    if n == 0:
        return out
    first_day = start + timedelta(days=n)

    def day(k):
        return (first_day + timedelta(days=k)).isoformat()

    if not out.enough_data:
        values = weekday_average(y, horizon)
        out.method, out.method_label = "weekday_average", LABELS["weekday_average"]
        out.days = [ForecastDay(day(k), round(v, 2), None, None) for k, v in enumerate(values)]
        return out

    pooled = backtest(y)
    table = {name: error_metrics(r["actual"], r["predicted"]) for name, r in pooled.items()}
    best = choose_method(table)
    out.method, out.method_label = best, LABELS[best]
    out.backtest_rounds = len(pooled[best]["actual"]) // HORIZON
    out.backtest = [{"method": name, "label": LABELS[name], "chosen": name == best,
                     **{k: (None if v is None else round(v, 4)) for k, v in table[name].items()}}
                    for name in METHODS]
    if best == "holt_winters":
        a, b, g = holt_winters_params(y)
        out.holt_winters_params = {"alpha": a, "beta": b, "gamma": g}

    low, high = interval_offsets(pooled[best]["actual"], pooled[best]["predicted"])
    out.interval_level = INTERVAL_HIGH - INTERVAL_LOW
    values = METHODS[best](y, horizon)
    for k, v in enumerate(values):
        spread = math.sqrt(max(k + 1, HORIZON) / HORIZON)    # the further out, the wider
        out.days.append(ForecastDay(day(k), round(v, 2), round(max(0.0, v + low * spread), 2),
                                    round(v + high * spread, 2)))
    return out


def build_forecast(horizon=HORIZON, today=None):
    """Orders and containers forecasts from the real order table."""
    series = load_daily_series(today)
    return {"series": series,
            "orders": forecast_series(series.orders, series.start, horizon),
            "containers": forecast_series(series.containers, series.start, horizon)}


# ---------------------------------------------------------------- planning hint and explanation

TRIPS_PER_VEHICLE_PER_DAY = 2          # one morning trip and one afternoon trip
TRIPS_NOTE = ("Rough planning number from the average vehicle size. It ignores routes and distances; "
              "the Plan screen makes the real trips.")
SHORT_NAMES = {"naive": "The naive method", "weekday_average": "The weekday average",
               "holt_winters": "Holt-Winters"}


def trips_hint(container_days, vehicle_capacities):
    """
    How many trips and riders the forecast containers might need. `container_days` are ForecastDay
    objects for containers; `vehicle_capacities` is the capacity of every AVAILABLE vehicle.
    Returns None when there is no vehicle to base it on.

    Per day: trips = containers / average vehicle capacity, rounded up. A vehicle can go out
    in the morning and again in the afternoon, so riders = trips / 2, rounded up. The "busy"
    figures use the top of the prediction band instead of the forecast itself.
    """
    caps = [c for c in vehicle_capacities if c and c > 0]
    if not caps:
        return None
    average = sum(caps) / len(caps)
    fleet_trips = len(caps) * TRIPS_PER_VEHICLE_PER_DAY
    rows = []
    for d in container_days:
        trips = math.ceil(d.value / average) if d.value > 0 else 0
        top = d.upper if d.upper is not None else d.value
        busy = math.ceil(top / average) if top > 0 else 0
        rows.append({"date": d.date, "containers": d.value, "trips_needed": trips,
                     "riders_needed": math.ceil(trips / TRIPS_PER_VEHICLE_PER_DAY),
                     "busy_trips_needed": busy,
                     "busy_riders_needed": math.ceil(busy / TRIPS_PER_VEHICLE_PER_DAY),
                     "fleet_enough": busy <= fleet_trips})
    peak = max(rows, key=lambda r: r["containers"], default=None)
    return {"vehicles": len(caps), "total_capacity": sum(caps), "average_capacity": round(average, 1),
            "fleet_trips_per_day": fleet_trips, "days": rows,
            "peak_date": peak["date"] if peak else None,
            "over_capacity_days": [r["date"] for r in rows if not r["fleet_enough"]],
            "note": TRIPS_NOTE}


def _plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def _day_label(iso):
    d = date.fromisoformat(iso)
    return f"{d:%A} {d.day} {d:%b}"


def explain(orders, containers, trips, days):
    """A few plain sentences for the owner. `orders` and `containers` are Forecast objects."""
    if orders.history_days == 0 or not orders.days:
        return ("There are no orders yet, so there is nothing to forecast. Once customers start "
                "ordering, this page shows what to expect each day.")
    peak = max(orders.days, key=lambda d: d.value)
    boxes = {d.date: d.value for d in containers.days}.get(peak.date)
    said = [f"Expect about {round(peak.value)} orders"
            + (f" ({round(boxes)} containers)" if boxes is not None else "")
            + f" on {_day_label(peak.date)}, the busiest day in the next {days} days."]
    said.append(f"In all, about {round(sum(d.value for d in orders.days))} orders over the next {days} days.")

    if trips is None:
        said.append("Add your vehicles on the Vehicles screen to get a trips estimate.")
    else:
        row = next((r for r in trips["days"] if r["date"] == peak.date), None)
        if row:
            line = (f"On that day plan about {_plural(row['trips_needed'], 'trip')} and "
                    f"{_plural(row['riders_needed'], 'rider')}")
            if row["busy_trips_needed"] > row["trips_needed"]:
                line += f" (up to {_plural(row['busy_trips_needed'], 'trip')} if it turns out busy)"
            said.append(line + ".")
        if trips["over_capacity_days"]:
            said.append(f"Your {_plural(trips['vehicles'], 'available vehicle')} can make "
                        f"{trips['fleet_trips_per_day']} trips a day, which may not be enough on "
                        f"{_day_label(trips['over_capacity_days'][0])}.")

    if orders.enough_data:
        chosen = next(r for r in orders.backtest if r["chosen"])
        wape = chosen["wape"]
        how = f"{SHORT_NAMES[orders.method]} was chosen because it was the most accurate in testing"
        if wape is not None:
            how += f", off by about {round(wape * 100)}% on average"
        said.append(how + f" (tested on {orders.backtest_rounds} past weeks).")
    else:
        said.append(f"There are only {orders.history_days} days of history (4 weeks are needed), so this "
                    "is a rough weekday-average guess, not a tested forecast.")
    return " ".join(said)
