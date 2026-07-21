from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0081_submittedcontribution_appealed_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='contributiontype',
            name='max_submissions_per_user_per_week',
            field=models.PositiveIntegerField(
                blank=True,
                help_text=(
                    'Maximum submissions each user may create for this '
                    'contribution type per Monday-Sunday UTC week. Every '
                    'submission state counts. Leave blank for unlimited.'
                ),
                null=True,
            ),
        ),
        migrations.AddIndex(
            model_name='submittedcontribution',
            index=models.Index(
                fields=['user', 'contribution_type', 'created_at'],
                name='sub_user_type_week_idx',
            ),
        ),
    ]
