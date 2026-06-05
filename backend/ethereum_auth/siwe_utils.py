from urllib.parse import urlparse

from django.conf import settings


def normalize_origin(value):
    return (value or '').strip().rstrip('/')


def _host_from_value(value):
    value = normalize_origin(value)
    if not value:
        return ''
    parsed = urlparse(value if '://' in value else f'//{value}')
    return parsed.netloc or parsed.path


def _hostname_from_host(host):
    if not host:
        return ''
    parsed = urlparse(f'//{host}')
    return parsed.hostname or host.split(':', 1)[0]


def get_expected_siwe_domain():
    """Return the SIWE domain expected in frontend-signed messages.

    Local configs often set SIWE_DOMAIN=localhost while the browser signs with
    window.location.host (localhost:5173). If the configured SIWE_DOMAIN is the
    same hostname as FRONTEND_URL but omits the port, use FRONTEND_URL's host.
    Otherwise, keep the explicit SIWE_DOMAIN value.
    """
    configured_domain = _host_from_value(settings.ETHEREUM_AUTH.get('SIWE_DOMAIN', ''))
    frontend_domain = _host_from_value(getattr(settings, 'FRONTEND_URL', ''))

    if not configured_domain:
        return frontend_domain
    if not frontend_domain:
        return configured_domain
    if configured_domain == frontend_domain:
        return configured_domain
    if configured_domain == _hostname_from_host(frontend_domain):
        return frontend_domain
    return configured_domain


def get_expected_siwe_uri():
    return normalize_origin(settings.FRONTEND_URL)
