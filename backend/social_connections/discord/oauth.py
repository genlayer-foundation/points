"""
Discord OAuth 2.0 authentication handling.
"""
import secrets
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

from cryptography.fernet import InvalidToken
from users.models import User
from social_connections.encryption import encrypt_token, decrypt_token
from social_connections.discord.models import DiscordConnection
from tally.middleware.logging_utils import get_app_logger
from tally.middleware.tracing import trace_external

logger = get_app_logger('discord_oauth')

# Cache to track used OAuth codes (prevents duplicate exchanges)
_used_oauth_codes = {}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def discord_oauth_initiate(request):
    """Initiate Discord OAuth 2.0 flow."""
    user_id = request.user.id
    logger.debug("Discord OAuth initiated")

    # Generate state token with user ID embedded
    state_data = {
        'user_id': user_id,
        'nonce': secrets.token_urlsafe(32)
    }

    # Sign the state data to make it tamper-proof
    state = signing.dumps(state_data, salt='discord_oauth_state')
    logger.debug("Generated signed OAuth state")

    # Build Discord OAuth URL
    discord_oauth_url = "https://discord.com/api/oauth2/authorize"
    params = {
        'response_type': 'code',
        'client_id': settings.DISCORD_CLIENT_ID,
        'redirect_uri': settings.DISCORD_REDIRECT_URI,
        'scope': 'identify guilds',
        'state': state
    }

    auth_url = f"{discord_oauth_url}?{urlencode(params)}"
    return redirect(auth_url)


@csrf_exempt
def discord_oauth_callback(request):
    """Handle Discord OAuth callback."""
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')
    error_description = request.GET.get('error_description')

    logger.debug("Discord OAuth callback received")

    template_context = {
        'platform': 'discord',
        'frontend_origin': settings.FRONTEND_URL
    }

    # Handle errors from Discord
    if error:
        logger.error(f"Discord OAuth error: {error} - {error_description}")
        return render(request, 'social_connections/oauth_callback.html', {
            **template_context,
            'success': False,
            'error': 'authorization_failed',
            'message': 'Authorization failed. This window will close automatically.',
        })

    # Validate state token
    if not state:
        logger.error("No state token received from Discord")
        return render(request, 'social_connections/oauth_callback.html', {
            **template_context,
            'success': False,
            'error': 'invalid_state',
            'message': 'Invalid state token. This window will close automatically.',
        })

    try:
        state_data = signing.loads(state, salt='discord_oauth_state', max_age=600)
        user_id = state_data.get('user_id')
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
    token_url = "https://discord.com/api/oauth2/token"

    token_params = {
        'client_id': settings.DISCORD_CLIENT_ID,
        'client_secret': settings.DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.DISCORD_REDIRECT_URI
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        with trace_external('discord', 'token_exchange'):
            token_response = requests.post(token_url, data=token_params, headers=headers)
            token_data = token_response.json()

        if token_response.status_code != 200 or 'error' in token_data:
            error_msg = token_data.get('error_description', token_data.get('error', 'Unknown error'))
            logger.error(f"Discord token exchange error: {error_msg}")
            return render(request, 'social_connections/oauth_callback.html', {
                **template_context,
                'success': False,
                'error': 'token_exchange_failed',
                'message': 'Failed to exchange token. This window will close automatically.',
            })

        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token', '')

        if not access_token:
            logger.error("No access token received from Discord")
            return render(request, 'social_connections/oauth_callback.html', {
                **template_context,
                'success': False,
                'error': 'no_access_token',
                'message': 'No access token received. This window will close automatically.',
            })

        # Fetch Discord user data
        user_url = "https://discord.com/api/v10/users/@me"
        user_headers = {
            'Authorization': f'Bearer {access_token}',
        }

        with trace_external('discord', 'get_user'):
            user_response = requests.get(user_url, headers=user_headers)
            user_response.raise_for_status()
            discord_user = user_response.json()

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

        # Check if this Discord account is already linked to another user
        existing_connection = DiscordConnection.objects.filter(
            platform_user_id=discord_user.get('id')
        ).exclude(user=user).first()

        if existing_connection:
            logger.warning("Discord account already linked to another user")
            return render(request, 'social_connections/oauth_callback.html', {
                **template_context,
                'success': False,
                'error': 'already_linked',
                'message': 'Discord account already linked. This window will close automatically.',
            })

        # Create or update DiscordConnection
        connection, created = DiscordConnection.objects.update_or_create(
            user=user,
            defaults={
                'username': discord_user.get('username', ''),
                'platform_user_id': discord_user.get('id', ''),
                'discriminator': discord_user.get('discriminator', '0'),
                'avatar_hash': discord_user.get('avatar', ''),
                'access_token': encrypt_token(access_token),
                'refresh_token': encrypt_token(refresh_token) if refresh_token else '',
                'linked_at': timezone.now()
            }
        )

        logger.debug("Discord account linked successfully")
        return render(request, 'social_connections/oauth_callback.html', {
            **template_context,
            'success': True,
            'error': '',
            'message': 'Discord account linked successfully! This window will close automatically.',
        })

    except requests.RequestException as e:
        logger.error(f"Discord API request failed: {e}")
        return render(request, 'social_connections/oauth_callback.html', {
            **template_context,
            'success': False,
            'error': 'api_request_failed',
            'message': 'API request failed. This window will close automatically.',
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disconnect_discord(request):
    """Disconnect Discord account from user profile."""
    try:
        user = request.user
        try:
            connection = user.discord_connection
            connection.delete()
            logger.debug("Discord connection deleted")
        except DiscordConnection.DoesNotExist:
            pass

        return Response({
            'message': 'Discord account disconnected successfully'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Failed to disconnect Discord: {e}")
        return Response({
            'error': 'Failed to disconnect Discord account'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_guild_membership(request):
    """Check if user is a member of the configured Discord guild/server."""
    user = request.user

    # Check if guild ID is configured
    guild_id = getattr(settings, 'DISCORD_GUILD_ID', '')
    if not guild_id:
        return Response({
            'is_member': False,
            'error': 'Discord guild not configured'
        }, status=status.HTTP_200_OK)

    # Try to get Discord connection
    try:
        connection = user.discord_connection
    except DiscordConnection.DoesNotExist:
        return Response({
            'is_member': False,
            'guild_id': guild_id,
            'error': 'Discord account not linked'
        }, status=status.HTTP_200_OK)

    if not connection.access_token:
        return Response({
            'is_member': False,
            'guild_id': guild_id,
            'error': 'Discord access token missing'
        }, status=status.HTTP_200_OK)

    try:
        token = decrypt_token(connection.access_token)
    except InvalidToken:
        logger.warning("Failed to decrypt Discord token")
        connection.access_token = ''
        connection.save()
        return Response({
            'is_member': False,
            'guild_id': guild_id,
            'error': 'Discord token invalid'
        }, status=status.HTTP_200_OK)

    try:
        # Fetch user's guilds
        guilds_url = "https://discord.com/api/v10/users/@me/guilds"
        headers = {
            'Authorization': f'Bearer {token}',
        }

        with trace_external('discord', 'get_guilds'):
            response = requests.get(guilds_url, headers=headers)

        if response.status_code == 401:
            # Token expired or revoked
            logger.warning("Discord token expired or revoked")
            return Response({
                'is_member': False,
                'guild_id': guild_id,
                'error': 'Discord authorization expired. Please reconnect your account.'
            }, status=status.HTTP_200_OK)

        response.raise_for_status()
        guilds = response.json()

        # Check if user is in the configured guild
        is_member = any(g.get('id') == guild_id for g in guilds)

        return Response({
            'is_member': is_member,
            'guild_id': guild_id,
            'discord_username': connection.username
        }, status=status.HTTP_200_OK)

    except requests.RequestException as e:
        logger.error(f"Failed to check guild membership: {e}")
        return Response({
            'is_member': False,
            'guild_id': guild_id,
            'error': 'Failed to check guild membership'
        }, status=status.HTTP_200_OK)
