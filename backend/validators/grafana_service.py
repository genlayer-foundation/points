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
import re

import requests
from django.conf import settings
from django.utils import timezone
from packaging.version import parse as parse_version

from .models import (
    Validator,
    ValidatorWallet,
    ValidatorWalletObservation,
    ValidatorWalletStatusSnapshot,
)
from .version_status import compute_version_status, safe_parse_version as _safe_parse

logger = logging.getLogger(__name__)

# Metrics/logs latch PESSIMISTICALLY (worst-of-day): one shame sample shames the
# whole day. Higher number = worse; _latch keeps the worse of prev/cur.
_METRICS_SEVERITY = {'unknown': 0, 'on': 1, 'shame': 2}

# Version latches OPTIMISTICALLY (best-of-day): a single up-to-date sample makes
# the day OK — once a node has upgraded that day, an earlier stale reading must
# not shame it. Higher number = better; _latch_version keeps the better of prev/cur.
_VERSION_GOODNESS = {'unknown': 0, 'shame': 1, 'warning': 2, 'on': 3}

# Node versions from Prometheus arrive as e.g. "v0.5.12"; the profile field forbids
# the leading "v". A stable release is a bare x.y.z (no -prerelease / +build).
_SEMVER_RE = re.compile(r'^\d+\.\d+\.\d+(-[a-zA-Z0-9\-.]+)?(\+[a-zA-Z0-9\-.]+)?$')
_STABLE_RE = re.compile(r'^\d+\.\d+\.\d+$')

# node_version columns are varchar(50); anything longer is operator-controlled junk.
_VERSION_MAX_LENGTH = 50

def min_operators_for_auto_target():
    """
    A stable release only becomes an auto-created target once this many distinct
    operators report it: the version label is self-reported by the node being judged
    and rewarded, so a single (malicious or misconfigured) operator must not be able
    to pin a fleet-wide target and shame everyone else / bank the first-adopter bonus.
    Read at call time (not import) so the setting is tunable without a code deploy.
    """
    return getattr(settings, 'NODE_VERSION_MIN_OPERATORS_FOR_AUTO_TARGET', 2)


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
            version series for ~5 minutes; the higher parseable version wins (and
            a parseable one always beats an unparseable one) so frame order can
            neither transiently downgrade a freshly-upgraded node nor pin a
            garbage label.
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
                            # A parseable version always beats an unparseable one
                            # (frame order must not pin a garbage label); between
                            # two parseable ones the higher wins.
                            if cur_parsed is not None and (
                                prev_parsed is None or cur_parsed > prev_parsed
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

        now = timezone.now()

        # Version detection covers every reporting node on the network (any on-chain
        # status), not just the active wallets checked for shame below — so it runs
        # before the no-active-wallets early return. It can auto-create a target, so
        # it also runs before the shame loop reads the active target.
        cls._sync_node_versions(network, version_by_addr, now)

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
            # a non-reporting node is already metrics/logs shame. Unparseable
            # versions read as 'unknown' inside compute_version_status (exact
            # target match excepted) — never a lexicographic verdict.
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

        # A blackout of a whole datasource (no Prometheus series at all, or no Loki
        # log counts at all) is an infra/config failure (rotated datasource UID,
        # token scope, renamed network label), not the entire fleet failing at once.
        # The live wallet statuses above self-heal on the next good run, but the
        # daily rollup latches worst-of-day permanently — so skip the history write
        # for suspect runs instead of shaming every validator's recorded day.
        if not prom_addresses or not log_counts:
            logger.error(
                "Grafana sync for %s returned no %s data; skipping history latch for this run",
                network, 'Prometheus' if not prom_addresses else 'Loki',
            )
        else:
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
        except Exception:  # pragma: no cover - defensive
            logger.exception("Failed to record validator observation history")

    @classmethod
    def _sync_node_versions(cls, network, version_by_address, now):
        """
        Grafana is the source of truth for node versions. From the versions observed
        this run ({address_lower: version}):
          1. auto-create a TargetNodeVersion when a STABLE release higher than the
             active target is reported by at least min_operators_for_auto_target()
             distinct linked operators (target_date=now);
          2. raise each linked operator's node_version_<network> to the highest
             valid version across their nodes (bypassing the profile-save path via
             a direct .update());
          3. directly award the node-upgrade contribution when an operator first
             reaches the active target.

        Trust boundary: the `version` label is self-reported by the node being
        judged and rewarded. Only versions observed on wallets known to this DB and
        linked to an operator count for anything, banned wallets count for nothing,
        and no single operator can move the fleet-wide target on their own.

        Any non-banned wallet qualifies for (2)/(3) — a quarantined/inactive node
        that still reports can record its upgrade and earn the award.

        Best-effort at two levels: the whole step never raises, and one operator's
        failure never blocks version updates or awards for the others.
        """
        try:
            from contributions.node_upgrade.models import TargetNodeVersion

            # Normalise + keep only field-valid, PEP 440-parseable semvers — anything
            # unparseable can't be compared, so it can't drive targets or awards.
            normalized = {}
            for addr, raw in version_by_address.items():
                v = _normalize_version(raw)
                if v and _SEMVER_RE.match(v) and _safe_parse(v) is not None:
                    normalized[addr.lower()] = v
            if not normalized:
                return

            # Versions only count when observed on a known, operator-linked,
            # non-banned wallet: an unknown Prometheus series (test rig, stale or
            # spoofed node) must not be able to move targets or earn points.
            wallets = (
                ValidatorWallet.objects
                .filter(network=network, operator__isnull=False)
                .exclude(status='banned')
                .select_related('operator', 'operator__user')
            )
            by_operator = {}
            for wallet in wallets:
                version = normalized.get((wallet.address or '').lower())
                if version:
                    by_operator.setdefault(wallet.operator, []).append(version)
            if not by_operator:
                return

            # (1) Auto-create target from the highest stable release reported by
            # enough distinct operators (min_operators_for_auto_target), so one
            # operator's self-reported label can't pin a bogus fleet-wide target
            # (and farm the first-adopter bonus). An active target with an
            # unparseable version is never superseded blindly.
            operators_by_stable = {}
            for operator, versions in by_operator.items():
                for v in versions:
                    if _STABLE_RE.match(v):
                        operators_by_stable.setdefault(v, set()).add(operator.pk)
            min_operators = min_operators_for_auto_target()
            corroborated = [
                v for v, ops in operators_by_stable.items()
                if len(ops) >= min_operators
            ]
            if corroborated:
                highest = max(corroborated, key=parse_version)
                active = TargetNodeVersion.get_active(network=network)
                active_parsed = _safe_parse(active.version) if active else None
                if not active or (
                    active_parsed is not None and parse_version(highest) > active_parsed
                ):
                    target = TargetNodeVersion.objects.create(
                        version=highest, network=network, target_date=now, is_active=True,
                    )
                    logger.info(
                        "Auto-created node version target %s for %s from Grafana",
                        highest, network,
                    )
                    cls._broadcast_auto_target(target)

            active = TargetNodeVersion.get_active(network=network)
            active_parsed = _safe_parse(active.version) if active else None

            # (2) + (3): per linked operator, using their highest observed version.
            field = f'node_version_{network}'
            for operator, versions in by_operator.items():
                try:
                    highest = max(versions, key=parse_version)
                    current = getattr(operator, field, None)
                    current_parsed = _safe_parse(current) if current else None
                    # (2) Monotonic write: only raise the stored version. A wallet
                    # that skips one scrape must not transiently downgrade the
                    # operator's version (and flip their wall-of-shame verdict).
                    # Genuine downgrades are not reflected until admin-corrected.
                    if current != highest and (
                        current_parsed is None or parse_version(highest) > current_parsed
                    ):
                        # Direct update bypasses NodeVersionMixin.save() so we control
                        # the award path (direct/approved).
                        Validator.objects.filter(pk=operator.pk).update(**{field: highest})
                        setattr(operator, field, highest)
                    # (3) Award once the operator (visible) reaches the active target.
                    if (
                        active
                        and active_parsed is not None
                        and operator.user_id
                        and getattr(operator.user, 'visible', False)
                        and parse_version(highest) >= active_parsed
                    ):
                        cls._award_node_upgrade(operator, network, active, now)
                except Exception:
                    logger.exception(
                        "Node version sync failed for operator %s on %s",
                        operator.pk, network,
                    )
        except Exception:  # pragma: no cover - defensive
            logger.exception("Failed to sync node versions for %s", network)

    @staticmethod
    def _broadcast_auto_target(target):
        """Notify validators of an auto-created target; the grace/bonus clock starts now."""
        try:
            from notifications.services import broadcast_target_node_version

            broadcast_target_node_version(
                target,
                message=(
                    f"Target node version for {target.get_network_display()} is now "
                    f"{target.version} (detected on the network). Upgrade within the "
                    "grace period to avoid the Wall of Shame; upgrading sooner earns "
                    "more points."
                ),
            )
        except Exception:
            logger.exception(
                "Failed to broadcast auto-created target %s", target.pk,
            )

    @staticmethod
    def _award_node_upgrade(operator, network, target, now):
        """
        Create a direct, already-approved node-upgrade Contribution for a Grafana-
        observed upgrade. Dedup shares the exact key with the manual profile flow
        (`version {v} [{network}]`), so the two paths never double-award.
        """
        from django.db import transaction

        from contributions.models import Contribution, ContributionType, SubmittedContribution
        from leaderboard.models import GlobalLeaderboardMultiplier
        from .node_version import calculate_early_upgrade_bonus

        contribution_type = ContributionType.objects.filter(slug='node-upgrade').first()
        if not contribution_type:
            return

        user = operator.user
        dedup_key = f"version {target.version} [{network}]"

        points = calculate_early_upgrade_bonus(target.target_date, now)
        try:
            _, multiplier_value = GlobalLeaderboardMultiplier.get_active_for_type(
                contribution_type, at_date=now,
            )
        except GlobalLeaderboardMultiplier.DoesNotExist:
            # Removing the multiplier is how stewards pause a points program; the
            # auto-award must respect that kill switch, not award at 1.0 anyway.
            logger.warning(
                "Skipping node-upgrade award for %s on %s: no active multiplier",
                user.pk, network,
            )
            return

        with transaction.atomic():
            # The grafana sync lock already serializes runs; locking the user row
            # here closes the residual stale-lock-takeover window so the dedup
            # check-then-create below can never double-award (no-op on SQLite).
            type(user).objects.select_for_update().get(pk=user.pk)

            already_awarded = Contribution.objects.filter(
                user=user, contribution_type=contribution_type, notes__contains=dedup_key,
            ).exists()
            pending = SubmittedContribution.objects.filter(
                user=user, contribution_type=contribution_type,
                state__in=['pending', 'accepted'], notes__contains=dedup_key,
            ).exists()
            if already_awarded or pending:
                return

            Contribution(
                user=user,
                contribution_type=contribution_type,
                points=points,
                contribution_date=now,
                multiplier_at_creation=multiplier_value,
                frozen_global_points=round(points * float(multiplier_value)),
                notes=(
                    f"Automatic node upgrade to version {target.version} "
                    f"[{network}] (detected via Grafana)"
                ),
            ).save()  # post_save signal updates the leaderboard

    @classmethod
    def sync_all_networks(cls):
        """Sync every configured network. Returns a list of per-network stats."""
        return [cls.sync_network(network) for network in settings.TESTNET_NETWORKS.keys()]
