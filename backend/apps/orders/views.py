from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from datetime import timedelta

from django.utils import timezone

from apps.accounts.permissions import IsCustomer
from apps.customers.models import Address
from apps.station.models import SystemSetting

from . import services, slots
from .models import Order
from .serializers import CancelSerializer, CustomerOrderSerializer, OrderCreateSerializer


@extend_schema(
    parameters=[
        OpenApiParameter("address", int, required=False, description="Saved address id, for 'Delivery nearby'"),
        OpenApiParameter("quantity", int, required=False, description="Containers wanted, for 'fits'"),
    ],
    responses=OpenApiTypes.OBJECT,
)
class SlotAvailabilityView(APIView):
    """
    Feature D. GET /api/customer/slots/?address=&quantity=
    Room left in every period the customer can order for (today and tomorrow),
    and whether a trip is already planned near the address.
    Feature E: best_time = the period that usually works at this address, or null.
    """

    permission_classes = [IsCustomer]

    def get(self, request):
        address = None
        if request.query_params.get("address"):
            address = Address.objects.filter(
                pk=request.query_params["address"], customer=request.user, is_archived=False
            ).first()
        try:
            qty = max(0, min(int(request.query_params.get("quantity", 0)), 60))
        except ValueError:
            qty = 0

        now = timezone.localtime()
        today = now.date()
        out = []
        for day in (today, today + timedelta(days=services.MAX_DAYS_AHEAD)):
            for period in Order.Period.values:
                is_open = day > today or now.time() < services.PERIOD_START[period]
                a = slots.slot_availability(
                    day, period, containers=qty,
                    lat=address.lat if address else None, lng=address.lng if address else None,
                )
                out.append({**a.as_dict(), "open": is_open})
        from apps.delivery.best_time import best_period    # local: delivery imports orders
        return Response({
            "slots": out,
            "nearby_radius_m": SystemSetting.load().nearby_radius_m,
            "best_time": best_period(address.pk) if address else None,   # Feature E
        })


@extend_schema(
    parameters=[
        OpenApiParameter(
            "status", str, required=False,
            description="Comma-separated, e.g. pending,confirmed",
        )
    ]
)
class CustomerOrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsCustomer]

    def get_queryset(self):
        qs = (
            Order.objects.filter(customer=self.request.user)
            .select_related("product", "address", "assigned_rider")
            .prefetch_related("history", "items__product")
        )
        statuses = self.request.query_params.get("status")
        if statuses:
            qs = qs.filter(status__in=[s.strip() for s in statuses.split(",") if s.strip()])
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return CustomerOrderSerializer

    @extend_schema(request=OrderCreateSerializer, responses={201: CustomerOrderSerializer})
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = services.place_order(request.user, **serializer.validated_data)
        order = self.get_queryset().get(pk=order.pk)  # reload with history
        return Response(CustomerOrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=["get"])
    def track(self, request, pk=None):
        """Live tracking: the rider's last position, stops before this one, distance and ETA."""
        from apps.delivery.tracking import track_payload  # local import: delivery imports orders
        return Response(track_payload(self.get_object()))

    @extend_schema(request=CancelSerializer, responses=CustomerOrderSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.cancel_by_customer(
            request.user, self.get_object(), serializer.validated_data.get("reason", "")
        )
        order = self.get_queryset().get(pk=pk)
        return Response(CustomerOrderSerializer(order).data)