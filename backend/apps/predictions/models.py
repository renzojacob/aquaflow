from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.orders.models import Order


class RefillPrediction(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name="refill_predictions")
    address = models.ForeignKey("customers.Address", on_delete=models.CASCADE,
                                related_name="refill_predictions")
    predicted_runout_date = models.DateField()
    days_per_container = models.DecimalField(max_digits=6, decimal_places=2)
    last_delivery_date = models.DateField()
    last_quantity = models.PositiveSmallIntegerField()
    inputs = models.JSONField(default=dict)        # the intervals used, for explainability
    is_current = models.BooleanField(default=True)
    actual_order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="+")   # filled in later, for accuracy reporting
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["customer", "address"], condition=Q(is_current=True),
                                    name="one_current_prediction_per_address"),
        ]

    def __str__(self):
        return f"{self.customer} runs out ~{self.predicted_runout_date}"


class ReminderLog(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "email"
        IN_APP = "in_app"

    prediction = models.ForeignKey(RefillPrediction, on_delete=models.CASCADE,
                                   related_name="reminders")
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name="reminders")
    channel = models.CharField(max_length=10, choices=Channel.choices)
    sent_at = models.DateTimeField(auto_now_add=True)
    reordered_order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name="+")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["prediction", "channel"],
                                    name="one_reminder_per_prediction_channel"),
        ]


class AddressPeriodStats(models.Model):
    """Feature E: delivery success per address and time period."""
    address = models.ForeignKey("customers.Address", on_delete=models.CASCADE,
                                related_name="period_stats")
    period = models.CharField(max_length=10, choices=Order.Period.choices)
    successes = models.PositiveIntegerField(default=0)
    failures = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "address period stats"
        constraints = [
            models.UniqueConstraint(fields=["address", "period"], name="unique_address_period"),
        ]

    @property
    def attempts(self):
        return self.successes + self.failures

    @property
    def success_rate(self):
        return self.successes / self.attempts if self.attempts else None