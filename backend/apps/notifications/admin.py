from django.contrib import admin
from .models import EmailLog

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "template", "to_email", "status", "attempts")
    list_filter = ("status", "template")
    def has_change_permission(self, request, obj=None): return False