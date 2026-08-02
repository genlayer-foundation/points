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


class TelegramBindCodeIssueRateThrottle(UserRateThrottle):
    """
    Per-user throttle for issuing Telegram group bind codes. Codes are cheap
    to mint but each is a live secret for 48h; a tight rate bounds hoarding
    and keeps the active-code surface small.
    """
    scope = 'telegram_bind_issue'


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


class CommunityPostVerificationRateThrottle(UserRateThrottle):
    scope = 'community_post_verify'


class CampaignRedirectRateThrottle(AnonRateThrottle):
    """
    Per-IP throttle for the public campaign vanity-link resolver. Generous
    enough for NAT'd event traffic; bounds pathological resolver floods.
    """
    scope = 'campaign_redirect'
