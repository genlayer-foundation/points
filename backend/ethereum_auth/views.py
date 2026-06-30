import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import login as django_login
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from utils.throttling import (
    ExistingEmailConfirmRateThrottle,
    ExistingEmailResendRateThrottle,
    ExistingEmailStartRateThrottle,
    PendingEmailConfirmRateThrottle,
    PendingEmailResendRateThrottle,
    PendingEmailStartRateThrottle,
    SiweAuthRateThrottle,
)
from siwe import SiweMessage, VerificationError

from .email_verification import EmailVerificationService, TurnstileVerifier
from .models import Nonce, PendingWalletSignup
from .authentication import CsrfExemptSessionAuthentication
from .siwe_utils import get_expected_siwe_domain, get_expected_siwe_uri, normalize_origin
from tally.middleware.logging_utils import get_app_logger

User = get_user_model()
logger = get_app_logger('auth')
LOGIN_STATEMENT = 'Sign in with Ethereum to GenLayer Testnet Contributions'
email_verification_service = EmailVerificationService()
turnstile_verifier = TurnstileVerifier()
PENDING_SIGNUP_PROFILE_FIELDS = {
    'name',
    'description',
    'website',
    'telegram_handle',
    'linkedin_handle',
    'selected_role',
}


def generate_nonce(length=32):
    """Generate a random nonce string of specified length"""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def validation_error_response(exc):
    detail = getattr(exc, 'detail', {'detail': 'Invalid request.'})
    return Response(detail, status=status.HTTP_400_BAD_REQUEST)


def get_pending_signup_profile_data(data):
    profile_data = {
        field: data.get(field)
        for field in PENDING_SIGNUP_PROFILE_FIELDS
        if field in data
    }
    return profile_data or None


def get_pending_signup_from_session(request):
    pending_id = request.session.get('pending_wallet_signup_id')
    pending_address = request.session.get('pending_wallet_address')
    queryset = PendingWalletSignup.objects.filter(status=PendingWalletSignup.STATUS_PENDING)
    if pending_id:
        pending = queryset.filter(pk=pending_id).first()
    elif pending_address:
        pending = queryset.filter(address__iexact=pending_address).first()
    else:
        pending = None
    if pending and pending.is_active():
        return pending
    return None


def normalize_pending_referral_code(value):
    code = str(value or '').strip().upper()
    return code if len(code) <= 8 else ''


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([SiweAuthRateThrottle])
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
@throttle_classes([SiweAuthRateThrottle])
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
        
        user = User.objects.filter(address__iexact=ethereum_address).first()
        if not user:
            if not request.session.session_key:
                request.session.create()
            expires_at = timezone.now() + timedelta(seconds=settings.PENDING_WALLET_SIGNUP_TTL_SECONDS)
            pending, _ = PendingWalletSignup.objects.update_or_create(
                address=ethereum_address,
                defaults={
                    'session_key': request.session.session_key,
                    'referral_code': normalize_pending_referral_code(referral_code),
                    'status': PendingWalletSignup.STATUS_PENDING,
                    'expires_at': expires_at,
                },
            )
            request.session['pending_wallet_signup_id'] = pending.id
            request.session['pending_wallet_address'] = ethereum_address
            request.session['authenticated'] = False
            request.session.save()
            return Response({
                'authenticated': False,
                'pending_signup': True,
                'address': ethereum_address,
            })

        django_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        request.session['ethereum_address'] = ethereum_address
        request.session['authenticated'] = True
        request.session.pop('pending_wallet_signup_id', None)
        request.session.pop('pending_wallet_address', None)
        request.session.save()  # Explicitly save the session

        logger.debug("Login successful, session created")

        # Return the authenticated user with referral data
        return Response({
            'authenticated': True,
            'address': ethereum_address,
            'user_id': user.id,
            'created': False,
            'referral_code': user.referral_code,
            'referred_by': {
                'id': user.referred_by.id,
                'name': user.referred_by.name or 'Anonymous',
                'address': user.referred_by.address,
                'referral_code': user.referred_by.referral_code
            } if user.referred_by else None
        })
        
    except Exception as e:
        logger.exception("Authentication failed")
        error_detail = f'Authentication failed: {str(e)}' if settings.DEBUG else 'Authentication failed.'
        return Response(
            {'error': error_detail},
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
    
    pending = get_pending_signup_from_session(request)
    return Response({
        'authenticated': False,
        'address': pending.address if pending else None,
        'user_id': None,
        'pending_signup': bool(pending),
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


def send_pending_signup_email(request):
    pending = get_pending_signup_from_session(request)
    if not pending:
        return Response({'detail': 'Pending signup is required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        email_verification_service.ensure_pending_signup_can_send(pending)
        turnstile_verifier.verify(request.data.get('turnstile_token'), get_client_ip(request))
        email_verification_service.start_for_pending_signup(
            pending,
            request.data.get('email'),
            profile_data=get_pending_signup_profile_data(request.data),
        )
    except Exception as exc:
        if hasattr(exc, 'detail'):
            return validation_error_response(exc)
        logger.exception("Failed to start pending signup email verification")
        return Response({'detail': 'Could not send verification email.'}, status=status.HTTP_400_BAD_REQUEST)
    return Response({'sent': True, 'cooldown_seconds': settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS})


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([CsrfExemptSessionAuthentication])
@throttle_classes([PendingEmailStartRateThrottle])
def signup_email_start(request):
    return send_pending_signup_email(request)


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([CsrfExemptSessionAuthentication])
@throttle_classes([PendingEmailResendRateThrottle])
def signup_email_resend(request):
    return send_pending_signup_email(request)


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([CsrfExemptSessionAuthentication])
@throttle_classes([PendingEmailConfirmRateThrottle])
def signup_email_confirm(request):
    pending = get_pending_signup_from_session(request)
    if not pending:
        return Response({'detail': 'Pending signup is required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        user = email_verification_service.confirm_pending_signup(
            pending,
            request.data.get('code') or request.data.get('token'),
        )
        confirmed_pending = pending
    except Exception as exc:
        if hasattr(exc, 'detail'):
            return validation_error_response(exc)
        logger.exception("Failed to confirm pending signup email code")
        return Response({'detail': 'Could not confirm verification code.'}, status=status.HTTP_400_BAD_REQUEST)

    django_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    request.session['ethereum_address'] = user.address
    request.session['authenticated'] = True
    request.session.pop('pending_wallet_signup_id', None)
    request.session.pop('pending_wallet_address', None)
    request.session.save()
    return Response({
        'authenticated': True,
        'requires_wallet_login': False,
        'address': user.address,
        'user_id': user.id,
        'created': True,
        'referral_code': user.referral_code,
        'selected_role': (confirmed_pending.profile_data or {}).get('selected_role', ''),
    })


def send_existing_user_email(request):
    try:
        email_verification_service.ensure_existing_user_can_send(request.user)
        turnstile_verifier.verify(request.data.get('turnstile_token'), get_client_ip(request))
        email_verification_service.start_for_user(request.user, request.data.get('email'))
    except Exception as exc:
        if hasattr(exc, 'detail'):
            return validation_error_response(exc)
        logger.exception("Failed to start email verification")
        return Response({'detail': 'Could not send verification email.'}, status=status.HTTP_400_BAD_REQUEST)
    return Response({'sent': True, 'cooldown_seconds': settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS})


@api_view(['POST'])
@throttle_classes([ExistingEmailStartRateThrottle])
def email_start(request):
    return send_existing_user_email(request)


@api_view(['POST'])
@throttle_classes([ExistingEmailResendRateThrottle])
def email_resend(request):
    return send_existing_user_email(request)


@api_view(['POST'])
@throttle_classes([ExistingEmailConfirmRateThrottle])
def email_confirm(request):
    try:
        user = email_verification_service.confirm_existing_user(
            request.user,
            request.data.get('code') or request.data.get('token'),
        )
    except Exception as exc:
        if hasattr(exc, 'detail'):
            return validation_error_response(exc)
        logger.exception("Failed to confirm email verification code")
        return Response({'detail': 'Could not confirm verification code.'}, status=status.HTTP_400_BAD_REQUEST)
    return Response({
        'verified': True,
        'email': user.email,
        'is_email_verified': user.is_email_verified,
        'email_verified_at': user.email_verified_at,
    })
