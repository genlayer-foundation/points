# Generated manually to add 'inactive' status choice

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('validators', '0007_validatorwallet'),
    ]

    operations = [
        migrations.AlterField(
            model_name='validatorwallet',
            name='status',
            field=models.CharField(
                choices=[
                    ('active', 'Active'),
                    ('banned', 'Banned'),
                    ('permabanned', 'Permabanned'),
                    ('inactive', 'Inactive'),
                ],
                default='active',
                max_length=20
            ),
        ),
    ]
