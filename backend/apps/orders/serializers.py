from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.customers.models import Address
from apps.inventory.models import Product

from .models import Order, OrderStatusHistory
from .services import CUSTOMER_CANCELLABLE, MAX_DAYS_AHEAD, SHOW_CODE_STATUSES


class OrderCreateSerializer(serializers.Serializer):
    address = serializers.PrimaryKeyRelatedField(queryset=Address.objects.none())
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1, max_value=50)
    expected_empties = serializers.IntegerField(min_value=0, max_value=50, default=0)
    delivery_date = serializers.DateField(
        help_text=f"YYYY-MM-DD, today up to {MAX_DAYS_AHEAD} days ahead"
    )
    period = serializers.ChoiceField(choices=Order.Period.choices)
    source = serializers.ChoiceField(
        choices=Order.Source.choices, default=Order.Source.MANUAL
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            # Customers can only pick their own, non-archived addresses.
            self.fields["address"].queryset = Address.objects.filter(
                customer=request.user, is_archived=False
            )


class OrderHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ["from_status", "to_status", "server_time", "note"]


class CustomerOrderSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    total = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    confirmation_code = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "status", "source",
            "product", "product_name", "quantity", "unit_price", "total",
            "expected_empties", "delivery_date", "period",
            "address", "address_text", "landmark", "lat", "lng",
            "rejection_reason", "cancel_reason",
            "confirmation_code", "can_cancel",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_total(self, order):
        return f"{order.unit_price * order.quantity:.2f}"

    @extend_schema_field(serializers.BooleanField())
    def get_can_cancel(self, order):
        return order.status in CUSTOMER_CANCELLABLE

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_confirmation_code(self, order):
        return order.confirmation_code if order.status in SHOW_CODE_STATUSES else None


class CustomerOrderDetailSerializer(CustomerOrderSerializer):
    history = OrderHistorySerializer(many=True, read_only=True)

    class Meta(CustomerOrderSerializer.Meta):
        fields = CustomerOrderSerializer.Meta.fields + ["history"]
        read_only_fields = fields


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)