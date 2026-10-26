from django.contrib import admin
from .models import SyncAction, SyncConflict

@admin.register(SyncAction)
class SyncActionAdmin(admin.ModelAdmin):
    list_display = ("server_time", "rider", "action_type", "order", "result")
    list_filter = ("result", "action_type")
    def has_change_permission(self, request, obj=None): return False

@admin.register(SyncConflict)
class SyncConflictAdmin(admin.ModelAdmin):
    list_display = ("created_at", "kind", "order", "status", "resolved_by")
    list_filter = ("status", "kind")