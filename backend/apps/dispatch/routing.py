"""
Road distances, travel times and route lines from OpenRouteService (heiGIT).

Two ORS calls are used:
  matrix      every point to every point (distance + duration), to choose the stop order.
              Pairs are saved in DistanceCache, so a trip that's edited again costs no new call.
  directions  the actual road path station -> stops -> station, with each leg's distance and
              duration. Used for the trip's numbers, arrival times and the line on the maps.

Set ORS_API_KEY in backend/.env. Without a key, or if ORS is down, slow or refuses a point,
everything falls back to straight-line x ROAD_FACTOR at tricycle speed and the trip is
labelled an estimate (distance_is_estimate = True), exactly as before. Planning never fails
because of ORS.

Points are (lat, lng) everywhere in AquaFlow; ORS wants [lng, lat]. Only this file converts.
"""
import json
import logging
import urllib.error
import urllib.request
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings

from apps.delivery.tracking import ROAD_FACTOR, TRICYCLE_KMH
from apps.station.geo import haversine_m

from .models import DistanceCache

log = logging.getLogger(__name__)

BASE_URL = "https://api.openrouteservice.org/v2"
SPEED_MPS = TRICYCLE_KMH * 1000 / 3600
SNAP_RADIUS_M = 1000           # how far a pin may be from a road and still be routed
MAX_MATRIX_POINTS = 50         # keep each matrix request well inside the free-plan limits


def enabled():
    return bool(getattr(settings, "ORS_API_KEY", ""))


def _profile():
    return getattr(settings, "ORS_PROFILE", "driving-car")


def _post(path, body):
    """POST to ORS and return the JSON answer, or None on any problem (logged, never raised)."""
    req = urllib.request.Request(
        f"{BASE_URL}/{path}",
        data=json.dumps(body).encode(),
        method="POST",
        headers={
            "Authorization": settings.ORS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json, application/geo+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=getattr(settings, "ORS_TIMEOUT_S", 8)) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read()[:300].decode(errors="replace")
        log.warning("OpenRouteService %s answered %s: %s", path, e.code, detail)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
        log.warning("OpenRouteService %s failed: %s", path, e)
    return None


def _lnglat(points):
    return [[float(lng), float(lat)] for lat, lng in points]


# ---------------------------------------------------------------------------
# Fallback (no key / ORS down)
# ---------------------------------------------------------------------------
def straight_m(a, b):
    return haversine_m(a[0], a[1], b[0], b[1]) * ROAD_FACTOR


def straight_leg(a, b):
    d = straight_m(a, b)
    return d, d / SPEED_MPS


# ---------------------------------------------------------------------------
# Matrix (for choosing the stop order), cached per pair
# ---------------------------------------------------------------------------
Q = Decimal("0.00001")


def _key(p):
    return (Decimal(str(p[0])).quantize(Q, ROUND_HALF_UP), Decimal(str(p[1])).quantize(Q, ROUND_HALF_UP))


class Matrix:
    """distance(i, j) / duration(i, j) between points[i] and points[j]. `is_estimate` if any pair fell back."""

    def __init__(self, points, dist, dur, is_estimate):
        self.points, self._dist, self._dur, self.is_estimate = points, dist, dur, is_estimate

    def distance(self, i, j):
        return self._dist[i][j]

    def duration(self, i, j):
        return self._dur[i][j]


def matrix(points):
    """Road distance and time between every pair of points. One ORS call at most, then cached."""
    points = [(float(a), float(b)) for a, b in points]
    n = len(points)
    keys = [_key(p) for p in points]
    dist = [[0.0] * n for _ in range(n)]
    dur = [[0.0] * n for _ in range(n)]
    if n < 2:
        return Matrix(points, dist, dur, False)

    pairs = {(i, j) for i in range(n) for j in range(n) if i != j and keys[i] != keys[j]}

    if enabled() and n <= MAX_MATRIX_POINTS:
        cached = {
            ((r.from_lat, r.from_lng), (r.to_lat, r.to_lng)): r
            for r in DistanceCache.objects.filter(
                source=DistanceCache.Source.ORS,
                from_lat__in={k[0] for k in keys}, to_lat__in={k[0] for k in keys})
        }
        missing = [(i, j) for i, j in pairs if (keys[i], keys[j]) not in cached]
        if missing:
            answer = _post(f"matrix/{_profile()}", {
                "locations": _lnglat(points), "metrics": ["distance", "duration"], "units": "m"})
            if answer and answer.get("distances") and answer.get("durations"):
                rows = []
                for i, j in pairs:
                    d, t = answer["distances"][i][j], answer["durations"][i][j]
                    if d is None or t is None:      # ORS couldn't route this pair
                        continue
                    rows.append(DistanceCache(
                        from_lat=keys[i][0], from_lng=keys[i][1], to_lat=keys[j][0], to_lng=keys[j][1],
                        distance_m=round(d), duration_s=round(t), source=DistanceCache.Source.ORS))
                DistanceCache.objects.bulk_create(
                    rows, update_conflicts=True,
                    unique_fields=["from_lat", "from_lng", "to_lat", "to_lng"],
                    update_fields=["distance_m", "duration_s", "source", "fetched_at"])
                cached.update({((r.from_lat, r.from_lng), (r.to_lat, r.to_lng)): r for r in rows})

        estimate = False
        for i, j in pairs:
            row = cached.get((keys[i], keys[j]))
            if row is not None:
                dist[i][j], dur[i][j] = row.distance_m, row.duration_s
            else:
                dist[i][j], dur[i][j] = straight_leg(points[i], points[j])
                estimate = True
        return Matrix(points, dist, dur, estimate)

    for i, j in pairs:
        dist[i][j], dur[i][j] = straight_leg(points[i], points[j])
    return Matrix(points, dist, dur, True)


# ---------------------------------------------------------------------------
# Directions (the real path + per-leg numbers)
# ---------------------------------------------------------------------------
def directions(points):
    """
    Road route through `points` in order (station, stops..., station).
    Returns {"line": [[lat, lng], ...], "legs": [(meters, seconds), ...]} or None to fall back.
    """
    points = [(float(a), float(b)) for a, b in points]
    if not enabled() or len(points) < 2:
        return None
    answer = _post(f"directions/{_profile()}/geojson", {
        "coordinates": _lnglat(points),
        "radiuses": [SNAP_RADIUS_M] * len(points),
        "instructions": False,
    })
    try:
        feature = answer["features"][0]
        line = [[round(lat, 6), round(lng, 6)] for lng, lat, *_ in feature["geometry"]["coordinates"]]
        segments = feature["properties"]["segments"]
    except (TypeError, KeyError, IndexError, ValueError):
        return None
    if len(segments) != len(points) - 1:
        return None
    return {"line": line, "legs": [(s.get("distance", 0), s.get("duration", 0)) for s in segments]}
