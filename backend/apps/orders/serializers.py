from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.customers.models import Address
from apps.inventory.models import Product

from .models import Order, OrderItem, OrderStatusHistory
from .services import MAX_QUANTITY


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ["from_status", "to_status", "server_time", "note"]


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    kind = serializers.CharField(source="product.kind", read_only=True)
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["product", "product_name", "kind", "quantity", "unit_price", "line_total"]


class CustomerOrderSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    address_label = serializers.CharField(source="address.label", read_only=True)
    address_street = serializers.CharField(source="address.street", read_only=True)
    address_barangay = serializers.CharField(source="address.barangay", read_only=True)
    history = OrderStatusHistorySerializer(many=True, read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    rider = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "status",
            "product", "product_name", "quantity", "containers", "unit_price", "total", "items",
            "expected_empties", "notes",
            "delivery_date", "period",
            "address", "address_label", "address_street", "address_barangay",
            "address_text", "landmark", "lat", "lng",
            "confirmation_code",
            "rejection_reason", "cancel_reason",
            "source", "created_at", "updated_at",
            "history", "rider",
        ]
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_rider(self, order):
        """The customer only sees the rider while the order is on the road (or after)."""
        r = order.assigned_rider
        if r is None or order.status not in ("out_for_delivery", "delivered", "failed"):
            return None
        return {"id": r.id, "name": r.get_full_name() or r.username, "phone": r.phone}


class StaffOrderSerializer(CustomerOrderSerializer):
    """Same order, plus who ordered it. For dispatcher and owner screens."""

    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)

    class Meta(CustomerOrderSerializer.Meta):
        fields = CustomerOrderSerializer.Meta.fields + ["customer_name", "customer_phone"]
        read_only_fields = fields

    def get_customer_name(self, order) -> str:
        return order.customer.get_full_name() or order.customer.username

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_rider(self, order):
        r = order.assigned_rider
        return None if r is None else {"id": r.id, "name": r.get_full_name() or r.username, "phone": r.phone}


class CartLineSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_QUANTITY)


class OrderCreateSerializer(serializers.Serializer):
    """Send a cart in `items`. (Older apps may send `quantity` (+ `product`) instead.)"""
    address = serializers.PrimaryKeyRelatedField(queryset=Address.objects.none())
    items = CartLineSerializer(many=True, required=False)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), required=False)
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_QUANTITY, required=False)
    delivery_date = serializers.DateField()
    period = serializers.ChoiceField(choices=Order.Period.choices)
    expected_empties = serializers.IntegerField(min_value=0, max_value=MAX_QUANTITY, required=False)
    notes = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get("items") and not attrs.get("quantity"):
            raise serializers.ValidationError({"items": ["Add at least one item."]})
        return attrs

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