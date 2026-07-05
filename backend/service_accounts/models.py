import hashlib
import secrets

from django.db import models

from utils.models import BaseModel


class ServiceAccount(BaseModel):
    """A machine identity for server-to-server API access.

    Acts as the DRF request principal when one of its tokens authenticates.
    It is not a User and must never become one: it has no password, no
    session, and no relation to django.contrib.auth.
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def __str__(self):
        return self.name


class ServiceAccountToken(BaseModel):
    """A scoped bearer token for a service account.

    Only the SHA-256 digest of the plaintext token is stored; the plaintext
    is shown once at issuance and looked up directly by its unique digest.
    Rotation = issue a new token + revoke the old one; there are no in-place
    secret updates.
    """

    service_account = models.ForeignKey(
        ServiceAccount,
        on_delete=models.CASCADE,
        related_name='tokens',
    )
    digest = models.CharField(max_length=64, unique=True)
    scopes = models.JSONField(default=list)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.service_account} ({self.identifier})'

    @property
    def identifier(self):
        """Short non-secret handle for admin/audit display."""
        return self.digest[:8]

    @staticmethod
    def hash_token(plaintext):
        # Plain SHA-256 (not salted_hmac): the secret has 256 bits of entropy,
        # and this survives SECRET_KEY rotation.
        return hashlib.sha256(plaintext.encode('utf-8')).hexdigest()

    @classmethod
    def issue(cls, service_account, scopes, expires_at=None):
        """Create a token and return (token, plaintext)."""
        plaintext = f'sa_{secrets.token_urlsafe(32)}'
        token = cls.objects.create(
            service_account=service_account,
            digest=cls.hash_token(plaintext),
            scopes=list(scopes),
            expires_at=expires_at,
        )
        return token, plaintext

    def has_scope(self, scope):
        return scope in (self.scopes or [])

    def is_usable(self, now):
        return self.revoked_at is None and (
            self.expires_at is None or self.expires_at > now
        )
