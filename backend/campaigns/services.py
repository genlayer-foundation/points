import logging
from datetime import timedelta
from urllib.parse import urlencode, urlparse

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import (
    CLICK_ID_FORWARD_PARAMS,
    MAX_DESTINATION_LENGTH,
    ROLE_SEGMENT_TO_ROLE,
    CampaignLink,
    CampaignRedirectHit,
    UserAcquisitionAttribution,
)

logger = logging.getLogger(__name__)

# ponytail: substring UA classification, swap for a UA-parser dependency only
# if the bot split ever proves too coarse.
BOT_UA_SUBSTRINGS = (
    'bot',
    'crawler',
    'spider',
    'slurp',
    'preview',
    'facebookexternalhit',
    'whatsapp',
    'embedly',
    'curl',
    'wget',
    'python-requests',
    'httpclient',
    'headless',
    'lighthouse',
    'scanner',
)
_BROWSER_FAMILIES = (
    ('edg', 'edge'),
    ('opr', 'opera'),
    ('firefox', 'firefox'),
    ('chrome', 'chrome'),
    ('safari', 'safari'),
)
_MAX_FORWARDED_CLICK_ID_LENGTH = 100


def classify_user_agent(user_agent):
    """Return (family, device_category, is_probable_bot) from a raw UA string."""
    ua = (user_agent or '').lower()
    if not ua:
        return ('', CampaignRedirectHit.DEVICE_UNKNOWN, True)
    for marker in BOT_UA_SUBSTRINGS:
        if marker in ua:
            return (marker[:32], CampaignRedirectHit.DEVICE_BOT, True)
    if 'ipad' in ua or 'tablet' in ua:
        device = CampaignRedirectHit.DEVICE_TABLET
    elif 'mobi' in ua or 'android' in ua:
        device = CampaignRedirectHit.DEVICE_MOBILE
    else:
        device = CampaignRedirectHit.DEVICE_DESKTOP
    family = 'other'
    for marker, name in _BROWSER_FAMILIES:
        if marker in ua:
            family = name
            break
    return (family, device, False)


def resolve_campaign_link(role_segment, alias):
    role = ROLE_SEGMENT_TO_ROLE.get((role_segment or '').lower())
    if not role:
        return None
    return (
        CampaignLink.objects.select_related('campaign')
        .filter(role=role, alias=(alias or '').lower())
        .first()
    )


def record_redirect_hit(link, request):
    """Best effort: a failed hit insert must never block the redirect."""
    try:
        referrer_host = ''
        referer = request.META.get('HTTP_REFERER', '')
        if referer:
            referrer_host = (urlparse(referer).hostname or '')[:100]
        family, device, is_bot = classify_user_agent(request.META.get('HTTP_USER_AGENT', ''))
        CampaignRedirectHit.objects.create(
            campaign_link=link,
            referrer_host=referrer_host,
            user_agent_family=family,
            device_category=device,
            is_probable_bot=is_bot,
        )
    except Exception:
        logger.warning('Campaign redirect hit logging failed for link %s', link.pk, exc_info=True)


def build_redirect_url(link, request):
    """Stored destination + stored UTMs, plus allowlisted ad click IDs
    forwarded from the incoming request (nothing else is ever forwarded)."""
    url = link.redirect_target
    forwarded = {
        key: request.GET[key][:_MAX_FORWARDED_CLICK_ID_LENGTH]
        for key in CLICK_ID_FORWARD_PARAMS
        if request.GET.get(key)
    }
    if forwarded:
        url = f'{url}&{urlencode(forwarded)}'
    return url


def _clear_pending_attribution_fields(pending):
    pending.acquisition_campaign_link = None
    pending.acquisition_snapshot = {}
    pending.acquisition_captured_at = None


_ATTRIBUTION_UPDATE_FIELDS = [
    'acquisition_campaign_link', 'acquisition_snapshot', 'acquisition_captured_at', 'updated_at',
]


def apply_pending_attribution(pending, payload, reset=False):
    """Write first-touch campaign attribution onto a pending wallet signup.

    Defensive by design: unknown or expired IDs and malformed payloads are
    ignored silently, never surfaced as errors (attribution must never make
    signup fail). The snapshot is built ONLY from the resolved link and its
    campaign, never from browser-supplied UTM text.
    """
    if reset and pending.acquisition_captured_at:
        # The pending row is being reused after expiry; stale acquisition data
        # must not leak into the new signup attempt.
        _clear_pending_attribution_fields(pending)
        pending.save(update_fields=_ATTRIBUTION_UPDATE_FIELDS)
    if pending.acquisition_captured_at:
        return  # first touch wins
    if not isinstance(payload, dict):
        return
    utm_id = payload.get('utm_id')
    if not isinstance(utm_id, str) or not utm_id or len(utm_id) > 64:
        return
    captured_raw = payload.get('captured_at')
    captured_dt = parse_datetime(captured_raw) if isinstance(captured_raw, str) else None
    if captured_dt is None or timezone.is_naive(captured_dt):
        return
    now = timezone.now()
    window = timedelta(days=settings.CAMPAIGN_ATTRIBUTION_WINDOW_DAYS)
    if captured_dt > now + timedelta(minutes=5) or captured_dt < now - window:
        return
    landing_path = payload.get('landing_path')
    if (
        not isinstance(landing_path, str)
        or not landing_path.startswith('/')
        or len(landing_path) > MAX_DESTINATION_LENGTH
    ):
        landing_path = ''
    else:
        landing_path = landing_path.split('?')[0].split('#')[0]
    link = CampaignLink.objects.select_related('campaign').filter(tracking_id=utm_id).first()
    if link is None or not link.is_live_at(captured_dt):
        return
    pending.acquisition_campaign_link = link
    pending.acquisition_snapshot = {
        'link_tracking_id': link.tracking_id,
        'campaign_key': link.campaign.tracking_key,
        'source': link.utm_source,
        'medium': link.utm_medium,
        'content': link.utm_content,
        'term': link.utm_term,
        'link_role': link.role,
        'landing_path': landing_path,
        'captured_at': captured_dt.isoformat(),
    }
    pending.acquisition_captured_at = captured_dt
    pending.save(update_fields=_ATTRIBUTION_UPDATE_FIELDS)


def record_user_acquisition(user, pending_signup):
    """Copy pending-signup attribution into the write-once acquisition record.

    Called inside the signup transaction so the record commits atomically with
    the new User. The nested atomic() creates a savepoint: a failure here rolls
    back only this insert and never aborts user creation (a bare try/except
    would poison the outer Postgres transaction).
    """
    if pending_signup is None or not pending_signup.acquisition_captured_at:
        return
    try:
        with transaction.atomic():
            if UserAcquisitionAttribution.objects.filter(user=user).exists():
                return
            snapshot = pending_signup.acquisition_snapshot or {}

            def _text(key, max_length):
                value = snapshot.get(key)
                return value[:max_length] if isinstance(value, str) else ''

            UserAcquisitionAttribution.objects.create(
                user=user,
                campaign_link=pending_signup.acquisition_campaign_link,
                link_tracking_id=_text('link_tracking_id', 20),
                campaign_key=_text('campaign_key', 64),
                source=_text('source', 64),
                medium=_text('medium', 64),
                content=_text('content', 64),
                term=_text('term', 64),
                link_role=_text('link_role', 16),
                landing_path=_text('landing_path', MAX_DESTINATION_LENGTH),
                captured_at=pending_signup.acquisition_captured_at,
                registered_at=timezone.now(),
            )
    except Exception:
        logger.exception('Failed to record acquisition attribution for user %s', user.pk)


def campaign_report(campaign):
    """Campaign funnel numbers from durable portal records, for the admin
    change page (and, later, the internal dashboard staff API).

    All user-level numbers are distinct users reaching their first qualifying
    outcome, never event counts. Source: Portal DB only; GA remains the
    session/multi-touch layer.
    """
    from contributions.models import Contribution, SubmittedContribution
    from ethereum_auth.models import PendingWalletSignup
    from social_tasks.models import SocialTaskCompletion

    hit_counts = CampaignRedirectHit.objects.filter(campaign_link__campaign=campaign).aggregate(
        human=Count('id', filter=Q(is_probable_bot=False)),
        bot=Count('id', filter=Q(is_probable_bot=True)),
    )
    wallet_connects = PendingWalletSignup.objects.filter(
        acquisition_campaign_link__campaign=campaign,
    ).count()
    # Filter on the snapshot key so acquisitions survive link deletion.
    user_ids = list(
        UserAcquisitionAttribution.objects.filter(
            Q(campaign_link__campaign=campaign) | Q(campaign_key=campaign.tracking_key)
        ).values_list('user_id', flat=True).distinct()
    )
    return {
        'source': 'portal_db',
        'redirect_hits_human': hit_counts['human'] or 0,
        'redirect_hits_bot': hit_counts['bot'] or 0,
        'wallet_connects': wallet_connects,
        'signups': len(user_ids),
        'activations': {
            'builder': SubmittedContribution.objects.filter(
                user_id__in=user_ids, contribution_type__category__slug='builder',
            ).values('user_id').distinct().count(),
            'validator': Contribution.objects.filter(
                user_id__in=user_ids, contribution_type__slug='validator-waitlist',
            ).values('user_id').distinct().count(),
            'community': SocialTaskCompletion.objects.filter(
                user_id__in=user_ids, task__counts_as_activation=True,
            ).values('user_id').distinct().count(),
        },
    }
