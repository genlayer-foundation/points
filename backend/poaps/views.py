from datetime import timezone as datetime_timezone

from django.db.models import BooleanField, Count, Exists, F, OuterRef, Prefetch, Q, Value
from django.utils import timezone
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

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
)


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
        except Exception as exc:
            if hasattr(exc, 'status_code'):
                return Response({'error': str(exc)}, status=exc.status_code)
            return Response({'error': 'Invalid mint link.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'claim': PoapClaimSerializer(claim).data,
            'drop': PoapDropListSerializer(claim.drop, context={'request': request}).data,
        }, status=status.HTTP_201_CREATED)


class UserPoapMixin:
    @action(detail=False, methods=['get'], url_path='by-address/(?P<address>[^/.]+)/poaps')
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
