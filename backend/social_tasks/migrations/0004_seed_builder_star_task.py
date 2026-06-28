"""Seed the builder-journey "star the boilerplate repo" social task.

This is the single points-bearing step of the builder journey: completing it
(a real GitHub star, via the github_star verifier) awards points AND is the gate
for the point-free Builder role grant (see users.views.complete_builder_journey
and settings.BUILDER_JOURNEY_TASK_SLUG).

Historical models skip the model's custom save(), so platform/action_url are set
explicitly here.
"""

from django.conf import settings
from django.db import migrations


TASK_SLUG = 'star-genlayer-boilerplate'


def seed_task(apps, schema_editor):
    Category = apps.get_model('contributions', 'Category')
    SocialTask = apps.get_model('social_tasks', 'SocialTask')

    builder, _ = Category.objects.get_or_create(
        slug='builder',
        defaults={'name': 'Builder', 'description': 'Builder contributions and tasks.'},
    )

    repo = getattr(settings, 'GITHUB_REPO_TO_STAR', 'genlayerlabs/genlayer-project-boilerplate')

    SocialTask.objects.update_or_create(
        slug=TASK_SLUG,
        defaults={
            'name': 'Star the GenLayer boilerplate',
            'description': 'Star the GenLayer project boilerplate on GitHub to kick off your builder journey.',
            'category': builder,
            'points': 25,  # matches the community-link-github reward; admin-tunable
            'verification_type': 'github_star',
            'target_repo': repo,
            'action_url': f'https://github.com/{repo}',
            'cta_text': 'Star repo',
            'platform': 'github',
            'is_active': True,
            'order': 10,
        },
    )


def noop_reverse(apps, schema_editor):
    """Keep the row (and any admin edits / completions referencing it) on rollback."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('social_tasks', '0003_deactivate_check_out_genlayer_x'),
    ]

    operations = [
        migrations.RunPython(seed_task, noop_reverse),
    ]
