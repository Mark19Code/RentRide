import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from rental.models import Customer, GPSLocation, Maintenance, Payment, Rental, Vehicle


CITY_POINTS = [
    ("Makati City", 14.5547, 121.0244), ("Quezon City", 14.6760, 121.0437),
    ("Manila", 14.5995, 120.9842), ("Pasig City", 14.5764, 121.0851),
    ("Taguig City", 14.5176, 121.0509), ("Pasay City", 14.5378, 121.0014),
    ("Parañaque", 14.4793, 121.0198), ("Muntinlupa", 14.4081, 121.0415),
    ("Antipolo", 14.6255, 121.1245), ("Caloocan", 14.6507, 120.9668),
    ("Las Piñas", 14.4445, 120.9939),
]
CATALOG = [
    ("Toyota", "Vios", "Sedan"), ("Toyota", "Wigo", "Hatchback"), ("Toyota", "Corolla Altis", "Sedan"),
    ("Toyota", "Innova", "MPV"), ("Toyota", "Fortuner", "SUV"), ("Toyota", "Avanza", "MPV"),
    ("Toyota", "Rush", "SUV"), ("Toyota", "Raize", "Crossover"), ("Honda", "City", "Sedan"),
    ("Honda", "Civic", "Sedan"), ("Honda", "BR-V", "SUV"), ("Honda", "HR-V", "Crossover"),
    ("Honda", "CR-V", "SUV"), ("Mitsubishi", "Mirage", "Hatchback"), ("Mitsubishi", "Xpander", "MPV"),
    ("Mitsubishi", "Montero Sport", "SUV"), ("Nissan", "Almera", "Sedan"), ("Nissan", "Navara", "Pickup"),
    ("Nissan", "Terra", "SUV"), ("Ford", "Ranger", "Pickup"), ("Ford", "Everest", "SUV"),
    ("Hyundai", "Accent", "Sedan"), ("Hyundai", "Tucson", "SUV"), ("Kia", "Soluto", "Sedan"),
    ("Kia", "Carnival", "MPV"), ("Mazda", "2", "Hatchback"), ("Mazda", "3", "Sedan"),
    ("Suzuki", "Swift", "Hatchback"), ("Suzuki", "Ertiga", "MPV"), ("Isuzu", "D-Max", "Pickup"),
    ("Isuzu", "mu-X", "SUV"), ("Subaru", "Forester", "SUV"), ("Volkswagen", "T-Cross", "Crossover"),
    ("BMW", "3 Series", "Luxury"), ("Mercedes-Benz", "C-Class", "Luxury"), ("Audi", "A4", "Luxury"),
    ("Lexus", "ES", "Luxury"), ("Chevrolet", "Trailblazer", "SUV"), ("Jeep", "Compass", "SUV"),
    ("MG", "ZS", "Crossover"), ("Geely", "Coolray", "Crossover"), ("BYD", "Atto 3", "Crossover"),
    ("Chery", "Tiggo 7", "SUV"),
]
COLORS = ["Pearl White", "Midnight Black", "Silver", "Graphite Gray", "Deep Blue", "Crimson Red", "Champagne"]
FIRST_NAMES = ["Alex", "Jamie", "Morgan", "Taylor", "Jordan", "Casey", "Riley", "Sam", "Avery", "Cameron", "Drew", "Skyler", "Robin", "Quinn", "Reese", "Kris", "Mika", "Noel"]
LAST_NAMES = ["Santos", "Reyes", "Cruz", "Garcia", "Mendoza", "Rivera", "Bautista", "Flores", "Navarro", "Castillo", "Aquino", "Ramos", "Villanueva", "Torres"]


class Command(BaseCommand):
    help = "Create fictional RentRide demo records (safe to rerun)."

    def add_arguments(self, parser):
        parser.add_argument("--skip-admin", action="store_true", help="Do not create the well-known development demo admin.")

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(481516)
        today = timezone.localdate()
        created_vehicles = 0
        for index in range(1, 155):
            if Vehicle.objects.filter(vehicle_code=f"RR-{index:03d}").exists():
                continue
            brand, model, category = CATALOG[(index - 1) % len(CATALOG)]
            city, lat, lng = CITY_POINTS[(index * 7) % len(CITY_POINTS)]
            premium = category == "Luxury"
            rate = rng.randrange(1400, 3800, 100) if not premium else rng.randrange(5500, 9800, 100)
            vehicle = Vehicle.objects.create(
                vehicle_code=f"RR-{index:03d}", plate_number=f"N{rng.randint(1000, 9999)}{chr(65 + index % 26)}",
                brand=brand, model=model, year=rng.randint(2019, 2026), category=category,
                color=rng.choice(COLORS), transmission="Manual" if category in ("Pickup", "Hatchback") and index % 5 == 0 else "Automatic",
                fuel_type="Hybrid" if brand in ("Toyota", "Lexus") and index % 6 == 0 else "Diesel" if category in ("Pickup", "SUV") and index % 3 == 0 else "Petrol",
                seats=7 if category in ("SUV", "MPV") else 5, daily_rate=Decimal(rate),
                status=rng.choices(["Available", "Rented", "Reserved", "Maintenance", "Inactive"], [55, 22, 10, 9, 4])[0],
                mileage=rng.randint(5000, 125000), vin=f"RR{index:015d}", latitude=Decimal(str(lat + rng.uniform(-0.006, 0.006))).quantize(Decimal("0.000001")),
                longitude=Decimal(str(lng + rng.uniform(-0.006, 0.006))).quantize(Decimal("0.000001")), current_location=city,
                speed=rng.randint(0, 58), gps_status="Active" if index % 17 else "No Signal",
            )
            GPSLocation.objects.create(vehicle=vehicle, latitude=vehicle.latitude, longitude=vehicle.longitude, location_label=city, speed=vehicle.speed, recorded_at=timezone.now() - timedelta(minutes=rng.randint(1, 240)))
            created_vehicles += 1

        customer_ids = []
        for index in range(1, 36):
            code = f"CUS-{index:05d}"
            customer, created = Customer.objects.get_or_create(customer_code=code, defaults={
                "full_name": f"{FIRST_NAMES[(index * 3) % len(FIRST_NAMES)]} {LAST_NAMES[(index * 5) % len(LAST_NAMES)]}",
                "email": f"demo.customer{index:03d}@example.test", "phone": f"09{rng.randint(100000000, 999999999)}",
                "address": f"{rng.randint(10, 999)} {rng.choice(['Ayala Avenue', 'EDSA', 'Commonwealth Avenue', 'Ortigas Avenue', 'Taft Avenue'])}, {CITY_POINTS[index % len(CITY_POINTS)][0]}",
                "license_number": f"D{index:09d}", "license_expiry": today + timedelta(days=rng.randint(200, 1800)),
                "date_of_birth": today - timedelta(days=rng.randint(22 * 365, 58 * 365)), "status": "Active",
            })
            customer_ids.append(customer.pk)

        vehicles = list(Vehicle.objects.order_by("id")[:154])
        customers = list(Customer.objects.filter(pk__in=customer_ids))
        rental_created = 0
        for index in range(min(60, len(vehicles))):
            code = f"RNT-{index + 1:05d}"
            if Rental.objects.filter(rental_code=code).exists():
                continue
            offset = (index % 12) - 5
            pickup = today + timedelta(days=offset)
            duration = 1 + index % 6
            status = "Completed" if offset < -1 else "Active" if offset <= 0 < offset + duration else "Reserved"
            if status == "Active":
                pickup = min(pickup, today - timedelta(days=1))
            customer = customers[index % len(customers)]
            vehicle = vehicles[index]
            rental = Rental.objects.create(customer=customer, vehicle=vehicle, pickup_date=pickup, return_date=pickup + timedelta(days=duration), daily_rate=vehicle.daily_rate,
                insurance_fee=Decimal("650.00"), service_fee=Decimal("250.00"), status=status, pickup_location=f"RentRide · {CITY_POINTS[index % len(CITY_POINTS)][0]}", return_location="RentRide · Makati")
            rental_created += 1
            if index % 2 == 0:
                paid_amount = min(rental.total_cost, (rental.total_cost * Decimal("0.5")).quantize(Decimal("0.01")))
                Payment.objects.create(rental=rental, amount=paid_amount, payment_date=pickup, method=["Cash", "GCash", "Maya", "Bank Transfer", "Card"][index % 5], status="Completed")

        maintenance_created = 0
        for index, vehicle in enumerate(vehicles[::9][:18], start=1):
            code = f"MNT-{index:05d}"
            if Maintenance.objects.filter(maintenance_code=code).exists():
                continue
            status = "In Progress" if index % 5 == 0 else "Scheduled" if index % 2 else "Completed"
            Maintenance.objects.create(vehicle=vehicle, type=["Oil Change", "Tire Replacement", "Brake Service", "General Inspection", "Preventive Maintenance"][index % 5],
                description="Routine fleet service · demo record", date=today - timedelta(days=index * 3), cost=Decimal(1800 + index * 175), mileage=vehicle.mileage,
                status=status, next_service_date=today + timedelta(days=45 + index))
            maintenance_created += 1

        if not options["skip_admin"]:
            User = get_user_model()
            admin_user, created = User.objects.get_or_create(username="admin", defaults={"email": "admin@rentridedemo.local", "is_staff": True, "is_superuser": True})
            if created:
                admin_user.set_password("Admin@12345")
                admin_user.save()
        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {Vehicle.objects.count()} vehicles, {Customer.objects.count()} customers, "
            f"{Rental.objects.count()} rentals, {Payment.objects.count()} payments, "
            f"{Maintenance.objects.count()} maintenance records. Added this run: {created_vehicles} vehicles, "
            f"{rental_created} rentals, {maintenance_created} maintenance records."
        ))
        if not options["skip_admin"]:
            self.stdout.write("Demo login: admin / Admin@12345")
