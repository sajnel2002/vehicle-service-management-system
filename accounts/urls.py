from django.urls import path

from .views import (
    dashboard,
    customer_dashboard,
    advisor_dashboard,
    admin_dashboard,
    user_login,
    advisor_login,
    admin_login,
    register,
    advisor_register,
    my_vehicles,
    my_bookings,
    create_booking,
    all_bookings,
    job_cards,
    technicians,
    reports,
    approve_advisor,
    reject_advisor,
    booking_detail,
    update_booking_status,
    payment_page,
    payment_history,
    earnings,
    advisor_management,
    user_logout,
    advisor_profile,
    revoke_advisor,
    available_booking_slots,
    razorpay_payment_success,
    view_joining_letter,
)


urlpatterns = [

    # =========================
    # LOGIN
    # =========================

    path(
        '',
        user_login,
        name='login'
    ),

    path(
        'advisor-login/',
        advisor_login,
        name='advisor_login'
    ),

    path(
        'admin-login/',
        admin_login,
        name='admin_login'
    ),


    # =========================
    # REGISTRATION
    # =========================

    path(
        'register/',
        register,
        name='register'
    ),

    path(
        'advisor-register/',
        advisor_register,
        name='advisor_register'
    ),


    # =========================
    # DASHBOARD
    # =========================

    path(
        'dashboard/',
        dashboard,
        name='dashboard'
    ),

    path(
        'customer-dashboard/',
        customer_dashboard,
        name='customer_dashboard'
    ),

    path(
        'advisor-dashboard/',
        advisor_dashboard,
        name='advisor_dashboard'
    ),

    path(
        'admin-dashboard/',
        admin_dashboard,
        name='admin_dashboard'
    ),


    # =========================
    # CUSTOMER
    # =========================

    path(
        'my-vehicles/',
        my_vehicles,
        name='my_vehicles'
    ),

    path(
        'create-booking/',
        create_booking,
        name='create_booking'
    ),

    path(
        'my-bookings/',
        my_bookings,
        name='my_bookings'
    ),

    path(
        'booking-available-slots/',
        available_booking_slots,
        name='available_booking_slots'
    ),

    path(
        'booking/<int:booking_id>/',
        booking_detail,
        name='booking_detail'
    ),

    path(
        'booking/<int:booking_id>/payment/',
        payment_page,
        name='payment_page'
    ),

    path(
        'booking/<int:booking_id>/payment/success/',
        razorpay_payment_success,
        name='razorpay_payment_success'
    ),

    path(
        'payments/',
        payment_history,
        name='payment_history'
    ),

    path(
        'earnings/',
        earnings,
        name='earnings'
    ),

    path(
        'advisor-profile/',
        advisor_profile,
        name='advisor_profile'
    ),

    path(
        'booking/<int:booking_id>/status/',
        update_booking_status,
        name='update_booking_status'
    ),

    path(
        'logout/',
        user_logout,
        name='logout'
    ),


    # =========================
    # ADVISOR
    # =========================

    path(
        'all-bookings/',
        all_bookings,
        name='all_bookings'
    ),

    path(
        'job-cards/',
        job_cards,
        name='job_cards'
    ),

    path(
        'technicians/',
        technicians,
        name='technicians'
    ),


    # =========================
    # ADMIN
    # =========================

    path(
        'reports/',
        reports,
        name='reports'
    ),

    path(
        'advisor-management/',
        advisor_management,
        name='advisor_management'
    ),

    path(
        'advisor/<int:user_id>/joining-letter/',
        view_joining_letter,
        name='view_joining_letter'
    ),

    path(
        'revoke-advisor/<int:user_id>/',
        revoke_advisor,
        name='revoke_advisor'
    ),

    path(
        'approve-advisor/<int:user_id>/',
        approve_advisor,
        name='approve_advisor'
    ),

    path(
        'reject-advisor/<int:user_id>/',
        reject_advisor,
        name='reject_advisor'
    ),
]
