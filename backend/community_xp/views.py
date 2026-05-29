import threading
import time

from django.conf import settings
from django.db import connection
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from tally.middleware.logging_utils import get_app_logger
from validators.permissions import IsCronToken

from .models import Mee6SyncRun
from .services import (
    Mee6SyncValidationError,
    acquire_sync_lock,
    apply_sync_run,
    refresh_sync_lock,
    release_sync_lock,
    run_mee6_sync,
)

logger = get_app_logger('community_xp')
HEARTBEAT_INTERVAL_SECONDS = int(getattr(settings, 'MEE6_SYNC_LOCK_HEARTBEAT_INTERVAL_SECONDS', 60))


def _parse_positive_int(value, field_name):
    if value in (None, ''):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise Mee6SyncValidationError(f'{field_name} must be a positive integer') from exc
    if parsed <= 0:
        raise Mee6SyncValidationError(f'{field_name} must be positive')
    return parsed


def _run_mee6_fetch_and_apply(*, guild_id=None, page_size=None):
    start = time.time()
    fetch_result = run_mee6_sync(
        guild_id=guild_id,
        page_size=page_size,
        use_lock=False,
    )
    run = Mee6SyncRun.objects.get(pk=fetch_result['run_id'])
    apply_result = apply_sync_run(run)
    logger.info(
        "MEE6 XP fetch/apply completed in %.1fs: fetch=%s apply=%s",
        time.time() - start,
        fetch_result,
        apply_result,
    )
    return fetch_result, apply_result


def _run_mee6_fetch_and_apply_in_background(*, guild_id=None, page_size=None, owner_token=None):
    heartbeat_stop = threading.Event()

    def _heartbeat():
        try:
            while not heartbeat_stop.wait(HEARTBEAT_INTERVAL_SECONDS):
                if not refresh_sync_lock(owner_token):
                    return
        finally:
            connection.close()

    heartbeat_thread = threading.Thread(target=_heartbeat, daemon=True)
    heartbeat_thread.start()

    try:
        _run_mee6_fetch_and_apply(guild_id=guild_id, page_size=page_size)
    except Exception as exc:
        logger.error("MEE6 XP fetch/apply failed: %s", exc, exc_info=True)
    finally:
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=1)
        release_sync_lock(owner_token)
        connection.close()


@api_view(['POST'])
@authentication_classes([])
@permission_classes([IsCronToken])
def sync_mee6_xp(request):
    """
    Trigger the daily Discord XP migration:
    1. Fetch a MEE6 leaderboard snapshot.
    2. Apply that snapshot as the active portal community XP baseline.
    """
    guild_id = request.data.get('guild_id') or None

    try:
        page_size = _parse_positive_int(request.data.get('page_size'), 'page_size')
        owner_token, elapsed_seconds = acquire_sync_lock()
    except Mee6SyncValidationError as exc:
        return Response({'success': False, 'message': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    if owner_token is None:
        elapsed = f' ({elapsed_seconds:.0f}s since last heartbeat)' if elapsed_seconds is not None else ''
        logger.warning("MEE6 XP sync skipped: another sync is already in progress%s", elapsed)
        return Response({
            'success': False,
            'message': f'MEE6 XP sync already in progress{elapsed}',
        }, status=status.HTTP_409_CONFLICT)

    thread = threading.Thread(
        target=_run_mee6_fetch_and_apply_in_background,
        kwargs={
            'guild_id': guild_id,
            'page_size': page_size,
            'owner_token': owner_token,
        },
        daemon=True,
    )
    try:
        thread.start()
    except Exception:
        release_sync_lock(owner_token)
        raise

    return Response({
        'success': True,
        'message': 'MEE6 XP fetch and portal migration started in background',
    }, status=status.HTTP_202_ACCEPTED)
