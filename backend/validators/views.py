import logging
import re
import uuid
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Min, Q, Count
from django.db import IntegrityError, transaction
from django.conf import settings
from django.utils import timezone
from .models import SyncLock, Validator, ValidatorWallet
from .serializers import ValidatorWalletSerializer, LightValidatorWalletSerializer
from .permissions import IsCronToken
from .genlayer_validators_service import GenLayerValidatorsService
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
    
    def get_permissions(self):
        """
        Allow read-only access without authentication for public endpoints.
        """
        if self.action in ['newest_validators']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def my_profile(self, request):
        """
        Get or update current user's validator profile.
        """
        if request.method == 'GET':
            try:
                validator = Validator.objects.get(user=request.user)
                serializer = self.get_serializer(validator)
                return Response(serializer.data)
            except Validator.DoesNotExist:
                return Response(
                    {'detail': 'Validator profile not found for current user.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        elif request.method == 'PATCH':
            validator, created = Validator.objects.get_or_create(user=request.user)
            serializer = self.get_serializer(validator, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
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

        # Get all validators with their first uptime contribution
        # Similar to ActiveValidatorsView query
        validators_with_first_uptime = (
            Contribution.objects
            .filter(contribution_type=uptime_type)
            .values('user', 'user__address', 'user__name')
            .annotate(
                first_uptime_date=Min('contribution_date')
            )
            .order_by('-first_uptime_date')[:limit]
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

    @action(detail=False, methods=['post'], url_path='link-by-operator')
    def link_by_operator(self, request):
        """
        Link validator wallets to the current user by operator address.
        Only available for validators who don't have any wallets linked yet.
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

        # Find wallets with this operator_address
        wallets = ValidatorWallet.objects.filter(operator_address__iexact=operator_address)

        if not wallets.exists():
            return Response(
                {'error': 'No validator wallets found for this operator address'},
                status=status.HTTP_404_NOT_FOUND
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
    SYNC_LOCK_STALE_AFTER_SECONDS = 1800
    SYNC_LOCK_HEARTBEAT_INTERVAL_SECONDS = 60

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
    def _ensure_sync_lock_row(cls):
        try:
            SyncLock.objects.get_or_create(name=cls.SYNC_LOCK_NAME)
        except IntegrityError:
            # Another request created the singleton row first.
            pass

    @classmethod
    def _acquire_sync_lock(cls):
        cls._ensure_sync_lock_row()

        with transaction.atomic():
            now = timezone.now()
            lock_row = (
                SyncLock.objects
                .select_for_update()
                .get(name=cls.SYNC_LOCK_NAME)
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
                    "Stale sync lock detected (%ss since last heartbeat), force-reclaiming",
                    f"{secs:.0f}",
                )

            lock_token = uuid.uuid4().hex
            lock_row.owner_token = lock_token
            lock_row.acquired_at = now
            lock_row.heartbeat_at = now
            lock_row.released_at = None
            lock_row.save(update_fields=['owner_token', 'acquired_at', 'heartbeat_at', 'released_at'])

        return lock_token, None

    @classmethod
    def _refresh_sync_lock(cls, lock_token):
        refreshed = (
            SyncLock.objects
            .filter(name=cls.SYNC_LOCK_NAME, owner_token=lock_token)
            .update(heartbeat_at=timezone.now())
        )
        if not refreshed:
            logger.warning("Skipped sync lock heartbeat because ownership changed")
        return bool(refreshed)

    @classmethod
    def _release_sync_lock(cls, lock_token):
        now = timezone.now()
        released = (
            SyncLock.objects
            .filter(name=cls.SYNC_LOCK_NAME, owner_token=lock_token)
            .update(owner_token=None, heartbeat_at=now, released_at=now)
        )
        if not released:
            logger.warning("Skipped sync lock release because ownership changed")

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
    def stats(self, request):
        """
        Lightweight endpoint returning validator wallet status counts per network.
        No wallet data is serialized — just aggregated counts.
        """
        network_breakdown = ValidatorWallet.objects.values(
            'network', 'status'
        ).annotate(count=Count('id')).order_by('network', 'status')

        network_stats = {}
        for entry in network_breakdown:
            net = entry['network']
            if net not in network_stats:
                network_stats[net] = {
                    'total': 0, 'active': 0,
                    'quarantined': 0, 'banned': 0, 'inactive': 0,
                }
            network_stats[net][entry['status']] = entry['count']
            network_stats[net]['total'] += entry['count']

        return Response({'network_stats': network_stats})

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
