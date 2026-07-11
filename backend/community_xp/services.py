import random
import secrets
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime

import requests
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from requests import RequestException

from social_connections.models import DiscordConnection
from tally.middleware.logging_utils import get_app_logger

from .constants import COMMUNITY_XP_EXCLUDED_TYPE_SLUGS
from .models import Mee6CurrentXP, Mee6PlayerSnapshot, Mee6SyncLock, Mee6SyncRun

logger = get_app_logger('community_xp')

DEFAULT_GUILD_ID = '1237055789441487021'
DEFAULT_PAGE_SIZE = 1000
LOCK_NAME = 'mee6_xp_sync'


class Mee6SyncError(Exception):
    """Raised when a MEE6 sync cannot safely complete."""


class Mee6SyncValidationError(Mee6SyncError):
    """Raised when sync input is invalid before contacting MEE6."""


class Mee6SyncAlreadyRunning(Mee6SyncError):
    def __init__(self, elapsed_seconds):
        self.elapsed_seconds = elapsed_seconds
        super().__init__('MEE6 XP sync already running')


@dataclass(frozen=True)
class NormalizedMee6Player:
    discord_id: str
    username: str
    discriminator: str
    avatar_hash: str
    rank: int
    xp: int
    level: int
    message_count: int
    detailed_xp: list
    raw_player: dict


@dataclass(frozen=True)
class Mee6FetchResult:
    guild_id: str
    guild_name: str
    page_size: int
    pages_fetched: int
    players: list[NormalizedMee6Player]
    duplicate_players: int


def get_default_guild_id():
    return (
        getattr(settings, 'MEE6_GUILD_ID', '')
        or getattr(settings, 'DISCORD_GUILD_ID', '')
        or DEFAULT_GUILD_ID
    )


def get_default_page_size():
    return int(getattr(settings, 'MEE6_PAGE_SIZE', DEFAULT_PAGE_SIZE) or DEFAULT_PAGE_SIZE)


def _as_non_negative_int(value, field_name):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise Mee6SyncError(f'Malformed MEE6 player field: {field_name}') from exc
    if parsed < 0:
        raise Mee6SyncError(f'Malformed MEE6 player field: {field_name} must be non-negative')
    return parsed


def _retry_after_seconds(value):
    if not value:
        return None
    try:
        return max(float(value), 0)
    except (TypeError, ValueError):
        pass

    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return max((retry_at - timezone.now()).total_seconds(), 0)


class Mee6Client:
    base_url = 'https://mee6.xyz/api/plugins/levels/leaderboard'

    def __init__(
        self,
        session=None,
        timeout=None,
        max_retries=None,
        base_delay=None,
        max_delay=None,
        inter_page_delay=None,
        sleep_func=time.sleep,
    ):
        self.session = session or requests.Session()
        self.timeout = timeout if timeout is not None else float(getattr(settings, 'MEE6_REQUEST_TIMEOUT', 20))
        self.max_retries = max_retries if max_retries is not None else int(getattr(settings, 'MEE6_MAX_RETRIES', 3))
        self.base_delay = base_delay if base_delay is not None else float(getattr(settings, 'MEE6_RETRY_BASE_DELAY', 1))
        self.max_delay = max_delay if max_delay is not None else float(getattr(settings, 'MEE6_RETRY_MAX_DELAY', 30))
        self.inter_page_delay = (
            inter_page_delay
            if inter_page_delay is not None
            else float(getattr(settings, 'MEE6_INTER_PAGE_DELAY', 0.25))
        )
        self.sleep_func = sleep_func

    def fetch_all_players(self, guild_id, page_size):
        players = []
        seen_discord_ids = set()
        duplicate_players = 0
        pages_fetched = 0
        guild_name = ''

        page = 0
        while True:
            payload = self.fetch_page(guild_id, page, page_size)
            guild = payload.get('guild') or {}
            response_guild_id = str(guild.get('id') or guild_id)
            if response_guild_id != str(guild_id):
                raise Mee6SyncError(
                    f'MEE6 response guild mismatch: expected {guild_id}, got {response_guild_id}'
                )

            if guild.get('name'):
                guild_name = str(guild['name'])[:255]

            page_players = payload.get('players')
            if not isinstance(page_players, list):
                raise Mee6SyncError('Malformed MEE6 response: players must be a list')
            if page == 0 and not page_players:
                raise Mee6SyncError('MEE6 returned no players on the first page')

            pages_fetched += 1
            for index, raw_player in enumerate(page_players):
                player = self.normalize_player(raw_player, rank=(page * page_size) + index + 1)
                if player.discord_id in seen_discord_ids:
                    duplicate_players += 1
                    continue
                seen_discord_ids.add(player.discord_id)
                players.append(player)

            if len(page_players) < page_size:
                break
            if self.inter_page_delay > 0:
                self.sleep_func(self.inter_page_delay)
            page += 1

        return Mee6FetchResult(
            guild_id=str(guild_id),
            guild_name=guild_name,
            page_size=page_size,
            pages_fetched=pages_fetched,
            players=players,
            duplicate_players=duplicate_players,
        )

    def fetch_page(self, guild_id, page, page_size):
        url = f'{self.base_url}/{guild_id}'
        params = {'page': page, 'limit': page_size}
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
            except RequestException as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    raise Mee6SyncError(f'MEE6 request failed for page {page}: {exc}') from exc
                self._sleep_before_retry(attempt)
                continue

            if response.status_code == 429 or response.status_code >= 500:
                last_error = f'HTTP {response.status_code}'
                if attempt >= self.max_retries:
                    raise Mee6SyncError(f'MEE6 request failed for page {page}: HTTP {response.status_code}')
                self._sleep_before_retry(attempt, response=response)
                continue

            if response.status_code >= 400:
                raise Mee6SyncError(f'MEE6 request failed for page {page}: HTTP {response.status_code}')

            try:
                return response.json()
            except ValueError as exc:
                raise Mee6SyncError(f'MEE6 returned malformed JSON for page {page}') from exc

        raise Mee6SyncError(f'MEE6 request failed for page {page}: {last_error}')

    def _sleep_before_retry(self, attempt, response=None):
        retry_after = _retry_after_seconds(response.headers.get('Retry-After')) if response is not None else None
        delay = retry_after
        if delay is None:
            delay = min(self.max_delay, self.base_delay * (2 ** attempt))
            delay += random.uniform(0, 0.25)
        self.sleep_func(delay)

    @staticmethod
    def normalize_player(raw_player, rank):
        if not isinstance(raw_player, dict):
            raise Mee6SyncError('Malformed MEE6 response: player must be an object')

        discord_id = str(raw_player.get('id') or '').strip()
        if not discord_id:
            raise Mee6SyncError('Malformed MEE6 player field: id')

        detailed_xp = raw_player.get('detailed_xp')
        if not isinstance(detailed_xp, list):
            detailed_xp = []

        return NormalizedMee6Player(
            discord_id=discord_id,
            username=str(raw_player.get('username') or '')[:100],
            discriminator=str(raw_player.get('discriminator') or '')[:10],
            avatar_hash=str(raw_player.get('avatar') or '')[:100],
            rank=rank,
            xp=_as_non_negative_int(raw_player.get('xp', 0), 'xp'),
            level=_as_non_negative_int(raw_player.get('level', 0), 'level'),
            message_count=_as_non_negative_int(raw_player.get('message_count', 0), 'message_count'),
            detailed_xp=detailed_xp,
            raw_player=raw_player,
        )


def _ensure_sync_lock_row():
    try:
        Mee6SyncLock.objects.get_or_create(name=LOCK_NAME)
    except IntegrityError:
        pass


def acquire_sync_lock(stale_after_seconds=None):
    stale_after_seconds = stale_after_seconds or int(getattr(settings, 'MEE6_SYNC_LOCK_STALE_AFTER_SECONDS', 3600))
    _ensure_sync_lock_row()

    with transaction.atomic():
        now = timezone.now()
        lock_row = Mee6SyncLock.objects.select_for_update().get(name=LOCK_NAME)
        is_running = (
            lock_row.owner_token is not None
            and lock_row.heartbeat_at is not None
            and (lock_row.released_at is None or lock_row.heartbeat_at > lock_row.released_at)
        )

        if is_running:
            elapsed_seconds = (now - lock_row.heartbeat_at).total_seconds()
            if elapsed_seconds <= stale_after_seconds:
                return None, elapsed_seconds
            logger.warning("Stale MEE6 XP sync lock detected after %ss", f"{elapsed_seconds:.0f}")

        owner_token = secrets.token_hex(16)
        lock_row.owner_token = owner_token
        lock_row.acquired_at = now
        lock_row.heartbeat_at = now
        lock_row.released_at = None
        lock_row.save(update_fields=['owner_token', 'acquired_at', 'heartbeat_at', 'released_at'])

    return owner_token, None


def release_sync_lock(owner_token):
    if not owner_token:
        return
    now = timezone.now()
    Mee6SyncLock.objects.filter(
        name=LOCK_NAME,
        owner_token=owner_token,
    ).update(owner_token=None, heartbeat_at=now, released_at=now)


def refresh_sync_lock(owner_token):
    if not owner_token:
        return False
    return bool(Mee6SyncLock.objects.filter(
        name=LOCK_NAME,
        owner_token=owner_token,
    ).update(heartbeat_at=timezone.now()))


def _connection_map(discord_ids):
    connections = (
        DiscordConnection.objects
        .filter(platform_user_id__in=discord_ids)
        .select_related('user')
        .order_by('id')
    )

    by_discord_id = {}
    for connection in connections:
        by_discord_id.setdefault(str(connection.platform_user_id), connection)
    return by_discord_id


def store_fetch_result(run, fetch_result):
    now = timezone.now()
    discord_ids = [player.discord_id for player in fetch_result.players]
    connections_by_discord_id = _connection_map(discord_ids)
    matched_user_ids = {
        connection.user_id
        for connection in connections_by_discord_id.values()
    }
    snapshots = []

    for player in fetch_result.players:
        snapshots.append(Mee6PlayerSnapshot(
            run=run,
            guild_id=fetch_result.guild_id,
            discord_id=player.discord_id,
            username=player.username,
            discriminator=player.discriminator,
            avatar_hash=player.avatar_hash,
            rank=player.rank,
            xp=player.xp,
            level=player.level,
            message_count=player.message_count,
            detailed_xp=player.detailed_xp,
            raw_player=player.raw_player,
        ))

    with transaction.atomic():
        Mee6PlayerSnapshot.objects.bulk_create(snapshots, batch_size=1000)
        run.guild_name = fetch_result.guild_name
        run.status = Mee6SyncRun.STATUS_SUCCESS
        run.page_size = fetch_result.page_size
        run.pages_fetched = fetch_result.pages_fetched
        run.players_fetched = len(fetch_result.players)
        run.duplicate_players = fetch_result.duplicate_players
        run.matched_players = len(matched_user_ids)
        run.unmatched_players = len(fetch_result.players) - len(matched_user_ids)
        run.completed_at = now
        run.error_message = ''
        run.save(update_fields=[
            'guild_name',
            'status',
            'page_size',
            'pages_fetched',
            'players_fetched',
            'duplicate_players',
            'matched_players',
            'unmatched_players',
            'completed_at',
            'error_message',
            'updated_at',
        ])

    return {
        'run_id': run.id,
        'guild_id': run.guild_id,
        'status': run.status,
        'players_fetched': run.players_fetched,
        'pages_fetched': run.pages_fetched,
        'matched_players': run.matched_players,
        'unmatched_players': run.unmatched_players,
        'duplicate_players': run.duplicate_players,
        'applied': False,
    }


def _validate_xp_state_before_applying(run):
    from contributions.models import ContributionDiscordXPState
    from django.db.models import Q

    late_distribution = (
        ContributionDiscordXPState.objects
        .filter(
            Q(contribution__contribution_type__category__slug='community') |
            Q(social_task_completion__task__category__slug='community'),
            distributed_at__gte=run.started_at,
            awarded_amount__gt=0,
        )
        .exclude(contribution__contribution_type__slug__in=COMMUNITY_XP_EXCLUDED_TYPE_SLUGS)
        .order_by('-distributed_at', '-id')
        .first()
    )
    if late_distribution:
        if late_distribution.contribution_id:
            source = f'contribution #{late_distribution.contribution_id}'
        else:
            source = f'social task completion #{late_distribution.social_task_completion_id}'
        raise Mee6SyncError(
            f'Cannot apply MEE6 sync #{run.id}; {source} was marked distributed '
            'after this snapshot fetch started. '
            'Fetch a newer MEE6 snapshot before applying a new baseline.'
        )


def _apply_sync_run_unlocked(run, applied_by=None):
    if run.status != Mee6SyncRun.STATUS_SUCCESS:
        raise Mee6SyncError('Only successful MEE6 sync runs can be applied as the baseline')
    if not run.completed_at:
        raise Mee6SyncError('Cannot apply a MEE6 sync run before it has completed')

    latest_applied_run = (
        Mee6SyncRun.objects
        .filter(
            guild_id=run.guild_id,
            status=Mee6SyncRun.STATUS_SUCCESS,
            completed_at__isnull=False,
            applied_at__isnull=False,
        )
        .exclude(id=run.id)
        .order_by('-completed_at', '-id')
        .first()
    )
    if latest_applied_run and run.completed_at < latest_applied_run.completed_at:
        raise Mee6SyncError(
            f'Cannot apply MEE6 sync #{run.id}; sync #{latest_applied_run.id} is newer and already applied'
        )

    _validate_xp_state_before_applying(run)

    now = timezone.now()
    snapshots = list(
        Mee6PlayerSnapshot.objects
        .filter(run=run)
        .order_by('rank')
    )
    if not snapshots:
        raise Mee6SyncError('Cannot apply a MEE6 sync run with no player snapshots')

    discord_ids = [snapshot.discord_id for snapshot in snapshots]
    connections_by_discord_id = _connection_map(discord_ids)
    matched_user_ids = set()
    current_rows = []

    for snapshot in snapshots:
        connection = connections_by_discord_id.get(str(snapshot.discord_id))
        matched_user = connection.user if connection else None
        matched_at = now if matched_user else None
        if matched_user:
            matched_user_ids.add(matched_user.id)

        current_rows.append(Mee6CurrentXP(
            guild_id=snapshot.guild_id,
            discord_id=snapshot.discord_id,
            username=snapshot.username,
            discriminator=snapshot.discriminator,
            avatar_hash=snapshot.avatar_hash,
            rank=snapshot.rank,
            xp=snapshot.xp,
            level=snapshot.level,
            message_count=snapshot.message_count,
            detailed_xp=snapshot.detailed_xp,
            sync_run=run,
            source_snapshot=snapshot,
            matched_user=matched_user,
            matched_at=matched_at,
            synced_at=run.completed_at,
        ))

    with transaction.atomic():
        Mee6CurrentXP.objects.filter(guild_id=run.guild_id).delete()
        Mee6CurrentXP.objects.bulk_create(current_rows, batch_size=1000)

        run.matched_players = len(matched_user_ids)
        run.unmatched_players = len(snapshots) - len(matched_user_ids)
        run.applied_at = now
        run.applied_by = applied_by if getattr(applied_by, 'pk', None) else None
        run.save(update_fields=[
            'matched_players',
            'unmatched_players',
            'applied_at',
            'applied_by',
            'updated_at',
        ])

    return {
        'run_id': run.id,
        'guild_id': run.guild_id,
        'status': run.status,
        'players_applied': len(snapshots),
        'matched_players': run.matched_players,
        'unmatched_players': run.unmatched_players,
        'applied_at': run.applied_at,
    }


def apply_sync_run(run, applied_by=None, lock_owner_token=None):
    """Apply a fetched snapshot while excluding concurrent XP mutations.

    The scheduled fetch/apply workflow passes the lock token it already owns.
    Manual/admin callers acquire the same lock for the duration of application.
    """
    acquired_here = False
    owner_token = lock_owner_token

    if owner_token:
        if not refresh_sync_lock(owner_token):
            raise Mee6SyncError('MEE6 XP sync lock ownership was lost before apply')
    else:
        owner_token, elapsed_seconds = acquire_sync_lock()
        if not owner_token:
            raise Mee6SyncAlreadyRunning(elapsed_seconds)
        acquired_here = True

    try:
        return _apply_sync_run_unlocked(run, applied_by=applied_by)
    finally:
        if acquired_here:
            release_sync_lock(owner_token)


def run_mee6_sync(guild_id=None, page_size=None, client=None, use_lock=True):
    guild_id = str(guild_id or get_default_guild_id())
    try:
        page_size = int(page_size or get_default_page_size())
    except (TypeError, ValueError) as exc:
        raise Mee6SyncValidationError('MEE6 page size must be a positive integer') from exc
    if page_size <= 0:
        raise Mee6SyncValidationError('MEE6 page size must be positive')

    owner_token = None
    if use_lock:
        owner_token, elapsed_seconds = acquire_sync_lock()
        if not owner_token:
            raise Mee6SyncAlreadyRunning(elapsed_seconds)

    run = Mee6SyncRun.objects.create(
        guild_id=guild_id,
        page_size=page_size,
        status=Mee6SyncRun.STATUS_RUNNING,
    )

    try:
        client = client or Mee6Client()
        fetch_result = client.fetch_all_players(guild_id, page_size)
        if not fetch_result.players:
            raise Mee6SyncError('MEE6 returned no players')
        return store_fetch_result(run, fetch_result)
    except Exception as exc:
        run.status = Mee6SyncRun.STATUS_FAILED
        run.completed_at = timezone.now()
        run.error_message = str(exc)[:4000]
        run.save(update_fields=['status', 'completed_at', 'error_message', 'updated_at'])
        logger.error("MEE6 XP sync failed: %s", exc, exc_info=True)
        raise
    finally:
        if owner_token:
            release_sync_lock(owner_token)


def match_current_xp_for_connection(connection, guild_id=None):
    guild_id = str(guild_id or get_default_guild_id())
    discord_id = str(connection.platform_user_id or '')
    if not discord_id:
        return None

    with transaction.atomic():
        current = (
            Mee6CurrentXP.objects
            .select_for_update()
            .filter(guild_id=guild_id, discord_id=discord_id)
            .first()
        )
        if not current:
            return None
        if current.matched_user_id == connection.user_id:
            return current

        current.matched_user = connection.user
        current.matched_at = timezone.now()
        current.save(update_fields=['matched_user', 'matched_at', 'updated_at'])

    return current


def clear_current_xp_match_for_connection(connection, guild_id=None):
    guild_id = str(guild_id or get_default_guild_id())
    discord_id = str(connection.platform_user_id or '')
    if not discord_id:
        return 0
    return Mee6CurrentXP.objects.filter(
        guild_id=guild_id,
        discord_id=discord_id,
        matched_user=connection.user,
    ).update(matched_user=None, matched_at=None)
