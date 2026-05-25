# Generated for community contribution Discord XP tracking.

from django.conf import settings
from django.db import migrations, models
from django.utils import timezone
import django.db.models.deletion


def backfill_community_discord_xp_states(apps, schema_editor):
    Contribution = apps.get_model('contributions', 'Contribution')
    ContributionDiscordXPState = apps.get_model('contributions', 'ContributionDiscordXPState')

    community_contribution_ids = Contribution.objects.filter(
        contribution_type__category__slug='community',
    ).values_list('id', flat=True)

    now = timezone.now()
    batch = []
    for contribution_id in community_contribution_ids.iterator(chunk_size=1000):
        batch.append(ContributionDiscordXPState(
            contribution_id=contribution_id,
            status='pending',
            awarded_amount=0,
            created_at=now,
            updated_at=now,
        ))
        if len(batch) >= 1000:
            ContributionDiscordXPState.objects.bulk_create(
                batch,
                ignore_conflicts=True,
                batch_size=1000,
            )
            batch = []

    if batch:
        ContributionDiscordXPState.objects.bulk_create(
            batch,
            ignore_conflicts=True,
            batch_size=1000,
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0060_contributiontype_required_discord_roles'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ContributionDiscordXPState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('distributed', 'Distributed'), ('needs_review', 'Needs review')], db_index=True, default='pending', max_length=20)),
                ('awarded_amount', models.PositiveIntegerField(default=0)),
                ('distributed_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('last_copied_at', models.DateTimeField(blank=True, null=True)),
                ('contribution', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='discord_xp_state', to='contributions.contribution')),
                ('distributed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='discord_xp_states_distributed', to=settings.AUTH_USER_MODEL)),
                ('last_copied_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='discord_xp_states_copied', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-contribution__created_at'],
                'indexes': [models.Index(fields=['status', 'distributed_at'], name='contrib_xp_status_dist_idx')],
            },
        ),
        migrations.CreateModel(
            name='DiscordXPDistributionEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('amount', models.PositiveIntegerField()),
                ('action', models.CharField(choices=[('copied', 'Copied command'), ('distributed', 'Marked distributed'), ('unset', 'Unset distributed')], db_index=True, max_length=20)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='discord_xp_distribution_events_made', to=settings.AUTH_USER_MODEL)),
                ('state', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='contributions.contributiondiscordxpstate')),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['action', 'created_at'], name='xp_event_action_created_idx'), models.Index(fields=['state', 'created_at'], name='xp_event_state_created_idx')],
            },
        ),
        migrations.RunPython(backfill_community_discord_xp_states, noop_reverse),
    ]
