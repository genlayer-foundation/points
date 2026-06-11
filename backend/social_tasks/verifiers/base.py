"""Verifier base class + registry for social tasks.

Each verification logic lives in its own module under `verifiers/` and registers
a `Verifier` subclass via the @register decorator. New logics are picked up
automatically by:

- `SocialTask.verification_type` choices in admin (rendered from `get_choices()`)
- `SocialTask.clean()` validation (uses `required_fields_for()`)
- `SocialTask.save()` to set the derived `platform` column
- The view's `complete` action (calls `verify()`)
- The serializer's `requires_verification` flag

Adding a new logic = one new file under `verifiers/` declaring a Verifier
subclass + @register. No central edits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class VerifierResult:
    ok: bool
    audit: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None


class Verifier:
    """Base class for social task verifiers.

    Subclasses declare:

        verification_type:     str, slug stored on SocialTask.verification_type
        label:                 str, admin-facing dropdown label
        platform:              str, drives the UI icon ('twitter'/'discord'/...)
        required_fields:       tuple of SocialTask field names that must be set
        requires_verification: False means "trust on click" — frontend will
                               award immediately on open without a verify step
        required_connection:   social connection the user must have linked
                               before this verifier can run ('twitter',
                               'discord', ...), or None. Shipped to the
                               frontend so the card can offer inline linking
                               without knowing verification_type slugs.

    Subclasses implement `verify(task, user) -> VerifierResult`.
    """

    verification_type: str = ''
    label: str = ''
    platform: str = 'generic'
    required_fields: tuple[str, ...] = ()
    requires_verification: bool = True
    required_connection: str | None = None

    def verify(self, task, user) -> VerifierResult:
        raise NotImplementedError


_REGISTRY: dict[str, Verifier] = {}


def register(verifier_cls: type[Verifier]) -> type[Verifier]:
    """Class decorator to register a Verifier in the global registry."""
    instance = verifier_cls()
    if not instance.verification_type:
        raise ValueError(
            f'{verifier_cls.__name__} must declare verification_type'
        )
    existing = _REGISTRY.get(instance.verification_type)
    if existing is not None:
        # Fail at import time: a silent overwrite would route verification
        # for every task of this type to the wrong implementation.
        raise ValueError(
            f'{verifier_cls.__name__} reuses verification_type '
            f'{instance.verification_type!r} already registered by '
            f'{type(existing).__name__}'
        )
    _REGISTRY[instance.verification_type] = instance
    return verifier_cls


def get_verifier(verification_type: str) -> Verifier | None:
    return _REGISTRY.get(verification_type)


def get_choices() -> list[tuple[str, str]]:
    """Choices tuple for admin dropdowns / serializers."""
    return sorted(
        ((v.verification_type, v.label) for v in _REGISTRY.values()),
        key=lambda pair: pair[1],
    )


def required_fields_for(verification_type: str) -> tuple[str, ...]:
    v = get_verifier(verification_type)
    return v.required_fields if v else ()


def platform_for(verification_type: str) -> str:
    v = get_verifier(verification_type)
    return v.platform if v else 'generic'


def requires_verification_for(verification_type: str) -> bool:
    v = get_verifier(verification_type)
    return bool(v and v.requires_verification)


def required_connection_for(verification_type: str) -> str | None:
    v = get_verifier(verification_type)
    return v.required_connection if v else None


def verify(task, user) -> VerifierResult:
    """Run the verifier registered for `task.verification_type`."""
    verifier = get_verifier(task.verification_type)
    if verifier is None:
        return VerifierResult(False, {}, 'unsupported_verification_type')
    return verifier.verify(task, user)
