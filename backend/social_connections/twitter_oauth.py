"""Twitter/X OAuth views — thin wrappers around TwitterOAuthService."""

from urllib.parse import quote, urlencode

from django.conf import settings
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from tally.middleware.logging_utils import get_app_logger

from .oauth_service import TwitterOAuthService, validate_redirect_url

logger = get_app_logger('twitter_oauth')
service = TwitterOAuthService()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def twitter_oauth_initiate(request):
    """Initiate Twitter OAuth 2.0 flow with PKCE — full-page redirect, not popup."""
    code_verifier = service.generate_code_verifier()
    code_challenge = service.generate_code_challenge(code_verifier)

    # Store the redirect URL so callback can send the user back to the frontend
    redirect_url = validate_redirect_url(request.GET.get('redirect', settings.FRONTEND_URL))

    # Store code_verifier and redirect_url in session to keep the state token small.
    # Twitter has URL length limits and a large state token causes invalid_request errors.
    request.session['twitter_oauth_code_verifier'] = code_verifier
    request.session['twitter_oauth_redirect_url'] = redirect_url

    state = service.generate_state(request.user.id)
    if len(state) > 500:
        logger.error("Twitter OAuth state exceeded X's 500 character limit")
        return Response({'detail': 'Unable to initiate Twitter OAuth'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    params = {
        'response_type': 'code',
        'client_id': service.get_client_id(),
        'redirect_uri': service.get_redirect_uri(),
        'scope': ' '.join(service.scopes),
        'state': state,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
    }

    return redirect(f"{service.authorize_url}?{urlencode(params, quote_via=quote)}")


@csrf_exempt
def twitter_oauth_callback(request):
    """Handle Twitter OAuth callback.
    Recovers code_verifier and redirect_url from the session and passes
    them to the shared callback handler."""
    session = getattr(request, 'session', None)
    # Recover code_verifier and redirect_url from session (stored during initiate)
    code_verifier = session.pop('twitter_oauth_code_verifier', '') if session else ''
    redirect_url = session.pop('twitter_oauth_redirect_url', '') if session else ''
    logger.info(
        "Twitter OAuth callback session data: has_session=%s has_code_verifier=%s has_redirect_url=%s code_present=%s error_present=%s",
        bool(session),
        bool(code_verifier),
        bool(redirect_url),
        bool(request.GET.get('code')),
        bool(request.GET.get('error')),
    )
    if request.GET.get('code') and not request.GET.get('error') and not code_verifier:
        logger.warning("Twitter OAuth callback missing session-backed code_verifier during token exchange")
    return service.handle_callback(request, session_data={
        'code_verifier': code_verifier,
        'redirect_url': redirect_url,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disconnect_twitter(request):
    """Disconnect Twitter account."""
    from .models import TwitterConnection
    try:
        connection = TwitterConnection.objects.get(user=request.user)
        connection.delete()
        logger.debug("Twitter connection deleted")
    except TwitterConnection.DoesNotExist:
        pass

    return Response({'message': 'Twitter account disconnected successfully'}, status=status.HTTP_200_OK)
