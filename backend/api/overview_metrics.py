from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal, InvalidOperation
import json
import logging

import requests
from django.conf import settings
from django.utils import timezone

from .models import MetricSnapshot

logger = logging.getLogger(__name__)

HTTP_TIMEOUT_SECONDS = 12
GEN_DECIMALS = 18
TESTNET_NETWORKS = ('asimov', 'bradbury')
EXPLORER_BASE_URLS = {
    'asimov': 'https://explorer-asimov.genlayer.com',
    'bradbury': 'https://explorer-bradbury.genlayer.com',
}
NETWORK_ACTIVITY_WEEKS = 12
NETWORK_ACTIVITY_MONTHS = 6
NETWORK_ACTIVITY_INTERVAL = 'week'
NETWORK_ACTIVITY_PAYLOAD_VERSION = 5
NETWORK_ACTIVITY_SECONDS_PER_WEEK = 7 * 24 * 60 * 60
STUDIO_NETWORK_ACTIVITY_RANGE = 'year'
OVERVIEW_PAYLOAD_METRIC_KEY = 'overview_payload'
OVERVIEW_PAYLOAD_VERSION = 1


def decimal_value(value):
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def format_usd(value):
    if value is None:
        return ''
    try:
        n = float(value)
    except (TypeError, ValueError):
        return ''
    if n >= 1_000_000_000:
        return f'${n / 1_000_000_000:.1f}B'
    if n >= 1_000_000:
        return f'${n / 1_000_000:.1f}M'
    if n >= 1_000:
        return f'${n / 1_000:.1f}K'
    return f'${n:,.0f}'


def snapshot(metric_key, source, value, unit='count', label='', dimensions=None, raw_payload=None, status='ok', error=''):
    return MetricSnapshot.objects.create(
        metric_key=metric_key,
        source=source,
        label=label,
        value=decimal_value(value),
        unit=unit,
        dimensions=dimensions or {},
        raw_payload=raw_payload or {},
        status=status,
        error=error or '',
    )


def snapshot_error(metric_key, source, error, label='', dimensions=None):
    logger.warning('Overview metric %s from %s failed: %s', metric_key, source, error)
    return snapshot(
        metric_key,
        source,
        None,
        label=label,
        dimensions=dimensions,
        status=MetricSnapshot.STATUS_ERROR,
        error=str(error),
    )


def latest_snapshot(metric_key):
    return MetricSnapshot.objects.filter(metric_key=metric_key, status=MetricSnapshot.STATUS_OK).order_by(
        '-observed_at',
        '-created_at',
    ).first()


def serialize_snapshot(item):
    if item is None:
        return None
    return {
        'metric_key': item.metric_key,
        'source': item.source,
        'label': item.label,
        'value': float(item.value) if item.value is not None else None,
        'unit': item.unit,
        'observed_at': item.observed_at.isoformat(),
        'dimensions': item.dimensions,
        'status': item.status,
        'error': item.error,
    }


def overview_count_metric(metric_key, label, value, observed_at=None):
    return {
        'metric_key': metric_key,
        'source': 'portal',
        'label': label,
        'value': value,
        'unit': 'count',
        'observed_at': (observed_at or timezone.now()).isoformat(),
        'dimensions': {},
        'status': MetricSnapshot.STATUS_OK,
        'error': '',
    }


def fetch_testnet_kpis(network):
    base_url = {
        'asimov': 'https://explorer-asimov.genlayer.com',
        'bradbury': 'https://explorer-bradbury.genlayer.com',
    }.get(network)
    if not base_url:
        raise ValueError(f'Unknown network {network}')

    general = requests.get(f'{base_url}/api/v1/analytics/general-kpis', timeout=HTTP_TIMEOUT_SECONDS)
    general.raise_for_status()
    data = general.json() or {}
    return {
        'decisions_made': int(data.get('total_finalized_transactions') or 0),
        'chain_transactions': int(data.get('total_rollup_transactions') or 0),
        'contracts_all_time': int(data.get('total_contracts') or 0),
        'network_validators': int(data.get('total_validators') or 0),
        'gen_staked': int(decimal_value(data.get('total_gen_staked')) or 0) // (10 ** GEN_DECIMALS),
        'raw': data,
    }


def collect_testnet_metrics():
    totals = {
        'decisions_made': 0,
        'chain_transactions': 0,
        'contracts_all_time': 0,
        'network_validators': 0,
        'gen_staked': 0,
    }
    collected = []

    for network in TESTNET_NETWORKS:
        try:
            metrics = fetch_testnet_kpis(network)
        except Exception as exc:
            collected.append(snapshot_error('network_status', 'genlayer_explorer', exc, dimensions={'network': network}))
            continue

        for key in totals:
            totals[key] += metrics[key]
            collected.append(snapshot(
                key,
                'genlayer_explorer',
                metrics[key],
                label=key.replace('_', ' ').title(),
                dimensions={'network': network},
                raw_payload=metrics['raw'],
            ))

    for key, value in totals.items():
        collected.append(snapshot(
            key,
            'genlayer_explorer',
            value,
            label=key.replace('_', ' ').title(),
            dimensions={'network': 'all'},
        ))

    return collected


def get_portal_counts():
    from contributions.models import Contribution
    from validators.models import Validator
    from community_xp.utils import get_community_member_user_ids
    from leaderboard.views import ONBOARDING_CONTRIBUTION_TYPE_SLUGS

    builder_count = (
        Contribution.objects
        .filter(user__visible=True, contribution_type__category__slug='builder')
        .exclude(contribution_type__slug__in=ONBOARDING_CONTRIBUTION_TYPE_SLUGS)
        .values('user_id')
        .distinct()
        .count()
    )

    # Mirrors the global contribution_count in leaderboard stats, but public.
    contributions_count = (
        Contribution.objects
        .filter(user__visible=True)
        .exclude(contribution_type__slug__in=ONBOARDING_CONTRIBUTION_TYPE_SLUGS)
        .count()
    )

    return {
        'builders': builder_count,
        'validators': Validator.objects.filter(user__visible=True).count(),
        'community_members': len(get_community_member_user_ids(visible_only=True)),
        'contributions': contributions_count,
    }


def collect_portal_metrics():
    counts = get_portal_counts()
    return [
        snapshot(key, 'portal', value, label=key.replace('_', ' ').title())
        for key, value in counts.items()
    ]


def collect_discord_members():
    token = getattr(settings, 'DISCORD_BOT_TOKEN', '')
    guild_id = getattr(settings, 'DISCORD_GUILD_ID', '')
    if not token or not guild_id:
        return snapshot_error('discord_members', 'discord', 'DISCORD_BOT_TOKEN or DISCORD_GUILD_ID is not configured')

    response = requests.get(
        f'https://discord.com/api/v10/guilds/{guild_id}',
        params={'with_counts': 'true'},
        headers={'Authorization': f'Bot {token}'},
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json() or {}
    return snapshot(
        'discord_members',
        'discord',
        payload.get('approximate_member_count'),
        label='Discord members',
        raw_payload=payload,
    )


def collect_telegram_members():
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', '')
    if token and chat_id:
        response = requests.get(
            f'https://api.telegram.org/bot{token}/getChatMemberCount',
            params={'chat_id': chat_id},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json() or {}
        return snapshot(
            'telegram_members',
            'telegram',
            payload.get('result'),
            label='Telegram members',
            raw_payload=payload,
            dimensions={'chat_id': chat_id},
        )
    if not token:
        return snapshot(
            'telegram_members',
            'telegram',
            getattr(settings, 'TELEGRAM_MEMBERS', '') or 13300,
            label='Telegram members',
            dimensions={'fallback': 'bot_token_missing'},
        )

    manual = getattr(settings, 'TELEGRAM_MEMBERS', '')
    if manual:
        return snapshot('telegram_members', 'telegram', manual, label='Telegram members')
    return snapshot_error(
        'telegram_members',
        'telegram',
        'TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID or TELEGRAM_MEMBERS is not configured',
    )


def collect_x_followers():
    token = getattr(settings, 'SORSA_API_KEY', '')
    base_url = getattr(settings, 'SORSA_API_BASE_URL', '').rstrip('/')
    username = getattr(settings, 'X_METRICS_USERNAME', 'GenLayer')
    if not token or not base_url:
        return snapshot_error('x_followers', 'sorsa', 'SORSA_API_BASE_URL or SORSA_API_KEY is not configured')

    response = requests.get(
        f'{base_url}/info-batch',
        params={'usernames': [username.lstrip('@')]},
        headers={'ApiKey': token, 'Accept': 'application/json'},
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json() or {}
    users = payload.get('users') or []
    profile = users[0] if users else {}
    followers_count = profile.get('followers_count')
    if followers_count is None:
        return snapshot_error('x_followers', 'sorsa', 'Sorsa profile response did not include followers_count')
    return snapshot(
        'x_followers',
        'sorsa',
        followers_count,
        label='X followers',
        raw_payload=payload,
        dimensions={'username': username},
    )


def collect_github_boilerplate_stars():
    repo = getattr(settings, 'GITHUB_METRICS_REPO', 'genlayerlabs/genlayer-project-boilerplate')
    headers = {
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'genlayer-portal-metrics',
    }
    token = getattr(settings, 'GITHUB_METRICS_TOKEN', '')
    if token:
        headers['Authorization'] = f'Bearer {token}'

    response = requests.get(f'https://api.github.com/repos/{repo}', headers=headers, timeout=HTTP_TIMEOUT_SECONDS)
    response.raise_for_status()
    payload = response.json() or {}
    return snapshot(
        'github_boilerplate_stars',
        'github',
        payload.get('stargazers_count'),
        label='GitHub stars',
        raw_payload=payload,
        dimensions={'repo': repo},
    )


def collect_defillama_fees_rank():
    configured_rank = getattr(settings, 'DEFILLAMA_FEES_RANK', '')
    if configured_rank:
        return snapshot(
            'defillama_fees_rank',
            'defillama',
            configured_rank,
            unit='rank',
            label='DeFiLlama fees rank',
            dimensions={'url': getattr(settings, 'DEFILLAMA_FEES_RANK_URL', 'https://defillama.com/fees/chains')},
        )
    return snapshot_error(
        'defillama_fees_rank',
        'defillama',
        'DEFILLAMA_FEES_RANK is not configured; documented API did not expose a stable GenLayer chain-rank payload',
    )


def collect_external_metrics():
    collectors = [
        collect_discord_members,
        collect_telegram_members,
        collect_x_followers,
        collect_github_boilerplate_stars,
        collect_defillama_fees_rank,
    ]
    results = []
    for collector in collectors:
        try:
            results.append(collector())
        except Exception as exc:
            metric_key = collector.__name__.replace('collect_', '')
            source = 'sorsa' if metric_key == 'x_followers' else metric_key.split('_')[0]
            results.append(snapshot_error(metric_key, source, exc))
    return results


# ---------------------------------------------------------------------------
# Network activity (overview chart): weekly decisions across Studio + testnets.
# Fetched here so the 15-minute cron persists it and the read endpoint can serve
# straight from the DB instead of doing a live multi-API fetch per request.
# ---------------------------------------------------------------------------

def _week_bounds_for_ts(ts, anchor_date):
    d = datetime.fromtimestamp(int(ts), tz=dt_timezone.utc).date()
    days_until_anchor = (anchor_date.weekday() - d.weekday()) % 7
    week_end = d + timedelta(days=days_until_anchor)
    return week_end - timedelta(days=7), week_end


def _week_key(week_start):
    return week_start.isoformat()


def _week_label(week_start, week_end):
    if week_start.month == week_end.month:
        return f'{week_start:%b} {week_start.day}-{week_end.day}'
    return f'{week_start:%b} {week_start.day} - {week_end:%b} {week_end.day}'


def _utc_midnight_ts(d):
    return int(datetime(d.year, d.month, d.day, tzinfo=dt_timezone.utc).timestamp())


def _shift_months(d, months):
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    return d.replace(year=year, month=month)


def _activity_window(anchor_date):
    current_month_start = anchor_date.replace(day=1)
    start_date = _shift_months(current_month_start, -(NETWORK_ACTIVITY_MONTHS - 1))
    next_month_start = _shift_months(current_month_start, 1)
    end_date = next_month_start - timedelta(days=1)
    return start_date, end_date


def _weekly_points(points, limit=NETWORK_ACTIVITY_WEEKS, anchor_date=None):
    anchor_date = anchor_date or timezone.now().date()
    buckets = {}
    for ts, value in points:
        week_start, week_end = _week_bounds_for_ts(ts, anchor_date)
        bucket = buckets.setdefault(week_start, {'week_end': week_end, 'value': 0})
        bucket['value'] += int(value or 0)
    return [
        {
            'week_start': _week_key(week_start),
            'week_end': _week_key(bucket['week_end']),
            'label': _week_label(week_start, bucket['week_end']),
            'value': bucket['value'],
        }
        for week_start, bucket in sorted(buckets.items())[-limit:]
    ]


def _daily_points_from_values(values, now):
    end_date = datetime.fromtimestamp(int(now), tz=dt_timezone.utc).date()
    start_date = end_date - timedelta(days=max(len(values) - 1, 0))
    return [
        (_utc_midnight_ts(start_date + timedelta(days=i)), round(float(value or 0)))
        for i, value in enumerate(values)
    ]


def _fetch_explorer_history(base, metric, frm, now):
    history = requests.get(
        f'{base}/api/v1/analytics/kpi-histories',
        params={
            'metric': metric,
            'interval': 'D1',
            'from_timestamp': frm,
            'to_timestamp': now,
        },
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    history.raise_for_status()
    buckets = (history.json() or {}).get('histories') or []
    points = []
    for bucket in buckets:
        if not isinstance(bucket, dict):
            continue
        try:
            points.append((int(bucket['timestamp']), round(float(bucket.get('value') or 0))))
        except (TypeError, ValueError, KeyError):
            continue
    return points


def fetch_explorer_activity(network, frm, now, anchor_date):
    base = EXPLORER_BASE_URLS[network]
    decision_points = _fetch_explorer_history(base, 'total_finalized_transactions', frm, now)
    decisions_weekly = _weekly_points(
        decision_points,
        anchor_date=anchor_date,
    )
    try:
        chain_points = _fetch_explorer_history(base, 'total_rollup_transactions', frm, now)
    except Exception as exc:
        logger.warning('Network activity: %s chain history failed: %s', network, exc)
        chain_points = []
    chain_weekly = _weekly_points(chain_points, anchor_date=anchor_date) if chain_points else []
    return {
        'points': decisions_weekly,
        'chain_points': chain_weekly,
        'daily_points': decision_points,
        'chain_daily_points': chain_points,
        'labels': [point['label'] for point in decisions_weekly],
        'values': [point['value'] for point in decisions_weekly],
    }


def fetch_studio_activity(now, anchor_date):
    url = getattr(
        settings,
        'STUDIO_METRICS_URL',
        'https://studio-metrics-dashboard.vercel.app/api/metrics/executive',
    )
    response = requests.get(
        url,
        params={'instanceId': 'all', 'range': STUDIO_NETWORK_ACTIVITY_RANGE},
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    metrics = {m.get('id'): m for m in (response.json() or {}).get('metrics', []) if isinstance(m, dict)}
    decisions = metrics.get('total-decisions', {})
    chain = metrics.get('chain-transactions', {})
    decision_values = [round(float(v or 0)) for v in (decisions.get('sparkline') or [])]
    chain_values = [round(float(v or 0)) for v in (chain.get('sparkline') or [])]
    decision_points = _daily_points_from_values(decision_values, now)
    chain_points = _daily_points_from_values(chain_values, now)
    weekly = _weekly_points(decision_points, anchor_date=anchor_date)
    chain_weekly = _weekly_points(chain_points, anchor_date=anchor_date)
    return {
        'points': weekly,
        'chain_points': chain_weekly,
        'daily_points': decision_points,
        'chain_daily_points': chain_points,
        'labels': [point['label'] for point in weekly],
        'values': [point['value'] for point in weekly],
    }


def _values_by_week(points):
    return {point['week_start']: int(point.get('value') or 0) for point in points}


def _values_by_day(points):
    values = {}
    for ts, value in points:
        day = datetime.fromtimestamp(int(ts), tz=dt_timezone.utc).date().isoformat()
        values[day] = values.get(day, 0) + int(value or 0)
    return values


def _latest_week_meta(source_activity, week_key):
    for item in source_activity:
        for point in item['points']:
            if point['week_start'] == week_key:
                return {
                    'week_start': point['week_start'],
                    'week_end': point.get('week_end'),
                    'label': point['label'],
                }
    return None


def build_network_activity():
    """Assemble the overview-chart payload and latest rolling-week KPIs.

    Each source degrades independently; a failed upstream is just omitted.
    """
    now = int(timezone.now().timestamp())
    anchor_date = datetime.fromtimestamp(now, tz=dt_timezone.utc).date()
    activity_start, activity_end = _activity_window(anchor_date)
    frm = _utc_midnight_ts(activity_start)

    source_activity = []

    # Studio first so it leads the legend/stack.
    try:
        studio = fetch_studio_activity(now, anchor_date)
        if studio['points']:
            source_activity.append({
                'key': 'studio',
                'label': 'Studio',
                'points': studio['points'],
                'chain_points': studio['chain_points'],
                'daily_points': studio['daily_points'],
                'chain_daily_points': studio['chain_daily_points'],
            })
    except Exception as exc:
        logger.warning('Network activity: studio source failed: %s', exc)

    for network in TESTNET_NETWORKS:
        try:
            net = fetch_explorer_activity(network, frm, now, anchor_date)
        except Exception as exc:
            logger.warning('Network activity: %s source failed: %s', network, exc)
            continue
        if net['points']:
            source_activity.append({
                'key': network,
                'label': network.title(),
                'points': net['points'],
                'chain_points': net['chain_points'],
                'daily_points': net['daily_points'],
                'chain_daily_points': net['chain_daily_points'],
            })

    week_keys = sorted({
        point['week_start']
        for item in source_activity
        for point in item['points']
    })[-NETWORK_ACTIVITY_WEEKS:]
    label_by_week = {
        point['week_start']: point['label']
        for item in source_activity
        for point in item['points']
    }
    labels = [label_by_week[key] for key in week_keys]
    series = []
    latest_week_key = week_keys[-1] if week_keys else None
    latest_week = _latest_week_meta(source_activity, latest_week_key) if latest_week_key else None
    latest_week_by_source = {}
    daily_values_by_source = {}
    daily_chain_values_by_source = {}

    for item in source_activity:
        decision_values_by_week = _values_by_week(item['points'])
        chain_values_by_week = _values_by_week(item['chain_points'])
        daily_values_by_source[item['key']] = _values_by_day(item.get('daily_points') or [])
        daily_chain_values_by_source[item['key']] = _values_by_day(item.get('chain_daily_points') or [])
        values = [decision_values_by_week.get(key) for key in week_keys]
        if any(value is not None for value in values):
            series.append({'key': item['key'], 'label': item['label'], 'values': values})
        if latest_week_key:
            latest_week_by_source[item['key']] = {
                'decisions_made': decision_values_by_week.get(latest_week_key, 0),
                'chain_transactions': chain_values_by_week.get(latest_week_key, 0),
            }

    decisions_week_total = sum(item['decisions_made'] for item in latest_week_by_source.values())
    chain_week_total = sum(item['chain_transactions'] for item in latest_week_by_source.values())
    daily_decisions = round(decisions_week_total / 7) if latest_week_key else None
    daily_chain = round(chain_week_total / 7) if latest_week_key else None
    transactions_per_second = (
        chain_week_total / NETWORK_ACTIVITY_SECONDS_PER_WEEK
        if latest_week_key
        else None
    )
    day_keys = []
    if source_activity:
        day_keys = [
            (activity_start + timedelta(days=offset)).isoformat()
            for offset in range((activity_end - activity_start).days + 1)
        ]
    activity = []
    for day_key in day_keys:
        sources = {}
        decisions_day_total = 0
        chain_day_total = 0
        for item in source_activity:
            decisions = daily_values_by_source.get(item['key'], {}).get(day_key, 0)
            chain = daily_chain_values_by_source.get(item['key'], {}).get(day_key, 0)
            decisions_day_total += decisions
            chain_day_total += chain
            sources[item['key']] = {
                'label': item['label'],
                'decisions_made': decisions,
                'chain_transactions': chain,
            }
        activity.append({
            'date': day_key,
            'decisions_made': decisions_day_total,
            'chain_transactions': chain_day_total,
            'sources': sources,
        })

    return {
        'version': NETWORK_ACTIVITY_PAYLOAD_VERSION,
        'labels': labels,
        'series': series,
        'activity': activity,
        'activity_window': {
            'start': activity_start.isoformat(),
            'end': activity_end.isoformat(),
        },
        'interval': NETWORK_ACTIVITY_INTERVAL,
        'latest_week': latest_week,
        'totals': {
            'decisions_made': decisions_week_total if latest_week_key else None,
            'chain_transactions': chain_week_total if latest_week_key else None,
            'daily_decisions_made': daily_decisions,
            'daily_chain_transactions': daily_chain,
            'transactions_per_second': transactions_per_second,
        },
        'latest_week_by_source': latest_week_by_source,
    }


def collect_network_activity():
    try:
        payload = build_network_activity()
    except Exception as exc:
        return snapshot_error('network_activity', 'composite', exc)
    # Don't overwrite a good snapshot with an empty one if every source failed.
    if not payload.get('series'):
        return snapshot_error('network_activity', 'composite', 'no network-activity sources resolved')
    return snapshot(
        'network_activity',
        'composite',
        payload['totals'].get('decisions_made'),
        unit='count',
        label='Network activity',
        raw_payload=payload,
    )


def _latest_network_activity_payload():
    snap = latest_snapshot('network_activity')
    if snap is None or not isinstance(snap.raw_payload, dict) or not snap.raw_payload.get('series'):
        return None
    return snap, dict(snap.raw_payload)


def latest_network_activity():
    latest = _latest_network_activity_payload()
    if latest is None:
        return None
    snap, payload = latest
    # The public overview must not keep serving older snapshots whose totals used
    # different semantics. Versions 3 and 4 already have the same weekly graph
    # semantics; they just lack the v5 six-month heatmap window, so keep serving
    # the graph while the cron catches up and normalize the missing fields below.
    if (
        payload.get('interval') != NETWORK_ACTIVITY_INTERVAL
        or payload.get('version') not in (3, 4, NETWORK_ACTIVITY_PAYLOAD_VERSION)
    ):
        return None
    payload['version'] = NETWORK_ACTIVITY_PAYLOAD_VERSION
    payload.setdefault('activity', [])
    payload.setdefault('activity_window', None)
    # ISO string so the response is identical whether served fresh or from cache,
    # regardless of the cache backend's (de)serialization.
    payload['generated_at'] = snap.observed_at.isoformat()
    return payload


def empty_network_activity_payload():
    return {
        'version': NETWORK_ACTIVITY_PAYLOAD_VERSION,
        'labels': [],
        'series': [],
        'activity': [],
        'activity_window': None,
        'interval': NETWORK_ACTIVITY_INTERVAL,
        'latest_week': None,
        'totals': {
            'decisions_made': None,
            'chain_transactions': None,
            'daily_decisions_made': None,
            'daily_chain_transactions': None,
            'transactions_per_second': None,
        },
        'latest_week_by_source': {},
        'generated_at': None,
    }


def refresh_overview_metrics():
    results = []
    results.extend(collect_testnet_metrics())
    results.extend(collect_portal_metrics())
    results.extend(collect_external_metrics())
    results.append(collect_network_activity())
    results.append(collect_overview_payload())
    return results


def latest_overview_snapshots():
    keys = [
        'decisions_made',
        'chain_transactions',
        'discord_members',
        'telegram_members',
        'x_followers',
        'github_boilerplate_stars',
        'defillama_fees_rank',
    ]
    return {key: serialize_snapshot(latest_snapshot(key)) for key in keys}


def empty_overview_payload():
    return {
        'version': OVERVIEW_PAYLOAD_VERSION,
        'metrics': {
            'decisions_made': None,
            'chain_transactions': None,
            'builders': None,
            'validators': None,
            'community_members': None,
            'contributions': None,
            'discord_members': None,
            'telegram_members': None,
            'x_followers': None,
            'github_boilerplate_stars': None,
            'defillama_fees_rank': None,
        },
        'top_validators': [],
        'generated_at': None,
    }


def build_overview_payload():
    generated_at = timezone.now()
    snapshots = latest_overview_snapshots()
    counts = get_portal_counts()
    return {
        'version': OVERVIEW_PAYLOAD_VERSION,
        'metrics': {
            'decisions_made': snapshots.get('decisions_made'),
            'chain_transactions': snapshots.get('chain_transactions'),
            'builders': overview_count_metric('builders', 'Builders', counts['builders'], generated_at),
            'validators': overview_count_metric('validators', 'Validators', counts['validators'], generated_at),
            'community_members': overview_count_metric(
                'community_members',
                'Creators',
                counts['community_members'],
                generated_at,
            ),
            'contributions': overview_count_metric(
                'contributions',
                'Contributions',
                counts['contributions'],
                generated_at,
            ),
            'discord_members': snapshots.get('discord_members'),
            'telegram_members': snapshots.get('telegram_members'),
            'x_followers': snapshots.get('x_followers'),
            'github_boilerplate_stars': snapshots.get('github_boilerplate_stars'),
            'defillama_fees_rank': snapshots.get('defillama_fees_rank'),
        },
        'top_validators': get_top_validators(limit=4),
        'generated_at': generated_at.isoformat(),
    }


def collect_overview_payload():
    try:
        payload = build_overview_payload()
    except Exception as exc:
        return snapshot_error(OVERVIEW_PAYLOAD_METRIC_KEY, 'composite', exc)
    return snapshot(
        OVERVIEW_PAYLOAD_METRIC_KEY,
        'composite',
        None,
        unit='payload',
        label='Overview payload',
        raw_payload=payload,
    )


def latest_overview_payload():
    snap = latest_snapshot(OVERVIEW_PAYLOAD_METRIC_KEY)
    if snap is None or not isinstance(snap.raw_payload, dict):
        return None
    payload = dict(snap.raw_payload)
    if payload.get('version') != OVERVIEW_PAYLOAD_VERSION:
        return None
    payload['generated_at'] = snap.observed_at.isoformat()
    return payload


def get_top_validators(limit=3):
    from validators.models import ValidatorWallet

    # Primary source: validators hand-picked in admin (show_in_overview), shown by
    # name + assets under management only — never the chain they run on.
    showcase = (
        ValidatorWallet.objects
        .filter(show_in_overview=True)
        .select_related('operator', 'operator__user')
        .order_by('overview_order', '-assets_under_management_usd', 'operator_address')
    )
    showcase_result = []
    seen = set()
    for wallet in showcase:
        key = wallet.operator_id or wallet.operator_address.lower()
        if key in seen:
            continue
        seen.add(key)
        user = (
            wallet.operator.user
            if wallet.operator and wallet.operator.user and wallet.operator.user.visible
            else None
        )
        name = (user.name if user and user.name else wallet.moniker) or 'Validator'
        showcase_result.append({
            'rank': len(showcase_result) + 1,
            'name': name,
            'subtitle': '',
            'aum': format_usd(wallet.assets_under_management_usd),
            'aum_usd': float(wallet.assets_under_management_usd) if wallet.assets_under_management_usd is not None else None,
            'logo_uri': wallet.logo_uri or '',
            'profile_image_url': (user.profile_image_url if user else '') or '',
            'website_url': wallet.website or '',
            'networks': [],
            'total_stake_gen': None,
        })
        if len(showcase_result) >= limit:
            break
    if showcase_result:
        return showcase_result

    curated = getattr(settings, 'OVERVIEW_TOP_VALIDATORS', [])
    if isinstance(curated, str):
        try:
            curated = json.loads(curated or '[]')
        except json.JSONDecodeError:
            curated = []
    if isinstance(curated, list) and curated:
        validators = []
        for index, item in enumerate(curated[:limit], start=1):
            if not isinstance(item, dict):
                continue
            validators.append({
                'rank': item.get('rank') or index,
                'name': item.get('name') or 'Validator',
                'subtitle': item.get('subtitle') or item.get('network') or '',
                'aum': item.get('aum') or item.get('assets_under_management') or '',
                'logo_uri': item.get('logo_uri') or item.get('logo_url') or '',
                'profile_image_url': item.get('profile_image_url') or '',
                'website_url': item.get('website_url') or '',
                'networks': item.get('networks') or [],
                'total_stake_gen': item.get('total_stake_gen'),
            })
        if validators:
            return validators

    from validators.models import ValidatorWallet

    wallets = (
        ValidatorWallet.objects
        .filter(status='active')
        .select_related('operator', 'operator__user')
        .order_by('operator_id', 'operator_address')
    )
    grouped = {}
    for wallet in wallets:
        key = wallet.operator_id or wallet.operator_address.lower()
        entry = grouped.setdefault(key, {
            'name': wallet.moniker or 'Validator',
            'address': wallet.operator_address,
            'profile_image_url': '',
            'logo_uri': '',
            'wallet_count': 0,
            'networks': set(),
            'total_stake_wei': 0,
        })
        user = wallet.operator.user if wallet.operator and wallet.operator.user and wallet.operator.user.visible else None
        if user:
            entry['name'] = user.name or wallet.moniker or 'Validator'
            entry['address'] = user.address or wallet.operator_address
            entry['profile_image_url'] = user.profile_image_url or ''
        if wallet.logo_uri and not entry['logo_uri']:
            entry['logo_uri'] = wallet.logo_uri
        entry['wallet_count'] += 1
        entry['networks'].add(wallet.network)
        for raw_stake in (wallet.v_stake, wallet.d_stake):
            try:
                entry['total_stake_wei'] += int(raw_stake or 0)
            except (TypeError, ValueError):
                continue

    ordered = sorted(grouped.values(), key=lambda item: item['total_stake_wei'], reverse=True)[:limit]
    for index, entry in enumerate(ordered, start=1):
        entry['rank'] = index
        entry['total_stake_gen'] = entry['total_stake_wei'] // (10 ** GEN_DECIMALS)
        entry['networks'] = sorted(entry['networks'])
    return ordered
