from django import forms
from django.contrib.auth import get_user_model

from .models import Customer, Maintenance, Payment, Rental, Vehicle


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} control".strip()
            if field.required:
                field.widget.attrs.setdefault("aria-required", "true")


class VehicleForm(StyledModelForm):
    class Meta:
        model = Vehicle
        fields = ["vehicle_code", "plate_number", "brand", "model", "year", "category", "color", "transmission", "fuel_type", "seats", "daily_rate", "status", "mileage", "vin", "image", "latitude", "longitude", "current_location", "speed", "gps_status"]
        widgets = {"daily_rate": forms.NumberInput(attrs={"min": "0", "step": "0.01"}), "year": forms.NumberInput(attrs={"min": 1990}), "mileage": forms.NumberInput(attrs={"min": 0}), "latitude": forms.NumberInput(attrs={"step": "0.000001"}), "longitude": forms.NumberInput(attrs={"step": "0.000001"}), "current_location": forms.TextInput(attrs={"placeholder": "e.g. Makati City"})}


class CustomerForm(StyledModelForm):
    class Meta:
        model = Customer
        fields = ["full_name", "email", "phone", "address", "license_number", "license_expiry", "date_of_birth", "status"]
        widgets = {"license_expiry": forms.DateInput(attrs={"type": "date"}), "date_of_birth": forms.DateInput(attrs={"type": "date"})}


class RentalForm(StyledModelForm):
    class Meta:
        model = Rental
        fields = ["customer", "vehicle", "pickup_date", "pickup_time", "return_date", "return_time", "daily_rate", "insurance_fee", "extra_mileage_fee", "late_fee", "service_fee", "status", "pickup_location", "return_location", "notes"]
        widgets = {"pickup_date": forms.DateInput(attrs={"type": "date"}), "return_date": forms.DateInput(attrs={"type": "date"}), "pickup_time": forms.TimeInput(attrs={"type": "time"}), "return_time": forms.TimeInput(attrs={"type": "time"}), "daily_rate": forms.NumberInput(attrs={"min": "0", "step": "0.01"}), "insurance_fee": forms.NumberInput(attrs={"min": "0", "step": "0.01"}), "extra_mileage_fee": forms.NumberInput(attrs={"min": "0", "step": "0.01"}), "late_fee": forms.NumberInput(attrs={"min": "0", "step": "0.01"}), "service_fee": forms.NumberInput(attrs={"min": "0", "step": "0.01"}), "notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = Customer.objects.filter(status=Customer.Status.ACTIVE)
        self.fields["vehicle"].queryset = Vehicle.objects.exclude(status__in=[Vehicle.Status.MAINTENANCE, Vehicle.Status.INACTIVE])
        if not self.instance.pk and not self.initial.get("daily_rate"):
            self.fields["daily_rate"].required = False

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("daily_rate") and cleaned_data.get("vehicle"):
            cleaned_data["daily_rate"] = cleaned_data["vehicle"].daily_rate
        return cleaned_data


class PaymentForm(StyledModelForm):
    class Meta:
        model = Payment
        fields = ["rental", "amount", "payment_date", "method", "status", "reference_number"]
        widgets = {"amount": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}), "payment_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rental"].queryset = Rental.objects.exclude(status=Rental.Status.CANCELLED)
        self.fields["reference_number"].required = False


class MaintenanceForm(StyledModelForm):
    class Meta:
        model = Maintenance
        fields = ["vehicle", "type", "description", "date", "cost", "mileage", "status", "next_service_date"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"}), "next_service_date": forms.DateInput(attrs={"type": "date"}), "cost": forms.NumberInput(attrs={"min": "0", "step": "0.01"}), "mileage": forms.NumberInput(attrs={"min": 0}), "description": forms.Textarea(attrs={"rows": 3})}


class ProfileForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ["first_name", "last_name", "email"]
        widgets = {"first_name": forms.TextInput(attrs={"class": "control"}), "last_name": forms.TextInput(attrs={"class": "control"}), "email": forms.EmailInput(attrs={"class": "control"})}
