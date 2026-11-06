"""
Feature C API.

Customer:  GET  /api/customer/refill/            the home card (one entry per household)
           POST /api/customer/refill/reorder/    one-tap reorder of the usual quantity
Staff:     GET  /api/v1/dispatch/demand          expected containers per day (?days=7)
           GET  /api/v1/dispatch/refill-accuracy backtest report (?days=90, 0 = all time)
"""
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsCustomer, IsDispatcherOrOwner
from apps.orders.models import Order
from apps.orders.serializers import CustomerOrderSerializer

from . import services
from .models import RefillPrediction


def _int_param(request, name, default, lo, hi):
    try:
        return max(lo, min(int(request.query_params.get(name, default)), hi))
    except (TypeError, ValueError):
        return default


class CustomerRefillView(APIView):
    """When each of my households is expected to run out, and what one tap would reorder."""

    permission_classes = [IsCustomer]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response({"households": services.customer_cards(request.user),
                         "min_orders": services.MIN_ORDERS,
                         "remind_days_before": services.REMIND_DAYS_BEFORE})


class ReorderSerializer(serializers.Serializer):
    prediction = serializers.IntegerField()
    delivery_date = serializers.DateField(required=False)
    period = serializers.ChoiceField(choices=Order.Period.choices, required=False)


class CustomerReorderView(APIView):
    """Place the usual order for a household from its prediction (or from the reminder link)."""

    permission_classes = [IsCustomer]

    @extend_schema(request=ReorderSerializer, responses={201: CustomerOrderSerializer})
    def post(self, request):
        s = ReorderSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        prediction = get_object_or_404(
            RefillPrediction.objects.select_related("address", "customer__customer_profile"),
            pk=s.validated_data["prediction"], customer=request.user)
        order = services.reorder(request.user, prediction,
                                 delivery_date=s.validated_data.get("delivery_date"),
                                 period=s.validated_data.get("period"))
        order = (Order.objects.select_related("product", "address", "assigned_rider")
                 .prefetch_related("history", "items__product").get(pk=order.pk))
        return Response(CustomerOrderSerializer(order).data, status=status.HTTP_201_CREATED)


class DemandView(APIView):
    """Confirmed orders + predicted reorders (tentative) per day, and what to prepare."""

    permission_classes = [IsDispatcherOrOwner]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(services.demand(days=_int_param(request, "days", 7, 1, 14)))


class RefillAccuracyView(APIView):
    """Backtest of the refill prediction against what households really did."""

    permission_classes = [IsDispatcherOrOwner]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        days = _int_param(request, "days", 90, 0, 3650)
        today = timezone.localdate()
        since = today - timedelta(days=days - 1) if days else None
        report = services.backtest(since=since, until=today)
        report["since"] = since.isoformat() if since else None
        report["until"] = today.isoformat()
        return Response(report)
