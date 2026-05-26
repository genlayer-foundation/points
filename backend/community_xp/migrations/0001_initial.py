from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Mee6SyncRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('guild_id', models.CharField(db_index=True, max_length=100)),
                ('guild_name', models.CharField(blank=True, max_length=255)),
                ('status', models.CharField(choices=[('running', 'Running'), ('success', 'Success'), ('failed', 'Failed')], default='running', max_length=20)),
                ('page_size', models.PositiveIntegerField(default=1000)),
                ('pages_fetched', models.PositiveIntegerField(default=0)),
                ('players_fetched', models.PositiveIntegerField(default=0)),
                ('duplicate_players', models.PositiveIntegerField(default=0)),
                ('matched_players', models.PositiveIntegerField(default=0)),
                ('unmatched_players', models.PositiveIntegerField(default=0)),
                ('started_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('applied_at', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True)),
                ('applied_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='applied_mee6_sync_runs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-started_at', '-id'],
            },
        ),
        migrations.CreateModel(
            name='Mee6SyncLock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('owner_token', models.CharField(blank=True, db_index=True, max_length=32, null=True)),
                ('acquired_at', models.DateTimeField(blank=True, null=True)),
                ('heartbeat_at', models.DateTimeField(blank=True, null=True)),
                ('released_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'community_xp_mee6_sync_lock',
            },
        ),
        migrations.CreateModel(
            name='Mee6PlayerSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('guild_id', models.CharField(db_index=True, max_length=100)),
                ('discord_id', models.CharField(db_index=True, max_length=100)),
                ('username', models.CharField(blank=True, max_length=100)),
                ('discriminator', models.CharField(blank=True, max_length=10)),
                ('avatar_hash', models.CharField(blank=True, max_length=100)),
                ('rank', models.PositiveIntegerField()),
                ('xp', models.PositiveIntegerField(default=0)),
                ('level', models.PositiveIntegerField(default=0)),
                ('message_count', models.PositiveIntegerField(default=0)),
                ('detailed_xp', models.JSONField(blank=True, default=list)),
                ('raw_player', models.JSONField(blank=True, default=dict)),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='player_snapshots', to='community_xp.mee6syncrun')),
            ],
            options={
                'ordering': ['run', 'rank'],
                'unique_together': {('run', 'discord_id')},
            },
        ),
        migrations.CreateModel(
            name='Mee6CurrentXP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('guild_id', models.CharField(db_index=True, max_length=100)),
                ('discord_id', models.CharField(db_index=True, max_length=100)),
                ('username', models.CharField(blank=True, max_length=100)),
                ('discriminator', models.CharField(blank=True, max_length=10)),
                ('avatar_hash', models.CharField(blank=True, max_length=100)),
                ('rank', models.PositiveIntegerField()),
                ('xp', models.PositiveIntegerField(default=0)),
                ('level', models.PositiveIntegerField(default=0)),
                ('message_count', models.PositiveIntegerField(default=0)),
                ('detailed_xp', models.JSONField(blank=True, default=list)),
                ('matched_at', models.DateTimeField(blank=True, null=True)),
                ('synced_at', models.DateTimeField()),
                ('matched_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mee6_current_xp_rows', to=settings.AUTH_USER_MODEL)),
                ('source_snapshot', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='current_xp_rows', to='community_xp.mee6playersnapshot')),
                ('sync_run', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='current_xp_rows', to='community_xp.mee6syncrun')),
            ],
            options={
                'ordering': ['rank'],
                'unique_together': {('guild_id', 'discord_id')},
            },
        ),
        migrations.AddIndex(
            model_name='mee6syncrun',
            index=models.Index(fields=['guild_id', 'status', '-completed_at'], name='community_x_guild_i_e893a4_idx'),
        ),
        migrations.AddIndex(
            model_name='mee6syncrun',
            index=models.Index(fields=['status', '-started_at'], name='community_x_status_b13a2e_idx'),
        ),
        migrations.AddIndex(
            model_name='mee6playersnapshot',
            index=models.Index(fields=['guild_id', 'discord_id'], name='community_x_guild_i_3d03ef_idx'),
        ),
        migrations.AddIndex(
            model_name='mee6playersnapshot',
            index=models.Index(fields=['run', 'rank'], name='community_x_run_id_4608f5_idx'),
        ),
        migrations.AddIndex(
            model_name='mee6currentxp',
            index=models.Index(fields=['guild_id', 'rank'], name='community_x_guild_i_c99401_idx'),
        ),
        migrations.AddIndex(
            model_name='mee6currentxp',
            index=models.Index(fields=['guild_id', 'discord_id'], name='community_x_guild_i_c04a8b_idx'),
        ),
        migrations.AddIndex(
            model_name='mee6currentxp',
            index=models.Index(fields=['matched_user'], name='community_x_matched_04c14e_idx'),
        ),
        migrations.AddIndex(
            model_name='mee6currentxp',
            index=models.Index(fields=['sync_run'], name='community_x_sync_ru_274a7d_idx'),
        ),
    ]
