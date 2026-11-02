"""
Vehicles and the service area.
URL prefix: /api/v1/dispatch/

  GET    vehicles?date=&period=     everyone on staff; shows which vehicle already has a trip (trip_id)
  POST   vehicles                   owner: {name, plate, capacity, is_available?}
  PATCH  vehicles/<id>              owner
  DELETE vehicles/<id>              owner (only if it never had a trip: otherwise switch it off)
  GET    service-area               station point, delivery radius, barangays served
  PUT    service-area               owner
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status as http
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasRole, IsDispatcherOrOwner
from apps.station.models import ServiceArea, Station
from apps.station.services import area_payload

from .models import Trip, Vehicle


class OwnerWritesStaffReads(HasRole):
    allowed_roles = ("dispatcher", "owner")

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.method in SAFE_METHODS or request.user.role == "owner"


def _vehicle_row(v, trip_id=None):
    return {"id": v.pk, "name": v.name, "plate": v.plate, "capacity": v.capacity_containers,
            "is_available": v.is_available, "trip_id": trip_id}


def _clean_vehicle(data, instance=None):
    name = str(data.get("name", instance.name if instance else "")).strip()
    plate = str(data.get("plate", instance.plate if instance else "")).strip().upper()
    raw = data.get("capacity", data.get("capacity_containers", instance.capacity_containers if instance else None))
    errors = {}
    if len(name) < 2:
        errors["name"] = ["Give the vehicle a name, like Tricycle 1."]
    if len(plate) < 2:
        errors["plate"] = ["Enter the plate number."]
    try:
        cap = int(raw)
        if not 1 <= cap <= 200:
            raise ValueError
    except (TypeError, ValueError):
        cap = None
        errors["capacity"] = ["Enter how many containers it can carry (1 to 200)."]
    if plate and Vehicle.objects.filter(plate__iexact=plate).exclude(pk=getattr(instance, "pk", None)).exists():
        errors["plate"] = ["Another vehicle already has this plate number."]
    if errors:
        raise ValidationError(errors)
    return name, plate, cap


class VehicleListCreateView(APIView):
    permission_classes = [OwnerWritesStaffReads]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        day = parse_date(request.query_params.get("date", ""))
        period = request.query_params.get("period")
        taken = {}
        if day and period:
            taken = dict(Trip.objects.filter(date=day, period=period).values_list("vehicle_id", "id"))
        return Response([_vehicle_row(v, taken.get(v.pk)) for v in Vehicle.objects.order_by("name", "id")])

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        name, plate, cap = _clean_vehicle(request.data)
        v = Vehicle.objects.create(name=name, plate=plate, capacity_containers=cap,
                                   is_available=bool(request.data.get("is_available", True)))
        return Response(_vehicle_row(v), status=http.HTTP_201_CREATED)


class VehicleDetailView(APIView):
    permission_classes = [OwnerWritesStaffReads]

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def patch(self, request, pk):
        v = get_object_or_404(Vehicle, pk=pk)
        name, plate, cap = _clean_vehicle(request.data, v)
        v.name, v.plate, v.capacity_containers = name, plate, cap
        if "is_available" in request.data:
            v.is_available = bool(request.data["is_available"])
        v.save()
        return Response(_vehicle_row(v))

    @extend_schema(responses=None)
    def delete(self, request, pk):
        v = get_object_or_404(Vehicle, pk=pk)
        if v.trips.exists():
            raise ValidationError("This vehicle has trips on record. Switch it off instead of deleting it.")
        v.delete()
        return Response(status=http.HTTP_204_NO_CONTENT)


class ServiceAreaView(APIView):
    permission_classes = [OwnerWritesStaffReads]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(area_payload())

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def put(self, request):
        d, errors = request.data, {}
        try:
            lat, lng = float(d["lat"]), float(d["lng"])
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            errors["lat"] = ["Click the map to place the station."]
        try:
            radius_m = round(float(d["radius_km"]) * 1000)
            if not 500 <= radius_m <= 50_000:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            errors["radius_km"] = ["Enter a radius from 0.5 to 50 km."]
        names = d.get("barangays") or []
        if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
            errors["barangays"] = ["Send the barangays as a list of names."]
        if errors:
            raise ValidationError(errors)

        station_name = str(d.get("name") or "AquaFlow Station").strip()[:100] or "AquaFlow Station"
        station = Station.objects.first() or Station(name=station_name)
        station.name, station.lat, station.lng = station_name, round(lat, 6), round(lng, 6)
        station.save()
        area = ServiceArea.objects.first() or ServiceArea(name="Delivery area")
        area.center_lat, area.center_lng, area.radius_m = round(lat, 6), round(lng, 6), radius_m
        area.barangays = sorted({n.strip() for n in names if n.strip()})
        area.save()
        return Response(area_payload())
