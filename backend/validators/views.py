import re
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Min, Q, Count
from django.conf import settings
from .models import Validator, ValidatorWallet
from .serializers import ValidatorWalletSerializer, LightValidatorWalletSerializer
from .permissions import IsCronToken
from .genlayer_validators_service import GenLayerValidatorsService
from users.models import User
from users.serializers import ValidatorSerializer, UserSerializer
from contributions.models import Contribution, ContributionType


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
                user_data['first_uptime_date'] = validator['first_uptime_date']
                result.append(user_data)
            else:
                # Fallback to simple data if user not found
                result.append({
                    'address': validator['user__address'],
                    'name': validator['user__name'],
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

    def get_queryset(self):
        """
        Optionally filter by operator address or status.
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

        return queryset

    def list(self, request, *args, **kwargs):
        """
        List all validator wallets with optional filtering.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        # Get counts
        active_count = queryset.filter(status='active').count()
        quarantined_count = queryset.filter(status='quarantined').count()
        banned_count = queryset.filter(status='banned').count()
        inactive_count = queryset.filter(status='inactive').count()

        return Response({
            'wallets': serializer.data,
            'stats': {
                'total': queryset.count(),
                'active': active_count,
                'quarantined': quarantined_count,
                'banned': banned_count,
                'inactive': inactive_count
            }
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

    @action(detail=False, methods=['post'], permission_classes=[IsCronToken], authentication_classes=[])
    def sync(self, request):
        """
        Trigger validator sync from GenLayer blockchain.
        Protected by X-Cron-Token header authentication.
        """
        try:
            service = GenLayerValidatorsService()

            # Perform sync (internally fetches active and banned validators)
            stats = service.sync_all_validators()

            # Get DB state after sync
            db_stats = ValidatorWallet.objects.values('status').annotate(
                count=Count('status')
            ).order_by('status')
            db_state = {stat['status']: stat['count'] for stat in db_stats}

            return Response({
                'success': True,
                'stats': stats,
                'db_state': db_state
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
