from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import authentication, exceptions
from rest_framework.authentication import SessionAuthentication

from tally.middleware.logging_utils import get_app_logger

User = get_user_model()
logger = get_app_logger('auth')


class EthereumAuthentication(authentication.BaseAuthentication):
    """
    Authentication class for Ethereum wallet addresses.
    Uses session authentication for the actual request validation.
    """

    def authenticate(self, request):
        # Check if the session has an authenticated ethereum address
        ethereum_address = request.session.get('ethereum_address')
        authenticated = request.session.get('authenticated', False)

        if not ethereum_address or not authenticated:
            return None

        try:
            # Get user with the authenticated ethereum address
            user = User.objects.get(address__iexact=ethereum_address)
            return (user, None)
        except User.DoesNotExist:
            logger.debug("User not found for authenticated session")
            return None
            

class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    Session Authentication with CSRF Exemption for the authentication endpoints.
    """
    def enforce_csrf(self, request):
        return