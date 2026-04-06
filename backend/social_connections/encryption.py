"""Shared encryption for OAuth token storage using Fernet symmetric encryption."""

from django.conf import settings
from cryptography.fernet import Fernet


def get_fernet():
    """Get Fernet encryption instance. Uses SOCIAL_ENCRYPTION_KEY with fallback to GITHUB_ENCRYPTION_KEY."""
    key = getattr(settings, 'SOCIAL_ENCRYPTION_KEY', '') or getattr(settings, 'GITHUB_ENCRYPTION_KEY', '')
    if not key:
        raise RuntimeError(
            "SOCIAL_ENCRYPTION_KEY (or GITHUB_ENCRYPTION_KEY) is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    key = key.encode() if isinstance(key, str) else key
    return Fernet(key)


def encrypt_token(token):
    """Encrypt a token for storage. Returns empty string for empty input."""
    if not token:
        return ""
    fernet = get_fernet()
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token):
    """Decrypt a stored token. Returns empty string for empty input."""
    if not encrypted_token:
        return ""
    fernet = get_fernet()
    return fernet.decrypt(encrypted_token.encode()).decode()
