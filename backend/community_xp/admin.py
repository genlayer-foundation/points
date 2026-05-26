from django.contrib import admin
from django.contrib import messages

from .models import (
    Mee6CurrentXP,
    Mee6PlayerSnapshot,
    Mee6SyncLock,
    Mee6SyncRun,
)
from .services import Mee6SyncError, apply_sync_run


@admin.register(Mee6SyncRun)
class Mee6SyncRunAdmin(admin.ModelAdmin):
    actions = ('apply_as_active_baseline',)
    list_display = (
        'id',
        'guild_id',
        'guild_name',
        'status',
        'applied_at',
        'players_fetched',
        'matched_players',
        'unmatched_players',
        'duplicate_players',
        'started_at',
        'completed_at',
    )
    list_filter = ('status', 'guild_id')
    search_fields = ('guild_id', 'guild_name', 'error_message')
    readonly_fields = (
        'created_at',
        'updated_at',
        'started_at',
        'completed_at',
        'applied_at',
        'applied_by',
    )

    @admin.action(description='Apply selected MEE6 run as active community XP baseline')
    def apply_as_active_baseline(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                'Select exactly one successful MEE6 sync run to apply.',
                level=messages.ERROR,
            )
            return

        run = queryset.first()
        try:
            result = apply_sync_run(run, applied_by=request.user)
        except Mee6SyncError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
            return

        self.message_user(
            request,
            (
                f"Applied MEE6 sync #{run.id}: "
                f"{result['players_applied']} players, "
                f"{result['matched_players']} matched, "
                f"{result['unmatched_players']} unmatched."
            ),
            level=messages.SUCCESS,
        )


@admin.register(Mee6PlayerSnapshot)
class Mee6PlayerSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'run',
        'rank',
        'username',
        'discord_id',
        'xp',
        'level',
    )
    list_filter = ('guild_id', 'run__status')
    search_fields = (
        'discord_id',
        'username',
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Mee6CurrentXP)
class Mee6CurrentXPAdmin(admin.ModelAdmin):
    list_display = (
        'rank',
        'username',
        'discord_id',
        'xp',
        'level',
        'matched_user',
        'synced_at',
    )
    list_filter = ('guild_id',)
    search_fields = (
        'discord_id',
        'username',
        'matched_user__email',
        'matched_user__address',
    )
    readonly_fields = ('created_at', 'updated_at', 'synced_at')


@admin.register(Mee6SyncLock)
class Mee6SyncLockAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner_token', 'acquired_at', 'heartbeat_at', 'released_at')
    readonly_fields = ('name', 'owner_token', 'acquired_at', 'heartbeat_at', 'released_at')
