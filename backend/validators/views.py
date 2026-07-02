import logging
import re
import uuid
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from utils.throttling import WalletLinkRateThrottle
from django.shortcuts import get_object_or_404
from django.db.models import Min, Q, Count
from django.db import IntegrityError, transaction
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from .models import SyncLock, Validator, ValidatorWallet
from .serializers import (
    GrafanaValidatorSerializer,
    ValidatorWalletSerializer,
    WallOfShameSerializer,
)
from .permissions import IsCronToken
from .genlayer_validators_service import GenLayerValidatorsService
from .grafana_service import GrafanaValidatorStatusService
from .version_status import compute_version_status
from . import streaks as streaks_lib
from users.models import User
from users.serializers import ValidatorSerializer, UserSerializer
from contributions.models import Contribution, ContributionType

logger = logging.getLogger(__name__)


class ValidatorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Validator profiles.
    """
    queryset = Validator.objects.all()
    serializer_class = ValidatorSerializer

    def _is_staff_mutation(self, request):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )

    def _deny_non_staff_mutation(self, request):
        if self._is_staff_mutation(request):
            return None
        return Response(
            {'detail': 'Only staff users can mutate validator profiles.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    def create(self, request, *args, **kwargs):
        denied = self._deny_non_staff_mutation(request)
        if denied is not None:
            return denied
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        denied = self._deny_non_staff_mutation(request)
        if denied is not None:
            return denied
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        denied = self._deny_non_staff_mutation(request)
        if denied is not None:
            return denied
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        denied = self._deny_non_staff_mutation(request)
        if denied is not None:
            return denied
        return super().destroy(request, *args, **kwargs)
    
    def get_permissions(self):
        """
        Allow read-only access without authentication for public endpoints.
        """
        if self.action in ['all_validators', 'newest_validators']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['get'], url_path='me')
    def my_profile(self, request):
        """
        Get current user's validator profile.

        Read-only: node versions are sourced from Grafana (see
        validators/grafana_service.py) and are not editable from the portal.
        """
        try:
            validator = Validator.objects.get(user=request.user)
            serializer = self.get_serializer(validator)
            return Response(serializer.data)
        except Validator.DoesNotExist:
            return Response(
                {'detail': 'Validator profile not found for current user.'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='all')
    def all_validators(self, request):
        """
        Get all validator profile users for public ecosystem displays.
        """
        from users.serializers import LightUserSerializer

        validators = (
            Validator.objects
            .select_related('user')
            .filter(user__visible=True)
            .order_by('display_order', '-created_at')
        )

        result = []
        for validator in validators:
            user_data = LightUserSerializer(validator.user).data
            user_data['validator'] = True
            user_data['validator_created_at'] = validator.created_at
            result.append(user_data)

        return Response(result)
    
    @action(detail=False, methods=['get'], url_path='newest')
    def newest_validators(self, request):
        """
        Get validators sorted by their first uptime contribution date (newest first).
        Returns the 5 most recent validators to join.
        Uses lightweight serializers to avoid N+1 queries.
        """
        from django.db.models.functions import TruncDate
        from users.serializers import LightUserSerializer

        limit = int(request.GET.get('limit', 5))

        # Get the Uptime contribution type
        try:
            uptime_type = ContributionType.objects.get(name__iexact='uptime')
        except ContributionType.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)

        # Get all validators with their first uptime contribution.
        # Order by Validator.display_order (admin-controlled), then newest-first
        # as a tiebreaker. Mirrors the Partners ordering pattern.
        validators_with_first_uptime = (
            Contribution.objects
            .filter(contribution_type=uptime_type)
            .values('user', 'user__address', 'user__name', 'user__validator__display_order')
            .annotate(
                first_uptime_date=Min('contribution_date')
            )
            .order_by('user__validator__display_order', '-first_uptime_date')[:limit]
        )

        # Get user IDs and fetch users with optimization
        user_ids = [v['user'] for v in validators_with_first_uptime]
        users_dict = {
            user.id: user
            for user in User.objects.filter(id__in=user_ids).select_related('validator', 'builder')
        }

        # Build result with lightweight serializer
        result = []
        for validator in validators_with_first_uptime:
            user = users_dict.get(validator['user'])
            if user:
                user_data = LightUserSerializer(user).data
                user_data['validator'] = True
                user_data['first_uptime_date'] = validator['first_uptime_date']
                result.append(user_data)
            else:
                # Fallback to simple data if user not found
                result.append({
                    'address': validator['user__address'],
                    'name': validator['user__name'],
                    'validator': True,
                    'first_uptime_date': validator['first_uptime_date']
                })

        return Response(result)

    @action(detail=False, methods=['get'], url_path='my-wallets')
    def my_wallets(self, request):
        """
        Get validator wallets for the current authenticated user (operator).
        Returns list of validator wallets linked to this operator.
        """
        if not hasattr(request.user, 'validator'):
            return Response(
                {'detail': 'No validator profile found for current user.'},
                status=status.HTTP_404_NOT_FOUND
            )

        wallets = ValidatorWallet.objects.filter(
            operator=request.user.validator
        ).order_by('-created_at')

        serializer = ValidatorWalletSerializer(wallets, many=True)
        return Response({
            'wallets': serializer.data,
            'active_count': wallets.filter(status='active').count(),
            'total_count': wallets.count()
        })

    @action(detail=False, methods=['post'], url_path='link-by-operator',
            throttle_classes=[WalletLinkRateThrottle])
    def link_by_operator(self, request):
        """
        Link validator wallets to the current user by operator address.
        Only available for validators who don't have any wallets linked yet.

        NOTE: linking is first-come-first-served on a public operator address
        and carries no cryptographic ownership proof; the throttle bounds
        mass-claiming, and mistaken/abusive links are logged and reversible
        by staff via the admin.
        """
        user = request.user

        # Verify user is a validator
        if not hasattr(user, 'validator'):
            return Response(
                {'error': 'Only validators can link wallets'},
                status=status.HTTP_403_FORBIDDEN
            )

        validator = user.validator

        # Check user has no linked wallets
        if ValidatorWallet.objects.filter(operator=validator).exists():
            return Response(
                {'error': 'You already have validator wallets linked'},
                status=status.HTTP_400_BAD_REQUEST
            )

        operator_address = request.data.get('operator_address', '').strip().lower()

        # Validate format (0x + 40 hex chars)
        if not re.match(r'^0x[a-fA-F0-9]{40}$', operator_address):
            return Response(
                {'error': 'Invalid Ethereum address format'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Claim atomically: lock the matching wallet rows so two concurrent
        # requests cannot both pass the "not linked yet" checks and link the
        # same operator (or give one user two operators).
        with transaction.atomic():
            wallets = (
                ValidatorWallet.objects
                .select_for_update()
                .filter(operator_address__iexact=operator_address)
            )

            if not wallets.exists():
                return Response(
                    {'error': 'No validator wallets found for this operator address'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Re-check under the lock that the caller still has no wallets
            if ValidatorWallet.objects.filter(operator=validator).exists():
                return Response(
                    {'error': 'You already have validator wallets linked'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if any wallet is already linked to another validator
            already_linked = wallets.exclude(operator__isnull=True).first()
            if already_linked:
                return Response(
                    {'error': 'This operator address is already linked to another validator'},
                    status=status.HTTP_409_CONFLICT
                )

            # Link all wallets to this validator
            count = wallets.update(operator=validator)

        logger.info(
            "Validator wallet link: user=%s (id=%s) claimed %s wallet(s) for operator %s",
            user.address, user.id, count, operator_address,
        )

        return Response({
            'success': True,
            'wallets_linked': count
        })


class ValidatorWalletViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for ValidatorWallet data.
    Read-only access to validator wallet information synced from GenLayer.
    """
    queryset = ValidatorWallet.objects.all()
    serializer_class = ValidatorWalletSerializer
    permission_classes = [AllowAny]
    SYNC_LOCK_NAME = 'validator_sync'
    GRAFANA_SYNC_LOCK_NAME = 'grafana_status_sync'
    SYNC_LOCK_STALE_AFTER_SECONDS = 1800
    SYNC_LOCK_HEARTBEAT_INTERVAL_SECONDS = 60
    WALL_OF_SHAME_CACHE_TTL_SECONDS = 60

    def get_queryset(self):
        """
        Optionally filter by operator address, status, or network.
        """
        queryset = ValidatorWallet.objects.select_related(
            'operator', 'operator__user'
        ).order_by('-created_at')

        # Filter by operator address
        operator_address = self.request.query_params.get('operator', None)
        if operator_address:
            queryset = queryset.filter(operator_address__iexact=operator_address)

        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by network
        network_filter = self.request.query_params.get('network', None)
        if network_filter:
            queryset = queryset.filter(network=network_filter)

        return queryset

    @classmethod
    def _ensure_sync_lock_row(cls, lock_name=None):
        name = lock_name or cls.SYNC_LOCK_NAME
        try:
            SyncLock.objects.get_or_create(name=name)
        except IntegrityError:
            # Another request created the singleton row first.
            pass

    @classmethod
    def _acquire_sync_lock(cls, lock_name=None):
        name = lock_name or cls.SYNC_LOCK_NAME
        cls._ensure_sync_lock_row(lock_name=name)

        with transaction.atomic():
            now = timezone.now()
            lock_row = (
                SyncLock.objects
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
                if secs <= cls.SYNC_LOCK_STALE_AFTER_SECONDS:
                    return None, secs

                logger.warning(
                    "Stale sync lock '%s' detected (%ss since last heartbeat), force-reclaiming",
                    name, f"{secs:.0f}",
                )

            lock_token = uuid.uuid4().hex
            lock_row.owner_token = lock_token
            lock_row.acquired_at = now
            lock_row.heartbeat_at = now
            lock_row.released_at = None
            lock_row.save(update_fields=['owner_token', 'acquired_at', 'heartbeat_at', 'released_at'])

        return lock_token, None

    @classmethod
    def _refresh_sync_lock(cls, lock_token, lock_name=None):
        name = lock_name or cls.SYNC_LOCK_NAME
        refreshed = (
            SyncLock.objects
            .filter(name=name, owner_token=lock_token)
            .update(heartbeat_at=timezone.now())
        )
        if not refreshed:
            logger.warning("Skipped sync lock '%s' heartbeat because ownership changed", name)
        return bool(refreshed)

    @classmethod
    def _release_sync_lock(cls, lock_token, lock_name=None):
        name = lock_name or cls.SYNC_LOCK_NAME
        now = timezone.now()
        released = (
            SyncLock.objects
            .filter(name=name, owner_token=lock_token)
            .update(owner_token=None, heartbeat_at=now, released_at=now)
        )
        if not released:
            logger.warning("Skipped sync lock '%s' release because ownership changed", name)

    def list(self, request, *args, **kwargs):
        """
        List all validator wallets with optional filtering.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        # Status counts
        active_count = queryset.filter(status='active').count()
        quarantined_count = queryset.filter(status='quarantined').count()
        banned_count = queryset.filter(status='banned').count()
        inactive_count = queryset.filter(status='inactive').count()

        # Per-network stats
        network_breakdown = ValidatorWallet.objects.values('network', 'status').annotate(
            count=Count('id')
        ).order_by('network', 'status')

        network_stats = {}
        for entry in network_breakdown:
            net = entry['network']
            if net not in network_stats:
                network_stats[net] = {'total': 0, 'active': 0, 'quarantined': 0, 'banned': 0, 'inactive': 0}
            network_stats[net][entry['status']] = entry['count']
            network_stats[net]['total'] += entry['count']

        return Response({
            'wallets': serializer.data,
            'stats': {
                'total': queryset.count(),
                'active': active_count,
                'quarantined': quarantined_count,
                'banned': banned_count,
                'inactive': inactive_count
            },
            'network_stats': network_stats
        })

    @action(detail=False, methods=['get'], url_path='by-operator/(?P<operator_address>[^/.]+)')
    def by_operator(self, request, operator_address=None):
        """
        Get all validator wallets for a specific operator address.
        """
        wallets = ValidatorWallet.objects.filter(
            operator_address__iexact=operator_address
        ).select_related('operator', 'operator__user').order_by('-created_at')

        serializer = self.get_serializer(wallets, many=True)
        return Response({
            'operator_address': operator_address,
            'wallets': serializer.data,
            'active_count': wallets.filter(status='active').count(),
            'total_count': wallets.count()
        })

    @action(detail=False, methods=['get'], url_path='by-user-address/(?P<user_address>[^/.]+)')
    def by_user_address(self, request, user_address=None):
        """
        Get all validator wallets for a user by their account address.
        Uses the operator FK relationship, which works even when the user's
        login address differs from their operator address on the blockchain.
        Falls back to operator_address matching if no FK link exists.
        """
        wallets = ValidatorWallet.objects.none()

        # First, try to find wallets via the operator FK relationship
        try:
            user = User.objects.get(address__iexact=user_address)
            if hasattr(user, 'validator'):
                wallets = ValidatorWallet.objects.filter(
                    operator=user.validator
                ).select_related('operator', 'operator__user').order_by('-created_at')
        except User.DoesNotExist:
            pass

        # If no wallets found via FK, fall back to operator_address matching
        if not wallets.exists():
            wallets = ValidatorWallet.objects.filter(
                operator_address__iexact=user_address
            ).select_related('operator', 'operator__user').order_by('-created_at')

        serializer = self.get_serializer(wallets, many=True)
        return Response({
            'user_address': user_address,
            'wallets': serializer.data,
            'active_count': wallets.filter(status='active').count(),
            'total_count': wallets.count()
        })

    @action(detail=False, methods=['post'], permission_classes=[IsCronToken], authentication_classes=[])
    def sync(self, request):
        """
        Trigger validator sync from GenLayer blockchain for all networks.
        Protected by X-Cron-Token header authentication.

        Runs the sync in a background thread and returns 202 Accepted immediately
        to avoid upstream proxy timeouts (504) on long-running syncs.
        Uses a database lock (SELECT FOR UPDATE + timestamp check) to prevent
        concurrent syncs across gunicorn workers.
        """
        import threading
        import time
        lock_token, elapsed_seconds = self._acquire_sync_lock()
        if lock_token is None:
            lock_row = SyncLock.objects.filter(name=self.SYNC_LOCK_NAME).only('acquired_at').first()
            elapsed = ''
            if lock_row and lock_row.acquired_at:
                runtime_seconds = (timezone.now() - lock_row.acquired_at).total_seconds()
                elapsed = f' (running for {runtime_seconds:.0f}s)'
            logger.warning(f"Validator sync skipped: another sync is already in progress{elapsed}")
            return Response({
                'success': False,
                'message': f'Sync already in progress{elapsed}',
            }, status=status.HTTP_409_CONFLICT)

        logger.info("Validator sync request accepted, starting background thread")
        heartbeat_stop = threading.Event()

        def _heartbeat():
            from django.db import connection

            try:
                while not heartbeat_stop.wait(self.SYNC_LOCK_HEARTBEAT_INTERVAL_SECONDS):
                    try:
                        if not self._refresh_sync_lock(lock_token):
                            return
                    except Exception:
                        logger.error("Failed to refresh sync lock heartbeat", exc_info=True)
                        return
            finally:
                connection.close()

        def _run_sync():
            from django.db import connection
            start = time.time()
            try:
                all_stats = GenLayerValidatorsService.sync_all_networks()
                duration = time.time() - start
                logger.info(f"Background validator sync completed in {duration:.1f}s: {all_stats}")
            except Exception as e:
                duration = time.time() - start
                logger.error(f"Background validator sync failed after {duration:.1f}s: {e}", exc_info=True)
            finally:
                heartbeat_stop.set()
                heartbeat_thread.join(timeout=1)
                try:
                    self._release_sync_lock(lock_token)
                except Exception:
                    logger.error("Failed to release sync lock", exc_info=True)
                connection.close()

        heartbeat_thread = threading.Thread(target=_heartbeat, daemon=True)
        thread = threading.Thread(target=_run_sync, daemon=True)
        try:
            heartbeat_thread.start()
            thread.start()
        except Exception:
            heartbeat_stop.set()
            self._release_sync_lock(lock_token)
            raise

        return Response({
            'success': True,
            'message': 'Validator sync started in background',
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['get'])
    def networks(self, request):
        """Return available network names and explorer URLs."""
        networks = []
        for key, config in settings.TESTNET_NETWORKS.items():
            if config.get('staking_contract_address'):
                networks.append({
                    'key': key,
                    'name': config['name'],
                    'explorer_url': config.get('explorer_url', ''),
                })
        return Response(networks)

    @action(
        detail=False, methods=['post'],
        url_path='sync-grafana',
        permission_classes=[IsCronToken], authentication_classes=[],
    )
    def sync_grafana(self, request):
        """
        Cross-check active validator wallets against Grafana Cloud
        (Prometheus + Loki) and update metrics_status / logs_status.
        Protected by X-Cron-Token. Runs in a background thread under a
        separate SyncLock so it can run alongside the on-chain validator sync.
        """
        import threading
        import time

        lock_name = self.GRAFANA_SYNC_LOCK_NAME
        lock_token, elapsed_seconds = self._acquire_sync_lock(lock_name=lock_name)
        if lock_token is None:
            lock_row = SyncLock.objects.filter(name=lock_name).only('acquired_at').first()
            elapsed = ''
            if lock_row and lock_row.acquired_at:
                runtime_seconds = (timezone.now() - lock_row.acquired_at).total_seconds()
                elapsed = f' (running for {runtime_seconds:.0f}s)'
            logger.warning(
                f"Grafana sync skipped: another sync is already in progress{elapsed}"
            )
            return Response({
                'success': False,
                'message': f'Sync already in progress{elapsed}',
            }, status=status.HTTP_409_CONFLICT)

        logger.info("Grafana sync request accepted, starting background thread")
        heartbeat_stop = threading.Event()

        def _heartbeat():
            from django.db import connection
            try:
                while not heartbeat_stop.wait(self.SYNC_LOCK_HEARTBEAT_INTERVAL_SECONDS):
                    try:
                        if not self._refresh_sync_lock(lock_token, lock_name=lock_name):
                            return
                    except Exception:
                        logger.error("Failed to refresh Grafana sync lock", exc_info=True)
                        return
            finally:
                connection.close()

        def _run_sync():
            from django.db import connection
            start = time.time()
            try:
                stats = GrafanaValidatorStatusService.sync_all_networks()
                duration = time.time() - start
                logger.info(f"Background Grafana sync completed in {duration:.1f}s: {stats}")
                # Invalidate cached wall-of-shame responses so next read returns fresh data
                self._invalidate_wall_of_shame_cache()
            except Exception as e:
                duration = time.time() - start
                logger.error(
                    f"Background Grafana sync failed after {duration:.1f}s: {e}",
                    exc_info=True,
                )
            finally:
                heartbeat_stop.set()
                heartbeat_thread.join(timeout=1)
                try:
                    self._release_sync_lock(lock_token, lock_name=lock_name)
                except Exception:
                    logger.error("Failed to release Grafana sync lock", exc_info=True)
                connection.close()

        heartbeat_thread = threading.Thread(target=_heartbeat, daemon=True)
        thread = threading.Thread(target=_run_sync, daemon=True)
        try:
            heartbeat_thread.start()
            thread.start()
        except Exception:
            heartbeat_stop.set()
            self._release_sync_lock(lock_token, lock_name=lock_name)
            raise

        return Response({
            'success': True,
            'message': 'Grafana sync started in background',
        }, status=status.HTTP_202_ACCEPTED)

    @classmethod
    def _wall_of_shame_cache_key(cls, network):
        return f'wall_of_shame:{network or "all"}'

    @classmethod
    def _invalidate_wall_of_shame_cache(cls):
        cache.delete(cls._wall_of_shame_cache_key('all'))
        for network in settings.TESTNET_NETWORKS.keys():
            cache.delete(cls._wall_of_shame_cache_key(network))

    @staticmethod
    def _days_since(started_at, now):
        if not started_at:
            return None
        return max(0, (now - started_at).days)

    @staticmethod
    def _operator_user_payload(wallet):
        if wallet.operator and wallet.operator.user and wallet.operator.user.visible:
            user = wallet.operator.user
            return {
                'id': user.id,
                'name': user.name,
                'address': user.address,
                'profile_image_url': user.profile_image_url,
                'visible': user.visible,
            }
        return None

    @classmethod
    def _version_context(cls, wallet, target, now):
        # Grace-aware version verdict; shared with the Grafana sync.
        return compute_version_status(wallet, target, now)

    @classmethod
    def _sync_shame_started_at(cls, wallets, targets, now):
        changed = []
        for wallet in wallets:
            update_wallet = False

            if wallet.metrics_status == 'shame':
                if not wallet.metrics_shame_started_at:
                    wallet.metrics_shame_started_at = now
                    update_wallet = True
            elif wallet.metrics_shame_started_at:
                wallet.metrics_shame_started_at = None
                update_wallet = True

            if wallet.logs_status == 'shame':
                if not wallet.logs_shame_started_at:
                    wallet.logs_shame_started_at = now
                    update_wallet = True
            elif wallet.logs_shame_started_at:
                wallet.logs_shame_started_at = None
                update_wallet = True

            version_context = cls._version_context(wallet, targets.get(wallet.network), now)
            desired_version_started_at = (
                version_context['shame_started_at']
                if version_context['status'] == 'shame'
                else None
            )
            if desired_version_started_at:
                if (
                    not wallet.version_shame_started_at
                    or wallet.version_shame_started_at < desired_version_started_at
                ):
                    wallet.version_shame_started_at = desired_version_started_at
                    update_wallet = True
            elif wallet.version_shame_started_at:
                wallet.version_shame_started_at = None
                update_wallet = True

            if update_wallet:
                changed.append(wallet)

        if changed:
            ValidatorWallet.objects.bulk_update(
                changed,
                [
                    'metrics_shame_started_at',
                    'logs_shame_started_at',
                    'version_shame_started_at',
                ],
            )

    @classmethod
    def _reason(cls, reason_type, label, started_at, now, reason_status='shame', **extra):
        return {
            'type': reason_type,
            'label': label,
            'status': reason_status,
            'started_at': started_at,
            'days_in_shame': cls._days_since(started_at, now),
            **extra,
        }

    @classmethod
    def _wallet_reasons(cls, wallet, target, now):
        reasons = []
        if wallet.metrics_status == 'shame':
            reasons.append(cls._reason(
                'metrics',
                'no metrics',
                wallet.metrics_shame_started_at,
                now,
            ))
        if wallet.logs_status == 'shame':
            reasons.append(cls._reason(
                'logs',
                'no logs',
                wallet.logs_shame_started_at,
                now,
            ))

        version_context = cls._version_context(wallet, target, now)
        if version_context['status'] in ('warning', 'shame'):
            started_at = (
                wallet.version_shame_started_at
                if version_context['status'] == 'shame'
                else None
            )
            reasons.append(cls._reason(
                'version',
                'outdated version',
                started_at,
                now,
                reason_status=version_context['status'],
                node_version=version_context['node_version'],
                target_version=version_context['target_version'],
                target_elapsed_days=version_context['target_elapsed_days'],
                grace_days_remaining=version_context['grace_days_remaining'],
            ))
        return reasons

    @classmethod
    def _build_validator_groups(cls, wallets, targets, now, snapshot_index=None,
                                streaks_by_wallet_id=None):
        groups = {}
        snapshot_index = snapshot_index or {}
        streaks_by_wallet_id = streaks_by_wallet_id or {}
        # Collect each operator+network's wallet ids for the any-node-clean roll-up.
        operator_network_wallet_ids = {}

        for wallet in wallets:
            operator_key = (
                f'validator:{wallet.operator_id}'
                if wallet.operator_id
                else f'operator:{(wallet.operator_address or "").lower()}'
            )
            operator_user = cls._operator_user_payload(wallet)
            group = groups.setdefault(operator_key, {
                'id': operator_key,
                'operator_address': wallet.operator_address,
                'operator_user': operator_user,
                'name': (
                    (operator_user or {}).get('name')
                    or wallet.moniker
                    or wallet.operator_address
                ),
                'logo_uri': wallet.logo_uri,
                'networks': [],
                'shame_reasons': [],
                'status': 'on',
            })
            if not group['logo_uri'] and wallet.logo_uri:
                group['logo_uri'] = wallet.logo_uri
            if not group['operator_user'] and operator_user:
                group['operator_user'] = operator_user

            target = targets.get(wallet.network)
            version_context = cls._version_context(wallet, target, now)
            reasons = cls._wallet_reasons(wallet, target, now)
            has_unknown = wallet.metrics_status == 'unknown' or wallet.logs_status == 'unknown'
            network_status = 'on'
            if any(reason['status'] == 'shame' for reason in reasons):
                network_status = 'shame'
            elif any(reason['status'] == 'warning' for reason in reasons):
                network_status = 'warning'
            elif has_unknown:
                network_status = 'unknown'

            for reason in reasons:
                group['shame_reasons'].append({
                    'network': wallet.network,
                    **reason,
                })

            node_streak = streaks_by_wallet_id.get(wallet.id) or {}
            operator_network_wallet_ids.setdefault(
                (operator_key, wallet.network), []
            ).append(wallet.id)

            group['networks'].append({
                'network': wallet.network,
                'wallet_id': wallet.id,
                'address': wallet.address,
                'moniker': wallet.moniker,
                'logo_uri': wallet.logo_uri,
                'metrics_status': wallet.metrics_status,
                'logs_status': wallet.logs_status,
                'version_status': version_context['status'],
                'node_version': version_context['node_version'],
                'target_version': version_context['target_version'],
                'status': network_status,
                'reasons': reasons,
                'clean_streak_days': node_streak.get('days'),
                'clean_streak_broken_by': node_streak.get('broken_by', []),
            })

        priority = {'shame': 0, 'warning': 1, 'unknown': 2, 'on': 3}
        network_order = {
            network: index for index, network in enumerate(settings.TESTNET_NETWORKS.keys())
        }

        for group in groups.values():
            statuses = [network['status'] for network in group['networks']]
            if 'shame' in statuses:
                group['status'] = 'shame'
            elif 'warning' in statuses:
                group['status'] = 'warning'
            elif 'unknown' in statuses:
                group['status'] = 'unknown'
            else:
                group['status'] = 'on'
            group['networks'].sort(key=lambda item: network_order.get(item['network'], 99))

            # Per-network operator streak, any-node-clean across the operator's
            # wallets on that network (a network-day is clean if ≥1 node was clean).
            network_streaks = {}
            for (op_key, net), wallet_ids in operator_network_wallet_ids.items():
                if op_key != group['id']:
                    continue
                network_streaks[net] = streaks_lib.clean_streak(
                    wallet_ids, now, snapshot_index
                )
            group['network_streaks'] = {
                net: {
                    'network': net,
                    'clean_streak_days': streak['days'],
                    'clean_streak_broken_by': streak['broken_by'],
                    'since': streak['since'],
                }
                for net, streak in sorted(
                    network_streaks.items(),
                    key=lambda kv: network_order.get(kv[0], 99),
                )
            }
            group['shame_reasons'].sort(
                key=lambda item: (
                    network_order.get(item['network'], 99),
                    priority.get(item['status'], 99),
                    item['label'],
                )
            )

        return sorted(
            groups.values(),
            key=lambda group: (
                priority.get(group['status'], 99),
                (group['name'] or '').lower(),
                group['operator_address'] or '',
            )
        )

    @action(detail=False, methods=['get'], url_path='grafana')
    def grafana(self, request):
        """
        Minimal validator roster for Grafana (Infinity datasource).

        Flat array, one row per validator wallet across ALL statuses, carrying
        the Grafana `network` label and the on-chain `node` address so a
        dashboard can join straight onto `genlayer_node_info`. Deliberately
        excludes the observability / Wall-of-Shame fields (metrics/logs status,
        shame timestamps) — those live on `wall-of-shame` and change often;
        this endpoint is meant to stay small and stable.

        Optional ?network=asimov|bradbury filter. Cached 60s. Public.
        """
        network = request.query_params.get('network', '').strip().lower() or None
        if network and network not in settings.TESTNET_NETWORKS:
            return Response(
                {'error': f"Unknown network '{network}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache_key = f'grafana_validators:{network or "all"}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        queryset = (
            ValidatorWallet.objects
            .select_related('operator', 'operator__user')
        )
        if network:
            queryset = queryset.filter(network=network)
        queryset = queryset.order_by('network', 'moniker', 'address')

        data = GrafanaValidatorSerializer(queryset, many=True).data
        cache.set(cache_key, data, 60)
        return Response(data)

    @action(detail=False, methods=['get'], url_path='wall-of-shame')
    def wall_of_shame(self, request):
        """
        Public Wall of Shame: active validators grouped by operator with their
        latest per-network metrics/logs/version reasons. Cached for 60s.
        Optional ?network=asimov|bradbury filter.
        """
        network = request.query_params.get('network', '').strip().lower() or None
        if network and network not in settings.TESTNET_NETWORKS:
            return Response(
                {'error': f"Unknown network '{network}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache_key = self._wall_of_shame_cache_key(network)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        queryset = (
            ValidatorWallet.objects
            .select_related('operator', 'operator__user')
            .filter(status='active')
        )
        if network:
            queryset = queryset.filter(network=network)

        # Keep wallet ordering stable for the compatibility `wallets` payload.
        from django.db.models import Case, IntegerField, Value, When
        from django.db.models.functions import Lower

        queryset = queryset.annotate(
            shame_priority=Case(
                When(metrics_status='shame', then=Value(0)),
                When(logs_status='shame', then=Value(0)),
                When(metrics_status='unknown', then=Value(1)),
                When(logs_status='unknown', then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            ),
            moniker_lower=Lower('moniker'),
        ).order_by('shame_priority', 'moniker_lower', 'address')

        # Pick the latest Grafana check timestamp across all returned rows so
        # the UI can show staleness of the data itself (not per-validator).
        wallets = list(queryset)
        now = timezone.now()

        from contributions.node_upgrade.models import TargetNodeVersion
        targets = {
            network_name: TargetNodeVersion.get_active(network=network_name)
            for network_name in settings.TESTNET_NETWORKS.keys()
        }
        self._sync_shame_started_at(wallets, targets, now)

        last_check = max(
            (w.last_grafana_check_at for w in wallets if w.last_grafana_check_at is not None),
            default=None,
        )

        # Consecutive "not shamed" uptime streaks, from the stored daily rollup.
        # One snapshot query for every wallet on the page, then compute in memory.
        snapshot_index = streaks_lib.load_snapshot_index([w.id for w in wallets], now)
        streaks_by_wallet_id = {
            w.id: streaks_lib.clean_streak([w.id], now, snapshot_index)
            for w in wallets
        }

        serializer = WallOfShameSerializer(
            wallets, many=True,
            context={'streaks_by_wallet_id': streaks_by_wallet_id},
        )
        validators = self._build_validator_groups(
            wallets, targets, now, snapshot_index, streaks_by_wallet_id,
        )
        on_count = sum(1 for validator in validators if validator['status'] == 'on')
        shame_count = sum(1 for validator in validators if validator['status'] == 'shame')
        warning_count = sum(1 for validator in validators if validator['status'] == 'warning')
        unknown_count = sum(1 for validator in validators if validator['status'] == 'unknown')

        payload = {
            'wallets': serializer.data,
            'validators': validators,
            'stats': {
                'total': len(validators),
                'on': on_count,
                'shame': shame_count,
                'warning': warning_count,
                'unknown': unknown_count,
            },
            'last_grafana_check_at': last_check,
            'network': network or 'all',
        }
        cache.set(cache_key, payload, self.WALL_OF_SHAME_CACHE_TTL_SECONDS)
        return Response(payload)
