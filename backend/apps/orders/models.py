import secrets
from django.conf import settings
from django.db import models
from django.db.models import Q


class Order(models.Model):
    class Period(models.TextChoices):
        MORNING = "morning"
        AFTERNOON = "afternoon"

    class Status(models.TextChoices):
        PENDING = "pending"
        CONFIRMED = "confirmed"
        PREPARING = "preparing"
        READY = "ready"
        OUT_FOR_DELIVERY = "out_for_delivery"
        DELIVERED = "delivered"
        REJECTED = "rejected"
        CANCELLED = "cancelled"
        FAILED = "failed"

    class Source(models.TextChoices):
        MANUAL = "manual"
        REMINDER_REORDER = "reminder_reorder"

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                 related_name="orders", limit_choices_to={"role": "customer"})
    address = models.ForeignKey("customers.Address", on_delete=models.PROTECT, related_name="orders")

    # Snapshots, copied from the address/product when the order is created
    lat = models.DecimalField(max_digits=9, decimal_places=6, editable=False)
    lng = models.DecimalField(max_digits=9, decimal_places=6, editable=False)
    address_text = models.CharField(max_length=255, editable=False)
    landmark = models.CharField(max_length=255, blank=True, editable=False)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2, editable=False)

    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT)
    quantity = models.PositiveSmallIntegerField()
    expected_empties = models.PositiveSmallIntegerField(default=0)
    delivery_date = models.DateField()
    period = models.CharField(max_length=10, choices=Period.choices)
    notes = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    rejection_reason = models.CharField(max_length=255, blank=True)
    cancel_reason = models.CharField(max_length=255, blank=True)

    confirmation_code = models.CharField(max_length=6, editable=False)
    code_salt = models.CharField(max_length=16, editable=False)

    replan_count = models.PositiveSmallIntegerField(default=0)
    needs_review = models.BooleanField(default=False)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["delivery_date", "period", "status"])]
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name="order_quantity_at_least_1"),
            models.CheckConstraint(condition=Q(replan_count__lte=1), name="order_replan_at_most_once"),
        ]

    def save(self, *args, **kwargs):
        if self._state.adding:
            a = self.address
            self.lat, self.lng = a.lat, a.lng
            self.address_text, self.landmark = a.address_text, a.landmark
            self.unit_price = self.product.price
            self.confirmation_code = f"{secrets.randbelow(10**6):06d}"
            self.code_salt = secrets.token_hex(8)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"#{self.pk} {self.customer.username} {self.delivery_date} {self.period} ({self.status})"


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="history")
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL)
    server_time = models.DateTimeField(auto_now_add=True)
    device_time = models.DateTimeField(null=True, blank=True)   # from rider phone when synced offline
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["server_time"]
        verbose_name_plural = "order status history"