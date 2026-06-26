"""Thin client for the Sorsa API.

Sorsa is the third-party we use to verify Twitter / X social actions
(follow, like, repost) without burning the user's own X API quota.

Only two settings live as env vars:

    SORSA_API_KEY        API key sent in the ApiKey header (secret, required)
    SORSA_API_BASE_URL   default: https://api.sorsa.io/v3  (in case staging
                         ever needs a different host)

The endpoint path, timeout, and response shape are code constants — if
Sorsa changes its contract, the response parser below must change with
it, so making them env-tunable would just spread one change across two
places.
"""

from __future__ import annotations

import logging
from http import cookiejar
from typing import Any

import requests
from django.conf import settings

from tally.middleware.tracing import trace_external

logger = logging.getLogger(__name__)


# Code constants — wire shape lives next to the parser below so any change
# to Sorsa's contract is a one-file diff.
SORSA_FOLLOW_PATH = '/check-follow'
SORSA_TWEET_INFO_PATH = '/tweet-info'
SORSA_TIMEOUT_SECONDS = 8.0


class SorsaError(Exception):
    """Raised for any Sorsa transport / parse failure."""


class SorsaClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
        follow_path: str | None = None,
        session: requests.Session | None = None,
    ):
        self.base_url = (base_url or getattr(settings, 'SORSA_API_BASE_URL', '') or '').rstrip('/')
        self.api_key = api_key or getattr(settings, 'SORSA_API_KEY', '') or ''
        self.timeout = timeout if timeout is not None else SORSA_TIMEOUT_SECONDS
        self.follow_path = follow_path or SORSA_FOLLOW_PATH
        if session is None:
            session = requests.Session()
            # The default client is a module singleton shared across threads;
            # a shared cookie jar is not thread-safe and could replay one
            # request's cookies on another. Sorsa auth is header-based, so
            # refuse cookies entirely.
            session.cookies.set_policy(
                cookiejar.DefaultCookiePolicy(allowed_domains=[])
            )
        self._session = session

    def is_following(self, actor_handle: str, target_handle: str) -> tuple[bool, dict[str, Any]]:
        """Return (is_following, raw_response_audit) for actor_handle -> target_handle.

        Raises SorsaError on any HTTP, network, or parse failure (caller decides whether
        to surface a 503 or treat as inconclusive).
        """
        if not self.base_url or not self.api_key:
            raise SorsaError('Sorsa is not configured (SORSA_API_BASE_URL / SORSA_API_KEY missing)')

        url = f'{self.base_url}{self.follow_path}'
        payload = {
            # Sorsa asks "does username_2 follow username_1?"
            'username_1': target_handle.lstrip('@'),
            'username_2': actor_handle.lstrip('@'),
        }
        headers = {
            'ApiKey': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        try:
            with trace_external('sorsa', 'check_follow'):
                response = self._session.post(
                    url, json=payload, headers=headers, timeout=self.timeout
                )
        except requests.RequestException as exc:
            raise SorsaError(f'Sorsa request failed: {exc}') from exc

        if response.status_code >= 500:
            raise SorsaError(f'Sorsa returned {response.status_code}')
        if response.status_code == 401 or response.status_code == 403:
            raise SorsaError(f'Sorsa auth failed ({response.status_code})')

        try:
            data = response.json()
        except ValueError as exc:
            raise SorsaError('Sorsa returned non-JSON response') from exc

        if response.status_code >= 400:
            raise SorsaError(f'Sorsa error {response.status_code}: {data}')

        # Strict type check: a schema change at Sorsa must surface as a loud
        # SorsaError (-> 503, user retries later), not silently read as
        # "not following" for every check.
        is_following = data.get('follow')
        if not isinstance(is_following, bool):
            raise SorsaError('Unexpected follow value')
        audit = {
            'status_code': response.status_code,
            'response': data,
            'actor_handle': payload['username_2'],
            'target_handle': payload['username_1'],
        }
        return is_following, audit

    def get_tweet(self, tweet_link: str) -> dict[str, str] | None:
        """Fetch a single tweet via POST /tweet-info.

        `tweet_link` accepts a full tweet URL or a bare tweet id.
        Returns {'full_text': str, 'username': str} (username without @), or
        None when the tweet is not found / deleted (404 — a verification
        failure, not an outage). Raises SorsaError on transport / auth / server
        / parse failures so the caller can surface a retryable 503.
        """
        if not self.base_url or not self.api_key:
            raise SorsaError('Sorsa is not configured (SORSA_API_BASE_URL / SORSA_API_KEY missing)')

        url = f'{self.base_url}{SORSA_TWEET_INFO_PATH}'
        headers = {
            'ApiKey': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        try:
            with trace_external('sorsa', 'tweet_info'):
                response = self._session.post(
                    url, json={'tweet_link': tweet_link}, headers=headers, timeout=self.timeout
                )
        except requests.RequestException as exc:
            raise SorsaError(f'Sorsa request failed: {exc}') from exc

        if response.status_code == 404:
            return None
        if response.status_code >= 500:
            raise SorsaError(f'Sorsa returned {response.status_code}')
        if response.status_code in (401, 403):
            raise SorsaError(f'Sorsa auth failed ({response.status_code})')

        try:
            data = response.json()
        except ValueError as exc:
            raise SorsaError('Sorsa returned non-JSON response') from exc

        if response.status_code >= 400:
            raise SorsaError(f'Sorsa error {response.status_code}: {data}')

        full_text = data.get('full_text')
        if not isinstance(full_text, str):
            raise SorsaError('Unexpected tweet-info response (no full_text)')
        user_payload = data.get('user')
        if not isinstance(user_payload, dict):
            raise SorsaError('Unexpected tweet-info response (no user object)')
        username = (user_payload.get('username') or '').lstrip('@')
        return {'full_text': full_text, 'username': username}


_default_client: SorsaClient | None = None


def get_default_client() -> SorsaClient:
    global _default_client
    if _default_client is None:
        _default_client = SorsaClient()
    return _default_client
