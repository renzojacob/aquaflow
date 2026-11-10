"""
Supplies: caps, seals and filters. Run:  python manage.py test apps.inventory
"""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.inventory import supplies as svc
from apps.inventory.models import Product, StockLevel, Supply, SupplyMovement

API = "/api/v1/dispatch/supplies"
PW = "Water2026!x"


def make_supply(**kw):
    data = {"name": "Bottle caps", "unit": "piece", "quantity": Decimal("500"),
            "used_per_refill": Decimal("1"), "reorder_level": Decimal("100"), "lead_time_days": 3}
    data.update(kw)
    return Supply.objects.create(**data)


class SupplyServiceTests(TestCase):
    def test_movement_changes_the_count_and_logs_it(self):
        s = make_supply(quantity=Decimal("10"))
        svc.apply_supply_movement(s, Decimal("5"), SupplyMovement.Reason.RECEIVED, note="delivery")
        s.refresh_from_db()
        self.assertEqual(s.quantity, Decimal("15.00"))
        self.assertEqual(s.movements.count(), 1)

    def test_it_never_goes_below_zero(self):
        s = make_supply(quantity=Decimal("3"))
        m = svc.apply_supply_movement(s, Decimal("-10"), SupplyMovement.Reason.USED)
        s.refresh_from_db()
        self.assertEqual(s.quantity, Decimal("0.00"))
        self.assertEqual(m.delta, Decimal("-3.00"))          # the log shows what was really possible
        self.assertIn("zero", m.note)

    def test_a_refill_batch_uses_caps_seals_and_filter_life(self):
        caps = make_supply(name="Caps", used_per_refill=Decimal("1"), quantity=Decimal("100"))
        seals = make_supply(name="Seals", used_per_refill=Decimal("1"), quantity=Decimal("100"))
        filt = make_supply(name="Filter", used_per_refill=Decimal("0.0005"), quantity=Decimal("1"), reorder_level=Decimal("0.2"))
        soap = make_supply(name="Soap", used_per_refill=Decimal("0"), quantity=Decimal("5"))
        svc.consume_for_refills(20, note="Filled 20 containers")
        for s in (caps, seals, filt, soap):
            s.refresh_from_db()
        self.assertEqual(caps.quantity, Decimal("80.00"))
        self.assertEqual(seals.quantity, Decimal("80.00"))
        self.assertEqual(filt.quantity, Decimal("0.99"))      # 0.0005 x 20 = 0.01
        self.assertEqual(soap.quantity, Decimal("5.00"))      # not used per container: untouched
        self.assertEqual(caps.movements.first().note, "Filled 20 containers")

    def test_a_switched_off_supply_is_not_used(self):
        off = make_supply(name="Old caps", is_active=False, quantity=Decimal("50"))
        svc.consume_for_refills(10)
        off.refresh_from_db()
        self.assertEqual(off.quantity, Decimal("50.00"))

    def test_days_left_comes_from_what_was_really_used(self):
        s = make_supply(quantity=Decimal("300"))
        svc.apply_supply_movement(s, Decimal("-300"), SupplyMovement.Reason.USED)   # 300 in the window
        s.refresh_from_db()
        svc.apply_supply_movement(s, Decimal("300"), SupplyMovement.Reason.RECEIVED)
        s.refresh_from_db()
        usage = svc.daily_usage(s)                                                  # 300 / 30 days
        self.assertEqual(usage, Decimal("10.00"))
        self.assertEqual(svc.days_left(s, usage), 30.0)

    def test_usage_falls_back_to_the_per_container_rate(self):
        s = make_supply(quantity=Decimal("300"), used_per_refill=Decimal("2"))
        p = Product.objects.create(name="5-gallon refill", price=30)
        StockLevel.objects.create(product=p)
        from apps.inventory.services import apply_movement
        apply_movement(p, "refill", available=150, note="batch")                    # 150 over 30 days = 5/day
        self.assertEqual(svc.daily_usage(s), Decimal("10.00"))                      # 5 x 2

    def test_unknown_usage_gives_no_days_left(self):
        s = make_supply(quantity=Decimal("40"), used_per_refill=Decimal("0"), reorder_level=Decimal("0"))
        self.assertIsNone(svc.daily_usage(s))
        self.assertIsNone(svc.days_left(s, None))
        self.assertEqual(svc.status_of(s, None)[0], "ok")

    def test_alerts(self):
        out = make_supply(name="None left", quantity=Decimal("0"))
        self.assertEqual(svc.status_of(out, Decimal("1"))[0], "out")

        below = make_supply(name="Below level", quantity=Decimal("90"), reorder_level=Decimal("100"))
        self.assertEqual(svc.status_of(below, None)[0], "low")

        # 20 left, 10 used a day = 2 days, but a delivery takes 3 days
        soon = make_supply(name="Runs out first", quantity=Decimal("20"), reorder_level=Decimal("0"), lead_time_days=3)
        status, why = svc.status_of(soon, Decimal("10"))
        self.assertEqual(status, "low")
        self.assertIn("Order now", why)

        fine = make_supply(name="Plenty", quantity=Decimal("900"), reorder_level=Decimal("100"))
        self.assertEqual(svc.status_of(fine, Decimal("10"))[0], "ok")


class SupplyApiTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user("o@t.com", "o@t.com", PW, role="owner")
        self.dispatcher = User.objects.create_user("d@t.com", "d@t.com", PW, role="dispatcher")
        self.customer = User.objects.create_user("c@t.com", "c@t.com", PW, role="customer")

    def as_(self, u):
        self.client.force_authenticate(u)
        return self.client

    def test_owner_adds_edits_and_the_dispatcher_can_only_look(self):
        r = self.as_(self.owner).post(API, {"name": "Bottle caps", "unit": "piece", "quantity": 500,
                                            "used_per_refill": 1, "reorder_level": 100, "lead_time_days": 3}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        row = r.data["supplies"][0]
        self.assertEqual((row["name"], row["quantity"]), ("Bottle caps", 500.0))
        self.assertTrue(row["auto"])

        self.assertEqual(self.as_(self.dispatcher).get(API).status_code, 200)
        self.assertEqual(self.as_(self.dispatcher).post(API, {"name": "X", "quantity": 1}, format="json").status_code, 403)
        self.assertEqual(self.as_(self.customer).get(API).status_code, 403)

        r = self.as_(self.owner).patch(f"{API}/{row['id']}", {"name": "Bottle caps", "reorder_level": 200}, format="json")
        self.assertEqual(r.data["supplies"][0]["reorder_level"], 200.0)

    def test_bad_input_gets_a_plain_message(self):
        c = self.as_(self.owner)
        self.assertEqual(c.post(API, {"name": "A"}, format="json").status_code, 400)
        c.post(API, {"name": "Caps", "quantity": 10}, format="json")
        r = c.post(API, {"name": "caps", "quantity": 5}, format="json")           # same name
        self.assertEqual(r.status_code, 400)
        self.assertIn("already have a supply", str(r.data))
        r = c.post(API, {"name": "Seals", "used_per_refill": "many"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_received_used_and_correction(self):
        s = make_supply(quantity=Decimal("100"))
        c = self.as_(self.owner)
        self.assertEqual(c.post(f"{API}/{s.pk}/adjust", {"type": "received", "quantity": 50}, format="json").data["supplies"][0]["quantity"], 150.0)
        self.assertEqual(c.post(f"{API}/{s.pk}/adjust", {"type": "used", "quantity": 20}, format="json").data["supplies"][0]["quantity"], 130.0)
        r = c.post(f"{API}/{s.pk}/adjust", {"type": "correction", "quantity": 125}, format="json")
        self.assertEqual(r.status_code, 400)                                       # a count needs a reason
        r = c.post(f"{API}/{s.pk}/adjust", {"type": "correction", "quantity": 125, "note": "counted the shelf"}, format="json")
        self.assertEqual(r.data["supplies"][0]["quantity"], 125.0)
        self.assertEqual(r.data["log"][0]["delta"], -5.0)

    def test_a_supply_with_history_cannot_be_deleted(self):
        s = make_supply()
        c = self.as_(self.owner)
        self.assertEqual(c.delete(f"{API}/{s.pk}").status_code, 200)               # no history yet: gone
        s2 = make_supply(name="Seals")
        svc.apply_supply_movement(s2, Decimal("1"), SupplyMovement.Reason.RECEIVED)
        r = c.delete(f"{API}/{s2.pk}")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Switch it off", str(r.data))

    def test_recording_a_refill_batch_takes_caps_off_the_shelf(self):
        """The real flow: dispatcher fills 10 containers on the Stock screen."""
        product = Product.objects.create(name="5-gallon refill", price=30)
        StockLevel.objects.create(product=product, empty_count=20)
        caps = make_supply(name="Caps", quantity=Decimal("12"), used_per_refill=Decimal("1"), reorder_level=Decimal("5"))

        r = self.as_(self.dispatcher).post("/api/v1/dispatch/stock/adjust",
                                           {"type": "refill", "quantity": 10, "reason": "morning batch"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        caps.refresh_from_db()
        self.assertEqual(caps.quantity, Decimal("2.00"))
        self.assertIn("Caps", str(r.data.get("supply_warnings")))                  # the dispatcher is told

    def test_refill_without_supplies_or_other_stock_changes_leave_supplies_alone(self):
        """Only a refill batch uses caps; counting or receiving containers must not."""
        product = Product.objects.create(name="5-gallon refill", price=30)
        StockLevel.objects.create(product=product, empty_count=20)
        r = self.as_(self.dispatcher).post("/api/v1/dispatch/stock/adjust",
                                           {"type": "refill", "quantity": 4}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["supply_warnings"], [])                            # nothing set up, nothing to warn
        caps = make_supply(name="Caps", quantity=Decimal("50"), used_per_refill=Decimal("1"))
        c = self.as_(self.dispatcher)
        self.assertEqual(c.post("/api/v1/dispatch/stock/adjust",
                                {"type": "receive", "quantity": 5}, format="json").status_code, 200)
        self.assertEqual(c.post("/api/v1/dispatch/stock/adjust",
                                {"type": "correction", "quantity": 4, "reason": "recount"}, format="json").status_code, 200)
        caps.refresh_from_db()
        self.assertEqual(caps.quantity, Decimal("50.00"))

    def test_payload_counts_and_alerts(self):
        make_supply(name="Fine", quantity=Decimal("900"), reorder_level=Decimal("10"))
        make_supply(name="Empty", quantity=Decimal("0"))
        make_supply(name="Hidden", quantity=Decimal("0"), is_active=False)
        data = self.as_(self.owner).get(API).data
        self.assertEqual(data["counts"], {"total": 2, "low": 0, "out": 1})
        self.assertEqual([a["name"] for a in data["alerts"]], ["Empty"])
        self.assertEqual(data["window_days"], 30)
