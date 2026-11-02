"""
Rider app + live tracking, end to end through HTTP.
Run:  python manage.py test apps.delivery
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import CustomerProfile, User
from apps.customers.models import Address
from apps.delivery.models import DeliveryAttempt, RiderLocation
from apps.inventory.models import Product, StockLevel
from apps.orders.models import Order
from apps.station.models import Station

PW = "Water2026!x"


class RiderFlowTest(APITestCase):
    def setUp(self):
        Station.objects.create(name="AquaFlow", lat=13.4108, lng=121.1792)
        self.product = Product.objects.create(name="5-gallon refill", price=30)
        StockLevel.objects.create(product=self.product, filled_available=50, empty_count=10)
        self.disp = User.objects.create_user("joy@t.ph", "joy@t.ph", PW, role="dispatcher")
        self.rider = User.objects.create_user("jomar@t.ph", "jomar@t.ph", PW, role="rider", first_name="Jomar", last_name="Reyes", phone="09195550123")
        self.other_rider = User.objects.create_user("leo@t.ph", "leo@t.ph", PW, role="rider")
        self.near = self._customer("ana", 13.4120, 121.1800)   # ~150 m from the station
        self.far = self._customer("ben", 13.4300, 121.2000)    # ~3 km away

    def _customer(self, name, lat, lng):
        u = User.objects.create_user(f"{name}@t.ph", f"{name}@t.ph", PW, role="customer", first_name=name.title())
        CustomerProfile.objects.create(user=u, containers_held=3)
        a = Address.objects.create(customer=u, label="Home", street="Purok 1", barangay="Lalud",
                                   address_text="Purok 1, Lalud", lat=lat, lng=lng, is_default=True)
        return u, a

    def _out_order(self, who, qty=2):
        """Place an order as the customer and walk it to 'out for delivery' with Jomar."""
        user, addr = who
        self.client.force_authenticate(user)
        r = self.client.post("/api/customer/orders/", {
            "address": addr.id, "quantity": qty, "period": "morning", "expected_empties": 1,
            "delivery_date": (timezone.localdate() + timedelta(days=1)).isoformat(),
        }, format="json")
        oid = r.data["id"]
        self.client.force_authenticate(self.disp)
        for a in ("confirm", "prepare", "ready"):
            self.client.post(f"/api/v1/dispatch/orders/{oid}/{a}", {}, format="json")
        self.client.post(f"/api/v1/dispatch/orders/{oid}/dispatch", {"rider_id": self.rider.id}, format="json")
        return Order.objects.get(pk=oid)

    def test_only_riders_use_the_rider_api(self):
        self.client.force_authenticate(self.near[0])
        self.assertEqual(self.client.get("/api/v1/rider/today").status_code, 403)

    def test_stops_nearest_first_and_customer_tracking(self):
        far_order = self._out_order(self.far)
        near_order = self._out_order(self.near)

        # Rider at the station: the near customer is first
        self.client.force_authenticate(self.rider)
        r = self.client.post("/api/v1/rider/location", {"lat": 13.4108, "lng": 121.1792, "accuracy_m": 8}, format="json")
        self.assertEqual(r.status_code, 201)
        r = self.client.get("/api/v1/rider/today")
        self.assertEqual([s["id"] for s in r.data["stops"]], [near_order.id, far_order.id])
        self.assertEqual(r.data["totals"]["on_board"], 4)
        self.assertEqual(r.data["totals"]["to_collect"], 120)

        # Far customer: 1 stop before them, a distance and an ETA, and Jomar's position
        self.client.force_authenticate(self.far[0])
        r = self.client.get(f"/api/customer/orders/{far_order.id}/track/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["stops_before"], 1)
        self.assertEqual(r.data["rider"]["name"], "Jomar Reyes")
        self.assertTrue(r.data["location"]["fresh"])
        self.assertGreater(r.data["distance_m"], 2000)
        self.assertGreaterEqual(r.data["eta_minutes"], 5)

        # Rider moves next to the far customer: now they are first
        self.client.force_authenticate(self.rider)
        self.client.post("/api/v1/rider/location", {"lat": 13.4298, "lng": 121.1998, "is_simulated": True}, format="json")
        r = self.client.get("/api/v1/rider/today")
        self.assertEqual(r.data["stops"][0]["id"], far_order.id)
        self.assertTrue(r.data["location"]["is_simulated"])

        # Another customer can't track this order
        self.client.force_authenticate(self.near[0])
        self.assertEqual(self.client.get(f"/api/customer/orders/{far_order.id}/track/").status_code, 404)

    def test_deliver_needs_the_right_code(self):
        order = self._out_order(self.near, qty=3)
        self.client.force_authenticate(self.rider)
        url = f"/api/v1/rider/orders/{order.id}/deliver"
        self.assertEqual(self.client.post(url, {"code": ""}, format="json").status_code, 400)
        r = self.client.post(url, {"code": "000000" if order.confirmation_code != "000000" else "111111"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("code", r.data)
        self.assertEqual(Order.objects.get(pk=order.pk).status, "out_for_delivery")

        # Right code, standing at the door (inside the geofence)
        r = self.client.post(url, {"code": order.confirmation_code, "empties_collected": 2,
                                   "lat": 13.4120, "lng": 121.1800, "accuracy_m": 10}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(r.data["code_ok"])
        self.assertFalse(r.data["geofence_flagged"])
        order.refresh_from_db()
        self.assertEqual(order.status, "delivered")
        self.assertFalse(order.needs_review)
        self.assertEqual(CustomerProfile.objects.get(user=self.near[0]).containers_held, 4)  # 3 + 3 - 2

        r = self.client.get("/api/v1/rider/today")
        self.assertEqual(r.data["totals"]["delivered"], 1)
        self.assertEqual(r.data["totals"]["collected"], 90)
        self.assertEqual(r.data["stops"], [])

    def test_no_code_delivery_is_flagged_for_review(self):
        order = self._out_order(self.near)
        self.client.force_authenticate(self.rider)
        r = self.client.post(f"/api/v1/rider/orders/{order.id}/deliver",
                             {"no_code": True, "lat": 13.44, "lng": 121.22}, format="json")  # far from the pin
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["geofence_flagged"])
        self.assertTrue(Order.objects.get(pk=order.pk).needs_review)

    def test_failed_delivery_with_reason(self):
        order = self._out_order(self.near)
        self.client.force_authenticate(self.rider)
        url = f"/api/v1/rider/orders/{order.id}/fail"
        self.assertEqual(self.client.post(url, {"failure_reason": "nope"}, format="json").status_code, 400)
        r = self.client.post(url, {"failure_reason": "absent", "note": "Gate locked"}, format="json")
        self.assertEqual(r.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, "failed")
        self.assertEqual(order.history.last().note, "No one was home: Gate locked")
        self.assertEqual(DeliveryAttempt.objects.get(order=order).outcome, "failed")

    def test_a_rider_cannot_touch_another_riders_order(self):
        order = self._out_order(self.near)
        self.client.force_authenticate(self.other_rider)
        r = self.client.post(f"/api/v1/rider/orders/{order.id}/deliver", {"code": order.confirmation_code}, format="json")
        self.assertEqual(r.status_code, 404)

    def test_bad_location_is_refused(self):
        self.client.force_authenticate(self.rider)
        self.assertEqual(self.client.post("/api/v1/rider/location", {"lat": 200, "lng": 1}, format="json").status_code, 400)
        self.assertEqual(RiderLocation.objects.count(), 0)
