from django.db import migrations


def backfill_graduated_validator_profiles(apps, schema_editor):
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
