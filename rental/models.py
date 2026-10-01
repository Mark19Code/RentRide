from datetime import date, time
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone


phone_validator = RegexValidator(
    r"^(\+63|0)?9\d{9}$|^\+?\d[\d\s\-]{6,14}$",
    "Enter a valid phone number, for example 09171234567.",
)
MONEY = {"max_digits": 10, "decimal_places": 2, "validators": [MinValueValidator(Decimal("0.00"))]}


def default_rental_time():
    return time(9, 0)


class Vehicle(models.Model):
    class Category(models.TextChoices):
        SEDAN = "Sedan", "Sedan"
        SUV = "SUV", "SUV"
        MPV = "MPV", "MPV"
        PICKUP = "Pickup", "Pickup"
        HATCHBACK = "Hatchback", "Hatchback"
        CROSSOVER = "Crossover", "Crossover"
        LUXURY = "Luxury", "Luxury"

    class Transmission(models.TextChoices):
        AUTOMATIC = "Automatic", "Automatic"
        MANUAL = "Manual", "Manual"

    class FuelType(models.TextChoices):
        PETROL = "Petrol", "Petrol"
        DIESEL = "Diesel", "Diesel"
        HYBRID = "Hybrid", "Hybrid"
        ELECTRIC = "Electric", "Electric"

    class Status(models.TextChoices):
        AVAILABLE = "Available", "Available"
        RENTED = "Rented", "Rented"
        RESERVED = "Reserved", "Reserved"
        MAINTENANCE = "Maintenance", "Maintenance"
        INACTIVE = "Inactive", "Inactive"

    class GPSStatus(models.TextChoices):
        ACTIVE = "Active", "Active"
        INACTIVE = "Inactive", "Inactive"
        NO_SIGNAL = "No Signal", "No Signal"

    vehicle_code = models.CharField("Vehicle ID", max_length=10, unique=True, help_text="Example: RR-001")
    plate_number = models.CharField(max_length=12, unique=True)
    brand = models.CharField(max_length=40, db_index=True)
    model = models.CharField(max_length=60)
    year = models.PositiveSmallIntegerField()
    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    color = models.CharField(max_length=30)
    transmission = models.CharField(max_length=12, choices=Transmission.choices)
    fuel_type = models.CharField(max_length=12, choices=FuelType.choices)
    seats = models.PositiveSmallIntegerField(default=5)
    daily_rate = models.DecimalField(**MONEY)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.AVAILABLE, db_index=True)
    mileage = models.PositiveIntegerField(default=0)
    vin = models.CharField(max_length=17, unique=True)
    image = models.ImageField(upload_to="cars/", blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, default=Decimal("14.5995"))
    longitude = models.DecimalField(max_digits=9, decimal_places=6, default=Decimal("120.9842"))
    current_location = models.CharField(max_length=120, blank=True)
    speed = models.PositiveSmallIntegerField(default=0)
    gps_status = models.CharField(max_length=12, choices=GPSStatus.choices, default=GPSStatus.ACTIVE)
    last_gps_update = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["vehicle_code"]
        indexes = [models.Index(fields=["brand", "model"]), models.Index(fields=["status", "category"])]

    def __str__(self):
        return f"{self.vehicle_code} · {self.year} {self.brand} {self.model}"

    @property
    def display_name(self):
        return f"{self.brand} {self.model}"

    @property
    def rental_status(self):
        rental = self.rentals.filter(status__in=Rental.OPEN_STATUSES).order_by("pickup_date").first()
        return rental.status if rental else "Not rented"

    @property
    def maintenance_status(self):
        if self.status == self.Status.MAINTENANCE:
            return "Under maintenance"
        if self.maintenance_records.filter(status=Maintenance.Status.SCHEDULED).exists():
            return "Service scheduled"
        return "OK"

    def clean(self):
        errors = {}
        if self.year and not 1990 <= self.year <= date.today().year + 1:
            errors["year"] = "Enter a realistic model year."
        if self.latitude is not None and not -90 <= self.latitude <= 90:
            errors["latitude"] = "Latitude must be between -90 and 90."
        if self.longitude is not None and not -180 <= self.longitude <= 180:
            errors["longitude"] = "Longitude must be between -180 and 180."
        if errors:
            raise ValidationError(errors)

    def is_available_for(self, start, end, exclude_rental=None):
        if self.status in (self.Status.MAINTENANCE, self.Status.INACTIVE):
            return False
        clashes = self.rentals.filter(
            status__in=Rental.OPEN_STATUSES,
            pickup_date__lte=end,
            return_date__gte=start,
        )
        if exclude_rental and exclude_rental.pk:
            clashes = clashes.exclude(pk=exclude_rental.pk)
        return not clashes.exists()


class GPSLocation(models.Model):
    """A stored simulated GPS reading; it is not connected to GPS hardware."""
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="gps_history")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    location_label = models.CharField(max_length=120, blank=True)
    speed = models.PositiveSmallIntegerField(default=0)
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-recorded_at"]
        verbose_name = "GPS location"

    def __str__(self):
        return f"{self.vehicle.vehicle_code} @ {self.latitude}, {self.longitude}"


class Customer(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "Active", "Active"
        INACTIVE = "Inactive", "Inactive"
        BLACKLISTED = "Blacklisted", "Blacklisted"

    customer_code = models.CharField("Customer ID", max_length=10, unique=True, blank=True)
    full_name = models.CharField(max_length=120, db_index=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, validators=[phone_validator])
    address = models.CharField(max_length=255)
    license_number = models.CharField(max_length=20, unique=True)
    license_expiry = models.DateField()
    date_of_birth = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.customer_code} · {self.full_name}"

    @property
    def rental_count(self):
        return self.rentals.count()

    @property
    def license_valid(self):
        return self.license_expiry >= date.today()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.customer_code:
            self.customer_code = f"CUS-{self.pk:05d}"
            super().save(update_fields=["customer_code"])

    def clean(self):
        errors = {}
        if self.date_of_birth and (date.today() - self.date_of_birth).days < 18 * 365:
            errors["date_of_birth"] = "Customer must be at least 18 years old."
        if self.license_expiry and self.license_expiry < date.today():
            errors["license_expiry"] = "Driver license is expired."
        if errors:
            raise ValidationError(errors)


class Rental(models.Model):
    class Status(models.TextChoices):
        RESERVED = "Reserved", "Reserved"
        ACTIVE = "Active", "Active"
        COMPLETED = "Completed", "Completed"
        CANCELLED = "Cancelled", "Cancelled"
        OVERDUE = "Overdue", "Overdue"

    class PaymentStatus(models.TextChoices):
        UNPAID = "Unpaid", "Unpaid"
        PARTIAL = "Partial", "Partial"
        PAID = "Paid", "Paid"
        REFUNDED = "Refunded", "Refunded"

    OPEN_STATUSES = ("Reserved", "Active", "Overdue")
    rental_code = models.CharField("Rental ID", max_length=12, unique=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="rentals")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="rentals")
    pickup_date = models.DateField()
    pickup_time = models.TimeField(default=default_rental_time)
    return_date = models.DateField()
    return_time = models.TimeField(default=default_rental_time)
    daily_rate = models.DecimalField(**MONEY)
    insurance_fee = models.DecimalField(default=0, **MONEY)
    extra_mileage_fee = models.DecimalField(default=0, **MONEY)
    late_fee = models.DecimalField(default=0, **MONEY)
    service_fee = models.DecimalField("Additional service fee", default=0, **MONEY)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    payment_status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RESERVED, db_index=True)
    pickup_location = models.CharField(max_length=120, default="RentRide · Makati")
    return_location = models.CharField(max_length=120, default="RentRide · Makati")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-pickup_date", "-id"]
        indexes = [models.Index(fields=["vehicle", "pickup_date", "return_date"])]

    def __str__(self):
        return f"{self.rental_code} · {self.customer.full_name}"

    @property
    def duration_days(self):
        if not self.pickup_date or not self.return_date:
            return 0
        return max((self.return_date - self.pickup_date).days, 1)

    @property
    def base_cost(self):
        return (self.daily_rate or Decimal("0")) * self.duration_days

    @property
    def amount_paid(self):
        return self.payments.filter(status=Payment.Status.COMPLETED).aggregate(total=models.Sum("amount"))["total"] or Decimal("0")

    @property
    def balance(self):
        return self.total_cost - self.amount_paid

    def calculate_total(self):
        fees = (self.insurance_fee or 0) + (self.extra_mileage_fee or 0) + (self.late_fee or 0) + (self.service_fee or 0)
        return self.base_cost + fees

    def clean(self):
        errors = {}
        if self.pickup_date and self.return_date:
            if self.return_date < self.pickup_date:
                errors["return_date"] = "Return date cannot be before pickup."
            elif self.return_date == self.pickup_date and self.return_time <= self.pickup_time:
                errors["return_time"] = "Return time must be after pickup time for same-day rentals."
        if self.customer_id:
            if self.customer.status != Customer.Status.ACTIVE:
                errors["customer"] = "Only active customers can make a rental."
            elif self.return_date and self.customer.license_expiry < self.return_date:
                errors["customer"] = "The customer's license expires before the return date."
        if self.vehicle_id and self.pickup_date and self.return_date and self.status in self.OPEN_STATUSES:
            if self.return_date >= self.pickup_date and not self.vehicle.is_available_for(
                self.pickup_date, self.return_date, exclude_rental=self
            ):
                errors["vehicle"] = "This vehicle is unavailable for the selected dates."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.vehicle_id and not self.daily_rate:
            self.daily_rate = self.vehicle.daily_rate
        self.total_cost = self.calculate_total()
        super().save(*args, **kwargs)
        if not self.rental_code:
            self.rental_code = f"RNT-{self.pk:05d}"
            super().save(update_fields=["rental_code"])
        self.sync_vehicle_status()

    def sync_vehicle_status(self):
        vehicle = self.vehicle
        if vehicle.status in (Vehicle.Status.MAINTENANCE, Vehicle.Status.INACTIVE):
            return
        ongoing = vehicle.rentals.filter(status__in=(self.Status.ACTIVE, self.Status.OVERDUE)).exists()
        reserved = vehicle.rentals.filter(status=self.Status.RESERVED).exists()
        next_status = Vehicle.Status.RENTED if ongoing else Vehicle.Status.RESERVED if reserved else Vehicle.Status.AVAILABLE
        if vehicle.status != next_status:
            vehicle.status = next_status
            vehicle.save(update_fields=["status", "updated_at"])


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "Cash", "Cash"
        GCASH = "GCash", "GCash"
        MAYA = "Maya", "Maya"
        BANK = "Bank Transfer", "Bank Transfer"
        CARD = "Card", "Card"

    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        COMPLETED = "Completed", "Completed"
        REFUNDED = "Refunded", "Refunded"
        FAILED = "Failed", "Failed"

    payment_code = models.CharField("Payment ID", max_length=12, unique=True, blank=True)
    rental = models.ForeignKey(Rental, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    payment_date = models.DateField(default=date.today)
    method = models.CharField(max_length=15, choices=Method.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.COMPLETED)
    reference_number = models.CharField(max_length=30, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date", "-id"]

    def __str__(self):
        return f"{self.payment_code} · ₱{self.amount}"

    @property
    def customer(self):
        return self.rental.customer

    def clean(self):
        if self.rental_id and self.amount and self.status == self.Status.COMPLETED:
            paid = self.rental.payments.filter(status=self.Status.COMPLETED).exclude(pk=self.pk).aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
            if paid + self.amount > self.rental.total_cost:
                raise ValidationError({"amount": "Payment exceeds the remaining rental balance."})

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        updates = []
        if not self.payment_code:
            self.payment_code = f"PAY-{self.pk:05d}"
            updates.append("payment_code")
        if not self.reference_number:
            self.reference_number = f"REF{self.payment_date:%Y%m%d}{self.pk:05d}"
            updates.append("reference_number")
        if updates:
            super().save(update_fields=updates)
        self.sync_rental_payment_status()

    def sync_rental_payment_status(self):
        rental = self.rental
        paid = rental.amount_paid
        status = Rental.PaymentStatus.PAID if paid >= rental.total_cost and paid else Rental.PaymentStatus.PARTIAL if paid else Rental.PaymentStatus.UNPAID
        if self.status == self.Status.REFUNDED and not paid:
            status = Rental.PaymentStatus.REFUNDED
        if rental.payment_status != status:
            rental.payment_status = status
            rental.save(update_fields=["payment_status", "updated_at"])


class Maintenance(models.Model):
    class Type(models.TextChoices):
        OIL = "Oil Change", "Oil Change"
        TIRE = "Tire Replacement", "Tire Replacement"
        BRAKE = "Brake Service", "Brake Service"
        ENGINE = "Engine Check", "Engine Check"
        INSPECTION = "General Inspection", "General Inspection"
        REPAIR = "Repair", "Repair"
        PREVENTIVE = "Preventive Maintenance", "Preventive Maintenance"

    class Status(models.TextChoices):
        SCHEDULED = "Scheduled", "Scheduled"
        IN_PROGRESS = "In Progress", "In Progress"
        COMPLETED = "Completed", "Completed"

    maintenance_code = models.CharField("Maintenance ID", max_length=12, unique=True, blank=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="maintenance_records")
    type = models.CharField(max_length=30, choices=Type.choices)
    description = models.TextField(blank=True)
    date = models.DateField(default=date.today)
    cost = models.DecimalField(default=0, **MONEY)
    mileage = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SCHEDULED)
    next_service_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name_plural = "maintenance records"

    def __str__(self):
        return f"{self.maintenance_code} · {self.vehicle.vehicle_code} {self.type}"

    def clean(self):
        errors = {}
        if self.next_service_date and self.date and self.next_service_date <= self.date:
            errors["next_service_date"] = "Next service date must be after the service date."
        if self.vehicle_id and self.status == self.Status.IN_PROGRESS:
            if self.vehicle.rentals.filter(status__in=(Rental.Status.ACTIVE, Rental.Status.OVERDUE)).exists():
                errors["vehicle"] = "The vehicle is currently on an active rental."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.maintenance_code:
            self.maintenance_code = f"MNT-{self.pk:05d}"
            super().save(update_fields=["maintenance_code"])
        self.sync_vehicle_status()

    def sync_vehicle_status(self):
        vehicle = self.vehicle
        in_service = vehicle.maintenance_records.filter(status=self.Status.IN_PROGRESS).exists()
        if in_service:
            next_status = Vehicle.Status.MAINTENANCE
        elif vehicle.status == Vehicle.Status.MAINTENANCE:
            active_rental = vehicle.rentals.filter(status__in=(Rental.Status.ACTIVE, Rental.Status.OVERDUE)).exists()
            next_status = Vehicle.Status.RENTED if active_rental else Vehicle.Status.AVAILABLE
        else:
            return
        if vehicle.status != next_status:
            vehicle.status = next_status
            vehicle.save(update_fields=["status", "updated_at"])
