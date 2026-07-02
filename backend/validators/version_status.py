"""
Version-shame verdict for a validator wallet against the active target node version.

Extracted from ValidatorWalletViewSet._version_context so the same logic is shared by
the Wall of Shame view and the Grafana sync. The grace period is the global
settings.NODE_VERSION_SHAME_GRACE_DAYS (default 3).

Versions are compared with `packaging` (PEP 440). When either side is unparseable
(legacy operator values or vendor formats like '0.6.0-genlayer.1'), the verdict is
'on' only on exact string equality with the target, otherwise 'unknown' — never a
lexicographic string comparison, which misorders versions ('0.10.0' < '0.9.0').
"""
from datetime import timedelta

from django.conf import settings
from packaging.version import InvalidVersion, parse as parse_version

_UNSET = object()


def default_grace_days():
    return getattr(settings, 'NODE_VERSION_SHAME_GRACE_DAYS', 3)


def safe_parse_version(v):
    """
    packaging Version, or None when the string is not PEP 440-parseable.

    Semver strings like '0.6.0-genlayer.1' are valid semver but invalid PEP 440;
    they must read as "can't compare", never abort a sync.
    """
    if not v:
        return None
    try:
        return parse_version(v)
    except InvalidVersion:
        return None


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

    if node_version:
        node_parsed = safe_parse_version(node_version)
        target_parsed = safe_parse_version(target.version)
        if node_parsed is not None and target_parsed is not None:
            if node_parsed >= target_parsed:
                context['status'] = 'on'
                return context
            # Parseable and behind → fall through to warning/shame.
        elif node_version.strip() == (target.version or '').strip():
            # Unparseable but exactly the target string (vendor-format fleets).
            context['status'] = 'on'
            return context
        else:
            # Either side unparseable and not an exact match: we can't honestly
            # rank them, so we neither clear nor shame.
            context['status'] = 'unknown'
            return context

    if context['target_elapsed_days'] <= grace_days:
        context['status'] = 'warning'
        context['grace_days_remaining'] = max(0, grace_days - context['target_elapsed_days'])
        return context

    context['status'] = 'shame'
    context['shame_started_at'] = target_date + timedelta(days=grace_days)
    return context
