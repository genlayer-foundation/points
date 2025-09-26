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
    # Get the SIWE message, signature, and optional referral code from the request
    message = request.data.get('message')
    signature = request.data.get('signature')
    referral_code = request.data.get('referral_code')
    
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
        user, created = User.objects.get_or_create(
            address__iexact=ethereum_address,
            defaults={
                'address': ethereum_address,
                'username': ethereum_address[:10],  # Use first 10 chars as username
                'email': f'{ethereum_address[:8]}@ethereum.address',  # Generate a dummy email
                # No name set by default for wallet-based users
            }
        )
        
        # Handle referral association for new users
        if created and referral_code:
            try:
                # Find referrer by referral code
                referrer = User.objects.get(referral_code=referral_code.upper())
                # Prevent self-referral (though this shouldn't happen with new users)
                if referrer != user:
                    user.referred_by = referrer
                    user.save(update_fields=['referred_by'])
                    print(f"New user {ethereum_address} referred by {referrer.address}")
            except User.DoesNotExist:
                # Invalid referral code, but don't fail the login
                print(f"Invalid referral code provided during login: {referral_code}")
        
        # Refresh user data from database to get referral_code from signal
        user.refresh_from_db()
        
        # Store the ethereum address in the session
        request.session['ethereum_address'] = ethereum_address
        request.session['authenticated'] = True
        request.session.save()  # Explicitly save the session
        
        # Debug logging
        print(f"Login - Session ID: {request.session.session_key}")
        print(f"Login - Setting ethereum_address: {ethereum_address}")
        print(f"Login - Session data: {dict(request.session)}")
        
        # Return the authenticated user with referral data
        return Response({
            'authenticated': True,
            'address': ethereum_address,
            'user_id': user.id,
            'created': created,
            'session_key': request.session.session_key,  # For debugging
            'referral_code': user.referral_code,
            'referred_by': {
                'id': user.referred_by.id,
                'name': user.referred_by.name or 'Anonymous',
                'address': user.referred_by.address,
                'referral_code': user.referred_by.referral_code
            } if user.referred_by else None
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
    
    # Debug logging
    print(f"Verify - Session ID: {request.session.session_key}")
    print(f"Verify - Ethereum Address: {ethereum_address}")
    print(f"Verify - Authenticated: {authenticated}")
    print(f"Verify - Session data: {dict(request.session)}")
    
    if authenticated and ethereum_address:
        try:
            user = User.objects.get(address__iexact=ethereum_address)
            return Response({
                'authenticated': True,
                'address': ethereum_address,
                'user_id': user.id,
                'session_key': request.session.session_key  # For debugging
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