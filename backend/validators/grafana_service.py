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

from .models import ValidatorWallet

logger = logging.getLogger(__name__)


class GrafanaValidatorStatusService:
    HTTP_TIMEOUT_SECONDS = 10

    @staticmethod
    def _build_query_body(network_label, prom_ds_uid, loki_ds_uid):
        """Build the /api/ds/query body matching the dashboard's panel-1 query B."""
        prom_expr = (
            'max by(validator_name, node) '
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

        Returns a 3-tuple:
          - prom_addresses: set of lowercased validator addresses reporting metrics
          - validator_name_by_address: {address_lower: validator_name}
          - log_counts_by_name: {validator_name: log_count}

        Matches the JQ in the dashboard panel-1 query B exactly.
        """
        results = (body or {}).get('results') or {}
        prom_frames = ((results.get('prom') or {}).get('frames')) or []
        loki_frames = ((results.get('loki') or {}).get('frames')) or []

        prom_addresses = set()
        validator_name_by_address = {}
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

        return prom_addresses, validator_name_by_address, log_counts_by_name

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

        prom_addresses, name_by_addr, log_counts = cls.parse_response(data)

        wallets = list(
            ValidatorWallet.objects
            .filter(network=network, status='active')
            .only('id', 'address')
        )

        if not wallets:
            logger.info("Grafana sync for %s: no active wallets to update", network)
            return {'network': network, 'wallets': 0}

        now = timezone.now()
        on_count = 0
        shame_count = 0

        for wallet in wallets:
            addr_lower = (wallet.address or '').lower()
            metrics_ok = addr_lower in prom_addresses
            vname = name_by_addr.get(addr_lower)
            logs_ok = bool(vname and log_counts.get(vname, 0) > 0)

            wallet.metrics_status = 'on' if metrics_ok else 'shame'
            wallet.logs_status = 'on' if logs_ok else 'shame'
            wallet.last_grafana_check_at = now

            if metrics_ok and logs_ok:
                on_count += 1
            else:
                shame_count += 1

        ValidatorWallet.objects.bulk_update(
            wallets,
            ['metrics_status', 'logs_status', 'last_grafana_check_at'],
        )

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
    def sync_all_networks(cls):
        """Sync every configured network. Returns a list of per-network stats."""
        return [cls.sync_network(network) for network in settings.TESTNET_NETWORKS.keys()]
