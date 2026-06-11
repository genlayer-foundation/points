"""Twitter / X follow verifier, backed by Sorsa.

Requires:
- user has a linked TwitterConnection
- task.target_handle is set (the handle to follow, without @)
"""

import logging

from django.utils import timezone

from ..sorsa_client import SorsaError, get_default_client
from .base import Verifier, VerifierResult, register

logger = logging.getLogger(__name__)


@register
class TwitterFollowVerifier(Verifier):
    verification_type = 'twitter_follow'
    label = 'Follow on X / Twitter'
    platform = 'twitter'
    required_fields = ('target_handle',)
    requires_verification = True
    required_connection = 'twitter'

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
