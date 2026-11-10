from django.conf import settings
from django.db import models


class Product(models.Model):
    class Kind(models.TextChoices):
        REFILL = "refill"        # we bring a filled station container and take an empty back
        CONTAINER = "container"  # the customer buys a new container and keeps it
        ITEM = "item"            # anything else sold: small bottles, ice, caps and seals

    name = models.CharField(max_length=100)          # e.g. "5-gallon refill"
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.REFILL)
    description = models.CharField(max_length=160, blank=True)
    max_per_order = models.PositiveSmallIntegerField(default=20)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


class StockLevel(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="stock")
    filled_available = models.PositiveIntegerField(default=0)   # filled and free to promise
    filled_reserved = models.PositiveIntegerField(default=0)    # filled, held for confirmed orders
    empty_count = models.PositiveIntegerField(default=0)        # empties at the station

    def __str__(self):
        return f"{self.product.name}: {self.filled_available} free / {self.filled_reserved} reserved / {self.empty_count} empty"


class StockMovement(models.Model):
    class Reason(models.TextChoices):
        RESERVE = "reserve"
        RELEASE = "release"
        LOAD_OUT = "load_out"
        RETURN_UNSOLD = "return_unsold"
        EMPTIES_IN = "empties_in"
        REFILL = "refill"
        ADJUST = "adjust"

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="movements")
    reason = models.CharField(max_length=20, choices=Reason.choices)
    d_available = models.IntegerField(default=0)    # change to filled_available
    d_reserved = models.IntegerField(default=0)     # change to filled_reserved
    d_empty = models.IntegerField(default=0)        # change to empty_count
    by_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                on_delete=models.SET_NULL)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.ForeignKey("orders.Order", null=True, blank=True,
                        on_delete=models.SET_NULL, related_name="stock_movements")
    trip = models.ForeignKey("dispatch.Trip", null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="stock_movements")

    class Meta:
        ordering = ["-created_at"]

    

class Supply(models.Model):
    """
    Something the station uses up that is NOT a container: caps, seals, filters, cleaning
    solution. Quantity is a decimal so a filter can be "0.8 of its life left" and a
    solution can be measured in litres.

    used_per_refill: how much of this is used for ONE filled container. Caps and seals are
    1 each; a filter that lasts 2000 containers is 0.0005. Leave it 0 for things that are
    not used per container (then usage is worked out from what staff record by hand).
    """
    class Unit(models.TextChoices):
        PIECE = "piece"
        LITRE = "litre"
        KILO = "kilo"
        SET = "set"

    name = models.CharField(max_length=60, unique=True)         # "Bottle caps"
    unit = models.CharField(max_length=10, choices=Unit.choices, default=Unit.PIECE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    used_per_refill = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    lead_time_days = models.PositiveSmallIntegerField(default=3)  # how long a delivery takes to arrive
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    note = models.CharField(max_length=160, blank=True)          # "Supplier: Calapan Plastics"
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "supplies"
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gte=0), name="supply_quantity_not_negative"),
        ]

    def __str__(self):
        return f"{self.name}: {self.quantity} {self.unit}"


class SupplyMovement(models.Model):
    """Append-only log of every change to a supply, so a count can always be explained."""
    class Reason(models.TextChoices):
        RECEIVED = "received"      # a delivery arrived
        USED = "used"              # used up (automatic when containers are filled, or recorded by hand)
        CORRECTION = "correction"  # a physical count

    supply = models.ForeignKey(Supply, on_delete=models.CASCADE, related_name="movements")
    reason = models.CharField(max_length=12, choices=Reason.choices)
    delta = models.DecimalField(max_digits=10, decimal_places=2)   # + in, - out
    by_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                on_delete=models.SET_NULL)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["supply", "created_at"])]

    def __str__(self):
        return f"{self.supply.name} {self.delta:+} ({self.reason})"
