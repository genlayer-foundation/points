"""
GitHub OAuth authentication handling
"""
import os
import json
import secrets
import logging
from datetime import datetime
from urllib.parse import urlencode, parse_qs, urlparse

import requests
from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from cryptography.fernet import Fernet
from .models import User

logger = logging.getLogger(__name__)

# Initialize encryption for tokens
def get_fernet():
    """Get or create Fernet encryption instance"""
    key = settings.GITHUB_ENCRYPTION_KEY
    if not key:
        # Generate a key if not set (for development)
        key = Fernet.generate_key().decode()
        logger.warning("Using generated encryption key - set GITHUB_ENCRYPTION_KEY in production")
    else:
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
@permission_classes([AllowAny])  # Allow anyone to initiate, we'll check session in callback
def github_oauth_initiate(request):
    """Initiate GitHub OAuth flow"""
    # Get the return URL from query params
    return_url = request.GET.get('return_url', '/builders/welcome')

    # Get user ID from session if authenticated
    user_id = None
    if request.user and request.user.is_authenticated:
        user_id = request.user.id
        logger.info(f"GitHub OAuth initiated by authenticated user {user_id}")
    else:
        logger.info("GitHub OAuth initiated by anonymous user")

    # Generate state token with return URL embedded
    state_data = {
        'return_url': return_url,
        'user_id': user_id,
        'nonce': secrets.token_urlsafe(32)
    }
    state = json.dumps(state_data)

    # Store state in session for validation
    request.session['github_oauth_state'] = state

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

    # Handle errors from GitHub
    if error:
        logger.error(f"GitHub OAuth error: {error} - {error_description}")
        return redirect(f'{settings.FRONTEND_URL}/#/builders/welcome?github_error=authorization_failed')

    # Validate state
    stored_state = request.session.get('github_oauth_state')
    if not state or state != stored_state:
        logger.error("Invalid OAuth state token")
        return redirect(f'{settings.FRONTEND_URL}/#/builders/welcome?github_error=invalid_state')

    # Clear the state from session to prevent replay attacks
    del request.session['github_oauth_state']

    # Parse state data
    try:
        state_data = json.loads(state)
        return_url = state_data.get('return_url', '/builders/welcome')
        user_id = state_data.get('user_id')
    except json.JSONDecodeError:
        logger.error("Failed to parse OAuth state")
        return redirect(f'{settings.FRONTEND_URL}/#/builders/welcome?github_error=invalid_state')

    # Exchange code for access token
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
                return redirect(f"{settings.FRONTEND_URL}/#/builders/welcome?github_error=code_already_used")
            return redirect(f"{settings.FRONTEND_URL}/#/builders/welcome?github_error=token_exchange_failed")

        access_token = token_data.get('access_token')
        if not access_token:
            logger.error("No access token received from GitHub")
            return redirect(f"{settings.FRONTEND_URL}/#/builders/welcome?github_error=no_access_token")

        # Fetch GitHub user data
        user_url = "https://api.github.com/user"
        user_headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/json'
        }

        user_response = requests.get(user_url, headers=user_headers)
        user_response.raise_for_status()
        github_user = user_response.json()

        # Get or update user
        # First try to get user from state, then from current session
        user = None
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                logger.info(f"Found user {user.id} from state")
            except User.DoesNotExist:
                logger.error(f"User {user_id} not found from state")

        # If no user from state, try to get from current request session
        # Get authenticated user from Django's auth middleware
        if not user:
            from django.contrib.auth import get_user
            session_user = get_user(request)
            if session_user and session_user.is_authenticated:
                user = session_user
                logger.info(f"Found user {user.id} from current session")

        if user:
            # Check if this GitHub account is already linked to another user
            existing_user = User.objects.filter(
                github_user_id=str(github_user['id'])
            ).exclude(id=user.id).first()

            if existing_user:
                logger.warning(f"GitHub account already linked to another user")
                return redirect(f"{settings.FRONTEND_URL}/#/builders/welcome?github_error=already_linked")

            # Update user with GitHub info
            user.github_username = github_user['login']
            user.github_user_id = str(github_user['id'])
            user.github_access_token = encrypt_token(access_token)
            user.github_linked_at = timezone.now()
            user.save()

            logger.info(f"GitHub account linked for user {user.id}")
            return redirect(f"{settings.FRONTEND_URL}/#/builders/welcome?github_success=true")
        else:
            # User not authenticated, redirect to login
            logger.warning("No authenticated user found for GitHub linking")
            return redirect(f'{settings.FRONTEND_URL}/#/builders/welcome?github_error=not_authenticated')

    except requests.RequestException as e:
        logger.error(f"GitHub API request failed: {e}")
        return redirect(f"{settings.FRONTEND_URL}/#/builders/welcome?github_error=api_request_failed")
    except Exception as e:
        logger.error(f"Unexpected error during GitHub OAuth: {e}")
        return redirect(f"{settings.FRONTEND_URL}/#/builders/welcome?github_error=unexpected_error")
    finally:
        # Clean up session
        if 'github_oauth_state' in request.session:
            del request.session['github_oauth_state']


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
def github_status(request):
    """Check if user has GitHub linked"""
    user = request.user
    return Response({
        'linked': bool(user.github_username),
        'username': user.github_username,
        'linked_at': user.github_linked_at
    }, status=status.HTTP_200_OK)


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
            except Exception as e:
                # Token decryption failed, likely due to encryption key change
                # Clear the invalid token
                logger.warning(f"Failed to decrypt GitHub token for user {user.username}, clearing token: {e}")
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def github_starred_repos(request):
    """Get user's starred repositories from GitHub"""
    user = request.user

    if not user.github_username:
        return Response({
            'error': 'GitHub account not linked'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Use the stored access token if available, otherwise use public API
        headers = {'Accept': 'application/json'}
        if user.github_access_token:
            try:
                token = decrypt_token(user.github_access_token)
                headers['Authorization'] = f'token {token}'
            except Exception as e:
                # Token decryption failed, likely due to encryption key change
                logger.warning(f"Failed to decrypt GitHub token for user {user.username}, clearing token: {e}")
                user.github_access_token = ''
                user.save()
                # Continue without auth header to use public API

        # GitHub API endpoint for starred repos (public info)
        url = f'https://api.github.com/users/{user.github_username}/starred'

        # Get first page of starred repos (up to 30)
        params = {'per_page': 30, 'page': 1}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        starred_repos = response.json()

        # Extract relevant info from each repo
        repos_data = []
        for repo in starred_repos:
            repos_data.append({
                'name': repo['name'],
                'full_name': repo['full_name'],
                'description': repo['description'],
                'stars': repo['stargazers_count'],
                'language': repo['language'],
                'url': repo['html_url']
            })

        return Response({
            'username': user.github_username,
            'starred_count': len(repos_data),
            'starred_repos': repos_data
        }, status=status.HTTP_200_OK)

    except requests.RequestException as e:
        logger.error(f"Failed to fetch starred repos for {user.github_username}: {e}")
        return Response({
            'error': 'Failed to fetch starred repositories'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)