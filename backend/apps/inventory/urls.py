from rest_framework.routers import DefaultRouter

from django.urls import path

from . import supplies_api
from .views import ProductViewSet

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")

urlpatterns = router.urls + [
    path("v1/dispatch/supplies", supplies_api.SupplyListCreateView.as_view(), name="staff-supplies"),
    path("v1/dispatch/supplies/<int:pk>", supplies_api.SupplyDetailView.as_view(), name="staff-supply"),
    path("v1/dispatch/supplies/<int:pk>/adjust", supplies_api.SupplyAdjustView.as_view(), name="staff-supply-adjust"),
]
