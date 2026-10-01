import csv
import json
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CustomerForm, MaintenanceForm, PaymentForm, ProfileForm, RentalForm, VehicleForm
from .models import Customer, GPSLocation, Maintenance, Payment, Rental, Vehicle


class RentRideLoginView(LoginView):
    template_name = "rental/login.html"
    redirect_authenticated_user = True


def home(request):
    return redirect("rental:dashboard" if request.user.is_authenticated else "rental:login")


@login_required
def dashboard(request):
    today = timezone.localdate()
    completed_revenue = Payment.objects.filter(status=Payment.Status.COMPLETED).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    month_revenue = Payment.objects.filter(status=Payment.Status.COMPLETED, payment_date__year=today.year, payment_date__month=today.month).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    recent_rentals = Rental.objects.select_related("customer", "vehicle")[:6]
    recent_gps = GPSLocation.objects.select_related("vehicle")[:5]
    months = []
    for offset in range(5, -1, -1):
        month = today.month - offset
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        amount = Payment.objects.filter(status=Payment.Status.COMPLETED, payment_date__year=year, payment_date__month=month).aggregate(total=Sum("amount"))["total"] or 0
        months.append({"label": timezone.datetime(year, month, 1).strftime("%b"), "value": float(amount)})
    context = {
        "page_title": "Dashboard",
        "total_vehicles": Vehicle.objects.count(),
        "available_vehicles": Vehicle.objects.filter(status=Vehicle.Status.AVAILABLE).count(),
        "rented_vehicles": Vehicle.objects.filter(status=Vehicle.Status.RENTED).count(),
        "maintenance_vehicles": Vehicle.objects.filter(status=Vehicle.Status.MAINTENANCE).count(),
        "total_customers": Customer.objects.count(),
        "active_rentals": Rental.objects.filter(status__in=Rental.OPEN_STATUSES).count(),
        "today_rentals": Rental.objects.filter(pickup_date=today).count(),
        "revenue": completed_revenue,
        "month_revenue": month_revenue,
        "recent_rentals": recent_rentals,
        "recent_gps": recent_gps,
        "chart_labels": json.dumps([item["label"] for item in months]),
        "chart_values": json.dumps([item["value"] for item in months]),
        "category_data": json.dumps(list(Vehicle.objects.values("category").annotate(total=Count("id")).order_by("category"))),
    }
    return render(request, "rental/dashboard.html", context)


@login_required
def vehicle_list(request):
    vehicles = Vehicle.objects.all()
    query = request.GET.get("q", "").strip()
    if query:
        from django.db.models import Q
        vehicles = vehicles.filter(Q(vehicle_code__icontains=query) | Q(plate_number__icontains=query) | Q(brand__icontains=query) | Q(model__icontains=query))
    for key, field in (("brand", "brand"), ("category", "category"), ("status", "status"), ("transmission", "transmission"), ("fuel_type", "fuel_type")):
        value = request.GET.get(key)
        if value:
            vehicles = vehicles.filter(**{field: value})
    minimum, maximum = request.GET.get("min_rate"), request.GET.get("max_rate")
    if minimum:
        vehicles = vehicles.filter(daily_rate__gte=minimum)
    if maximum:
        vehicles = vehicles.filter(daily_rate__lte=maximum)
    page = Paginator(vehicles, 12).get_page(request.GET.get("page"))
    return render(request, "rental/vehicles.html", {
        "page_title": "Vehicles", "page_obj": page, "vehicles": page.object_list,
        "available_vehicles": Vehicle.objects.filter(status=Vehicle.Status.AVAILABLE).count(),
        "brands": Vehicle.objects.order_by("brand").values_list("brand", flat=True).distinct(),
        "categories": Vehicle.Category.choices, "statuses": Vehicle.Status.choices,
        "transmissions": Vehicle.Transmission.choices, "fuel_types": Vehicle.FuelType.choices,
        "filters": request.GET,
    })


@login_required
def vehicle_detail(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    return render(request, "rental/vehicle_detail.html", {"page_title": vehicle.vehicle_code, "vehicle": vehicle, "rentals": vehicle.rentals.select_related("customer")[:8], "maintenance_records": vehicle.maintenance_records[:5]})


@login_required
def vehicle_create(request):
    form = VehicleForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        vehicle = form.save()
        messages.success(request, f"{vehicle.vehicle_code} was added to your fleet.")
        return redirect("rental:vehicle_detail", pk=vehicle.pk)
    return render(request, "rental/form_page.html", {"page_title": "Add vehicle", "form": form, "back_url": "rental:vehicles", "submit_label": "Save vehicle"})


@login_required
def vehicle_edit(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    form = VehicleForm(request.POST or None, request.FILES or None, instance=vehicle)
    if form.is_valid():
        form.save()
        messages.success(request, "Vehicle details updated.")
        return redirect("rental:vehicle_detail", pk=vehicle.pk)
    return render(request, "rental/form_page.html", {"page_title": f"Edit {vehicle.vehicle_code}", "form": form, "back_url": "rental:vehicle_detail", "back_args": [vehicle.pk], "submit_label": "Save changes"})


@login_required
@require_POST
def vehicle_delete(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if vehicle.rentals.exists():
        messages.error(request, "This vehicle has rental history and cannot be deleted. Mark it inactive instead.")
    else:
        vehicle.delete()
        messages.success(request, "Vehicle deleted.")
    return redirect("rental:vehicles")


@login_required
def customer_list(request):
    customers = Customer.objects.annotate(rentals_total=Count("rentals")).order_by("full_name", "pk")
    query = request.GET.get("q", "").strip()
    if query:
        from django.db.models import Q
        customers = customers.filter(Q(customer_code__icontains=query) | Q(full_name__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query))
    status = request.GET.get("status")
    if status:
        customers = customers.filter(status=status)
    page = Paginator(customers, 14).get_page(request.GET.get("page"))
    return render(request, "rental/customers.html", {"page_title": "Customers", "customers": page.object_list, "page_obj": page, "statuses": Customer.Status.choices, "filters": request.GET})


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    return render(request, "rental/customer_detail.html", {"page_title": customer.full_name, "customer": customer, "rentals": customer.rentals.select_related("vehicle")[:12]})


@login_required
def customer_create(request):
    form = CustomerForm(request.POST or None)
    if form.is_valid():
        customer = form.save()
        messages.success(request, "Customer profile created.")
        return redirect("rental:customer_detail", pk=customer.pk)
    return render(request, "rental/form_page.html", {"page_title": "Add customer", "form": form, "back_url": "rental:customers", "submit_label": "Save customer"})


@login_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    if form.is_valid():
        form.save()
        messages.success(request, "Customer profile updated.")
        return redirect("rental:customer_detail", pk=customer.pk)
    return render(request, "rental/form_page.html", {"page_title": "Edit customer", "form": form, "back_url": "rental:customer_detail", "back_args": [customer.pk], "submit_label": "Save changes"})


@login_required
@require_POST
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if customer.rentals.exists():
        messages.error(request, "This customer has rental history and cannot be deleted.")
    else:
        customer.delete()
        messages.success(request, "Customer deleted.")
    return redirect("rental:customers")


@login_required
def rental_list(request):
    rentals = Rental.objects.select_related("customer", "vehicle")
    query = request.GET.get("q", "").strip()
    if query:
        from django.db.models import Q
        rentals = rentals.filter(Q(rental_code__icontains=query) | Q(customer__full_name__icontains=query) | Q(vehicle__vehicle_code__icontains=query))
    if request.GET.get("status"):
        rentals = rentals.filter(status=request.GET["status"])
    page = Paginator(rentals, 14).get_page(request.GET.get("page"))
    return render(request, "rental/rentals.html", {
        "page_title": "Rentals", "rentals": page.object_list, "page_obj": page,
        "statuses": Rental.Status.choices, "filters": request.GET,
        "open_count": Rental.objects.filter(status__in=Rental.OPEN_STATUSES).count(),
        "completed_count": Rental.objects.filter(status=Rental.Status.COMPLETED).count(),
        "rental_value": Rental.objects.aggregate(total=Sum("total_cost"))["total"] or 0,
    })


@login_required
def rental_create(request):
    form = RentalForm(request.POST or None, initial={"daily_rate": request.GET.get("rate", ""), "pickup_date": timezone.localdate(), "return_date": timezone.localdate() + timedelta(days=1)})
    if form.is_valid():
        rental = form.save()
        messages.success(request, f"Rental {rental.rental_code} created.")
        return redirect("rental:rentals")
    return render(request, "rental/form_page.html", {"page_title": "Create rental", "form": form, "back_url": "rental:rentals", "submit_label": "Create rental", "show_rental_calculator": True})


@login_required
def rental_edit(request, pk):
    rental = get_object_or_404(Rental, pk=pk)
    form = RentalForm(request.POST or None, instance=rental)
    if form.is_valid():
        rental = form.save()
        messages.success(request, f"{rental.rental_code} updated.")
        return redirect("rental:rentals")
    return render(request, "rental/form_page.html", {"page_title": f"Edit {rental.rental_code}", "form": form, "back_url": "rental:rentals", "submit_label": "Save changes", "show_rental_calculator": True})


@login_required
def payment_list(request):
    payments = Payment.objects.select_related("rental__customer", "rental__vehicle")
    query = request.GET.get("q", "").strip()
    if query:
        from django.db.models import Q
        payments = payments.filter(Q(payment_code__icontains=query) | Q(rental__rental_code__icontains=query) | Q(rental__customer__full_name__icontains=query))
    page = Paginator(payments, 15).get_page(request.GET.get("page"))
    total = Payment.objects.filter(status=Payment.Status.COMPLETED).aggregate(total=Sum("amount"))["total"] or 0
    return render(request, "rental/payments.html", {"page_title": "Payments", "payments": page.object_list, "page_obj": page, "total_paid": total, "filters": request.GET})


@login_required
def payment_create(request):
    form = PaymentForm(request.POST or None)
    if form.is_valid():
        payment = form.save()
        messages.success(request, f"Payment {payment.payment_code} recorded. Payments are simulated; no gateway is connected.")
        return redirect("rental:payments")
    return render(request, "rental/form_page.html", {"page_title": "Record payment", "form": form, "back_url": "rental:payments", "submit_label": "Record payment"})


@login_required
def payment_edit(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    form = PaymentForm(request.POST or None, instance=payment)
    if form.is_valid():
        form.save()
        messages.success(request, f"{payment.payment_code} updated.")
        return redirect("rental:payments")
    return render(request, "rental/form_page.html", {"page_title": f"Edit {payment.payment_code}", "form": form, "back_url": "rental:payments", "submit_label": "Save changes"})


@login_required
def maintenance_list(request):
    records = Maintenance.objects.select_related("vehicle")
    if request.GET.get("status"):
        records = records.filter(status=request.GET["status"])
    page = Paginator(records, 14).get_page(request.GET.get("page"))
    return render(request, "rental/maintenance.html", {"page_title": "Maintenance", "records": page.object_list, "page_obj": page, "statuses": Maintenance.Status.choices, "filters": request.GET, "open_count": Maintenance.objects.filter(status=Maintenance.Status.IN_PROGRESS).count(), "total_vehicles": Vehicle.objects.count()})


@login_required
def maintenance_create(request):
    form = MaintenanceForm(request.POST or None)
    if form.is_valid():
        record = form.save()
        messages.success(request, f"Maintenance record {record.maintenance_code} created.")
        return redirect("rental:maintenance")
    return render(request, "rental/form_page.html", {"page_title": "Add maintenance record", "form": form, "back_url": "rental:maintenance", "submit_label": "Save record"})


@login_required
def maintenance_edit(request, pk):
    record = get_object_or_404(Maintenance, pk=pk)
    form = MaintenanceForm(request.POST or None, instance=record)
    if form.is_valid():
        form.save()
        messages.success(request, f"{record.maintenance_code} updated.")
        return redirect("rental:maintenance")
    return render(request, "rental/form_page.html", {"page_title": f"Edit {record.maintenance_code}", "form": form, "back_url": "rental:maintenance", "submit_label": "Save changes"})


@login_required
def gps_tracking(request):
    vehicles = Vehicle.objects.all().order_by("vehicle_code")
    map_vehicles = [{"code": v.vehicle_code, "name": v.display_name, "plate": v.plate_number, "lat": float(v.latitude), "lng": float(v.longitude), "location": v.current_location or "Metro Manila", "speed": v.speed, "gps": v.gps_status, "status": v.status, "rental": v.rental_status, "updated": timezone.localtime(v.last_gps_update).strftime("%b %d, %H:%M")} for v in vehicles]
    return render(request, "rental/gps_tracking.html", {"page_title": "GPS Tracking", "vehicles": vehicles, "map_vehicles": map_vehicles})


@login_required
@require_POST
def gps_simulate(request):
    city_points = [("Makati City", 14.5547, 121.0244), ("Quezon City", 14.6760, 121.0437), ("Manila", 14.5995, 120.9842), ("Pasig City", 14.5764, 121.0851), ("Taguig City", 14.5176, 121.0509), ("Pasay City", 14.5378, 121.0014), ("Parañaque", 14.4793, 121.0198), ("Muntinlupa", 14.4081, 121.0415), ("Antipolo", 14.6255, 121.1245)]
    updated = 0
    for vehicle in Vehicle.objects.filter(gps_status=Vehicle.GPSStatus.ACTIVE):
        city, lat, lng = random.choice(city_points)
        vehicle.latitude = Decimal(str(lat + random.uniform(-0.008, 0.008))).quantize(Decimal("0.000001"))
        vehicle.longitude = Decimal(str(lng + random.uniform(-0.008, 0.008))).quantize(Decimal("0.000001"))
        vehicle.current_location = city
        vehicle.speed = random.randint(8, 58) if vehicle.status == Vehicle.Status.RENTED else 0
        vehicle.last_gps_update = timezone.now()
        vehicle.save(update_fields=["latitude", "longitude", "current_location", "speed", "last_gps_update", "updated_at"])
        GPSLocation.objects.create(vehicle=vehicle, latitude=vehicle.latitude, longitude=vehicle.longitude, location_label=city, speed=vehicle.speed)
        updated += 1
    return JsonResponse({"ok": True, "updated": updated, "message": f"Demo GPS refreshed for {updated} vehicles."})


@login_required
def rental_history(request):
    rentals = Rental.objects.select_related("customer", "vehicle").filter(status__in=[Rental.Status.COMPLETED, Rental.Status.CANCELLED]).order_by("-return_date")
    query = request.GET.get("q", "").strip()
    if query:
        from django.db.models import Q
        rentals = rentals.filter(Q(rental_code__icontains=query) | Q(customer__full_name__icontains=query) | Q(vehicle__vehicle_code__icontains=query))
    if request.GET.get("from"):
        rentals = rentals.filter(pickup_date__gte=request.GET["from"])
    if request.GET.get("to"):
        rentals = rentals.filter(return_date__lte=request.GET["to"])
    page = Paginator(rentals, 15).get_page(request.GET.get("page"))
    return render(request, "rental/history.html", {"page_title": "Rental history", "rentals": page.object_list, "page_obj": page, "filters": request.GET})


@login_required
def history_export(request):
    rentals = Rental.objects.select_related("customer", "vehicle").filter(
        status__in=[Rental.Status.COMPLETED, Rental.Status.CANCELLED]
    ).order_by("-return_date")
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="rentride-rental-history.csv"'
    writer = csv.writer(response)
    writer.writerow(["Rental ID", "Customer", "Vehicle", "Pickup", "Return", "Days", "Total", "Payment", "Status"])
    for rental in rentals:
        writer.writerow([rental.rental_code, rental.customer.full_name, rental.vehicle.display_name,
                         rental.pickup_date, rental.return_date, rental.duration_days, rental.total_cost,
                         rental.payment_status, rental.status])
    return response


@login_required
def reports(request):
    categories = list(Vehicle.objects.values("category").annotate(total=Count("id")).order_by("category"))
    most_rented = Vehicle.objects.annotate(rental_total=Count("rentals")).order_by("-rental_total")[:5]
    revenue_by_category = list(Payment.objects.filter(status=Payment.Status.COMPLETED).values("rental__vehicle__category").annotate(total=Sum("amount")).order_by("rental__vehicle__category"))
    context = {"page_title": "Reports", "total_rentals": Rental.objects.count(), "active_rentals": Rental.objects.filter(status__in=Rental.OPEN_STATUSES).count(), "completed_rentals": Rental.objects.filter(status=Rental.Status.COMPLETED).count(), "cancelled_rentals": Rental.objects.filter(status=Rental.Status.CANCELLED).count(), "revenue": Payment.objects.filter(status=Payment.Status.COMPLETED).aggregate(total=Sum("amount"))["total"] or 0, "categories_json": json.dumps(categories), "revenue_json": json.dumps([{"category": row["rental__vehicle__category"], "total": float(row["total"] or 0)} for row in revenue_by_category]), "most_rented": most_rented, "maintenance_due": Maintenance.objects.filter(status__in=[Maintenance.Status.SCHEDULED, Maintenance.Status.IN_PROGRESS]).select_related("vehicle")[:6]}
    return render(request, "rental/reports.html", context)


@login_required
def settings_page(request):
    profile_form = ProfileForm(request.POST if "profile_submit" in request.POST else None, instance=request.user, prefix="profile")
    password_form = PasswordChangeForm(user=request.user, data=request.POST if "password_submit" in request.POST else None, prefix="password")
    for field in password_form.fields.values():
        field.widget.attrs["class"] = "control"
    if request.method == "POST":
        if "profile_submit" in request.POST and profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Profile details saved.")
            return redirect("rental:settings")
        if "password_submit" in request.POST and password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was changed.")
            return redirect("rental:settings")
    return render(request, "rental/settings.html", {"page_title": "Settings", "profile_form": profile_form, "password_form": password_form})
