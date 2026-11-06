from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.views import LoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/login/", LoginView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.inventory.urls")),
    path("api/customer/", include("apps.customers.urls")),
    path("api/", include("apps.orders.urls")),
    path("api/", include("apps.station.urls")),             # settings/public/
    path("api/", include("apps.predictions.urls")),         # Feature C: refill prediction
    path("api/v1/dispatch/", include("apps.dispatch.urls")),   # dispatcher + owner
    path("api/v1/owner/", include("apps.accounts.staff_urls")),  # owner: people
    path("api/v1/rider/", include("apps.delivery.urls")),      # rider app
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
