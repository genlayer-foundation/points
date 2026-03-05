"""
Twitter/X OAuth 2.0 authentication handling with PKCE.
"""
import secrets
import hashlib
import base64
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.core import signing
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from users.models import User
from social_connections.encryption import encrypt_token
from social_connections.twitter.models import TwitterConnection
from tally.middleware.logging_utils import get_app_logger
from tally.middleware.tracing import trace_external

logger = get_app_logger('twitter_oauth')

# Cache to track used OAuth codes (prevents duplicate exchanges)
_used_oauth_codes = {}


def generate_code_verifier():
    """Generate a cryptographically random code verifier for PKCE."""
    return secrets.token_urlsafe(64)[:128]  # Max 128 chars per spec


def generate_code_challenge(verifier):
    """Generate code challenge from verifier using S256 method."""
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip('=')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def twitter_oauth_initiate(request):
    """Initiate Twitter OAuth 2.0 flow with PKCE."""
    user_id = request.user.id
    logger.debug("Twitter OAuth initiated")

    # Generate PKCE code verifier and challenge
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)

    # Generate state token with user ID and code_verifier embedded
    state_data = {
        'user_id': user_id,
        'code_verifier': code_verifier,
        'nonce': secrets.token_urlsafe(32)
    }

    # Sign the state data to make it tamper-proof
    state = signing.dumps(state_data, salt='twitter_oauth_state')
    logger.debug("Generated signed OAuth state with PKCE")

    # Build Twitter OAuth URL
    twitter_oauth_url = "https://twitter.com/i/oauth2/authorize"
    params = {
        'response_type': 'code',
        'client_id': settings.TWITTER_CLIENT_ID,
        'redirect_uri': settings.TWITTER_REDIRECT_URI,
        'scope': 'tweet.read users.read offline.access',
        'state': state,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256'
    }

    auth_url = f"{twitter_oauth_url}?{urlencode(params)}"
    return redirect(auth_url)


@csrf_exempt
def twitter_oauth_callback(request):
    """Handle Twitter OAuth callback."""
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')
    error_description = request.GET.get('error_description')

    logger.debug("Twitter OAuth callback received")

    template_context = {
        'platform': 'twitter',
        'frontend_origin': settings.FRONTEND_URL
    }

    # Handle errors from Twitter
    if error:
        logger.error(f"Twitter OAuth error: {error} - {error_description}")
        return render(request, 'social_connections/oauth_callback.html', {
            **template_context,
            'success': False,
            'error': 'authorization_failed',
            'message': 'Authorization failed. This window will close automatically.',
        })

    # Validate state token
    if not state:
        logger.error("No state token received from Twitter")
        return render(request, 'social_connections/oauth_callback.html', {
            **template_context,
            'success': False,
            'error': 'invalid_state',
            'message': 'Invalid state token. This window will close automatically.',
        })

    try:
        state_data = signing.loads(state, salt='twitter_oauth_state', max_age=600)
        user_id = state_data.get('user_id')
        code_verifier = state_data.get('code_verifier')
        logger.debug("Successfully validated signed OAuth state")
    except signing.SignatureExpired:
        logger.error("OAuth state token has expired")
        return render(request, 'social_connections/oauth_callback.html', {
            **template_context,
            'success': False,
            'error': 'state_expired',
            'message': 'Session expired. This window will close automatically.',
        })
    except signing.BadSignature:
        logger.error("OAuth state token has invalid signature")
        return render(request, 'social_connections/oauth_callback.html', {
            **template_context,
            'success': False,
            'error': 'invalid_state',
            'message': 'Invalid state token. This window will close automatically.',
        })

    # Clean up old codes (older than 10 minutes)
    cutoff = timezone.now() - timezone.timedelta(minutes=10)
    expired_codes = [k for k, v in _used_oauth_codes.items() if v <= cutoff]
    for expired_code in expired_codes:
        del _used_oauth_codes[expired_code]

    # Check if this code has already been used
    if code in _used_oauth_codes:
        logger.warning("OAuth code already used, rejecting duplicate request")
        return render(request, 'social_connections/oauth_callback.html', {
            **template_context,
            'success': False,
            'error': 'code_already_used',
            'message': 'This code has already been used. This window will close automatically.',
        })

    # Mark code as used immediately
    _used_oauth_codes[code] = timezone.now()

    # Exchange code for access token
    logger.debug("Attempting to exchange OAuth code for access token")
    token_url = "https://api.twitter.com/2/oauth2/token"

    # Twitter requires Basic auth for confidential clients
    auth = (settings.TWITTER_CLIENT_ID, settings.TWITTER_CLIENT_SECRET)

    token_params = {
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': settings.TWITTER_REDIRECT_URI,
        'code_verifier': code_verifier
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        with trace_external('twitter', 'token_exchange'):
            token_response = requests.post(
                token_url,
                data=token_params,
                headers=headers,
                auth=auth
            )
            token_data = token_response.json()

        if token_response.status_code != 200 or 'error' in token_data:
            error_msg = token_data.get('error_description', token_data.get('error', 'Unknown error'))
            logger.error(f"Twitter token exchange error: {error_msg}")
            return render(request, 'social_connections/oauth_callback.html', {
                **template_context,
                'success': False,
                'error': 'token_exchange_failed',
                'message': 'Failed to exchange token. This window will close automatically.',
            })

        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token', '')

        if not access_token:
            logger.error("No access token received from Twitter")
            return render(request, 'social_connections/oauth_callback.html', {
                **template_context,
                'success': False,
                'error': 'no_access_token',
                'message': 'No access token received. This window will close automatically.',
            })

        # Fetch Twitter user data
        user_url = "https://api.twitter.com/2/users/me"
        user_headers = {
            'Authorization': f'Bearer {access_token}',
        }

        with trace_external('twitter', 'get_user'):
            user_response = requests.get(user_url, headers=user_headers)
            user_response.raise_for_status()
            twitter_data = user_response.json()

        twitter_user = twitter_data.get('data', {})

        # Get user from state token
        if not user_id:
            logger.error("No user_id in state token")
            return render(request, 'social_connections/oauth_callback.html', {
                **template_context,
                'success': False,
                'error': 'invalid_state',
                'message': 'Invalid authentication state. This window will close automatically.',
            })

        try:
            user = User.objects.get(id=user_id)
            logger.debug("Found user from state token")
        except User.DoesNotExist:
            logger.error("User from state not found")
            return render(request, 'social_connections/oauth_callback.html', {
                **template_context,
                'success': False,
                'error': 'user_not_found',
                'message': 'User not found. This window will close automatically.',
            })

        # Check if this Twitter account is already linked to another user
        existing_connection = TwitterConnection.objects.filter(
            platform_user_id=twitter_user.get('id')
        ).exclude(user=user).first()

        if existing_connection:
            logger.warning("Twitter account already linked to another user")
            return render(request, 'social_connections/oauth_callback.html', {
                **template_context,
                'success': False,
                'error': 'already_linked',
                'message': 'Twitter account already linked. This window will close automatically.',
            })

        # Create or update TwitterConnection
        connection, created = TwitterConnection.objects.update_or_create(
            user=user,
            defaults={
                'username': twitter_user.get('username', ''),
                'platform_user_id': twitter_user.get('id', ''),
                'access_token': encrypt_token(access_token),
                'refresh_token': encrypt_token(refresh_token) if refresh_token else '',
                'linked_at': timezone.now()
            }
        )

        logger.debug("Twitter account linked successfully")
        return render(request, 'social_connections/oauth_callback.html', {
            **template_context,
            'success': True,
            'error': '',
            'message': 'Twitter account linked successfully! This window will close automatically.',
        })

    except requests.RequestException as e:
        logger.error(f"Twitter API request failed: {e}")
        return render(request, 'social_connections/oauth_callback.html', {
            **template_context,
            'success': False,
            'error': 'api_request_failed',
            'message': 'API request failed. This window will close automatically.',
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disconnect_twitter(request):
    """Disconnect Twitter account from user profile."""
    try:
        user = request.user
        try:
            connection = user.twitter_connection
            connection.delete()
            logger.debug("Twitter connection deleted")
        except TwitterConnection.DoesNotExist:
            pass

        return Response({
            'message': 'Twitter account disconnected successfully'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Failed to disconnect Twitter: {e}")
        return Response({
            'error': 'Failed to disconnect Twitter account'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
