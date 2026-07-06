"""The AI steward identity used for attribution of automated review actions.

Service account tokens authenticate the external AI agent, but its proposals,
notes, and Tier-1 auto-rejects are attributed to this hidden portal user
(visible=False, unusable password, never a login identity).
"""

from django.contrib.auth import get_user_model

AI_STEWARD_EMAIL = 'genlayer-steward@genlayer.foundation'
AI_STEWARD_NAME = 'GenLayer Steward'


def get_ai_steward():
    """Get or create the AI steward user (self-healing, no 500 path)."""
    user, created = get_user_model().objects.get_or_create(
        email=AI_STEWARD_EMAIL,
        defaults={'name': AI_STEWARD_NAME, 'visible': False},
    )
    if created:
        user.set_unusable_password()
        user.save()
    return user
