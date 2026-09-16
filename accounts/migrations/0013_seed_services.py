from django.db import migrations


def create_services(apps, schema_editor):
    Service = apps.get_model('accounts', 'Service')

    services = [
        {
            'name': 'General Service',
            'description': 'Basic checkup and maintenance',
            'price': 999,
        },
        {
            'name': 'Oil Change',
            'description': 'Engine oil and filter replacement',
            'price': 799,
        },
        {
            'name': 'Full Service',
            'description': 'Complete inspection and servicing',
            'price': 2499,
        },
        {
            'name': 'AC Service',
            'description': 'AC gas refill and inspection',
            'price': 1499,
        },
    ]

    for data in services:
        Service.objects.get_or_create(
            name=data['name'],
            defaults=data
        )


def remove_services(apps, schema_editor):
    Service = apps.get_model('accounts', 'Service')
    Service.objects.filter(
        name__in=[
            'General Service',
            'Oil Change',
            'Full Service',
            'AC Service',
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_previous_migration_name_here'),
    ]

    operations = [
        migrations.RunPython(create_services, remove_services),
    ]