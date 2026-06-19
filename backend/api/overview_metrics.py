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
NETWORK_ACTIVITY_DAYS = NETWORK_ACTIVITY_WEEKS * 7
NETWORK_ACTIVITY_INTERVAL = 'week'
STUDIO_NETWORK_ACTIVITY_RANGE = 'quarter'
# The three surfaces whose decisions/chain-tx feed the overview chart + headline.
NETWORK_ACTIVITY_SOURCES = ('studio',) + TESTNET_NETWORKS


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
        'observed_at': item.observed_at,
        'dimensions': item.dimensions,
        'status': item.status,
        'error': item.error,
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
    # ponytail: env fallback mirrors DEFILLAMA_FEES_RANK — show a curated number until a bot is wired
    manual = getattr(settings, 'TELEGRAM_MEMBERS', '')
    if manual:
        return snapshot('telegram_members', 'telegram', manual, label='Telegram members')
    return snapshot_error(
        'telegram_members',
        'telegram',
        'TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID or TELEGRAM_MEMBERS is not configured',
    )


def collect_x_followers():
    token = getattr(settings, 'X_BEARER_TOKEN', '')
    username = getattr(settings, 'X_METRICS_USERNAME', 'GenLayer')
    if not token:
        return snapshot_error('x_followers', 'x', 'X_BEARER_TOKEN is not configured')

    response = requests.get(
        f'https://api.x.com/2/users/by/username/{username}',
        params={'user.fields': 'public_metrics'},
        headers={'Authorization': f'Bearer {token}'},
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json() or {}
    metrics = payload.get('data', {}).get('public_metrics', {})
    return snapshot(
        'x_followers',
        'x',
        metrics.get('followers_count'),
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
            results.append(snapshot_error(metric_key, metric_key.split('_')[0], exc))
    return results


# ---------------------------------------------------------------------------
# Network activity (overview chart): weekly decisions across Studio + testnets.
# Fetched here so the 15-minute cron persists it and the read endpoint can serve
# straight from the DB instead of doing a live multi-API fetch per request.
# ---------------------------------------------------------------------------

def _week_start_for_ts(ts):
    d = datetime.fromtimestamp(int(ts), tz=dt_timezone.utc).date()
    return d - timedelta(days=d.weekday())


def _week_key(week_start):
    return week_start.isoformat()


def _week_label(week_start):
    week_end = week_start + timedelta(days=6)
    if week_start.month == week_end.month:
        return f'{week_start:%b} {week_start.day}-{week_end.day}'
    return f'{week_start:%b} {week_start.day} - {week_end:%b} {week_end.day}'


def _utc_midnight_ts(d):
    return int(datetime(d.year, d.month, d.day, tzinfo=dt_timezone.utc).timestamp())


def _weekly_points(points, limit=NETWORK_ACTIVITY_WEEKS):
    buckets = {}
    for ts, value in points:
        week_start = _week_start_for_ts(ts)
        buckets[week_start] = buckets.get(week_start, 0) + int(value or 0)
    return [
        {'week_start': _week_key(week_start), 'label': _week_label(week_start), 'value': value}
        for week_start, value in sorted(buckets.items())[-limit:]
    ]


def _daily_points_from_values(values, now):
    end_date = datetime.fromtimestamp(int(now), tz=dt_timezone.utc).date()
    start_date = end_date - timedelta(days=max(len(values) - 1, 0))
    return [
        (_utc_midnight_ts(start_date + timedelta(days=i)), round(float(value or 0)))
        for i, value in enumerate(values)
    ]


def fetch_explorer_decisions(network, frm, now):
    base = EXPLORER_BASE_URLS[network]
    history = requests.get(
        f'{base}/api/v1/analytics/kpi-histories',
        params={
            'metric': 'total_finalized_transactions',
            'interval': 'D1',
            'from_timestamp': frm,
            'to_timestamp': now,
        },
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    general = requests.get(f'{base}/api/v1/analytics/general-kpis', timeout=HTTP_TIMEOUT_SECONDS)
    history.raise_for_status()
    general.raise_for_status()
    buckets = (history.json() or {}).get('histories') or []
    points = []
    for bucket in buckets:
        if not isinstance(bucket, dict):
            continue
        try:
            points.append((int(bucket['timestamp']), round(float(bucket.get('value') or 0))))
        except (TypeError, ValueError, KeyError):
            continue
    weekly = _weekly_points(points)
    gen = general.json() or {}
    return {
        'points': weekly,
        'labels': [point['label'] for point in weekly],
        'values': [point['value'] for point in weekly],
        'decisions_all_time': int(gen.get('total_finalized_transactions') or 0),
        'chain_all_time': int(gen.get('total_rollup_transactions') or 0),
    }


def fetch_studio_decisions(now):
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
    values = [round(float(v or 0)) for v in (decisions.get('sparkline') or [])]
    weekly = _weekly_points(_daily_points_from_values(values, now))
    return {
        'points': weekly,
        'labels': [point['label'] for point in weekly],
        'values': [point['value'] for point in weekly],
        'decisions_all_time': int(decisions.get('allTimeValue') or 0),
        'chain_all_time': int(chain.get('allTimeValue') or 0),
    }


def _network_activity_fees_rank():
    rank_snapshot = latest_snapshot('defillama_fees_rank')
    if rank_snapshot and rank_snapshot.value is not None:
        return float(rank_snapshot.value)
    configured = getattr(settings, 'DEFILLAMA_FEES_RANK', '')
    try:
        return float(configured) if configured else None
    except (TypeError, ValueError):
        return None


def build_network_activity():
    """Assemble the overview-chart payload (3 weekly curves + all-time totals).

    Each source degrades independently; a failed upstream is just omitted.
    """
    now = int(timezone.now().timestamp())
    frm = now - NETWORK_ACTIVITY_DAYS * 86400

    source_series = []
    all_time = {}  # per-source {decisions, chain} for sources that resolved this run

    # Studio first so it leads the legend/stack.
    try:
        studio = fetch_studio_decisions(now)
        if studio['points']:
            source_series.append({'key': 'studio', 'label': 'Studio', 'points': studio['points']})
        all_time['studio'] = {'decisions': studio['decisions_all_time'], 'chain': studio['chain_all_time']}
    except Exception as exc:
        logger.warning('Network activity: studio source failed: %s', exc)

    for network in TESTNET_NETWORKS:
        try:
            net = fetch_explorer_decisions(network, frm, now)
        except Exception as exc:
            logger.warning('Network activity: %s source failed: %s', network, exc)
            continue
        if net['points']:
            source_series.append({'key': network, 'label': network.title(), 'points': net['points']})
        all_time[network] = {'decisions': net['decisions_all_time'], 'chain': net['chain_all_time']}

    week_keys = sorted({
        point['week_start']
        for item in source_series
        for point in item['points']
    })[-NETWORK_ACTIVITY_WEEKS:]
    label_by_week = {
        point['week_start']: point['label']
        for item in source_series
        for point in item['points']
    }
    labels = [label_by_week[key] for key in week_keys]
    series = []
    for item in source_series:
        values_by_week = {point['week_start']: point['value'] for point in item['points']}
        values = [values_by_week.get(key) for key in week_keys]
        if any(value is not None for value in values):
            series.append({'key': item['key'], 'label': item['label'], 'values': values})

    # Backfill the all-time figure of any source that failed this run from the
    # last good snapshot, so a transient upstream blip never undercounts the
    # investor-facing headline totals (and never shows 0).
    previous = _latest_network_activity_payload()
    previous_all_time = (previous[1].get('all_time_by_source') or {}) if previous else {}
    merged_all_time = {}
    for key in NETWORK_ACTIVITY_SOURCES:
        if key in all_time:
            merged_all_time[key] = all_time[key]
        elif key in previous_all_time:
            merged_all_time[key] = previous_all_time[key]
            # All-time counters only grow, so carrying the last-known value is the
            # least-wrong choice during an outage (dropping the source would cliff
            # the headline). Log so a prolonged outage is visible to ops.
            logger.warning('Network activity: %s all-time backfilled from previous snapshot', key)

    decisions_total = sum(int(v.get('decisions') or 0) for v in merged_all_time.values())
    chain_total = sum(int(v.get('chain') or 0) for v in merged_all_time.values())

    return {
        'labels': labels,
        'series': series,
        'interval': NETWORK_ACTIVITY_INTERVAL,
        'totals': {
            'decisions_made': decisions_total,
            'chain_transactions': chain_total,
            'defillama_fees_rank': _network_activity_fees_rank(),
        },
        'all_time_by_source': merged_all_time,
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
    # The public overview must not keep serving a pre-weekly daily snapshot after
    # deploy. Returning None makes the read view rebuild weekly data live once;
    # the cron then persists a fresh weekly snapshot.
    if payload.get('interval') != NETWORK_ACTIVITY_INTERVAL:
        return None
    # ISO string so the response is identical whether served fresh or from cache,
    # regardless of the cache backend's (de)serialization.
    payload['generated_at'] = snap.observed_at.isoformat()
    return payload


def refresh_overview_metrics():
    results = []
    results.extend(collect_testnet_metrics())
    results.extend(collect_portal_metrics())
    results.extend(collect_external_metrics())
    # Last, so the freshly-collected DeFiLlama rank is available to the totals.
    results.append(collect_network_activity())
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
