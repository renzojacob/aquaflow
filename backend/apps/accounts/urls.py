from django.urls import path

from .views import CustomerProfileView, MeView, RegisterView

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("me/", MeView.as_view(), name="me"),
    path("me/profile/", CustomerProfileView.as_view(), name="me-profile"),
]