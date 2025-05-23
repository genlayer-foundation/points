from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import authentication, exceptions
from rest_framework.authentication import SessionAuthentication

User = get_user_model()


class EthereumAuthentication(authentication.BaseAuthentication):
    """
    Authentication class for Ethereum wallet addresses.
    Uses session authentication for the actual request validation.
    """
    
    def authenticate(self, request):
        # Check if the session has an authenticated ethereum address
        if not request.session.get('ethereum_address'):
            return None
            
        try:
            # Get user with the authenticated ethereum address
            ethereum_address = request.session.get('ethereum_address')
            user = User.objects.get(address=ethereum_address)
            return (user, None)
        except User.DoesNotExist:
            return None
            

class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    Session Authentication with CSRF Exemption for the authentication endpoints.
    """
    def enforce_csrf(self, request):
        return