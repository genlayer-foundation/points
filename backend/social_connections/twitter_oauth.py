"""Twitter/X OAuth views — thin wrappers around TwitterOAuthService."""

from urllib.parse import quote, urlencode

import requests
from django.conf import settings
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from tally.middleware.logging_utils import get_app_logger

from .serializers import TwitterConnectionSerializer
from .oauth_service import TwitterOAuthService

logger = get_app_logger('twitter_oauth')
service = TwitterOAuthService()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def twitter_oauth_initiate(request):
    """Initiate Twitter OAuth 2.0 flow with PKCE — full-page redirect, not popup."""
    code_verifier = service.generate_code_verifier()
    code_challenge = service.generate_code_challenge(code_verifier)

    redirect_url = request.GET.get('redirect', settings.FRONTEND_URL)

    # Pack code_verifier and redirect_url into the signed state token
    # (not sessions — sessions break on multi-instance deployments like App Runner).
    state = service.generate_state(request.user.id, extra_data={
        'code_verifier': code_verifier,
        'redirect_url': redirect_url,
    })
    if len(state) > 500:
        logger.error("Twitter OAuth state exceeded X's 500 character limit (len=%d)", len(state))
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
    """Handle Twitter OAuth callback."""
    return service.handle_callback(request)


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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refresh_twitter_username(request):
    """Refresh the linked X username from X's current user API."""
    from .models import TwitterConnection

    try:
        connection = request.user.twitterconnection
    except TwitterConnection.DoesNotExist:
        return Response({
            'error': 'X account not linked',
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        connection, changed = service.refresh_connection_username(connection)
    except ValueError as e:
        error_code = str(e)
        if error_code in (
            'missing_access_token',
            'invalid_access_token',
            'missing_refresh_token',
            'invalid_refresh_token',
            'refresh_not_supported',
            'no_access_token',
        ):
            return Response({
                'error': 'X authorization is no longer valid. Please reconnect X.',
                'code': error_code,
            }, status=status.HTTP_400_BAD_REQUEST)
        if error_code == 'account_mismatch':
            logger.warning(
                "X refresh returned a different account for user %s",
                request.user.id,
            )
            return Response({
                'error': 'X account mismatch. Please reconnect X.',
                'code': error_code,
            }, status=status.HTTP_409_CONFLICT)
        logger.error(f"Failed to refresh X username: {e}")
        return Response({
            'error': 'Failed to refresh X username',
        }, status=status.HTTP_400_BAD_REQUEST)
    except requests.RequestException as e:
        logger.error(f"X API request failed while refreshing username: {e}")
        return Response({
            'error': 'Failed to reach X. Please try again.',
        }, status=status.HTTP_502_BAD_GATEWAY)

    return Response({
        'message': 'X username refreshed successfully',
        'changed': changed,
        'twitter_connection': TwitterConnectionSerializer(connection).data,
    }, status=status.HTTP_200_OK)
