from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError


# =========================
# USER
# =========================
class User(AbstractUser):

    ROLE_CHOICES = (
        ('ADMIN', 'Administrator'),
        ('ADVISOR', 'Service Advisor'),
        ('CUSTOMER', 'Customer'),
    )

    ADVISOR_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='CUSTOMER'
    )

    phone = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    advisor_status = models.CharField(
        max_length=20,
        choices=ADVISOR_STATUS_CHOICES,
        default='PENDING'
    )

    # Advisor joining letter PDF
    joining_letter = models.FileField(
        upload_to='advisor_joining_letters/',
        blank=True,
        null=True
    )

    def __str__(self):
        return self.username


# =========================
# VEHICLE
# =========================
class Vehicle(models.Model):

    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    vehicle_number = models.CharField(
        max_length=20
    )

    vehicle_model = models.CharField(
        max_length=100
    )

    vehicle_type = models.CharField(
        max_length=50
    )

    year = models.PositiveIntegerField()

    def __str__(self):
        return self.vehicle_number

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'customer',
                    'vehicle_number'
                ],
                name='unique_customer_vehicle_number'
            )
        ]


# =========================
# SERVICE
# =========================
class Service(models.Model):

    name = models.CharField(
        max_length=100
    )

    description = models.TextField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return self.name


# =========================
# SERVICE BOOKING
# =========================
class ServiceBooking(models.Model):

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )

    TIME_SLOT_CHOICES = (
        ('09:00', '09:00 AM - 10:00 AM'),
        ('10:00', '10:00 AM - 11:00 AM'),
        ('11:00', '11:00 AM - 12:00 PM'),
        ('12:00', '12:00 PM - 01:00 PM'),
        ('14:00', '02:00 PM - 03:00 PM'),
        ('15:00', '03:00 PM - 04:00 PM'),
        ('16:00', '04:00 PM - 05:00 PM'),
        ('17:00', '05:00 PM - 06:00 PM'),
    )

    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='customer_bookings'
    )

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE
    )

    # Approved service advisor
    advisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='advisor_bookings',
        limit_choices_to={
            'role': 'ADVISOR',
            'advisor_status': 'APPROVED'
        }
    )

    # Customer selected city/location
    location = models.CharField(
        max_length=100,
        default='Kochi'
    )

    booking_date = models.DateField()

    booking_time = models.CharField(
        max_length=5,
        choices=TIME_SLOT_CHOICES
    )

    problem_description = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'advisor',
                    'booking_date',
                    'booking_time'
                ],
                name='unique_advisor_booking_slot'
            )
        ]

        ordering = [
            '-booking_date',
            'booking_time'
        ]

    def clean(self):

        # Advisor must be an approved advisor
        if self.advisor:

            if self.advisor.role != 'ADVISOR':

                raise ValidationError(
                    'The assigned user must be a Service Advisor.'
                )

            if self.advisor.advisor_status != 'APPROVED':

                raise ValidationError(
                    'The assigned advisor must be approved.'
                )

    def __str__(self):

        return (
            f"{self.customer.username} - "
            f"{self.vehicle.vehicle_number} - "
            f"{self.booking_date} {self.booking_time}"
        )


# =========================
# TECHNICIAN
# =========================
class Technician(models.Model):

    name = models.CharField(
        max_length=100
    )

    phone = models.CharField(
        max_length=15
    )

    specialization = models.CharField(
        max_length=100
    )

    def __str__(self):
        return self.name


# =========================
# JOB CARD
# =========================
class JobCard(models.Model):

    STATUS_CHOICES = (
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('DELIVERED', 'Delivered'),
    )

    booking = models.OneToOneField(
        ServiceBooking,
        on_delete=models.CASCADE
    )

    technician = models.ForeignKey(
        Technician,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    service_description = models.TextField()

    estimated_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    final_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='OPEN'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Job Card - {self.booking}"


# =========================
# PAYMENT
# =========================
class Payment(models.Model):

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Successful'),
        ('FAILED', 'Failed'),
    )

    METHOD_CHOICES = (
        ('RAZORPAY', 'Razorpay'),
    )

    booking = models.OneToOneField(
        ServiceBooking,
        on_delete=models.CASCADE,
        related_name='payment'
    )

    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments'
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    platform_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    advisor_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    payment_method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        default='RAZORPAY'
    )

    # Existing transaction/reference ID
    transaction_id = models.CharField(
        max_length=128,
        blank=True
    )

    # Razorpay order created on server
    razorpay_order_id = models.CharField(
        max_length=128,
        blank=True
    )

    # Razorpay payment returned by Checkout
    razorpay_payment_id = models.CharField(
        max_length=128,
        blank=True
    )

    # Razorpay signature used for server verification
    razorpay_signature = models.CharField(
        max_length=256,
        blank=True
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            '-created_at'
        ]

    def __str__(self):
        return (
            f"Payment #{self.booking_id} - "
            f"{self.payment_status}"
        )


# =========================
# CUSTOMER PROFILE
# =========================
class CustomerProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    phone = models.CharField(
        max_length=15
    )

    address = models.TextField()

    def __str__(self):
        return self.user.username
