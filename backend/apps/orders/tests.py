"""
Cart (several products in one order), through HTTP.
Run:  python manage.py test apps.orders
"""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import CustomerProfile, User
from apps.customers.models import Address
from apps.inventory.models import Product, StockLevel
from apps.orders.models import Order

PW = "Water2026!x"


class CartTest(APITestCase):
    def setUp(self):
        self.refill = Product.objects.create(name="5-gallon refill", price=30, kind="refill", sort_order=1)
        self.jug = Product.objects.create(name="New 5-gallon container", price=250, kind="container", sort_order=2, max_per_order=3)
        self.ice = Product.objects.create(name="Ice tube 1 kg", price=25, kind="item", sort_order=3)
        StockLevel.objects.create(product=self.refill, filled_available=20, empty_count=10)
        StockLevel.objects.create(product=self.jug, filled_available=5)
        StockLevel.objects.create(product=self.ice, filled_available=1)
        self.cust = User.objects.create_user("ana@t.ph", "ana@t.ph", PW, role="customer", first_name="Ana")
        CustomerProfile.objects.create(user=self.cust, containers_held=2)
        self.addr = Address.objects.create(customer=self.cust, label="Home", street="Purok 1", barangay="Lalud",
                                           address_text="Purok 1, Lalud", lat=13.41, lng=121.18, is_default=True)
        self.disp = User.objects.create_user("joy@t.ph", "joy@t.ph", PW, role="dispatcher")
        self.owner = User.objects.create_user("own@t.ph", "own@t.ph", PW, role="owner")

    def order(self, items, **extra):
        self.client.force_authenticate(self.cust)
        return self.client.post("/api/customer/orders/", {
            "address": self.addr.id, "period": "morning",
            "delivery_date": (timezone.localdate() + timedelta(days=1)).isoformat(),
            "items": items, **extra,
        }, format="json")

    def act(self, oid, action, **body):
        self.client.force_authenticate(self.disp)
        return self.client.post(f"/api/v1/dispatch/orders/{oid}/{action}", body, format="json")

    def test_settings_list_the_catalog(self):
        self.ice.is_active = False
        self.ice.save()
        r = self.client.get("/api/settings/public/")
        self.assertEqual([p["name"] for p in r.data["products"]], ["5-gallon refill", "New 5-gallon container"])
        self.assertEqual(r.data["price_per_container"], 30)

    def test_mixed_cart_totals_and_containers(self):
        r = self.order([{"product": self.refill.id, "quantity": 3}, {"product": self.jug.id, "quantity": 1},
                        {"product": self.refill.id, "quantity": 1}])  # repeated product is merged
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Decimal(r.data["total"]), Decimal("370"))       # 4 x 30 + 250
        self.assertEqual(r.data["containers"], 4)                       # refills only
        self.assertEqual(r.data["quantity"], 5)
        self.assertEqual([(i["product_name"], i["quantity"]) for i in r.data["items"]],
                         [("5-gallon refill", 4), ("New 5-gallon container", 1)])
        self.assertEqual(r.data["expected_empties"], 2)                 # min(held 2, refills 4)

    def test_stock_is_reserved_per_product(self):
        oid = self.order([{"product": self.refill.id, "quantity": 2}, {"product": self.jug.id, "quantity": 2}]).data["id"]
        self.assertEqual(self.act(oid, "confirm").status_code, 200)
        self.assertEqual(StockLevel.objects.get(product=self.refill).filled_available, 18)
        self.assertEqual(StockLevel.objects.get(product=self.jug).filled_available, 3)
        self.assertEqual(StockLevel.objects.get(product=self.jug).filled_reserved, 2)
        # cancel gives both back
        self.act(oid, "cancel", reason="Customer asked to cancel")
        self.assertEqual(StockLevel.objects.get(product=self.jug).filled_available, 5)
        self.assertEqual(StockLevel.objects.get(product=self.refill).filled_reserved, 0)

    def test_not_enough_of_one_product_names_it_and_changes_nothing(self):
        oid = self.order([{"product": self.refill.id, "quantity": 2}, {"product": self.ice.id, "quantity": 3}]).data["id"]
        r = self.act(oid, "confirm")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Ice tube", str(r.data))
        self.assertEqual(StockLevel.objects.get(product=self.refill).filled_available, 20)  # rolled back
        self.assertEqual(Order.objects.get(pk=oid).status, "pending")

    def test_delivery_counts_only_refills_as_containers(self):
        oid = self.order([{"product": self.refill.id, "quantity": 2}, {"product": self.jug.id, "quantity": 1}],
                         expected_empties=1).data["id"]
        for a in ("confirm", "prepare", "ready", "dispatch"):
            self.assertEqual(self.act(oid, a).status_code, 200, a)
        self.act(oid, "deliver", empties_collected=1)
        Order.objects.filter(pk=oid).update(delivery_date=timezone.localdate())  # count it in today's sales
        self.assertEqual(CustomerProfile.objects.get(user=self.cust).containers_held, 3)  # 2 + 2 refills - 1 back
        self.assertEqual(StockLevel.objects.get(product=self.refill).empty_count, 11)
        self.client.force_authenticate(self.owner)
        r = self.client.get("/api/v1/dispatch/summary", {"days": 3})
        self.assertEqual(r.data["totals"]["revenue"], 310)
        self.assertEqual(r.data["totals"]["containers"], 2)

    def test_rules(self):
        self.assertEqual(self.order([]).status_code, 400)
        r = self.order([{"product": self.jug.id, "quantity": 4}])            # max 3 per order
        self.assertEqual(r.status_code, 400)
        self.assertIn("up to 3", str(r.data))
        self.ice.is_active = False
        self.ice.save()
        self.assertEqual(self.order([{"product": self.ice.id, "quantity": 1}]).status_code, 400)
        r = self.order([{"product": self.jug.id, "quantity": 1}], expected_empties=1)  # no refills: no empties
        self.assertEqual(r.status_code, 400)

    def test_old_style_order_still_works(self):
        self.client.force_authenticate(self.cust)
        r = self.client.post("/api/customer/orders/", {
            "address": self.addr.id, "period": "morning", "quantity": 3,
            "delivery_date": (timezone.localdate() + timedelta(days=1)).isoformat(),
        }, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Decimal(r.data["total"]), Decimal("90"))
        self.assertEqual(len(r.data["items"]), 1)

    def test_owner_manages_products(self):
        self.client.force_authenticate(self.owner)
        r = self.client.post("/api/v1/owner/products", {"name": "1-gallon bottle", "kind": "item", "price": "15", "max_per_order": 10}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        pid = r.data["id"]
        self.assertEqual(self.client.patch(f"/api/v1/owner/products/{pid}", {"price": "18"}, format="json").data["price"], 18)
        self.assertEqual(self.client.post("/api/v1/owner/products", {"name": "X", "kind": "item", "price": "0"}, format="json").status_code, 400)
        # the last refill can't be switched off
        r = self.client.patch(f"/api/v1/owner/products/{self.refill.id}", {"is_active": False}, format="json")
        self.assertEqual(r.status_code, 400)
        # stock for a non-refill product
        self.client.force_authenticate(self.disp)
        r = self.client.post("/api/v1/dispatch/stock/adjust", {"product_id": pid, "type": "add", "quantity": 12}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(next(o for o in r.data["others"] if o["id"] == pid)["available"], 12)
        self.client.force_authenticate(self.cust)
        self.assertEqual(self.client.get("/api/v1/owner/products").status_code, 403)
