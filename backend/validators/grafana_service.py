"""
Grafana Wall of Shame service.

Mirrors the GenLayer Foundation "Validator Overview" Grafana dashboard server-side:
for each on-chain active validator wallet, checks whether the node has been
reporting Prometheus metrics and Loki logs in the last 5 minutes. Results are
written inline on ValidatorWallet (metrics_status, logs_status,
last_grafana_check_at) so the public Wall of Shame endpoint serves from the
points DB without round-tripping to Grafana per request.
"""

import logging

import requests
from django.conf import settings
from django.utils import timezone
from packaging.version import InvalidVersion, parse as parse_version

from .models import (
    ValidatorWallet,
    ValidatorWalletObservation,
    ValidatorWalletStatusSnapshot,
)
from .version_status import compute_version_status

logger = logging.getLogger(__name__)

# Metrics/logs latch PESSIMISTICALLY (worst-of-day): one shame sample shames the
# whole day. Higher number = worse; _latch keeps the worse of prev/cur.
_METRICS_SEVERITY = {'unknown': 0, 'on': 1, 'shame': 2}

# Version latches OPTIMISTICALLY (best-of-day): a single up-to-date sample makes
# the day OK — once a node has upgraded that day, an earlier stale reading must
# not shame it. Higher number = better; _latch_version keeps the better of prev/cur.
_VERSION_GOODNESS = {'unknown': 0, 'shame': 1, 'warning': 2, 'on': 3}

# node_version columns are varchar(50); anything longer is operator-controlled junk.
_VERSION_MAX_LENGTH = 50


def _latch(prev, cur, severity):
    """Return whichever of prev/cur is worse (higher severity) — worst-of-day."""
    return prev if severity.get(prev, 0) >= severity.get(cur, 0) else cur


def _latch_version(prev, cur):
    """Return the better of prev/cur (higher goodness) — best-of-day for version."""
    return prev if _VERSION_GOODNESS.get(prev, 0) >= _VERSION_GOODNESS.get(cur, 0) else cur


def _normalize_version(raw):
    """Strip a leading 'v' so a Prometheus 'v0.5.12' matches the profile field format."""
    if not raw:
        return ''
    v = raw.strip()
    if v[:1] in ('v', 'V'):
        v = v[1:]
    return v


def _safe_parse(v):
    """
    packaging Version, or None when the string is not PEP 440-parseable.

    Semver strings like '0.6.0-genlayer.1' are valid semver but invalid PEP 440;
    parse_version() raising on one node's label must never abort a whole sync.
    """
    try:
        return parse_version(v)
    except InvalidVersion:
        return None


class GrafanaValidatorStatusService:
    HTTP_TIMEOUT_SECONDS = 10

    @staticmethod
    def _build_query_body(network_label, prom_ds_uid, loki_ds_uid):
        """Build the /api/ds/query body matching the dashboard's panel-1 query B."""
        prom_expr = (
            'max by(validator_name, node, version) '
            '(genlayer_node_info{job="prometheus.scrape.genlayer_node", '
            f'network="{network_label}"}})'
        )
        loki_expr = (
            'sum by (validator_name) '
            '(count_over_time({job="genlayer-node"} | json | '
            f'network="{network_label}" [5m]))'
        )
        return {
            'queries': [
                {
                    'datasource': {'type': 'prometheus', 'uid': prom_ds_uid},
                    'expr': prom_expr,
                    'format': 'table',
                    'instant': True,
                    'refId': 'prom',
                },
                {
                    'datasource': {'type': 'loki', 'uid': loki_ds_uid},
                    'expr': loki_expr,
                    'queryType': 'instant',
                    'refId': 'loki',
                },
            ],
            'from': 'now-5m',
            'to': 'now',
        }

    @staticmethod
    def parse_response(body):
        """
        Parse a Grafana /api/ds/query response.

        Returns a 4-tuple:
          - prom_addresses: set of lowercased validator addresses reporting metrics
          - validator_name_by_address: {address_lower: validator_name}
          - log_counts_by_name: {validator_name: log_count}
          - version_by_address: {address_lower: node_version} (from the `version`
            label, normalised — 'v' prefix stripped, capped to the column length).
            Right after an upgrade Prometheus can return BOTH the old and new
            version series for ~5 minutes; the higher parseable version wins so a
            stale frame can't transiently downgrade a freshly-upgraded node.
        """
        results = (body or {}).get('results') or {}
        prom_frames = ((results.get('prom') or {}).get('frames')) or []
        loki_frames = ((results.get('loki') or {}).get('frames')) or []

        prom_addresses = set()
        validator_name_by_address = {}
        version_by_address = {}
        for frame in prom_frames:
            schema = frame.get('schema') or {}
            for field in schema.get('fields') or []:
                labels = field.get('labels') or {}
                vname = labels.get('validator_name')
                node = labels.get('node') or ''
                if vname and node:
                    addr = node.lower()
                    prom_addresses.add(addr)
                    validator_name_by_address[addr] = vname
                    version = _normalize_version(labels.get('version'))[:_VERSION_MAX_LENGTH]
                    if version:
                        prev = version_by_address.get(addr)
                        if prev is None:
                            version_by_address[addr] = version
                        else:
                            prev_parsed = _safe_parse(prev)
                            cur_parsed = _safe_parse(version)
                            if (
                                prev_parsed is not None
                                and cur_parsed is not None
                                and cur_parsed > prev_parsed
                            ):
                                version_by_address[addr] = version

        log_counts_by_name = {}
        for frame in loki_frames:
            schema = frame.get('schema') or {}
            vname = None
            for field in schema.get('fields') or []:
                labels = field.get('labels') or {}
                if labels.get('validator_name'):
                    vname = labels['validator_name']
                    break
            if not vname:
                continue
            data = frame.get('data') or {}
            values = data.get('values') or []
            count = 0
            if len(values) > 1 and values[1]:
                try:
                    count = int(values[1][0] or 0)
                except (TypeError, ValueError):
                    count = 0
            log_counts_by_name[vname] = count

        return prom_addresses, validator_name_by_address, log_counts_by_name, version_by_address

    @classmethod
    def sync_network(cls, network):
        """
        Sync Grafana metrics/logs status for one network. Returns a stats dict.
        Never raises: logs and returns an error key on any failure so the caller
        can continue with other networks.
        """
        base_url = (settings.GRAFANA_BASE_URL or '').rstrip('/')
        token = settings.GRAFANA_API_TOKEN
        if not base_url or not token:
            logger.warning(
                "Grafana sync skipped for %s: GRAFANA_BASE_URL or GRAFANA_API_TOKEN not set",
                network,
            )
            return {'network': network, 'skipped': True, 'reason': 'config'}

        network_label = settings.GRAFANA_NETWORK_LABELS.get(network)
        if not network_label:
            logger.warning(
                "Grafana sync skipped for %s: no GRAFANA_NETWORK_LABELS entry",
                network,
            )
            return {'network': network, 'skipped': True, 'reason': 'no_label'}

        body = cls._build_query_body(
            network_label,
            settings.GRAFANA_PROM_DS_UID,
            settings.GRAFANA_LOKI_DS_UID,
        )
        url = f'{base_url}/api/ds/query'

        try:
            response = requests.post(
                url,
                json=body,
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json',
                },
                timeout=cls.HTTP_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            logger.warning("Grafana request failed for %s: %s", network, exc)
            return {'network': network, 'error': str(exc)}

        if not response.ok:
            logger.warning(
                "Grafana returned %s for %s: %s",
                response.status_code, network, response.text[:500],
            )
            return {'network': network, 'error': f'HTTP {response.status_code}'}

        try:
            data = response.json()
        except ValueError as exc:
            logger.warning("Grafana returned non-JSON for %s: %s", network, exc)
            return {'network': network, 'error': 'invalid_json'}

        prom_addresses, name_by_addr, log_counts, version_by_addr = cls.parse_response(data)

        wallets = list(
            ValidatorWallet.objects
            .filter(network=network, status='active')
            .only(
                'id',
                'address',
                'status',
                'metrics_status',
                'logs_status',
                'metrics_shame_started_at',
                'logs_shame_started_at',
            )
        )

        if not wallets:
            logger.info("Grafana sync for %s: no active wallets to update", network)
            return {'network': network, 'wallets': 0}

        from contributions.node_upgrade.models import TargetNodeVersion
        target = TargetNodeVersion.get_active(network=network)

        now = timezone.now()
        on_count = 0
        shame_count = 0
        samples = []

        for wallet in wallets:
            addr_lower = (wallet.address or '').lower()
            metrics_ok = addr_lower in prom_addresses
            vname = name_by_addr.get(addr_lower)
            logs_ok = bool(vname and log_counts.get(vname, 0) > 0)
            observed_version = version_by_addr.get(addr_lower) or ''

            metrics_status = 'on' if metrics_ok else 'shame'
            logs_status = 'on' if logs_ok else 'shame'
            # Only assess version when we actually observed a running version;
            # a non-reporting node is already metrics/logs shame.
            version_status = (
                compute_version_status(wallet, target, now, node_version=observed_version)['status']
                if observed_version else 'unknown'
            )

            if metrics_status == 'shame':
                if wallet.metrics_status != 'shame' or not wallet.metrics_shame_started_at:
                    wallet.metrics_shame_started_at = now
            else:
                wallet.metrics_shame_started_at = None

            if logs_status == 'shame':
                if wallet.logs_status != 'shame' or not wallet.logs_shame_started_at:
                    wallet.logs_shame_started_at = now
            else:
                wallet.logs_shame_started_at = None

            wallet.metrics_status = metrics_status
            wallet.logs_status = logs_status
            wallet.last_grafana_check_at = now

            samples.append({
                'wallet': wallet,
                'onchain_status': wallet.status,
                'metrics_status': metrics_status,
                'logs_status': logs_status,
                'version_status': version_status,
                'node_version': observed_version,
                'metrics_ok': metrics_ok,
                'logs_ok': logs_ok,
            })

            if metrics_ok and logs_ok:
                on_count += 1
            else:
                shame_count += 1

        ValidatorWallet.objects.bulk_update(
            wallets,
            [
                'metrics_status',
                'logs_status',
                'last_grafana_check_at',
                'metrics_shame_started_at',
                'logs_shame_started_at',
            ],
        )

        cls._record_history(samples, now)

        logger.info(
            "Grafana sync for %s: %d on, %d shame (%d total)",
            network, on_count, shame_count, len(wallets),
        )
        return {
            'network': network,
            'wallets': len(wallets),
            'on': on_count,
            'shame': shame_count,
        }

    @classmethod
    def _record_history(cls, samples, now):
        """
        Persist the raw observations for this sync run and latch them into today's
        per-day rollup (worst-of-day). Never raises: history is best-effort and must
        not break the live status sync.
        """
        if not samples:
            return
        try:
            today = timezone.localdate(now)

            ValidatorWalletObservation.objects.bulk_create([
                ValidatorWalletObservation(
                    wallet=s['wallet'],
                    observed_at=now,
                    onchain_status=s['onchain_status'],
                    metrics_status=s['metrics_status'],
                    logs_status=s['logs_status'],
                    version_status=s['version_status'],
                    node_version=s['node_version'],
                )
                for s in samples
            ])

            wallet_ids = [s['wallet'].id for s in samples]
            existing = {
                snap.wallet_id: snap
                for snap in ValidatorWalletStatusSnapshot.objects.filter(
                    wallet_id__in=wallet_ids, date=today
                )
            }

            rollups = []
            for s in samples:
                wallet = s['wallet']
                prev = existing.get(wallet.id)
                prev_metrics = prev.metrics_status if prev else 'unknown'
                prev_logs = prev.logs_status if prev else 'unknown'
                prev_version = prev.version_status if prev else 'unknown'
                prev_m_samples = prev.metrics_samples if prev else 0
                prev_l_samples = prev.logs_samples if prev else 0

                rollups.append(ValidatorWalletStatusSnapshot(
                    wallet=wallet,
                    date=today,
                    status=wallet.status,
                    metrics_status=_latch(prev_metrics, s['metrics_status'], _METRICS_SEVERITY),
                    logs_status=_latch(prev_logs, s['logs_status'], _METRICS_SEVERITY),
                    version_status=_latch_version(prev_version, s['version_status']),
                    node_version=s['node_version'] or (prev.node_version if prev else ''),
                    metrics_samples=prev_m_samples + (1 if s['metrics_ok'] else 0),
                    logs_samples=prev_l_samples + (1 if s['logs_ok'] else 0),
                ))

            # On insert, `status` is set from the wallet; on conflict only the
            # observability columns update, so the on-chain sync's `status` is preserved.
            ValidatorWalletStatusSnapshot.objects.bulk_create(
                rollups,
                update_conflicts=True,
                unique_fields=['wallet', 'date'],
                update_fields=[
                    'metrics_status', 'logs_status', 'version_status',
                    'node_version', 'metrics_samples', 'logs_samples',
                ],
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to record validator observation history: %s", exc)

    @classmethod
    def sync_all_networks(cls):
        """Sync every configured network. Returns a list of per-network stats."""
        return [cls.sync_network(network) for network in settings.TESTNET_NETWORKS.keys()]
