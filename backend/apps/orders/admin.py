from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from .models import Order, OrderStatusHistory
from .services import transition


class HistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    can_delete = False
    readonly_fields = ("from_status", "to_status", "changed_by", "server_time", "device_time", "note")
    def has_add_permission(self, request, obj=None): return False


def _bulk(modeladmin, request, queryset, to):
    for o in queryset:
        try:
            transition(o, to, by=request.user)
        except ValidationError as e:
            modeladmin.message_user(request, f"Order #{o.pk}: {e.messages[0]}", messages.ERROR)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "delivery_date", "period", "quantity", "status", "needs_review")
    list_filter = ("status", "period", "delivery_date")
    search_fields = ("customer__username", "address_text", "confirmation_code")
    readonly_fields = ("status", "lat", "lng", "address_text", "landmark", "unit_price",
                       "confirmation_code", "replan_count", "created_at", "updated_at")
    inlines = [HistoryInline]
    actions = ["confirm", "cancel", "reject"]

    @admin.action(description="Confirm selected orders")
    def confirm(self, request, qs): _bulk(self, request, qs, Order.Status.CONFIRMED)

    @admin.action(description="Cancel selected orders")
    def cancel(self, request, qs): _bulk(self, request, qs, Order.Status.CANCELLED)

    @admin.action(description="Reject selected orders")
    def reject(self, request, qs): _bulk(self, request, qs, Order.Status.REJECTED)