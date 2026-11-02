"""
Vehicles, service area, planning and trips, through HTTP.
Run:  python manage.py test apps.dispatch.tests_trips
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import CustomerProfile, User
from apps.customers.models import Address
from apps.dispatch import planner
from apps.dispatch.models import Trip, TripStop, Vehicle
from apps.inventory.models import Product, StockLevel
from apps.orders.models import Order, OrderItem
from apps.orders.services import place_order, transition
from apps.station.models import ServiceArea, Station

API = "/api/v1/dispatch"
PW = "Water2026!x"


class TripBase(APITestCase):
    def setUp(self):
        self.product = Product.objects.create(name="5-gallon refill", price=30)
        StockLevel.objects.create(product=self.product, filled_available=100)
        self.dispatcher = User.objects.create_user("d@t.com", "d@t.com", PW, role="dispatcher")
        self.owner = User.objects.create_user("o@t.com", "o@t.com", PW, role="owner")
        self.rider = User.objects.create_user("r@t.com", "r@t.com", PW, role="rider", first_name="Jomar")
        self.rider2 = User.objects.create_user("r2@t.com", "r2@t.com", PW, role="rider", first_name="Ana")
        self.day = timezone.localdate() + timedelta(days=1)
        Station.objects.create(name="AquaFlow", lat=13.4117, lng=121.1803)
        self.n = 0

    def order(self, containers=2, lat=13.41, lng=121.18, status="confirmed", period="morning", empties=0):
        """Create an order directly in the database (the planner only cares about status, load, place)."""
        self.n += 1
        c = User.objects.create_user(f"c{self.n}@t.com", f"c{self.n}@t.com", PW, role="customer")
        CustomerProfile.objects.create(user=c, containers_held=5)
        a = Address.objects.create(customer=c, label="Home", address_text=f"Street {self.n}", barangay="Camilmil",
                                   lat=lat, lng=lng, is_default=True)
        o = Order.objects.create(customer=c, address=a, product=self.product, quantity=containers,
                                 containers=containers, expected_empties=empties, delivery_date=self.day,
                                 period=period, status=status)
        OrderItem.objects.create(order=o, product=self.product, quantity=containers, unit_price=30)
        if status in ("confirmed", "preparing", "ready"):      # a confirmed order holds its stock
            st = StockLevel.objects.get(product=self.product)
            st.filled_available -= containers
            st.filled_reserved += containers
            st.save()
        return o

    def as_(self, user):
        self.client.force_authenticate(user)
        return self.client


class VehicleAndAreaTests(TripBase):
    def test_owner_manages_vehicles_dispatcher_only_reads(self):
        r = self.as_(self.owner).post(f"{API}/vehicles", {"name": "Tricycle 1", "plate": "abc 123", "capacity": 12}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["plate"], "ABC 123")
        vid = r.data["id"]
        self.assertEqual(self.as_(self.dispatcher).get(f"{API}/vehicles").status_code, 200)
        self.assertEqual(self.as_(self.dispatcher).post(f"{API}/vehicles", {"name": "X1", "plate": "X1", "capacity": 5}, format="json").status_code, 403)
        # duplicate plate and bad capacity give plain messages
        r = self.as_(self.owner).post(f"{API}/vehicles", {"name": "T2", "plate": "ABC 123", "capacity": 0}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client.patch(f"{API}/vehicles/{vid}", {"capacity": 15, "is_available": False}, format="json")
        self.assertEqual((r.data["capacity"], r.data["is_available"]), (15, False))

    def test_vehicle_with_trips_cannot_be_deleted(self):
        v = Vehicle.objects.create(name="T1", plate="P1", capacity_containers=10)
        Trip.objects.create(date=self.day, period="morning", vehicle=v)
        self.assertEqual(self.as_(self.owner).delete(f"{API}/vehicles/{v.pk}").status_code, 400)

    def test_service_area_roundtrip_and_order_blocking(self):
        r = self.as_(self.owner).put(f"{API}/service-area", {
            "lat": 13.4117, "lng": 121.1803, "radius_km": 3, "barangays": ["Camilmil", "Ibaba East"]}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["radius_km"], 3)
        self.assertEqual(ServiceArea.objects.count(), 1)
        self.assertEqual(self.as_(self.dispatcher).put(f"{API}/service-area", {}, format="json").status_code, 403)

        c = User.objects.create_user("cust@t.com", "cust@t.com", PW, role="customer")
        CustomerProfile.objects.create(user=c)
        far = Address.objects.create(customer=c, label="Far", address_text="Far", barangay="Camilmil", lat=13.60, lng=121.18)
        other = Address.objects.create(customer=c, label="O", address_text="O", barangay="Suqui", lat=13.42, lng=121.18)
        ok = Address.objects.create(customer=c, label="OK", address_text="OK", barangay="camilmil", lat=13.41, lng=121.18)
        from django.core.exceptions import ValidationError
        for bad in (far, other):
            with self.assertRaises(ValidationError):
                place_order(c, address=bad, delivery_date=self.day, period="afternoon", quantity=1)
        self.assertIsNotNone(place_order(c, address=ok, delivery_date=self.day, period="afternoon", quantity=1))

    def test_no_area_set_blocks_nothing(self):
        c = User.objects.create_user("cust@t.com", "cust@t.com", PW, role="customer")
        CustomerProfile.objects.create(user=c)
        a = Address.objects.create(customer=c, label="Far", address_text="Far", barangay="Anywhere", lat=14.5, lng=121.0)
        self.assertIsNotNone(place_order(c, address=a, delivery_date=self.day, period="afternoon", quantity=1))


class PlannerTests(TripBase):
    def test_load_profile_counts_empties_coming_back(self):
        a, b = self.order(3, empties=3), self.order(2, empties=0)
        dep, peak, after = planner.load_profile([a, b])
        self.assertEqual((dep, peak, after), (5, 5, [5, 3]))

    def test_nearest_first_and_no_crossing(self):
        far = self.order(1, lat=13.45, lng=121.18)
        near = self.order(1, lat=13.415, lng=121.18)
        mid = self.order(1, lat=13.43, lng=121.18)
        seq = planner.best_sequence([far, near, mid])
        self.assertEqual([o.pk for o in seq], [near.pk, mid.pk, far.pk])

    def test_plan_fills_vehicles_and_flags_leftovers(self):
        Vehicle.objects.create(name="Big", plate="B1", capacity_containers=6)
        Vehicle.objects.create(name="Small", plate="S1", capacity_containers=4)
        os = [self.order(3, lat=13.40 + i * 0.004) for i in range(4)]      # 12 containers, room for 10
        huge = self.order(9)                                              # fits nothing
        r = self.as_(self.dispatcher).post(f"{API}/plan", {"date": self.day.isoformat(), "period": "morning"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        for t in r.data["trips"]:
            self.assertLessEqual(t["load"]["peak"], t["load"]["capacity"])
        planned = sum(len(t["stops"]) for t in r.data["trips"])
        self.assertEqual(planned + len(r.data["not_fitted"]), 5)
        self.assertIn(huge.pk, [o["order_id"] for o in r.data["not_fitted"]])
        self.assertTrue(all(o["reason"] for o in r.data["not_fitted"]))
        # every stop got an ETA and a load number
        stop = TripStop.objects.first()
        self.assertIsNotNone(stop.eta)
        self.assertIsNotNone(stop.expected_load_after)
        self.assertTrue(Trip.objects.first().distance_is_estimate)

    def test_replan_replaces_drafts_but_keeps_approved(self):
        v1 = Vehicle.objects.create(name="A", plate="A1", capacity_containers=10)
        Vehicle.objects.create(name="B", plate="B1", capacity_containers=10)
        o1, o2 = self.order(2), self.order(2, lat=13.43)
        c = self.as_(self.dispatcher)
        t = c.post(f"{API}/trips", {"date": self.day.isoformat(), "period": "morning", "vehicle_id": v1.pk,
                                    "order_ids": [o1.pk], "rider_id": self.rider.pk}, format="json").data
        c.post(f"{API}/trips/{t['id']}/approve")
        r = c.post(f"{API}/plan", {"date": self.day.isoformat(), "period": "morning"}, format="json")
        self.assertEqual(len(r.data["trips"]), 1)                       # only vehicle B is free
        self.assertEqual(r.data["trips"][0]["stops"][0]["order_id"], o2.pk)
        self.assertEqual(Trip.objects.get(pk=t["id"]).status, "approved")
        c.post(f"{API}/plan", {"date": self.day.isoformat(), "period": "morning"}, format="json")
        self.assertEqual(Trip.objects.count(), 2)                       # draft replaced, not doubled

    def test_afternoon_orders_are_not_planned_in_the_morning(self):
        Vehicle.objects.create(name="A", plate="A1", capacity_containers=10)
        self.order(2, period="afternoon")
        self.order(2, status="pending")
        r = self.as_(self.dispatcher).post(f"{API}/plan", {"date": self.day.isoformat(), "period": "morning"}, format="json")
        self.assertEqual((r.data["trips"], r.data["not_fitted"]), ([], []))


class TripApiTests(TripBase):
    def setUp(self):
        super().setUp()
        self.v = Vehicle.objects.create(name="Tricycle 1", plate="T1", capacity_containers=6)
        self.v2 = Vehicle.objects.create(name="Multicab", plate="M1", capacity_containers=20)
        self.o1, self.o2, self.o3 = self.order(3), self.order(3, lat=13.43), self.order(3, lat=13.44)
        self.slot = {"date": self.day.isoformat(), "period": "morning"}

    def make(self, orders, vehicle=None, rider=None):
        body = {**self.slot, "vehicle_id": (vehicle or self.v).pk, "order_ids": [o.pk for o in orders]}
        if rider:
            body["rider_id"] = rider.pk
        return self.as_(self.dispatcher).post(f"{API}/trips", body, format="json")

    def test_create_keeps_order_and_checks_capacity(self):
        r = self.make([self.o2, self.o1])
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual([s["order_id"] for s in r.data["stops"]], [self.o2.pk, self.o1.pk])
        self.assertEqual(r.data["load"], {"departure": 6, "peak": 6, "capacity": 6})
        r = self.make([self.o3], vehicle=self.v)                       # same vehicle, same slot
        self.assertEqual(r.status_code, 400)
        self.assertIn("already has a trip", str(r.data))

    def test_over_capacity_is_refused_with_message(self):
        r = self.make([self.o1, self.o2, self.o3])
        self.assertEqual(r.status_code, 400)
        self.assertIn("holds 6", str(r.data))

    def test_order_cannot_be_on_two_trips_or_be_unconfirmed(self):
        self.make([self.o1])
        r = self.make([self.o1], vehicle=self.v2)
        self.assertEqual(r.status_code, 400)
        pending = self.order(1, status="pending")
        self.assertEqual(self.make([pending], vehicle=self.v2).status_code, 400)

    def test_list_shows_unplanned_orders(self):
        self.make([self.o1])
        r = self.as_(self.dispatcher).get(f"{API}/trips", self.slot)
        self.assertEqual(len(r.data["trips"]), 1)
        self.assertEqual({o["order_id"] for o in r.data["unplanned"]}, {self.o2.pk, self.o3.pk})

    def test_edit_stops_bumps_version_and_logs(self):
        t = self.make([self.o1]).data
        r = self.as_(self.dispatcher).put(f"{API}/trips/{t['id']}/stops", {"order_ids": [self.o2.pk, self.o1.pk]}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["version"], t["version"] + 1)
        actions = {c["action"] for c in r.data["change_log"]}
        self.assertTrue({"moved_in", "planned"} <= actions)
        r = self.client.put(f"{API}/trips/{t['id']}/stops", {"order_ids": [self.o1.pk, self.o2.pk]}, format="json")
        self.assertIn("reordered", {c["action"] for c in r.data["change_log"]})
        r = self.client.put(f"{API}/trips/{t['id']}/stops", {"order_ids": [self.o1.pk, self.o2.pk, self.o3.pk]}, format="json")
        self.assertEqual(r.status_code, 400)                           # 9 containers in a 6 vehicle

    def test_approve_needs_rider_then_rider_can_download_and_start(self):
        t = self.make([self.o1, self.o2]).data
        c = self.as_(self.dispatcher)
        self.assertEqual(c.post(f"{API}/trips/{t['id']}/approve").status_code, 400)       # no rider yet
        r = c.post(f"{API}/trips/{t['id']}/assign", {"rider_id": self.rider.pk}, format="json")
        self.assertEqual(r.data["rider"]["name"], "Jomar")
        self.assertEqual(c.post(f"{API}/trips/{t['id']}/approve").data["status"], "approved")

        rc = self.as_(self.rider)
        self.assertEqual(len(rc.get("/api/v1/rider/trips").data), 1)
        d = rc.post(f"/api/v1/rider/trips/{t['id']}/download")
        self.assertEqual(d.status_code, 200, d.data)
        self.assertEqual(len(d.data["stops"]), 2)
        self.assertNotIn("confirmation_code", str(d.data))
        self.assertEqual(len(d.data["stops"][0]["code_hash"]), 64)
        self.assertEqual(Trip.objects.get(pk=t["id"]).status, "downloaded")

        # dispatcher changes the trip after the download -> phone is out of date
        out = self.as_(self.dispatcher).put(f"{API}/trips/{t['id']}/stops", {"order_ids": [self.o2.pk]}, format="json")
        self.assertTrue(out.data["phone_out_of_date"])

        s = self.as_(self.rider).post(f"/api/v1/rider/trips/{t['id']}/start", {}, format="json")
        self.assertEqual(s.status_code, 200, s.data)
        self.assertEqual(Order.objects.get(pk=self.o2.pk).status, "out_for_delivery")
        # a trip that left cannot be deleted or edited
        self.assertEqual(self.as_(self.dispatcher).delete(f"{API}/trips/{t['id']}").status_code, 400)

    def test_rider_cannot_have_two_trips_in_one_slot(self):
        self.make([self.o1], rider=self.rider)
        r = self.make([self.o2], vehicle=self.v2, rider=self.rider)
        self.assertEqual(r.status_code, 400)
        self.assertIn("already has a trip", str(r.data))

    def test_delete_draft_frees_the_orders(self):
        t = self.make([self.o1]).data
        self.assertEqual(self.as_(self.dispatcher).delete(f"{API}/trips/{t['id']}").status_code, 204)
        r = self.client.get(f"{API}/trips", self.slot)
        self.assertIn(self.o1.pk, [o["order_id"] for o in r.data["unplanned"]])

    def test_cancelling_an_order_removes_its_stop(self):
        t = self.make([self.o1, self.o2]).data
        transition(self.o1, "cancelled", by=self.dispatcher, reason="test")
        r = self.as_(self.dispatcher).get(f"{API}/trips/{t['id']}")
        self.assertEqual([s["order_id"] for s in r.data["stops"]], [self.o2.pk])
        self.assertEqual(r.data["version"], t["version"] + 1)

    def test_customer_and_rider_cannot_use_dispatch_trip_api(self):
        c = User.objects.create_user("cu@t.com", "cu@t.com", PW, role="customer")
        for u in (c, self.rider):
            self.assertEqual(self.as_(u).get(f"{API}/trips").status_code, 403)
            self.assertEqual(self.client.post(f"{API}/plan", self.slot, format="json").status_code, 403)
