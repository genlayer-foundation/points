from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('validators', '0012_validatorwallet_last_grafana_check_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='validatorwallet',
            name='metrics_shame_started_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='validatorwallet',
            name='logs_shame_started_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='validatorwallet',
            name='version_shame_started_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
