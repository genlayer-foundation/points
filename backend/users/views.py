from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import User
from .serializers import UserSerializer, UserCreateSerializer
from web3 import Web3


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows users to be viewed.
    Users with visible=False are excluded from the queryset,
    except for the authenticated user viewing their own profile.
    """
    queryset = User.objects.filter(visible=True)
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]  # Allow read-only access without authentication
    lookup_field = 'address'  # Change default lookup field from 'pk' to 'address'
    
    def get_object(self):
        """
        Override to allow users to access their own profile
        even if they're marked as not visible.
        """
        obj = super().get_object()
        # If the user is accessing their own profile, allow it
        if self.request.user.is_authenticated and obj.id == self.request.user.id:
            return obj
        # Otherwise, enforce visibility rules
        if not obj.visible:
            self.permission_denied(self.request, message="User not found.")
        return obj
        
    @action(detail=False, methods=['get'], url_path='by-address/(?P<address>[^/.]+)')
    def by_address(self, request, address=None):
        """
        Get a user by their Ethereum wallet address
        """
        user = get_object_or_404(User.objects.filter(visible=True), address=address)
        serializer = self.get_serializer(user)
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
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """
        Get the authenticated user's profile.
        Users can always see their own profile regardless of visibility setting.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
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
            
            # Just return the list of addresses without case conversion
            return Response(validators, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
