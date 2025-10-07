"""
GitHub OAuth authentication handling
"""
import secrets
import logging
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.core import signing
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from cryptography.fernet import Fernet, InvalidToken
from .models import User

logger = logging.getLogger(__name__)

# Cache to track used OAuth codes (prevents duplicate exchanges)
# Format: {code: timestamp}
_used_oauth_codes = {}

# Initialize encryption for tokens
def get_fernet():
    """Get Fernet encryption instance using configured key"""
    key = settings.GITHUB_ENCRYPTION_KEY
    if not key:
        raise RuntimeError(
            "GITHUB_ENCRYPTION_KEY is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    key = key.encode() if isinstance(key, str) else key
    return Fernet(key)

def encrypt_token(token):
    """Encrypt a token for storage"""
    if not token:
        return ""
    fernet = get_fernet()
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token):
    """Decrypt a stored token"""
    if not encrypted_token:
        return ""
    fernet = get_fernet()
    return fernet.decrypt(encrypted_token.encode()).decode()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def github_oauth_initiate(request):
    """Initiate GitHub OAuth flow"""
    # User is guaranteed to be authenticated due to @permission_classes([IsAuthenticated])
    user_id = request.user.id
    logger.info(f"GitHub OAuth initiated by authenticated user {user_id}")

    # Generate state token with user ID embedded
    state_data = {
        'user_id': user_id,
        'nonce': secrets.token_urlsafe(32)
    }

    # Sign the state data to make it tamper-proof and not rely on session
    # This works even if session cookies don't persist across OAuth redirects
    state = signing.dumps(state_data, salt='github_oauth_state')
    logger.info(f"Generated signed OAuth state for user {user_id}")

    # Build GitHub OAuth URL with minimal read-only permissions
    # Empty scope gives read access to public user info including starred repos
    github_oauth_url = "https://github.com/login/oauth/authorize"
    params = {
        'client_id': settings.GITHUB_CLIENT_ID,
        'redirect_uri': settings.GITHUB_REDIRECT_URI,
        'scope': '',  # Empty scope = read-only public info (profile, starred repos, etc)
        'state': state,
        'allow_signup': 'false'  # Don't allow GitHub signup, only linking
    }

    auth_url = f"{github_oauth_url}?{urlencode(params)}"
    return redirect(auth_url)


@csrf_exempt
def github_oauth_callback(request):
    """Handle GitHub OAuth callback"""
    # Get code and state from GitHub
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')
    error_description = request.GET.get('error_description')

    logger.info(f"OAuth callback - Session key: {request.session.session_key}")

    # Handle errors from GitHub
    if error:
        logger.error(f"GitHub OAuth error: {error} - {error_description}")
        return render(request, 'github_callback.html', {
            'success': False,
            'error': 'authorization_failed',
            'message': 'Authorization failed. This window will close automatically.',
            'frontend_origin': settings.FRONTEND_URL
        })

    # Validate and unsign the state token
    # This doesn't rely on session cookies, so it works across OAuth redirects
    if not state:
        logger.error("No state token received from GitHub")
        return render(request, 'github_callback.html', {
            'success': False,
            'error': 'invalid_state',
            'message': 'Invalid state token. This window will close automatically.',
            'frontend_origin': settings.FRONTEND_URL
        })

    try:
        # Unsign the state with max_age of 10 minutes to prevent replay attacks
        state_data = signing.loads(state, salt='github_oauth_state', max_age=600)
        user_id = state_data.get('user_id')
        logger.info(f"Successfully validated signed OAuth state for user_id: {user_id}")
    except signing.SignatureExpired:
        logger.error("OAuth state token has expired (>10 minutes old)")
        return render(request, 'github_callback.html', {
            'success': False,
            'error': 'state_expired',
            'message': 'Session expired. This window will close automatically.',
            'frontend_origin': settings.FRONTEND_URL
        })
    except signing.BadSignature:
        logger.error("OAuth state token has invalid signature (tampering detected)")
        return render(request, 'github_callback.html', {
            'success': False,
            'error': 'invalid_state',
            'message': 'Invalid state token. This window will close automatically.',
            'frontend_origin': settings.FRONTEND_URL
        })

    # Clean up old codes first (older than 10 minutes)
    cutoff = timezone.now() - timezone.timedelta(minutes=10)
    expired_codes = [k for k, v in _used_oauth_codes.items() if v <= cutoff]
    for expired_code in expired_codes:
        del _used_oauth_codes[expired_code]

    if expired_codes:
        logger.info(f"Cleaned up {len(expired_codes)} expired OAuth codes")

    # Check if this code has already been used (prevent duplicate exchanges)
    if code in _used_oauth_codes:
        logger.warning(f"OAuth code {code[:10]}... has already been used, rejecting duplicate request")
        return render(request, 'github_callback.html', {
            'success': False,
            'error': 'code_already_used',
            'message': 'This code has already been used. This window will close automatically.',
            'frontend_origin': settings.FRONTEND_URL
        })

    # Mark code as used immediately (before exchange attempt)
    _used_oauth_codes[code] = timezone.now()
    logger.info(f"Marked OAuth code {code[:10]}... as used ({len(_used_oauth_codes)} codes in cache)")

    # Exchange code for access token
    logger.info(f"Attempting to exchange OAuth code {code[:10]}... for access token")
    token_url = "https://github.com/login/oauth/access_token"
    token_params = {
        'client_id': settings.GITHUB_CLIENT_ID,
        'client_secret': settings.GITHUB_CLIENT_SECRET,
        'code': code,
        'redirect_uri': settings.GITHUB_REDIRECT_URI
    }

    headers = {'Accept': 'application/json'}

    try:
        token_response = requests.post(token_url, data=token_params, headers=headers)
        token_response.raise_for_status()
        token_data = token_response.json()

        if 'error' in token_data:
            logger.error(f"GitHub token exchange error: {token_data}")
            # Check if it's because the code was already used
            if token_data.get('error') == 'bad_verification_code':
                return render(request, 'github_callback.html', {
                    'success': False,
                    'error': 'code_already_used',
                    'message': 'This code has already been used. This window will close automatically.',
                    'frontend_origin': settings.FRONTEND_URL
                })
            return render(request, 'github_callback.html', {
                'success': False,
                'error': 'token_exchange_failed',
                'message': 'Failed to exchange token. This window will close automatically.',
                'frontend_origin': settings.FRONTEND_URL
            })

        access_token = token_data.get('access_token')
        if not access_token:
            logger.error("No access token received from GitHub")
            return render(request, 'github_callback.html', {
                'success': False,
                'error': 'no_access_token',
                'message': 'No access token received. This window will close automatically.',
                'frontend_origin': settings.FRONTEND_URL
            })

        # Fetch GitHub user data
        user_url = "https://api.github.com/user"
        user_headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/json'
        }

        user_response = requests.get(user_url, headers=user_headers)
        user_response.raise_for_status()
        github_user = user_response.json()

        # Get user from state token
        # User ID must be present in state since we require authentication to initiate OAuth
        if not user_id:
            logger.error("No user_id in state token")
            return render(request, 'github_callback.html', {
                'success': False,
                'error': 'invalid_state',
                'message': 'Invalid authentication state. This window will close automatically.',
                'frontend_origin': settings.FRONTEND_URL
            })

        try:
            user = User.objects.get(id=user_id)
            logger.info(f"Found user {user.id} from state token")
        except User.DoesNotExist:
            logger.error(f"User {user_id} from state not found")
            return render(request, 'github_callback.html', {
                'success': False,
                'error': 'user_not_found',
                'message': 'User not found. This window will close automatically.',
                'frontend_origin': settings.FRONTEND_URL
            })

        # Check if this GitHub account is already linked to another user
        existing_user = User.objects.filter(
            github_user_id=str(github_user['id'])
        ).exclude(id=user.id).first()

        if existing_user:
            logger.warning(f"GitHub account already linked to another user")
            return render(request, 'github_callback.html', {
                'success': False,
                'error': 'already_linked',
                'message': 'GitHub account already linked. This window will close automatically.',
                'frontend_origin': settings.FRONTEND_URL
            })

        # Update user with GitHub info
        user.github_username = github_user['login']
        user.github_user_id = str(github_user['id'])
        user.github_access_token = encrypt_token(access_token)
        user.github_linked_at = timezone.now()
        user.save()

        logger.info(f"GitHub account linked for user {user.id}")
        # Success! Render the callback template
        return render(request, 'github_callback.html', {
            'success': True,
            'error': '',
            'message': 'GitHub account linked successfully! This window will close automatically.',
            'frontend_origin': settings.FRONTEND_URL
        })

    except requests.RequestException as e:
        logger.error(f"GitHub API request failed: {e}")
        return render(request, 'github_callback.html', {
            'success': False,
            'error': 'api_request_failed',
            'message': 'API request failed. This window will close automatically.',
            'frontend_origin': settings.FRONTEND_URL
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disconnect_github(request):
    """Disconnect GitHub account from user profile"""
    try:
        user = request.user
        user.github_username = ""
        user.github_user_id = ""
        user.github_access_token = ""
        user.github_linked_at = None
        user.save()

        return Response({
            'message': 'GitHub account disconnected successfully'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Failed to disconnect GitHub for user {request.user.id}: {e}")
        return Response({
            'error': 'Failed to disconnect GitHub account'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_repo_star(request):
    """Check if user has starred the required repository"""
    user = request.user

    if not user.github_username:
        return Response({
            'has_starred': False,
            'repo': settings.GITHUB_REPO_TO_STAR,
            'error': 'GitHub account not linked'
        }, status=status.HTTP_200_OK)

    try:
        # Use the stored access token if available, otherwise use public API
        headers = {'Accept': 'application/json'}
        if user.github_access_token:
            try:
                token = decrypt_token(user.github_access_token)
                headers['Authorization'] = f'token {token}'
            except InvalidToken:
                # Token decryption failed, likely due to encryption key change
                # Clear the invalid token
                logger.warning(f"Failed to decrypt GitHub token for user id={user.id}, clearing token")
                user.github_access_token = ''
                user.save()
                # Continue without auth header to use public API

        # Parse the repo owner and name
        repo_parts = settings.GITHUB_REPO_TO_STAR.split('/')
        if len(repo_parts) != 2:
            logger.error(f"Invalid GITHUB_REPO_TO_STAR format: {settings.GITHUB_REPO_TO_STAR}")
            return Response({
                'error': 'Invalid repository configuration'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        owner, repo = repo_parts

        # Check if user has starred the specific repo
        if user.github_access_token and 'Authorization' in headers:
            # Authenticated API: GET /user/starred/{owner}/{repo} returns 204 if starred, 404 if not
            url = f'https://api.github.com/user/starred/{owner}/{repo}'
            response = requests.get(url, headers=headers)
            has_starred = response.status_code == 204
        else:
            # Public API: Check in user's starred repos list
            # This is less efficient but works without authentication
            url = f'https://api.github.com/users/{user.github_username}/starred'
            response = requests.get(url, headers={'Accept': 'application/json'})

            if response.status_code == 200:
                starred_repos = response.json()
                repo_full_name = f'{owner}/{repo}'
                has_starred = any(r.get('full_name') == repo_full_name for r in starred_repos)
            else:
                has_starred = False

        return Response({
            'has_starred': has_starred,
            'repo': settings.GITHUB_REPO_TO_STAR,
            'github_username': user.github_username
        }, status=status.HTTP_200_OK)

    except requests.RequestException as e:
        logger.error(f"Failed to check star status for {user.github_username}: {e}")
        return Response({
            'has_starred': False,
            'repo': settings.GITHUB_REPO_TO_STAR,
            'error': 'Failed to check star status'
        }, status=status.HTTP_200_OK)  # Return 200 with has_starred=False to not break the UI