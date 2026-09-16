# Align the historical nullable transition field with the current model.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0009_payment_vehicle_unique')]

    operations = [
        migrations.AlterField(
            model_name='servicebooking',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
