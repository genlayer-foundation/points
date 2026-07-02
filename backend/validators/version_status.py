"""
Version-shame verdict for a validator wallet against the active target node version.

Extracted from ValidatorWalletViewSet._version_context so the same logic is shared by
the Wall of Shame view and the Grafana sync. The grace period is the global
settings.NODE_VERSION_SHAME_GRACE_DAYS (default 3).
"""
from datetime import timedelta

from django.conf import settings

from .node_version import NodeVersionMixin

_UNSET = object()


def default_grace_days():
    return getattr(settings, 'NODE_VERSION_SHAME_GRACE_DAYS', 3)


def compute_version_status(wallet, target, now, node_version=_UNSET):
    """
    Return a context dict describing the wallet's version status vs the target:
      status: 'unknown' | 'on' | 'warning' | 'shame'
      node_version, target_version, target_date, target_elapsed_days,
      grace_days, grace_days_remaining, shame_started_at

    By default the node version is read from the linked operator
    (node_version_<network>). Callers that already know the running version (e.g.
    the Grafana sync, which reads it from Prometheus) can pass `node_version`
    explicitly — including None to mean "unknown" — to bypass the operator lookup.
    """
    if node_version is _UNSET:
        field_name = f'node_version_{wallet.network}'
        node_version = getattr(wallet.operator, field_name, None) if wallet.operator else None
    target_version = target.version if target else None
    target_date = target.target_date if target else None
    grace_days = default_grace_days()

    context = {
        'status': 'unknown' if not target else 'on',
        'node_version': node_version,
        'target_version': target_version,
        'target_date': target_date,
        'target_elapsed_days': None,
        'grace_days': grace_days,
        'grace_days_remaining': None,
        'shame_started_at': None,
    }
    if not target or not target_date or target_date > now:
        return context

    context['target_elapsed_days'] = max(0, (now - target_date).days)
    matches_target = bool(
        node_version
        and NodeVersionMixin._compare_versions(node_version, target.version)
    )
    if matches_target:
        context['status'] = 'on'
        return context

    if context['target_elapsed_days'] <= grace_days:
        context['status'] = 'warning'
        context['grace_days_remaining'] = max(0, grace_days - context['target_elapsed_days'])
        return context

    context['status'] = 'shame'
    context['shame_started_at'] = target_date + timedelta(days=grace_days)
    return context
