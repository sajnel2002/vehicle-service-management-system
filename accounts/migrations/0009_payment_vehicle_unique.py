# Generated manually for the AutoCare payment workflow.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0008_alter_servicebooking_options_servicebooking_advisor_and_more')]

    operations = [
        migrations.AddConstraint(model_name='vehicle', constraint=models.UniqueConstraint(fields=('customer', 'vehicle_number'), name='unique_customer_vehicle_number')),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('platform_fee', models.DecimalField(decimal_places=2, max_digits=10)),
                ('advisor_earnings', models.DecimalField(decimal_places=2, max_digits=10)),
                ('payment_status', models.CharField(choices=[('PENDING', 'Pending'), ('SUCCESS', 'Successful')], default='PENDING', max_length=12)),
                ('payment_method', models.CharField(choices=[('DEMO', 'Demo Payment'), ('RAZORPAY', 'Razorpay')], default='DEMO', max_length=20)),
                ('transaction_id', models.CharField(blank=True, max_length=64)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='payment', to='accounts.servicebooking')),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
