"""
Owner: manage people. This is how dispatcher and rider accounts are made
(the public sign-up page only ever creates customers).
URL prefix: /api/v1/owner/
"""
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CustomerProfile, RiderProfile, User
from .permissions import IsOwner

STAFF_ROLES = ("dispatcher", "rider", "owner")


def user_row(u, stats=None):
    s = stats or {}
    return {
        "id": u.id,
        "full_name": u.get_full_name() or u.username,
        "email": u.email,
        "phone": u.phone,
        "role": u.role,
        "is_active": u.is_active,
        "date_joined": u.date_joined.isoformat(),
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "orders": s.get("orders", 0),
        "delivered": s.get("delivered", 0),
    }


class StaffCreateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, allow_blank=True, required=False)
    role = serializers.ChoiceField(choices=STAFF_ROLES)
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(Q(email__iexact=value) | Q(username__iexact=value)).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        candidate = User(username=attrs["email"], email=attrs["email"], first_name=attrs["full_name"])
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return attrs


class UserListView(APIView):
    """GET ?role=rider -> people. POST -> create a dispatcher / rider / owner account."""

    permission_classes = [IsOwner]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        qs = User.objects.all().order_by("role", "first_name", "username")
        role = request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        qs = qs.annotate(
            n_orders=Count("orders", distinct=True),
            n_delivered=Count("orders", filter=Q(orders__status="delivered"), distinct=True),
            n_rides=Count("assigned_orders", filter=Q(assigned_orders__status="delivered"), distinct=True),
        )
        rows = []
        for u in qs:
            rows.append(user_row(u, {
                "orders": u.n_orders,
                "delivered": u.n_rides if u.role == "rider" else u.n_delivered,
            }))
        return Response(rows)

    @extend_schema(request=StaffCreateSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        ser = StaffCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        first, _, last = " ".join(d["full_name"].split()).partition(" ")
        user = User(username=d["email"], email=d["email"], phone=d.get("phone", ""),
                    first_name=first, last_name=last, role=d["role"])
        user.set_password(d["password"])
        user.save()
        if user.role == "rider":
            RiderProfile.objects.get_or_create(user=user)
        return Response(user_row(user), status=201)


class UserDetailView(APIView):
    """PATCH {is_active} -> turn an account on/off. Owners can't switch themselves off."""

    permission_classes = [IsOwner]

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def patch(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if "is_active" in request.data:
            if user.pk == request.user.pk:
                raise serializers.ValidationError({"is_active": ["You can't deactivate your own account."]})
            user.is_active = bool(request.data["is_active"])
            user.save(update_fields=["is_active"])
        return Response(user_row(user))


# ---------------------------------------------------------------------------
# Products & prices (what customers can put in their cart)
# ---------------------------------------------------------------------------
from django.db.models import Sum as _Sum

from apps.inventory.models import Product, StockLevel
from apps.orders.models import OrderItem


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "kind", "price", "description", "max_per_order", "sort_order", "is_active"]

    def validate_name(self, value):
        value = " ".join(value.split())
        if len(value) < 3:
            raise serializers.ValidationError("Give the product a name customers understand.")
        return value

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("The price must be more than zero.")
        return value

    def validate_max_per_order(self, value):
        if not 1 <= value <= 20:
            raise serializers.ValidationError("Between 1 and 20 per order.")
        return value


def product_row(p, sold=None):
    st = StockLevel.objects.filter(product=p).first()
    data = ProductSerializer(p).data
    data["price"] = float(p.price)
    data["available"] = st.filled_available if st else 0
    data["reserved"] = st.filled_reserved if st else 0
    data["sold"] = sold if sold is not None else (
        OrderItem.objects.filter(product=p, order__status="delivered").aggregate(n=_Sum("quantity"))["n"] or 0
    )
    return data


class ProductListView(APIView):
    permission_classes = [IsOwner]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response([product_row(p) for p in Product.objects.order_by("sort_order", "id")])

    @extend_schema(request=ProductSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        ser = ProductSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        p = ser.save()
        StockLevel.objects.get_or_create(product=p)
        return Response(product_row(p, sold=0), status=201)


class ProductDetailView(APIView):
    permission_classes = [IsOwner]

    @extend_schema(request=ProductSerializer, responses=OpenApiTypes.OBJECT)
    def patch(self, request, pk):
        p = get_object_or_404(Product, pk=pk)
        ser = ProductSerializer(p, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        if ser.validated_data.get("is_active") is False and p.kind == Product.Kind.REFILL:
            others = Product.objects.filter(kind=Product.Kind.REFILL, is_active=True).exclude(pk=p.pk)
            if not others.exists():
                raise serializers.ValidationError({"is_active": ["Keep at least one refill on sale, or customers can't order water."]})
        ser.save()
        return Response(product_row(p))
