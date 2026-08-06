import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0084_enable_builder_review_hierarchy'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SubmissionMoreInfoResponse',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('request_message', models.TextField()),
                ('requested_at', models.DateTimeField(blank=True, null=True)),
                ('message', models.TextField(max_length=1000)),
                (
                    'request_note',
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='submitter_response',
                        to='contributions.submissionnote',
                    ),
                ),
                (
                    'requested_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='more_info_requests_answered',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'responder',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='submission_more_info_responses',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'submitted_contribution',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='more_info_responses',
                        to='contributions.submittedcontribution',
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at', '-id'],
                'indexes': [
                    models.Index(
                        fields=['submitted_contribution', 'created_at'],
                        name='sub_info_resp_created_idx',
                    ),
                ],
            },
        ),
    ]
