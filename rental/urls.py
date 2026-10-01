from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "rental"
urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.RentRideLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("vehicles/", views.vehicle_list, name="vehicles"),
    path("vehicles/add/", views.vehicle_create, name="vehicle_create"),
    path("vehicles/<int:pk>/", views.vehicle_detail, name="vehicle_detail"),
    path("vehicles/<int:pk>/edit/", views.vehicle_edit, name="vehicle_edit"),
    path("vehicles/<int:pk>/delete/", views.vehicle_delete, name="vehicle_delete"),
    path("customers/", views.customer_list, name="customers"),
    path("customers/add/", views.customer_create, name="customer_create"),
    path("customers/<int:pk>/", views.customer_detail, name="customer_detail"),
    path("customers/<int:pk>/edit/", views.customer_edit, name="customer_edit"),
    path("customers/<int:pk>/delete/", views.customer_delete, name="customer_delete"),
    path("rentals/", views.rental_list, name="rentals"),
    path("rentals/new/", views.rental_create, name="rental_create"),
    path("rentals/<int:pk>/edit/", views.rental_edit, name="rental_edit"),
    path("gps/", views.gps_tracking, name="gps_tracking"),
    path("gps/simulate/", views.gps_simulate, name="gps_simulate"),
    path("maintenance/", views.maintenance_list, name="maintenance"),
    path("maintenance/add/", views.maintenance_create, name="maintenance_create"),
    path("payments/", views.payment_list, name="payments"),
    path("payments/add/", views.payment_create, name="payment_create"),
    path("payments/<int:pk>/edit/", views.payment_edit, name="payment_edit"),
    path("history/", views.rental_history, name="history"),
    path("history/export/", views.history_export, name="history_export"),
    path("maintenance/<int:pk>/edit/", views.maintenance_edit, name="maintenance_edit"),
    path("reports/", views.reports, name="reports"),
    path("settings/", views.settings_page, name="settings"),
]
