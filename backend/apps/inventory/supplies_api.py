"""
Supplies API (caps, seals, filters...).  Prefix: /api/v1/dispatch/

  GET    supplies                 everything + alerts + the recent log   (dispatcher and owner)
  POST   supplies                 add a supply                           (owner)
  PATCH  supplies/<id>            change one                             (owner)
  DELETE supplies/<id>            only if it was never used              (owner)
  POST   supplies/<id>/adjust     {type: received|used|correction, quantity, note}

Every answer is the whole payload, so the screen never has to guess what changed.
"""
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status as http
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasRole

from . import supplies as svc
from .models import Supply, SupplyMovement


class OwnerWritesStaffReads(HasRole):
    """Dispatchers can look; only the owner can change the list."""
    allowed_roles = ("dispatcher", "owner")
    message = "Only the owner can change supplies."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.method in SAFE_METHODS or request.user.role == "owner"


def _quantity(data, label="Quantity"):
    try:
        value = Decimal(str(data.get("quantity")))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({"quantity": [f"Enter a number for {label.lower()}."]})
    if value < 0 or value > Decimal("1000000"):
        raise ValidationError({"quantity": [f"{label} must be 0 or more."]})
    return value


class SupplyListCreateView(APIView):
    permission_classes = [OwnerWritesStaffReads]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(svc.supplies_payload())

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        fields = svc.clean_supply(request.data)
        starting = _quantity(request.data, "Starting amount") if request.data.get("quantity") not in (None, "") else Decimal("0")
        supply = Supply.objects.create(**fields)
        if starting > 0:
            svc.apply_supply_movement(supply, starting, SupplyMovement.Reason.RECEIVED,
                                      by=request.user, note="Starting amount")
        return Response(svc.supplies_payload(), status=http.HTTP_201_CREATED)


class SupplyDetailView(APIView):
    permission_classes = [OwnerWritesStaffReads]

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def patch(self, request, pk):
        supply = get_object_or_404(Supply, pk=pk)
        for key, value in svc.clean_supply(request.data, supply).items():
            setattr(supply, key, value)
        supply.save()
        return Response(svc.supplies_payload())

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def delete(self, request, pk):
        supply = get_object_or_404(Supply, pk=pk)
        if supply.movements.exists():
            raise ValidationError("This supply has a history. Switch it off instead of deleting it.")
        supply.delete()
        return Response(svc.supplies_payload())


class SupplyAdjustView(APIView):
    """
    received:   a delivery arrived, add this much
    used:       used up by hand (what the refill batches don't already count)
    correction: a physical count; `quantity` is what is really on the shelf
    """
    permission_classes = [OwnerWritesStaffReads]

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def post(self, request, pk):
        supply = get_object_or_404(Supply, pk=pk)
        kind = request.data.get("type")
        note = str(request.data.get("note") or "").strip()
        qty = _quantity(request.data)

        if kind == "received":
            if qty <= 0:
                raise ValidationError({"quantity": ["Enter how much arrived."]})
            svc.apply_supply_movement(supply, qty, SupplyMovement.Reason.RECEIVED,
                                      by=request.user, note=note or "Delivery received")
        elif kind == "used":
            if qty <= 0:
                raise ValidationError({"quantity": ["Enter how much was used."]})
            svc.apply_supply_movement(supply, -qty, SupplyMovement.Reason.USED,
                                      by=request.user, note=note or "Used")
        elif kind == "correction":
            if len(note) < 3:
                raise ValidationError({"note": ["Say why the count changed."]})
            svc.apply_supply_movement(supply, qty - supply.quantity, SupplyMovement.Reason.CORRECTION,
                                      by=request.user, note=note)
        else:
            raise ValidationError({"type": ["Use received, used or correction."]})
        return Response(svc.supplies_payload())
