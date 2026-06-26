from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.db.models import Sum, Q
from .models import BanAppeal, User
from .serializers import (
    BanAppealSerializer, UserSerializer,
    UserProfileUpdateSerializer, PublicUserListSerializer,
)
from .cloudinary_service import CloudinaryService
from .genlayer_service import GenLayerDeploymentService
from contributions.models import Contribution
from leaderboard.models import LeaderboardEntry
from poaps.views import UserPoapMixin
from web3 import Web3
import secrets
import string

from tally.middleware.logging_utils import get_app_logger
from tally.middleware.tracing import trace_external

logger = get_app_logger('users')


class UserViewSet(UserPoapMixin, viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows users to be viewed.
    Users with visible=False are excluded from the queryset,
    except for the authenticated user viewing their own profile.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'address'  # Change default lookup field from 'pk' to 'address'
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['date_joined', 'created_at']
    public_highlights_default_limit = 5
    public_highlights_max_limit = 20

    def _parse_public_limit(self, default, max_limit):
        raw_limit = self.request.query_params.get('limit', default)
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            return None, Response(
                {'detail': 'limit must be a non-negative integer.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if limit < 0:
            return None, Response(
                {'detail': 'limit must be a non-negative integer.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return min(limit, max_limit), None

    def get_permissions(self):
        public_actions = {'retrieve', 'by_address', 'user_highlights', 'search'}
        if self.action in public_actions:
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_throttles(self):
        action = getattr(self, 'action', None)
        if action in {'retrieve', 'by_address', 'user_highlights'}:
            self.throttle_scope = 'public_user_profile'
        elif action == 'search':
            self.throttle_scope = 'public_user_search'
        else:
            self.throttle_scope = None
        return super().get_throttles()

    def _can_view_user(self, user):
        request_user = self.request.user
        return bool(
            user.visible
            or (
                request_user.is_authenticated
                and (request_user.id == user.id or request_user.is_staff)
            )
        )

    def get_queryset(self):
        """
        Public user collections should only include visible profiles.
        Staff can still inspect all users; users access their own hidden profile
        through /users/me/ rather than through the public directory.
        """
        queryset = User.objects.all()
        request_user = self.request.user

        if request_user.is_authenticated and request_user.is_staff:
            return queryset

        return queryset.filter(visible=True)
    
    def get_object(self):
        """
        Override to use case-insensitive address lookup and allow users to access 
        their own profile even if they're marked as not visible.
        """
        lookup_value = self.kwargs[self.lookup_field]  # Gets address from URL
        obj = get_object_or_404(User, address__iexact=lookup_value)  # Case-insensitive
        
        if not self._can_view_user(obj):
            raise Http404
        return obj
        
    def get_serializer_context(self):
        """
        Add context flags to control serializer behavior.
        Use lightweight serializers for list views, full serializers for detail views.
        """
        context = super().get_serializer_context()
        # Use light serializers for list view, full for detail/by_address
        context['use_light_serializers'] = self.action == 'list'
        # Referral breakdowns belong on owner-only endpoints such as /users/me/.
        context['include_referral_details'] = False
        context['public_profile'] = self.action in ['retrieve', 'by_address']
        return context

    @action(detail=False, methods=['get'], url_path='by-address/(?P<address>[^/.]+)')
    def by_address(self, request, address=None):
        """
        Get a user by their Ethereum wallet address
        """
        user = get_object_or_404(
            User.objects.select_related('validator', 'builder', 'steward', 'creator'),
            address__iexact=address
        )

        if not self._can_view_user(user):
            raise Http404

        # Override context for by_address to include full details
        context = self.get_serializer_context()
        context['use_light_serializers'] = False
        context['include_referral_details'] = False
        serializer = self.get_serializer(user, context=context)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='by-address/(?P<address>[^/.]+)/highlights')
    def user_highlights(self, request, address=None):
        """
        Get highlights for a specific user by their address, optionally filtered by category
        """
        from contributions.models import ContributionHighlight, Category
        from contributions.serializers import ContributionHighlightSerializer

        user = get_object_or_404(User, address__iexact=address)
        if not self._can_view_user(user):
            raise Http404

        limit, error_response = self._parse_public_limit(
            self.public_highlights_default_limit,
            self.public_highlights_max_limit,
        )
        if error_response is not None:
            return error_response
        category = request.query_params.get('category')

        # Build the queryset for filtering
        queryset = ContributionHighlight.objects.filter(contribution__user=user)

        # Filter by category if provided
        if category and category != 'global':
            category_obj = get_object_or_404(Category, slug=category)
            queryset = queryset.filter(contribution__contribution_type__category=category_obj)

        # Order by featured date (newest first), then contribution date.
        queryset = queryset.order_by('-created_at', '-contribution__contribution_date')
        queryset = queryset.select_related(
            'contribution',
            'contribution__user',
            'contribution__contribution_type'
        )

        highlights = queryset[:limit]
        serializer = ContributionHighlightSerializer(highlights, many=True)
        return Response(serializer.data)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PublicUserListSerializer
        return UserSerializer
        
    @action(detail=False, methods=['get', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """
        Get or update the authenticated user's profile.
        Users can always see their own profile regardless of visibility setting.
        For PATCH requests, only the name field can be updated.
        """
        if request.method == 'GET':
            # For /users/me/, include full details including referral_details
            context = self.get_serializer_context()
            context['use_light_serializers'] = False
            context['include_referral_details'] = True
            serializer = self.get_serializer(request.user, context=context)
            return Response(serializer.data)
        elif request.method == 'PATCH':
            serializer = UserProfileUpdateSerializer(request.user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                # Return the full user data after update with full details
                context = self.get_serializer_context()
                context['use_light_serializers'] = False
                context['include_referral_details'] = True
                full_serializer = self.get_serializer(request.user, context=context)
                return Response(full_serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated],
            parser_classes=[MultiPartParser, FormParser])
    def upload_profile_image(self, request):
        """
        Upload and update user's profile image.
        Expects a multipart form with 'image' field.
        """
        if 'image' not in request.FILES:
            return Response(
                {'error': 'No image file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        image = request.FILES['image']
        
        # Validate file size (10MB max)
        if image.size > 10 * 1024 * 1024:
            return Response(
                {'error': 'File size must be less than 10MB'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if image.content_type not in allowed_types:
            return Response(
                {'error': 'Invalid file type. Allowed: JPEG, PNG, WebP'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Delete old image if exists
            if request.user.profile_image_public_id:
                CloudinaryService.delete_image(request.user.profile_image_public_id)
            
            # Upload new image
            result = CloudinaryService.upload_profile_image(image, request.user.id)
            
            # Update user model
            request.user.profile_image_url = result['url']
            request.user.profile_image_public_id = result['public_id']
            request.user.save()
            
            serializer = self.get_serializer(request.user)
            return Response({
                'message': 'Profile image uploaded successfully',
                'profile_image_url': result['url'],
                'user': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Profile image upload failed: {str(e)}")
            return Response(
                {'error': 'Failed to upload image'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated],
            parser_classes=[MultiPartParser, FormParser])
    def upload_banner_image(self, request):
        """
        Upload and update user's banner image.
        Expects a multipart form with 'image' field.
        """
        if 'image' not in request.FILES:
            return Response(
                {'error': 'No image file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        image = request.FILES['image']
        
        # Validate file size (10MB max)
        if image.size > 10 * 1024 * 1024:
            return Response(
                {'error': 'File size must be less than 10MB'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if image.content_type not in allowed_types:
            return Response(
                {'error': 'Invalid file type. Allowed: JPEG, PNG, WebP'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Delete old image if exists
            if request.user.banner_image_public_id:
                CloudinaryService.delete_image(request.user.banner_image_public_id)
            
            # Upload new image
            result = CloudinaryService.upload_banner_image(image, request.user.id)
            
            # Update user model
            request.user.banner_image_url = result['url']
            request.user.banner_image_public_id = result['public_id']
            request.user.save()
            
            serializer = self.get_serializer(request.user)
            return Response({
                'message': 'Banner image uploaded successfully',
                'banner_image_url': result['url'],
                'user': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Banner image upload failed: {str(e)}")
            return Response(
                {'error': 'Failed to upload image'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def cloudinary_config(self, request):
        """
        Get Cloudinary configuration for direct browser uploads.
        """
        image_type = request.query_params.get('type', 'profile')
        
        if image_type not in ['profile', 'banner']:
            return Response(
                {'error': 'Invalid image type. Must be "profile" or "banner"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            config = CloudinaryService.get_upload_preset(image_type)
            return Response(config)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Registration will be handled by MetaMask authentication
    
    def _get_web3_contract(self):
        """
        Helper method to create a Web3 contract instance
        """
        # Connect to the blockchain using environment variables
        w3 = Web3(Web3.HTTPProvider(settings.VALIDATOR_RPC_URL))
        
        # Contract address from network config (Asimov - this endpoint is Asimov-only)
        contract_address = settings.TESTNET_NETWORKS['asimov']['staking_contract_address']
        
        # Minimal ABI for the validators functions
        abi = [
            {
                'inputs': [],
                'name': 'getValidatorsAtCurrentEpoch',
                'outputs': [{'type': 'address[]', 'name': ''}],
                'stateMutability': 'view',
                'type': 'function'
            },
            {
                'inputs': [],
                'name': 'getAllBannedValidators',
                'outputs': [{'type': 'address[]', 'name': ''}],
                'stateMutability': 'view',
                'type': 'function'
            },
            {
                'inputs': [],
                'name': 'getValidatorBansCount',
                'outputs': [{'type': 'uint256', 'name': ''}],
                'stateMutability': 'view',
                'type': 'function'
            },
            {
                'inputs': [{'type': 'uint256', 'name': 'index'}],
                'name': 'validatorsBanned',
                'outputs': [{'type': 'address', 'name': ''}],
                'stateMutability': 'view',
                'type': 'function'
            }
        ]
        
        # Create contract instance
        return w3.eth.contract(address=contract_address, abi=abi)
    
    def _mark_journey_started(self, request, role):
        """Mark a role journey as started with a 0-point `<role>-welcome` marker.

        Point-free (not farmable) and idempotent. `role` in {builder, validator,
        community}. The marker persists "journey started" across sessions; points
        come only from the journey's verifiable tasks. This is the lightweight
        "entered the journey" signal, distinct from a role's deeper commitments
        (validator waitlist, becoming a creator), which keep their own rows.
        """
        from contributions.models import Contribution, ContributionType, Category
        from django.utils import timezone

        role_welcome = {
            'builder': ('builder-welcome', 'builder', 'Builder Welcome'),
            'validator': ('validator-welcome', 'validator', 'Validator Welcome'),
            'community': ('community-welcome', 'community', 'Community Welcome'),
        }
        if role not in role_welcome:
            return Response(
                {'error': "role must be one of: builder, validator, community"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        slug, category_slug, name = role_welcome[role]
        user = request.user
        category = Category.objects.filter(slug=category_slug).first()
        welcome_type, _ = ContributionType.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name,
                'description': f'Started the {role} journey',
                'category': category,
                'is_submittable': False,
                'min_points': 0,
                'max_points': 0,
            },
        )

        from django.db import transaction
        from django.contrib.auth import get_user_model
        from leaderboard.models import GlobalLeaderboardMultiplier

        with transaction.atomic():
            # Lock the user row to serialize concurrent requests
            get_user_model().objects.select_for_update().get(pk=user.pk)

            if Contribution.objects.filter(user=user, contribution_type=welcome_type).exists():
                serializer = self.get_serializer(user)
                return Response({
                    'message': f'{role} journey already started',
                    'user': serializer.data
                }, status=status.HTTP_200_OK)

            # Contribution.clean() requires an active multiplier for the type, even
            # for a 0-point marker. Ensure one exists (value is irrelevant at 0 pts).
            # Lock the shared type row so concurrent requests for DIFFERENT users
            # can't both pass the exists() check and duplicate the default row.
            ContributionType.objects.select_for_update().get(pk=welcome_type.pk)
            if not GlobalLeaderboardMultiplier.objects.filter(contribution_type=welcome_type).exists():
                GlobalLeaderboardMultiplier.objects.create(
                    contribution_type=welcome_type,
                    multiplier_value=1.0,
                    valid_from=timezone.now() - timezone.timedelta(days=30),
                    description=f'Default multiplier for {name} (0-point started marker)',
                    notes='Applied when users start a role journey',
                )

            # ponytail: 0-point marker only — "started", not a reward.
            Contribution.objects.create(
                user=user,
                contribution_type=welcome_type,
                points=0,
                contribution_date=timezone.now(),
                notes=f'Started the {role} journey',
            )

        serializer = self.get_serializer(user)
        return Response({
            'message': f'{role} journey started',
            'user': serializer.data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def start_builder_journey(self, request):
        """Mark the builder journey as started, point-free. See _mark_journey_started."""
        return self._mark_journey_started(request, 'builder')

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def start_role_journey(self, request):
        """Mark any role journey as started, point-free. `role` in {builder, validator, community}."""
        role = (request.data.get('role') or '').strip().lower()
        return self._mark_journey_started(request, role)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def start_validator_journey(self, request):
        """
        Award the validator waitlist contribution to start the validator journey.
        This gives the user their first contribution without checking other requirements.
        """
        from contributions.models import Contribution, ContributionType
        from django.utils import timezone
        
        user = request.user
        started_response = self._mark_journey_started(request, 'validator')
        if started_response.status_code >= 400:
            return started_response
        
        # Check if user already has the contribution
        try:
            waitlist_type = ContributionType.objects.get(slug='validator-waitlist')
        except ContributionType.DoesNotExist:
            return Response(
                {'error': 'Validator waitlist contribution type not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        if Contribution.objects.filter(user=user, contribution_type=waitlist_type).exists():
            return Response(
                {'message': 'You already have the validator waitlist contribution'},
                status=status.HTTP_200_OK
            )
        
        # Create the contribution to start the journey
        try:
            contribution = Contribution.objects.create(
                user=user,
                contribution_type=waitlist_type,
                points=0,
                contribution_date=timezone.now(),
                notes='Joined the validator waitlist'
            )
            
            serializer = self.get_serializer(user)
            return Response({
                'message': 'Validator journey started successfully!',
                'user': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to start journey: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def complete_builder_journey(self, request):
        """
        Grant the Builder role once the journey is done.

        The journey is POINT-FREE: becoming a Builder awards no points. The old
        `builder` (+50) contribution was self-serve and farmable, so it was
        removed. Points come only from the verifiable task inside the journey
        (starring the boilerplate repo, a builder-category social task).

        Requirement: the user has completed the boilerplate-star social task
        (`settings.BUILDER_JOURNEY_TASK_SLUG`), which itself requires a linked
        GitHub account and a real star. That single check subsumes "connect
        GitHub and star the repo".
        """
        from django.conf import settings
        from builders.models import Builder
        from social_tasks.models import SocialTaskCompletion

        user = request.user

        # Idempotent: already a Builder.
        if hasattr(user, 'builder'):
            serializer = self.get_serializer(user)
            return Response({
                'message': 'You are already a GenLayer Builder',
                'user': serializer.data
            }, status=status.HTTP_200_OK)

        # ponytail: role gate is the boilerplate-star task by slug. Renaming or
        # deactivating that task blocks completion until it's restored.
        starred = SocialTaskCompletion.objects.filter(
            user=user, task__slug=settings.BUILDER_JOURNEY_TASK_SLUG
        ).exists()
        if not starred:
            return Response(
                {'error': 'Finish the builder journey first: connect GitHub and star the boilerplate repository.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from django.db import transaction
            from django.contrib.auth import get_user_model

            with transaction.atomic():
                # Lock the user row so two concurrent requests can't both pass
                # the hasattr check above and race into a OneToOne IntegrityError.
                get_user_model().objects.select_for_update().get(pk=user.pk)
                _, created = Builder.objects.get_or_create(user=user)

                if created:
                    # Recalculate leaderboard entries now that the Builder relation
                    # exists. The grant itself adds no points, but builder-category
                    # aggregation keys off the Builder profile being present.
                    from leaderboard.models import update_user_leaderboard_entries
                    fresh_user = type(user).objects.get(pk=user.pk)
                    update_user_leaderboard_entries(fresh_user)

            serializer = self.get_serializer(user)
            return Response({
                'message': 'Welcome to GenLayer Builders!',
                'user': serializer.data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to complete builder journey: {str(e)}")
            return Response(
                {'error': f'Failed to complete journey: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _award_social_link_points(self, request, *, slug, connection_attr, label, oauth_label):
        """Award the configured points for linking a social account.

        Idempotent, and locks the user row so concurrent calls can't double-award.
        `label` is the display name (X / Discord / GitHub); `oauth_label` is the
        name shown in the connect prompt (X uses "X (Twitter)").
        """
        from contributions.models import Contribution, ContributionType
        from django.utils import timezone
        from django.db import transaction

        user = request.user

        try:
            link_type = ContributionType.objects.get(slug=slug)
        except ContributionType.DoesNotExist:
            return Response(
                {'error': f'Community link {label} contribution type not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not hasattr(user, connection_attr):
            return Response(
                {'error': f'You must link your {oauth_label} account first'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # Lock the user row to serialize concurrent requests
                from django.contrib.auth import get_user_model
                get_user_model().objects.select_for_update().get(pk=user.pk)

                if Contribution.objects.filter(user=user, contribution_type=link_type).exists():
                    return Response(
                        {'message': f'You already earned points for linking your {label} account'},
                        status=status.HTTP_200_OK
                    )

                from leaderboard.models import GlobalLeaderboardMultiplier
                # Lock the shared type row so concurrent requests for DIFFERENT users
                # can't both pass the exists() check and duplicate the default row.
                ContributionType.objects.select_for_update().get(pk=link_type.pk)
                if not GlobalLeaderboardMultiplier.objects.filter(contribution_type=link_type).exists():
                    GlobalLeaderboardMultiplier.objects.create(
                        contribution_type=link_type,
                        multiplier_value=1.0,
                        valid_from=timezone.now() - timezone.timedelta(days=30),
                        description=f'Default multiplier for Community Link {label} contributions',
                        notes=f'Applied when users link their {label} account'
                    )

                Contribution.objects.create(
                    user=user,
                    contribution_type=link_type,
                    points=link_type.min_points,
                    contribution_date=timezone.now(),
                    notes=f'Linked {oauth_label} account to GenLayer profile'
                )

            serializer = self.get_serializer(user)
            return Response({
                'message': f'{label} account linked successfully! {link_type.min_points} points awarded.',
                'user': serializer.data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to award {label} link points: {str(e)}")
            return Response(
                {'error': 'Failed to award points. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def link_x_account(self, request):
        """Award points for linking an X (Twitter) account (verified via OAuth)."""
        return self._award_social_link_points(
            request,
            slug='community-link-x',
            connection_attr='twitterconnection',
            label='X',
            oauth_label='X (Twitter)',
        )

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def link_discord_account(self, request):
        """Award points for linking a Discord account (verified via OAuth)."""
        return self._award_social_link_points(
            request,
            slug='community-link-discord',
            connection_attr='discordconnection',
            label='Discord',
            oauth_label='Discord',
        )

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def link_github_account(self, request):
        """Award points for linking a GitHub account (verified via OAuth)."""
        return self._award_social_link_points(
            request,
            slug='community-link-github',
            connection_attr='githubconnection',
            label='GitHub',
            oauth_label='GitHub',
        )

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def community_journey(self, request):
        """Community journey status: the 5 steps + completion + membership."""
        from creators import community_journey as cj
        return Response(cj.journey_status(request.user), status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def verify_community_post(self, request):
        """Step 5: verify the user's X post (tags GenLayer + contains their code).

        The post must be a well-formed X post URL from the user's linked X
        account; we read its text via Sorsa /tweet-info and check the pattern.
        """
        from creators import community_journey as cj
        from creators.models import CommunityPostProof
        from contributions.url_utils import get_user_social_handle, normalize_url
        from social_tasks.sorsa_client import get_default_client, SorsaError

        user = request.user
        post_url = (request.data.get('post_url') or '').strip()
        if not post_url:
            return Response(
                {'error': 'missing_url', 'message': 'Provide the URL of your X post.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # The post must come from the user's linked X account.
        if not hasattr(user, 'twitterconnection'):
            return Response(
                {'error': 'x_not_linked', 'message': 'Link your X account first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        post_url = normalize_url(post_url)
        url_handle, tweet_id = cj.parse_x_post(post_url)
        if not tweet_id:
            return Response(
                {'error': 'invalid_url', 'message': 'That is not a valid X post URL.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        linked_handle = get_user_social_handle(user, 'twitter')
        if not linked_handle:
            # twitterconnection exists but carries no handle: cannot verify
            # ownership, so fail closed rather than skip the check.
            return Response(
                {'error': 'x_not_linked', 'message': 'Reconnect your X account and try again.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if url_handle != linked_handle:
            return Response(
                {'error': 'account_mismatch', 'message': 'The post must come from your linked X account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            tweet = get_default_client().get_tweet(tweet_id)
        except SorsaError as exc:
            logger.warning(f"Sorsa tweet-info failed: {exc}")
            return Response(
                {'error': 'verification_unavailable', 'message': 'Could not verify your post right now. Please try again shortly.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if tweet is None:
            return Response(
                {'error': 'post_not_found', 'message': 'We could not find that post. Make sure it is public and the URL is correct.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Authoritative author check (Sorsa) against the linked handle. Fail
        # closed: an absent/empty author must not pass the check.
        author = (tweet['username'] or '').lower()
        if not author:
            return Response(
                {'error': 'verification_unavailable', 'message': 'Could not verify your post right now. Please try again shortly.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if author != linked_handle:
            return Response(
                {'error': 'account_mismatch', 'message': 'The post must come from your linked X account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ok, error_code = cj.post_matches(tweet['full_text'], user)
        if not ok:
            message = (
                f"Your post must @mention @{cj.genlayer_handle()}."
                if error_code == 'tag_missing'
                else 'Your post must include your verification code exactly as shown.'
            )
            return Response({'error': error_code, 'message': message}, status=status.HTTP_400_BAD_REQUEST)

        CommunityPostProof.objects.update_or_create(
            user=user,
            defaults={'post_url': post_url, 'tweet_id': tweet_id},
        )
        return Response(
            {'status': 'verified', 'journey': cj.journey_status(user)},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def complete_community_journey(self, request):
        """Grant the Creator (community) role once all 5 journey steps are done.
        Point-free (steps 1-4 keep their own points)."""
        from creators import community_journey as cj
        from creators.models import Creator
        from leaderboard.models import update_user_leaderboard_entries

        user = request.user

        # Existing members are grandfathered in: the journey only applies to
        # newcomers, so never funnel a Creator back through the steps.
        if hasattr(user, 'creator'):
            return Response(
                {'message': 'You are already a community member', 'user': self.get_serializer(user).data},
                status=status.HTTP_200_OK,
            )

        journey = cj.journey_status(user)
        if not journey['started']:
            return Response(
                {
                    'error': 'not_started',
                    'missing_steps': ['start'],
                    'message': 'Start the community journey first.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not journey['complete']:
            return Response(
                {
                    'error': 'incomplete',
                    'missing_steps': journey['missing_steps'],
                    'message': 'Complete all community journey steps first.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.db import transaction
        from django.contrib.auth import get_user_model

        with transaction.atomic():
            # Lock the user row so two concurrent requests can't both pass the
            # hasattr check above and race into a OneToOne IntegrityError.
            get_user_model().objects.select_for_update().get(pk=user.pk)
            _, created = Creator.objects.get_or_create(user=user)

            if not created:
                return Response(
                    {'message': 'You are already a community member', 'user': self.get_serializer(user).data},
                    status=status.HTTP_200_OK,
                )

            fresh_user = type(user).objects.get(pk=user.pk)
            update_user_leaderboard_entries(fresh_user)

        return Response(
            {'message': 'Welcome to the GenLayer community!', 'user': self.get_serializer(fresh_user).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'])
    def validators(self, request):
        """
        Get the list of active validators from the GenLayer contract
        """
        try:
            # Create contract instance
            contract = self._get_web3_contract()
            
            # Call getValidatorsAtCurrentEpoch function
            validators = contract.functions.getValidatorsAtCurrentEpoch().call()
            
            # Filter out invalid addresses (0x0, 0x000, etc.)
            # Keep original case from blockchain but ensure consistent format
            valid_validators = [
                addr for addr in validators 
                if addr and 
                addr.lower() not in ['0x0', '0x000', '0x0000000000000000000000000000000000000000']
            ]
            
            # Return the filtered list of addresses (keeping original case from blockchain)
            return Response(valid_validators, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def check_deployments(self, request):
        """
        Check if the authenticated user has deployed any contracts on GenLayer Studio.
        Returns deployment status and contract details if any deployments are found.
        """
        user = request.user
        
        # Check if user has a wallet address
        if not user.address:
            return Response({
                'has_deployments': False,
                'deployments': [],
                'error': 'No wallet address associated with this account'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Initialize GenLayer service
            genlayer_service = GenLayerDeploymentService()
            
            # Convert address to checksum format for GenLayer API
            from web3 import Web3
            checksum_address = Web3.to_checksum_address(user.address)
            
            # Check for deployments
            deployment_result = genlayer_service.get_user_deployments(checksum_address)
            
            logger.debug(f"Deployment check: {deployment_result.get('deployment_count', 0)} deployments found")
            
            return Response(deployment_result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error checking deployments: {str(e)}")
            return Response({
                'has_deployments': False,
                'deployments': [],
                'error': 'Failed to check deployments. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def deployment_status(self, request):
        """
        Get a simplified deployment status for the authenticated user.
        Useful for quick checks without detailed deployment information.
        """
        user = request.user
        
        if not user.address:
            return Response({
                'has_deployments': False,
                'message': 'No wallet address associated with this account'
            })
        
        try:
            genlayer_service = GenLayerDeploymentService()
            
            # Convert address to checksum format for GenLayer API
            from web3 import Web3
            checksum_address = Web3.to_checksum_address(user.address)
            
            deployment_result = genlayer_service.get_user_deployments(checksum_address)
            
            return Response({
                'has_deployments': deployment_result.get('has_deployments', False),
                'deployment_count': deployment_result.get('deployment_count', 0),
                'wallet_address': user.address
            })
            
        except Exception as e:
            logger.error(f"Error checking deployment status: {str(e)}")
            return Response({
                'has_deployments': False,
                'deployment_count': 0,
                'error': 'Failed to check deployment status'
            })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def referral_points(self, request):
        """
        Quick endpoint for referral points only.
        Used by Waitlist.svelte and other summary views.
        """
        from leaderboard.models import ReferralPoints

        try:
            rp = request.user.referral_points
            return Response({
                'builder_points': rp.builder_points,
                'validator_points': rp.validator_points
            })
        except ReferralPoints.DoesNotExist:
            return Response({
                'builder_points': 0,
                'validator_points': 0
            })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def referrals(self, request):
        """Full referral details. Used by Referrals page."""
        from leaderboard.models import get_referral_breakdown
        return Response(get_referral_breakdown(request.user))

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def search(self, request):
        """Search visible users by public identifiers."""
        query = request.query_params.get('q', '').strip()

        if len(query) < 2:
            return Response([])

        search_query = (
            Q(name__icontains=query) |
            Q(address__icontains=query) |
            Q(twitter_handle__icontains=query) |
            Q(discord_handle__icontains=query) |
            Q(telegram_handle__icontains=query) |
            Q(githubconnection__platform_username__icontains=query)
        )

        users = User.objects.filter(search_query).filter(visible=True)[:10]

        return Response([
            {
                'id': user.id,
                'name': user.name,
                'address': user.address,
                'profile_image_url': user.profile_image_url
            }
            for user in users
        ])

    @action(detail=False, methods=['get', 'post'], permission_classes=[IsAuthenticated],
            url_path='me/appeal')
    def appeal(self, request):
        """
        GET: Get current ban appeal status (if any).
        POST: Submit a one-time ban appeal. Only allowed if user is banned
              and has not already submitted an appeal.
        """
        if request.method == 'GET':
            appeal = BanAppeal.objects.filter(user=request.user).first()
            if appeal is None:
                return Response(
                    {'appeal': None, 'can_appeal': request.user.is_banned},
                )
            serializer = BanAppealSerializer(appeal)
            return Response({
                'appeal': serializer.data,
                'can_appeal': False,
            })

        # POST — submit appeal
        if not request.user.is_banned:
            return Response(
                {'error': 'Your account is not banned.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if BanAppeal.objects.filter(user=request.user).exists():
            return Response(
                {'error': 'You have already submitted an appeal. '
                          'Each user may only appeal once.'},
                status=status.HTTP_409_CONFLICT,
            )

        appeal_text = request.data.get('appeal_text', '').strip()
        if not appeal_text:
            return Response(
                {'error': 'Please provide an explanation for your appeal.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        appeal = BanAppeal.objects.create(
            user=request.user,
            appeal_text=appeal_text,
        )
        serializer = BanAppealSerializer(appeal)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
