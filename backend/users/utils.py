"""
Wallet address privacy helpers.

Portal user account addresses are never exposed in full on public API
surfaces — only the truncated display form. Full addresses remain available
to the owner (/users/me/, auth endpoints) and staff. Validator node wallet
addresses and on-chain operator addresses are NOT covered by this rule:
they are public on-chain data consumed by explorers and Grafana.
"""
import re

FULL_ADDRESS_RE = re.compile(r'^0x[0-9a-fA-F]{40}$')


def is_full_address(value):
    """True if value is a complete 0x-prefixed 40-hex-char address."""
    return bool(value and FULL_ADDRESS_RE.match(str(value).strip()))


def truncate_address(address):
    """
    Public display form of a wallet address: 0x1234...abcd.
    Idempotent — already-truncated values pass through unchanged.
    """
    if not address:
        return address
    address = str(address)
    if len(address) <= 10:
        return address
    return f"{address[:6]}...{address[-4:]}"


def user_lookup_kwargs(key, user_field=None):
    """
    Dual-key public user lookup: a full address resolves by address
    (case-insensitive), a numeric key by primary key. Malformed keys fall
    through to an address miss and the caller's 404.

    With user_field set (e.g. 'user'), returns filter kwargs across that
    relation instead — for views whose ?user_address= param now also accepts
    a user id.
    """
    key = str(key).strip()
    if key.isdigit():
        if user_field:
            return {f'{user_field}_id': int(key)}
        return {'pk': int(key)}
    if user_field:
        return {f'{user_field}__address__iexact': key}
    return {'address__iexact': key}
