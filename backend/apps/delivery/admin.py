from django.contrib import admin
from .models import DeliveryAttempt

@admin.register(DeliveryAttempt)
class DeliveryAttemptAdmin(admin.ModelAdmin):
    list_display = ("server_time", "order", "rider", "outcome", "failure_reason",
                    "empties_collected", "distance_from_pin_m", "geofence_flagged")
    list_filter = ("outcome", "geofence_flagged", "failure_reason")
    def has_change_permission(self, request, obj=None): return False