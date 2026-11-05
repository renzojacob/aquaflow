"""
Demo data for trying the trip flow by hand (or with backend/scripts/try_trip_flow.py).

    python manage.py seed_trip_demo                 # tomorrow, morning
    python manage.py seed_trip_demo --period afternoon

Creates (or reuses) demo accounts, two vehicles and enough stock, then places 3 NEW
confirmed orders for the slot. Demo trips already in that slot are removed first, so the
command can be run again and again. Only touches records whose names start with "Demo".
Never run it on production data.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import CustomerProfile, User
from apps.customers.models import Address
from apps.dispatch.models import Trip, Vehicle
from apps.inventory.models import Product, StockLevel
from apps.inventory.services import apply_movement
from apps.orders.models import Order
from apps.orders.services import default_product, place_order, transition
from apps.station.models import Station

PASSWORD = "Demo2026!x"
STAFF = [
    ("demo.dispatcher@aquaflow.test", "dispatcher", "Demo", "Dispatcher", ""),
    ("demo.rider@aquaflow.test", "rider", "Demo", "Rider", "09170000001"),
    ("demo.rider2@aquaflow.test", "rider", "Demo", "Rider Two", "09170000002"),
]
# name, lat, lng, barangay: spread around Calapan so the sequence matters
CUSTOMERS = [
    ("ana", 13.4120, 121.1800, "Lalud"),
    ("ben", 13.4300, 121.2000, "Camilmil"),
    ("cora", 13.3990, 121.1700, "Sto. Niño"),
]
VEHICLES = [("Demo Tricycle", "DEMO-001", 20), ("Demo Bike", "DEMO-002", 4)]


def _user(email, role, first, last, phone=""):
    user, created = User.objects.get_or_create(
        username=email, defaults={"email": email, "role": role, "first_name": first,
                                  "last_name": last, "phone": phone})
    if created:
        user.set_password(PASSWORD)
        user.save()
    return user


class Command(BaseCommand):
    help = "Seed demo accounts, vehicles, stock and 3 confirmed orders to try the trip flow."

    def add_arguments(self, parser):
        parser.add_argument("--period", choices=["morning", "afternoon"], default="morning")

    @transaction.atomic
    def handle(self, *args, **opts):
        period = opts["period"]
        day = timezone.localdate() + timedelta(days=1)   # tomorrow is always open for orders

        if not Station.objects.exists():
            Station.objects.create(name="AquaFlow (demo)", lat=13.4108, lng=121.1792)

        product = default_product() or Product.objects.create(name="5-gallon refill", price=30)
        StockLevel.objects.get_or_create(product=product)
        stock = StockLevel.objects.get(product=product)
        if stock.filled_available < 20:
            apply_movement(product, "adjust", None, available=20 - stock.filled_available,
                           note="Demo stock for trip flow")

        staff = {email: _user(email, role, first, last, phone) for email, role, first, last, phone in STAFF}
        dispatcher = staff["demo.dispatcher@aquaflow.test"]

        for name, plate, cap in VEHICLES:
            Vehicle.objects.update_or_create(plate=plate, defaults={"name": name, "capacity_containers": cap,
                                                                    "is_available": True})

        # Free the slot: remove demo trips there (completed ones too) so riders/vehicles are free
        demo_trips = Trip.objects.filter(date=day, period=period, vehicle__plate__startswith="DEMO-")
        removed = demo_trips.count()
        demo_trips.delete()

        orders = []
        for name, lat, lng, barangay in CUSTOMERS:
            email = f"demo.{name}@aquaflow.test"
            cust = _user(email, "customer", "Demo", name.title(), "0917000010" + str(len(orders)))
            profile, _ = CustomerProfile.objects.get_or_create(user=cust)
            if profile.containers_held < 2:
                profile.containers_held = 2
                profile.save(update_fields=["containers_held"])
            addr = Address.objects.filter(customer=cust, is_archived=False).first() or Address.objects.create(
                customer=cust, label="Home", street="Purok 1", barangay=barangay,
                address_text=f"Purok 1, {barangay}", lat=lat, lng=lng, is_default=True)
            order = place_order(cust, address=addr, delivery_date=day, period=period,
                                items=[{"product": product, "quantity": 2}], expected_empties=1)
            orders.append(transition(order, Order.Status.CONFIRMED, by=dispatcher, note="Demo order"))

        self.stdout.write(self.style.SUCCESS(f"Demo data ready for {day} {period}."))
        if removed:
            self.stdout.write(f"  removed {removed} old demo trip(s) in that slot")
        self.stdout.write(f"  password for every demo account: {PASSWORD}")
        for email, role, *_ in STAFF:
            self.stdout.write(f"  {role:<10} {email}")
        for o in orders:
            self.stdout.write(f"  order AF-{o.pk}  {o.customer.username}  2 containers, 1 empty back")
        for name, plate, cap in VEHICLES:
            self.stdout.write(f"  vehicle {name} ({plate}) capacity {cap}")
