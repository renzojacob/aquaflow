"""
Demand forecasting: the math, the data loader and the demo seeder.
Run:  python manage.py test apps.dispatch.tests_forecasting
"""
import math
from datetime import date, timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.accounts.models import CustomerProfile, User
from apps.customers.models import Address
from apps.dispatch import forecasting as fc
from apps.dispatch.management.commands import seed_forecast_demo as demo
from apps.inventory.models import Product
from apps.orders.models import Order

MONDAY = date(2026, 1, 5)
WEEK = [10, 12, 9, 11, 15, 20, 8]


def table(result):
    return {row["method"]: row for row in result.backtest}


class ErrorMetricTests(SimpleTestCase):
    def test_hand_computed_case(self):
        m = fc.error_metrics([10, 20], [12, 17])        # errors: -2 and +3
        self.assertAlmostEqual(m["mae"], 2.5)
        self.assertAlmostEqual(m["rmse"], math.sqrt((4 + 9) / 2))
        self.assertAlmostEqual(m["wape"], 5 / 30)

    def test_wape_is_undefined_when_nothing_was_ordered(self):
        m = fc.error_metrics([0, 0, 0], [1, 0, 2])
        self.assertIsNone(m["wape"])
        self.assertAlmostEqual(m["mae"], 1.0)

    def test_perfect_forecast_has_no_error(self):
        self.assertEqual(fc.error_metrics([3, 4], [3, 4]), {"mae": 0.0, "rmse": 0.0, "wape": 0.0})


class MethodTests(SimpleTestCase):
    def test_naive_repeats_the_last_day(self):
        self.assertEqual(fc.naive([1, 2, 9], 3), [9.0, 9.0, 9.0])

    def test_weekday_average_follows_the_weekday(self):
        y = WEEK * 6
        self.assertEqual(fc.weekday_average(y, 14), [float(v) for v in WEEK * 2])

    def test_weekday_average_uses_only_the_last_four_weeks(self):
        old, recent = [100] * 7 * 4, WEEK * 4
        self.assertEqual(fc.weekday_average(old + recent, 7), [float(v) for v in WEEK])

    def test_holt_winters_picks_parameters_from_the_grid(self):
        a, b, g = fc.holt_winters_params([WEEK[i % 7] + i * 0.1 for i in range(56)])
        self.assertIn(a, fc.ALPHAS)
        self.assertIn(b, fc.BETAS)
        self.assertIn(g, fc.GAMMAS)

    def test_holt_winters_never_forecasts_below_zero(self):
        y = [max(0, 30 - 2 * t) for t in range(40)]          # falling fast
        self.assertTrue(all(v >= 0 for v in fc.holt_winters(y, 14)))

    def test_holt_winters_with_under_two_weeks_uses_the_weekday_average(self):
        y = [4, 5, 6, 7, 8, 9, 10, 4, 5]
        self.assertEqual(fc.holt_winters(y, 3), fc.weekday_average(y, 3))


class BacktestTests(SimpleTestCase):
    def test_rounds_are_expanding_and_weekly(self):
        pooled = fc.backtest([5] * 56)             # origins at day 21, 28, 35, 42, 49
        self.assertEqual(len(pooled["naive"]["actual"]), 5 * fc.HORIZON)
        self.assertEqual(set(pooled), set(fc.METHODS))

    def test_a_round_never_sees_the_days_it_is_scored_on(self):
        y = [1] * 28 + [1000] * 7                  # one huge week at the very end
        pooled = fc.backtest(y)
        last = fc.HORIZON
        self.assertEqual(pooled["naive"]["actual"][-last:], [1000] * last)
        self.assertEqual(pooled["naive"]["predicted"][-last:], [1.0] * last)

    def test_a_remainder_shorter_than_the_horizon_is_ignored(self):
        self.assertEqual(len(fc.backtest([5] * 30)["naive"]["actual"]), fc.HORIZON)


class KnownSeriesTests(SimpleTestCase):
    def run_series(self, y, horizon=7):
        return fc.forecast_series(y, MONDAY, horizon)

    def test_constant_series(self):
        r = self.run_series([10] * 56)
        self.assertTrue(r.enough_data)
        self.assertEqual(r.method, "naive")                      # all tie at 0 error: simplest wins
        for row in r.backtest:
            self.assertEqual((row["mae"], row["rmse"], row["wape"]), (0.0, 0.0, 0.0))
        for d in r.days:
            self.assertEqual((d.value, d.lower, d.upper), (10.0, 10.0, 10.0))

    def test_pure_weekly_pattern(self):
        r = self.run_series(WEEK * 8)
        t = table(r)
        self.assertEqual(r.method, "weekday_average")            # ties Holt-Winters at 0, and is simpler
        self.assertAlmostEqual(t["weekday_average"]["wape"], 0.0, places=6)
        self.assertAlmostEqual(t["holt_winters"]["wape"], 0.0, places=6)
        self.assertGreater(t["naive"]["wape"], 0.2)
        self.assertEqual([d.value for d in r.days], [float(v) for v in WEEK])

    def test_linear_trend_goes_to_holt_winters(self):
        r = self.run_series([10 + 0.5 * t for t in range(56)])
        t = table(r)
        self.assertEqual(r.method, "holt_winters")
        self.assertLess(t["holt_winters"]["wape"], t["weekday_average"]["wape"])
        self.assertLess(t["holt_winters"]["wape"], t["naive"]["wape"])
        self.assertAlmostEqual(r.days[0].value, 10 + 0.5 * 56, places=1)
        self.assertAlmostEqual(r.days[6].value, 10 + 0.5 * 62, places=1)
        self.assertIsNotNone(r.holt_winters_params)

    def test_trend_plus_weekly_pattern(self):
        y = [10 + 0.5 * t + [0, 1, -1, 0, 3, 5, -2][t % 7] for t in range(56)]
        r = self.run_series(y)
        self.assertEqual(r.method, "holt_winters")
        self.assertAlmostEqual(table(r)["holt_winters"]["wape"], 0.0, places=6)

    def test_forecast_dates_start_the_day_after_the_history(self):
        r = self.run_series([10] * 56)
        self.assertEqual(r.days[0].date, (MONDAY + timedelta(days=56)).isoformat())
        self.assertEqual(len(self.run_series([10] * 56, horizon=14).days), 14)


class NotEnoughDataTests(SimpleTestCase):
    def test_under_four_weeks_falls_back_with_a_flag(self):
        r = fc.forecast_series((WEEK * 3)[:20], MONDAY, 7)
        self.assertFalse(r.enough_data)
        self.assertEqual(r.method, "weekday_average")
        self.assertEqual(r.backtest, [])
        self.assertIsNone(r.interval_level)
        self.assertEqual(len(r.days), 7)
        self.assertTrue(all(d.lower is None and d.upper is None for d in r.days))
        self.assertTrue(any("28" in w for w in r.warnings))

    def test_exactly_four_weeks_is_enough(self):
        r = fc.forecast_series(WEEK * 4, MONDAY, 7)
        self.assertTrue(r.enough_data)
        self.assertEqual(r.backtest_rounds, 1)

    def test_no_history_at_all(self):
        r = fc.forecast_series([], None, 7)
        self.assertFalse(r.enough_data)
        self.assertEqual(r.days, [])
        self.assertTrue(r.warnings)


class IntervalTests(SimpleTestCase):
    noisy = [round(10 + 0.1 * t + [0, 1, -1, 0, 3, 5, -2][t % 7] + (3 if t % 5 == 0 else -2 if t % 4 == 0 else 0))
             for t in range(70)]

    def test_band_contains_the_forecast_and_stays_above_zero(self):
        r = fc.forecast_series(self.noisy, MONDAY, 14)
        self.assertEqual(r.interval_level, 0.8)
        for d in r.days:
            self.assertGreaterEqual(d.lower, 0)
            self.assertLessEqual(d.lower, d.value)
            self.assertGreaterEqual(d.upper, d.value)

    def test_band_widens_beyond_one_week(self):
        r = fc.forecast_series(self.noisy, MONDAY, 14)
        width = [d.upper - d.lower for d in r.days]
        self.assertGreater(width[13], width[6])
        self.assertEqual(round(width[0], 2), round(width[6], 2))

    def test_offsets_always_bracket_zero(self):
        low, high = fc.interval_offsets([5, 6, 7] * 5, [1, 1, 1] * 5)       # always under-forecast
        self.assertEqual(low, 0.0)
        self.assertGreater(high, 0.0)

    def test_few_errors_use_the_normal_theory_band(self):
        low, high = fc.interval_offsets([10, 20], [12, 17])
        rmse = math.sqrt((4 + 9) / 2)
        self.assertAlmostEqual(high, fc.Z_80 * rmse)
        self.assertAlmostEqual(low, -fc.Z_80 * rmse)


class DataQualityTests(SimpleTestCase):
    def test_clean_history_has_no_warnings(self):
        self.assertEqual(fc.data_quality(WEEK * 8), [])

    def test_mostly_empty_days(self):
        self.assertTrue(any("no orders" in w for w in fc.data_quality([0, 0, 0, 5, 0, 0, 0] * 6)))

    def test_service_stopped_recently(self):
        self.assertTrue(any("last 4 days" in w for w in fc.data_quality(WEEK * 6 + [0, 0, 0, 0])))

    def test_one_off_spike(self):
        y = WEEK * 8
        y[30] = 300
        self.assertTrue(any("unusual" in w for w in fc.data_quality(y)))


class DemoPlanTests(SimpleTestCase):
    today = date(2026, 6, 15)

    def test_same_arguments_same_history(self):
        self.assertEqual(demo.demo_day_plan(self.today), demo.demo_day_plan(self.today))

    def test_twelve_weeks_ending_yesterday(self):
        plan = demo.demo_day_plan(self.today)
        self.assertEqual(len(plan), 84)
        self.assertEqual(plan[-1]["date"], self.today - timedelta(days=1))
        self.assertEqual(plan[0]["date"], self.today - timedelta(days=84))

    def test_friday_and_saturday_are_busiest_and_volume_trends_up(self):
        plan = demo.demo_day_plan(self.today)
        avg = lambda days: sum(len(p["containers"]) for p in days) / len(days)      # noqa: E731
        weekend = [p for p in plan if p["date"].weekday() in (4, 5)]
        other = [p for p in plan if p["date"].weekday() not in (4, 5)]
        self.assertGreater(avg(weekend), 1.2 * avg(other))
        self.assertGreater(avg(plan[-28:]), avg(plan[:28]))

    def test_rainy_days_dip_and_cancelled_orders_exist(self):
        plan = demo.demo_day_plan(self.today)
        for i in demo.RAINY_DAYS:
            same_weekday = [len(plan[j]["containers"]) for j in range(len(plan))
                            if plan[j]["date"].weekday() == plan[i]["date"].weekday() and j != i]
            self.assertLess(len(plan[i]["containers"]), sum(same_weekday) / len(same_weekday))
        self.assertGreater(sum(len(p["extra"]) for p in plan), 0)

    def test_the_forecast_beats_naive_on_demo_history(self):
        plan = demo.demo_day_plan(self.today)
        y = [len(p["containers"]) for p in plan]
        t = table(fc.forecast_series(y, plan[0]["date"], 7))
        self.assertLess(t["weekday_average"]["wape"], t["naive"]["wape"])
        self.assertLess(t["holt_winters"]["wape"], t["naive"]["wape"])


class DbBase:
    def make_customer(self, n=1):
        user = User.objects.create_user(f"real{n}@t.ph", f"real{n}@t.ph", "Water2026!x", role="customer")
        CustomerProfile.objects.create(user=user)
        addr = Address.objects.create(customer=user, label="Home", address_text="Real St", barangay="Lalud",
                                      lat=13.41, lng=121.18, is_default=True)
        return user, addr

    def make_order(self, day, status="delivered", containers=2, notes=""):
        return Order.objects.create(customer=self.user, address=self.addr, product=self.product,
                                    quantity=containers, containers=containers, delivery_date=day,
                                    period="morning", status=status, notes=notes)


class LoaderTests(DbBase, TestCase):
    today = date(2026, 3, 10)

    def setUp(self):
        self.product = Product.objects.create(name="5-gallon refill", price=30, kind="refill")
        self.user, self.addr = self.make_customer()

    def test_empty_orders_table(self):
        series = fc.load_daily_series(self.today)
        self.assertEqual(len(series), 0)
        self.assertEqual(fc.build_forecast(7, self.today)["orders"].days, [])

    def test_fills_missing_days_and_leaves_out_invalid_orders_and_today(self):
        d = lambda n: date(2026, 3, n)                          # noqa: E731
        self.make_order(d(1), containers=2)
        self.make_order(d(1), containers=3)
        self.make_order(d(2), status="cancelled")
        self.make_order(d(4), containers=5)
        self.make_order(d(5), status="failed")
        self.make_order(d(5), status="rejected")
        self.make_order(self.today)                             # today is still filling up
        self.make_order(self.today + timedelta(days=1))         # and tomorrow has not happened
        s = fc.load_daily_series(self.today)
        self.assertEqual(s.start, d(1))
        self.assertEqual(s.orders, [2, 0, 0, 1, 0, 0, 0, 0, 0])             # 1 March .. yesterday
        self.assertEqual(s.containers, [5, 0, 0, 5, 0, 0, 0, 0, 0])
        self.assertEqual(s.dates()[-1], self.today - timedelta(days=1))

    def test_pending_and_in_progress_orders_count_as_demand(self):
        for status in ("pending", "confirmed", "out_for_delivery", "delivered"):
            self.make_order(date(2026, 3, 2), status=status)
        self.assertEqual(fc.load_daily_series(self.today).orders[0], 4)


class SeedCommandTests(DbBase, TestCase):
    def setUp(self):
        self.product = Product.objects.create(name="5-gallon refill", price=30, kind="refill")
        self.user, self.addr = self.make_customer()
        self.real = self.make_order(timezone.localdate() - timedelta(days=3), notes="a real order")

    def run_cmd(self, *args):
        out = StringIO()
        call_command("seed_forecast_demo", *args, stdout=out)
        return out.getvalue()

    def demo_orders(self):
        return Order.objects.filter(notes__startswith=demo.MARK)

    def expected(self):
        return sum(len(p["containers"]) + len(p["extra"]) for p in demo.demo_day_plan(timezone.localdate()))

    def test_creates_marked_orders_and_warns(self):
        out = self.run_cmd("--yes")
        self.assertIn("DEMO DATA", out)
        self.assertIn("Never present forecasts", out)
        self.assertEqual(self.demo_orders().count(), self.expected())
        self.assertEqual(User.objects.filter(username__startswith="demo.fc.").count(), demo.N_CUSTOMERS)

    def test_running_twice_gives_the_same_data(self):
        self.run_cmd("--yes")
        first = sorted(self.demo_orders().values_list("delivery_date", "status", "containers"))
        self.run_cmd("--yes")
        self.assertEqual(sorted(self.demo_orders().values_list("delivery_date", "status", "containers")), first)
        self.assertEqual(User.objects.filter(username__startswith="demo.fc.").count(), demo.N_CUSTOMERS)

    def test_clear_removes_only_demo_data(self):
        self.run_cmd("--yes")
        self.run_cmd("--clear", "--yes")
        self.assertEqual(self.demo_orders().count(), 0)
        self.assertFalse(User.objects.filter(username__startswith="demo.fc.").exists())
        self.assertTrue(Order.objects.filter(pk=self.real.pk, notes="a real order").exists())
        self.assertTrue(User.objects.filter(username="real1@t.ph").exists())
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())
        self.assertEqual(Order.objects.count(), 1)

    def test_real_orders_are_never_changed(self):
        before = Order.objects.filter(pk=self.real.pk).values().get()
        self.run_cmd("--yes")
        self.assertEqual(Order.objects.filter(pk=self.real.pk).values().get(), before)

    def test_asks_first_and_does_nothing_on_no(self):
        with mock.patch("builtins.input", return_value="no"):
            out = self.run_cmd()
        self.assertIn("Cancelled", out)
        self.assertEqual(self.demo_orders().count(), 0)

    def test_asks_first_and_goes_ahead_on_yes(self):
        with mock.patch("builtins.input", return_value="yes"):
            self.run_cmd()
        self.assertEqual(self.demo_orders().count(), self.expected())

    def test_no_terminal_means_no(self):
        with mock.patch("builtins.input", side_effect=EOFError):
            self.run_cmd()
        self.assertEqual(self.demo_orders().count(), 0)

    def test_seeded_history_round_trips_through_the_loader(self):
        self.run_cmd("--yes")
        today = timezone.localdate()
        plan = demo.demo_day_plan(today)
        series = fc.load_daily_series(today)
        by_day = dict(zip(series.dates(), series.orders))
        for p in plan:
            self.assertEqual(by_day.get(p["date"], 0) - (1 if p["date"] == self.real.delivery_date else 0),
                             len(p["containers"]), p["date"])
        # cancelled / failed / rejected demo orders are in the table but not in the series
        self.assertGreater(self.demo_orders().count(), sum(len(p["containers"]) for p in plan))

    def test_forecast_runs_on_the_seeded_history(self):
        self.run_cmd("--yes")
        result = fc.build_forecast(14, timezone.localdate())["orders"]
        self.assertTrue(result.enough_data)
        self.assertEqual(len(result.days), 14)
        self.assertEqual(result.days[0].date, timezone.localdate().isoformat())
        self.assertEqual({r["method"] for r in result.backtest}, set(fc.METHODS))
