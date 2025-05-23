import secrets
import string
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from eth_account.messages import encode_defunct
from eth_account import Account

from .models import Nonce
from .authentication import CsrfExemptSessionAuthentication

User = get_user_model()


def generate_nonce(length=32):
    """Generate a random nonce string of specified length"""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


@api_view(['GET'])
@permission_classes([AllowAny])
def get_nonce(request):
    """
    Generate a new nonce for SIWE authentication.
    """
    # Generate a random nonce
    nonce_value = generate_nonce()
    
    # Set expiration time (e.g., 5 minutes from now)
    expires_at = timezone.now() + timedelta(minutes=5)
    
    # Create and save the nonce
    nonce = Nonce.objects.create(
        value=nonce_value,
        expires_at=expires_at
    )
    
    # Return the nonce to the client
    return Response({'nonce': nonce_value})


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([CsrfExemptSessionAuthentication])
def login(request):
    """
    Authenticate a user with a SIWE message.
    """
    # Get the SIWE message and signature from the request
    message = request.data.get('message')
    signature = request.data.get('signature')
    
    if not message or not signature:
        return Response(
            {'error': 'Message and signature are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Extract the nonce and address from the message directly
        # Parse the message format which should be:
        # domain wants you to sign in with your Ethereum account:
        # 0x123...
        # 
        # Sign in with Ethereum to Tally
        # 
        # URI: http://...
        # Version: 1
        # Chain ID: 1
        # Nonce: abc123
        # Issued At: 2023-...

        message_lines = message.strip().split('\n')
        ethereum_address = message_lines[1].lower()
        
        # Find the nonce line and extract the value
        nonce_line = next((line for line in message_lines if line.startswith('Nonce:')), None)
        if not nonce_line:
            return Response(
                {'error': 'Invalid message format: No nonce found.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        nonce_value = nonce_line.split(':', 1)[1].strip()
        
        # Verify the nonce
        try:
            nonce = Nonce.objects.get(value=nonce_value)
            if not nonce.is_valid():
                return Response(
                    {'error': 'Invalid or expired nonce.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Nonce.DoesNotExist:
            return Response(
                {'error': 'Invalid nonce.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify the signature using eth_account
        message_hash = encode_defunct(text=message)
        recovered_address = Account.recover_message(message_hash, signature=signature)
        
        if recovered_address.lower() != ethereum_address:
            return Response(
                {'error': 'Invalid signature: address mismatch'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Mark the nonce as used
        nonce.mark_as_used()
        
        # Get or create the user
        ethereum_address = ethereum_address.lower()
        
        user, created = User.objects.get_or_create(
            address=ethereum_address,
            defaults={
                'username': ethereum_address[:10],  # Use first 10 chars as username
                'email': f'{ethereum_address[:8]}@ethereum.address',  # Generate a dummy email
                'name': f'Ethereum User {ethereum_address[:6]}'  # Generate a dummy name
            }
        )
        
        # Store the ethereum address in the session
        request.session['ethereum_address'] = ethereum_address
        request.session['authenticated'] = True
        
        # Return the authenticated user
        return Response({
            'authenticated': True,
            'address': ethereum_address,
            'user_id': user.id,
            'created': created
        })
        
    except Exception as e:
        return Response(
            {'error': f'Authentication failed: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_auth(request):
    """
    Verify if the user is authenticated.
    """
    ethereum_address = request.session.get('ethereum_address')
    authenticated = request.session.get('authenticated', False)
    
    if authenticated and ethereum_address:
        try:
            user = User.objects.get(address=ethereum_address)
            return Response({
                'authenticated': True,
                'address': ethereum_address,
                'user_id': user.id
            })
        except User.DoesNotExist:
            pass
    
    return Response({
        'authenticated': False,
        'address': None,
        'user_id': None
    })


@api_view(['POST'])
def logout(request):
    """
    Log out the user by clearing the session.
    """
    request.session.flush()
    return Response({'message': 'Logged out successfully.'})


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_session(request):
    """
    Refresh the session to prevent expiration.
    """
    ethereum_address = request.session.get('ethereum_address')
    authenticated = request.session.get('authenticated', False)
    
    if authenticated and ethereum_address:
        # Simply touching the session extends its lifetime
        request.session.modified = True
        return Response({'message': 'Session refreshed successfully.'})
    
    return Response(
        {'error': 'Not authenticated.'},
        status=status.HTTP_401_UNAUTHORIZED
    )