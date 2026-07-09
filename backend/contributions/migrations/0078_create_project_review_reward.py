from django.db import migrations
from django.utils import timezone


def apply(apps, schema_editor):
    Category = apps.get_model('contributions', 'Category')
    ContributionType = apps.get_model('contributions', 'ContributionType')
    GlobalLeaderboardMultiplier = apps.get_model('leaderboard', 'GlobalLeaderboardMultiplier')

    builder_category = Category.objects.filter(slug='builder').first()
    if builder_category is None:
        raise RuntimeError('builder category missing; cannot seed project-review-reward')

    contribution_type, _ = ContributionType.objects.update_or_create(
        slug='project-review-reward',
        defaults={
            'name': 'Project Review Reward',
            'description': 'Reward for accurate Builder Project review proposals',
            'category': builder_category,
            'min_points': 0,
            'max_points': 100,
            'is_default': False,
            'is_submittable': False,
        },
    )

    if not GlobalLeaderboardMultiplier.objects.filter(
        contribution_type=contribution_type,
    ).exists():
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=contribution_type,
            multiplier_value=1.0,
            valid_from=timezone.now() - timezone.timedelta(days=30),
            description='Default multiplier for project review rewards',
            notes='Created for reviewer points economy',
        )


def reverse(apps, schema_editor):
    ContributionType = apps.get_model('contributions', 'ContributionType')
    ContributionType.objects.filter(slug='project-review-reward').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0077_reviewproposal'),
        ('leaderboard', '0015_leaderboardentry_type_rank_index'),
    ]

    operations = [
        migrations.RunPython(apply, reverse),
    ]
