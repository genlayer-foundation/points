"""GitHub-link reward (builder category) + builder-welcome as a 0-point marker.

Merged from the former 0073 + 0074 into one migration.

- Linking GitHub is a BUILDER action, so the reward type lives in the `builder`
  category (it feeds the builder leaderboard / shows as a builder contribution).
  The slug stays `community-link-github` and the serializer field stays
  `has_community_link_github` to match the existing link-reward family and the
  frontend that already consumes that field.
- `builder-welcome` is no longer a farmable +20 reward; it is the point-free
  "started the builder journey" marker, so its type is relaxed to 0 points.
"""

from django.db import migrations


def apply(apps, schema_editor):
    Category = apps.get_model('contributions', 'Category')
    ContributionType = apps.get_model('contributions', 'ContributionType')

    builder_category = Category.objects.filter(slug='builder').first()
    ContributionType.objects.update_or_create(
        slug='community-link-github',
        defaults={
            'name': 'Link GitHub Account',
            'description': 'Linked your GitHub account to your GenLayer profile',
            'category': builder_category,
            'min_points': 25,
            'max_points': 25,
            'is_default': False,
            'is_submittable': False,
        },
    )

    ContributionType.objects.filter(slug='builder-welcome').update(min_points=0, max_points=0)


def reverse(apps, schema_editor):
    ContributionType = apps.get_model('contributions', 'ContributionType')
    ContributionType.objects.filter(slug='community-link-github').delete()
    ContributionType.objects.filter(slug='builder-welcome').update(min_points=20, max_points=20)


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0072_submittedcontribution_gate_reviewed'),
    ]

    operations = [
        migrations.RunPython(apply, reverse),
    ]
