"""
GET /api/v1/dispatch/forecast?days=7|14

How many orders and containers to expect each day, with a prediction band, how well each method
did in testing, and a rough number of trips and riders. Owner and dispatcher only.
The math lives in forecasting.py; this file only reads the data, calls it and shapes the answer.
"""
from django.conf import settings
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsDispatcherOrOwner
from apps.orders.models import Order

from . import forecasting
from .management.commands.seed_forecast_demo import MARK as DEMO_MARK
from .models import Vehicle

HISTORY_DAYS = 28
ALLOWED_DAYS = {"7": 7, "14": 14}

EXAMPLE = {
    "days": 7, "generated_on": "2026-11-10", "timezone": "Asia/Manila", "enough_data": True,
    "history": {"start": "2026-10-14", "end": "2026-11-09",
                "orders": [{"date": "2026-11-09", "value": 15}],
                "containers": [{"date": "2026-11-09", "value": 31}]},
    "orders": {"method": "weekday_average", "method_label": "Weekday average (last 4 weeks)",
               "enough_data": True, "history_days": 84, "backtest_rounds": 9, "interval_level": 0.8,
               "holt_winters_params": None,
               "days": [{"date": "2026-11-10", "value": 18.8, "lower": 15.8, "upper": 23.2}],
               "backtest": [{"method": "naive", "label": "Naive (same as the last day)", "chosen": False,
                             "mae": 4.76, "rmse": 6.55, "wape": 0.256}]},
    "containers": {"method": "weekday_average", "days": [{"date": "2026-11-10", "value": 38.8,
                                                          "lower": 32.0, "upper": 49.8}]},
    "warnings": [],
    "trips": {"vehicles": 2, "average_capacity": 15.0, "fleet_trips_per_day": 4,
              "note": forecasting.TRIPS_NOTE},
    "explanation": "Expect about 30 orders (63 containers) on Friday 13 Nov, the busiest day in the next 7 days. ...",
}


def _series_rows(dates, values):
    return [{"date": d.isoformat(), "value": v} for d, v in zip(dates, values)]


class ForecastView(APIView):
    """Forecast of daily order volume for the next 7 or 14 days."""

    permission_classes = [IsDispatcherOrOwner]

    @extend_schema(
        summary="Forecast daily orders and containers",
        description=(
            "Compares three methods (naive, weekday average, Holt-Winters) with a rolling-origin "
            "backtest and forecasts with the one that has the lowest WAPE. Days are counted by "
            "delivery date in Asia/Manila; rejected, cancelled and failed orders are left out; "
            "today is left out of the history, so the first forecast day is today. With fewer than "
            "28 days of history `enough_data` is false and the weekday average is returned without "
            "a prediction band. `trips` is a rough planning number, or null when no vehicle is "
            "available."),
        parameters=[OpenApiParameter("days", int, required=False, enum=[7, 14],
                                     description="How many days to forecast. 7 (default) or 14.")],
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
        examples=[OpenApiExample("Seven-day forecast (shortened)", value=EXAMPLE, response_only=True)],
    )
    def get(self, request):
        raw = request.query_params.get("days", "7")
        if raw not in ALLOWED_DAYS:
            raise ValidationError({"days": ["Use 7 or 14."]})
        days = ALLOWED_DAYS[raw]

        result = forecasting.build_forecast(days)
        series, orders, boxes = result["series"], result["orders"], result["containers"]

        dates = series.dates()[-HISTORY_DAYS:]
        history = {"start": dates[0].isoformat() if dates else None,
                   "end": dates[-1].isoformat() if dates else None,
                   "orders": _series_rows(dates, series.orders[-HISTORY_DAYS:]),
                   "containers": _series_rows(dates, series.containers[-HISTORY_DAYS:])}

        capacities = list(Vehicle.objects.filter(is_available=True).values_list("capacity_containers", flat=True))
        trips = forecasting.trips_hint(boxes.days, capacities) if boxes.days else None

        warnings = list(orders.warnings)
        if Order.objects.filter(notes__startswith=DEMO_MARK).exists():
            warnings.append("This history includes DEMO orders (from seed_forecast_demo). "
                            "Do not present these numbers as real results.")

        def shape(f):
            out = f.as_dict()
            out.pop("warnings")
            return out

        return Response({
            "days": days,
            "generated_on": timezone.localdate().isoformat(),
            "timezone": settings.TIME_ZONE,
            "enough_data": orders.enough_data,
            "history": history,
            "orders": shape(orders),
            "containers": shape(boxes),
            "warnings": warnings,
            "trips": trips,
            "explanation": forecasting.explain(orders, boxes, trips, days),
        })
