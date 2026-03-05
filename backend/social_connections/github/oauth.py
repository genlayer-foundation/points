"""
GitHub OAuth authentication handling.
"""
import secrets
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

from cryptography.fernet import InvalidToken
from users.models import User
from social_connections.encryption import encrypt_token, decrypt_token
from social_connections.github.models import GitHubConnection
from tally.middleware.logging_utils import get_app_logger
from tally.middleware.tracing import trace_external

logger = get_app_logger('github_oauth')

# Cache to track used OAuth codes (prevents duplicate exchanges)
# Format: {code: timestamp}
_used_oauth_codes = {}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def github_oauth_initiate(request):
    """Initiate GitHub OAuth flow."""
    user_id = request.user.id
    logger.debug("GitHub OAuth initiated")

    # Generate state token with user ID embedded
    state_data = {
        'user_id': user_id,
        'nonce': secrets.token_urlsafe(32)
    }

    # Sign the state data to make it tamper-proof
    state = signing.dumps(state_data, salt='github_oauth_state')
    logger.debug("Generated signed OAuth state")

    # Build GitHub OAuth URL with minimal read-only permissions
    github_oauth_url = "https://github.com/login/oauth/authorize"
    params = {
        'client_id': settings.GITHUB_CLIENT_ID,
        'redirect_uri': settings.GITHUB_REDIRECT_URI,
        'scope': '',  # Empty scope = read-only public info
        'state': state,
        'allow_signup': 'false'
    }

    auth_url = f"{github_oauth_url}?{urlencode(params)}"
    return redirect(auth_url)


@csrf_exempt
def github_oauth_callback(request):
    """Handle GitHub OAuth callback."""
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')
    error_description = request.GET.get('error_description')

    logger.debug("OAuth callback received")

    template_context = {
        'platform': 'github',
        'frontend_origin': settings.FRONTEND_URL
    }

    # Handle errors from GitHub
    if error:
        logger.error(f"GitHub OAuth error: {error} - {error_description}")
        return render(request, 'social_connections/oauth_callback.html', {
            **template_context,
            'success': False,
            'error': 'authorization_failed',
            'message': 'Authorization failed. This window will close automatically.',
        })

    # Validate state token
    if not state:
        logger.error("No state token received from GitHub")
        return render(request, 'social_connections/oauth_callback.html', {
            **template_context,
            'success': False,
            'error': 'invalid_state',
            'message': 'Invalid state token. This window will close automatically.',
        })

    try:
        state_data = signing.loads(state, salt='github_oauth_state', max_age=600)
        user_id = state_data.get('user_id')
        logger.debug("Successfully validated signed OAuth state")
    except signing.SignatureExpired:
        logger.error("OAuth state token has expired")
        return render(request, 'social_connections/oauth_callback.html', {
            **template_context,
            'success': False,
            'error': 'state_expired',
            'message': 'Session expired. This window will close automatically.',
        })
    except signing.BadSignature:
        logger.error("OAuth state token has invalid signature")
        return render(request, 'social_connections/oauth_callback.html', {
            **template_context,
            'success': False,
            'error': 'invalid_state',
            'message': 'Invalid state token. This window will close automatically.',
        })

    # Clean up old codes (older than 10 minutes)
    cutoff = timezone.now() - timezone.timedelta(minutes=10)
    expired_codes = [k for k, v in _used_oauth_codes.items() if v <= cutoff]
    for expired_code in expired_codes:
        del _used_oauth_codes[expired_code]

    if expired_codes:
        logger.debug(f"Cleaned up {len(expired_codes)} expired OAuth codes")

    # Check if this code has already been used
    if code in _used_oauth_codes:
        logger.warning("OAuth code already used, rejecting duplicate request")
        return render(request, 'social_connections/oauth_callback.html', {
            **template_context,
            'success': False,
            'error': 'code_already_used',
            'message': 'This code has already been used. This window will close automatically.',
        })

    # Mark code as used immediately
    _used_oauth_codes[code] = timezone.now()
    logger.debug(f"Marked OAuth code as used ({len(_used_oauth_codes)} codes in cache)")

    # Exchange code for access token
    logger.debug("Attempting to exchange OAuth code for access token")
    token_url = "https://github.com/login/oauth/access_token"
    token_params = {
        'client_id': settings.GITHUB_CLIENT_ID,
        'client_secret': settings.GITHUB_CLIENT_SECRET,
        'code': code,
        'redirect_uri': settings.GITHUB_REDIRECT_URI
    }

    headers = {'Accept': 'application/json'}

    try:
        with trace_external('github', 'token_exchange'):
            token_response = requests.post(token_url, data=token_params, headers=headers)
            token_response.raise_for_status()
            token_data = token_response.json()

        if 'error' in token_data:
            logger.error("GitHub token exchange error")
            if token_data.get('error') == 'bad_verification_code':
                return render(request, 'social_connections/oauth_callback.html', {
                    **template_context,
                    'success': False,
                    'error': 'code_already_used',
                    'message': 'This code has already been used. This window will close automatically.',
                })
            return render(request, 'social_connections/oauth_callback.html', {
                **template_context,
                'success': False,
                'error': 'token_exchange_failed',
                'message': 'Failed to exchange token. This window will close automatically.',
            })

        access_token = token_data.get('access_token')
        if not access_token:
            logger.error("No access token received from GitHub")
            return render(request, 'social_connections/oauth_callback.html', {
                **template_context,
                'success': False,
                'error': 'no_access_token',
                'message': 'No access token received. This window will close automatically.',
            })

        # Fetch GitHub user data
        user_url = "https://api.github.com/user"
        user_headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/json'
        }

        with trace_external('github', 'get_user'):
            user_response = requests.get(user_url, headers=user_headers)
            user_response.raise_for_status()
            github_user = user_response.json()

        # Get user from state token
        if not user_id:
            logger.error("No user_id in state token")
            return render(request, 'social_connections/oauth_callback.html', {
                **template_context,
                'success': False,
                'error': 'invalid_state',
                'message': 'Invalid authentication state. This window will close automatically.',
            })

        try:
            user = User.objects.get(id=user_id)
            logger.debug("Found user from state token")
        except User.DoesNotExist:
            logger.error("User from state not found")
            return render(request, 'social_connections/oauth_callback.html', {
                **template_context,
                'success': False,
                'error': 'user_not_found',
                'message': 'User not found. This window will close automatically.',
            })

        # Check if this GitHub account is already linked to another user
        existing_connection = GitHubConnection.objects.filter(
            platform_user_id=str(github_user['id'])
        ).exclude(user=user).first()

        if existing_connection:
            logger.warning("GitHub account already linked to another user")
            return render(request, 'social_connections/oauth_callback.html', {
                **template_context,
                'success': False,
                'error': 'already_linked',
                'message': 'GitHub account already linked. This window will close automatically.',
            })

        # Create or update GitHubConnection
        connection, created = GitHubConnection.objects.update_or_create(
            user=user,
            defaults={
                'username': github_user['login'],
                'platform_user_id': str(github_user['id']),
                'access_token': encrypt_token(access_token),
                'linked_at': timezone.now()
            }
        )

        logger.debug("GitHub account linked successfully")
        return render(request, 'social_connections/oauth_callback.html', {
            **template_context,
            'success': True,
            'error': '',
            'message': 'GitHub account linked successfully! This window will close automatically.',
        })

    except requests.RequestException as e:
        logger.error(f"GitHub API request failed: {e}")
        return render(request, 'social_connections/oauth_callback.html', {
            **template_context,
            'success': False,
            'error': 'api_request_failed',
            'message': 'API request failed. This window will close automatically.',
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disconnect_github(request):
    """Disconnect GitHub account from user profile."""
    try:
        user = request.user
        try:
            connection = user.github_connection
            connection.delete()
            logger.debug("GitHub connection deleted")
        except GitHubConnection.DoesNotExist:
            pass  # No connection to delete

        return Response({
            'message': 'GitHub account disconnected successfully'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Failed to disconnect GitHub: {e}")
        return Response({
            'error': 'Failed to disconnect GitHub account'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_repo_star(request):
    """Check if user has starred the required repository."""
    user = request.user

    # Try to get GitHub connection
    try:
        connection = user.github_connection
        github_username = connection.username
        github_access_token = connection.access_token
    except GitHubConnection.DoesNotExist:
        return Response({
            'has_starred': False,
            'repo': settings.GITHUB_REPO_TO_STAR,
            'error': 'GitHub account not linked'
        }, status=status.HTTP_200_OK)

    if not github_username:
        return Response({
            'has_starred': False,
            'repo': settings.GITHUB_REPO_TO_STAR,
            'error': 'GitHub account not linked'
        }, status=status.HTTP_200_OK)

    try:
        headers = {'Accept': 'application/json'}
        if github_access_token:
            try:
                token = decrypt_token(github_access_token)
                headers['Authorization'] = f'token {token}'
            except InvalidToken:
                logger.warning("Failed to decrypt GitHub token, clearing token")
                connection.access_token = ''
                connection.save()

        # Parse the repo owner and name
        repo_parts = settings.GITHUB_REPO_TO_STAR.split('/')
        if len(repo_parts) != 2:
            logger.error(f"Invalid GITHUB_REPO_TO_STAR format: {settings.GITHUB_REPO_TO_STAR}")
            return Response({
                'error': 'Invalid repository configuration'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        owner, repo = repo_parts

        # Check if user has starred the specific repo
        if github_access_token and 'Authorization' in headers:
            url = f'https://api.github.com/user/starred/{owner}/{repo}'
            with trace_external('github', 'check_star'):
                response = requests.get(url, headers=headers)
            has_starred = response.status_code == 204
        else:
            url = f'https://api.github.com/users/{github_username}/starred'
            with trace_external('github', 'check_star_public'):
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
            'github_username': github_username
        }, status=status.HTTP_200_OK)

    except requests.RequestException as e:
        logger.error(f"Failed to check star status: {e}")
        return Response({
            'has_starred': False,
            'repo': settings.GITHUB_REPO_TO_STAR,
            'error': 'Failed to check star status'
        }, status=status.HTTP_200_OK)
