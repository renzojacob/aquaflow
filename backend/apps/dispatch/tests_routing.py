"""
OpenRouteService integration, with a fake ORS (no network, no real key needed).
Run:  python manage.py test apps.dispatch.tests_routing
"""
import io
import json
from unittest import mock

from django.test import override_settings

from apps.dispatch import planner, routing
from apps.dispatch.models import DistanceCache, Trip, Vehicle
from apps.dispatch.tests_trips import API, TripBase

STATION = (13.4117, 121.1803)


class FakeORS:
    """Stands in for routing._post. Records calls; answers like ORS does."""

    def __init__(self, matrix_m=None, fail=False):
        self.calls, self.matrix_m, self.fail = [], matrix_m, fail

    def __call__(self, path, body):
        self.calls.append((path, body))
        if self.fail:
            return None
        if path.startswith("matrix/"):
            n = len(body["locations"])
            dist = self.matrix_m or [[0 if i == j else 1000 * abs(i - j) for j in range(n)] for i in range(n)]
            return {"distances": dist, "durations": [[d / 10 for d in row] for row in dist]}
        coords = body["coordinates"]                      # [lng, lat]
        legs = len(coords) - 1
        return {"features": [{
            "geometry": {"coordinates": coords},          # the "road" = the points themselves
            "properties": {"segments": [{"distance": 2000.0, "duration": 60.0} for _ in range(legs)]},
        }]}

    def count(self, kind):
        return sum(1 for p, _ in self.calls if p.startswith(kind))


@override_settings(ORS_API_KEY="test-key")
class RoutingTests(TripBase):
    def setUp(self):
        super().setUp()
        self.v = Vehicle.objects.create(name="Tricycle 1", plate="T1", capacity_containers=20)

    def test_request_uses_key_profile_and_lng_lat(self):
        sent = {}

        def fake_urlopen(req, timeout):
            sent.update(url=req.full_url, auth=req.get_header("Authorization"), body=json.loads(req.data))
            return io.BytesIO(json.dumps({"distances": [[0, 5], [5, 0]], "durations": [[0, 1], [1, 0]]}).encode())

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            m = routing.matrix([(13.41, 121.18), (13.42, 121.19)])
        self.assertEqual(sent["url"], "https://api.openrouteservice.org/v2/matrix/driving-car")
        self.assertEqual(sent["auth"], "test-key")
        self.assertEqual(sent["body"]["locations"], [[121.18, 13.41], [121.19, 13.42]])   # lng first
        self.assertEqual((m.distance(0, 1), m.is_estimate), (5, False))

    def test_road_distances_decide_the_stop_order(self):
        # B is closer in a straight line, but by road (river in between) A is closer
        a = self.order(2, lat=13.4200, lng=121.1803)
        b = self.order(2, lat=13.4140, lng=121.1803)
        road = [[0, 500, 4000], [500, 0, 4500], [4000, 4500, 0]]    # 0 station, 1 = a, 2 = b
        with mock.patch.object(routing, "_post", FakeORS(matrix_m=road)):
            self.assertEqual(planner.best_sequence([a, b], STATION), [a, b])
        with override_settings(ORS_API_KEY=""):                     # straight line picks b first
            self.assertEqual(planner.best_sequence([a, b], STATION), [b, a])

    def test_trip_gets_road_numbers_line_and_tricycle_times(self):
        o1, o2 = self.order(2, lat=13.42), self.order(2, lat=13.43)
        fake = FakeORS()
        with mock.patch.object(routing, "_post", fake):
            r = self.as_(self.dispatcher).post(f"{API}/trips", {
                "date": self.day.isoformat(), "period": "morning",
                "vehicle_id": self.v.pk, "order_ids": [o1.pk, o2.pk]}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertFalse(r.data["distance_is_estimate"])
        self.assertEqual(r.data["total_distance_m"], 6000)                  # 3 legs x 2000 m
        self.assertEqual(len(r.data["route_line"]), 4)                       # station, 2 stops, station
        self.assertEqual(r.data["route_line"][1], [13.42, 121.18])           # back to [lat, lng]
        # ORS says 60 s per 2 km (car); a tricycle at 18 km/h needs 400 s, so 400 s is used
        t = Trip.objects.get(pk=r.data["id"])
        self.assertEqual(t.total_duration_s, 3 * 400 + 2 * 4 * 60)
        self.assertEqual(fake.count("directions/driving-car/geojson"), 1)

    def test_matrix_pairs_are_cached(self):
        pts = [STATION, (13.42, 121.18), (13.43, 121.19)]
        fake = FakeORS()
        with mock.patch.object(routing, "_post", fake):
            routing.matrix(pts)
            m = routing.matrix(pts)
        self.assertEqual(fake.count("matrix"), 1)
        self.assertEqual(DistanceCache.objects.count(), 6)
        self.assertFalse(m.is_estimate)

    def test_ors_down_falls_back_to_estimate(self):
        o1 = self.order(2, lat=13.42)
        with mock.patch.object(routing, "_post", FakeORS(fail=True)):
            r = self.as_(self.dispatcher).post(f"{API}/trips", {
                "date": self.day.isoformat(), "period": "morning",
                "vehicle_id": self.v.pk, "order_ids": [o1.pk]}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(r.data["distance_is_estimate"])
        self.assertIsNone(r.data["route_line"])
        self.assertGreater(r.data["total_distance_m"], 0)

    @override_settings(ORS_API_KEY="")
    def test_no_key_makes_no_calls(self):
        o1 = self.order(2, lat=13.42)
        fake = FakeORS()
        with mock.patch.object(routing, "_post", fake):
            planner.plan_slot(self.day, "morning", self.dispatcher)
        self.assertEqual(fake.calls, [])
        self.assertTrue(Trip.objects.get().distance_is_estimate)

    def test_rider_download_and_today_carry_the_line(self):
        o1 = self.order(2, lat=13.42)
        with mock.patch.object(routing, "_post", FakeORS()):
            tid = self.as_(self.dispatcher).post(f"{API}/trips", {
                "date": self.day.isoformat(), "period": "morning", "vehicle_id": self.v.pk,
                "order_ids": [o1.pk], "rider_id": self.rider.pk}, format="json").data["id"]
        self.client.post(f"{API}/trips/{tid}/approve")
        rc = self.as_(self.rider)
        self.assertEqual(len(rc.post(f"/api/v1/rider/trips/{tid}/download").data["route_line"]), 3)
        rc.post(f"/api/v1/rider/trips/{tid}/start", {}, format="json")
        self.assertEqual(len(rc.get("/api/v1/rider/today").data["route_line"]), 3)
