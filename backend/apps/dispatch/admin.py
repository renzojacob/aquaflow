from django.contrib import admin
from .models import Vehicle, Trip, TripStop, DistanceCache, TripChangeLog

admin.site.register(Vehicle)


class TripStopInline(admin.TabularInline):
    model = TripStop
    extra = 0
    fields = ("sequence", "order", "expected_load_after", "eta", "status")
    ordering = ("sequence",)


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "period", "vehicle", "rider", "status", "version")
    list_filter = ("status", "period", "date")
    readonly_fields = ("version", "total_distance_m", "total_duration_s", "distance_is_estimate")
    inlines = [TripStopInline]


@admin.register(DistanceCache)
class DistanceCacheAdmin(admin.ModelAdmin):
    list_display = ("from_lat", "from_lng", "to_lat", "to_lng", "distance_m", "duration_s", "source")
    list_filter = ("source",)


@admin.register(TripChangeLog)
class TripChangeLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "trip", "action", "order", "by_user")
    list_filter = ("action",)
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False