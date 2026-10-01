from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import Customer, GPSLocation, Payment, Rental, Vehicle


class RentalModelTests(TestCase):
    def setUp(self):
        self.vehicle = Vehicle.objects.create(
            vehicle_code="RR-TEST1", plate_number="ABC1234", brand="Toyota", model="Vios", year=2024,
            category="Sedan", color="White", transmission="Automatic", fuel_type="Petrol", seats=5,
            daily_rate=Decimal("1800.00"), vin="TESTVIN0000000001", current_location="Makati City",
        )
        self.customer = Customer.objects.create(
            full_name="Demo Customer", email="demo@example.test", phone="09171234567", address="Makati City",
            license_number="DEMO123456", license_expiry=date.today() + timedelta(days=800),
            date_of_birth=date.today() - timedelta(days=30 * 365),
        )

    def rental(self, **overrides):
        today = timezone.localdate()
        values = {
            "customer": self.customer,
            "vehicle": self.vehicle,
            "pickup_date": today + timedelta(days=2),
            "return_date": today + timedelta(days=4),
            "daily_rate": Decimal("1800.00"),
            "insurance_fee": Decimal("500.00"),
            "status": Rental.Status.RESERVED,
        }
        values.update(overrides)
        return Rental.objects.create(**values)

    def test_total_cost_includes_days_and_optional_fees(self):
        rental = self.rental()
        self.assertEqual(rental.duration_days, 2)
        self.assertEqual(rental.total_cost, Decimal("4100.00"))

    def test_overlapping_rental_is_rejected_by_validation(self):
        existing = self.rental()
        duplicate = Rental(
            customer=self.customer, vehicle=self.vehicle,
            pickup_date=existing.pickup_date + timedelta(days=1),
            return_date=existing.return_date + timedelta(days=1),
            daily_rate=self.vehicle.daily_rate, status=Rental.Status.RESERVED,
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_reserved_rental_updates_vehicle_status(self):
        self.rental()
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, Vehicle.Status.RESERVED)

    def test_completed_payment_updates_rental_balance_status(self):
        rental = self.rental()
        Payment.objects.create(rental=rental, amount=Decimal("1000.00"), method=Payment.Method.CASH)
        rental.refresh_from_db()
        self.assertEqual(rental.payment_status, Rental.PaymentStatus.PARTIAL)
        self.assertEqual(rental.balance, Decimal("3100.00"))


class WorkspaceViewTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.user = get_user_model().objects.create_user(username="test-admin", password="safe-test-pass")
        self.client.force_login(self.user)
        self.vehicle = Vehicle.objects.create(
            vehicle_code="RR-WEB01", plate_number="WEB1234", brand="Honda", model="City", year=2023,
            category="Sedan", color="Blue", transmission="Automatic", fuel_type="Petrol", seats=5,
            daily_rate=Decimal("2000.00"), vin="WEBVIN00000000001", current_location="Makati City",
        )

    def test_workspace_pages_render(self):
        from django.urls import reverse
        page_names = [
            "dashboard", "vehicles", "vehicle_create", "customers", "customer_create",
            "rentals", "rental_create", "gps_tracking", "maintenance", "maintenance_create",
            "payments", "payment_create", "history", "reports", "settings",
        ]
        for name in page_names:
            with self.subTest(page=name):
                response = self.client.get(reverse(f"rental:{name}"))
                self.assertEqual(response.status_code, 200)

    def test_gps_simulation_and_csv_export(self):
        from django.urls import reverse
        response = self.client.post(reverse("rental:gps_simulate"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["updated"], 1)
        self.assertEqual(GPSLocation.objects.filter(vehicle=self.vehicle).count(), 1)
        export = self.client.get(reverse("rental:history_export"))
        self.assertEqual(export.status_code, 200)
        self.assertTrue(export["Content-Type"].startswith("text/csv"))

    def test_deployment_bootstrap_creates_admins_without_resetting_existing_passwords(self):
        from django.contrib.auth import get_user_model
        from django.core.management import call_command
        user_model = get_user_model()
        env = {
            "DJANGO_ADMIN_1_USERNAME": "deploy-admin",
            "DJANGO_ADMIN_1_PASSWORD": "deployment-safe-test-password",
        }
        with patch.dict("os.environ", env, clear=False):
            call_command("bootstrap_admins", verbosity=0)
            user = user_model.objects.get(username="deploy-admin")
            self.assertTrue(user.is_superuser)
            self.assertTrue(user.check_password("deployment-safe-test-password"))
            user.set_password("changed-after-first-login")
            user.save(update_fields=["password"])
            call_command("bootstrap_admins", verbosity=0)
            user.refresh_from_db()
            self.assertTrue(user.check_password("changed-after-first-login"))

    def test_admin_can_log_out_and_log_back_in(self):
        from django.urls import reverse
        logout_response = self.client.post(reverse("rental:logout"), follow=True)
        self.assertEqual(logout_response.status_code, 200)
        self.assertFalse("_auth_user_id" in self.client.session)
        login_response = self.client.post(reverse("rental:login"), {
            "username": "test-admin",
            "password": "safe-test-pass",
        }, follow=True)
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue("_auth_user_id" in self.client.session)
