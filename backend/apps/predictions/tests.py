"""
Feature C: refill prediction, reminders, one-tap reorder, demand and backtest.
Run:  python manage.py test apps.predictions
"""
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import CustomerProfile, User
from apps.customers.models import Address
from apps.dispatch import services as dispatch_services
from apps.inventory.models import Product, StockLevel
from apps.notifications.models import EmailLog
from apps.orders.models import Order
from apps.station.models import Station

from . import services
from .models import RefillPrediction, ReminderLog

PW = "Water2026!x"
D = date.fromisoformat


class EstimateTest(TestCase):
    """The calculation itself, no database."""

    def test_reyes_example_from_the_spec(self):
        # 3 containers on Oct 1, Oct 7, Oct 13 -> 2 days per container -> run out Oct 19
        est = services.estimate([(D("2026-10-01"), 3), (D("2026-10-07"), 3), (D("2026-10-13"), 3)])
        self.assertEqual(est.days_per_container, Decimal("2.00"))
        self.assertEqual(est.runout, D("2026-10-19"))
        self.assertEqual(est.weights, [3, 2])

    def test_needs_three_orders(self):
        self.assertIsNone(services.estimate([]))
        self.assertIsNone(services.estimate([(D("2026-10-01"), 3), (D("2026-10-07"), 3)]))

    def test_last_three_intervals_weighted_3_2_1(self):
        # intervals per container: 10/2=5 (ignored, 4th from last), 4/2=2, 6/2=3, 8/2=4 (most recent)
        deliveries = [(D("2026-09-01"), 2), (D("2026-09-11"), 2), (D("2026-09-15"), 2),
                      (D("2026-09-21"), 2), (D("2026-09-29"), 2)]
        est = services.estimate(deliveries)
        # (4*3 + 3*2 + 2*1) / 6 = 3.33
        self.assertEqual(est.days_per_container, Decimal("3.33"))
        self.assertEqual(len(est.intervals), 3)
        # 2 containers x 3.33 = 6.66 -> 7 days after Sep 29
        self.assertEqual(est.runout, D("2026-10-06"))

    def test_divides_by_the_earlier_delivery(self):
        # 2 containers lasted 6 days (3/container), then 4 containers lasted 8 days (2/container)
        est = services.estimate([(D("2026-10-01"), 2), (D("2026-10-07"), 4), (D("2026-10-15"), 1)])
        self.assertEqual(est.days_per_container, Decimal("2.40"))   # (2*3 + 3*2) / 5
        self.assertEqual(est.runout, D("2026-10-17"))               # 1 x 2.4 -> 2 days

    def test_same_day_deliveries_are_merged(self):
        merged = services.merge_same_day([(D("2026-10-07"), 1), (D("2026-10-01"), 3), (D("2026-10-07"), 2),
                                          (D("2026-10-05"), 0)])
        self.assertEqual(merged, [(D("2026-10-01"), 3), (D("2026-10-07"), 3)])


class Base(APITestCase):
    def setUp(self):
        Station.objects.create(name="AquaFlow", lat=13.4108, lng=121.1792)
        self.refill = Product.objects.create(name="5-gallon refill", price=30)
        self.ice = Product.objects.create(name="Ice", price=20, kind=Product.Kind.ITEM)
        StockLevel.objects.create(product=self.refill, filled_available=40, filled_reserved=0, empty_count=10)
        self.disp = User.objects.create_user("joy@t.ph", "joy@t.ph", PW, role="dispatcher")
        self.owner = User.objects.create_user("own@t.ph", "own@t.ph", PW, role="owner")
        self.rider = User.objects.create_user("jomar@t.ph", "jomar@t.ph", PW, role="rider")
        self.today = timezone.localdate()
        self.reyes, self.home = self._customer("reyes", usual=3)

    def _customer(self, name, usual=3, reminders=True, email=True):
        u = User.objects.create_user(name, f"{name}@t.ph" if email else "", PW, role="customer",
                                     first_name=name.title(), last_name="Family")
        CustomerProfile.objects.create(user=u, containers_held=3, usual_quantity=usual,
                                       reminders_enabled=reminders)
        a = Address.objects.create(customer=u, label="Home", street="Purok 1", barangay="Lalud",
                                   address_text="Purok 1, Lalud", lat=13.4120, lng=121.1800, is_default=True)
        return u, a

    def _order(self, user, addr, day, qty=3, status=Order.Status.DELIVERED, product=None):
        product = product or self.refill
        return Order.objects.create(customer=user, address=addr, product=product, quantity=qty,
                                    containers=qty if product.kind == Product.Kind.REFILL else 0,
                                    delivery_date=day, period="morning", status=status)

    def _history(self, user, addr, days_ago, qty=3):
        """Delivered orders `days_ago` before today, then a fresh prediction."""
        for n in days_ago:
            self._order(user, addr, self.today - timedelta(days=n), qty)
        return services.refresh_prediction(user, addr)


class RefreshTest(Base):
    def test_not_enough_history(self):
        self.assertIsNone(self._history(self.reyes, self.home, [12, 6]))
        self.assertFalse(RefillPrediction.objects.exists())

    def test_items_only_orders_are_not_refills(self):
        self._order(self.reyes, self.home, self.today - timedelta(days=3), qty=2, product=self.ice)
        self.assertIsNone(self._history(self.reyes, self.home, [12, 6]))

    def test_delivery_refreshes_prediction_and_keeps_the_old_one(self):
        first = self._history(self.reyes, self.home, [18, 12, 6])
        self.assertEqual(first.predicted_runout_date, self.today)          # 6 + 3x2 days after
        self.assertEqual(first.inputs["weights"], [3, 2])

        # A new order delivered by the dispatcher today
        o = self._order(self.reyes, self.home, self.today, status=Order.Status.OUT_FOR_DELIVERY)
        dispatch_services.mark_delivered(o, self.disp, empties_collected=3)

        first.refresh_from_db()
        self.assertFalse(first.is_current)
        self.assertEqual(first.actual_order_id, o.pk)                       # for accuracy reporting
        now = RefillPrediction.objects.get(is_current=True)
        self.assertEqual(now.last_delivery_date, self.today)
        self.assertEqual(now.predicted_runout_date, self.today + timedelta(days=6))

    def test_rider_delivery_refreshes_prediction(self):
        from apps.delivery.services import record_attempt
        from apps.delivery.models import DeliveryAttempt
        self._history(self.reyes, self.home, [18, 12, 6])
        o = self._order(self.reyes, self.home, self.today, status=Order.Status.OUT_FOR_DELIVERY)
        record_attempt(o, self.rider, DeliveryAttempt.Outcome.DELIVERED, device_time=timezone.now(),
                       code=o.confirmation_code, gps_lat=13.4120, gps_lng=121.1800)
        self.assertEqual(RefillPrediction.objects.filter(customer=self.reyes).count(), 2)
        self.assertEqual(RefillPrediction.objects.get(is_current=True).last_delivery_date, self.today)

    def test_rebuild_command(self):
        for n in (18, 12, 6):
            self._order(self.reyes, self.home, self.today - timedelta(days=n))
        other, addr = self._customer("cruz")
        self._order(other, addr, self.today - timedelta(days=3))
        out = StringIO()
        call_command("rebuild_refill_predictions", stdout=out)
        self.assertIn("1 household(s) predicted, 1 without enough history", out.getvalue())


class ReminderTest(Base):
    def test_reminder_two_days_before_runout(self):
        p = self._history(self.reyes, self.home, [16, 10, 4])               # runs out in 2 days
        self.assertEqual(p.predicted_runout_date, self.today + timedelta(days=2))
        self.assertEqual(services.due_reminders(self.today - timedelta(days=1)), [])  # 3 days before: not yet

        out = StringIO()
        call_command("send_refill_reminders", stdout=out)
        self.assertIn("1 household(s) reminded", out.getvalue())
        self.assertEqual(set(ReminderLog.objects.values_list("channel", flat=True)), {"in_app", "email"})
        mail = EmailLog.objects.get()
        self.assertEqual(mail.template, "refill_reminder")
        self.assertEqual(mail.context["quantity"], 3)
        self.assertTrue(mail.context["reorder_url"].endswith(f"/customer/home?reorder={p.pk}"))

        # Running again the same day (or the next) sends nothing new
        call_command("send_refill_reminders", stdout=StringIO())
        self.assertEqual(ReminderLog.objects.count(), 2)
        self.assertEqual(EmailLog.objects.count(), 1)

    def test_missed_day_is_caught_up_but_never_after_runout(self):
        p = self._history(self.reyes, self.home, [17, 11, 5])               # runs out tomorrow
        self.assertEqual(p.predicted_runout_date, self.today + timedelta(days=1))
        self.assertEqual(services.due_reminders(), [p])
        self.assertEqual(services.due_reminders(self.today + timedelta(days=2)), [])

    def test_respects_reminders_enabled_and_open_orders(self):
        self._history(self.reyes, self.home, [16, 10, 4])
        quiet, qa = self._customer("quiet", reminders=False)
        self._history(quiet, qa, [16, 10, 4])
        busy, ba = self._customer("busy")
        self._history(busy, ba, [16, 10, 4])
        self._order(busy, ba, self.today + timedelta(days=1), status=Order.Status.PENDING)
        self.assertEqual([p.customer for p in services.due_reminders()], [self.reyes])

    def test_no_email_address_still_gets_in_app(self):
        u, a = self._customer("noemail", email=False)
        p = self._history(u, a, [16, 10, 4])
        self.assertEqual(services.send_reminder(p), ["in_app"])
        self.assertFalse(EmailLog.objects.exists())


class CustomerApiTest(Base):
    def test_home_card_not_enough_history(self):
        self._history(self.reyes, self.home, [6])
        self.client.force_authenticate(self.reyes)
        r = self.client.get("/api/customer/refill/")
        self.assertEqual(r.status_code, 200)
        card = r.data["households"][0]
        self.assertEqual(card["state"], "not_enough_history")
        self.assertEqual((card["orders_counted"], card["orders_needed"]), (1, 3))

    def test_home_card_with_prediction(self):
        p = self._history(self.reyes, self.home, [16, 10, 4])
        services.send_reminder(p)
        self.client.force_authenticate(self.reyes)
        card = self.client.get("/api/customer/refill/").data["households"][0]
        self.assertEqual(card["state"], "ok")
        self.assertEqual(card["days_left"], 2)
        self.assertEqual(card["days_per_container"], 2.0)
        self.assertEqual(card["reorder"]["quantity"], 3)
        self.assertEqual(card["reorder"]["total"], 90.0)
        self.assertIsNotNone(card["reminder_sent_at"])

    def test_only_customers_and_only_their_own(self):
        self.client.force_authenticate(self.disp)
        self.assertEqual(self.client.get("/api/customer/refill/").status_code, 403)
        p = self._history(self.reyes, self.home, [16, 10, 4])
        other, _ = self._customer("other")
        self.client.force_authenticate(other)
        r = self.client.post("/api/customer/refill/reorder/", {"prediction": p.pk}, format="json")
        self.assertEqual(r.status_code, 404)

    def test_one_tap_reorder(self):
        p = self._history(self.reyes, self.home, [16, 10, 4])
        services.send_reminder(p)
        self.client.force_authenticate(self.reyes)
        tomorrow = (self.today + timedelta(days=1)).isoformat()
        r = self.client.post("/api/customer/refill/reorder/",
                             {"prediction": p.pk, "delivery_date": tomorrow, "period": "morning"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        order = Order.objects.get(pk=r.data["id"])
        self.assertEqual(order.source, Order.Source.REMINDER_REORDER)
        self.assertEqual((order.containers, order.address_id), (3, self.home.pk))
        self.assertEqual(set(ReminderLog.objects.values_list("reordered_order", flat=True)), {order.pk})

        # A second tap does not order twice
        r = self.client.post("/api/customer/refill/reorder/", {"prediction": p.pk}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("already have an order", str(r.data))

        # ...and the home card now points at the order in progress
        card = self.client.get("/api/customer/refill/").data["households"][0]
        self.assertEqual(card["open_order"]["id"], order.pk)

    def test_reorder_without_slot_picks_the_earliest_open_one(self):
        p = self._history(self.reyes, self.home, [16, 10, 4])
        self.client.force_authenticate(self.reyes)
        r = self.client.post("/api/customer/refill/reorder/", {"prediction": p.pk}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        day, period = services.earliest_slot()
        self.assertEqual((r.data["delivery_date"], r.data["period"]), (day.isoformat(), period))


class StaffApiTest(Base):
    def test_demand_counts_confirmed_plus_predicted_without_open_orders(self):
        tomorrow = self.today + timedelta(days=1)
        # Reyes: runs out tomorrow, no order -> 3 predicted tomorrow
        self._history(self.reyes, self.home, [17, 11, 5])
        # Cruz: runs out tomorrow but already has a confirmed order -> counted once, as confirmed
        cruz, ca = self._customer("cruz")
        self._history(cruz, ca, [17, 11, 5], qty=2)
        self._order(cruz, ca, tomorrow, qty=4, status=Order.Status.CONFIRMED)
        # Santos: ran out 3 days ago, never reordered -> expected today
        santos, sa = self._customer("santos")
        self._history(santos, sa, [21, 15, 9], qty=4)                       # 1.5 d/container -> ran out 3 days ago
        # Lapsed: ran out long ago -> not expected
        gone, ga = self._customer("gone")
        self._history(gone, ga, [60, 54, 48])
        # A pending order tomorrow: shown, not counted
        new, na = self._customer("newbie")
        self._order(new, na, tomorrow, qty=2, status=Order.Status.PENDING)

        self.client.force_authenticate(self.disp)
        r = self.client.get("/api/v1/dispatch/demand?days=3")
        self.assertEqual(r.status_code, 200)
        today_row, tom_row, _ = r.data["days"]

        self.assertEqual(today_row["predicted"], 4)
        self.assertEqual(today_row["households"][0]["overdue_days"], 3)
        self.assertEqual((tom_row["confirmed"], tom_row["predicted"], tom_row["pending"]), (4, 3, 2))
        self.assertEqual(tom_row["expected"], 7)
        self.assertEqual([h["customer"] for h in tom_row["households"]], ["Reyes Family"])
        self.assertEqual(r.data["ready_stock"], 40)
        self.assertEqual(r.data["days"][-1]["prepare"], max(0, r.data["days"][-1]["cumulative_expected"] - 40))

    def test_prepare_suggestion(self):
        self._history(self.reyes, self.home, [17, 11, 5])
        StockLevel.objects.filter(product=self.refill).update(filled_available=1, filled_reserved=0)
        day = services.demand(days=2)["days"][1]
        self.assertEqual(day["prepare"], 2)                                 # 3 expected, 1 ready

    def test_backtest(self):
        # Every 6 days with 3 containers: perfectly regular -> error 0
        self._history(self.reyes, self.home, [30, 24, 18, 12, 6])
        # Irregular household: 3 containers on day -30, -24, -18, then -9 (3 days late)
        cruz, ca = self._customer("cruz")
        self._history(cruz, ca, [30, 24, 18, 9])
        self.client.force_authenticate(self.owner)
        r = self.client.get("/api/v1/dispatch/refill-accuracy?days=0")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["predictions"], 3)                           # reyes 2, cruz 1
        self.assertEqual(r.data["households"], 2)
        self.assertEqual(r.data["mean_abs_error"], 1.0)                      # (0 + 0 + 3) / 3
        self.assertEqual(r.data["mean_error"], 1.0)
        self.assertEqual(r.data["within_1_day"], 0.6667)
        self.assertEqual(r.data["per_household"][0]["customer"], "Cruz Family")
        self.assertEqual(sum(b["count"] for b in r.data["histogram"]), 3)

    def test_backtest_window_and_permissions(self):
        self._history(self.reyes, self.home, [30, 24, 18, 12, 6])
        self.client.force_authenticate(self.owner)
        r = self.client.get("/api/v1/dispatch/refill-accuracy?days=10")
        self.assertEqual(r.data["predictions"], 1)                           # only the order 6 days ago
        self.client.force_authenticate(self.reyes)
        self.assertEqual(self.client.get("/api/v1/dispatch/refill-accuracy").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/dispatch/demand").status_code, 403)
