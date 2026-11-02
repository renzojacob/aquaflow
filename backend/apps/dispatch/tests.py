"""
End-to-end test of the dispatcher API: one order's whole life, through HTTP.
Run:  python manage.py test apps.dispatch
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import CustomerProfile, User
from apps.customers.models import Address
from apps.inventory.models import Product, StockLevel
from apps.orders.models import Order


class OrderLifecycleTest(APITestCase):
    def setUp(self):
        self.product = Product.objects.create(name="5-gallon refill", price=30)
        self.customer = User.objects.create_user("maria@test.com", "maria@test.com", "Water2026!x",
                                                 role="customer", first_name="Maria", last_name="Santos",
                                                 phone="09175550142")
        CustomerProfile.objects.create(user=self.customer, containers_held=2)
        self.dispatcher = User.objects.create_user("joy@test.com", "joy@test.com", "Water2026!x", role="dispatcher")
        self.rider = User.objects.create_user("jomar@test.com", "jomar@test.com", "Water2026!x", role="rider",
                                              first_name="Jomar", last_name="Reyes", phone="09195550123")
        self.owner = User.objects.create_user("owner@test.com", "owner@test.com", "Water2026!x", role="owner")
        self.address = Address.objects.create(customer=self.customer, label="Home", address_text="Purok 3, Camilmil",
                                              street="Purok 3", barangay="Camilmil", lat=13.41, lng=121.18,
                                              is_default=True)

    def place_order(self, qty=3):
        self.client.force_authenticate(self.customer)
        r = self.client.post("/api/customer/orders/", {
            "address": self.address.id, "quantity": qty,
            "delivery_date": (timezone.localdate() + timedelta(days=1)).isoformat(),
            "period": "morning", "expected_empties": 2,
        }, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        return r.data["id"]

    def act(self, oid, action, **body):
        self.client.force_authenticate(self.dispatcher)
        return self.client.post(f"/api/v1/dispatch/orders/{oid}/{action}", body, format="json")

    def test_customer_cannot_use_dispatch_api(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get("/api/v1/dispatch/stock").status_code, 403)

    def test_full_life_of_an_order(self):
        oid = self.place_order(3)

        # Queue shows it with the customer's name
        self.client.force_authenticate(self.dispatcher)
        day = (timezone.localdate() + timedelta(days=1)).isoformat()
        r = self.client.get("/api/v1/dispatch/orders", {"date": day})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data[0]["customer_name"], "Maria Santos")

        # No stock yet -> confirm is refused with a clear message (not a 500)
        r = self.act(oid, "confirm")
        self.assertEqual(r.status_code, 400, r.data)

        # Station receives 10 new empties, fills 8 of them
        r = self.client.post("/api/v1/dispatch/stock/adjust", {"type": "receive", "quantity": 10}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        r = self.client.post("/api/v1/dispatch/stock/adjust", {"type": "refill", "quantity": 8}, format="json")
        self.assertEqual(r.data["available"], 8)
        self.assertEqual(r.data["empty_at_station"], 2)

        # Confirm reserves 3
        r = self.act(oid, "confirm")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(StockLevel.objects.get().filled_reserved, 3)

        # Reject needs a reason
        self.assertEqual(self.act(oid, "cancel").status_code, 400)

        self.assertEqual(self.act(oid, "prepare").status_code, 200)
        self.assertEqual(self.act(oid, "ready").status_code, 200)

        # Riders list, then send out with Jomar
        r = self.client.get("/api/v1/dispatch/riders")
        self.assertEqual(r.data[0]["name"], "Jomar Reyes")
        r = self.act(oid, "dispatch", rider_id=self.rider.id)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["status"], "out_for_delivery")
        self.assertEqual(r.data["rider"]["name"], "Jomar Reyes")

        # The customer now sees the rider and can call them
        self.client.force_authenticate(self.customer)
        r = self.client.get(f"/api/customer/orders/{oid}/")
        self.assertEqual(r.data["rider"]["phone"], "09195550123")

        # Delivered: 3 left with customer, 2 empties back
        r = self.act(oid, "deliver", empties_collected=2)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["status"], "delivered")
        self.assertEqual(CustomerProfile.objects.get(user=self.customer).containers_held, 3)
        stock = StockLevel.objects.get()
        self.assertEqual((stock.filled_available, stock.filled_reserved, stock.empty_count), (5, 0, 4))

        # Stock log + summary are real
        r = self.client.get("/api/v1/dispatch/stock")
        self.assertTrue(len(r.data["log"]) >= 4)
        self.client.force_authenticate(self.owner)
        r = self.client.get("/api/v1/dispatch/summary", {"days": 7})
        self.assertEqual(r.status_code, 200)
        self.assertIn("days", r.data)

    def test_failed_delivery_returns_stock_and_replans_once(self):
        oid = self.place_order(2)
        self.client.force_authenticate(self.dispatcher)
        self.client.post("/api/v1/dispatch/stock/adjust", {"type": "receive", "quantity": 5}, format="json")
        self.client.post("/api/v1/dispatch/stock/adjust", {"type": "refill", "quantity": 5}, format="json")
        for a in ("confirm", "prepare", "ready", "dispatch"):
            self.assertEqual(self.act(oid, a).status_code, 200, a)
        self.assertEqual(self.act(oid, "fail").status_code, 400)      # needs a reason
        r = self.act(oid, "fail", reason="Nobody home")
        self.assertEqual(r.data["status"], "failed")
        self.assertEqual(StockLevel.objects.get().filled_available, 5)
        self.assertEqual(self.act(oid, "replan").status_code, 200)
        self.assertEqual(Order.objects.get(pk=oid).status, "confirmed")

    def test_owner_creates_staff_accounts(self):
        self.client.force_authenticate(self.owner)
        r = self.client.post("/api/v1/owner/users", {
            "full_name": "Joy Dela Cruz", "email": "joy2@test.com", "phone": "0918", "role": "dispatcher",
            "password": "Water2026!x",
        }, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(User.objects.get(email="joy2@test.com").role, "dispatcher")
        # weak password is refused with a readable reason
        r = self.client.post("/api/v1/owner/users", {
            "full_name": "X Y", "email": "x@test.com", "role": "rider", "password": "admin1234",
        }, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("password", r.data)
        # dispatcher can't manage people
        self.client.force_authenticate(self.dispatcher)
        self.assertEqual(self.client.get("/api/v1/owner/users").status_code, 403)
