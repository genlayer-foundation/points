"""Community journey logic: the 5 steps to become a Creator.

1. Link X            -> `community-link-x` contribution (existing reward)
2. Link Discord      -> `community-link-discord` contribution (existing reward)
3. Follow GenLayer   -> `follow-genlayer-x` social task completion
4. Join Discord      -> `join-genlayer-discord` social task completion
5. X post with referral code -> a CommunityPostProof, verified via Sorsa /tweet-info

Completing all 5 grants the Creator role (point-free); steps 1-4 keep their own
existing points. The X-post step uses the user's referral code and the post must
@mention GenLayer and come from the user's linked X account.
"""

import re
from urllib.parse import parse_qs, quote, urlparse

from django.conf import settings

LINK_X_SLUG = 'community-link-x'
LINK_DISCORD_SLUG = 'community-link-discord'
FOLLOW_TASK_SLUG = 'follow-genlayer-x'
JOIN_DISCORD_TASK_SLUG = 'join-genlayer-discord'
WELCOME_SLUG = 'community-welcome'
PORTAL_REFERRAL_BASE_URL = 'https://portal.genlayer.foundation'

# A well-formed X / Twitter post URL: https://x.com/<handle>/status/<id>
X_POST_RE = re.compile(
    r'^https?://(?:www\.)?(?:x\.com|twitter\.com)/'
    r'(?P<handle>[A-Za-z0-9_]{1,15})/status(?:es)?/(?P<id>\d+)',
    re.IGNORECASE,
)
URL_RE = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)
TRAILING_URL_PUNCTUATION = '.,!?:;)]}'


def genlayer_handle() -> str:
    return getattr(settings, 'GENLAYER_X_HANDLE', 'genlayer').lstrip('@').lower()


def genlayer_mention() -> str:
    handle = getattr(settings, 'GENLAYER_X_HANDLE', 'GenLayer').lstrip('@')
    return 'GenLayer' if handle.lower() == 'genlayer' else handle


def _ensure_referral_code(user) -> str:
    """Return a persisted referral code, creating one for stale legacy records."""
    code = (getattr(user, 'referral_code', None) or '').strip().upper()
    if code:
        return code

    user.refresh_from_db(fields=['referral_code'])
    code = (getattr(user, 'referral_code', None) or '').strip().upper()
    if code:
        return code

    from users.signals import generate_unique_referral_code

    code = generate_unique_referral_code()
    user.referral_code = code
    user.save(update_fields=['referral_code'])
    return code


def verification_code(user) -> str:
    """Per-user token embedded in the X post. This now reuses the referral code."""
    return _ensure_referral_code(user)


def portal_referral_base_url() -> str:
    base_url = getattr(settings, 'PORTAL_REFERRAL_BASE_URL', PORTAL_REFERRAL_BASE_URL).strip().rstrip('/')
    if not base_url:
        base_url = PORTAL_REFERRAL_BASE_URL
    return base_url


def portal_referral_url(code: str) -> str:
    base_url = portal_referral_base_url()
    return f'{base_url}/?ref={quote(code)}'


def post_has_referral_url(full_text: str, user) -> bool:
    expected_code = verification_code(user).lower()
    expected_host = urlparse(portal_referral_base_url()).netloc.lower()

    for raw_url in URL_RE.findall(full_text or ''):
        candidate = raw_url.rstrip(TRAILING_URL_PUNCTUATION)
        parsed = urlparse(candidate)
        if parsed.netloc.lower() != expected_host:
            continue
        ref_values = parse_qs(parsed.query).get('ref', [])
        if any(value.strip().lower() == expected_code for value in ref_values):
            return True
    return False


def post_text_options(user) -> list[dict]:
    code = verification_code(user)
    mention = f'@{genlayer_mention()}'
    referral_url = portal_referral_url(code)
    templates = [
        f'Becoming part of the {mention} community of builders, validators, and creators. {referral_url}',
        f'Officially part of the {mention} community builders, validators, and creators. {referral_url}',
        f"Convincing {mention} I'm not a bot to join their community of builders, validators, and creators. {referral_url}",
    ]
    return [
        {
            'id': f'community-post-{index}',
            'text': text,
            'intent_url': f'https://x.com/intent/post?text={quote(text)}',
        }
        for index, text in enumerate(templates, start=1)
    ]


def share_text(user) -> str:
    return post_text_options(user)[0]['text']


def intent_url(user) -> str:
    return post_text_options(user)[0]['intent_url']


def parse_x_post(url: str):
    """Return (handle_lower, tweet_id) for a well-formed X post URL, else (None, None)."""
    match = X_POST_RE.match((url or '').strip())
    if not match:
        return None, None
    return match.group('handle').lower(), match.group('id')


def post_matches(full_text: str, user):
    """Whether the tweet text contains the user's referral URL and @mentions GenLayer.
    Returns (ok, error_code)."""
    text = (full_text or '').lower()
    if not post_has_referral_url(full_text, user):
        return False, 'code_missing'
    handle_re = re.compile(rf'(^|[^a-z0-9_])@{re.escape(genlayer_handle())}(?![a-z0-9_])')
    if not handle_re.search(text):
        return False, 'tag_missing'
    return True, None


def _has_contribution(user, slug) -> bool:
    from contributions.models import Contribution
    return Contribution.objects.filter(user=user, contribution_type__slug=slug).exists()


def _contribution_points(user, slug):
    """Current reward, or the user's awarded snapshot once completed."""
    from contributions.models import Contribution, ContributionType

    contribution = (
        Contribution.objects
        .filter(user=user, contribution_type__slug=slug)
        .order_by('-created_at')
        .first()
    )
    if contribution:
        return contribution.points

    contribution_type = ContributionType.objects.filter(slug=slug).first()
    if contribution_type is None:
        return None
    return contribution_type.min_points


def _has_task_completion(user, slug) -> bool:
    from social_tasks.models import SocialTaskCompletion
    return SocialTaskCompletion.objects.filter(user=user, task__slug=slug).exists()


def _task_points(user, slug):
    """Current task reward, or the user's awarded snapshot once completed."""
    from social_tasks.models import SocialTask, SocialTaskCompletion

    completion = (
        SocialTaskCompletion.objects
        .filter(user=user, task__slug=slug)
        .select_related('task')
        .order_by('-completed_at')
        .first()
    )
    if completion:
        return completion.points_awarded

    task = SocialTask.objects.filter(slug=slug).first()
    if task is None:
        return None
    return task.points


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
    # Existing creators are grandfathered in: the Creator role means the
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
            'link_x': {
                'done': states['link_x'],
                'points': _contribution_points(user, LINK_X_SLUG),
            },
            'link_discord': {
                'done': states['link_discord'],
                'points': _contribution_points(user, LINK_DISCORD_SLUG),
            },
            'follow_x': {
                'done': states['follow_x'],
                'points': _task_points(user, FOLLOW_TASK_SLUG),
            },
            'join_discord': {
                'done': states['join_discord'],
                'points': _task_points(user, JOIN_DISCORD_TASK_SLUG),
            },
            'x_post': {
                'done': states['x_post'],
                'verification_code': verification_code(user),
                'share_text': share_text(user),
                'intent_url': intent_url(user),
                'post_options': post_text_options(user),
                'post_url': proof.post_url if proof else None,
            },
        },
        'missing_steps': missing_steps,
        'complete': is_creator or (started and not missing_steps),
        'is_member': is_creator,
    }
