"""
GET /api/v1/dispatch/forecast, plus the trips hint and the plain-English explanation.
Run:  python manage.py test apps.dispatch.tests_forecast_api
"""
from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import CustomerProfile, User
from apps.customers.models import Address
from apps.dispatch import forecasting as fc
from apps.dispatch.management.commands.seed_forecast_demo import MARK
from apps.dispatch.models import Vehicle
from apps.inventory.models import Product
from apps.orders.models import Order

URL = "/api/v1/dispatch/forecast"
PW = "Water2026!x"
WEEK = [10, 12, 9, 11, 15, 20, 8]


def day(k, start="2026-01-05", containers=None):
    from datetime import date
    return fc.ForecastDay((date.fromisoformat(start) + timedelta(days=k)).isoformat(), *containers)


class ApiBase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user("o@t.com", "o@t.com", PW, role="owner")
        self.dispatcher = User.objects.create_user("d@t.com", "d@t.com", PW, role="dispatcher")
        self.rider = User.objects.create_user("r@t.com", "r@t.com", PW, role="rider")
        self.customer = User.objects.create_user("c@t.com", "c@t.com", PW, role="customer")
        CustomerProfile.objects.create(user=self.customer)
        self.addr = Address.objects.create(customer=self.customer, label="Home", address_text="Street 1",
                                           barangay="Lalud", lat=13.41, lng=121.18, is_default=True)
        self.product = Product.objects.create(name="5-gallon refill", price=30, kind="refill")
        self.today = timezone.localdate()

    def as_(self, user):
        self.client.force_authenticate(user)
        return self.client

    def orders_per_day(self, counts, containers=2, status="delivered", notes=""):
        """counts: {date: how many orders}. Written in bulk, with what Order.save() normally fills in."""
        rows = [Order(customer=self.customer, address=self.addr, product=self.product, quantity=containers,
                      containers=containers, delivery_date=d, period="morning", status=status, notes=notes,
                      lat=self.addr.lat, lng=self.addr.lng, address_text="Street 1", unit_price=30,
                      total=30 * containers, confirmation_code="000000", code_salt="x")
                for d, n in counts.items() for _ in range(n)]
        Order.objects.bulk_create(rows)

    def history(self, days, pattern=WEEK, **kw):
        """`days` days ending yesterday, following a weekly pattern."""
        start = self.today - timedelta(days=days)
        self.orders_per_day({start + timedelta(days=i): pattern[i % 7] for i in range(days)}, **kw)

    def get(self, query="", user=None):
        return self.as_(user or self.owner).get(URL + query)


class PermissionTests(ApiBase):
    def test_owner_and_dispatcher_may_read_it(self):
        self.assertEqual(self.get(user=self.owner).status_code, 200)
        self.assertEqual(self.get(user=self.dispatcher).status_code, 200)

    def test_customer_and_rider_are_refused(self):
        self.assertEqual(self.get(user=self.customer).status_code, 403)
        self.assertEqual(self.get(user=self.rider).status_code, 403)

    def test_anonymous_is_refused(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(URL).status_code, (401, 403))


class DaysParameterTests(ApiBase):
    def setUp(self):
        super().setUp()
        self.history(56)

    def test_default_is_seven_days(self):
        r = self.get().data
        self.assertEqual(r["days"], 7)
        self.assertEqual(len(r["orders"]["days"]), 7)
        self.assertEqual(len(r["containers"]["days"]), 7)

    def test_fourteen_days(self):
        r = self.get("?days=14").data
        self.assertEqual(r["days"], 14)
        self.assertEqual(len(r["orders"]["days"]), 14)
        self.assertEqual(r["orders"]["days"][0]["date"], self.today.isoformat())
        self.assertEqual(r["orders"]["days"][-1]["date"], (self.today + timedelta(days=13)).isoformat())

    def test_seven_and_fourteen_share_the_same_first_week(self):
        a, b = self.get("?days=7").data, self.get("?days=14").data
        self.assertEqual([d["value"] for d in a["orders"]["days"]], [d["value"] for d in b["orders"]["days"][:7]])

    def test_anything_else_is_a_400(self):
        for bad in ("5", "0", "15", "-7", "abc", "", "7.0", "7 "):
            r = self.get(f"?days={bad}")
            self.assertEqual(r.status_code, 400, bad)
            self.assertEqual(r.data["days"], ["Use 7 or 14."])


class EmptyTableTests(ApiBase):
    def test_no_orders_is_a_calm_200(self):
        r = self.get()
        self.assertEqual(r.status_code, 200)
        d = r.data
        self.assertFalse(d["enough_data"])
        self.assertEqual(d["orders"]["days"], [])
        self.assertEqual(d["containers"]["days"], [])
        self.assertEqual(d["history"], {"start": None, "end": None, "orders": [], "containers": []})
        self.assertIsNone(d["orders"]["method"])
        self.assertIsNone(d["trips"])
        self.assertIn("nothing to forecast", d["explanation"])
        self.assertTrue(d["warnings"])

    def test_only_invalid_orders_counts_as_empty(self):
        self.orders_per_day({self.today - timedelta(days=2): 3}, status="cancelled")
        self.assertEqual(self.get().data["orders"]["days"], [])


class NotEnoughDataTests(ApiBase):
    def test_ten_days_falls_back_to_the_weekday_average(self):
        self.history(10)
        d = self.get().data
        self.assertFalse(d["enough_data"])
        self.assertFalse(d["orders"]["enough_data"])
        self.assertEqual(d["orders"]["method"], "weekday_average")
        self.assertEqual(d["orders"]["backtest"], [])
        self.assertEqual(len(d["orders"]["days"]), 7)
        for f in d["orders"]["days"]:
            self.assertIsNone(f["lower"])
            self.assertIsNone(f["upper"])
        self.assertEqual(len(d["history"]["orders"]), 10)
        self.assertTrue(any("28" in w for w in d["warnings"]))
        self.assertIn("rough", d["explanation"])
        self.assertIn("10 days", d["explanation"])


class ResponseShapeTests(ApiBase):
    def setUp(self):
        super().setUp()
        self.history(56)
        Vehicle.objects.create(name="T1", plate="T1", capacity_containers=10)
        Vehicle.objects.create(name="T2", plate="T2", capacity_containers=20)

    def test_top_level_keys(self):
        d = self.get().data
        self.assertEqual(set(d), {"days", "generated_on", "timezone", "enough_data", "history", "orders",
                                  "containers", "warnings", "trips", "explanation"})
        self.assertEqual(d["timezone"], "Asia/Manila")
        self.assertEqual(d["generated_on"], self.today.isoformat())
        self.assertIsInstance(d["explanation"], str)
        self.assertIsInstance(d["warnings"], list)

    def test_history_is_the_last_28_days_ending_yesterday(self):
        h = self.get().data["history"]
        self.assertEqual(len(h["orders"]), 28)
        self.assertEqual(len(h["containers"]), 28)
        self.assertEqual(h["end"], (self.today - timedelta(days=1)).isoformat())
        self.assertEqual(h["start"], (self.today - timedelta(days=28)).isoformat())
        self.assertEqual(set(h["orders"][0]), {"date", "value"})
        self.assertEqual([x["value"] for x in h["orders"][:7]], [WEEK[(28 + i) % 7] for i in range(7)])
        self.assertEqual(h["containers"][0]["value"], 2 * h["orders"][0]["value"])      # 2 containers per order

    def test_forecast_block(self):
        o = self.get().data["orders"]
        self.assertEqual(set(o), {"method", "method_label", "enough_data", "history_days", "horizon",
                                  "days", "backtest", "backtest_rounds", "interval_level",
                                  "holt_winters_params"})
        self.assertEqual(o["history_days"], 56)
        self.assertEqual(o["interval_level"], 0.8)
        for f in o["days"]:
            self.assertEqual(set(f), {"date", "value", "lower", "upper"})
            self.assertLessEqual(f["lower"], f["value"])
            self.assertLessEqual(f["value"], f["upper"])
            self.assertGreaterEqual(f["lower"], 0)

    def test_backtest_table(self):
        o = self.get().data["orders"]
        self.assertEqual([r["method"] for r in o["backtest"]], ["naive", "weekday_average", "holt_winters"])
        self.assertEqual(sum(1 for r in o["backtest"] if r["chosen"]), 1)
        self.assertEqual(next(r["method"] for r in o["backtest"] if r["chosen"]), o["method"])
        for r in o["backtest"]:
            self.assertEqual(set(r), {"method", "label", "chosen", "mae", "rmse", "wape"})
        self.assertEqual(o["method"], "weekday_average")                  # a pure weekly pattern
        self.assertEqual([f["value"] for f in o["days"]],
                         [float(WEEK[(56 + i) % 7]) for i in range(7)])

    def test_containers_follow_orders(self):
        d = self.get().data
        for a, b in zip(d["orders"]["days"], d["containers"]["days"]):
            self.assertEqual(a["date"], b["date"])
            self.assertAlmostEqual(b["value"], 2 * a["value"], places=1)

    def test_it_is_in_the_api_schema(self):
        r = self.client.get("/api/schema/")
        if r.status_code == 200:
            self.assertIn("/api/v1/dispatch/forecast", r.content.decode())


class TripsOnTheEndpointTests(ApiBase):
    def setUp(self):
        super().setUp()
        self.history(56, pattern=[10] * 7)                    # 10 orders x 2 containers = 20 a day, flat

    def test_no_vehicles_means_no_estimate(self):
        d = self.get().data
        self.assertIsNone(d["trips"])
        self.assertIn("Add your vehicles", d["explanation"])

    def test_uses_available_vehicles_only(self):
        Vehicle.objects.create(name="T1", plate="T1", capacity_containers=10)
        Vehicle.objects.create(name="T2", plate="T2", capacity_containers=20)
        Vehicle.objects.create(name="Broken", plate="T3", capacity_containers=50, is_available=False)
        t = self.get().data["trips"]
        self.assertEqual(t["vehicles"], 2)
        self.assertEqual(t["total_capacity"], 30)
        self.assertEqual(t["average_capacity"], 15.0)
        self.assertEqual(t["fleet_trips_per_day"], 4)
        self.assertEqual(len(t["days"]), 7)
        self.assertEqual(t["days"][0]["containers"], 20.0)
        self.assertEqual((t["days"][0]["trips_needed"], t["days"][0]["riders_needed"]), (2, 1))   # ceil(20/15)
        self.assertIn("Rough planning number", t["note"])
        self.assertEqual(t["over_capacity_days"], [])


class DemoWarningTests(ApiBase):
    def test_demo_orders_are_called_out(self):
        self.history(56, notes=MARK)
        self.assertTrue(any("DEMO" in w for w in self.get().data["warnings"]))

    def test_real_history_has_no_demo_warning(self):
        self.history(56)
        self.assertFalse(any("DEMO" in w for w in self.get().data["warnings"]))


class TripsHintTests(SimpleTestCase):
    days = [day(0, containers=(30.0, 25.0, 41.0)), day(1, containers=(14.0, 10.0, 19.0)),
            day(2, containers=(70.0, 60.0, 90.0))]

    def test_known_numbers(self):
        t = fc.trips_hint(self.days, [10, 20])                    # average capacity 15, 4 trips a day
        self.assertEqual((t["vehicles"], t["total_capacity"], t["average_capacity"]), (2, 30, 15.0))
        self.assertEqual(t["fleet_trips_per_day"], 4)
        a, b, c = t["days"]
        self.assertEqual((a["trips_needed"], a["riders_needed"]), (2, 1))              # 30 / 15
        self.assertEqual((a["busy_trips_needed"], a["busy_riders_needed"]), (3, 2))    # 41 / 15 -> 3
        self.assertEqual((b["trips_needed"], b["riders_needed"]), (1, 1))              # 14 / 15 -> 1
        self.assertEqual((c["trips_needed"], c["busy_trips_needed"]), (5, 6))
        self.assertTrue(a["fleet_enough"])
        self.assertFalse(c["fleet_enough"])                                            # 6 trips > 4
        self.assertEqual(t["over_capacity_days"], [c["date"]])
        self.assertEqual(t["peak_date"], c["date"])

    def test_no_bounds_means_busy_equals_expected(self):
        t = fc.trips_hint([day(0, containers=(30.0, None, None))], [15])
        self.assertEqual(t["days"][0]["busy_trips_needed"], t["days"][0]["trips_needed"])

    def test_zero_containers_need_no_trip(self):
        t = fc.trips_hint([day(0, containers=(0.0, 0.0, 0.0))], [10])
        self.assertEqual(t["days"][0]["trips_needed"], 0)
        self.assertEqual(t["days"][0]["riders_needed"], 0)

    def test_no_usable_vehicle(self):
        self.assertIsNone(fc.trips_hint(self.days, []))
        self.assertIsNone(fc.trips_hint(self.days, [0, None]))


class ExplanationTests(SimpleTestCase):
    def forecast(self, y, horizon=7):
        from datetime import date
        return fc.forecast_series(y, date(2026, 1, 5), horizon)

    def test_normal_case_names_the_busiest_day_and_the_plan(self):
        orders, boxes = self.forecast(WEEK * 8), self.forecast([2 * v for v in WEEK * 8])
        trips = fc.trips_hint(boxes.days, [10, 20])
        text = fc.explain(orders, boxes, trips, 7)
        self.assertIn("Expect about 20 orders (40 containers) on", text)        # the busiest day of the pattern
        self.assertIn("busiest day in the next 7 days", text)
        self.assertIn("On that day plan about 3 trips and 2 riders", text)       # 40 / 15 -> 3
        self.assertIn("In all, about 85 orders over the next 7 days", text)
        self.assertIn("The weekday average was chosen", text)
        self.assertIn("off by about 0%", text)

    def test_short_history_says_it_is_a_guess(self):
        f = self.forecast([5] * 12)
        text = fc.explain(f, f, None, 7)
        self.assertIn("only 12 days", text)
        self.assertIn("rough", text)
        self.assertNotIn("was chosen", text)

    def test_empty_history(self):
        f = self.forecast([])
        self.assertIn("nothing to forecast", fc.explain(f, f, None, 7))
