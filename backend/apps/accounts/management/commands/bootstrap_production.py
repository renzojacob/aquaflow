"""
First-time setup for an EMPTY production database. Safe to run again: it only creates what is missing
and never changes an existing account's password.

    python manage.py bootstrap_production

Accounts come from environment variables (no passwords in code). A role is created only when both
its EMAIL and PASSWORD are set:
    BOOTSTRAP_{OWNER,DISPATCHER,RIDER,CUSTOMER}_EMAIL / _PASSWORD

Also creates, if missing: the station, a service area, the default refill product with its stock row,
the system settings row and one vehicle. (Delivery slots are not stored: they are worked out from the
fleet's vehicle capacity, so having a vehicle is what opens the morning/afternoon slots.)
Optional tuning variables: see backend/.env.example.
"""
import os
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import CustomerProfile, RiderProfile, User
from apps.dispatch.models import Vehicle
from apps.inventory.models import Product, StockLevel
from apps.station.models import ServiceArea, Station, SystemSetting

ROLES = ["owner", "dispatcher", "rider", "customer"]


def _env(name, default):
    return (os.environ.get(name) or "").strip() or default


class Command(BaseCommand):
    help = "Create the role accounts, station, area, product and vehicle in an empty database (safe to re-run)."

    @transaction.atomic
    def handle(self, *args, **opts):
        for role in ROLES:
            self._account(role)

        lat = Decimal(_env("BOOTSTRAP_STATION_LAT", "13.4108"))
        lng = Decimal(_env("BOOTSTRAP_STATION_LNG", "121.1792"))

        if not Station.objects.exists():
            Station.objects.create(name=_env("BOOTSTRAP_STATION_NAME", "AquaFlow Station"), lat=lat, lng=lng)
            self.stdout.write("created station")
        if not ServiceArea.objects.exists():
            ServiceArea.objects.create(name=_env("BOOTSTRAP_AREA_NAME", "Calapan City"),
                                       center_lat=lat, center_lng=lng,
                                       radius_m=int(_env("BOOTSTRAP_AREA_RADIUS_M", "8000")))
            self.stdout.write("created service area")
        if not Product.objects.exists():
            product = Product.objects.create(name=_env("BOOTSTRAP_PRODUCT_NAME", "5-gallon refill"),
                                             price=Decimal(_env("BOOTSTRAP_PRODUCT_PRICE", "30")),
                                             kind=Product.Kind.REFILL)
            StockLevel.objects.get_or_create(product=product)
            self.stdout.write("created product")
        SystemSetting.load()
        _, made = Vehicle.objects.get_or_create(
            plate=_env("BOOTSTRAP_VEHICLE_PLATE", "AQF-001"),
            defaults={"name": _env("BOOTSTRAP_VEHICLE_NAME", "Tricycle 1"),
                      "capacity_containers": int(_env("BOOTSTRAP_VEHICLE_CAPACITY", "20")),
                      "is_available": True})
        if made:
            self.stdout.write("created vehicle")
        self.stdout.write(self.style.SUCCESS("bootstrap_production finished."))

    def _account(self, role):
        key = role.upper()
        email = _env(f"BOOTSTRAP_{key}_EMAIL", "")
        password = os.environ.get(f"BOOTSTRAP_{key}_PASSWORD", "")
        if not email or not password:
            self.stdout.write(f"skipped {role} (BOOTSTRAP_{key}_EMAIL / _PASSWORD not both set)")
            return
        user = User.objects.filter(username=email).first()
        if user:
            self.stdout.write(f"{role} already exists: {email}")
            return
        user = User(username=email, email=email, role=role, first_name=role.title())
        if role == "owner":                       # lets the owner sign in to the Django admin
            user.is_staff = user.is_superuser = True
        user.set_password(password)
        user.save()
        if role == "customer":
            CustomerProfile.objects.get_or_create(user=user)
        elif role == "rider":
            RiderProfile.objects.get_or_create(user=user)
        self.stdout.write(f"created {role}: {email}")
