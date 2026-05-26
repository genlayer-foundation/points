from django.conf import settings
from django.db import models
from django.utils import timezone

from utils.models import BaseModel


class Mee6SyncRun(BaseModel):
    STATUS_RUNNING = 'running'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_RUNNING, 'Running'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED, 'Failed'),
    ]

    guild_id = models.CharField(max_length=100, db_index=True)
    guild_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RUNNING)
    page_size = models.PositiveIntegerField(default=1000)
    pages_fetched = models.PositiveIntegerField(default=0)
    players_fetched = models.PositiveIntegerField(default=0)
    duplicate_players = models.PositiveIntegerField(default=0)
    matched_players = models.PositiveIntegerField(default=0)
    unmatched_players = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applied_mee6_sync_runs',
    )
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-started_at', '-id']
        indexes = [
            models.Index(fields=['guild_id', 'status', '-completed_at']),
            models.Index(fields=['status', '-started_at']),
        ]

    def __str__(self):
        return f"MEE6 sync {self.guild_id} #{self.pk} ({self.status})"


class Mee6PlayerSnapshot(BaseModel):
    run = models.ForeignKey(
        Mee6SyncRun,
        on_delete=models.CASCADE,
        related_name='player_snapshots',
    )
    guild_id = models.CharField(max_length=100, db_index=True)
    discord_id = models.CharField(max_length=100, db_index=True)
    username = models.CharField(max_length=100, blank=True)
    discriminator = models.CharField(max_length=10, blank=True)
    avatar_hash = models.CharField(max_length=100, blank=True)
    rank = models.PositiveIntegerField()
    xp = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=0)
    message_count = models.PositiveIntegerField(default=0)
    detailed_xp = models.JSONField(default=list, blank=True)
    raw_player = models.JSONField(default=dict, blank=True)
    matched_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mee6_player_snapshots',
    )
    matched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['run', 'rank']
        unique_together = [('run', 'discord_id')]
        indexes = [
            models.Index(fields=['guild_id', 'discord_id']),
            models.Index(fields=['run', 'rank']),
            models.Index(fields=['matched_user']),
        ]

    def __str__(self):
        return f"{self.discord_id} - {self.xp} XP ({self.guild_id})"


class Mee6CurrentXP(BaseModel):
    guild_id = models.CharField(max_length=100, db_index=True)
    discord_id = models.CharField(max_length=100, db_index=True)
    username = models.CharField(max_length=100, blank=True)
    discriminator = models.CharField(max_length=10, blank=True)
    avatar_hash = models.CharField(max_length=100, blank=True)
    rank = models.PositiveIntegerField()
    xp = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=0)
    message_count = models.PositiveIntegerField(default=0)
    detailed_xp = models.JSONField(default=list, blank=True)
    sync_run = models.ForeignKey(
        Mee6SyncRun,
        on_delete=models.PROTECT,
        related_name='current_xp_rows',
    )
    source_snapshot = models.ForeignKey(
        Mee6PlayerSnapshot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_xp_rows',
    )
    matched_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mee6_current_xp_rows',
    )
    matched_at = models.DateTimeField(null=True, blank=True)
    synced_at = models.DateTimeField()

    class Meta:
        ordering = ['rank']
        unique_together = [('guild_id', 'discord_id')]
        indexes = [
            models.Index(fields=['guild_id', 'rank']),
            models.Index(fields=['guild_id', 'discord_id']),
            models.Index(fields=['matched_user']),
            models.Index(fields=['sync_run']),
        ]

    def __str__(self):
        return f"{self.discord_id} - {self.xp} current XP ({self.guild_id})"


class Mee6SyncLock(models.Model):
    name = models.CharField(max_length=100, unique=True)
    owner_token = models.CharField(max_length=32, null=True, blank=True, db_index=True)
    acquired_at = models.DateTimeField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'community_xp_mee6_sync_lock'

    def __str__(self):
        return f"Mee6SyncLock({self.name}, acquired={self.acquired_at})"
