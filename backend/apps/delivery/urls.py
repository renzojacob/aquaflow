from django.urls import path

from . import rider_api

urlpatterns = [
    path("today", rider_api.TodayView.as_view(), name="rider-today"),
    path("location", rider_api.LocationView.as_view(), name="rider-location"),
    path("orders/<int:pk>/deliver", rider_api.DeliverView.as_view(), name="rider-deliver"),
    path("orders/<int:pk>/fail", rider_api.FailView.as_view(), name="rider-fail"),
]
