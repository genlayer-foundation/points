import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from social_connections.models import DiscordConnection

from .models import PoapClaim, PoapDistribution, PoapDrop, PoapMintLink


class PoapClaimError(Exception):
    status_code = 400


class AlreadyClaimedError(PoapClaimError):
    status_code = 409


class InvalidClaimError(PoapClaimError):
    status_code = 400


class ClaimClosedError(PoapClaimError):
    status_code = 400
    CLAIM_NOT_OPEN = 'This POAP is not open for claiming yet.'
    CLAIM_WINDOW_ENDED = 'This POAP claim window has ended.'


class MissingDiscordConnectionError(PoapClaimError):
    status_code = 403


def normalize_secret(value):
    return ' '.join((value or '').strip().lower().split())


def hash_secret(value):
    normalized = normalize_secret(value)
    return salted_hmac('poap.secret', normalized, secret=settings.SECRET_KEY).hexdigest()


def hash_token(value):
    return salted_hmac('poap.mint-link', value or '', secret=settings.SECRET_KEY).hexdigest()


def secure_compare(left, right):
    return constant_time_compare(left or '', right or '')


def _fernet():
    digest = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_token(token):
    return _fernet().encrypt(token.encode('utf-8')).decode('utf-8')


def decrypt_token(ciphertext):
    if not ciphertext:
        return ''
    try:
        return _fernet().decrypt(ciphertext.encode('utf-8')).decode('utf-8')
    except InvalidToken:
        return ''


def validate_drop_capacity(drop):
    if drop.status != PoapDrop.STATUS_ACTIVE:
        raise ClaimClosedError('This POAP is not open for claiming.')
    now = timezone.now()
    if drop.event_start_at and now < drop.event_start_at:
        raise ClaimClosedError(ClaimClosedError.CLAIM_NOT_OPEN)
    if drop.event_end_at and now > drop.event_end_at:
        raise ClaimClosedError(ClaimClosedError.CLAIM_WINDOW_ENDED)
    if drop.max_claims is not None:
        claimed = PoapClaim.objects.filter(drop=drop, user__isnull=False).count()
        if claimed >= drop.max_claims:
            raise ClaimClosedError('This POAP has reached its claim limit.')


def validate_distribution(distribution):
    if not distribution.is_open():
        raise ClaimClosedError('This distribution is not currently open.')


def validate_discord_connection(user):
    if not DiscordConnection.objects.filter(user_id=user.pk).exists():
        raise MissingDiscordConnectionError(
            'You must link your Discord account to claim this POAP.'
        )


def _create_claim(*, drop, user, distribution, mint_link=None, method=None):
    if PoapClaim.objects.filter(drop=drop, user=user).exists():
        raise AlreadyClaimedError('You already claimed this POAP.')

    try:
        claim = PoapClaim.objects.create(
            drop=drop,
            user=user,
            distribution=distribution,
            mint_link=mint_link,
            claim_method=method or distribution.method,
            source=PoapClaim.SOURCE_PORTAL,
        )
    except IntegrityError as exc:
        raise AlreadyClaimedError('You already claimed this POAP.') from exc

    PoapDistribution.objects.filter(pk=distribution.pk).update(
        claimed_count=F('claimed_count') + 1
    )
    if mint_link:
        PoapMintLink.objects.filter(pk=mint_link.pk).update(
            used_count=F('used_count') + 1
        )
    return claim


def claim_with_secret(*, drop_slug, user, secret):
    if not user or not user.is_authenticated:
        raise InvalidClaimError('Authentication is required.')
    validate_discord_connection(user)

    candidate_hash = hash_secret(secret)
    with transaction.atomic():
        drop = PoapDrop.objects.select_for_update().get(slug=drop_slug)
        validate_drop_capacity(drop)

        distributions = (
            PoapDistribution.objects
            .select_for_update()
            .filter(
                drop=drop,
                method=PoapDistribution.METHOD_SECRET,
                active=True,
            )
            .order_by('-created_at')
        )
        distribution = None
        matched_closed_distribution = False
        for item in distributions:
            if secure_compare(item.secret_hash, candidate_hash):
                if item.is_open():
                    distribution = item
                    break
                matched_closed_distribution = True

        if distribution is None:
            if matched_closed_distribution:
                raise ClaimClosedError('This distribution is not currently open.')
            raise InvalidClaimError('Invalid secret phrase.')

        return _create_claim(
            drop=drop,
            user=user,
            distribution=distribution,
            method=PoapClaim.CLAIM_SECRET,
        )


def claim_with_mint_link(*, token, user):
    if not user or not user.is_authenticated:
        raise InvalidClaimError('Authentication is required.')
    if not token:
        raise InvalidClaimError('Mint link token is missing.')
    validate_discord_connection(user)

    token_digest = hash_token(token)
    with transaction.atomic():
        try:
            mint_link = (
                PoapMintLink.objects
                .select_for_update()
                .select_related('distribution', 'distribution__drop')
                .get(token_hash=token_digest)
            )
        except PoapMintLink.DoesNotExist as exc:
            raise InvalidClaimError(
                'Mint link token was not found. Check that the full Claim URL was copied from the admin.'
            ) from exc

        distribution = mint_link.distribution
        drop = PoapDrop.objects.select_for_update().get(pk=distribution.drop_id)
        now = timezone.now()

        if distribution.method != PoapDistribution.METHOD_MINT_LINK:
            raise InvalidClaimError('This mint link is not attached to a mint-link distribution.')

        if drop.status == PoapDrop.STATUS_DRAFT:
            raise ClaimClosedError('This POAP is still in draft and cannot be claimed yet.')
        if drop.status == PoapDrop.STATUS_ARCHIVED:
            raise ClaimClosedError('This POAP is archived and is no longer claimable.')

        validate_drop_capacity(drop)

        if not distribution.active:
            raise ClaimClosedError('This mint-link distribution is inactive.')
        if distribution.starts_at and now < distribution.starts_at:
            raise ClaimClosedError('This mint-link distribution is not open yet.')
        if distribution.ends_at and now > distribution.ends_at:
            raise ClaimClosedError('This mint-link distribution has ended.')
        if distribution.max_claims is not None and distribution.claimed_count >= distribution.max_claims:
            raise ClaimClosedError('This mint-link distribution has reached its claim limit.')

        if mint_link.expires_at and now > mint_link.expires_at:
            raise ClaimClosedError('This mint link has expired.')
        if mint_link.used_count >= mint_link.max_uses:
            raise ClaimClosedError('This mint link has already been used.')

        return _create_claim(
            drop=drop,
            user=user,
            distribution=distribution,
            mint_link=mint_link,
            method=PoapClaim.CLAIM_MINT_LINK,
        )


def generate_mint_links(*, distribution, count, max_uses=1, expires_at=None):
    created = []
    for _ in range(count):
        token = PoapMintLink.generate_token()
        link = PoapMintLink.objects.create(
            distribution=distribution,
            token_hash=hash_token(token),
            token_ciphertext=encrypt_token(token),
            max_uses=max_uses,
            expires_at=expires_at,
        )
        created.append((link, token))
    return created


def normalize_wallet_address(value):
    return (value or '').strip().lower()


def recover_unmatched_claims_for_wallet(user, wallet_address):
    result = {
        'attached_claims': [],
        'skipped_existing_drop_count': 0,
    }
    if not user or not user.pk or not wallet_address:
        return result

    normalized_wallet = normalize_wallet_address(wallet_address)
    if not normalized_wallet:
        return result

    with transaction.atomic():
        claims = list(
            PoapClaim.objects
            .select_for_update()
            .filter(
                user__isnull=True,
                legacy_wallet_address__iexact=normalized_wallet,
            )
            .select_related('drop')
            .order_by('claimed_at', 'pk')
        )
        if not claims:
            return result

        drop_ids = [claim.drop_id for claim in claims]
        existing_drop_ids = set(
            PoapClaim.objects
            .filter(user=user, drop_id__in=drop_ids)
            .values_list('drop_id', flat=True)
        )

        for claim in claims:
            if claim.drop_id in existing_drop_ids:
                result['skipped_existing_drop_count'] += 1
                continue
            claim.user = user
            claim.save(update_fields=['user', 'updated_at'])
            result['attached_claims'].append(claim)
            existing_drop_ids.add(claim.drop_id)

    return result


def attach_unmatched_claims_for_wallet(user, wallet_address):
    return recover_unmatched_claims_for_wallet(user, wallet_address)['attached_claims']


def attach_unmatched_claims_for_user(user):
    if not user or not user.pk or not user.address:
        return 0

    return len(attach_unmatched_claims_for_wallet(user, user.address))


def find_user_for_legacy_claim(wallet='', email=''):
    User = get_user_model()
    if wallet:
        user = User.objects.filter(address__iexact=wallet).first()
        if user:
            return user
    return None
