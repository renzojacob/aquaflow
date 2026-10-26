from django.contrib import admin
from .models import Product, StockLevel, StockMovement

admin.site.register(Product)
admin.site.register(StockLevel)

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("created_at", "product", "reason", "d_available", "d_reserved", "d_empty", "by_user")
    list_filter = ("reason", "product")
    def has_change_permission(self, request, obj=None): return False   # ledger is append-only
    def has_delete_permission(self, request, obj=None): return False