from django.db import migrations


def zero_validator_waitlist_points(apps, schema_editor):
    ContributionType = apps.get_model('contributions', 'ContributionType')
    Contribution = apps.get_model('contributions', 'Contribution')

    ContributionType.objects.filter(slug='validator-waitlist').update(
        min_points=0,
        max_points=0,
        is_submittable=False,
    )

    Contribution.objects.filter(contribution_type__slug='validator-waitlist').update(
        points=0,
        frozen_global_points=0,
    )

    from leaderboard.models import recalculate_all_leaderboards
    recalculate_all_leaderboards()


def restore_validator_waitlist_points(apps, schema_editor):
    # Only restores the ContributionType metadata. Per-Contribution point
    # values are destructively overwritten by the forward operation and
    # cannot be recovered here, so rolling this migration back leaves every
    # historical validator-waitlist Contribution permanently at 0 points.
    ContributionType = apps.get_model('contributions', 'ContributionType')

    ContributionType.objects.filter(slug='validator-waitlist').update(
        min_points=20,
        max_points=20,
        is_submittable=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0050_evidence_url_types'),
        ('leaderboard', '0014_add_referral_points_model'),
    ]

    operations = [
        migrations.RunPython(
            zero_validator_waitlist_points,
            restore_validator_waitlist_points,
        ),
    ]
