from django.contrib import admin

from .models import Customer, GPSLocation, Maintenance, Payment, Rental, Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("vehicle_code", "brand", "model", "plate_number", "category", "status", "daily_rate")
    list_filter = ("status", "category", "brand", "fuel_type")
    search_fields = ("vehicle_code", "plate_number", "brand", "model", "vin")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("customer_code", "full_name", "email", "phone", "status", "license_expiry")
    list_filter = ("status",)
    search_fields = ("customer_code", "full_name", "email", "license_number")


@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = ("rental_code", "customer", "vehicle", "pickup_date", "return_date", "status", "payment_status", "total_cost")
    list_filter = ("status", "payment_status", "pickup_date")
    search_fields = ("rental_code", "customer__full_name", "vehicle__vehicle_code")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_code", "rental", "amount", "method", "status", "payment_date")
    list_filter = ("status", "method", "payment_date")


@admin.register(Maintenance)
class MaintenanceAdmin(admin.ModelAdmin):
    list_display = ("maintenance_code", "vehicle", "type", "date", "status", "cost")
    list_filter = ("status", "type", "date")


@admin.register(GPSLocation)
class GPSLocationAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "location_label", "latitude", "longitude", "speed", "recorded_at")
    list_filter = ("recorded_at",)
    search_fields = ("vehicle__vehicle_code", "location_label")
