"""GitHub repository star verifier.

Requires the user to have linked their GitHub account; the target repository
comes from `SocialTask.target_repo` as `owner/repo`.

The Discord precedent applies here too: we call the GitHub API inline rather
than reusing `GitHubOAuthService.check_repo_star`, because that helper
collapses 401/403/5xx into "not starred" and silently falls back to an
unpaginated public listing. We need to distinguish statuses so the frontend
can prompt re-link on dead tokens and retry on service errors.

`GET /user/starred/{owner}/{repo}` works with the portal's empty-scope OAuth
tokens (starred repos are public data): 204 starred, 404 not starred,
401 bad credentials, 403 rate-limited.
"""

import logging
import re

import requests
from cryptography.fernet import InvalidToken
from django.utils import timezone

from social_connections.encryption import decrypt_token
from tally.middleware.tracing import trace_external

from .base import Verifier, VerifierResult, register

logger = logging.getLogger(__name__)


GITHUB_STARRED_URL = 'https://api.github.com/user/starred/{repo}'
GITHUB_REQUEST_TIMEOUT = 8.0

# owner/repo: GitHub owner is alphanumeric + hyphens, repo also allows . and _
REPO_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._-]+$')


@register
class GitHubStarVerifier(Verifier):
    verification_type = 'github_star'
    label = 'Star a GitHub repository'
    platform = 'github'
    required_fields = ('target_repo',)
    requires_verification = True
    required_connection = 'github'

    def clean_task(self, task) -> dict[str, str]:
        repo = (task.target_repo or '').strip()
        if not REPO_RE.match(repo):
            return {'target_repo': 'Must be in owner/repo format (e.g. genlayer-foundation/points).'}
        return {}

    def verify(self, task, user) -> VerifierResult:
        connection = getattr(user, 'githubconnection', None)
        if connection is None:
            return VerifierResult(False, {'platform': 'github'}, 'social_account_not_linked')

        if not connection.access_token:
            return VerifierResult(False, {'platform': 'github'}, 'token_invalid_relink_required')

        try:
            token = decrypt_token(connection.access_token)
        except InvalidToken:
            logger.warning('Failed to decrypt GitHub token for user %s', user.pk)
            return VerifierResult(False, {'platform': 'github'}, 'token_invalid_relink_required')

        repo = (task.target_repo or '').strip().strip('/')
        if not repo:
            logger.error('GitHub repo missing for task %s', task.slug)
            return VerifierResult(False, {}, 'verification_unavailable')

        try:
            with trace_external('github', 'check_star'):
                response = requests.get(
                    GITHUB_STARRED_URL.format(repo=repo),
                    headers={
                        'Authorization': f'token {token}',
                        'Accept': 'application/vnd.github+json',
                    },
                    timeout=GITHUB_REQUEST_TIMEOUT,
                )
        except requests.RequestException as exc:
            logger.warning('GitHub star check transport error for user %s: %s', user.pk, exc)
            return VerifierResult(
                False,
                {'platform': 'github', 'repo': repo, 'error': str(exc)},
                'verification_unavailable',
            )

        audit = {
            'kind': 'github_star',
            'repo': repo,
            'status_code': response.status_code,
            'checked_at': timezone.now().isoformat(),
        }

        if response.status_code == 204:
            return VerifierResult(True, audit, None)

        if response.status_code == 404:
            return VerifierResult(False, audit, 'verification_failed')

        if response.status_code == 401:
            logger.warning(
                'GitHub token rejected during star check for user %s', user.pk,
            )
            return VerifierResult(
                False,
                {**audit, 'platform': 'github'},
                'token_invalid_relink_required',
            )

        # 403 is GitHub's rate-limit status; 429/5xx and anything else are
        # service issues. All retryable, none the user's fault.
        logger.error(
            'GitHub star check returned status %s for task %s',
            response.status_code, task.slug,
        )
        return VerifierResult(False, audit, 'verification_unavailable')
