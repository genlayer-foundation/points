from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0051_zero_validator_waitlist_points'),
    ]

    operations = [
        migrations.AddField(
            model_name='contributiontype',
            name='required_evidence_url_types',
            field=models.ManyToManyField(
                blank=True,
                help_text=(
                    'If set, at least one submitted evidence URL must match one of '
                    'these types. Required types are implicitly accepted.'
                ),
                related_name='required_by_contribution_types',
                to='contributions.evidenceurltype',
            ),
        ),
    ]
