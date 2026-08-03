import logging

from django.http import HttpResponseGone, HttpResponseNotFound, HttpResponseRedirect
from django.utils import timezone
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny

from utils.throttling import CampaignRedirectRateThrottle

from .models import validate_destination_path
from .services import build_redirect_url, record_redirect_hit, resolve_campaign_link

logger = logging.getLogger(__name__)


@api_view(['GET', 'HEAD'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([CampaignRedirectRateThrottle])
def campaign_redirect(request, role, alias):
    """Resolve a vanity link (/join/<role>/<alias>, reverse-proxied here by
    Amplify) into a 302 to the stored portal destination with server-built
    UTMs. 302 + no-store on purpose: campaign destinations and status can
    change, so nothing may cache the redirect.
    """
    link = resolve_campaign_link(role, alias)
    if link is None:
        return HttpResponseNotFound()
    now = timezone.now()
    if link.is_expired_at(now):
        return HttpResponseGone()
    if not link.is_live_at(now):
        return HttpResponseNotFound()
    try:
        validate_destination_path(link.destination_path)
    except Exception:
        logger.error('Campaign link %s has an invalid stored destination; failing closed', link.pk)
        return HttpResponseNotFound()
    record_redirect_hit(link, request)
    response = HttpResponseRedirect(build_redirect_url(link, request))
    response['Cache-Control'] = 'no-store'
    return response
