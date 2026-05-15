from django.db import migrations, models
from django.db.models import Q


def forwards(apps, schema_editor):
    SubmittedContribution = apps.get_model(
        'contributions', 'SubmittedContribution'
    )
    cancellation_note = (
        Q(staff_reply__iexact='Cancelled by user')
        | Q(staff_reply__iexact='Canceled by user')
        | Q(notes__iexact='Cancelled by user')
        | Q(notes__iexact='Canceled by user')
    )
    SubmittedContribution.objects.filter(state='rejected').filter(
        cancellation_note
    ).update(state='canceled')


def backwards(apps, schema_editor):
    SubmittedContribution = apps.get_model(
        'contributions', 'SubmittedContribution'
    )
    SubmittedContribution.objects.filter(state='canceled').update(
        state='rejected'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0058_mission_max_submissions_per_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contributiontype',
            name='max_submissions',
            field=models.PositiveIntegerField(
                blank=True,
                help_text=(
                    'Maximum number of non-rejected, non-canceled '
                    'submissions allowed for this contribution type. Leave '
                    'blank for unlimited.'
                ),
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='submittedcontribution',
            name='state',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending Review'),
                    ('accepted', 'Accepted'),
                    ('rejected', 'Rejected'),
                    ('canceled', 'Canceled'),
                    ('more_info_needed', 'More Information Needed'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='mission',
            name='max_submissions',
            field=models.PositiveIntegerField(
                blank=True,
                help_text=(
                    'Maximum number of non-rejected, non-canceled '
                    'submissions allowed for this mission. Leave blank for '
                    'unlimited.'
                ),
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='mission',
            name='max_submissions_per_user',
            field=models.PositiveIntegerField(
                blank=True,
                help_text=(
                    'Maximum number of non-rejected, non-canceled '
                    'submissions allowed per user for this mission. Leave '
                    'blank for unlimited.'
                ),
                null=True,
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]
