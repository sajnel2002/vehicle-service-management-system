from decimal import Decimal
from datetime import datetime, timedelta
from functools import wraps

import logging
import os

import razorpay

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from django.db.models import Sum
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    AdvisorRegistrationForm,
    CustomerRegistrationForm,
    VehicleForm,
)
from .models import (
    CustomerProfile,
    JobCard,
    Payment,
    Service,
    ServiceBooking,
    Technician,
    User,
    Vehicle,
)


logger = logging.getLogger(__name__)


def role_required(*roles):

    def decorator(view_func):

        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):

            if request.user.role not in roles:
                messages.error(
                    request,
                    'You do not have permission to access this page.'
                )
                return redirect('dashboard')

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


# =========================
# HOME / LOGIN
# =========================

def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            if user.role == 'CUSTOMER':
                login(request, user)
                return redirect('dashboard')

            messages.error(
                request,
                'Please use the correct login page for your role.'
            )
        else:
            messages.error(
                request,
                'Invalid username or password.'
            )

    return render(
        request,
        'accounts/login.html'
    )


def advisor_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None and user.role == 'ADVISOR':

            if getattr(user, 'advisor_status', '') != 'APPROVED':
                messages.error(
                    request,
                    'Your advisor account has not been approved.'
                )
                return redirect('advisor_login')

            login(request, user)
            return redirect('dashboard')

        messages.error(
            request,
            'Invalid advisor username or password.'
        )

    return render(
        request,
        'accounts/advisor_login.html'
    )


def admin_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None and user.role == 'ADMIN':
            login(request, user)
            return redirect('dashboard')

        messages.error(
            request,
            'Invalid admin username or password.'
        )

    return render(
        request,
        'accounts/admin_login.html'
    )


# =========================
# CUSTOMER REGISTRATION
# =========================

def register(request):

    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':

        form = CustomerRegistrationForm(
            request.POST
        )

        if form.is_valid():

            user = form.save(
                commit=False
            )

            user.role = 'CUSTOMER'

            user.save()

            CustomerProfile.objects.get_or_create(
                user=user
            )

            messages.success(
                request,
                'Registration successful. Please login.'
            )

            return redirect('login')

    else:
        form = CustomerRegistrationForm()

    return render(
        request,
        'accounts/register.html',
        {
            'form': form
        }
    )


# =========================
# ADVISOR REGISTRATION
# =========================

def advisor_register(request):

    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':

        form = AdvisorRegistrationForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            user = form.save(
                commit=False
            )

            user.role = 'ADVISOR'

            if hasattr(user, 'advisor_status'):
                user.advisor_status = 'PENDING'

            user.save()

            messages.success(
                request,
                'Advisor registration submitted successfully. '
                'Wait for admin approval.'
            )

            return redirect('advisor_login')

    else:
        form = AdvisorRegistrationForm()

    return render(
        request,
        'accounts/advisor_register.html',
        {
            'form': form
        }
    )


# =========================
# DASHBOARD
# =========================

@login_required
def dashboard(request):

    if request.user.role == 'ADMIN':

        return redirect('admin_dashboard')

    if request.user.role == 'ADVISOR':

        if getattr(
            request.user,
            'advisor_status',
            ''
        ) != 'APPROVED':

            logout(request)

            messages.error(
                request,
                'Your advisor account is not approved.'
            )

            return redirect('advisor_login')

        return redirect('advisor_dashboard')

    return redirect('customer_dashboard')


# =========================
# CUSTOMER DASHBOARD
# =========================

@role_required('CUSTOMER')
def customer_dashboard(request):

    vehicles_count = Vehicle.objects.filter(
        customer=request.user
    ).count()

    bookings_count = ServiceBooking.objects.filter(
        customer=request.user
    ).count()

    completed_count = ServiceBooking.objects.filter(
        customer=request.user,
        status='COMPLETED'
    ).count()

    recent_bookings = ServiceBooking.objects.filter(
        customer=request.user
    ).select_related(
        'service',
        'vehicle',
        'advisor'
    ).order_by(
        '-created_at'
    )[:5]

    return render(
        request,
        'accounts/customer_dashboard.html',
        {
            'vehicles_count': vehicles_count,
            'bookings_count': bookings_count,
            'completed_count': completed_count,
            'recent_bookings': recent_bookings,
        }
    )


# =========================
# ADVISOR DASHBOARD
# =========================

@role_required('ADVISOR')
def advisor_dashboard(request):

    if getattr(
        request.user,
        'advisor_status',
        ''
    ) != 'APPROVED':

        logout(request)

        messages.error(
            request,
            'Your advisor account is not approved.'
        )

        return redirect('advisor_login')

    today = timezone.localdate()

    total_bookings = ServiceBooking.objects.filter(
        advisor=request.user
    ).count()

    pending_bookings = ServiceBooking.objects.filter(
        advisor=request.user,
        status='PENDING'
    ).count()

    confirmed_bookings = ServiceBooking.objects.filter(
        advisor=request.user,
        status='CONFIRMED'
    ).count()

    completed_bookings = ServiceBooking.objects.filter(
        advisor=request.user,
        status='COMPLETED'
    ).count()

    today_bookings = ServiceBooking.objects.filter(
        advisor=request.user,
        booking_date=today
    ).select_related(
        'customer',
        'vehicle',
        'service'
    ).order_by(
        'booking_time'
    )

    return render(
        request,
        'accounts/advisor_dashboard.html',
        {
            'total_bookings': total_bookings,
            'pending_bookings': pending_bookings,
            'confirmed_bookings': confirmed_bookings,
            'completed_bookings': completed_bookings,
            'today_bookings': today_bookings,
        }
    )


# =========================
# ADMIN DASHBOARD
# =========================

@role_required('ADMIN')
def admin_dashboard(request):

    total_customers = User.objects.filter(
        role='CUSTOMER'
    ).count()

    total_advisors = User.objects.filter(
        role='ADVISOR'
    ).count()

    pending_advisors = User.objects.filter(
        role='ADVISOR',
        advisor_status='PENDING'
    ).count()

    approved_advisors = User.objects.filter(
        role='ADVISOR',
        advisor_status='APPROVED'
    ).count()

    total_vehicles = Vehicle.objects.count()

    total_bookings = ServiceBooking.objects.count()

    pending_bookings = ServiceBooking.objects.filter(
        status='PENDING'
    ).count()

    completed_bookings = ServiceBooking.objects.filter(
        status='COMPLETED'
    ).count()

    return render(
        request,
        'accounts/admin_dashboard.html',
        {
            'total_customers': total_customers,
            'total_advisors': total_advisors,
            'pending_advisors': pending_advisors,
            'approved_advisors': approved_advisors,
            'total_vehicles': total_vehicles,
            'total_bookings': total_bookings,
            'pending_bookings': pending_bookings,
            'completed_bookings': completed_bookings,
        }
    )


# =========================
# VEHICLES
# =========================

@role_required('CUSTOMER')
def my_vehicles(request):

    vehicles = Vehicle.objects.filter(
        customer=request.user
    ).order_by('-id')

    return render(
        request,
        'accounts/my_vehicles.html',
        {
            'vehicles': vehicles
        }
    )


@role_required('CUSTOMER')
def add_vehicle(request):

    if request.method == 'POST':

        form = VehicleForm(
            request.POST
        )

        if form.is_valid():

            vehicle = form.save(
                commit=False
            )

            vehicle.customer = request.user

            vehicle.save()

            messages.success(
                request,
                'Vehicle added successfully.'
            )

            return redirect('my_vehicles')

    else:
        form = VehicleForm()

    return render(
        request,
        'accounts/add_vehicle.html',
        {
            'form': form
        }
    )
# =========================
# CUSTOMER - MY BOOKINGS
# =========================

@login_required
def my_bookings(request):

    bookings = ServiceBooking.objects.filter(
        customer=request.user
    ).select_related(
        'service',
        'vehicle',
        'advisor'
    ).order_by(
        '-booking_date',
        '-booking_time'
    )

    return render(
        request,
        'accounts/my_bookings.html',
        {
            'bookings': bookings
        }
    )


# =========================
# CUSTOMER - BOOKING DETAIL
# =========================

@login_required
def booking_detail(request, booking_id):

    booking = get_object_or_404(
        ServiceBooking.objects.select_related(
            'service',
            'vehicle',
            'advisor',
            'customer'
        ),
        pk=booking_id
    )

    if (
        request.user.role == 'CUSTOMER'
        and booking.customer != request.user
    ):
        messages.error(
            request,
            'You do not have permission to view this booking.'
        )

        return redirect(
            'my_bookings'
        )

    if (
        request.user.role == 'ADVISOR'
        and booking.advisor != request.user
    ):
        messages.error(
            request,
            'You do not have permission to view this booking.'
        )

        return redirect(
            'all_bookings'
        )

    if request.user.role not in [
        'CUSTOMER',
        'ADVISOR',
        'ADMIN'
    ]:
        messages.error(
            request,
            'You do not have permission to view this booking.'
        )

        return redirect(
            'dashboard'
        )

    return render(
        request,
        'accounts/booking_detail.html',
        {
            'booking': booking
        }
    )


# =========================
# CUSTOMER - CREATE BOOKING
# =========================

@role_required('CUSTOMER')
def create_booking(request):

    services = Service.objects.all()

    advisors = User.objects.filter(
        role='ADVISOR',
        advisor_status='APPROVED',
        is_active=True
    ).order_by(
        'first_name',
        'last_name',
        'username'
    )

    if request.method == 'POST':

        required = (
            'vehicle_number',
            'vehicle_model',
            'vehicle_type',
            'year',
            'service',
            'advisor',
            'booking_date',
            'booking_time',
            'location',
            'problem_description'
        )

        if not all(
            request.POST.get(
                key,
                ''
            ).strip()
            for key in required
        ):

            messages.error(
                request,
                'Please complete every booking field.'
            )

            return render(
                request,
                'accounts/create_booking.html',
                {
                    'services': services,
                    'advisors': advisors
                }
            )

        vehicle_number = request.POST.get(
            'vehicle_number'
        ).strip()

        vehicle_model = request.POST.get(
            'vehicle_model'
        ).strip()

        vehicle_type = request.POST.get(
            'vehicle_type'
        ).strip()

        year = request.POST.get(
            'year'
        ).strip()

        service_id = request.POST.get(
            'service'
        )

        advisor_id = request.POST.get(
            'advisor'
        )

        booking_date = request.POST.get(
            'booking_date'
        )

        booking_time = request.POST.get(
            'booking_time'
        )

        location = request.POST.get(
            'location'
        ).strip()

        problem_description = request.POST.get(
            'problem_description'
        ).strip()

        try:

            service = Service.objects.get(
                pk=service_id
            )

        except Service.DoesNotExist:

            messages.error(
                request,
                'Please select a valid service.'
            )

            return render(
                request,
                'accounts/create_booking.html',
                {
                    'services': services,
                    'advisors': advisors
                }
            )

        try:

            advisor = User.objects.get(
                pk=advisor_id,
                role='ADVISOR',
                advisor_status='APPROVED',
                is_active=True
            )

        except User.DoesNotExist:

            messages.error(
                request,
                'Please select a valid approved Service Advisor.'
            )

            return render(
                request,
                'accounts/create_booking.html',
                {
                    'services': services,
                    'advisors': advisors
                }
            )

        try:

            booking_date_obj = datetime.strptime(
                booking_date,
                '%Y-%m-%d'
            ).date()

            booking_time_obj = datetime.strptime(
                booking_time,
                '%H:%M'
            ).time()

        except ValueError:

            messages.error(
                request,
                'Please select a valid appointment date and time.'
            )

            return render(
                request,
                'accounts/create_booking.html',
                {
                    'services': services,
                    'advisors': advisors
                }
            )

        now = timezone.localtime()

        appointment_datetime = timezone.make_aware(
            datetime.combine(
                booking_date_obj,
                booking_time_obj
            ),
            timezone.get_current_timezone()
        )

        if appointment_datetime <= (
            now + timedelta(hours=2)
        ):

            messages.error(
                request,
                'Appointments must be booked more than 2 hours in advance.'
            )

            return render(
                request,
                'accounts/create_booking.html',
                {
                    'services': services,
                    'advisors': advisors
                }
            )

        if booking_date_obj < timezone.localdate():

            messages.error(
                request,
                'Appointments cannot be scheduled in the past.'
            )

            return render(
                request,
                'accounts/create_booking.html',
                {
                    'services': services,
                    'advisors': advisors
                }
            )

        if ServiceBooking.objects.filter(
            advisor=advisor,
            booking_date=booking_date_obj,
            booking_time=booking_time
        ).exclude(
            status='CANCELLED'
        ).exists():

            messages.error(
                request,
                'This advisor already has an appointment at this time. '
                'Please select another time.'
            )

            return render(
                request,
                'accounts/create_booking.html',
                {
                    'services': services,
                    'advisors': advisors
                }
            )

        try:

            vehicle, created = Vehicle.objects.get_or_create(
                customer=request.user,
                vehicle_number=vehicle_number,
                defaults={
                    'vehicle_model': vehicle_model,
                    'vehicle_type': vehicle_type,
                    'year': year
                }
            )

            if not created:

                vehicle.vehicle_model = vehicle_model
                vehicle.vehicle_type = vehicle_type
                vehicle.year = year

                vehicle.save()

            booking = ServiceBooking.objects.create(
                customer=request.user,
                vehicle=vehicle,
                service=service,
                advisor=advisor,
                booking_date=booking_date_obj,
                booking_time=booking_time,
                location=location,
                problem_description=problem_description,
                status='PENDING'
            )

            messages.success(
                request,
                'Service booking created successfully.'
            )

            return redirect(
                'booking_detail',
                booking_id=booking.id
            )

        except IntegrityError:

            messages.error(
                request,
                'This appointment slot is already booked. '
                'Please select another time.'
            )

    return render(
        request,
        'accounts/create_booking.html',
        {
            'services': services,
            'advisors': advisors
        }
    )
# =========================
# CUSTOMER - AVAILABLE BOOKING SLOTS
# =========================

@role_required('CUSTOMER')
def available_booking_slots(request):

    advisor_id = request.GET.get(
        'advisor'
    )

    booking_date = request.GET.get(
        'date'
    )

    if not advisor_id or not booking_date:

        return JsonResponse(
            {
                'available_slots': [],
                'message': (
                    'Select a Service Advisor and appointment '
                    'date first.'
                )
            },
            status=400
        )

    try:

        date = datetime.strptime(
            booking_date,
            '%Y-%m-%d'
        ).date()

        advisor = User.objects.get(
            pk=advisor_id,
            role='ADVISOR',
            advisor_status='APPROVED',
            is_active=True
        )

    except (
        ValueError,
        User.DoesNotExist
    ):

        return JsonResponse(
            {
                'available_slots': [],
                'message': (
                    'Please select a valid approved '
                    'Service Advisor and date.'
                )
            },
            status=400
        )

    today = timezone.localdate()

    if date < today:

        return JsonResponse(
            {
                'available_slots': [],
                'message': (
                    'Appointments cannot be scheduled in the past.'
                )
            },
            status=400
        )

    booked_slots = set(
        ServiceBooking.objects.filter(
            advisor=advisor,
            booking_date=date
        ).exclude(
            status='CANCELLED'
        ).values_list(
            'booking_time',
            flat=True
        )
    )

    now = timezone.localtime()

    available_slots = []

    for value, label in ServiceBooking.TIME_SLOT_CHOICES:

        slot_time = datetime.strptime(
            value,
            '%H:%M'
        ).time()

        slot_datetime = timezone.make_aware(
            datetime.combine(
                date,
                slot_time
            ),
            timezone.get_current_timezone()
        )

        if slot_time in booked_slots:
            continue

        if slot_datetime <= (
            now + timedelta(hours=2)
        ):
            continue

        available_slots.append(
            {
                'value': value,
                'label': label
            }
        )

    return JsonResponse(
        {
            'available_slots': available_slots
        }
    )


# =========================
# CUSTOMER - MY BOOKINGS
# =========================

@role_required('CUSTOMER')
def customer_bookings(request):

    bookings = ServiceBooking.objects.filter(
        customer=request.user
    ).select_related(
        'service',
        'vehicle',
        'advisor'
    ).order_by(
        '-booking_date',
        '-booking_time'
    )

    return render(
        request,
        'accounts/my_bookings.html',
        {
            'bookings': bookings
        }
    )


# =========================
# ALL BOOKINGS
# =========================

@login_required
def all_bookings(request):

    if request.user.role not in [
        'ADMIN',
        'ADVISOR'
    ]:

        messages.error(
            request,
            'You do not have permission to view bookings.'
        )

        return redirect(
            'dashboard'
        )

    if (
        request.user.role == 'ADVISOR'
        and request.user.advisor_status != 'APPROVED'
    ):

        messages.error(
            request,
            'Your advisor account is not approved.'
        )

        return redirect(
            'advisor_login'
        )

    if request.user.role == 'ADMIN':

        bookings = ServiceBooking.objects.select_related(
            'customer',
            'vehicle',
            'service',
            'advisor'
        ).order_by(
            '-booking_date',
            '-booking_time'
        )

    else:

        bookings = ServiceBooking.objects.filter(
            advisor=request.user
        ).select_related(
            'customer',
            'vehicle',
            'service',
            'advisor'
        ).order_by(
            '-booking_date',
            '-booking_time'
        )

    return render(
        request,
        'accounts/all_bookings.html',
        {
            'bookings': bookings
        }
    )


# =========================
# ADVISOR - UPDATE BOOKING STATUS
# =========================

@role_required('ADVISOR')
@require_POST
def update_booking_status(
    request,
    booking_id
):

    if request.user.advisor_status != 'APPROVED':

        messages.error(
            request,
            'Your advisor account is not approved.'
        )

        return redirect(
            'advisor_login'
        )

    booking = get_object_or_404(
        ServiceBooking,
        pk=booking_id,
        advisor=request.user
    )

    status = request.POST.get(
        'status'
    )

    valid_statuses = dict(
        ServiceBooking.STATUS_CHOICES
    )

    if (
        status in valid_statuses
        and status != 'CANCELLED'
    ):

        booking.status = status

        booking.save(
            update_fields=[
                'status'
            ]
        )

        # Keep Job Card status synchronized
        # with the booking status.

        jobcard_status = {
            'CONFIRMED': 'OPEN',
            'PENDING': 'OPEN',
            'IN_PROGRESS': 'IN_PROGRESS',
            'COMPLETED': 'COMPLETED',
        }.get(
            booking.status,
            'OPEN'
        )

        jobcard, created = (
            JobCard.objects.get_or_create(
                booking=booking,
                defaults={
                    'service_description':
                        booking.problem_description,

                    'estimated_cost':
                        booking.service.price,

                    'status':
                        jobcard_status
                }
            )
        )

        if not created:

            jobcard.status = jobcard_status

            jobcard.save(
                update_fields=[
                    'status'
                ]
            )

        messages.success(
            request,
            'Service status updated successfully.'
        )

    return redirect(
        'all_bookings'
    )


# =========================
# JOB CARDS
# =========================

@login_required
def job_cards(request):

    if request.user.role not in [
        'ADMIN',
        'ADVISOR',
        'CUSTOMER'
    ]:

        messages.error(
            request,
            'You do not have permission to view job cards.'
        )

        return redirect(
            'dashboard'
        )

    if (
        request.user.role == 'ADVISOR'
        and request.user.advisor_status != 'APPROVED'
    ):

        messages.error(
            request,
            'Your advisor account is not approved.'
        )

        return redirect(
            'advisor_login'
        )

    if request.user.role == 'CUSTOMER':

        jobcards = JobCard.objects.filter(
            booking__customer=request.user
        ).select_related(
            'booking',
            'booking__vehicle',
            'booking__service',
            'booking__advisor',
            'technician'
        ).order_by(
            '-created_at'
        )

    elif request.user.role == 'ADVISOR':

        jobcards = JobCard.objects.filter(
            booking__advisor=request.user
        ).select_related(
            'booking',
            'booking__customer',
            'booking__vehicle',
            'booking__service',
            'technician'
        ).order_by(
            '-created_at'
        )

    else:

        jobcards = JobCard.objects.select_related(
            'booking',
            'booking__customer',
            'booking__vehicle',
            'booking__service',
            'booking__advisor',
            'technician'
        ).order_by(
            '-created_at'
        )

    return render(
        request,
        'accounts/job_cards.html',
        {
            'jobcards': jobcards
        }
    )


# =========================
# TECHNICIANS
# =========================

@login_required
def technicians(request):

    if request.user.role not in [
        'ADMIN',
        'ADVISOR'
    ]:

        messages.error(
            request,
            'You do not have permission to view technicians.'
        )

        return redirect(
            'dashboard'
        )

    if (
        request.user.role == 'ADVISOR'
        and request.user.advisor_status != 'APPROVED'
    ):

        messages.error(
            request,
            'Your advisor account is not approved.'
        )

        return redirect(
            'advisor_login'
        )

    technicians_list = Technician.objects.all()

    return render(
        request,
        'accounts/technicians.html',
        {
            'technicians': technicians_list
        }
    )


# =========================
# CUSTOMER - PAY FOR BOOKING
# =========================
@role_required('CUSTOMER')
def payment_page(request, booking_id):

    booking = get_object_or_404(
        ServiceBooking.objects.select_related(
            'service',
            'vehicle',
            'advisor'
        ),
        pk=booking_id,
        customer=request.user
    )

    payment, _ = Payment.objects.get_or_create(
        booking=booking,
        defaults={
            'customer': request.user,

            'total_amount':
                booking.service.price,

            'platform_fee':
                booking.service.price *
                Decimal('.10'),

            'advisor_earnings':
                booking.service.price *
                Decimal('.90'),

            'payment_method':
                'RAZORPAY',

            'payment_status':
                'PENDING'
        }
    )

    razorpay_enabled = (
        payment.payment_status == 'SUCCESS'
    )

    key_id = getattr(
        settings,
        'RAZORPAY_KEY_ID',
        ''
    )

    key_secret = getattr(
        settings,
        'RAZORPAY_KEY_SECRET',
        ''
    )

    currency = getattr(
        settings,
        'RAZORPAY_CURRENCY',
        'INR'
    )

    razorpay_amount = int(
        payment.total_amount *
        Decimal('100')
    )

    if (
        payment.payment_status != 'SUCCESS'
        and key_id
        and key_secret
    ):

        try:

            client = razorpay.Client(
                auth=(
                    key_id,
                    key_secret
                )
            )

            if not payment.razorpay_order_id:

                order = client.order.create(
                    {
                        'amount': int(
                            payment.total_amount *
                            Decimal('100')
                        ),

                        'currency': currency,

                        'receipt':
                            f'booking_{booking.id}',

                        'notes': {
                            'booking_id':
                                str(booking.id),

                            'customer_id':
                                str(request.user.id)
                        }
                    }
                )

                payment.razorpay_order_id = (
                    order['id']
                )

                payment.payment_method = (
                    'RAZORPAY'
                )

                payment.save(
                    update_fields=[
                        'razorpay_order_id',
                        'payment_method'
                    ]
                )

            razorpay_enabled = True

        except Exception:

            logger.exception(
                'Unable to create Razorpay order '
                'for booking %s.',
                booking.id
            )

    return render(
        request,
        'accounts/payment.html',
        {
            'booking': booking,

            'payment': payment,

            'razorpay_enabled':
                razorpay_enabled,

            'razorpay_key_id':
                key_id,

            'razorpay_order_id':
                payment.razorpay_order_id,

            'razorpay_amount':
                razorpay_amount,

            'razorpay_currency':
                currency
        }
    )


# =========================
# CUSTOMER - PAYMENT SUCCESS
# =========================
@role_required('CUSTOMER')
def razorpay_payment_success(request, booking_id):

    booking = get_object_or_404(
        ServiceBooking.objects.select_related(
            'service',
            'vehicle',
            'advisor'
        ),
        pk=booking_id,
        customer=request.user
    )

    payment = get_object_or_404(
        Payment,
        booking=booking,
        customer=request.user
    )

    if request.method != 'POST':

        messages.error(
            request,
            'Invalid payment request.'
        )

        return redirect(
            'payment_page',
            booking_id=booking.id
        )

    razorpay_payment_id = request.POST.get(
        'razorpay_payment_id',
        ''
    )

    razorpay_order_id = request.POST.get(
        'razorpay_order_id',
        ''
    )

    razorpay_signature = request.POST.get(
        'razorpay_signature',
        ''
    )

    if not (
        razorpay_payment_id
        and razorpay_order_id
        and razorpay_signature
    ):

        messages.error(
            request,
            'Payment verification details are missing.'
        )

        return redirect(
            'payment_page',
            booking_id=booking.id
        )

    if razorpay_order_id != payment.razorpay_order_id:

        messages.error(
            request,
            'Payment verification failed for this booking.'
        )

        return redirect(
            'payment_page',
            booking_id=booking.id
        )

    try:

        client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET
            )
        )

        client.utility.verify_payment_signature(
            {
                'razorpay_order_id':
                    razorpay_order_id,

                'razorpay_payment_id':
                    razorpay_payment_id,

                'razorpay_signature':
                    razorpay_signature
            }
        )

        payment.payment_status = 'SUCCESS'

        payment.payment_method = 'RAZORPAY'

        payment.razorpay_order_id = (
            razorpay_order_id
        )

        payment.transaction_id = (
            razorpay_payment_id
        )

        payment.razorpay_payment_id = (
            razorpay_payment_id
        )

        payment.razorpay_signature = (
            razorpay_signature
        )

        payment.paid_at = timezone.now()

        payment.save()

        messages.success(
            request,
            'Payment completed successfully.'
        )

        return redirect(
            'booking_detail',
            booking_id=booking.id
        )

    except Exception:

        logger.exception(
            'Razorpay payment verification failed '
            'for booking %s.',
            booking.id
        )

        payment.payment_status = 'FAILED'

        payment.save(
            update_fields=[
                'payment_status'
            ]
        )

        messages.error(
            request,
            'Payment verification failed. '
            'Please try again.'
        )

        return redirect(
            'payment_page',
            booking_id=booking.id
        )


# =========================
# PAYMENT HISTORY
# =========================
@role_required('CUSTOMER', 'ADVISOR', 'ADMIN')
def payment_history(request):

    payments = Payment.objects.select_related(
        'booking__service',
        'booking__advisor',
        'booking__vehicle',
        'customer'
    ).order_by(
        '-created_at'
    )

    if request.user.role == 'CUSTOMER':
        payments = payments.filter(customer=request.user)
    elif request.user.role == 'ADVISOR':
        payments = payments.filter(booking__advisor=request.user)

    return render(
        request,
        'accounts/payment_history.html',
        {'payments': payments}
    )


# =========================
# ADVISOR - EARNINGS
# =========================
@role_required('ADVISOR')
def earnings(request):

    payments = Payment.objects.filter(
        booking__advisor=request.user,
        payment_status='SUCCESS'
    ).select_related(
        'booking__service',
        'customer'
    ).order_by(
        '-paid_at'
    )

    total_earnings = payments.aggregate(
        value=Sum('advisor_earnings')
    )['value'] or 0

    return render(
        request,
        'accounts/earnings.html',
        {
            'payments': payments,
            'total_earnings': total_earnings
        }
    )


# =========================
# ADMIN - REPORTS
# =========================
def reports(request):

    if request.user.role != 'ADMIN':
        messages.error(
            request,
            'Only administrators can view reports.'
        )
        return redirect('dashboard')

    context = {
        'total_vehicles': Vehicle.objects.count(),
        'total_bookings': ServiceBooking.objects.count(),
        'pending_bookings': ServiceBooking.objects.filter(
            status='PENDING'
        ).count(),
        'completed_bookings': ServiceBooking.objects.filter(
            status='COMPLETED'
        ).count(),
        'total_jobcards': JobCard.objects.count(),
        'total_technicians': Technician.objects.count(),
    }

    return render(
        request,
        'accounts/reports.html',
        context
    )


# =========================
# ADMIN - ADVISOR MANAGEMENT
# =========================
@role_required('ADMIN')
def advisor_management(request):

    return render(
        request,
        'accounts/advisor_management.html',
        {
            'pending_advisors': User.objects.filter(
                role='ADVISOR',
                advisor_status='PENDING'
            ),
            'approved_advisors': User.objects.filter(
                role='ADVISOR',
                advisor_status='APPROVED'
            ),
            'rejected_advisors': User.objects.filter(
                role='ADVISOR',
                advisor_status='REJECTED'
            )
        }
    )


# =========================
# ADMIN - VIEW JOINING LETTER
# =========================
@role_required('ADMIN')
def view_joining_letter(request, user_id):

    advisor = get_object_or_404(
        User,
        id=user_id,
        role='ADVISOR'
    )

    if not advisor.joining_letter:
        raise Http404('Joining letter not found.')

    try:
        file_path = advisor.joining_letter.path
    except Exception as error:
        print('Joining letter path error:', error)
        raise Http404('Joining letter file is unavailable.')

    if not os.path.exists(file_path):
        raise Http404('Joining letter file is unavailable.')

    return FileResponse(
        open(file_path, 'rb'),
        content_type='application/pdf'
    )


# =========================
# ADMIN - APPROVE ADVISOR
# =========================
@role_required('ADMIN')
@require_POST
def approve_advisor(request, user_id):

    advisor = get_object_or_404(
        User,
        id=user_id,
        role='ADVISOR'
    )

    advisor.advisor_status = 'APPROVED'
    advisor.is_active = True

    advisor.save(
        update_fields=[
            'advisor_status',
            'is_active'
        ]
    )

    messages.success(
        request,
        f'{advisor.get_full_name() or advisor.username} '
        'has been approved successfully.'
    )

    return redirect(
        'advisor_management'
    )


# =========================
# ADMIN - REJECT ADVISOR
# =========================
@role_required('ADMIN')
@require_POST
def reject_advisor(request, user_id):

    advisor = get_object_or_404(
        User,
        id=user_id,
        role='ADVISOR'
    )

    advisor.advisor_status = 'REJECTED'
    advisor.is_active = False

    advisor.save(
        update_fields=[
            'advisor_status',
            'is_active'
        ]
    )

    messages.success(
        request,
        f'{advisor.get_full_name() or advisor.username} '
        'has been rejected.'
    )

    return redirect(
        'advisor_management'
    )


# =========================
# ADMIN - ALL BOOKINGS
# =========================
@role_required('ADMIN')
def admin_all_bookings(request):

    bookings = ServiceBooking.objects.select_related(
        'customer',
        'vehicle',
        'service',
        'advisor'
    ).order_by(
        '-booking_date',
        '-booking_time'
    )

    return render(
        request,
        'accounts/all_bookings.html',
        {
            'bookings': bookings
        }
    )
# =========================
# ADMIN - REVOKE ADVISOR
# =========================
@role_required('ADMIN')
@require_POST
def revoke_advisor(
    request,
    user_id
):

    advisor = get_object_or_404(
        User,
        id=user_id,
        role='ADVISOR',
        advisor_status='APPROVED'
    )

    advisor.advisor_status = 'REJECTED'

    advisor.save(
        update_fields=[
            'advisor_status'
        ]
    )

    messages.success(
        request,
        f'{advisor.username} no longer has advisor access.'
    )

    return redirect(
        'advisor_management'
    )


# =========================
# LOGOUT
# =========================
@require_POST
def user_logout(request):

    role = (
        request.user.role
        if request.user.is_authenticated
        else 'CUSTOMER'
    )

    logout(request)

    return redirect(
        {
            'ADMIN':
                'admin_login',

            'ADVISOR':
                'advisor_login'
        }.get(
            role,
            'login'
        )
    )


# =========================
# ADVISOR PROFILE
# =========================
@role_required('ADVISOR')
def advisor_profile(request):

    if request.method == 'POST':

        first_name = request.POST.get(
            'first_name',
            ''
        ).strip()

        last_name = request.POST.get(
            'last_name',
            ''
        ).strip()

        email = request.POST.get(
            'email',
            ''
        ).strip()

        phone = request.POST.get(
            'phone',
            ''
        ).strip()

        try:

            if not email:

                raise ValidationError(
                    'Email address is required.'
                )

            validate_email(
                email
            )

            if len(first_name) > 150:

                raise ValidationError(
                    'First name must be 150 characters or fewer.'
                )

            if len(last_name) > 150:

                raise ValidationError(
                    'Last name must be 150 characters or fewer.'
                )

            if len(phone) > 15:

                raise ValidationError(
                    'Phone number must be 15 characters or fewer.'
                )

        except ValidationError as error:

            messages.error(
                request,
                error.messages[0]
            )

            return render(
                request,
                'accounts/advisor_profile.html',
                {
                    'profile_values':
                        request.POST
                }
            )

        request.user.first_name = (
            first_name
        )

        request.user.last_name = (
            last_name
        )

        request.user.email = (
            email
        )

        request.user.phone = (
            phone
        )

        request.user.save(
            update_fields=[
                'first_name',
                'last_name',
                'email',
                'phone'
            ]
        )

        messages.success(
            request,
            'Your profile details have been updated.'
        )

        return redirect(
            'advisor_profile'
        )

    return render(
        request,
        'accounts/advisor_profile.html',
        {
            'profile_values':
                request.user
        }
    )
