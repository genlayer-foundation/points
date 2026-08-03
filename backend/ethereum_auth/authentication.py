from rest_framework import authentication, exceptions
from rest_framework.authentication import SessionAuthentication

from tally.middleware.logging_utils import get_app_logger
from users.utils import truncate_address

logger = get_app_logger('auth')


def same_wallet(user_address, session_address):
    """
    Compare a stored address to a session address case-insensitively.

    The comparison must stay case-insensitive: login stores the lowercased SIWE
    address while signup_email_confirm stores the address as held in the
    database, and production still holds mixed-case rows (migration
    users.0006_merge_duplicate_addresses deliberately preserved casing).
    """
    if not user_address or not session_address:
        return False
    return user_address.lower() == session_address.lower()


class EthereumAuthentication(authentication.BaseAuthentication):
    """
    Authentication class for Ethereum wallet addresses.

    The user is resolved through Django's own session machinery
    (AuthenticationMiddleware -> django.contrib.auth.get_user), which validates
    _auth_user_backend and _auth_user_hash, applies the backend's is_active
    check, and costs a single primary-key lookup. The session's wallet address
    must still bind to the resolved user.

    Sessions written before django_login() was introduced carry no
    _auth_user_id and are rejected; the wallet re-signs in once. Looking the
    user up by address instead would be a sequential scan on every request,
    since the only index on users_user.address is case-sensitive.
    """

    def authenticate(self, request):
        # Check if the session has an authenticated ethereum address
        session_address = request.session.get('ethereum_address')
        authenticated = request.session.get('authenticated', False)

        if not session_address or not authenticated:
            return None

        SessionAuthentication().enforce_csrf(request)

        # The Django request's user, not the DRF request's, whose property
        # would re-enter this authenticator.
        user = getattr(request._request, 'user', None)
        if user is None or not user.is_authenticated or not user.is_active:
            logger.debug("No usable Django session user for authenticated session")
            return None

        if not same_wallet(user.address, session_address):
            # Must raise, not return None: returning None would let the next
            # authenticator in the chain resolve the very same session user and
            # grant the request, bypassing this binding check entirely.
            logger.warning(
                "wallet-binding-mismatch user=%s session=%s db=%s",
                user.pk,
                truncate_address(session_address),
                truncate_address(user.address),
            )
            raise exceptions.AuthenticationFailed('Session wallet mismatch.')

        return (user, None)


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    Session Authentication with CSRF Exemption for the authentication endpoints.
    """
    def enforce_csrf(self, request):
        return
