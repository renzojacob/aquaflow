from django.conf import settings
from django.db import models


class EmailLog(models.Model):
    class Template(models.TextChoices):
        ORDER_CONFIRMED = "order_confirmed"
        ORDER_REJECTED = "order_rejected"
        ORDER_CANCELLED = "order_cancelled"
        OUT_FOR_DELIVERY = "out_for_delivery"
        DELIVERED = "delivered"
        REFILL_REMINDER = "refill_reminder"
        PASSWORD_RESET = "password_reset"

    class Status(models.TextChoices):
        QUEUED = "queued"
        SENT = "sent"
        FAILED = "failed"

    to_email = models.EmailField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="emails")
    template = models.CharField(max_length=30, choices=Template.choices)
    context = models.JSONField(default=dict)       # values passed to the Brevo template
    order = models.ForeignKey("orders.Order", null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="emails")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    attempts = models.PositiveSmallIntegerField(default=0)
    brevo_message_id = models.CharField(max_length=100, blank=True)
    last_error = models.TextField(blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "next_retry_at"])]   # for the retry job

    def __str__(self):
        return f"{self.template} → {self.to_email} ({self.status})"