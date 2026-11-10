"""
FAKE order history for trying the Forecasting screen. Not real data.

    python manage.py seed_forecast_demo            # asks first
    python manage.py seed_forecast_demo --yes      # no question
    python manage.py seed_forecast_demo --clear    # remove the demo data and stop

About 12 weeks of orders ending yesterday: busier on Friday and Saturday, a mild upward trend,
some noise, two rainy-day dips and a few cancelled orders (which the forecast must ignore).

Safety:
  * Never runs by itself. Nothing imports or calls it.
  * Every order it writes carries the note "[DEMO-FORECAST]" and belongs to a customer named
    demo.fc.NN@aquaflow.test. Only those are ever deleted. Real orders are never read or changed.
  * Safe to run again: the previous demo set is replaced by an identical one.
  * Demo numbers must never be shown to anyone as real results.
"""
import random
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

MARK = "[DEMO-FORECAST]"
EMAIL = "demo.fc.{:02d}@aquaflow.test"
PRODUCT_NAME = "Demo 5-gallon refill (forecast demo)"
N_CUSTOMERS = 25
WEEKS = 12
SEED = 42

BASE_ORDERS = 16                                    # a typical weekday at the start
WEEKDAY_FACTOR = (0.85, 0.90, 0.90, 1.00, 1.35, 1.30, 0.80)   # Monday .. Sunday: Friday/Saturday are busy
TREND_PER_DAY = 0.0025                              # about +20% over 12 weeks
RAINY_DAYS = (30, 61)                               # day numbers in the 84-day window
RAIN_FACTOR = 0.55
BOX_SIZES, BOX_WEIGHTS = (1, 2, 3, 4), (35, 35, 20, 10)
CANCEL_RATE = 0.06
OTHER_ENDINGS = ("cancelled", "failed", "rejected")


def demo_day_plan(today, weeks=WEEKS, seed=SEED):
    """
    The made-up history, one entry per day, oldest first, ending yesterday:
    {"date", "containers": [size of each valid order], "extra": [status of each cancelled/failed/rejected one]}.
    Pure function: no database, same answer for the same arguments.
    """
    rng = random.Random(seed)
    days = weeks * 7
    plan = []
    for i in range(days):
        day = today - timedelta(days=days - i)
        mean = BASE_ORDERS * WEEKDAY_FACTOR[day.weekday()] * (1 + TREND_PER_DAY * i)
        if i in RAINY_DAYS:
            mean *= RAIN_FACTOR
        n = max(0, round(rng.gauss(mean, mean * 0.12 + 0.5)))
        sizes = [rng.choices(BOX_SIZES, weights=BOX_WEIGHTS)[0] for _ in range(n)]
        extra = [OTHER_ENDINGS[j % 3] for j in range(sum(1 for _ in range(n) if rng.random() < CANCEL_RATE))]
        plan.append({"date": day, "containers": sizes, "extra": extra})
    return plan


def _demo_orders():
    from apps.orders.models import Order
    return Order.objects.filter(notes__startswith=MARK)


def clear_demo_data():
    """Delete only what this command created. Returns how many orders were removed."""
    from apps.accounts.models import User
    from apps.inventory.models import Product

    removed, _ = _demo_orders().delete()
    # Order.customer / Order.product are PROTECT, which is why the orders go first.
    User.objects.filter(username__startswith="demo.fc.", username__endswith="@aquaflow.test").delete()
    Product.objects.filter(name=PRODUCT_NAME).delete()
    return removed


class Command(BaseCommand):
    help = "Seed ~12 weeks of FAKE orders to try the Forecasting screen (demo data, marked, removable)."

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true", help="Do not ask for confirmation.")
        parser.add_argument("--clear", action="store_true", help="Remove the demo data and stop.")

    def handle(self, *args, **opts):
        self.stdout.write(self.style.WARNING(
            "\n  DEMO DATA: these orders are fake. Never present forecasts built on them as real results.\n"
            f"  Every demo order is marked {MARK} and can be removed with --clear.\n"))
        verb = "REMOVE all demo forecast data" if opts["clear"] else "REPLACE any demo forecast data with fresh fake orders"
        if not opts["yes"] and not self._confirmed(verb):
            self.stdout.write("Cancelled. Nothing was changed.")
            return
        with transaction.atomic():
            removed = clear_demo_data()
            if opts["clear"]:
                self.stdout.write(self.style.SUCCESS(f"Removed {removed} demo order(s) and the demo customers."))
                return
            made, first, last = self._seed()
        if removed:
            self.stdout.write(f"  replaced {removed} earlier demo order(s)")
        self.stdout.write(self.style.SUCCESS(
            f"Created {made} fake orders from {first} to {last}. Remove them with: manage.py seed_forecast_demo --clear"))

    def _confirmed(self, verb):
        try:
            answer = input(f"  This will {verb}. Real orders are not touched. Type yes to continue: ")
        except EOFError:
            return False
        return answer.strip().lower() in ("yes", "y")

    def _seed(self):
        from django.utils import timezone

        from apps.accounts.models import CustomerProfile, User
        from apps.customers.models import Address
        from apps.inventory.models import Product
        from apps.orders.models import Order
        from apps.orders.services import default_product

        today = timezone.localdate()
        rng = random.Random(SEED + 1)
        product = default_product() or Product.objects.create(name=PRODUCT_NAME, price=30, kind=Product.Kind.REFILL)

        customers = []
        for n in range(1, N_CUSTOMERS + 1):
            email = EMAIL.format(n)
            user = User.objects.create_user(email, email, "Demo2026!x", role="customer",
                                            first_name="Demo", last_name=f"Forecast {n}")
            CustomerProfile.objects.get_or_create(user=user)
            addr = Address.objects.create(
                customer=user, label="Home", street=f"Demo Street {n}", barangay="Lalud",
                address_text=f"Demo Street {n}, Lalud", is_default=True,
                lat=round(13.41 + rng.uniform(-0.02, 0.02), 6), lng=round(121.18 + rng.uniform(-0.02, 0.02), 6))
            customers.append((user, addr))

        plan = demo_day_plan(today)
        made = 0
        for entry in plan:
            ids = []
            rows = [("delivered", size) for size in entry["containers"]]
            rows += [(status, rng.choice(BOX_SIZES)) for status in entry["extra"]]
            for status, size in rows:
                user, addr = rng.choice(customers)
                order = Order.objects.create(
                    customer=user, address=addr, product=product, quantity=size, containers=size,
                    delivery_date=entry["date"], period=rng.choice(("morning", "morning", "afternoon")),
                    status=status, notes=MARK,
                    cancel_reason="Demo" if status in ("cancelled", "failed") else "",
                    rejection_reason="Demo" if status == "rejected" else "")
                ids.append(order.pk)
            # created_at is set by the database on insert; place it on the day before delivery instead.
            placed = timezone.make_aware(datetime.combine(entry["date"] - timedelta(days=1), time(18, 0)))
            Order.objects.filter(pk__in=ids).update(created_at=placed)
            made += len(ids)
        return made, plan[0]["date"], plan[-1]["date"]
