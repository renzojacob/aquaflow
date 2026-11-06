from django.urls import path

from apps.sync import views as sync_views

from . import rider_api

urlpatterns = [
    path("today", rider_api.TodayView.as_view(), name="rider-today"),
    path("location", rider_api.LocationView.as_view(), name="rider-location"),
    path("orders/<int:pk>/deliver", rider_api.DeliverView.as_view(), name="rider-deliver"),
    path("orders/<int:pk>/fail", rider_api.FailView.as_view(), name="rider-fail"),
    path("trips", rider_api.TripListView.as_view(), name="rider-trips"),
    path("trips/<int:pk>/download", rider_api.TripDownloadView.as_view(), name="rider-trip-download"),
    path("trips/<int:pk>/start", rider_api.TripStartView.as_view(), name="rider-trip-start"),
    path("sync", sync_views.RiderSyncView.as_view(), name="rider-sync"),
]
