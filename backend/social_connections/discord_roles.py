"""Discord guild role synchronization via the Discord REST API."""

import time
from dataclasses import dataclass
from datetime import timedelta, timezone as datetime_timezone
from urllib.parse import quote

import requests
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from tally.middleware.logging_utils import get_app_logger
from tally.middleware.tracing import trace_external

from .models import DiscordConnection, DiscordRole

logger = get_app_logger('discord_roles')


class DiscordRoleSyncError(Exception):
    """Base exception for Discord role sync failures."""


class DiscordRoleSyncConfigurationError(DiscordRoleSyncError):
    """Discord role sync is not configured."""


class DiscordRoleSyncUnavailable(DiscordRoleSyncError):
    """Discord API could not satisfy the request right now."""

    def __init__(self, message, status_code=None, retry_after=None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


@dataclass
class MemberRoleSyncResult:
    connection: DiscordConnection
    is_member: bool


class DiscordRoleSyncService:
    """Small REST client and persistence layer for Discord guild roles."""

    api_base_url = 'https://discord.com/api/v10'

    def __init__(self, guild_id=None, bot_token=None, timeout=10):
        self.guild_id = guild_id or getattr(settings, 'DISCORD_GUILD_ID', '')
        self.bot_token = bot_token or getattr(settings, 'DISCORD_BOT_TOKEN', '')
        self.timeout = timeout

    def _ensure_configured(self):
        if not self.guild_id:
            raise DiscordRoleSyncConfigurationError('Discord guild not configured')
        if not self.bot_token:
            raise DiscordRoleSyncConfigurationError('Discord bot token not configured')

    def _parse_retry_after(self, response):
        retry_after = response.headers.get('Retry-After')
        try:
            if retry_after:
                return float(retry_after)
        except (TypeError, ValueError):
            pass

        try:
            data = response.json()
        except ValueError:
            return None

        retry_after = data.get('retry_after')
        try:
            return float(retry_after) if retry_after is not None else None
        except (TypeError, ValueError):
            return None

    def _request(self, method, path, trace_name, retry_once=True, audit_log_reason=None):
        self._ensure_configured()

        url = f"{self.api_base_url}{path}"
        headers = {
            'Authorization': f'Bot {self.bot_token}',
            'Accept': 'application/json',
        }
        if audit_log_reason:
            headers['X-Audit-Log-Reason'] = quote(audit_log_reason, safe='')

        try:
            with trace_external('discord', trace_name):
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    timeout=self.timeout,
                )
        except requests.RequestException as exc:
            logger.warning(
                "Discord request failed for %s %s: %s",
                method,
                path,
                exc,
            )
            raise DiscordRoleSyncUnavailable(
                'Discord request failed',
            ) from exc

        if response.status_code == 429 and retry_once:
            retry_after = self._parse_retry_after(response)
            if retry_after is not None and retry_after <= 2:
                time.sleep(retry_after)
                return self._request(
                    method,
                    path,
                    trace_name,
                    retry_once=False,
                    audit_log_reason=audit_log_reason,
                )
            raise DiscordRoleSyncUnavailable(
                'Discord rate limit exceeded',
                status_code=429,
                retry_after=retry_after,
            )

        return response

    def sync_role_catalog(self):
        """Fetch and persist all roles for the configured guild."""
        response = self._request(
            'GET',
            f'/guilds/{self.guild_id}/roles',
            'get_guild_roles',
        )

        if response.status_code in (401, 403):
            raise DiscordRoleSyncUnavailable(
                'Discord bot is not authorized to read guild roles',
                status_code=response.status_code,
            )
        if response.status_code >= 400:
            raise DiscordRoleSyncUnavailable(
                f'Discord role catalog request failed with {response.status_code}',
                status_code=response.status_code,
            )

        try:
            role_payloads = response.json()
        except ValueError as exc:
            raise DiscordRoleSyncUnavailable('Discord role catalog response was invalid') from exc

        now = timezone.now()
        seen_role_ids = set()
        synced_roles = []

        with transaction.atomic():
            for payload in role_payloads:
                role_id = str(payload.get('id') or '')
                name = str(payload.get('name') or '')[:100]
                if not role_id or not name:
                    continue

                seen_role_ids.add(role_id)
                role, _ = DiscordRole.objects.update_or_create(
                    guild_id=self.guild_id,
                    role_id=role_id,
                    defaults={
                        'name': name,
                        'color': int(payload.get('color') or 0),
                        'position': int(payload.get('position') or 0),
                        'hoist': bool(payload.get('hoist') or False),
                        'managed': bool(payload.get('managed') or False),
                        'mentionable': bool(payload.get('mentionable') or False),
                        'deleted_at': None,
                        'last_synced_at': now,
                    },
                )
                synced_roles.append(role)

            DiscordRole.objects.filter(
                guild_id=self.guild_id,
                deleted_at__isnull=True,
            ).exclude(
                role_id__in=seen_role_ids,
            ).update(
                deleted_at=now,
                last_synced_at=now,
            )

        return synced_roles

    def _get_or_create_missing_roles(self, role_ids):
        roles_by_id = {
            role.role_id: role
            for role in DiscordRole.objects.filter(
                guild_id=self.guild_id,
                role_id__in=role_ids,
            )
        }

        missing_ids = [role_id for role_id in role_ids if role_id not in roles_by_id]
        for role_id in missing_ids:
            role, _ = DiscordRole.objects.get_or_create(
                guild_id=self.guild_id,
                role_id=role_id,
                defaults={
                    'name': role_id,
                    'last_synced_at': timezone.now(),
                },
            )
            roles_by_id[role_id] = role

        return [roles_by_id[role_id] for role_id in role_ids if role_id in roles_by_id]

    def _record_not_member(self, connection):
        now = timezone.now()
        connection.guild_member = False
        connection.guild_checked_at = now
        connection.roles_synced_at = now
        connection.roles_sync_error = ''
        connection.guild_joined_at = None
        connection.guild_nick = ''
        connection.save(update_fields=[
            'guild_member',
            'guild_checked_at',
            'roles_synced_at',
            'roles_sync_error',
            'guild_joined_at',
            'guild_nick',
        ])
        connection.current_roles.clear()
        return MemberRoleSyncResult(connection=connection, is_member=False)

    def _record_sync_error(self, connection, message):
        connection.roles_sync_error = str(message)[:1000]
        connection.save(update_fields=['roles_sync_error'])

    def sync_member_roles(self, connection, sync_catalog=True):
        """Fetch and persist one linked user's membership and role IDs."""
        if sync_catalog:
            self.sync_role_catalog()

        response = self._request(
            'GET',
            f'/guilds/{self.guild_id}/members/{connection.platform_user_id}',
            'get_guild_member',
        )

        if response.status_code == 404:
            return self._record_not_member(connection)

        if response.status_code in (401, 403):
            message = 'Discord bot is not authorized to read guild members'
            self._record_sync_error(connection, message)
            raise DiscordRoleSyncUnavailable(message, status_code=response.status_code)

        if response.status_code >= 400:
            message = f'Discord member request failed with {response.status_code}'
            self._record_sync_error(connection, message)
            raise DiscordRoleSyncUnavailable(message, status_code=response.status_code)

        try:
            member_data = response.json()
        except ValueError as exc:
            message = 'Discord member response was invalid'
            self._record_sync_error(connection, message)
            raise DiscordRoleSyncUnavailable(message) from exc

        role_ids = [str(role_id) for role_id in member_data.get('roles', []) if role_id]
        roles = self._get_or_create_missing_roles(role_ids)

        joined_at = member_data.get('joined_at')
        parsed_joined_at = parse_datetime(joined_at) if joined_at else None
        if parsed_joined_at and timezone.is_naive(parsed_joined_at):
            parsed_joined_at = timezone.make_aware(parsed_joined_at, datetime_timezone.utc)

        now = timezone.now()
        connection.guild_member = True
        connection.guild_checked_at = now
        connection.roles_synced_at = now
        connection.roles_sync_error = ''
        connection.guild_joined_at = parsed_joined_at
        connection.guild_nick = str(member_data.get('nick') or '')[:100]
        connection.save(update_fields=[
            'guild_member',
            'guild_checked_at',
            'roles_synced_at',
            'roles_sync_error',
            'guild_joined_at',
            'guild_nick',
        ])
        connection.current_roles.set(roles)
        return MemberRoleSyncResult(connection=connection, is_member=True)

    def add_member_role(self, discord_user_id, role_id, audit_log_reason=None):
        """Assign one guild role to a member. Returns False if the member left."""
        response = self._request(
            'PUT',
            f'/guilds/{self.guild_id}/members/{discord_user_id}/roles/{role_id}',
            'add_member_role',
            audit_log_reason=audit_log_reason,
        )

        if response.status_code == 404:
            return False

        if response.status_code in (401, 403):
            raise DiscordRoleSyncUnavailable(
                'Discord bot is not authorized to manage guild roles',
                status_code=response.status_code,
            )

        if response.status_code >= 400:
            raise DiscordRoleSyncUnavailable(
                f'Discord role assignment failed with {response.status_code}',
                status_code=response.status_code,
            )

        return True

    def sync_oldest_connections(self, batch_size=None):
        """Sync a batch of linked Discord connections, oldest first."""
        batch_size = int(batch_size or getattr(settings, 'DISCORD_ROLE_SYNC_BATCH_SIZE', 500))
        self.sync_role_catalog()

        stats = {
            'checked': 0,
            'members': 0,
            'non_members': 0,
            'errors': 0,
        }

        connections = list(
            DiscordConnection.objects.order_by(
                F('roles_synced_at').asc(nulls_first=True),
                'id',
            )[:batch_size]
        )

        for connection in connections:
            stats['checked'] += 1
            try:
                result = self.sync_member_roles(connection, sync_catalog=False)
                if result.is_member:
                    stats['members'] += 1
                else:
                    stats['non_members'] += 1
            except DiscordRoleSyncError as exc:
                stats['errors'] += 1
                logger.warning(
                    "Failed to sync Discord roles for connection %s: %s",
                    connection.id,
                    exc,
                )

        return stats


def manual_refresh_next_allowed_at(connection):
    """Return when a user may next manually refresh Discord roles."""
    if not connection.roles_manual_synced_at:
        return None
    cooldown_seconds = int(
        getattr(settings, 'DISCORD_MANUAL_ROLE_SYNC_COOLDOWN_SECONDS', 30)
    )
    return connection.roles_manual_synced_at + timedelta(seconds=cooldown_seconds)
