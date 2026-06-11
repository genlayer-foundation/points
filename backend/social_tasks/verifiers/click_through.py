"""Click-through "verifier" — trust the user on click, no API check."""

from django.utils import timezone

from .base import Verifier, VerifierResult, register


@register
class ClickThroughVerifier(Verifier):
    verification_type = 'click_through'
    label = 'Click through (no verification)'
    platform = 'generic'
    required_fields = ()
    requires_verification = False

    def verify(self, task, user) -> VerifierResult:
        audit = {
            'kind': 'click_through',
            'at': timezone.now().isoformat(),
        }
        return VerifierResult(True, audit, None)
