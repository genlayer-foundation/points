"""Discord guild membership verifier.

Requires the user to have linked their Discord account; takes the target guild
from `SocialTask.target_guild_id` with a fallback to `settings.DISCORD_GUILD_ID`.

We perform the Discord API call inline rather than going through
`DiscordOAuthService.check_guild_membership` because that helper collapses
401 / 404 / 5xx all into `False`. We need to distinguish them so the
frontend can prompt re-link on expired tokens and retry on service errors
instead of telling the user "we did not see you in the server yet".
"""

import logging

import requests
from cryptography.fernet import InvalidToken
from django.conf import settings
from django.utils import timezone

from social_connections.encryption import decrypt_token
from tally.middleware.tracing import trace_external

from .base import Verifier, VerifierResult, register

logger = logging.getLogger(__name__)


DISCORD_GUILD_MEMBER_URL = 'https://discord.com/api/v10/users/@me/guilds/{guild_id}/member'
DISCORD_REQUEST_TIMEOUT = 8.0


@register
class DiscordGuildJoinVerifier(Verifier):
    verification_type = 'discord_guild_join'
    label = 'Join Discord server'
    platform = 'discord'
    required_fields = ()  # target_guild_id is optional (falls back to settings.DISCORD_GUILD_ID)
    requires_verification = True
    required_connection = 'discord'

    def verify(self, task, user) -> VerifierResult:
        connection = getattr(user, 'discordconnection', None)
        if connection is None:
            return VerifierResult(False, {'platform': 'discord'}, 'social_account_not_linked')

        if not connection.access_token:
            return VerifierResult(False, {'platform': 'discord'}, 'token_invalid_relink_required')

        try:
            token = decrypt_token(connection.access_token)
        except InvalidToken:
            logger.warning('Failed to decrypt Discord token for user %s', user.pk)
            return VerifierResult(False, {'platform': 'discord'}, 'token_invalid_relink_required')

        guild_id = (task.target_guild_id or '').strip() or getattr(settings, 'DISCORD_GUILD_ID', '')
        if not guild_id:
            logger.error('Discord guild_id missing for task %s', task.slug)
            return VerifierResult(False, {}, 'verification_unavailable')

        try:
            with trace_external('discord', 'check_guild'):
                response = requests.get(
                    DISCORD_GUILD_MEMBER_URL.format(guild_id=guild_id),
                    headers={'Authorization': f'Bearer {token}'},
                    timeout=DISCORD_REQUEST_TIMEOUT,
                )
        except requests.RequestException as exc:
            logger.warning('Discord guild check transport error for user %s: %s', user.pk, exc)
            return VerifierResult(
                False,
                {'platform': 'discord', 'guild_id': guild_id, 'error': str(exc)},
                'verification_unavailable',
            )

        audit = {
            'kind': 'discord_guild_join',
            'guild_id': guild_id,
            'status_code': response.status_code,
            'checked_at': timezone.now().isoformat(),
        }

        # Only cache the cached guild_member flag when we just checked the
        # configured main GenLayer guild. Otherwise a task that targets a
        # campaign-specific guild would clobber the user's main-guild status.
        is_main_guild = guild_id == getattr(settings, 'DISCORD_GUILD_ID', '')

        if response.status_code == 200:
            if is_main_guild:
                self._cache_membership(connection, True)
            return VerifierResult(True, audit, None)

        if response.status_code == 404:
            if is_main_guild:
                self._cache_membership(connection, False)
            return VerifierResult(False, audit, 'verification_failed')

        if response.status_code in (401, 403):
            logger.warning(
                'Discord token rejected during guild check for user %s (status %s)',
                user.pk, response.status_code,
            )
            return VerifierResult(
                False,
                {**audit, 'platform': 'discord'},
                'token_invalid_relink_required',
            )

        # 429, 5xx, anything else -> service issue; tell the user to retry.
        logger.error(
            'Discord guild check returned status %s for task %s',
            response.status_code, task.slug,
        )
        return VerifierResult(False, audit, 'verification_unavailable')

    @staticmethod
    def _cache_membership(connection, is_member):
        connection.guild_member = is_member
        connection.guild_checked_at = timezone.now()
        connection.save(update_fields=['guild_member', 'guild_checked_at'])
