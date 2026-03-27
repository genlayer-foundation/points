from django.db import migrations
from django.utils import timezone


def create_uptime_type(apps, schema_editor):
    """
    Create the Uptime ContributionType and its multiplier if they don't exist.
    Required by the add_daily_uptime management command.
    """
    ContributionType = apps.get_model('contributions', 'ContributionType')
    Category = apps.get_model('contributions', 'Category')
    GlobalLeaderboardMultiplier = apps.get_model('leaderboard', 'GlobalLeaderboardMultiplier')

    # Get the validator category (created by migration 0017)
    validator_category = Category.objects.filter(slug='validator').first()

    contribution_type, created = ContributionType.objects.get_or_create(
        slug='uptime',
        defaults={
            'name': 'Uptime',
            'description': 'Daily validator uptime points for active validators',
            'category': validator_category,
            'min_points': 1,
            'max_points': 10,
            'is_default': False,
            'is_submittable': False,
        }
    )

    if created:
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=contribution_type,
            multiplier_value=2.0,
            valid_from=timezone.now(),
            description='Initial multiplier for daily uptime points',
        )


def reverse_uptime_type(apps, schema_editor):
    ContributionType = apps.get_model('contributions', 'ContributionType')
    GlobalLeaderboardMultiplier = apps.get_model('leaderboard', 'GlobalLeaderboardMultiplier')

    try:
        contribution_type = ContributionType.objects.get(slug='uptime')
        GlobalLeaderboardMultiplier.objects.filter(contribution_type=contribution_type).delete()
        contribution_type.delete()
    except ContributionType.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0040_convert_featured_images_to_cloudinary'),
        ('leaderboard', '0014_add_referral_points_model'),
    ]

    operations = [
        migrations.RunPython(create_uptime_type, reverse_uptime_type),
    ]
