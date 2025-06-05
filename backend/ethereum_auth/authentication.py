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
        ethereum_address = request.session.get('ethereum_address')
        authenticated = request.session.get('authenticated', False)
        
        # Debug logging
        print(f"EthereumAuthentication - Session ID: {request.session.session_key}")
        print(f"EthereumAuthentication - Ethereum Address: {ethereum_address}")
        print(f"EthereumAuthentication - Authenticated: {authenticated}")
        
        if not ethereum_address or not authenticated:
            return None
            
        try:
            # Get user with the authenticated ethereum address
            user = User.objects.get(address=ethereum_address)
            print(f"EthereumAuthentication - User found: {user.email}")
            return (user, None)
        except User.DoesNotExist:
            print(f"EthereumAuthentication - User not found for address: {ethereum_address}")
            return None
            

class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    Session Authentication with CSRF Exemption for the authentication endpoints.
    """
    def enforce_csrf(self, request):
        return