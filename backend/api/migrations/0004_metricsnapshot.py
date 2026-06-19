import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_remove_badge_action_remove_badge_participant_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='MetricSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('metric_key', models.CharField(db_index=True, max_length=120)),
                ('source', models.CharField(db_index=True, max_length=80)),
                ('label', models.CharField(blank=True, max_length=160)),
                ('value', models.DecimalField(blank=True, decimal_places=8, max_digits=40, null=True)),
                ('unit', models.CharField(blank=True, max_length=40)),
                ('observed_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('dimensions', models.JSONField(blank=True, default=dict)),
                ('raw_payload', models.JSONField(blank=True, default=dict)),
                ('status', models.CharField(choices=[('ok', 'OK'), ('error', 'Error')], db_index=True, default='ok', max_length=20)),
                ('error', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['-observed_at', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='metricsnapshot',
            index=models.Index(fields=['metric_key', '-observed_at'], name='api_metric_observed_idx'),
        ),
        migrations.AddIndex(
            model_name='metricsnapshot',
            index=models.Index(fields=['source', '-observed_at'], name='api_source_observed_idx'),
        ),
    ]
