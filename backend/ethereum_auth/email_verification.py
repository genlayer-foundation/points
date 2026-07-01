import base64
import hashlib
import hmac
import logging
import math
import secrets
from dataclasses import dataclass

import requests
from cryptography.fernet import Fernet
from disposable_email_domains import blocklist
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.utils.html import escape
from django.utils import timezone
from email_validator import EmailNotValidError, validate_email
from rest_framework import serializers

from .models import EmailVerificationToken, PendingWalletSignup

User = get_user_model()
logger = logging.getLogger(__name__)
GENERIC_EMAIL_ERROR = 'Enter a valid email address that can receive mail.'
PLACEHOLDER_DOMAIN = 'ethereum.address'


@dataclass
class EmailPreflightResult:
    email: str
    fingerprint: str


class TurnstileVerifier:
    verify_url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'

    def verify(self, token, remote_ip=None):
        if settings.DEBUG and token == 'debug-pass':
            return True
        if not token:
            raise serializers.ValidationError({'turnstile_token': 'Verification is required.'})
        if not settings.TURNSTILE_SECRET_KEY:
            if settings.DEBUG:
                return True
            raise serializers.ValidationError({'turnstile_token': 'Verification is unavailable.'})

        try:
            response = requests.post(
                self.verify_url,
                data={
                    'secret': settings.TURNSTILE_SECRET_KEY,
                    'response': token,
                    'remoteip': remote_ip or '',
                },
                timeout=5,
            )
            payload = response.json()
        except Exception as exc:
            logger.warning("Turnstile siteverify request failed: %s", exc)
            raise serializers.ValidationError({'turnstile_token': 'Verification failed.'})

        if not payload.get('success'):
            logger.warning(
                "Turnstile rejected token: errors=%s hostname=%s",
                payload.get('error-codes', []),
                payload.get('hostname', ''),
            )
            raise serializers.ValidationError({'turnstile_token': 'Verification failed.'})

        allowed = getattr(settings, 'TURNSTILE_ALLOWED_HOSTNAMES', [])
        hostname = payload.get('hostname')
        if allowed and hostname not in allowed:
            logger.warning("Turnstile hostname rejected: hostname=%s allowed=%s", hostname, allowed)
            raise serializers.ValidationError({'turnstile_token': 'Verification failed.'})
        return True


class EmailPreflightValidator:
    def validate(self, email, *, user=None, pending_signup=None):
        try:
            valid = validate_email(
                email or '',
                check_deliverability=True,
                test_environment=False,
                globally_deliverable=True,
                allow_domain_literal=False,
                timeout=10,
            )
        except EmailNotValidError:
            raise serializers.ValidationError({'email': GENERIC_EMAIL_ERROR})

        normalized = valid.normalized
        domain = valid.domain.lower()
        if domain == PLACEHOLDER_DOMAIN or domain in blocklist:
            raise serializers.ValidationError({'email': GENERIC_EMAIL_ERROR})

        queryset = User.objects.filter(email__iexact=normalized, is_email_verified=True)
        if user is not None:
            queryset = queryset.exclude(pk=user.pk)
        if queryset.exists():
            raise serializers.ValidationError({'email': 'This email is already in use.'})

        fingerprint = email_fingerprint(normalized)
        active = EmailVerificationToken.objects.filter(
            email_fingerprint=fingerprint,
            consumed_at__isnull=True,
            expires_at__gt=timezone.now(),
        )
        if user is not None:
            active = active.exclude(user=user)
        if pending_signup is not None:
            active = active.exclude(pending_signup=pending_signup)
        if active.exists():
            raise serializers.ValidationError({'email': 'This email is already being verified.'})

        return EmailPreflightResult(email=normalized, fingerprint=fingerprint)


def email_fingerprint(email):
    key = settings.EMAIL_VERIFICATION_HMAC_KEY.encode()
    return hmac.new(key, email.lower().encode(), hashlib.sha256).hexdigest()


def token_lookup_hash(raw_token):
    key = settings.EMAIL_VERIFICATION_HMAC_KEY.encode()
    return hmac.new(key, (raw_token or '').encode(), hashlib.sha256).hexdigest()


def _fernet():
    key = settings.EMAIL_VERIFICATION_ENCRYPTION_KEY
    if not key:
        digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode())


def encrypt_email(email):
    return _fernet().encrypt(email.encode()).decode()


def decrypt_email(encrypted_email):
    return _fernet().decrypt(encrypted_email.encode()).decode()


def _generate_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def cooldown_validation_error(elapsed_seconds):
    remaining = max(1, math.ceil(settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS - elapsed_seconds))
    return serializers.ValidationError({
        'detail': 'Please wait before requesting another verification email.',
        'cooldown_seconds': remaining,
    })


class EmailVerificationService:
    preflight = EmailPreflightValidator()

    def ensure_pending_signup_can_send(self, pending_signup):
        self._ensure_pending_signup_active(pending_signup)
        self._enforce_pending_cooldown(pending_signup)

    def ensure_existing_user_can_send(self, user):
        existing = EmailVerificationToken.objects.filter(
            purpose=EmailVerificationToken.PURPOSE_EXISTING_USER,
            user=user,
            consumed_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).order_by('-last_sent_at').first()
        now = timezone.now()
        if existing:
            elapsed = (now - existing.last_sent_at).total_seconds()
            if elapsed < settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS:
                raise cooldown_validation_error(elapsed)

    def start_for_pending_signup(self, pending_signup, email, *, profile_data=None):
        self._ensure_pending_signup_active(pending_signup)
        self._enforce_pending_cooldown(pending_signup)
        result = self.preflight.validate(email, pending_signup=pending_signup)
        if profile_data is not None:
            pending_signup.profile_data = _clean_profile_data(profile_data)
            pending_signup.save(update_fields=['profile_data', 'updated_at'])
        return self._create_or_resend_token(
            purpose=EmailVerificationToken.PURPOSE_PENDING_SIGNUP,
            email_result=result,
            pending_signup=pending_signup,
        )

    def start_for_user(self, user, email):
        result = self.preflight.validate(email, user=user)
        return self._create_or_resend_token(
            purpose=EmailVerificationToken.PURPOSE_EXISTING_USER,
            email_result=result,
            user=user,
        )

    def confirm_pending_signup(self, pending_signup: PendingWalletSignup, raw_code: str) -> User:
        self._ensure_pending_signup_active(pending_signup)
        user, _ = self._confirm_pending_signup_token(raw_code, pending_signup=pending_signup)
        return user

    def _confirm_pending_signup_token(
        self,
        raw_code: str,
        *,
        pending_signup: PendingWalletSignup,
    ) -> tuple[User, PendingWalletSignup]:
        token_error = None
        with transaction.atomic():
            token = self._get_locked_pending_token(raw_code, pending_signup=pending_signup)
            token_pending_signup = token.pending_signup
            self._ensure_pending_signup_active(token_pending_signup)
            try:
                email = self._consume_token(token, raw_code)
            except serializers.ValidationError as exc:
                token_error = exc
                email = None
            if token_error is None:
                self.preflight.validate(email, pending_signup=token_pending_signup)
                self._release_unverified_email_claims(email)
                user = self._create_user_from_pending_signup(token_pending_signup, email)
                token.user = user
                token.save(update_fields=['user', 'updated_at'])
                token_pending_signup.mark_consumed()
                return user, token_pending_signup
        if token_error is not None:
            raise token_error
        raise serializers.ValidationError({'code': 'Invalid or expired verification code.'})

    def confirm_existing_user(self, user: User, raw_code: str) -> User:
        token_error = None
        with transaction.atomic():
            token = self._get_locked_token(
                purpose=EmailVerificationToken.PURPOSE_EXISTING_USER,
                user=user,
            )
            try:
                email = self._consume_token(token, raw_code)
            except serializers.ValidationError as exc:
                token_error = exc
                email = None
            if token_error is None:
                self.preflight.validate(email, user=user)
                self._release_unverified_email_claims(email, except_user=user)
                user.email = email
                user.is_email_verified = True
                user.email_verified_at = timezone.now()
                user.save(update_fields=['email', 'is_email_verified', 'email_verified_at'])
                return user
        if token_error is not None:
            raise token_error
        raise serializers.ValidationError({'code': 'Invalid or expired verification code.'})

    def _create_or_resend_token(self, *, purpose, email_result, user=None, pending_signup=None):
        owner_filter = {'purpose': purpose}
        if user is not None:
            owner_filter['user'] = user
        if pending_signup is not None:
            owner_filter['pending_signup'] = pending_signup

        existing = EmailVerificationToken.objects.filter(
            **owner_filter,
            consumed_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).first()
        now = timezone.now()
        if existing:
            elapsed = (now - existing.last_sent_at).total_seconds()
            if elapsed < settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS:
                raise cooldown_validation_error(elapsed)

        raw_code = _generate_verification_code()
        expires_at = now + timezone.timedelta(seconds=settings.EMAIL_VERIFICATION_TOKEN_TTL_SECONDS)
        with transaction.atomic():
            if existing:
                existing.encrypted_email = encrypt_email(email_result.email)
                existing.email_fingerprint = email_result.fingerprint
                existing.token_lookup_hash = token_lookup_hash(raw_code)
                existing.token_hash = make_password(raw_code)
                existing.attempts = 0
                existing.send_count += 1
                existing.last_sent_at = now
                existing.expires_at = expires_at
                existing.save()
                token = existing
            else:
                token = EmailVerificationToken.objects.create(
                    purpose=purpose,
                    user=user,
                    pending_signup=pending_signup,
                    encrypted_email=encrypt_email(email_result.email),
                    email_fingerprint=email_result.fingerprint,
                    token_lookup_hash=token_lookup_hash(raw_code),
                    token_hash=make_password(raw_code),
                    last_sent_at=now,
                    expires_at=expires_at,
                )

            if pending_signup is not None:
                pending_signup.last_email_sent_at = now
                pending_signup.save(update_fields=['last_email_sent_at', 'updated_at'])

            self._send_code(email_result.email, raw_code, display_name=self._display_name(user, pending_signup))
            return token

    def _display_name(self, user=None, pending_signup=None):
        if user is not None:
            return (getattr(user, 'name', '') or '').strip()
        if pending_signup is not None:
            return str((pending_signup.profile_data or {}).get('name', '')).strip()
        return ''

    def _send_code(self, email: str, code: str, *, display_name: str = '') -> None:
        greeting = f"Hi {display_name}," if display_name else "Hi,"
        ttl_minutes = max(1, settings.EMAIL_VERIFICATION_TOKEN_TTL_SECONDS // 60)
        message = (
            f'{greeting}\n\n'
            'Use this GenLayer Portal verification code:\n\n'
            f'{code}\n\n'
            f'Enter it in the Portal to finish verifying your email. This code expires in {ttl_minutes} minutes.\n\n'
            'If you did not request this, you can ignore this email.'
        )
        email_message = EmailMultiAlternatives(
            subject='Verify your GenLayer Portal email',
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        email_message.attach_alternative(
            self._render_verification_email_html(code, display_name=display_name, ttl_minutes=ttl_minutes),
            'text/html',
        )
        email_message.send(fail_silently=False)

    def _render_verification_email_html(self, code: str, *, display_name: str = '', ttl_minutes: int = 30) -> str:
        safe_code = escape(code)
        safe_name = escape(display_name)
        logo_url = escape(f"{settings.FRONTEND_URL}/assets/gl-logo-black.svg")
        greeting = f"Hi {safe_name}," if safe_name else "Hi,"
        return f"""<!doctype html>
<html>
  <body style="margin:0;background:#f6f6f4;padding:40px 16px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;color:#131214;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;max-width:520px;background:#ffffff;border:1px solid #ececea;border-radius:16px;box-shadow:0 18px 44px rgba(19,18,20,0.08);">
            <tr>
              <td align="center" style="padding:40px 34px 0;">
                <img src="{logo_url}" width="134" height="32" alt="GenLayer" style="display:block;border:0;outline:none;text-decoration:none;width:134px;height:auto;">
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:30px 34px 14px;">
                <h1 style="margin:0;color:#2f2f32;font-size:26px;line-height:1.2;font-weight:700;letter-spacing:0;">Your verification code</h1>
                <p style="margin:12px 0 0;color:#62636a;font-size:15px;line-height:1.55;">{greeting} enter this code in GenLayer Portal to finish verifying your email.</p>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:10px 34px 8px;">
                <div style="display:inline-block;border:1px solid #e6e6e4;border-radius:12px;background:#fbfbfa;padding:13px 18px;color:#252529;font-size:30px;line-height:1;font-weight:650;letter-spacing:10px;text-align:center;">{safe_code}</div>
                <div style="margin-top:12px;color:#77787f;font-size:12px;line-height:1.5;">One-time code. Do not share it with anyone.</div>
              </td>
            </tr>
            <tr>
              <td style="padding:18px 34px 34px;">
                <div style="border-top:1px solid #eeeeec;padding-top:18px;text-align:center;color:#77787f;font-size:12px;line-height:1.6;">
                  This code expires in {ttl_minutes} minutes and can be used once. If you did not request this code, you can ignore this email.
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:0 34px 34px;text-align:center;color:#9a9aa0;font-size:12px;line-height:1.5;">
                This is an automated message. Please do not reply.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""

    def _get_locked_token(self, **filters):
        token = (
            EmailVerificationToken.objects
            .select_for_update()
            .filter(**filters, consumed_at__isnull=True)
            .order_by('-created_at')
            .first()
        )
        if not token:
            raise serializers.ValidationError({'code': 'Invalid or expired verification code.'})
        return token

    def _get_locked_pending_token(
        self,
        raw_code: str,
        *,
        pending_signup: PendingWalletSignup,
    ) -> EmailVerificationToken:
        token = (
            EmailVerificationToken.objects
            .select_for_update()
            .filter(
                purpose=EmailVerificationToken.PURPOSE_PENDING_SIGNUP,
                token_lookup_hash=token_lookup_hash(raw_code),
                consumed_at__isnull=True,
            )
        )
        token = token.filter(pending_signup=pending_signup)
        token = token.order_by('-created_at').first()
        if token:
            return token
        return self._get_locked_token(
            purpose=EmailVerificationToken.PURPOSE_PENDING_SIGNUP,
            pending_signup=pending_signup,
        )

    def _consume_token(self, token: EmailVerificationToken, raw_code: str) -> str:
        now = timezone.now()
        if token.expires_at <= now:
            raise serializers.ValidationError({'code': 'Invalid or expired verification code.'})
        if token.attempts >= settings.EMAIL_VERIFICATION_MAX_ATTEMPTS:
            raise serializers.ValidationError({'code': 'Invalid or expired verification code.'})
        if not check_password(raw_code or '', token.token_hash):
            token.attempts += 1
            token.save(update_fields=['attempts', 'updated_at'])
            raise serializers.ValidationError({'code': 'Invalid or expired verification code.'})

        token.consumed_at = now
        token.save(update_fields=['consumed_at', 'updated_at'])
        return decrypt_email(token.encrypted_email)

    def _ensure_pending_signup_active(self, pending_signup):
        if not pending_signup or not pending_signup.is_active():
            raise serializers.ValidationError({'detail': 'Pending signup has expired.'})

    def _enforce_pending_cooldown(self, pending_signup):
        if not pending_signup.last_email_sent_at:
            return
        elapsed = (timezone.now() - pending_signup.last_email_sent_at).total_seconds()
        if elapsed < settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS:
            raise cooldown_validation_error(elapsed)

    def _release_unverified_email_claims(self, email, *, except_user=None):
        queryset = User.objects.select_for_update().filter(
            email__iexact=email,
            is_email_verified=False,
        )
        if except_user is not None:
            queryset = queryset.exclude(pk=except_user.pk)

        for stale_user in queryset:
            stale_user.email = self._placeholder_email_for_user(stale_user)
            stale_user.is_email_verified = False
            stale_user.email_verified_at = None
            stale_user.save(update_fields=['email', 'is_email_verified', 'email_verified_at'])

    def _placeholder_email_for_user(self, user):
        base = (user.address or '').strip().lower() or f'user-{user.pk}'
        candidate = f'{base}@{PLACEHOLDER_DOMAIN}'
        if not User.objects.filter(email__iexact=candidate).exclude(pk=user.pk).exists():
            return candidate

        for suffix in range(1, 100):
            candidate = f'{base}-{suffix}@{PLACEHOLDER_DOMAIN}'
            if not User.objects.filter(email__iexact=candidate).exclude(pk=user.pk).exists():
                return candidate

        return f'{base}-{secrets.token_hex(4)}@{PLACEHOLDER_DOMAIN}'

    def _create_user_from_pending_signup(self, pending_signup, email):
        profile = pending_signup.profile_data or {}
        user = User.objects.create_user(
            email=email,
            password=None,
            address=pending_signup.address.lower(),
            username=pending_signup.address[:10],
            name=profile.get('name', ''),
            description=profile.get('description', ''),
            website=profile.get('website', ''),
            telegram_handle=profile.get('telegram_handle', ''),
            linkedin_handle=profile.get('linkedin_handle', ''),
            is_email_verified=True,
            email_verified_at=timezone.now(),
        )
        if pending_signup.referral_code:
            try:
                referrer = User.objects.get(referral_code=pending_signup.referral_code.upper())
            except User.DoesNotExist:
                referrer = None
            if referrer and referrer != user:
                user.referred_by = referrer
                user.save(update_fields=['referred_by'])
                try:
                    from notifications.services import notify_referral_joined
                    notify_referral_joined(user)
                except Exception:
                    pass
        user.refresh_from_db()
        return user


def _clean_profile_data(data):
    allowed = {
        'name',
        'description',
        'website',
        'telegram_handle',
        'linkedin_handle',
        'selected_role',
    }
    return {
        key: str(value).strip()
        for key, value in (data or {}).items()
        if key in allowed and value is not None
    }
