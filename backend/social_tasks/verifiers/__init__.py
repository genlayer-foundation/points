"""Verifier registry public API.

Adding a new verifier:
1. Create `social_tasks/verifiers/<name>.py` declaring a `Verifier` subclass
   with @register.
2. Import the module from this file (side-effect import below).
3. Done — the model, admin, serializer, and view auto-pick it up via the
   registry helpers exported here.
"""

from .base import (
    Verifier,
    VerifierResult,
    get_choices,
    get_verifier,
    platform_for,
    required_connection_for,
    required_fields_for,
    requires_verification_for,
    verify,
)

# Side-effect imports register each verifier in the registry.
from . import click_through  # noqa: F401
from . import discord_guild_join  # noqa: F401
from . import github_star  # noqa: F401
from . import twitter_follow  # noqa: F401


__all__ = [
    'Verifier',
    'VerifierResult',
    'get_choices',
    'get_verifier',
    'platform_for',
    'required_connection_for',
    'required_fields_for',
    'requires_verification_for',
    'verify',
]
