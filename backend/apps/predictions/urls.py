from django.urls import path

from . import views

urlpatterns = [
    path("customer/refill/", views.CustomerRefillView.as_view(), name="customer-refill"),
    path("customer/refill/reorder/", views.CustomerReorderView.as_view(), name="customer-refill-reorder"),
    path("v1/dispatch/demand", views.DemandView.as_view(), name="staff-demand"),
    path("v1/dispatch/refill-accuracy", views.RefillAccuracyView.as_view(), name="staff-refill-accuracy"),
]
