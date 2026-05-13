"""GitHub OAuth views — thin wrappers around GitHubOAuthService."""

from urllib.parse import urlencode

import requests
from django.conf import settings
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from tally.middleware.logging_utils import get_app_logger

from .oauth_service import GitHubOAuthService
from .serializers import GitHubConnectionSerializer

logger = get_app_logger('github_oauth')
service = GitHubOAuthService()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def github_oauth_initiate(request):
    """Initiate GitHub OAuth flow — full-page redirect."""
    redirect_url = request.GET.get('redirect', settings.FRONTEND_URL)

    state = service.generate_state(request.user.id, extra_data={
        'redirect_url': redirect_url,
    })

    params = {
        'client_id': service.get_client_id(),
        'redirect_uri': service.get_redirect_uri(),
        'scope': '',
        'state': state,
        'allow_signup': 'false',
    }

    return redirect(f"{service.authorize_url}?{urlencode(params)}")


@csrf_exempt
def github_oauth_callback(request):
    """Handle GitHub OAuth callback."""
    return service.handle_callback(request)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disconnect_github(request):
    """Disconnect GitHub account."""
    from .models import GitHubConnection
    try:
        connection = GitHubConnection.objects.get(user=request.user)
        connection.delete()
        logger.debug("GitHub connection deleted")
    except GitHubConnection.DoesNotExist:
        pass

    return Response({'message': 'GitHub account disconnected successfully'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refresh_github_username(request):
    """Refresh the linked GitHub username from GitHub's current user API."""
    from .models import GitHubConnection

    try:
        connection = request.user.githubconnection
    except GitHubConnection.DoesNotExist:
        return Response({
            'error': 'GitHub account not linked',
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        connection, changed = service.refresh_connection_username(connection)
    except ValueError as e:
        error_code = str(e)
        if error_code in ('missing_access_token', 'invalid_access_token'):
            return Response({
                'error': 'GitHub authorization is no longer valid. Please reconnect GitHub.',
                'code': error_code,
            }, status=status.HTTP_400_BAD_REQUEST)
        if error_code == 'account_mismatch':
            logger.warning(
                "GitHub refresh returned a different account for user %s",
                request.user.id,
            )
            return Response({
                'error': 'GitHub account mismatch. Please reconnect GitHub.',
                'code': error_code,
            }, status=status.HTTP_409_CONFLICT)
        logger.error(f"Failed to refresh GitHub username: {e}")
        return Response({
            'error': 'Failed to refresh GitHub username',
        }, status=status.HTTP_400_BAD_REQUEST)
    except requests.RequestException as e:
        logger.error(f"GitHub API request failed while refreshing username: {e}")
        return Response({
            'error': 'Failed to reach GitHub. Please try again.',
        }, status=status.HTTP_502_BAD_GATEWAY)

    return Response({
        'message': 'GitHub username refreshed successfully',
        'changed': changed,
        'github_connection': GitHubConnectionSerializer(connection).data,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_repo_star(request):
    """Check if user has starred the required repository."""
    from .models import GitHubConnection

    try:
        connection = request.user.githubconnection
    except GitHubConnection.DoesNotExist:
        return Response({
            'has_starred': False,
            'repo': settings.GITHUB_REPO_TO_STAR,
            'error': 'GitHub account not linked',
        }, status=status.HTTP_200_OK)

    try:
        has_starred = service.check_repo_star(connection)
        if has_starred is None:
            return Response({
                'error': 'Invalid repository configuration',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'has_starred': has_starred,
            'repo': settings.GITHUB_REPO_TO_STAR,
            'github_username': connection.platform_username,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Failed to check star status: {e}")
        return Response({
            'has_starred': False,
            'repo': settings.GITHUB_REPO_TO_STAR,
            'error': 'Failed to check star status',
        }, status=status.HTTP_200_OK)
