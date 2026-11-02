"""
Dispatcher + owner API: the order queue, order actions, stock, and the owner's numbers.
URL prefix: /api/v1/dispatch/  (the frontend's dispatcherService.js calls these).

Every rule lives in the services (orders.services.transition and dispatch.services),
so these views only read the request, call one service, and return the order.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import CustomerProfile
from apps.accounts.permissions import IsDispatcherOrOwner
from apps.inventory.models import StockLevel, StockMovement
from apps.inventory.services import apply_movement
from apps.orders.models import Order
from apps.orders.serializers import StaffOrderSerializer
from apps.orders.services import default_product, transition

from . import services

S = Order.Status
User = get_user_model()


def _orders():
    return Order.objects.select_related("customer", "product", "address", "assigned_rider").prefetch_related("history", "items__product")


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
class StaffOrderListView(APIView):
    """GET ?date=YYYY-MM-DD -> every order for that delivery day, newest first."""

    permission_classes = [IsDispatcherOrOwner]

    @extend_schema(responses=StaffOrderSerializer(many=True))
    def get(self, request):
        day = parse_date(request.query_params.get("date", "")) or timezone.localdate()
        qs = _orders().filter(delivery_date=day).order_by("-created_at")
        return Response(StaffOrderSerializer(qs, many=True).data)


class StaffOrderDetailView(APIView):
    permission_classes = [IsDispatcherOrOwner]

    @extend_schema(responses=StaffOrderSerializer)
    def get(self, request, pk):
        return Response(StaffOrderSerializer(get_object_or_404(_orders(), pk=pk)).data)


# action name from the app -> what happens
ACTIONS = {
    "confirm": S.CONFIRMED,
    "reject": S.REJECTED,
    "prepare": S.PREPARING,
    "ready": S.READY,
    "cancel": S.CANCELLED,
    "replan": S.CONFIRMED,       # failed -> confirmed, allowed once (transition() checks)
}
NEEDS_REASON = {"reject", "cancel"}


class StaffOrderActionView(APIView):
    """POST /orders/<id>/<action>  body: {reason?, rider_id?, empties_collected?}"""

    permission_classes = [IsDispatcherOrOwner]

    @extend_schema(request=OpenApiTypes.OBJECT, responses=StaffOrderSerializer)
    def post(self, request, pk, action):
        order = get_object_or_404(Order, pk=pk)
        reason = (request.data.get("reason") or "").strip()
        user = request.user

        if action in NEEDS_REASON and len(reason) < 3:
            raise ValidationError({"reason": ["Give a reason. The customer will see it."]})

        services.ensure_stock_row(order.product)

        if action in ACTIONS:
            if action == "replan" and order.status != S.FAILED:
                raise ValidationError("Only a failed delivery can be re-planned.")
            transition(order, ACTIONS[action], by=user, reason=reason,
                       note=reason or ("Re-planned for the next trip" if action == "replan" else ""))
        elif action == "dispatch":
            services.send_out(order, user, rider_id=request.data.get("rider_id"))
        elif action == "deliver":
            services.mark_delivered(order, user, request.data.get("empties_collected"))
        elif action == "fail":
            services.mark_failed(order, user, reason)
        else:
            raise ValidationError(f"Unknown action '{action}'.")

        return Response(StaffOrderSerializer(_orders().get(pk=pk)).data)


class RiderListView(APIView):
    """Active riders, for the "who is bringing it?" picker."""

    permission_classes = [IsDispatcherOrOwner]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        riders = User.objects.filter(role="rider", is_active=True).order_by("first_name", "username")
        today = timezone.localdate()
        on_road = dict(
            Order.objects.filter(status=S.OUT_FOR_DELIVERY, delivery_date=today, assigned_rider__isnull=False)
            .values_list("assigned_rider").annotate(n=Count("id"))
        )
        from apps.delivery.tracking import last_location
        return Response([
            {"id": r.id, "name": r.get_full_name() or r.username, "phone": r.phone,
             "on_road": on_road.get(r.id, 0), "location": last_location(r)}
            for r in riders
        ])


# ---------------------------------------------------------------------------
# Stock
# ---------------------------------------------------------------------------
LOG_LABEL = {
    "refill": "refill", "adjust": "correction", "reserve": "reserve", "release": "release",
    "load_out": "load_out", "return_unsold": "return_unsold", "empties_in": "empties_in",
}


def stock_payload():
    product = default_product()
    if product is None:
        return {"filled_ready": 0, "reserved": 0, "available": 0, "empty_at_station": 0,
                "owned_total": 0, "on_road": 0, "with_customers": 0, "log": []}
    stock, _ = StockLevel.objects.get_or_create(product=product)
    on_road = Order.objects.filter(status=S.OUT_FOR_DELIVERY).aggregate(n=Sum("containers"))["n"] or 0
    with_customers = CustomerProfile.objects.aggregate(n=Sum("containers_held"))["n"] or 0
    filled_ready = stock.filled_available + stock.filled_reserved
    log = []
    for m in StockMovement.objects.filter(product=product).select_related("by_user", "order")[:40]:
        by = (m.by_user.get_full_name() or m.by_user.username) if m.by_user else "System"
        filled_change = m.d_available + m.d_reserved
        delta = filled_change if filled_change else m.d_empty
        kind = LOG_LABEL.get(m.reason, m.reason)
        if m.reason == "adjust" and not filled_change and m.d_empty:
            kind = "receive"
        log.append({
            "at": m.created_at.isoformat(),
            "type": kind,
            "delta": delta,
            "reason": m.note or (f"Order AF-{m.order_id}" if m.order_id else ""),
            "by": by,
        })
    return {
        "filled_ready": filled_ready,
        "reserved": stock.filled_reserved,
        "available": stock.filled_available,
        "empty_at_station": stock.empty_count,
        "on_road": on_road,
        "with_customers": with_customers,
        "owned_total": filled_ready + stock.empty_count + on_road + with_customers,
        "log": log,
        "product": {"id": product.id, "name": product.name},
        "others": other_products(product),
    }


def other_products(main):
    """Stock of everything else the station sells (new containers, small bottles, ice...)."""
    from apps.inventory.models import Product
    rows = []
    for p in Product.objects.exclude(pk=main.pk).order_by("sort_order", "id"):
        st, _ = StockLevel.objects.get_or_create(product=p)
        rows.append({"id": p.id, "name": p.name, "kind": p.kind, "is_active": p.is_active,
                     "available": st.filled_available, "reserved": st.filled_reserved})
    return rows


class StockView(APIView):
    permission_classes = [IsDispatcherOrOwner]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(stock_payload())


class StockAdjustView(APIView):
    """
    refill:     `quantity` empties were washed and filled (empties go down, ready goes up)
    correction: physical count; `quantity` = real number of filled containers on hand
    receive:    `quantity` NEW empty containers bought by the station (empties go up)
    """

    permission_classes = [IsDispatcherOrOwner]

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        from apps.inventory.models import Product
        product = default_product()
        if product is None:
            raise ValidationError("No product is set up yet. Add one on the Products screen first.")
        # Other products (send product_id): "add" new stock, or "correction" after a count
        pid = request.data.get("product_id")
        if pid and str(pid) != str(product.pk):
            return self._other(request, get_object_or_404(Product, pk=pid))
        stock, _ = StockLevel.objects.get_or_create(product=product)
        kind = request.data.get("type")
        reason = (request.data.get("reason") or "").strip()
        try:
            qty = int(request.data.get("quantity"))
        except (TypeError, ValueError):
            raise ValidationError({"quantity": ["Enter a whole number."]})
        if qty < 0:
            raise ValidationError({"quantity": ["Enter a whole number."]})

        if kind == "refill":
            if qty < 1:
                raise ValidationError({"quantity": ["Enter how many containers you filled."]})
            if qty > stock.empty_count:
                raise ValidationError({"quantity": [f"Only {stock.empty_count} empty containers are at the station."]})
            apply_movement(product, "refill", request.user, available=qty, empty=-qty, note=reason or "Refill batch")
        elif kind == "correction":
            if len(reason) < 3:
                raise ValidationError({"reason": ["Say why the count changed."]})
            if qty < stock.filled_reserved:
                raise ValidationError({"quantity": [
                    f"{stock.filled_reserved} containers are already promised to confirmed orders. "
                    "Count again, or cancel some orders first."]})
            delta = qty - (stock.filled_available + stock.filled_reserved)
            apply_movement(product, "adjust", request.user, available=delta, note=reason)
        elif kind == "receive":
            if qty < 1:
                raise ValidationError({"quantity": ["Enter how many new containers arrived."]})
            apply_movement(product, "adjust", request.user, empty=qty, note=reason or "New containers received")
        else:
            raise ValidationError({"type": ["Use refill, correction or receive."]})
        return Response(stock_payload())

    def _other(self, request, product):
        stock, _ = StockLevel.objects.get_or_create(product=product)
        kind = request.data.get("type")
        reason = (request.data.get("reason") or "").strip()
        try:
            qty = int(request.data.get("quantity"))
        except (TypeError, ValueError):
            raise ValidationError({"quantity": ["Enter a whole number."]})
        if kind == "add":
            if qty < 1:
                raise ValidationError({"quantity": [f"Enter how many {product.name} arrived."]})
            apply_movement(product, "adjust", request.user, available=qty, note=reason or "Stock added")
        elif kind == "correction":
            if qty < stock.filled_reserved:
                raise ValidationError({"quantity": [f"{stock.filled_reserved} are already promised to orders."]})
            if len(reason) < 3:
                raise ValidationError({"reason": ["Say why the count changed."]})
            apply_movement(product, "adjust", request.user,
                           available=qty - (stock.filled_available + stock.filled_reserved), note=reason)
        else:
            raise ValidationError({"type": ["Use add or correction."]})
        return Response(stock_payload())


# ---------------------------------------------------------------------------
# Owner / dashboard numbers
# ---------------------------------------------------------------------------
class SummaryView(APIView):
    """
    GET ?days=14 -> real numbers for dashboards:
    per-day orders/revenue/containers, status counts for today, top barangays,
    period split, customer count, stock.
    """

    permission_classes = [IsDispatcherOrOwner]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        try:
            days = max(1, min(int(request.query_params.get("days", 14)), 90))
        except ValueError:
            days = 14
        today = timezone.localdate()
        start = today - timedelta(days=days - 1)
        window = Order.objects.filter(delivery_date__gte=start, delivery_date__lte=today)

        per_day = {start + timedelta(days=i): {"orders": 0, "delivered": 0, "containers": 0, "revenue": 0.0}
                   for i in range(days)}
        for o in window.only("delivery_date", "status", "containers", "total"):
            d = per_day[o.delivery_date]
            d["orders"] += 1
            if o.status == S.DELIVERED:
                d["delivered"] += 1
                d["containers"] += o.containers
                d["revenue"] += float(o.total)

        today_qs = Order.objects.filter(delivery_date=today)
        status_today = {row["status"]: row["n"] for row in today_qs.values("status").annotate(n=Count("id"))}

        barangays = (
            window.exclude(status__in=[S.REJECTED, S.CANCELLED])
            .values("address__barangay").annotate(n=Count("id"), containers=Sum("containers"))
            .order_by("-n")[:6]
        )
        periods = {row["period"]: row["n"] for row in window.values("period").annotate(n=Count("id"))}
        delivered_all = window.filter(status=S.DELIVERED)
        failed_all = window.filter(status=S.FAILED).count()

        return Response({
            "days": [
                {"date": d.isoformat(), **v} for d, v in sorted(per_day.items())
            ],
            "status_today": status_today,
            "top_barangays": [
                {"name": b["address__barangay"] or "Unknown", "orders": b["n"], "containers": b["containers"] or 0}
                for b in barangays
            ],
            "periods": {"morning": periods.get("morning", 0), "afternoon": periods.get("afternoon", 0)},
            "totals": {
                "orders": window.count(),
                "delivered": delivered_all.count(),
                "failed": failed_all,
                "cancelled": window.filter(status__in=[S.CANCELLED, S.REJECTED]).count(),
                "revenue": float(delivered_all.aggregate(n=Sum("total"))["n"] or 0),
                "containers": delivered_all.aggregate(n=Sum("containers"))["n"] or 0,
            },
            "customers": User.objects.filter(role="customer", is_active=True).count(),
            "new_customers": User.objects.filter(role="customer", date_joined__date__gte=start).count(),
            "riders": User.objects.filter(role="rider", is_active=True).count(),
            "stock": {k: v for k, v in stock_payload().items() if k != "log"},
        })
