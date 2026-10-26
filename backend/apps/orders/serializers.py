from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.customers.models import Address
from apps.inventory.models import Product

from .models import Order, OrderStatusHistory
from .services import MAX_QUANTITY


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ["from_status", "to_status", "server_time", "note"]


class CustomerOrderSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    address_label = serializers.CharField(source="address.label", read_only=True)
    address_street = serializers.CharField(source="address.street", read_only=True)
    address_barangay = serializers.CharField(source="address.barangay", read_only=True)
    total = serializers.SerializerMethodField()
    history = OrderStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "status",
            "product", "product_name", "quantity", "unit_price", "total",
            "expected_empties", "notes",
            "delivery_date", "period",
            "address", "address_label", "address_street", "address_barangay",
            "address_text", "landmark", "lat", "lng",
            "confirmation_code",
            "rejection_reason", "cancel_reason",
            "source", "created_at", "updated_at",
            "history",
        ]
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.DECIMAL)
    def get_total(self, order):
        return str(order.unit_price * order.quantity)


class OrderCreateSerializer(serializers.Serializer):
    address = serializers.PrimaryKeyRelatedField(queryset=Address.objects.none())
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), required=False)
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_QUANTITY)
    delivery_date = serializers.DateField()
    period = serializers.ChoiceField(choices=Order.Period.choices)
    expected_empties = serializers.IntegerField(min_value=0, max_value=MAX_QUANTITY, required=False)
    notes = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            fields["address"].queryset = Address.objects.filter(
                customer=request.user, is_archived=False
            )
        return fields


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)