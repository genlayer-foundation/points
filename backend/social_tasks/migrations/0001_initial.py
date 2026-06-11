"""Initial migration for the social_tasks app.

Single migration that creates both models AND seeds the initial three tasks
under the community category. Admins can edit / disable / add more via Django
admin afterwards.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


SEED_TASKS = [
    {
        'slug': 'follow-genlayer-x',
        'name': 'Follow @genlayer on X',
        'description': 'Stay in the loop on protocol updates, hackathons, and ecosystem news.',
        'points': 10,
        'verification_type': 'twitter_follow',
        'target_handle': 'genlayer',
        'action_url': 'https://x.com/intent/follow?screen_name=genlayer',
        'cta_text': 'Follow',
        'platform': 'twitter',
        'order': 10,
    },
    {
        'slug': 'join-genlayer-discord',
        'name': 'Join the GenLayer Discord',
        'description': 'Hang out with builders, validators, and the core team.',
        'points': 10,
        'verification_type': 'discord_guild_join',
        'target_guild_id': '',  # falls back to settings.DISCORD_GUILD_ID
        'action_url': 'https://discord.gg/genlayer',
        'cta_text': 'Join',
        'platform': 'discord',
        'order': 20,
    },
    {
        'slug': 'like-genlayer-launch-post',
        'name': 'Like our latest featured post',
        'description': 'Boost the GenLayer launch announcement on X.',
        'points': 5,
        'verification_type': 'click_through',
        'action_url': 'https://x.com/genlayer',
        'cta_text': 'Like',
        'platform': 'generic',
        'order': 30,
    },
]


def seed_tasks(apps, schema_editor):
    Category = apps.get_model('contributions', 'Category')
    SocialTask = apps.get_model('social_tasks', 'SocialTask')

    community, _ = Category.objects.get_or_create(
        slug='community',
        defaults={'name': 'Community', 'description': 'Community contributions and social actions.'},
    )

    for spec in SEED_TASKS:
        SocialTask.objects.update_or_create(
            slug=spec['slug'],
            defaults={
                'name': spec['name'],
                'description': spec['description'],
                'category': community,
                'points': spec['points'],
                'verification_type': spec['verification_type'],
                'target_handle': spec.get('target_handle', ''),
                'target_guild_id': spec.get('target_guild_id', ''),
                'action_url': spec['action_url'],
                'cta_text': spec['cta_text'],
                'platform': spec['platform'],
                'is_active': True,
                'order': spec['order'],
            },
        )


def noop_reverse(apps, schema_editor):
    """Intentional noop: keep admin edits on rollback. CreateModel below handles
    table drop on full rollback anyway."""
    pass


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contributions', '0053_add_show_in_contributions'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SocialTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(max_length=120, unique=True)),
                ('description', models.TextField(blank=True)),
                ('points', models.PositiveIntegerField(default=10, help_text='Points awarded on completion. Frozen as points_awarded on each completion row.')),
                ('verification_type', models.CharField(max_length=32)),
                ('target_handle', models.CharField(blank=True, help_text='X / Twitter handle without @. Used by: twitter_follow.', max_length=64)),
                ('target_guild_id', models.CharField(blank=True, help_text='Discord server (guild) id. Used by: discord_guild_join. Falls back to settings.DISCORD_GUILD_ID when blank.', max_length=64)),
                ('target_repo', models.CharField(blank=True, help_text='GitHub repository as owner/repo (e.g. genlayer-foundation/points). Used by: github_star.', max_length=140)),
                ('action_url', models.URLField(help_text='External URL the user is sent to on click.')),
                ('cta_text', models.CharField(default='Complete', max_length=50)),
                ('platform', models.CharField(default='generic', editable=False, max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('starts_at', models.DateTimeField(blank=True, null=True)),
                ('ends_at', models.DateTimeField(blank=True, null=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='social_tasks', to='contributions.category')),
            ],
            options={
                'ordering': ['order', 'created_at'],
            },
        ),
        migrations.CreateModel(
            name='SocialTaskCompletion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('points_awarded', models.PositiveIntegerField(help_text='Snapshot of task.points at completion time. Frozen.')),
                ('completed_at', models.DateTimeField(auto_now_add=True)),
                ('verification_type', models.CharField(max_length=32)),
                ('verification_data', models.JSONField(blank=True, default=dict)),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='completions', to='social_tasks.socialtask')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='social_task_completions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [models.Index(fields=['task', 'completed_at'], name='social_task_task_id_c83603_idx')],
                'unique_together': {('user', 'task')},
            },
        ),
        migrations.RunPython(seed_tasks, noop_reverse),
    ]
