from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsCustomer

from . import services
from .models import Order
from .serializers import (
    CancelSerializer, CustomerOrderDetailSerializer,
    CustomerOrderSerializer, OrderCreateSerializer,
)


class CustomerOrderViewSet(mixins.ListModelMixin,
                           mixins.RetrieveModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):
    permission_classes = [IsCustomer]

    def get_queryset(self):
        qs = Order.objects.filter(customer=self.request.user).select_related("product")
        scope = self.request.query_params.get("scope")
        if scope == "active":
            qs = qs.filter(status__in=services.ACTIVE_STATUSES)
        elif scope == "past":
            qs = qs.exclude(status__in=services.ACTIVE_STATUSES)
        if self.action == "retrieve":
            qs = qs.prefetch_related("history")
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        if self.action == "retrieve":
            return CustomerOrderDetailSerializer
        return CustomerOrderSerializer

    @extend_schema(parameters=[
        OpenApiParameter("scope", str, enum=["active", "past"], required=False,
                         description="active = in progress, past = finished. Omit for all."),
    ])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(request=OrderCreateSerializer, responses={201: CustomerOrderDetailSerializer})
    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        order = services.place_order(request.user, **serializer.validated_data)
        return Response(CustomerOrderDetailSerializer(order).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=CancelSerializer, responses=CustomerOrderDetailSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = services.customer_cancel(
            self.get_object(), request.user, serializer.validated_data.get("reason", "")
        )
        return Response(CustomerOrderDetailSerializer(order).data)