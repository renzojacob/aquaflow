from django.db import models

class Station(models.Model):
    name = models.CharField(max_length=100)
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)

    def __str__(self):
        return self.name


class ServiceArea(models.Model):
    name = models.CharField(max_length=100)
    center_lat = models.DecimalField(max_digits=9, decimal_places=6)
    center_lng = models.DecimalField(max_digits=9, decimal_places=6)
    radius_m = models.PositiveIntegerField()

    def __str__(self):
        return self.name


class SystemSetting(models.Model):
    """Single-row table. Always use SystemSetting.load()."""
    geofence_threshold_m = models.PositiveIntegerField(default=150)
    reminder_lead_days = models.PositiveSmallIntegerField(default=2)
    nearby_radius_m = models.PositiveIntegerField(default=1000)
    min_history_orders = models.PositiveSmallIntegerField(default=3)
    best_time_min_attempts = models.PositiveSmallIntegerField(default=4)

    def save(self, *args, **kwargs):
        self.pk = 1                       # forces a single row
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass                              # the row can't be deleted

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "System settings"