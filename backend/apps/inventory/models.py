from django.conf import settings
from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=100)          # e.g. "5-gallon refill"
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)

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

    