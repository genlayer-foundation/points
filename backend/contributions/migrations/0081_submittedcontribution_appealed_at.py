from django.db import migrations, models


def backfill_appealed_at(apps, schema_editor):
    SubmittedContribution = apps.get_model('contributions', 'SubmittedContribution')
    SubmissionNote = apps.get_model('contributions', 'SubmissionNote')
    SubmissionStateTransition = apps.get_model(
        'contributions',
        'SubmissionStateTransition',
    )
    database = schema_editor.connection.alias

    submissions = (
        SubmittedContribution.objects.using(database)
        .filter(has_appeal=True, appealed_at__isnull=True)
        .values_list('id', flat=True)
    )
    for submission_id in submissions.iterator():
        appealed_at = (
            SubmissionStateTransition.objects.using(database)
            .filter(submitted_contribution_id=submission_id, event='appeal')
            .order_by('created_at')
            .values_list('created_at', flat=True)
            .first()
        )
        if appealed_at is None:
            appealed_at = (
                SubmissionNote.objects.using(database)
                .filter(
                    submitted_contribution_id=submission_id,
                    data__kind='appeal',
                )
                .order_by('created_at')
                .values_list('created_at', flat=True)
                .first()
            )
        if appealed_at is not None:
            (
                SubmittedContribution.objects.using(database)
                .filter(id=submission_id)
                .update(appealed_at=appealed_at)
            )


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0080_aireviewfeedback'),
    ]

    operations = [
        migrations.AddField(
            model_name='submittedcontribution',
            name='appealed_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When the submitter appealed the rejection.',
                null=True,
            ),
        ),
        migrations.RunPython(backfill_appealed_at, migrations.RunPython.noop),
    ]
