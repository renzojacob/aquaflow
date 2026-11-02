from django.urls import path

from . import staff_api

urlpatterns = [
    path("users", staff_api.UserListView.as_view(), name="owner-users"),
    path("users/<int:pk>", staff_api.UserDetailView.as_view(), name="owner-user"),
]
