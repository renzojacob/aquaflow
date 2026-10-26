from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q

LAT_VALIDATORS = [MinValueValidator(-90), MaxValueValidator(90)]
LNG_VALIDATORS = [MinValueValidator(-180), MaxValueValidator(180)]


class Address(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name="addresses",
                                 limit_choices_to={"role": "customer"})
    label = models.CharField(max_length=50)                  # "Home", "Store"
    address_text = models.CharField(max_length=255)
    landmark = models.CharField(max_length=255, blank=True)  # "blue gate beside sari-sari store"
    label = models.CharField(max_length=40, blank=True)      # "Home", "Work"
    street = models.CharField(max_length=200, blank=True)
    barangay = models.CharField(max_length=100, blank=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, validators=LAT_VALIDATORS)
    lng = models.DecimalField(max_digits=9, decimal_places=6, validators=LNG_VALIDATORS)
    is_default = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)          # archive, never delete (old orders point here)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "addresses"
        constraints = [
            models.UniqueConstraint(
                fields=["customer"],
                condition=Q(is_default=True, is_archived=False),
                name="one_default_address_per_customer",
            ),
        ]

    def __str__(self):
        return f"{self.customer.username} - {self.label}"


class ContainerMovement(models.Model):
    """Ledger of containers a customer holds. Balance = sum(delivered) - sum(returned)."""
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                 related_name="container_movements")
    delivered = models.PositiveSmallIntegerField(default=0)   # filled containers left with customer
    returned = models.PositiveSmallIntegerField(default=0)    # empties picked up
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.ForeignKey("orders.Order", null=True, blank=True,
                            on_delete=models.SET_NULL, related_name="container_movements")

    class Meta:
        ordering = ["-created_at"]