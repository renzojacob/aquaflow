"""
Feature D: slot capacity and "Delivery nearby".
Run:  python manage.py test apps.orders.tests_slots
"""
import threading
from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import CustomerProfile, User
from apps.customers.models import Address
from apps.dispatch.models import Trip, TripStop, Vehicle
from apps.inventory.models import Product
from apps.orders.models import Order
from apps.orders.services import place_order
from apps.orders.slots import slot_availability
from apps.predictions.services import earliest_slot
from apps.station.models import SystemSetting

PW = "Water2026!x"
BASE = (13.41, 121.18)
M_PER_DEG_LAT = 111_195     # 0.0045 deg of latitude is about 500 m


class SlotBase:
    def setup_data(self):
        self.refill = Product.objects.create(name="5-gallon refill", price=30, kind="refill", sort_order=1)
        self.ice = Product.objects.create(name="Ice tube", price=25, kind="item", sort_order=2)
        self.day = timezone.localdate() + timedelta(days=1)
        self.n = 0
        self.cust, self.addr = self.customer()

    def customer(self, lat=BASE[0], lng=BASE[1]):
        self.n += 1
        u = User.objects.create_user(f"c{self.n}@t.ph", f"c{self.n}@t.ph", PW, role="customer")
        CustomerProfile.objects.create(user=u, containers_held=0)
        a = Address.objects.create(customer=u, label="Home", address_text=f"Street {self.n}", barangay="Lalud",
                                   lat=lat, lng=lng, is_default=True)
        return u, a

    def booked(self, containers, status="confirmed", period="morning", lat=BASE[0], lng=BASE[1]):
        """An order already in the slot, written straight to the database."""
        c, a = self.customer(lat, lng)
        return Order.objects.create(customer=c, address=a, product=self.refill, quantity=containers,
                                    containers=containers, delivery_date=self.day, period=period, status=status)


class SlotCapacityTests(SlotBase, APITestCase):
    def setUp(self):
        self.setup_data()

    def post(self, qty=None, period="morning", items=None):
        self.client.force_authenticate(self.cust)
        body = {"address": self.addr.id, "period": period, "delivery_date": self.day.isoformat()}
        body.update({"items": items} if items else {"quantity": qty})
        return self.client.post("/api/customer/orders/", body, format="json")

    def slots(self, **params):
        self.client.force_authenticate(self.cust)
        r = self.client.get("/api/customer/slots/", params)
        self.assertEqual(r.status_code, 200, r.data)
        return {(s["date"], s["period"]): s for s in r.data["slots"]}

    def tomorrow(self, period="morning", **params):
        return self.slots(**params)[(self.day.isoformat(), period)]

    def test_no_vehicles_means_nothing_is_blocked(self):
        self.booked(50)
        s = self.tomorrow()
        self.assertFalse(s["limited"])
        self.assertIsNone(s["remaining"])
        self.assertEqual(self.post(5).status_code, 201)

    def test_remaining_counts_open_orders_only(self):
        Vehicle.objects.create(name="T1", plate="T1", capacity_containers=10)
        self.booked(3, status="pending")           # pending holds room too
        self.booked(4, status="confirmed")
        self.booked(1, status="delivered")
        for st in ("cancelled", "rejected", "failed"):
            self.booked(5, status=st)              # these don't
        self.booked(6, period="afternoon")         # other period
        s = self.tomorrow()
        self.assertEqual((s["capacity"], s["booked"], s["remaining"]), (10, 8, 2))
        self.assertTrue(s["almost_full"])
        self.assertFalse(s["full"])
        self.assertEqual(self.tomorrow("afternoon")["remaining"], 4)

    def test_order_that_does_not_fit_is_rejected_with_a_clear_reason(self):
        Vehicle.objects.create(name="T1", plate="T1", capacity_containers=10)
        self.booked(8)
        r = self.post(3)
        self.assertEqual(r.status_code, 400)
        self.assertIn("Only 2 containers left for morning", r.data["period"][0])
        self.assertFalse(self.tomorrow(quantity=3)["fits"])
        self.assertEqual(self.post(2).status_code, 201)      # exactly fills it
        s = self.tomorrow()
        self.assertTrue(s["full"])
        r = self.post(1)
        self.assertEqual(r.status_code, 400)
        self.assertIn("fully booked", r.data["period"][0])
        self.assertEqual(self.post(1, period="afternoon").status_code, 201)   # afternoon still open

    def test_items_without_containers_still_go_through_when_full(self):
        Vehicle.objects.create(name="T1", plate="T1", capacity_containers=4)
        self.booked(4)
        r = self.post(items=[{"product": self.ice.id, "quantity": 2}])
        self.assertEqual(r.status_code, 201, r.data)

    def test_switched_off_vehicle_counts_only_if_it_already_has_a_trip(self):
        Vehicle.objects.create(name="On", plate="A1", capacity_containers=10)
        off = Vehicle.objects.create(name="Off", plate="B1", capacity_containers=6, is_available=False)
        self.assertEqual(self.tomorrow()["capacity"], 10)
        Trip.objects.create(date=self.day, period="morning", vehicle=off)
        self.assertEqual(self.tomorrow()["capacity"], 16)
        self.assertEqual(self.tomorrow("afternoon")["capacity"], 10)

    def test_every_vehicle_switched_off_closes_ordering(self):
        Vehicle.objects.create(name="Off", plate="B1", capacity_containers=6, is_available=False)
        self.assertTrue(self.tomorrow()["full"])
        self.assertEqual(self.post(1).status_code, 400)

    def test_only_customers_can_ask(self):
        rider = User.objects.create_user("r@t.ph", "r@t.ph", PW, role="rider")
        self.client.force_authenticate(rider)
        self.assertEqual(self.client.get("/api/customer/slots/").status_code, 403)

    def test_reorder_slot_skips_a_full_period(self):
        Vehicle.objects.create(name="T1", plate="T1", capacity_containers=5)
        self.booked(5)                                           # tomorrow morning is full
        early = timezone.make_aware(datetime.combine(self.day - timedelta(days=1), time(20, 0)))
        self.assertEqual(earliest_slot(now=early), (self.day, "morning"))
        self.assertEqual(earliest_slot(now=early, containers=3), (self.day, "afternoon"))


class DeliveryNearbyTests(SlotBase, APITestCase):
    def setUp(self):
        self.setup_data()
        self.v = Vehicle.objects.create(name="T1", plate="T1", capacity_containers=10)
        self.trip = Trip.objects.create(date=self.day, period="morning", vehicle=self.v)

    def stop_at(self, metres_north, containers=2, trip=None, status="pending"):
        o = self.booked(containers, lat=BASE[0] + metres_north / M_PER_DEG_LAT)
        trip = trip or self.trip
        return TripStop.objects.create(trip=trip, order=o, sequence=trip.stops.count() + 1, status=status)

    def nearby(self, qty=None):
        self.client.force_authenticate(self.cust)
        params = {"address": self.addr.id, **({"quantity": qty} if qty else {})}
        r = self.client.get("/api/customer/slots/", params)
        return {s["period"]: s["delivery_nearby"] for s in r.data["slots"] if s["date"] == self.day.isoformat()}

    def test_planned_stop_within_one_km_is_nearby(self):
        self.stop_at(500)
        self.assertEqual(self.nearby(), {"morning": True, "afternoon": False})

    def test_stop_further_than_the_setting_is_not(self):
        self.stop_at(1500)
        self.assertFalse(self.nearby()["morning"])
        s = SystemSetting.load()
        s.nearby_radius_m = 2000
        s.save()
        self.assertTrue(self.nearby()["morning"])

    def test_trip_without_room_is_not_nearby(self):
        self.stop_at(300, containers=8)
        self.assertTrue(self.nearby(qty=2)["morning"])            # 2 left on the trip
        self.assertFalse(self.nearby(qty=3)["morning"])

    def test_failed_stops_and_departed_trips_do_not_count(self):
        self.stop_at(300, status="failed")
        self.assertFalse(self.nearby()["morning"])
        self.stop_at(300)
        self.trip.status = Trip.Status.OUT
        self.trip.save()
        self.assertFalse(self.nearby()["morning"])

    def test_someone_elses_address_gets_no_nearby_answer(self):
        self.stop_at(200)
        _, other = self.customer()
        self.client.force_authenticate(self.cust)
        r = self.client.get("/api/customer/slots/", {"address": other.id})
        self.assertFalse(any(s["delivery_nearby"] for s in r.data["slots"]))


class LastContainersRaceTest(SlotBase, TransactionTestCase):
    """Two customers order the last containers at the same moment: exactly one gets them."""

    def setUp(self):
        self.setup_data()
        Vehicle.objects.create(name="T1", plate="T1", capacity_containers=10)
        self.booked(8)
        self.other, self.other_addr = self.customer()

    def test_only_one_of_two_simultaneous_orders_wins(self):
        start, results = threading.Barrier(2), []

        def attempt(user, address):
            try:
                start.wait()
                place_order(user, address=address, delivery_date=self.day, period="morning", quantity=2)
                results.append("ok")
            except ValidationError:
                results.append("full")
            finally:
                connection.close()

        threads = [threading.Thread(target=attempt, args=(self.cust, self.addr)),
                   threading.Thread(target=attempt, args=(self.other, self.other_addr))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(sorted(results), ["full", "ok"])
        self.assertEqual(slot_availability(self.day, "morning").booked, 10)
