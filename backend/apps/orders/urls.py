from rest_framework.routers import SimpleRouter

from .views import CustomerOrderViewSet

router = SimpleRouter()
router.register("customer/orders", CustomerOrderViewSet, basename="customer-order")

urlpatterns = router.urls
