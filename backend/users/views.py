from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import User
from .serializers import UserSerializer, UserCreateSerializer, UserProfileUpdateSerializer
from .cloudinary_service import CloudinaryService
from .genlayer_service import GenLayerDeploymentService
from web3 import Web3
import logging

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows users to be viewed.
    Users with visible=False are excluded from the queryset,
    except for the authenticated user viewing their own profile.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]  # Allow read-only access without authentication
    lookup_field = 'address'  # Change default lookup field from 'pk' to 'address'
    
    def get_object(self):
        """
        Override to use case-insensitive address lookup and allow users to access 
        their own profile even if they're marked as not visible.
        """
        lookup_value = self.kwargs[self.lookup_field]  # Gets address from URL
        obj = get_object_or_404(User, address__iexact=lookup_value)  # Case-insensitive
        
        # If the user is accessing their own profile, allow it
        if self.request.user.is_authenticated and obj.id == self.request.user.id:
            return obj
        return obj
        
    @action(detail=False, methods=['get'], url_path='by-address/(?P<address>[^/.]+)')
    def by_address(self, request, address=None):
        """
        Get a user by their Ethereum wallet address
        """
        user = get_object_or_404(
            User.objects.select_related('validator', 'builder', 'steward'),
            address__iexact=address
        )
        serializer = self.get_serializer(user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='by-address/(?P<address>[^/.]+)/highlights')
    def user_highlights(self, request, address=None):
        """
        Get highlights for a specific user by their address
        """
        from contributions.models import ContributionHighlight
        from contributions.serializers import ContributionHighlightSerializer
        
        user = get_object_or_404(User, address__iexact=address)
        limit = int(request.query_params.get('limit', 5))
        
        highlights = ContributionHighlight.get_active_highlights(user=user, limit=limit)
        serializer = ContributionHighlightSerializer(highlights, many=True)
        return Response(serializer.data)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
        
    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == 'create' and 'visible' in self.request.data:
            context['visible'] = self.request.data.get('visible')
        return context
    
    @action(detail=False, methods=['get', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """
        Get or update the authenticated user's profile.
        Users can always see their own profile regardless of visibility setting.
        For PATCH requests, only the name field can be updated.
        """
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        elif request.method == 'PATCH':
            serializer = UserProfileUpdateSerializer(request.user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                # Return the full user data after update
                full_serializer = self.get_serializer(request.user)
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
            logger.error(f"Profile image upload failed for user {request.user.id}: {str(e)}")
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
            logger.error(f"Banner image upload failed for user {request.user.id}: {str(e)}")
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
        
        # Contract address from environment variables
        contract_address = settings.VALIDATOR_CONTRACT_ADDRESS
        
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
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def start_builder_journey(self, request):
        """
        Award the builder welcome contribution to start the builder journey.
        This gives the user their first contribution without checking other requirements.
        """
        from contributions.models import Contribution, ContributionType
        from django.utils import timezone
        from django.db import transaction
        
        user = request.user
        
        # Check if user already has the contribution
        try:
            welcome_type = ContributionType.objects.get(slug='builder-welcome')
        except ContributionType.DoesNotExist:
            return Response(
                {'error': 'Builder welcome contribution type not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        if Contribution.objects.filter(user=user, contribution_type=welcome_type).exists():
            return Response(
                {'message': 'You already have the builder welcome contribution'},
                status=status.HTTP_200_OK
            )
        
        # Create the contribution to start the journey
        try:
            with transaction.atomic():
                # Ensure multiplier exists for builder-welcome contribution type
                from leaderboard.models import GlobalLeaderboardMultiplier
                if not GlobalLeaderboardMultiplier.objects.filter(contribution_type=welcome_type).exists():
                    GlobalLeaderboardMultiplier.objects.create(
                        contribution_type=welcome_type,
                        multiplier_value=1.0,
                        valid_from=timezone.now() - timezone.timedelta(days=30),
                        description='Default multiplier for Builder Welcome contributions',
                        notes='Applied when users start the builder journey'
                    )
                
                contribution = Contribution.objects.create(
                    user=user,
                    contribution_type=welcome_type,
                    points=20,
                    contribution_date=timezone.now(),
                    notes='Started builder journey - welcome to the GenLayer community!'
                )
            
            serializer = self.get_serializer(user)
            return Response({
                'message': 'Builder journey started successfully!',
                'user': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Failed to start builder journey for user {user.id}: {str(e)}")
            return Response(
                {'error': f'Failed to start journey: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def start_validator_journey(self, request):
        """
        Award the validator waitlist contribution to start the validator journey.
        This gives the user their first contribution without checking other requirements.
        """
        from contributions.models import Contribution, ContributionType
        from django.utils import timezone
        
        user = request.user
        
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
                points=20,
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
        Check if user meets builder journey requirements and award the builder contribution.
        Requirements:
        1. Has at least one contribution (any type)
        2. Has testnet balance > 0
        
        Also creates Builder profile if it doesn't exist.
        """
        from contributions.models import Contribution, ContributionType
        from builders.models import Builder
        from django.utils import timezone
        from django.db import transaction
        from web3 import Web3
        import requests
        
        user = request.user
        
        # Check if user already has the BUILDER contribution (not builder-welcome)
        try:
            builder_type = ContributionType.objects.get(slug='builder')
        except ContributionType.DoesNotExist:
            # If builder contribution type doesn't exist, create it
            from contributions.models import Category
            try:
                builder_category = Category.objects.get(slug='builder')
            except Category.DoesNotExist:
                builder_category = None
            
            builder_type = ContributionType.objects.create(
                name='Builder',
                slug='builder',
                description='Awarded when becoming a GenLayer Builder',
                category=builder_category
            )
        
        if Contribution.objects.filter(user=user, contribution_type=builder_type).exists():
            # User already has the builder contribution, just ensure they have a Builder profile
            if not hasattr(user, 'builder'):
                Builder.objects.create(user=user)
            
            serializer = self.get_serializer(user)
            return Response({
                'message': 'You are already a GenLayer Builder',
                'user': serializer.data
            }, status=status.HTTP_200_OK)
        
        # Check requirement 1: Has at least one contribution
        has_contribution = Contribution.objects.filter(user=user).exists()
        if not has_contribution:
            return Response(
                {'error': 'You need at least one contribution to complete the builder journey'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check requirement 2: Has testnet balance > 0
        if not user.address:
            return Response(
                {'error': 'No wallet address associated with your account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Check testnet balance using Web3 with RPC URL from settings
            from django.conf import settings
            web3 = Web3(Web3.HTTPProvider(settings.VALIDATOR_RPC_URL))
            checksum_address = Web3.to_checksum_address(user.address)
            balance_wei = web3.eth.get_balance(checksum_address)
            balance_eth = web3.from_wei(balance_wei, 'ether')
            
            if balance_eth <= 0:
                return Response(
                    {'error': 'You need testnet tokens to complete the builder journey. Visit the faucet to get tokens.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            logger.warning(f"Failed to check balance for {user.address}: {str(e)}")
            # If we can't check balance, we'll allow proceeding (fail open)
            pass
        
        # All requirements met, create the BUILDER contribution and Builder profile atomically
        try:
            with transaction.atomic():
                # First ensure the multiplier exists for the builder contribution type
                from leaderboard.models import GlobalLeaderboardMultiplier
                if not GlobalLeaderboardMultiplier.objects.filter(contribution_type=builder_type).exists():
                    # Create a default multiplier if it doesn't exist
                    GlobalLeaderboardMultiplier.objects.create(
                        contribution_type=builder_type,
                        multiplier_value=1.0,
                        valid_from=timezone.now() - timezone.timedelta(days=30),
                        description='Default multiplier for Builder contributions',
                        notes='Applied when users complete the builder journey'
                    )
                
                # Create the BUILDER contribution (this is the actual achievement)
                contribution = Contribution.objects.create(
                    user=user,
                    contribution_type=builder_type,
                    points=50,  # Points for becoming a builder
                    contribution_date=timezone.now(),
                    notes='Became a GenLayer Builder - completed all requirements'
                )
                
                # Create Builder profile if it doesn't exist
                builder_created = False
                if not hasattr(user, 'builder'):
                    Builder.objects.create(user=user)
                    builder_created = True
            
            # Transaction successful, return response
            serializer = self.get_serializer(user)
            return Response({
                'message': 'Builder journey completed successfully!',
                'user': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # Transaction will be rolled back automatically
            logger.error(f"Failed to complete builder journey for user {user.id}: {str(e)}")
            return Response(
                {'error': f'Failed to complete journey: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
            valid_validators = [
                addr for addr in validators 
                if addr and 
                addr.lower() not in ['0x0', '0x000', '0x0000000000000000000000000000000000000000']
            ]
            
            # Return the filtered list of addresses
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
            
            # Check for deployments
            deployment_result = genlayer_service.get_user_deployments(user.address)
            
            # Log the check for monitoring
            logger.info(f"Deployment check for user {user.id} (address: {user.address}): "
                       f"{deployment_result.get('deployment_count', 0)} deployments found")
            
            return Response(deployment_result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error checking deployments for user {user.id}: {str(e)}")
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
            deployment_result = genlayer_service.get_user_deployments(user.address)
            
            return Response({
                'has_deployments': deployment_result.get('has_deployments', False),
                'deployment_count': deployment_result.get('deployment_count', 0),
                'wallet_address': user.address
            })
            
        except Exception as e:
            logger.error(f"Error checking deployment status for user {user.id}: {str(e)}")
            return Response({
                'has_deployments': False,
                'deployment_count': 0,
                'error': 'Failed to check deployment status'
            })
            
