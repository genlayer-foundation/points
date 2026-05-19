# Generated manually for the portal POAP system.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q
from django.utils import timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PoapDrop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=180)),
                ('slug', models.SlugField(blank=True, max_length=200, unique=True)),
                ('description', models.TextField(blank=True)),
                ('artwork_url', models.URLField(blank=True, max_length=500)),
                ('artwork_public_id', models.CharField(blank=True, max_length=255)),
                ('event_start_at', models.DateTimeField()),
                ('event_end_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('archived', 'Archived')], default='draft', max_length=20)),
                ('max_claims', models.PositiveIntegerField(blank=True, null=True)),
                ('legacy_poap_id', models.CharField(blank=True, db_index=True, max_length=100)),
                ('discord_role_id', models.CharField(blank=True, max_length=100)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_poap_drops', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-event_start_at', '-created_at'],
                'indexes': [models.Index(fields=['status', 'event_start_at'], name='poaps_poapd_status_99326a_idx')],
                'constraints': [models.UniqueConstraint(condition=~Q(legacy_poap_id=''), fields=('legacy_poap_id',), name='unique_poap_drop_legacy_poap_id')],
            },
        ),
        migrations.CreateModel(
            name='PoapImportBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('source_name', models.CharField(max_length=100)),
                ('file_name', models.CharField(blank=True, max_length=255)),
                ('total_rows', models.PositiveIntegerField(default=0)),
                ('imported_count', models.PositiveIntegerField(default=0)),
                ('matched_count', models.PositiveIntegerField(default=0)),
                ('unmatched_count', models.PositiveIntegerField(default=0)),
                ('error_count', models.PositiveIntegerField(default=0)),
                ('errors', models.JSONField(blank=True, default=list)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='poap_import_batches', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='PoapDistribution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('method', models.CharField(choices=[('secret', 'Secret phrase'), ('mint_link', 'Mint link'), ('discord_voice', 'Discord voice')], max_length=30)),
                ('active', models.BooleanField(default=True)),
                ('starts_at', models.DateTimeField(blank=True, null=True)),
                ('ends_at', models.DateTimeField(blank=True, null=True)),
                ('max_claims', models.PositiveIntegerField(blank=True, null=True)),
                ('claimed_count', models.PositiveIntegerField(default=0)),
                ('secret_hash', models.CharField(blank=True, max_length=128)),
                ('drop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='distributions', to='poaps.poapdrop')),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['method', 'active', 'starts_at', 'ends_at'], name='poaps_poapd_method_bd5594_idx')],
            },
        ),
        migrations.CreateModel(
            name='PoapMintLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('token_hash', models.CharField(max_length=128, unique=True)),
                ('token_ciphertext', models.TextField(blank=True)),
                ('max_uses', models.PositiveIntegerField(default=1)),
                ('used_count', models.PositiveIntegerField(default=0)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('distribution', models.ForeignKey(limit_choices_to={'method': 'mint_link'}, on_delete=django.db.models.deletion.CASCADE, related_name='mint_links', to='poaps.poapdistribution')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='PoapClaim',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('claim_method', models.CharField(choices=[('secret', 'Secret phrase'), ('mint_link', 'Mint link'), ('discord_voice', 'Discord voice'), ('admin', 'Admin'), ('legacy', 'Legacy import')], max_length=30)),
                ('claimed_at', models.DateTimeField(default=timezone.now)),
                ('source', models.CharField(choices=[('portal', 'Portal'), ('legacy_import', 'Legacy import')], default='portal', max_length=30)),
                ('legacy_wallet_address', models.CharField(blank=True, db_index=True, max_length=100)),
                ('legacy_email', models.EmailField(blank=True, db_index=True, max_length=254)),
                ('legacy_external_id', models.CharField(blank=True, db_index=True, max_length=120)),
                ('legacy_metadata', models.JSONField(blank=True, default=dict)),
                ('distribution', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='claims', to='poaps.poapdistribution')),
                ('drop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='claims', to='poaps.poapdrop')),
                ('import_batch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='claims', to='poaps.poapimportbatch')),
                ('mint_link', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='claims', to='poaps.poapmintlink')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='poap_claims', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-claimed_at', '-created_at'],
                'indexes': [
                    models.Index(fields=['drop', 'claimed_at'], name='poaps_poapc_drop_id_aaf02a_idx'),
                    models.Index(fields=['user', 'claimed_at'], name='poaps_poapc_user_id_99543b_idx'),
                ],
                'constraints': [models.UniqueConstraint(condition=Q(('user__isnull', False)), fields=('drop', 'user'), name='unique_poap_claim_per_user_drop')],
            },
        ),
    ]
