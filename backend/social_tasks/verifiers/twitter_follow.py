"""Twitter / X follow verifier, backed by Sorsa.

Requires:
- user has a linked TwitterConnection
- task.target_handle is set (the handle to follow, without @)
"""

import logging
import re

from django.utils import timezone

from ..sorsa_client import SorsaError, get_default_client
from .base import Verifier, VerifierResult, register

logger = logging.getLogger(__name__)

# X / Twitter usernames: 1-15 letters, digits, or underscores; optional @.
HANDLE_RE = re.compile(r'^@?[A-Za-z0-9_]{1,15}$')


@register
class TwitterFollowVerifier(Verifier):
    verification_type = 'twitter_follow'
    label = 'Follow on X / Twitter'
    platform = 'twitter'
    required_fields = ('target_handle',)
    requires_verification = True
    required_connection = 'twitter'

    def clean_task(self, task) -> dict[str, str]:
        handle = (task.target_handle or '').strip()
        if not HANDLE_RE.match(handle):
            return {
                'target_handle': (
                    'Must be a bare X handle (1-15 letters, digits or underscores, '
                    'optional leading @) — not a profile URL.'
                )
            }
        return {}

    def derive_action_url(self, task) -> str | None:
        handle = (task.target_handle or '').strip().lstrip('@')
        if not handle:
            return None
        return f'https://x.com/intent/follow?screen_name={handle}'

    def verify(self, task, user) -> VerifierResult:
        connection = getattr(user, 'twitterconnection', None)
        if connection is None:
            return VerifierResult(False, {'platform': 'twitter'}, 'social_account_not_linked')

        actor_handle = (connection.platform_username or '').strip()
        target_handle = (task.target_handle or '').strip()
        if not actor_handle or not target_handle:
            logger.error('Twitter follow verification missing handles for task %s', task.slug)
            return VerifierResult(False, {}, 'verification_unavailable')

        try:
            is_following, sorsa_audit = get_default_client().is_following(actor_handle, target_handle)
        except SorsaError as exc:
            logger.warning('Sorsa follow check failed for user %s: %s', user.pk, exc)
            return VerifierResult(False, {'error': str(exc)}, 'verification_unavailable')

        audit = {
            'kind': 'twitter_follow',
            'sorsa': sorsa_audit,
            'checked_at': timezone.now().isoformat(),
        }
        if is_following:
            return VerifierResult(True, audit, None)
        return VerifierResult(False, audit, 'verification_failed')
