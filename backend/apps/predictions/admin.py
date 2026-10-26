from django.contrib import admin
from .models import RefillPrediction, ReminderLog, AddressPeriodStats

@admin.register(RefillPrediction)
class RefillPredictionAdmin(admin.ModelAdmin):
    list_display = ("customer", "address", "predicted_runout_date", "days_per_container", "is_current")
    list_filter = ("is_current",)

@admin.register(ReminderLog)
class ReminderLogAdmin(admin.ModelAdmin):
    list_display = ("sent_at", "customer", "channel", "reordered_order")

@admin.register(AddressPeriodStats)
class AddressPeriodStatsAdmin(admin.ModelAdmin):
    list_display = ("address", "period", "successes", "failures", "success_rate")