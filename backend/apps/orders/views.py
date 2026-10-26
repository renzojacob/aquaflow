from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsCustomer

from . import services
from .models import Order
from .serializers import CancelSerializer, CustomerOrderSerializer, OrderCreateSerializer


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
            .select_related("product", "address")
            .prefetch_related("history")
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