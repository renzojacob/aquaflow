from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import CustomerOrderViewSet, SlotAvailabilityView

router = SimpleRouter()
router.register("customer/orders", CustomerOrderViewSet, basename="customer-order")

urlpatterns = [
    path("customer/slots/", SlotAvailabilityView.as_view(), name="customer-slots"),  # Feature D
    *router.urls,
]
