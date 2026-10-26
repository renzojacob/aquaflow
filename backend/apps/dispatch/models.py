from django.conf import settings
from django.db import models
from django.db.models import Deferrable, Q


class Vehicle(models.Model):
    name = models.CharField(max_length=50)                 # "Tricycle 1"
    plate = models.CharField(max_length=20, unique=True)
    capacity_containers = models.PositiveSmallIntegerField()
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.capacity_containers})"


class Trip(models.Model):
    class Period(models.TextChoices):
        MORNING = "morning"
        AFTERNOON = "afternoon"

    class Status(models.TextChoices):
        DRAFT = "draft"
        APPROVED = "approved"
        DOWNLOADED = "downloaded"    # rider app has the offline copy
        OUT = "out"
        COMPLETED = "completed"

    date = models.DateField()
    period = models.CharField(max_length=10, choices=Period.choices)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="trips")
    rider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                              null=True, blank=True, related_name="trips",
                              limit_choices_to={"role": "rider"})
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)

    total_distance_m = models.PositiveIntegerField(default=0)
    total_duration_s = models.PositiveIntegerField(default=0)
    distance_is_estimate = models.BooleanField(default=False)   # True if haversine fallback was used

    version = models.PositiveIntegerField(default=1)            # bump on every change
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "period"]
        constraints = [
            models.UniqueConstraint(fields=["date", "period", "vehicle"],
                                    name="one_trip_per_vehicle_per_period"),
            models.UniqueConstraint(fields=["date", "period", "rider"],
                                    name="one_trip_per_rider_per_period"),
        ]

    def __str__(self):
        return f"Trip #{self.pk} {self.date} {self.period} - {self.vehicle.name}"


class TripStop(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        DONE = "done"
        FAILED = "failed"

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="stops")
    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="trip_stops")
    sequence = models.PositiveSmallIntegerField()
    expected_load_after = models.PositiveSmallIntegerField(null=True, blank=True)
    eta = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ["trip", "sequence"]
        constraints = [
            # Checked at COMMIT, so you can swap two sequences inside one transaction
            models.UniqueConstraint(fields=["trip", "sequence"], name="unique_stop_sequence",
                                    deferrable=Deferrable.DEFERRED),
            # An order can have at most one active stop; a failed stop allows a re-plan
            models.UniqueConstraint(fields=["order"], condition=~Q(status="failed"),
                                    name="one_active_stop_per_order"),
        ]

    def __str__(self):
        return f"{self.trip} - stop {self.sequence}: order #{self.order_id}"


class DistanceCache(models.Model):
    class Source(models.TextChoices):
        ORS = "ors"
        HAVERSINE = "haversine"

    # Rounded to 5 decimals (~1 m), so nearby lookups hit the same row
    from_lat = models.DecimalField(max_digits=8, decimal_places=5)
    from_lng = models.DecimalField(max_digits=8, decimal_places=5)
    to_lat = models.DecimalField(max_digits=8, decimal_places=5)
    to_lng = models.DecimalField(max_digits=8, decimal_places=5)
    distance_m = models.PositiveIntegerField()
    duration_s = models.PositiveIntegerField()
    source = models.CharField(max_length=10, choices=Source.choices)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["from_lat", "from_lng", "to_lat", "to_lng"],
                                    name="unique_distance_pair"),
        ]


class TripChangeLog(models.Model):
    class Action(models.TextChoices):
        PLANNED = "planned"
        MOVED_IN = "moved_in"
        MOVED_OUT = "moved_out"
        REORDERED = "reordered"
        REPLAN_INSERT = "replan_insert"
        REMOVED = "removed"

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="change_log")
    action = models.CharField(max_length=20, choices=Action.choices)
    order = models.ForeignKey("orders.Order", null=True, blank=True, on_delete=models.SET_NULL)
    by_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                on_delete=models.SET_NULL)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]