from django.urls import path

from . import api, fleet_api, trips_api

urlpatterns = [
    path("orders", api.StaffOrderListView.as_view(), name="staff-orders"),
    path("orders/<int:pk>", api.StaffOrderDetailView.as_view(), name="staff-order"),
    path("orders/<int:pk>/<str:action>", api.StaffOrderActionView.as_view(), name="staff-order-action"),
    path("riders", api.RiderListView.as_view(), name="staff-riders"),
    path("stock", api.StockView.as_view(), name="staff-stock"),
    path("stock/adjust", api.StockAdjustView.as_view(), name="staff-stock-adjust"),
    path("summary", api.SummaryView.as_view(), name="staff-summary"),
    path("vehicles", fleet_api.VehicleListCreateView.as_view(), name="staff-vehicles"),
    path("vehicles/<int:pk>", fleet_api.VehicleDetailView.as_view(), name="staff-vehicle"),
    path("service-area", fleet_api.ServiceAreaView.as_view(), name="staff-service-area"),
    path("trips", trips_api.TripListCreateView.as_view(), name="staff-trips"),
    path("trips/<int:pk>", trips_api.TripDetailView.as_view(), name="staff-trip"),
    path("trips/<int:pk>/stops", trips_api.TripStopsView.as_view(), name="staff-trip-stops"),
    path("trips/<int:pk>/approve", trips_api.TripApproveView.as_view(), name="staff-trip-approve"),
    path("trips/<int:pk>/assign", trips_api.TripAssignView.as_view(), name="staff-trip-assign"),
    path("plan", trips_api.PlanSlotView.as_view(), name="staff-plan"),
]
