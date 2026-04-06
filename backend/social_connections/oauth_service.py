"""Shared OAuth service base class for all social platform integrations."""

import secrets
import hashlib
import base64
from urllib.parse import urlencode, urlparse, urlunparse

import requests
from django.conf import settings
from django.core import signing
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils import timezone

from tally.middleware.logging_utils import get_app_logger
from tally.middleware.tracing import trace_external

from .encryption import encrypt_token, decrypt_token
from .models import UsedOAuthCode

logger = get_app_logger('social_oauth')


def validate_redirect_url(url):
    """Validate that a redirect URL belongs to an allowed origin.
    Returns the validated URL or FRONTEND_URL as fallback."""
    if not url:
        return settings.FRONTEND_URL

    try:
        parsed = urlparse(url)
    except Exception:
        return settings.FRONTEND_URL

    # Build allowed origins from FRONTEND_URL and BACKEND_URL
    allowed_origins = set()
    for setting_url in [settings.FRONTEND_URL, settings.BACKEND_URL]:
        try:
            p = urlparse(setting_url)
            allowed_origins.add(f"{p.scheme}://{p.netloc}")
        except Exception:
            pass

    request_origin = f"{parsed.scheme}://{parsed.netloc}"
    if request_origin in allowed_origins:
        return url

    logger.warning(f"Rejected redirect URL with origin {request_origin}")
    return settings.FRONTEND_URL


class OAuthService:
    """Base OAuth service with shared logic for all social providers."""

    platform_name = None        # 'github', 'twitter', 'discord'
    authorize_url = None
    token_url = None
    user_info_url = None
    scopes = []
    uses_pkce = False

    def get_connection_model(self):
        """Return the Django model class for this platform's connections."""
        raise NotImplementedError

    def get_client_id(self):
        raise NotImplementedError

    def get_client_secret(self):
        raise NotImplementedError

    def get_redirect_uri(self):
        raise NotImplementedError

    # --- State token management ---

    def generate_state(self, user_id, extra_data=None):
        """Generate a signed state token embedding the user_id.
        Sensitive fields (code_verifier) are encrypted before embedding."""
        state_data = {
            'user_id': user_id,
            'nonce': secrets.token_urlsafe(32),
        }
        if extra_data:
            # Encrypt code_verifier so it's not readable in the URL
            if 'code_verifier' in extra_data:
                extra_data = dict(extra_data)
                extra_data['code_verifier'] = encrypt_token(extra_data['code_verifier'])
            # Validate redirect_url against allowed origins
            if 'redirect_url' in extra_data:
                extra_data = dict(extra_data) if not isinstance(extra_data, dict) else extra_data
                extra_data['redirect_url'] = validate_redirect_url(extra_data['redirect_url'])
            state_data.update(extra_data)
        return signing.dumps(state_data, salt=f'{self.platform_name}_oauth_state')

    def validate_state(self, state):
        """Validate and return state data dict. Decrypts encrypted fields.
        Raises signing exceptions on failure."""
        data = signing.loads(state, salt=f'{self.platform_name}_oauth_state', max_age=600)
        # Decrypt code_verifier if present
        if 'code_verifier' in data:
            try:
                data['code_verifier'] = decrypt_token(data['code_verifier'])
            except Exception:
                logger.error("Failed to decrypt code_verifier from state")
                raise signing.BadSignature("Invalid state: code_verifier decryption failed")
        return data

    # --- Code replay prevention ---

    def mark_code_used(self, code):
        """Mark an OAuth code as used. Returns True if newly used, False if duplicate."""
        UsedOAuthCode.cleanup_old(minutes=10)
        return UsedOAuthCode.mark_used(code, self.platform_name)

    # --- Token exchange (override per platform) ---

    def exchange_code(self, code, **kwargs):
        """Exchange authorization code for access token. Returns token response dict."""
        raise NotImplementedError

    # --- User info (override per platform) ---

    def fetch_user_info(self, access_token):
        """Fetch and normalize user info. Returns dict with 'platform_user_id', 'platform_username', and any extras."""
        raise NotImplementedError

    # --- Template rendering ---

    def render_callback(self, request, success, error='', message='', redirect_url=None):
        """Redirect back to frontend with OAuth result as query params.

        Handles hash-based SPA URLs correctly by inserting query params
        BEFORE the fragment, e.g.:
          http://host/#/profile -> http://host/?oauth_platform=github#/profile
        """
        target = redirect_url or settings.FRONTEND_URL
        params = {
            'oauth_platform': self.platform_name,
            'oauth_verified': 'true' if success else 'false',
        }
        if error:
            params['oauth_error'] = error

        parsed = urlparse(target)
        # Merge new params with any existing query params
        existing_query = parsed.query
        new_query = urlencode(params)
        if existing_query:
            merged_query = f"{existing_query}&{new_query}"
        else:
            merged_query = new_query

        # Rebuild URL with query params before fragment
        final_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            merged_query,
            parsed.fragment,
        ))
        return HttpResponseRedirect(final_url)

    # --- Shared callback flow ---

    def handle_callback(self, request, session_data=None):
        """Full OAuth callback flow. Called by each platform's callback view.
        session_data: optional dict with data stored in session during initiate
        (e.g. code_verifier, redirect_url) to keep the state token small."""
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')

        platform = self.platform_name
        log_prefix = f"{platform.title()} OAuth"
        redirect_url = None

        def respond(success, error='', message=''):
            return self.render_callback(request, success=success, error=error,
                                        message=message, redirect_url=redirect_url)

        # Handle provider errors
        if error:
            logger.error(f"{log_prefix} error: {error}")
            return respond(False, error='authorization_failed')

        # Validate state
        if not state:
            logger.error(f"{log_prefix}: no state token received")
            return respond(False, error='invalid_state')

        try:
            state_data = self.validate_state(state)
            user_id = state_data.get('user_id')
            redirect_url = state_data.get('redirect_url')
        except signing.SignatureExpired:
            logger.error(f"{log_prefix}: state token expired")
            return respond(False, error='state_expired')
        except signing.BadSignature:
            logger.error(f"{log_prefix}: invalid state signature")
            return respond(False, error='invalid_state')

        # Merge session data into state_data (for platforms that store
        # large values like code_verifier in the session instead of the state token)
        if session_data:
            state_data.update(session_data)
            if not redirect_url:
                redirect_url = session_data.get('redirect_url')

        # Prevent code replay
        if not code:
            logger.error(f"{log_prefix}: no code received")
            return respond(False, error='no_code')

        if not self.mark_code_used(code):
            logger.warning(f"{log_prefix}: code already used")
            return respond(False, error='code_already_used')

        # Exchange code for token
        try:
            token_data = self.exchange_code(code, state_data=state_data)
        except requests.RequestException as e:
            logger.error(f"{log_prefix}: token exchange failed: {e}")
            return respond(False, error='token_exchange_failed')
        except ValueError as e:
            logger.error(f"{log_prefix}: token exchange error: {e}")
            error_code = 'code_already_used' if 'bad_verification_code' in str(e) else 'token_exchange_failed'
            return respond(False, error=error_code)

        access_token = token_data.get('access_token')
        if not access_token:
            logger.error(f"{log_prefix}: no access token in response")
            return respond(False, error='no_access_token')

        # Fetch user info
        try:
            user_info = self.fetch_user_info(access_token)
        except requests.RequestException as e:
            logger.error(f"{log_prefix}: failed to fetch user info: {e}")
            return respond(False, error='api_request_failed')
        except ValueError as e:
            logger.error(f"{log_prefix}: invalid user info response: {e}")
            return respond(False, error='api_request_failed')

        # Validate required fields
        platform_user_id = str(user_info.get('platform_user_id', ''))
        platform_username = str(user_info.get('platform_username', ''))[:100]

        if not platform_user_id or not platform_username:
            logger.error(f"{log_prefix}: missing user ID or username in response")
            return respond(False, error='api_request_failed')

        # Look up user
        from users.models import User
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"{log_prefix}: user {user_id} not found")
            return respond(False, error='user_not_found')

        # Check if platform account is already linked to another user
        ConnectionModel = self.get_connection_model()
        existing = ConnectionModel.objects.filter(
            platform_user_id=platform_user_id
        ).exclude(user=user).first()

        if existing:
            logger.warning(f"{log_prefix}: account already linked to another user")
            return respond(False, error='already_linked')

        # Build defaults for connection
        defaults = {
            'platform_user_id': platform_user_id,
            'platform_username': platform_username,
            'access_token': encrypt_token(access_token),
            'linked_at': timezone.now(),
        }

        # Add refresh token if present
        refresh_token = token_data.get('refresh_token')
        if refresh_token:
            defaults['refresh_token'] = encrypt_token(refresh_token)

        # Add platform-specific extra fields
        extra_fields = user_info.get('extra_fields', {})
        defaults.update(extra_fields)

        # Create or update connection
        ConnectionModel.objects.update_or_create(user=user, defaults=defaults)
        logger.debug(f"{log_prefix}: account linked successfully for user {user_id}")

        return respond(True)

    # --- PKCE helpers (used by Twitter) ---

    @staticmethod
    def generate_code_verifier():
        """Generate a PKCE code verifier."""
        return secrets.token_urlsafe(64)[:128]

    @staticmethod
    def generate_code_challenge(verifier):
        """Generate a PKCE S256 code challenge from a verifier."""
        digest = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()


class GitHubOAuthService(OAuthService):
    platform_name = 'github'
    authorize_url = 'https://github.com/login/oauth/authorize'
    token_url = 'https://github.com/login/oauth/access_token'
    user_info_url = 'https://api.github.com/user'
    scopes = []

    def get_connection_model(self):
        from .models import GitHubConnection
        return GitHubConnection

    def get_client_id(self):
        return settings.GITHUB_CLIENT_ID

    def get_client_secret(self):
        return settings.GITHUB_CLIENT_SECRET

    def get_redirect_uri(self):
        return settings.GITHUB_REDIRECT_URI

    def exchange_code(self, code, **kwargs):
        with trace_external('github', 'token_exchange'):
            response = requests.post(self.token_url, data={
                'client_id': self.get_client_id(),
                'client_secret': self.get_client_secret(),
                'code': code,
                'redirect_uri': self.get_redirect_uri(),
            }, headers={'Accept': 'application/json'})
            response.raise_for_status()
            data = response.json()

        if 'error' in data:
            raise ValueError(data.get('error', 'unknown error'))
        return data

    def fetch_user_info(self, access_token):
        with trace_external('github', 'get_user'):
            response = requests.get(self.user_info_url, headers={
                'Authorization': f'token {access_token}',
                'Accept': 'application/json',
            })
            response.raise_for_status()
            data = response.json()

        if not data.get('id') or not data.get('login'):
            raise ValueError("Missing id or login in GitHub user response")

        return {
            'platform_user_id': str(data['id']),
            'platform_username': data['login'],
        }

    def check_repo_star(self, connection):
        """Check if user has starred the configured repository."""
        from .encryption import decrypt_token
        from cryptography.fernet import InvalidToken

        repo = settings.GITHUB_REPO_TO_STAR
        repo_parts = repo.split('/')
        if len(repo_parts) != 2:
            logger.error(f"Invalid GITHUB_REPO_TO_STAR format: {repo}")
            return None

        owner, repo_name = repo_parts
        headers = {'Accept': 'application/json'}

        if connection.access_token:
            try:
                token = decrypt_token(connection.access_token)
                headers['Authorization'] = f'token {token}'
            except InvalidToken:
                logger.warning("Failed to decrypt GitHub token")
                # Fall through to public API

        if 'Authorization' in headers:
            url = f'https://api.github.com/user/starred/{owner}/{repo_name}'
            with trace_external('github', 'check_star'):
                response = requests.get(url, headers=headers)
            return response.status_code == 204
        else:
            url = f'https://api.github.com/users/{connection.platform_username}/starred'
            with trace_external('github', 'check_star_public'):
                response = requests.get(url, headers={'Accept': 'application/json'})
            if response.status_code == 200:
                starred_repos = response.json()
                return any(r.get('full_name') == f'{owner}/{repo_name}' for r in starred_repos)
            return False


class TwitterOAuthService(OAuthService):
    platform_name = 'twitter'
    authorize_url = 'https://x.com/i/oauth2/authorize'
    token_url = 'https://api.x.com/2/oauth2/token'
    user_info_url = 'https://api.x.com/2/users/me'
    scopes = ['tweet.read', 'users.read']
    uses_pkce = True

    def get_connection_model(self):
        from .models import TwitterConnection
        return TwitterConnection

    def get_client_id(self):
        return settings.TWITTER_CLIENT_ID

    def get_client_secret(self):
        return settings.TWITTER_CLIENT_SECRET

    def get_redirect_uri(self):
        return settings.TWITTER_REDIRECT_URI

    def exchange_code(self, code, **kwargs):
        state_data = kwargs.get('state_data', {})
        code_verifier = state_data.get('code_verifier', '')

        auth_string = base64.b64encode(
            f"{self.get_client_id()}:{self.get_client_secret()}".encode()
        ).decode()

        with trace_external('twitter', 'token_exchange'):
            response = requests.post(self.token_url, data={
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': self.get_redirect_uri(),
                'code_verifier': code_verifier,
            }, headers={
                'Authorization': f'Basic {auth_string}',
                'Content-Type': 'application/x-www-form-urlencoded',
            })
            response.raise_for_status()
            data = response.json()

        if 'error' in data:
            raise ValueError(data.get('error', 'unknown error'))
        return data

    def fetch_user_info(self, access_token):
        with trace_external('twitter', 'get_user'):
            response = requests.get(self.user_info_url, headers={
                'Authorization': f'Bearer {access_token}',
            })
            response.raise_for_status()
            data = response.json()

        user_data = data.get('data', {})
        if not user_data.get('id') or not user_data.get('username'):
            raise ValueError("Missing id or username in Twitter user response")

        return {
            'platform_user_id': str(user_data['id']),
            'platform_username': user_data['username'],
        }


class DiscordOAuthService(OAuthService):
    platform_name = 'discord'
    authorize_url = 'https://discord.com/oauth2/authorize'
    token_url = 'https://discord.com/api/v10/oauth2/token'
    user_info_url = 'https://discord.com/api/v10/users/@me'
    scopes = ['identify', 'guilds.members.read']

    def get_connection_model(self):
        from .models import DiscordConnection
        return DiscordConnection

    def get_client_id(self):
        return settings.DISCORD_CLIENT_ID

    def get_client_secret(self):
        return settings.DISCORD_CLIENT_SECRET

    def get_redirect_uri(self):
        return settings.DISCORD_REDIRECT_URI

    def exchange_code(self, code, **kwargs):
        with trace_external('discord', 'token_exchange'):
            response = requests.post(self.token_url, data={
                'client_id': self.get_client_id(),
                'client_secret': self.get_client_secret(),
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self.get_redirect_uri(),
            }, headers={
                'Content-Type': 'application/x-www-form-urlencoded',
            })
            response.raise_for_status()
            data = response.json()

        if 'error' in data:
            raise ValueError(data.get('error', 'unknown error'))
        return data

    def fetch_user_info(self, access_token):
        with trace_external('discord', 'get_user'):
            response = requests.get(self.user_info_url, headers={
                'Authorization': f'Bearer {access_token}',
            })
            response.raise_for_status()
            data = response.json()

        if not data.get('id') or not data.get('username'):
            raise ValueError("Missing id or username in Discord user response")

        extra_fields = {}
        if data.get('discriminator'):
            extra_fields['discriminator'] = str(data['discriminator'])[:10]
        if data.get('avatar'):
            extra_fields['avatar_hash'] = str(data['avatar'])[:100]

        return {
            'platform_user_id': str(data['id']),
            'platform_username': data['username'],
            'extra_fields': extra_fields,
        }

    def check_guild_membership(self, access_token, guild_id):
        """Check if user is a member of the specified guild. Returns True/False."""
        url = f'https://discord.com/api/v10/users/@me/guilds/{guild_id}/member'
        with trace_external('discord', 'check_guild'):
            response = requests.get(url, headers={
                'Authorization': f'Bearer {access_token}',
            })

        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False
        elif response.status_code == 401:
            logger.warning("Discord token expired or revoked during guild check")
            return False
        else:
            logger.error(f"Discord guild check returned status {response.status_code}")
            return False
