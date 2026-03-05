"""
Shared encryption utilities for social connection tokens.
"""
from django.conf import settings
from cryptography.fernet import Fernet


def get_fernet():
    """
    Get Fernet encryption instance using configured key.

    Uses SOCIAL_ENCRYPTION_KEY setting, falling back to GITHUB_ENCRYPTION_KEY
    for backward compatibility.
    """
    key = getattr(settings, 'SOCIAL_ENCRYPTION_KEY', None) or \
          getattr(settings, 'GITHUB_ENCRYPTION_KEY', None)

    if not key:
        raise RuntimeError(
            "SOCIAL_ENCRYPTION_KEY is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

    key = key.encode() if isinstance(key, str) else key
    return Fernet(key)


def encrypt_token(token):
    """Encrypt a token for secure storage."""
    if not token:
        return ""
    fernet = get_fernet()
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token):
    """Decrypt a stored token."""
    if not encrypted_token:
        return ""
    fernet = get_fernet()
    return fernet.decrypt(encrypted_token.encode()).decode()
