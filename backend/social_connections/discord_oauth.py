"""Discord OAuth views — thin wrappers around DiscordOAuthService."""

from urllib.parse import urlencode

import requests
from django.conf import settings
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from tally.middleware.logging_utils import get_app_logger

from .encryption import decrypt_token
from .oauth_service import DiscordOAuthService
from .serializers import DiscordConnectionSerializer

logger = get_app_logger('discord_oauth')
service = DiscordOAuthService()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def discord_oauth_initiate(request):
    """Initiate Discord OAuth 2.0 flow — full-page redirect."""
    redirect_url = request.GET.get('redirect', settings.FRONTEND_URL)

    state = service.generate_state(request.user.id, extra_data={
        'redirect_url': redirect_url,
    })

    params = {
        'response_type': 'code',
        'client_id': service.get_client_id(),
        'redirect_uri': service.get_redirect_uri(),
        'scope': ' '.join(service.scopes),
        'state': state,
    }

    return redirect(f"{service.authorize_url}?{urlencode(params)}")


@csrf_exempt
def discord_oauth_callback(request):
    """Handle Discord OAuth callback."""
    return service.handle_callback(request)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disconnect_discord(request):
    """Disconnect Discord account."""
    from .models import DiscordConnection
    try:
        connection = DiscordConnection.objects.get(user=request.user)
        connection.delete()
        logger.debug("Discord connection deleted")
    except DiscordConnection.DoesNotExist:
        pass

    return Response({'message': 'Discord account disconnected successfully'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refresh_discord_username(request):
    """Refresh the linked Discord username from Discord's current user API."""
    from .models import DiscordConnection

    try:
        connection = request.user.discordconnection
    except DiscordConnection.DoesNotExist:
        return Response({
            'error': 'Discord account not linked',
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
                'error': 'Discord authorization is no longer valid. Please reconnect Discord.',
                'code': error_code,
            }, status=status.HTTP_400_BAD_REQUEST)
        if error_code == 'account_mismatch':
            logger.warning(
                "Discord refresh returned a different account for user %s",
                request.user.id,
            )
            return Response({
                'error': 'Discord account mismatch. Please reconnect Discord.',
                'code': error_code,
            }, status=status.HTTP_409_CONFLICT)
        logger.error(f"Failed to refresh Discord username: {e}")
        return Response({
            'error': 'Failed to refresh Discord username',
        }, status=status.HTTP_400_BAD_REQUEST)
    except requests.RequestException as e:
        logger.error(f"Discord API request failed while refreshing username: {e}")
        return Response({
            'error': 'Failed to reach Discord. Please try again.',
        }, status=status.HTTP_502_BAD_GATEWAY)

    return Response({
        'message': 'Discord username refreshed successfully',
        'changed': changed,
        'discord_connection': DiscordConnectionSerializer(connection).data,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_discord_guild(request):
    """Check if user is a member of the configured Discord guild."""
    from .models import DiscordConnection
    from cryptography.fernet import InvalidToken
    from django.utils import timezone

    guild_id = getattr(settings, 'DISCORD_GUILD_ID', '')
    if not guild_id:
        return Response({
            'error': 'Discord guild not configured',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    try:
        connection = request.user.discordconnection
    except DiscordConnection.DoesNotExist:
        return Response({
            'is_member': False,
            'guild_id': guild_id,
            'error': 'Discord account not linked',
        }, status=status.HTTP_200_OK)

    if not connection.access_token:
        return Response({
            'is_member': False,
            'guild_id': guild_id,
            'error': 'No access token available',
        }, status=status.HTTP_200_OK)

    try:
        token = decrypt_token(connection.access_token)
    except InvalidToken:
        logger.warning("Failed to decrypt Discord token")
        return Response({
            'is_member': False,
            'guild_id': guild_id,
            'error': 'Discord authorization expired. Please reconnect your account.',
        }, status=status.HTTP_200_OK)

    is_member = service.check_guild_membership(token, guild_id)

    # Cache the result
    connection.guild_member = is_member
    connection.guild_checked_at = timezone.now()
    connection.save(update_fields=['guild_member', 'guild_checked_at'])

    return Response({
        'is_member': is_member,
        'guild_id': guild_id,
    }, status=status.HTTP_200_OK)
