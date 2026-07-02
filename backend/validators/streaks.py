"""
Consecutive "not shamed" uptime streaks, derived from the daily
ValidatorWalletStatusSnapshot rollup.

A day counts as CLEAN for a wallet when the node was on-chain active, reported
both metrics and logs at least once, and was not shamed on any dimension:

    status == 'active'
    AND metrics_samples >= 1 AND logs_samples >= 1
    AND metrics_status != 'shame'
    AND logs_status  != 'shame'
    AND version_status != 'shame'

Operator roll-up is "any-node-clean": an operator is not shamed on a network for
a day if AT LEAST ONE of their wallets on that network was clean that day.

History only starts at deploy (past days were never recorded), so a streak's
`since` marks the first counted clean day, not necessarily the true start.
"""
from datetime import timedelta

from django.utils import timezone

from .models import ValidatorWalletStatusSnapshot

DEFAULT_MAX_DAYS = 180

# Fields the streak logic needs; keeps the prefetch lean.
_SNAP_FIELDS = (
    'wallet_id', 'date', 'status',
    'metrics_status', 'logs_status', 'version_status',
    'metrics_samples', 'logs_samples',
)


def _is_clean(snap):
    return bool(
        snap is not None
        and snap.status == 'active'
        and snap.metrics_samples >= 1
        and snap.logs_samples >= 1
        and snap.metrics_status != 'shame'
        and snap.logs_status != 'shame'
        and snap.version_status != 'shame'
    )


def _has_observation(snap):
    """Whether the Grafana sync recorded anything for this day (vs not-yet-synced)."""
    return bool(
        snap is not None
        and (
            snap.metrics_samples > 0
            or snap.logs_samples > 0
            or snap.metrics_status != 'unknown'
            or snap.logs_status != 'unknown'
        )
    )


def _shame_dims(snap):
    """
    Dimensions that made a day non-clean, for explaining a broken streak.

    Only attributes a reason when the day was actually observed. A missing day or
    the edge of recorded history returns [] — we can't claim the node was shamed,
    we simply have no data there.
    """
    if not _has_observation(snap):
        return []
    dims = []
    if snap.status != 'active':
        dims.append('status')
    if snap.metrics_status == 'shame' or snap.metrics_samples < 1:
        dims.append('metrics')
    if snap.logs_status == 'shame' or snap.logs_samples < 1:
        dims.append('logs')
    if snap.version_status == 'shame':
        dims.append('version')
    return dims


def load_snapshot_index(wallet_ids, now, max_days=DEFAULT_MAX_DAYS):
    """One query → {(wallet_id, date): snapshot} for all given wallets in the window."""
    if not wallet_ids:
        return {}
    cutoff = timezone.localdate(now) - timedelta(days=max_days)
    rows = (
        ValidatorWalletStatusSnapshot.objects
        .filter(wallet_id__in=wallet_ids, date__gte=cutoff)
        .only(*_SNAP_FIELDS)
    )
    return {(row.wallet_id, row.date): row for row in rows}


def clean_streak(wallet_ids, now, index, max_days=DEFAULT_MAX_DAYS):
    """
    Consecutive clean days ending today, over `wallet_ids` with any-node-clean
    semantics (one wallet id = per-node; several = per-operator-per-network).

    Returns {'days': int, 'broken_by': [dims], 'since': date | None}.
    A partial (not-yet-synced) today never breaks the streak; an already-shamed
    today breaks it at 0.
    """
    wallet_ids = list(wallet_ids)
    today = timezone.localdate(now)

    def snaps_on(day):
        return [index.get((wid, day)) for wid in wallet_ids]

    def clean_on(day):
        return any(_is_clean(s) for s in snaps_on(day))

    def observed_on(day):
        return any(_has_observation(s) for s in snaps_on(day))

    def dims_on(day):
        dims = []
        for s in snaps_on(day):
            for d in _shame_dims(s):
                if d not in dims:
                    dims.append(d)
        return dims

    # Skip an unsynced today so a partial day doesn't reset the streak.
    start = 0
    if not clean_on(today) and not observed_on(today):
        start = 1

    days = 0
    since = None
    broken_by = []
    for offset in range(start, max_days + 1):
        day = today - timedelta(days=offset)
        if clean_on(day):
            days += 1
            since = day
        else:
            broken_by = dims_on(day)
            break

    return {'days': days, 'broken_by': broken_by, 'since': since}
