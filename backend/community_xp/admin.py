from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import path

from .models import (
    Mee6CurrentXP,
    Mee6PlayerSnapshot,
    Mee6SyncLock,
    Mee6SyncRun,
)
from .services import Mee6SyncAlreadyRunning, Mee6SyncError, apply_sync_run, run_mee6_sync


@admin.register(Mee6SyncRun)
class Mee6SyncRunAdmin(admin.ModelAdmin):
    actions = ('fetch_new_snapshot', 'apply_as_active_baseline')
    change_list_template = 'admin/community_xp/mee6syncrun/change_list.html'
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

    def get_urls(self):
        return [
            path(
                'fetch-new-snapshot/',
                self.admin_site.admin_view(self.fetch_new_snapshot_view),
                name='community_xp_mee6syncrun_fetch_new_snapshot',
            ),
        ] + super().get_urls()

    def fetch_new_snapshot_view(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied
        if request.method == 'POST':
            self._fetch_new_snapshot(request)
        return redirect('..')

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['can_fetch_new_snapshot'] = self.has_add_permission(request)
        return super().changelist_view(request, extra_context=extra_context)

    def _fetch_new_snapshot(self, request, guild_id=None, page_size=None):
        try:
            result = run_mee6_sync(
                guild_id=guild_id,
                page_size=page_size,
            )
        except Mee6SyncAlreadyRunning as exc:
            elapsed = f" for {exc.elapsed_seconds:.0f}s" if exc.elapsed_seconds is not None else ''
            self.message_user(
                request,
                f'MEE6 XP sync already running{elapsed}.',
                level=messages.ERROR,
            )
            return
        except Mee6SyncError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
            return

        self.message_user(
            request,
            (
                f"Fetched MEE6 sync #{result['run_id']}: "
                f"{result['players_fetched']} players, "
                f"{result['matched_players']} matched, "
                f"{result['unmatched_players']} unmatched, "
                f"{result['pages_fetched']} pages. "
                "Apply it to update active community XP."
            ),
            level=messages.SUCCESS,
        )

    @admin.action(description='Fetch new MEE6 XP snapshot using selected run settings')
    def fetch_new_snapshot(self, request, queryset):
        if not self.has_add_permission(request) or not self.has_change_permission(request):
            raise PermissionDenied
        if queryset.count() != 1:
            self.message_user(
                request,
                'Select exactly one MEE6 sync run to reuse its guild and page size.',
                level=messages.ERROR,
            )
            return

        source_run = queryset.first()
        self._fetch_new_snapshot(
            request,
            guild_id=source_run.guild_id,
            page_size=source_run.page_size,
        )

    @admin.action(description='Apply selected MEE6 run as active community XP baseline')
    def apply_as_active_baseline(self, request, queryset):
        if not self.has_change_permission(request):
            raise PermissionDenied
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
