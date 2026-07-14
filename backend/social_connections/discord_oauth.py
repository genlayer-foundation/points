"""Discord OAuth views — thin wrappers around DiscordOAuthService."""

import threading
import time
import uuid
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.db import IntegrityError, transaction
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.decorators import authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from validators.permissions import IsCronToken

from tally.middleware.logging_utils import get_app_logger

from .encryption import decrypt_token
from .discord_roles import (
    DiscordRoleSyncConfigurationError,
    DiscordRoleSyncError,
    DiscordRoleSyncService,
    DiscordRoleSyncUnavailable,
    manual_refresh_next_allowed_at,
)
from .models import DiscordRoleSyncLock
from .oauth_service import DiscordOAuthService
from .serializers import DiscordConnectionSerializer
from users.serializers import UserSerializer

logger = get_app_logger('discord_oauth')
service = DiscordOAuthService()

DISCORD_ROLE_SYNC_LOCK_NAME = 'discord_role_sync'
DISCORD_EARNED_ROLE_LOCK_NAME = 'discord_earned_role_assign'
DISCORD_ROLE_SYNC_LOCK_STALE_AFTER_SECONDS = 1800
DISCORD_ROLE_SYNC_HEARTBEAT_INTERVAL_SECONDS = 60


def _ensure_role_sync_lock_row(name=DISCORD_ROLE_SYNC_LOCK_NAME):
    try:
        DiscordRoleSyncLock.objects.get_or_create(name=name)
    except IntegrityError:
        pass


def _acquire_role_sync_lock(name=DISCORD_ROLE_SYNC_LOCK_NAME):
    _ensure_role_sync_lock_row(name)

    with transaction.atomic():
        now = timezone.now()
        lock_row = (
            DiscordRoleSyncLock.objects
            .select_for_update()
            .get(name=name)
        )

        is_running = (
            lock_row.owner_token is not None
            and lock_row.heartbeat_at is not None
            and (lock_row.released_at is None or lock_row.heartbeat_at > lock_row.released_at)
        )

        if is_running:
            secs = (now - lock_row.heartbeat_at).total_seconds()
            if secs <= DISCORD_ROLE_SYNC_LOCK_STALE_AFTER_SECONDS:
                return None, secs
            logger.warning("Stale Discord role sync lock detected after %ss", f"{secs:.0f}")

        lock_token = uuid.uuid4().hex
        lock_row.owner_token = lock_token
        lock_row.acquired_at = now
        lock_row.heartbeat_at = now
        lock_row.released_at = None
        lock_row.save(update_fields=['owner_token', 'acquired_at', 'heartbeat_at', 'released_at'])

    return lock_token, None


def _refresh_role_sync_lock(lock_token, name=DISCORD_ROLE_SYNC_LOCK_NAME):
    return bool(
        DiscordRoleSyncLock.objects.filter(
            name=name,
            owner_token=lock_token,
        ).update(heartbeat_at=timezone.now())
    )


def _release_role_sync_lock(lock_token, name=DISCORD_ROLE_SYNC_LOCK_NAME):
    now = timezone.now()
    DiscordRoleSyncLock.objects.filter(
        name=name,
        owner_token=lock_token,
    ).update(owner_token=None, heartbeat_at=now, released_at=now)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def discord_oauth_initiate(request):
    """Initiate Discord OAuth 2.0 flow — full-page redirect."""
    redirect_url = request.GET.get('redirect', settings.FRONTEND_URL)

    state = service.create_pending_state(
        request.user,
        redirect_url=redirect_url,
        request=request,
    )

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

    if getattr(settings, 'DISCORD_BOT_TOKEN', ''):
        try:
            result = DiscordRoleSyncService().sync_member_roles(connection)
        except DiscordRoleSyncConfigurationError as e:
            logger.warning("Discord role sync is not configured for guild check: %s", e)
        except DiscordRoleSyncUnavailable as e:
            logger.warning("Discord API unavailable during guild check: %s", e)
            return Response({
                'is_member': bool(connection.guild_member),
                'guild_id': guild_id,
                'discord_connection': DiscordConnectionSerializer(connection).data,
                'error': 'Failed to refresh Discord guild membership',
            }, status=status.HTTP_502_BAD_GATEWAY)
        else:
            return Response({
                'is_member': result.is_member,
                'guild_id': guild_id,
                'discord_connection': DiscordConnectionSerializer(result.connection).data,
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
        'discord_connection': DiscordConnectionSerializer(connection).data,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_my_discord_roles(request):
    """Manually refresh the authenticated user's Discord roles."""
    from .models import DiscordConnection

    try:
        connection = request.user.discordconnection
    except DiscordConnection.DoesNotExist:
        return Response({
            'error': 'Discord account not linked',
        }, status=status.HTTP_400_BAD_REQUEST)

    now = timezone.now()
    next_allowed_at = manual_refresh_next_allowed_at(connection)
    if next_allowed_at and now < next_allowed_at:
        return Response({
            'message': 'Discord roles were refreshed recently.',
            'cooldown_active': True,
            'next_allowed_at': next_allowed_at,
            'discord_connection': DiscordConnectionSerializer(connection).data,
            'user': UserSerializer(request.user, context={'request': request}).data,
        }, status=status.HTTP_200_OK)

    try:
        result = DiscordRoleSyncService().sync_member_roles(connection)
    except DiscordRoleSyncConfigurationError as e:
        return Response({
            'error': str(e),
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except DiscordRoleSyncUnavailable as e:
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE
        payload = {
            'error': 'Discord is unavailable. Please try again later.',
            'code': 'discord_unavailable',
        }
        if e.retry_after is not None:
            payload['retry_after'] = e.retry_after
        return Response(payload, status=response_status)
    except DiscordRoleSyncError:
        return Response({
            'error': 'Failed to refresh Discord roles.',
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    connection = result.connection
    connection.roles_manual_synced_at = now
    connection.save(update_fields=['roles_manual_synced_at'])

    return Response({
        'message': 'Discord roles refreshed successfully.',
        'cooldown_active': False,
        'is_member': result.is_member,
        'next_allowed_at': manual_refresh_next_allowed_at(connection),
        'discord_connection': DiscordConnectionSerializer(connection).data,
        'user': UserSerializer(request.user, context={'request': request}).data,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([IsCronToken])
def sync_discord_roles(request):
    """Trigger a background sync of Discord role catalog and linked members."""
    batch_size = int(request.data.get(
        'batch_size',
        getattr(settings, 'DISCORD_ROLE_SYNC_BATCH_SIZE', 500),
    ))

    lock_token, elapsed_seconds = _acquire_role_sync_lock()
    if lock_token is None:
        elapsed = f' ({elapsed_seconds:.0f}s since last heartbeat)' if elapsed_seconds is not None else ''
        return Response({
            'success': False,
            'message': f'Discord role sync already in progress{elapsed}',
        }, status=status.HTTP_409_CONFLICT)

    heartbeat_stop = threading.Event()

    def _heartbeat():
        from django.db import connection as db_connection

        try:
            while not heartbeat_stop.wait(DISCORD_ROLE_SYNC_HEARTBEAT_INTERVAL_SECONDS):
                if not _refresh_role_sync_lock(lock_token):
                    return
        finally:
            db_connection.close()

    def _run_sync():
        from django.db import connection as db_connection

        start = time.time()
        try:
            stats = DiscordRoleSyncService().sync_oldest_connections(batch_size=batch_size)
            logger.info(
                "Background Discord role sync completed in %.1fs: %s",
                time.time() - start,
                stats,
            )
        except Exception as e:
            logger.error("Background Discord role sync failed: %s", e, exc_info=True)
        finally:
            heartbeat_stop.set()
            heartbeat_thread.join(timeout=1)
            _release_role_sync_lock(lock_token)
            db_connection.close()

    heartbeat_thread = threading.Thread(target=_heartbeat, daemon=True)
    sync_thread = threading.Thread(target=_run_sync, daemon=True)
    try:
        heartbeat_thread.start()
        sync_thread.start()
    except Exception:
        heartbeat_stop.set()
        _release_role_sync_lock(lock_token)
        raise

    return Response({
        'success': True,
        'message': 'Discord role sync started in background',
        'batch_size': batch_size,
    }, status=status.HTTP_202_ACCEPTED)


def start_earned_role_assignment():
    """Start earned role assignment in the background if no run is active."""
    from .earned_roles import assign_earned_community_roles

    lock_token, elapsed_seconds = _acquire_role_sync_lock(DISCORD_EARNED_ROLE_LOCK_NAME)
    if lock_token is None:
        return False, elapsed_seconds

    heartbeat_stop = threading.Event()

    def _heartbeat():
        from django.db import connection as db_connection

        try:
            while not heartbeat_stop.wait(DISCORD_ROLE_SYNC_HEARTBEAT_INTERVAL_SECONDS):
                if not _refresh_role_sync_lock(lock_token, DISCORD_EARNED_ROLE_LOCK_NAME):
                    return
        finally:
            db_connection.close()

    def _run_assignment():
        from django.db import connection as db_connection

        start = time.time()
        try:
            stats = assign_earned_community_roles()
            stats.pop('assignments', None)
            logger.info(
                "Background earned role assignment completed in %.1fs: %s",
                time.time() - start,
                stats,
            )
        except Exception as e:
            logger.error("Background earned role assignment failed: %s", e, exc_info=True)
        finally:
            heartbeat_stop.set()
            heartbeat_thread.join(timeout=1)
            _release_role_sync_lock(lock_token, DISCORD_EARNED_ROLE_LOCK_NAME)
            db_connection.close()

    heartbeat_thread = threading.Thread(target=_heartbeat, daemon=True)
    assign_thread = threading.Thread(target=_run_assignment, daemon=True)
    try:
        heartbeat_thread.start()
        assign_thread.start()
    except Exception:
        heartbeat_stop.set()
        _release_role_sync_lock(lock_token, DISCORD_EARNED_ROLE_LOCK_NAME)
        raise

    return True, None


@api_view(['POST'])
@authentication_classes([])
@permission_classes([IsCronToken])
def assign_earned_discord_roles(request):
    """Trigger a background assignment of earned community roles (Synapse/Brain)."""
    started, elapsed_seconds = start_earned_role_assignment()
    if not started:
        elapsed = f' ({elapsed_seconds:.0f}s since last heartbeat)' if elapsed_seconds is not None else ''
        return Response({
            'success': False,
            'message': f'Earned role assignment already in progress{elapsed}',
        }, status=status.HTTP_409_CONFLICT)

    return Response({
        'success': True,
        'message': 'Earned role assignment started in background',
    }, status=status.HTTP_202_ACCEPTED)
