from django.db import migrations


def backfill_graduated_validator_profiles(apps, schema_editor):
    Contribution = apps.get_model('contributions', 'Contribution')
    Validator = apps.get_model('validators', 'Validator')

    graduated_user_ids = list(
        Contribution.objects.filter(
            contribution_type__slug='validator',
        ).values_list('user_id', flat=True).distinct()
    )

    for user_id in graduated_user_ids:
        Validator.objects.get_or_create(user_id=user_id)

    if graduated_user_ids:
        from leaderboard.models import recalculate_all_leaderboards

        recalculate_all_leaderboards()


def noop_reverse(apps, schema_editor):
    # Do not delete Validator profiles on rollback: they may have wallets,
    # node-version history, or admin edits after being backfilled.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0076_submission_proposal_review_status'),
        ('leaderboard', '0015_leaderboardentry_type_rank_index'),
        ('validators', '0015_validatorwalletstatussnapshot_logs_samples_and_more'),
    ]

    operations = [
        migrations.RunPython(
            backfill_graduated_validator_profiles,
            noop_reverse,
        ),
    ]
