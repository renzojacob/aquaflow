from django.conf import settings
from django.db import models
from django.db.models import Q


class DeliveryAttempt(models.Model):
    class Outcome(models.TextChoices):
        DELIVERED = "delivered"
        FAILED = "failed"

    class FailureReason(models.TextChoices):
        ABSENT = "absent"
        WRONG_ADDRESS = "wrong_address"
        REFUSED = "refused"
        OTHER = "other"

    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="attempts")
    trip_stop = models.ForeignKey("dispatch.TripStop", null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name="attempts")
    rider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                              related_name="delivery_attempts")
    outcome = models.CharField(max_length=10, choices=Outcome.choices)
    failure_reason = models.CharField(max_length=20, choices=FailureReason.choices, blank=True)
    empties_collected = models.PositiveSmallIntegerField(default=0)
    code_ok = models.BooleanField(null=True)     # None = not checked (e.g. failed attempt)

    # Feature F: geofence proof
    gps_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_accuracy_m = models.FloatField(null=True, blank=True)
    distance_from_pin_m = models.PositiveIntegerField(null=True, blank=True)
    geofence_flagged = models.BooleanField(default=False)

    device_time = models.DateTimeField()
    server_time = models.DateTimeField(auto_now_add=True)
    sync_action = models.OneToOneField("sync.SyncAction", null=True, blank=True,
                                       on_delete=models.SET_NULL, related_name="delivery_attempt")

    class Meta:
        ordering = ["-server_time"]
        constraints = [
            models.CheckConstraint(
                condition=Q(outcome="delivered") | ~Q(failure_reason=""),
                name="failed_attempt_needs_reason",
            ),
        ]

    def __str__(self):
        return f"Order #{self.order_id}: {self.outcome}"

class RiderLocation(models.Model):
    """One GPS point sent by a rider's phone while delivering. The newest one is "where they are"."""

    rider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="locations")
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy_m = models.FloatField(null=True, blank=True)
    heading = models.FloatField(null=True, blank=True)      # degrees, 0 = north
    speed_mps = models.FloatField(null=True, blank=True)
    is_simulated = models.BooleanField(default=False)       # demo drive, not a real GPS reading
    device_time = models.DateTimeField()
    server_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-server_time"]
        indexes = [models.Index(fields=["rider", "-server_time"])]

    def __str__(self):
        return f"{self.rider} @ {self.lat},{self.lng}"
