from datetime import timedelta
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import JobCard, Payment, Service, ServiceBooking, User, Vehicle


class CoreApplicationFlowTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            username='customer',
            password='test-password',
            role='CUSTOMER'
        )
        self.advisor = User.objects.create_user(
            username='advisor',
            password='test-password',
            role='ADVISOR',
            advisor_status='APPROVED'
        )
        self.admin = User.objects.create_user(
            username='admin',
            password='test-password',
            role='ADMIN'
        )
        self.service = Service.objects.create(
            name='General Service',
            description='Routine maintenance',
            price='1000.00'
        )

    def test_role_dashboard_routes_resolve(self):
        for user, route_name in (
            (self.customer, 'customer_dashboard'),
            (self.advisor, 'advisor_dashboard'),
            (self.admin, 'admin_dashboard'),
        ):
            self.client.force_login(user)
            response = self.client.get(reverse('dashboard'))
            self.assertRedirects(response, reverse(route_name))
            self.assertEqual(self.client.get(reverse(route_name)).status_code, 200)

    def test_customer_and_advisor_registration(self):
        customer_response = self.client.post(
            reverse('register'),
            {
                'username': 'new-customer',
                'password': 'secure-password',
                'confirm_password': 'secure-password',
            }
        )
        self.assertRedirects(customer_response, reverse('login'))
        self.assertEqual(User.objects.get(username='new-customer').role, 'CUSTOMER')

        advisor_response = self.client.post(
            reverse('advisor_register'),
            {
                'username': 'new-advisor',
                'email': 'advisor@example.com',
                'phone': '9876543210',
                'password': 'secure-password',
                'confirm_password': 'secure-password',
                'joining_letter': SimpleUploadedFile(
                    'joining-letter.pdf',
                    b'%PDF-1.4 test document',
                    content_type='application/pdf'
                ),
            }
        )
        self.assertRedirects(advisor_response, reverse('advisor_login'))
        self.assertEqual(
            User.objects.get(username='new-advisor').advisor_status,
            'PENDING'
        )

    def test_booking_status_and_payment_flow(self):
        booking_date = timezone.localdate() + timedelta(days=2)
        self.client.force_login(self.customer)
        response = self.client.post(
            reverse('create_booking'),
            {
                'vehicle_number': 'KL 07 AB 1234',
                'vehicle_model': 'City',
                'vehicle_type': 'Car',
                'year': '2022',
                'service': self.service.id,
                'advisor': self.advisor.id,
                'booking_date': booking_date.isoformat(),
                'booking_time': '09:00',
                'location': 'Kochi',
                'problem_description': 'Routine service',
            }
        )
        booking = ServiceBooking.objects.get(customer=self.customer)
        self.assertRedirects(response, reverse('booking_detail', args=[booking.id]))
        self.assertTrue(Vehicle.objects.filter(customer=self.customer).exists())

        self.client.force_login(self.advisor)
        status_response = self.client.post(
            reverse('update_booking_status', args=[booking.id]),
            {'status': 'CONFIRMED'}
        )
        self.assertRedirects(status_response, reverse('all_bookings'))
        self.assertTrue(JobCard.objects.filter(booking=booking).exists())

        self.client.force_login(self.customer)
        with patch('accounts.views.razorpay.Client') as client_class:
            gateway_client = Mock()
            gateway_client.order.create.return_value = {'id': 'order_test_123'}
            client_class.return_value = gateway_client
            payment_response = self.client.get(
                reverse('payment_page', args=[booking.id])
            )

        self.assertEqual(payment_response.status_code, 200)
        payment = Payment.objects.get(booking=booking)
        self.assertEqual(payment.razorpay_order_id, 'order_test_123')

        with patch('accounts.views.razorpay.Client') as client_class:
            gateway_client = Mock()
            client_class.return_value = gateway_client
            success_response = self.client.post(
                reverse('razorpay_payment_success', args=[booking.id]),
                {
                    'razorpay_order_id': 'order_test_123',
                    'razorpay_payment_id': 'pay_test_123',
                    'razorpay_signature': 'signature',
                }
            )

        self.assertRedirects(success_response, reverse('booking_detail', args=[booking.id]))
        payment.refresh_from_db()
        self.assertEqual(payment.payment_status, 'SUCCESS')
        self.assertEqual(payment.payment_method, 'RAZORPAY')
        self.assertEqual(payment.transaction_id, 'pay_test_123')
