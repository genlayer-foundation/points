from django.db import migrations


def create_community_onboarding_types(apps, schema_editor):
    Category = apps.get_model('contributions', 'Category')
    ContributionType = apps.get_model('contributions', 'ContributionType')

    community_category = Category.objects.get(slug='community')

    ContributionType.objects.create(
        name='Link X Account',
        slug='community-link-x',
        description='Linked your X (Twitter) account to your GenLayer profile',
        category=community_category,
        min_points=20,
        max_points=20,
        is_default=False,
        is_submittable=False,
    )

    ContributionType.objects.create(
        name='Link Discord Account',
        slug='community-link-discord',
        description='Linked your Discord account to your GenLayer profile',
        category=community_category,
        min_points=20,
        max_points=20,
        is_default=False,
        is_submittable=False,
    )


def reverse_community_onboarding_types(apps, schema_editor):
    ContributionType = apps.get_model('contributions', 'ContributionType')
    ContributionType.objects.filter(
        slug__in=['community-link-x', 'community-link-discord']
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0046_contributiontype_required_social_accounts'),
    ]

    operations = [
        migrations.RunPython(
            create_community_onboarding_types,
            reverse_community_onboarding_types,
        ),
    ]
