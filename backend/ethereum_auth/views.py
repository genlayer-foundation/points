import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from siwe import SiweMessage, VerificationError

from .models import Nonce
from .authentication import CsrfExemptSessionAuthentication
from .siwe_utils import get_expected_siwe_domain, get_expected_siwe_uri, normalize_origin
from tally.middleware.logging_utils import get_app_logger

User = get_user_model()
logger = get_app_logger('auth')
LOGIN_STATEMENT = 'Sign in with Ethereum to GenLayer Testnet Contributions'


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
    purpose = request.query_params.get('purpose', Nonce.PURPOSE_LOGIN)
    valid_purposes = {choice[0] for choice in Nonce.PURPOSE_CHOICES}
    if purpose not in valid_purposes:
        return Response(
            {'error': 'Invalid nonce purpose.'},
            status=status.HTTP_400_BAD_REQUEST,
    )

    nonce_value = generate_nonce()
    expiry_minutes = settings.ETHEREUM_AUTH.get('NONCE_EXPIRY_MINUTES', 5)
    expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
    
    # Create and save the nonce
    nonce = Nonce.objects.create(
        value=nonce_value,
        purpose=purpose,
        expires_at=expires_at
    )
    
    # Return the nonce to the client
    return Response({'nonce': nonce_value, 'purpose': purpose})


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
        try:
            siwe_message = SiweMessage.from_message(message)
        except Exception:
            return Response(
                {'error': 'Invalid SIWE message.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if siwe_message.statement != LOGIN_STATEMENT:
            return Response(
                {'error': 'Invalid SIWE statement.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if normalize_origin(str(siwe_message.uri)) != get_expected_siwe_uri():
            return Response(
                {'error': 'Invalid SIWE URI.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            try:
                nonce = Nonce.objects.select_for_update().get(
                    value=siwe_message.nonce,
                    purpose=Nonce.PURPOSE_LOGIN,
                )
            except Nonce.DoesNotExist:
                return Response(
                    {'error': 'Invalid nonce.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not nonce.is_valid():
                return Response(
                    {'error': 'Invalid or expired nonce.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                siwe_message.verify(
                    signature,
                    domain=get_expected_siwe_domain(),
                    nonce=siwe_message.nonce,
                )
            except VerificationError:
                return Response(
                    {'error': 'Invalid SIWE signature.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            nonce.mark_as_used()

        ethereum_address = siwe_message.address.lower()
        
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
                    logger.debug("New user referred successfully")
            except User.DoesNotExist:
                # Invalid referral code, but don't fail the login
                logger.warning("Invalid referral code provided during login")
        
        # Refresh user data from database to get referral_code from signal
        user.refresh_from_db()
        
        # Store the ethereum address in the session
        request.session['ethereum_address'] = ethereum_address
        request.session['authenticated'] = True
        request.session.save()  # Explicitly save the session

        logger.debug("Login successful, session created")

        # Return the authenticated user with referral data
        return Response({
            'authenticated': True,
            'address': ethereum_address,
            'user_id': user.id,
            'created': created,
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

    if authenticated and ethereum_address:
        try:
            user = User.objects.get(address__iexact=ethereum_address)
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
