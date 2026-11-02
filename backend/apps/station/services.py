"""The delivery area: what the owner set, and whether an address is inside it."""
from .geo import haversine_m
from .models import ServiceArea, Station

DEFAULT_CENTER = (13.4117, 121.1803)  # Calapan City
DEFAULT_RADIUS_M = 5000


def area_payload():
    station, area = Station.objects.first(), ServiceArea.objects.first()
    lat = float(station.lat) if station else float(area.center_lat) if area else DEFAULT_CENTER[0]
    lng = float(station.lng) if station else float(area.center_lng) if area else DEFAULT_CENTER[1]
    return {
        "name": station.name if station else "AquaFlow Station",
        "lat": lat, "lng": lng,
        "radius_km": (area.radius_m if area else DEFAULT_RADIUS_M) / 1000,
        "barangays": list(area.barangays) if area else [],
        "is_configured": bool(area),
    }


def outside_area_message(lat, lng, barangay=""):
    """None if the address can be served. Otherwise a message for the customer.
    If the owner never set a service area, nothing is blocked."""
    area = ServiceArea.objects.first()
    if area is None:
        return None
    km = haversine_m(lat, lng, area.center_lat, area.center_lng) / 1000
    if km > area.radius_m / 1000:
        return (f"Sorry, this address is {km:.1f} km from our station. "
                f"We deliver within {area.radius_m / 1000:g} km.")
    served = [b.lower() for b in (area.barangays or [])]
    if served:
        if not (barangay or "").strip():
            return "Please choose your barangay on the address so we know if we deliver there."
        if barangay.strip().lower() not in served:
            return f"Sorry, we don't deliver to {barangay.strip()} yet."
    return None
