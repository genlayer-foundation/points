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
            or snap.version_status != 'unknown'
        )
    )


def _shame_dims(snap):
    """
    Dimensions that made a day non-clean, for explaining a broken streak.

    The on-chain `status` is trusted whenever a snapshot row exists (the on-chain
    sync owns that column); the observability dimensions are only attributed when
    the Grafana sync actually observed the day — we can't claim a node was shamed
    on a day we have no data for.
    """
    if snap is None:
        return []
    dims = []
    if snap.status != 'active':
        dims.append('status')
    if _has_observation(snap):
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

    A day with no Grafana data while the node was active (partial today, a sync
    outage, or pre-history) is SKIPPED — it neither counts nor breaks, so an infra
    failure on our side can't reset every validator's streak. A day the node spent
    non-active (per the on-chain sync) or was observed shamed breaks the streak.
    """
    wallet_ids = list(wallet_ids)
    today = timezone.localdate(now)

    def dims_on(snaps):
        dims = []
        for s in snaps:
            for d in _shame_dims(s):
                if d not in dims:
                    dims.append(d)
        return dims

    days = 0
    since = None
    broken_by = []
    for offset in range(max_days):
        day = today - timedelta(days=offset)
        snaps = [index.get((wid, day)) for wid in wallet_ids]
        if any(_is_clean(s) for s in snaps):
            days += 1
            since = day
            continue
        non_active = any(s is not None and s.status != 'active' for s in snaps)
        observed = any(_has_observation(s) for s in snaps)
        if non_active or observed:
            broken_by = dims_on(snaps)
            break
        # No data for this day: skip it, don't break.

    return {'days': days, 'broken_by': broken_by, 'since': since}
