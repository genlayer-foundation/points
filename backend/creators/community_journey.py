"""Community journey logic: the 5 steps to become a Creator (community member).

1. Link X            -> `community-link-x` contribution (existing reward)
2. Link Discord      -> `community-link-discord` contribution (existing reward)
3. Follow GenLayer   -> `follow-genlayer-x` social task completion
4. Join Discord      -> `join-genlayer-discord` social task completion
5. X post with code  -> a CommunityPostProof, verified via Sorsa /tweet-info

Completing all 5 grants the Creator role (point-free); steps 1-4 keep their own
existing points. The X-post step uses a deterministic per-user code (no storage
of the code needed) and the post must @mention GenLayer and come from the user's
linked X account.
"""

import hashlib
import hmac
import re
from urllib.parse import quote

from django.conf import settings

LINK_X_SLUG = 'community-link-x'
LINK_DISCORD_SLUG = 'community-link-discord'
FOLLOW_TASK_SLUG = 'follow-genlayer-x'
JOIN_DISCORD_TASK_SLUG = 'join-genlayer-discord'
WELCOME_SLUG = 'community-welcome'

CODE_PREFIX = 'GL-'

# A well-formed X / Twitter post URL: https://x.com/<handle>/status/<id>
X_POST_RE = re.compile(
    r'^https?://(?:www\.)?(?:x\.com|twitter\.com)/'
    r'(?P<handle>[A-Za-z0-9_]{1,15})/status(?:es)?/(?P<id>\d+)',
    re.IGNORECASE,
)


def genlayer_handle() -> str:
    return getattr(settings, 'GENLAYER_X_HANDLE', 'genlayer').lstrip('@').lower()


def verification_code(user) -> str:
    """Deterministic per-user code embedded in the X post. Recomputed at verify
    time, so nothing is stored. Tied to SECRET_KEY so it cannot be guessed."""
    digest = hmac.new(
        settings.SECRET_KEY.encode(),
        f'community-x-post:{user.pk}'.encode(),
        hashlib.sha256,
    ).hexdigest()[:8].upper()
    return f'{CODE_PREFIX}{digest}'


def share_text(user) -> str:
    return f"I'm joining the @{genlayer_handle()} community! {verification_code(user)}"


def intent_url(user) -> str:
    return f'https://x.com/intent/post?text={quote(share_text(user))}'


def parse_x_post(url: str):
    """Return (handle_lower, tweet_id) for a well-formed X post URL, else (None, None)."""
    match = X_POST_RE.match((url or '').strip())
    if not match:
        return None, None
    return match.group('handle').lower(), match.group('id')


def post_matches(full_text: str, user):
    """Whether the tweet text contains the user's code and @mentions GenLayer.
    Returns (ok, error_code)."""
    text = (full_text or '').lower()
    if verification_code(user).lower() not in text:
        return False, 'code_missing'
    handle_re = re.compile(rf'(^|[^a-z0-9_])@{re.escape(genlayer_handle())}(?![a-z0-9_])')
    if not handle_re.search(text):
        return False, 'tag_missing'
    return True, None


def _has_contribution(user, slug) -> bool:
    from contributions.models import Contribution
    return Contribution.objects.filter(user=user, contribution_type__slug=slug).exists()


def _has_task_completion(user, slug) -> bool:
    from social_tasks.models import SocialTaskCompletion
    return SocialTaskCompletion.objects.filter(user=user, task__slug=slug).exists()


def is_started(user) -> bool:
    return _has_contribution(user, WELCOME_SLUG)


def step_states(user) -> dict:
    return {
        'link_x': _has_contribution(user, LINK_X_SLUG),
        'link_discord': _has_contribution(user, LINK_DISCORD_SLUG),
        'follow_x': _has_task_completion(user, FOLLOW_TASK_SLUG),
        'join_discord': _has_task_completion(user, JOIN_DISCORD_TASK_SLUG),
        'x_post': hasattr(user, 'community_post_proof'),
    }


def journey_status(user) -> dict:
    # Existing community members (the Creator role) are grandfathered in: the
    # journey only applies to newcomers, so a member is always treated as
    # started/complete regardless of the newer welcome-marker + step records.
    is_creator = hasattr(user, 'creator')
    states = step_states(user)
    started = is_creator or is_started(user)
    missing_steps = [key for key, done in states.items() if not done]
    proof = getattr(user, 'community_post_proof', None)
    return {
        'started': started,
        'steps': {
            'link_x': {'done': states['link_x']},
            'link_discord': {'done': states['link_discord']},
            'follow_x': {'done': states['follow_x']},
            'join_discord': {'done': states['join_discord']},
            'x_post': {
                'done': states['x_post'],
                'verification_code': verification_code(user),
                'share_text': share_text(user),
                'intent_url': intent_url(user),
                'post_url': proof.post_url if proof else None,
            },
        },
        'missing_steps': missing_steps,
        'complete': is_creator or (started and not missing_steps),
        'is_member': is_creator,
    }
