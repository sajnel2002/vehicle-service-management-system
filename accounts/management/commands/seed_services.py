from django.core.management.base import BaseCommand

from accounts.models import Service


class Command(BaseCommand):
    help = 'Create or update the four standard AutoCare services.'

    def handle(self, *args, **options):
        services = {
            'Basic Service': ('Essential inspection, oil and filter check.', 1000),
            'General Service': ('Routine maintenance and multi-point inspection.', 1500),
            'Full Service': ('Comprehensive maintenance for reliable performance.', 2500),
            'Premium Service': ('Complete care with detailed inspection and support.', 3500),
        }
        for name, (description, price) in services.items():
            Service.objects.update_or_create(name=name, defaults={'description': description, 'price': price})
        self.stdout.write(self.style.SUCCESS('Standard services are ready.'))
