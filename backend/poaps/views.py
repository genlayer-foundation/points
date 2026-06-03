import re
from datetime import timezone as datetime_timezone

from django.contrib.auth import get_user_model
from django.db.models import BooleanField, Count, Exists, F, OuterRef, Prefetch, Q, Value
from django.db import transaction
from django.utils import timezone
from eth_account import Account
from eth_account.messages import encode_defunct
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ethereum_auth.models import Nonce

from .models import PoapClaim, PoapDistribution, PoapDrop
from .serializers import (
    PoapClaimSerializer,
    PoapDropDetailSerializer,
    PoapDropListSerializer,
    PoapProfileClaimSerializer,
)
from .services import (
    PoapClaimError,
    claim_with_mint_link,
    claim_with_secret,
    normalize_wallet_address,
    recover_unmatched_claims_for_wallet,
)

User = get_user_model()


def extract_message_field(message, field_name):
    prefix = f'{field_name}:'
    for line in (message or '').splitlines():
        if line.startswith(prefix):
            return line.split(':', 1)[1].strip()
    return ''


def extract_nonce(message):
    return extract_message_field(message, 'Nonce')


def is_ethereum_address(value):
    return bool(re.fullmatch(r'0x[a-fA-F0-9]{40}', value or ''))


def open_distribution_queryset(at_time=None):
    at_time = at_time or timezone.now()
    secret_distribution = (
        Q(method=PoapDistribution.METHOD_SECRET)
        & ~Q(secret_hash='')
    )
    mint_link_distribution = (
        Q(method=PoapDistribution.METHOD_MINT_LINK)
        & Q(mint_links__used_count__lt=F('mint_links__max_uses'))
        & (Q(mint_links__expires_at__isnull=True) | Q(mint_links__expires_at__gte=at_time))
    )
    return (
        PoapDistribution.objects
        .filter(
            active=True,
            drop_id=OuterRef('pk'),
        )
        .filter(Q(starts_at__isnull=True) | Q(starts_at__lte=at_time))
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gte=at_time))
        .filter(Q(max_claims__isnull=True) | Q(claimed_count__lt=F('max_claims')))
        .filter(secret_distribution | mint_link_distribution)
    )


class PoapDropViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = 'slug'
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'legacy_poap_id']
    ordering_fields = ['event_start_at', 'created_at', 'title']
    ordering = ['-event_start_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PoapDropDetailSerializer
        return PoapDropListSerializer

    def get_queryset(self):
        user = self.request.user
        now = timezone.now()
        claimed_subquery = PoapClaim.objects.filter(
            drop_id=OuterRef('pk'),
            user=user,
        ) if user.is_authenticated else PoapClaim.objects.none()
        open_distribution_subquery = open_distribution_queryset(now)

        queryset = (
            PoapDrop.objects
            .select_related('created_by')
            .annotate(
                claimed_count_value=Count(
                    'claims',
                    filter=Q(claims__user__isnull=False),
                    distinct=True,
                ),
                has_claimed_value=Exists(claimed_subquery)
                if user.is_authenticated
                else Value(False, output_field=BooleanField()),
                has_open_distribution_value=Exists(open_distribution_subquery),
            )
        )

        if not (user.is_authenticated and user.is_staff):
            queryset = queryset.exclude(status=PoapDrop.STATUS_DRAFT)

        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        month = self.request.query_params.get('month')
        if month:
            try:
                year, month_number = [int(part) for part in month.split('-', 1)]
                start = timezone.datetime(year, month_number, 1, tzinfo=datetime_timezone.utc)
                if month_number == 12:
                    end = timezone.datetime(year + 1, 1, 1, tzinfo=datetime_timezone.utc)
                else:
                    end = timezone.datetime(year, month_number + 1, 1, tzinfo=datetime_timezone.utc)
                queryset = queryset.filter(event_start_at__gte=start, event_start_at__lt=end)
            except (TypeError, ValueError):
                pass

        if self.action == 'retrieve':
            distributions = (
                PoapDistribution.objects
                .annotate(mint_link_count=Count('mint_links'))
                .order_by('-created_at')
            )
            queryset = queryset.prefetch_related(
                Prefetch('distributions', queryset=distributions, to_attr='prefetched_distributions')
            )

        return queryset

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.is_authenticated:
            instance.current_user_claim_obj = (
                PoapClaim.objects
                .filter(drop=instance, user=request.user)
                .only('id', 'claimed_at', 'claim_method', 'source')
                .first()
            )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
    def claims(self, request, slug=None):
        drop = self.get_object()
        queryset = (
            drop.claims
            .filter(user__isnull=False)
            .select_related('user')
            .order_by('-claimed_at', '-created_at')
        )
        page = self.paginate_queryset(queryset)
        serializer = PoapClaimSerializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='claim-secret', permission_classes=[permissions.IsAuthenticated])
    def claim_secret(self, request, slug=None):
        try:
            claim = claim_with_secret(
                drop_slug=slug,
                user=request.user,
                secret=request.data.get('secret', ''),
            )
        except PoapDrop.DoesNotExist:
            return Response({'error': 'POAP not found.'}, status=status.HTTP_404_NOT_FOUND)
        except PoapClaimError as exc:
            return Response({'error': str(exc)}, status=exc.status_code)

        return Response(PoapClaimSerializer(claim).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path=r'claim-link/(?P<token>[^/.]+)', permission_classes=[permissions.IsAuthenticated])
    def claim_link(self, request, token=None):
        try:
            claim = claim_with_mint_link(token=token, user=request.user)
        except PoapDrop.DoesNotExist:
            return Response({'error': 'POAP not found.'}, status=status.HTTP_404_NOT_FOUND)
        except PoapClaimError as exc:
            return Response({'error': str(exc)}, status=exc.status_code)

        return Response({
            'claim': PoapClaimSerializer(claim).data,
            'drop': PoapDropListSerializer(claim.drop, context={'request': request}).data,
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='verify-wallet', permission_classes=[permissions.IsAuthenticated])
    def verify_wallet(self, request):
        if not request.user.address:
            return Response(
                {'error': 'Your portal account does not have a wallet address.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        wallet_address = normalize_wallet_address(request.data.get('address'))
        message = request.data.get('message') or ''
        signature = request.data.get('signature') or ''

        if not wallet_address or not message or not signature:
            return Response(
                {'error': 'Address, message, and signature are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not is_ethereum_address(wallet_address):
            return Response({'error': 'Invalid wallet address.'}, status=status.HTTP_400_BAD_REQUEST)
        if 'GenLayer POAP recovery' not in message or 'will not sign you into the portal' not in message:
            return Response(
                {'error': 'Invalid recovery message.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if wallet_address not in message.lower():
            return Response(
                {'error': 'Recovery message does not include the wallet being verified.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        portal_account = normalize_wallet_address(extract_message_field(message, 'Portal Account'))
        if portal_account != normalize_wallet_address(request.user.address):
            return Response(
                {'error': 'Recovery message is not for the current portal account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        nonce_value = extract_nonce(message)
        if not nonce_value:
            return Response({'error': 'Invalid message format: No nonce found.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            try:
                nonce = Nonce.objects.select_for_update().get(value=nonce_value)
            except Nonce.DoesNotExist:
                return Response({'error': 'Invalid nonce.'}, status=status.HTTP_400_BAD_REQUEST)

            if not nonce.is_valid():
                return Response({'error': 'Invalid or expired nonce.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                recovered_address = Account.recover_message(
                    encode_defunct(text=message),
                    signature=signature,
                )
            except Exception:
                return Response({'error': 'Invalid signature.'}, status=status.HTTP_400_BAD_REQUEST)

            if normalize_wallet_address(recovered_address) != wallet_address:
                return Response(
                    {'error': 'Invalid signature: address mismatch.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            nonce.mark_as_used()

            if User.objects.filter(address__iexact=wallet_address).exclude(pk=request.user.pk).exists():
                return Response(
                    {'error': 'This wallet already belongs to another portal account.'},
                    status=status.HTTP_409_CONFLICT,
                )

            attached_to_other = (
                PoapClaim.objects
                .filter(
                    legacy_wallet_address__iexact=wallet_address,
                    user__isnull=False,
                )
                .exclude(user=request.user)
                .exists()
            )
            if attached_to_other:
                return Response(
                    {'error': 'POAPs for this wallet are already linked to another portal account.'},
                    status=status.HTTP_409_CONFLICT,
                )

            recovery_result = recover_unmatched_claims_for_wallet(request.user, wallet_address)
            attached_claims = recovery_result['attached_claims']
            skipped_existing_drop_count = recovery_result['skipped_existing_drop_count']

            if not attached_claims and (
                PoapClaim.objects
                .filter(
                    legacy_wallet_address__iexact=wallet_address,
                    user__isnull=False,
                )
                .exclude(user=request.user)
                .exists()
            ):
                return Response(
                    {'error': 'POAPs for this wallet were linked to another portal account.'},
                    status=status.HTTP_409_CONFLICT,
                )

            already_attached_count = PoapClaim.objects.filter(
                legacy_wallet_address__iexact=wallet_address,
                user=request.user,
            ).count()

        serializer = PoapProfileClaimSerializer(
            attached_claims,
            many=True,
            context={'request': request},
        )
        return Response({
            'verified_address': wallet_address,
            'attached_count': len(attached_claims),
            'skipped_existing_drop_count': skipped_existing_drop_count,
            'already_attached_count': already_attached_count,
            'attached_poaps': serializer.data,
        })


class UserPoapMixin:
    @action(
        detail=False,
        methods=['get'],
        url_path='by-address/(?P<address>[^/.]+)/poaps',
        permission_classes=[permissions.AllowAny],
    )
    def poaps(self, request, address=None):
        from django.shortcuts import get_object_or_404
        from users.models import User

        user = get_object_or_404(User, address__iexact=address)
        queryset = (
            PoapClaim.objects
            .filter(user=user)
            .select_related('drop')
            .order_by('-claimed_at', '-created_at')
        )
        page = self.paginate_queryset(queryset)
        serializer = PoapProfileClaimSerializer(
            page if page is not None else queryset,
            many=True,
            context={'request': request},
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
