from django.contrib import admin
from .models import Address, ContainerMovement

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("customer", "label", "address_text", "lat", "lng", "is_default", "is_archived")
    list_filter = ("is_default", "is_archived")
    search_fields = ("customer__username", "address_text", "landmark")

@admin.register(ContainerMovement)
class ContainerMovementAdmin(admin.ModelAdmin):
    list_display = ("created_at", "customer", "delivered", "returned", "note")
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False