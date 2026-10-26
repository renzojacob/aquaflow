from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.services import MAX_QUANTITY, PERIOD_START, default_product

from .models import ServiceArea, Station

# Used only if no Station / ServiceArea has been entered in admin yet
DEFAULT_CENTER = (13.4117, 121.1803)  # Calapan City
DEFAULT_RADIUS_M = 5000


def _pick(obj, *names):
    """First non-empty attribute from a list of possible field names."""
    if obj is None:
        return None
    for name in names:
        value = getattr(obj, name, None)
        if value not in (None, ""):
            return value
    return None


class PublicSettingsView(APIView):
    """What the app needs before ordering: price, limits, cut-off times, service area."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        station = Station.objects.first()
        area = ServiceArea.objects.first()
        product = default_product()

        lat = _pick(area, "center_lat", "lat", "latitude") or _pick(station, "lat", "latitude") or DEFAULT_CENTER[0]
        lng = _pick(area, "center_lng", "lng", "longitude") or _pick(station, "lng", "longitude") or DEFAULT_CENTER[1]
        radius_m = _pick(area, "radius_m") or DEFAULT_RADIUS_M

        return Response({
            "product_id": product.id if product else None,
            "price_per_container": float(product.price) if product else 0,
            "max_containers_per_order": MAX_QUANTITY,
            "cutoff": {p.value: t.strftime("%H:%M") for p, t in PERIOD_START.items()},
            "station": {
                "name": _pick(station, "name") or "AquaFlow Station",
                "address": _pick(station, "address", "address_text") or "",
                "lat": float(lat),
                "lng": float(lng),
            },
            "service_radius_km": float(radius_m) / 1000,
        })