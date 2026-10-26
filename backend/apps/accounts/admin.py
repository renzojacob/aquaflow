from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, CustomerProfile, RiderProfile

class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    extra = 0

class RiderProfileInline(admin.StackedInline):
    model = RiderProfile
    extra = 0

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("AquaFlow", {"fields": ("role", "phone")}),)
    list_display = ("username", "email", "role", "is_active")
    list_filter = ("role", "is_active")
    inlines = [CustomerProfileInline, RiderProfileInline]
