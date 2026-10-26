import uuid
from django.conf import settings
from django.db import models


class SyncAction(models.Model):
    """One action from a rider's phone. idempotency_key makes replays harmless."""
    class ActionType(models.TextChoices):
        START_TRIP = "start_trip"
        DELIVER = "deliver"
        FAIL = "fail"
        EMPTIES = "empties"

    class Result(models.TextChoices):
        APPLIED = "applied"
        DUPLICATE = "duplicate"
        REJECTED = "rejected"
        CONFLICT = "conflict"

    idempotency_key = models.UUIDField(unique=True, default=uuid.uuid4)  # generated on the phone
    rider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                              related_name="sync_actions")
    device_id = models.CharField(max_length=100)
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    trip = models.ForeignKey("dispatch.Trip", null=True, blank=True, on_delete=models.SET_NULL)
    order = models.ForeignKey("orders.Order", null=True, blank=True, on_delete=models.SET_NULL)
    payload = models.JSONField(default=dict)
    device_time = models.DateTimeField()
    server_time = models.DateTimeField(auto_now_add=True)
    result = models.CharField(max_length=12, choices=Result.choices)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-server_time"]
        indexes = [models.Index(fields=["rider", "server_time"])]

    def __str__(self):
        return f"{self.action_type} by {self.rider} ({self.result})"


class SyncConflict(models.Model):
    class Kind(models.TextChoices):
        DELIVERED_AFTER_CANCEL = "delivered_after_cancel"
        REASSIGNED = "reassigned"
        OUT_OF_ORDER = "out_of_order"
        CODE_MISMATCH = "code_mismatch"

    class Status(models.TextChoices):
        OPEN = "open"
        RESOLVED = "resolved"

    sync_action = models.ForeignKey(SyncAction, on_delete=models.CASCADE, related_name="conflicts")
    order = models.ForeignKey("orders.Order", null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="sync_conflicts")
    kind = models.CharField(max_length=30, choices=Kind.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")
    resolution_note = models.CharField(max_length=255, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["status", "-created_at"]