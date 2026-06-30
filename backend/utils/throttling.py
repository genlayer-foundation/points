from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class SiweAuthRateThrottle(AnonRateThrottle):
    """
    Per-IP throttle for the unauthenticated SIWE endpoints (nonce + login).
    Bounds signature brute-forcing and nonce-table flooding without affecting
    normal sign-in flows (a login uses two requests).
    """
    scope = 'siwe_auth'


class WalletLinkRateThrottle(UserRateThrottle):
    """
    Per-user throttle for validator wallet linking. Linking is a one-time
    action, so a tight rate bounds mass-claiming of operator addresses.
    """
    scope = 'wallet_link'


class PendingEmailStartRateThrottle(AnonRateThrottle):
    scope = 'pending_email_start'


class PendingEmailResendRateThrottle(AnonRateThrottle):
    scope = 'pending_email_resend'


class PendingEmailConfirmRateThrottle(AnonRateThrottle):
    scope = 'pending_email_confirm'


class ExistingEmailStartRateThrottle(UserRateThrottle):
    scope = 'existing_email_start'


class ExistingEmailResendRateThrottle(UserRateThrottle):
    scope = 'existing_email_resend'


class ExistingEmailConfirmRateThrottle(UserRateThrottle):
    scope = 'existing_email_confirm'
