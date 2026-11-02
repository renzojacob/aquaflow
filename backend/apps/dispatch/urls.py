from django.urls import path

from . import api

urlpatterns = [
    path("orders", api.StaffOrderListView.as_view(), name="staff-orders"),
    path("orders/<int:pk>", api.StaffOrderDetailView.as_view(), name="staff-order"),
    path("orders/<int:pk>/<str:action>", api.StaffOrderActionView.as_view(), name="staff-order-action"),
    path("riders", api.RiderListView.as_view(), name="staff-riders"),
    path("stock", api.StockView.as_view(), name="staff-stock"),
    path("stock/adjust", api.StockAdjustView.as_view(), name="staff-stock-adjust"),
    path("summary", api.SummaryView.as_view(), name="staff-summary"),
]
