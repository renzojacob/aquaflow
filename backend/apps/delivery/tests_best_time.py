"""
Feature E: best time to deliver.
Run:  python manage.py test apps.delivery.tests_best_time
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import CustomerProfile, User
from apps.customers.models import Address
from apps.delivery.best_time import best_period
from apps.delivery.models import DeliveryAttempt
from apps.inventory.models import Product
from apps.orders.models import Order
from apps.station.models import Station, SystemSetting

PW = "Water2026!x"
D, F = DeliveryAttempt.Outcome.DELIVERED, DeliveryAttempt.Outcome.FAILED


class BestTimeBase(APITestCase):
    def setUp(self):
        self.refill = Product.objects.create(name="5-gallon refill", price=30, kind="refill", sort_order=1)
        self.rider = User.objects.create_user("r@t.ph", "r@t.ph", PW, role="rider")
        self.cust, self.addr = self.customer("ana")
        self.clock = timezone.now() - timedelta(days=200)

    def customer(self, name):
        u = User.objects.create_user(f"{name}@t.ph", f"{name}@t.ph", PW, role="customer")
        CustomerProfile.objects.create(user=u)
        a = Address.objects.create(customer=u, label="Home", address_text="Purok 1", barangay="Lalud",
                                   lat=13.41, lng=121.18, is_default=True)
        return u, a

    def history(self, period, outcomes, reason="absent", address=None):
        """One past order + attempt per outcome, oldest first, a day apart."""
        address = address or self.addr
        for outcome in outcomes:
            self.clock += timedelta(days=1)
            o = Order.objects.create(customer=address.customer, address=address, product=self.refill, quantity=1,
                                     containers=1, delivery_date=self.clock.date(), period=period,
                                     status="delivered" if outcome == D else "failed")
            att = DeliveryAttempt.objects.create(order=o, rider=self.rider, outcome=outcome,
                                                 failure_reason="" if outcome == D else reason,
                                                 device_time=self.clock)
            DeliveryAttempt.objects.filter(pk=att.pk).update(server_time=self.clock)


class SuggestionRules(BestTimeBase):
    def test_spec_example_suggests_afternoon(self):
        self.history("morning", [F, D, F, F])            # failed 3 of 4 mornings
        self.history("afternoon", [D, D, D])             # every afternoon worked
        s = best_period(self.addr.pk)
        self.assertEqual((s["period"], s["basis"]), ("afternoon", "compared"))
        self.assertEqual(s["stats"]["morning"], {"attempts": 4, "delivered": 1})
        self.assertEqual(s["summary"], "3 of 3 afternoon deliveries worked here, but only 1 of 4 morning deliveries.")

    def test_needs_at_least_four_attempts(self):
        self.history("morning", [F, F])
        self.history("afternoon", [D])
        self.assertIsNone(best_period(self.addr.pk))
        s = SystemSetting.load()
        s.best_time_min_attempts = 3
        s.save()
        self.assertEqual(best_period(self.addr.pk)["period"], "afternoon")

    def test_small_difference_is_not_a_suggestion(self):
        self.history("morning", [D, F, D, F])            # 50%
        self.history("afternoon", [D, D, D, F])          # 75%
        self.assertIsNone(best_period(self.addr.pk))

    def test_failures_unrelated_to_time_are_not_counted(self):
        self.history("morning", [F, F, F], reason="wrong_address")
        self.history("morning", [F], reason="refused")
        self.history("afternoon", [D])
        self.assertIsNone(best_period(self.addr.pk))     # only 1 attempt counts

    def test_period_never_tried_is_suggested_when_the_other_keeps_failing(self):
        self.history("morning", [F, D, F, F])
        s = best_period(self.addr.pk)
        self.assertEqual((s["period"], s["basis"]), ("afternoon", "untried"))
        self.assertIn("Afternoon hasn't been tried yet", s["summary"])

    def test_untried_period_is_not_suggested_when_the_tried_one_mostly_works(self):
        self.history("morning", [F, D, D, F])
        self.assertIsNone(best_period(self.addr.pk))

    def test_only_recent_attempts_count(self):
        self.history("morning", [F] * 10)                # long ago: never home in the morning
        self.history("afternoon", [D] * 10)
        self.history("morning", [D] * 10)                # lately: home every morning
        self.history("afternoon", [D] * 10)
        self.assertIsNone(best_period(self.addr.pk))

    def test_each_address_has_its_own_history(self):
        _, shop = self.customer("shop")
        self.history("morning", [F, F, F, F], address=shop)
        self.assertIsNone(best_period(self.addr.pk))
        self.assertEqual(best_period(shop.pk)["period"], "afternoon")


class WhereItShows(BestTimeBase):
    def setUp(self):
        super().setUp()
        self.history("morning", [F, D, F, F])
        self.history("afternoon", [D, D, D])
        self.dispatcher = User.objects.create_user("d@t.ph", "d@t.ph", PW, role="dispatcher")
        Station.objects.create(name="AquaFlow", lat=13.4117, lng=121.1803)

    def test_order_form_gets_the_suggestion_for_its_own_address_only(self):
        self.client.force_authenticate(self.cust)
        r = self.client.get("/api/customer/slots/", {"address": self.addr.id})
        self.assertEqual(r.data["best_time"]["period"], "afternoon")
        self.assertEqual(self.client.get("/api/customer/slots/").data["best_time"], None)
        other, other_addr = self.customer("ben")
        self.history("morning", [F, F, F, F], address=other_addr)
        r = self.client.get("/api/customer/slots/", {"address": other_addr.id})   # not ana's
        self.assertIsNone(r.data["best_time"])

    def test_planner_flags_orders_booked_for_the_worse_period(self):
        day = timezone.localdate() + timedelta(days=1)
        morning = Order.objects.create(customer=self.cust, address=self.addr, product=self.refill, quantity=2,
                                       containers=2, delivery_date=day, period="morning", status="confirmed")
        self.client.force_authenticate(self.dispatcher)
        r = self.client.get("/api/v1/dispatch/trips", {"date": day.isoformat(), "period": "morning"})
        o = next(x for x in r.data["unplanned"] if x["order_id"] == morning.pk)
        self.assertEqual(o["better_period"]["period"], "afternoon")
        self.assertIn("1 of 4 morning", o["better_period"]["summary"])

        morning.period = "afternoon"                     # already in the good period: nothing to say
        morning.save()
        r = self.client.get("/api/v1/dispatch/trips", {"date": day.isoformat(), "period": "afternoon"})
        self.assertIsNone(r.data["unplanned"][0]["better_period"])

    def test_trip_stops_carry_the_hint(self):
        from apps.dispatch.models import Trip, TripStop, Vehicle
        day = timezone.localdate() + timedelta(days=1)
        o = Order.objects.create(customer=self.cust, address=self.addr, product=self.refill, quantity=2,
                                 containers=2, delivery_date=day, period="morning", status="confirmed")
        t = Trip.objects.create(date=day, period="morning",
                                vehicle=Vehicle.objects.create(name="T1", plate="T1", capacity_containers=10))
        TripStop.objects.create(trip=t, order=o, sequence=1)
        self.client.force_authenticate(self.dispatcher)
        r = self.client.get(f"/api/v1/dispatch/trips/{t.pk}")
        self.assertEqual(r.data["stops"][0]["better_period"]["period"], "afternoon")
