"""Grant the builder-journey star task to all pre-existing Builders.

Builders that predate the star-gated journey (see users.views.complete_builder_journey
and social_tasks 0004) never received the star-genlayer-boilerplate completion or its
points. Grant it to every Builder-profile user missing it, then recalculate all
leaderboards once so totals include the new completions and entries/ranks reflect the
write-time builder eligibility rule (Builder profile + ≥1 real builder contribution).

Historical models + bulk_create skip signals on purpose: the single closing recalc
replaces N per-user leaderboard updates.
"""

from django.conf import settings
from django.db import migrations


BACKFILL_SOURCE = 'social_tasks.0006_backfill_builder_star_completions'


def backfill_completions(apps, schema_editor):
    SocialTask = apps.get_model('social_tasks', 'SocialTask')
    SocialTaskCompletion = apps.get_model('social_tasks', 'SocialTaskCompletion')
    Builder = apps.get_model('builders', 'Builder')

    slug = getattr(settings, 'BUILDER_JOURNEY_TASK_SLUG', 'star-genlayer-boilerplate')
    task = SocialTask.objects.filter(slug=slug).first()
    if task is None:
        print(f"social_tasks.0006: task '{slug}' not found; skipping backfill")
        return

    builder_user_ids = set(Builder.objects.values_list('user_id', flat=True))
    already_completed = set(
        SocialTaskCompletion.objects.filter(task=task).values_list('user_id', flat=True)
    )
    to_grant = builder_user_ids - already_completed

    SocialTaskCompletion.objects.bulk_create(
        [
            SocialTaskCompletion(
                user_id=user_id,
                task=task,
                points_awarded=task.points,
                verification_type=task.verification_type,
                verification_data={
                    'backfill': True,
                    'source': BACKFILL_SOURCE,
                    'note': 'Granted to pre-existing Builders without live verification',
                },
            )
            for user_id in to_grant
        ],
        batch_size=500,
        # A user can organically complete the task while this runs; their row
        # wins and must not abort the deploy on the (user, task) constraint.
        ignore_conflicts=True,
    )
    print(f"social_tasks.0006: granted '{slug}' to {len(to_grant)} builders")


def remove_backfilled_completions(apps, schema_editor):
    """Reverse: delete only the rows this migration created (tagged by source)."""
    SocialTaskCompletion = apps.get_model('social_tasks', 'SocialTaskCompletion')
    SocialTaskCompletion.objects.filter(
        verification_data__source=BACKFILL_SOURCE
    ).delete()


def recalculate(apps, schema_editor):
    # Live import on purpose (precedent: contributions 0051; the
    # _social_tasks_ready() guard in leaderboard.models exists for this).
    # One recalc folds the new completions into totals, purges entries for
    # builders ineligible under the write-time rule, and rewrites contiguous
    # ranks. Fresh-DB replays see empty tables and no-op.
    from leaderboard.models import recalculate_all_leaderboards

    print(f"social_tasks.0006: {recalculate_all_leaderboards()}")


class Migration(migrations.Migration):

    dependencies = [
        ('social_tasks', '0005_socialtask_eligibility_requirements'),
        ('builders', '0001_initial'),
        # The recalc runs live code over these apps' tables; pin it after the
        # schema this release ships with.
        ('leaderboard', '0015_leaderboardentry_type_rank_index'),
        ('users', '0019_user_email_verified_at'),
        ('contributions', '0075_intelligent_contracts_evidence_types'),
        ('validators', '0015_validatorwalletstatussnapshot_logs_samples_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_completions, remove_backfilled_completions),
        migrations.RunPython(recalculate, migrations.RunPython.noop),
    ]
