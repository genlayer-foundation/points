from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_active_proposal_status(apps, schema_editor):
    SubmittedContribution = apps.get_model('contributions', 'SubmittedContribution')
    SubmittedContribution.objects.filter(
        proposed_action__isnull=False,
        proposal_review_status__isnull=True,
    ).update(proposal_review_status='pending_review')


def clear_backfilled_proposal_status(apps, schema_editor):
    SubmittedContribution = apps.get_model('contributions', 'SubmittedContribution')
    SubmittedContribution.objects.filter(
        proposed_action__isnull=False,
        proposal_review_status='pending_review',
        proposal_review_feedback='',
        proposal_questioned_by__isnull=True,
        proposal_questioned_at__isnull=True,
    ).update(proposal_review_status=None)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contributions', '0075_intelligent_contracts_evidence_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='submittedcontribution',
            name='proposal_review_status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('pending_review', 'Pending Review'),
                    ('questioned', 'Questioned'),
                ],
                db_index=True,
                help_text='Internal review status for the active proposal',
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='submittedcontribution',
            name='proposal_review_feedback',
            field=models.TextField(
                blank=True,
                help_text='Feedback sent to the proposer when a proposal is questioned',
            ),
        ),
        migrations.AddField(
            model_name='submittedcontribution',
            name='proposal_questioned_by',
            field=models.ForeignKey(
                blank=True,
                help_text='Steward who questioned the active proposal',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='questioned_submission_proposals',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='submittedcontribution',
            name='proposal_questioned_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When the active proposal was questioned',
                null=True,
            ),
        ),
        migrations.RunPython(
            backfill_active_proposal_status,
            clear_backfilled_proposal_status,
        ),
    ]
