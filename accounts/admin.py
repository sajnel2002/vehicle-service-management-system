from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User,
    Vehicle,
    Service,
    ServiceBooking,
    Technician,
    CustomerProfile,
    JobCard,
    Payment,
)


class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Role', {'fields': ('role',)}),
    )


class PaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'customer', 'total_amount', 'platform_fee', 'advisor_earnings', 'payment_status', 'paid_at')
    list_filter = ('payment_status', 'payment_method')


admin.site.register(User, CustomUserAdmin)
admin.site.register(Vehicle)
admin.site.register(Service)
admin.site.register(ServiceBooking)
admin.site.register(Technician)
admin.site.register(CustomerProfile)
admin.site.register(JobCard)
admin.site.register(Payment, PaymentAdmin)
