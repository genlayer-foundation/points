"""
Tests for the Grafana Wall of Shame integration.

The Grafana /api/ds/query response shape is undocumented, so the parser is
locked down here with representative fixtures cribbed from the real dashboard
panel-1 query B output. The endpoint tests cover sort order, network
filtering, cache invalidation, and operator identity surfacing.
"""

from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from contributions.node_upgrade.models import TargetNodeVersion
from users.models import User
from validators.models import (
    Validator,
    ValidatorWallet,
    ValidatorWalletObservation,
    ValidatorWalletStatusSnapshot,
)
from validators.grafana_service import GrafanaValidatorStatusService


EMPTY_GRAFANA_RESPONSE = {"results": {"prom": {"frames": []}, "loki": {"frames": []}}}


# Two known validators reporting, one not.
GRAFANA_RESPONSE_FIXTURE = {
    "results": {
        "prom": {
            "frames": [
                {
                    "schema": {
                        "fields": [
                            {
                                "name": "Value",
                                "labels": {
                                    "validator_name": "alice-validator",
                                    "node": "0xAAAAaaaaAAAAaaaaAAAAaaaaAAAAaaaaAAAAaaaa",
                                    "network": "bradbury-phase1",
                                    "version": "v0.5.12",
                                },
                            }
                        ]
                    },
                    "data": {"values": [[1700000000000], [1]]},
                },
                {
                    "schema": {
                        "fields": [
                            {
                                "name": "Value",
                                "labels": {
                                    "validator_name": "bob-validator",
                                    "node": "0xBBBBbbbbBBBBbbbbBBBBbbbbBBBBbbbbBBBBbbbb",
                                    "network": "bradbury-phase1",
                                    "version": "v0.5.11",
                                },
                            }
                        ]
                    },
                    "data": {"values": [[1700000000000], [1]]},
                },
            ]
        },
        "loki": {
            "frames": [
                {
                    "schema": {
                        "fields": [
                            {
                                "name": "Time",
                                "labels": None,
                            },
                            {
                                "name": "Value",
                                "labels": {"validator_name": "alice-validator"},
                            },
                        ]
                    },
                    # values[1][0] = log count (alice has 42 log lines in window)
                    "data": {"values": [[1700000000000], [42]]},
                }
                # Note: no Loki frame for bob → bob has metrics but no logs (logs SHAME)
            ]
        },
    }
}


class GrafanaParseResponseTests(TestCase):
    """Lock down the parser against the dashboard's expected response shape."""

    def test_parses_prometheus_addresses_lowercased(self):
        prom_addrs, _name_by_addr, _log_counts, _versions = (
            GrafanaValidatorStatusService.parse_response(GRAFANA_RESPONSE_FIXTURE)
        )
        # All addresses should be lowercased.
        self.assertIn('0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', prom_addrs)
        self.assertIn('0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', prom_addrs)
        self.assertEqual(len(prom_addrs), 2)

    def test_maps_address_to_validator_name(self):
        _, name_by_addr, _, _ = GrafanaValidatorStatusService.parse_response(
            GRAFANA_RESPONSE_FIXTURE
        )
        self.assertEqual(
            name_by_addr['0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'],
            'alice-validator',
        )
        self.assertEqual(
            name_by_addr['0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'],
            'bob-validator',
        )

    def test_parses_node_version_label_normalized(self):
        # Versions are normalised at ingest ('v' prefix stripped) so every
        # persisted copy (observations, rollups, profile) shares one format.
        _, _, _, version_by_addr = GrafanaValidatorStatusService.parse_response(
            GRAFANA_RESPONSE_FIXTURE
        )
        self.assertEqual(
            version_by_addr['0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'], '0.5.12',
        )
        self.assertEqual(
            version_by_addr['0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'], '0.5.11',
        )

    def test_duplicate_version_series_keeps_the_higher_version(self):
        # Right after an upgrade Prometheus returns BOTH the old and new version
        # series for ~5 minutes; the stale frame must not win regardless of order.
        def frame(version):
            return {
                "schema": {"fields": [{"name": "Value", "labels": {
                    "validator_name": "alice-validator",
                    "node": "0xAAAAaaaaAAAAaaaaAAAAaaaaAAAAaaaaAAAAaaaa",
                    "version": version,
                }}]},
                "data": {"values": [[1700000000000], [1]]},
            }

        for order in (["v0.6.0", "v0.5.11"], ["v0.5.11", "v0.6.0"]):
            body = {"results": {"prom": {"frames": [frame(v) for v in order]},
                                "loki": {"frames": []}}}
            _, _, _, version_by_addr = GrafanaValidatorStatusService.parse_response(body)
            self.assertEqual(
                version_by_addr['0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'],
                '0.6.0',
                f"order {order} let the stale version win",
            )

    def test_overlong_version_label_is_truncated_not_fatal(self):
        long_version = 'v0.5.12-rc.1+build.' + 'a' * 60
        body = {"results": {"prom": {"frames": [{
            "schema": {"fields": [{"name": "Value", "labels": {
                "validator_name": "alice-validator",
                "node": "0xAAAAaaaaAAAAaaaaAAAAaaaaAAAAaaaaAAAAaaaa",
                "version": long_version,
            }}]},
            "data": {"values": [[1700000000000], [1]]},
        }]}, "loki": {"frames": []}}}
        _, _, _, version_by_addr = GrafanaValidatorStatusService.parse_response(body)
        stored = version_by_addr['0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa']
        # Capped to the node_version column length so bulk_create never DataErrors.
        self.assertLessEqual(len(stored), 50)

    def test_loki_log_count_pulled_from_values_index_1(self):
        _, _, log_counts, _ = GrafanaValidatorStatusService.parse_response(
            GRAFANA_RESPONSE_FIXTURE
        )
        self.assertEqual(log_counts['alice-validator'], 42)
        # Bob has no Loki frame at all.
        self.assertNotIn('bob-validator', log_counts)

    def test_empty_response_does_not_crash(self):
        self.assertEqual(
            GrafanaValidatorStatusService.parse_response({}),
            (set(), {}, {}, {}),
        )
        self.assertEqual(
            GrafanaValidatorStatusService.parse_response(None),
            (set(), {}, {}, {}),
        )

    def test_zero_log_count_is_recorded(self):
        body = {
            "results": {
                "prom": {"frames": []},
                "loki": {
                    "frames": [
                        {
                            "schema": {
                                "fields": [
                                    {"name": "Value",
                                     "labels": {"validator_name": "quiet-validator"}}
                                ]
                            },
                            "data": {"values": [[1700000000000], [0]]},
                        }
                    ]
                },
            }
        }
        _, _, log_counts, _ = GrafanaValidatorStatusService.parse_response(body)
        self.assertEqual(log_counts['quiet-validator'], 0)


class GrafanaSyncNetworkTests(TestCase):
    def setUp(self):
        # Three on-chain active validators on bradbury:
        # - alice: has metrics + logs → ON / ON
        # - bob: has metrics, no logs → ON / SHAME
        # - carol: not in Grafana at all → SHAME / SHAME
        self.alice = ValidatorWallet.objects.create(
            address='0xAAAAaaaaAAAAaaaaAAAAaaaaAAAAaaaaAAAAaaaa',  # mixed case on purpose
            network='bradbury',
            operator_address='0x1111111111111111111111111111111111111111',
            status='active',
            moniker='alice',
        )
        self.bob = ValidatorWallet.objects.create(
            address='0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
            network='bradbury',
            operator_address='0x2222222222222222222222222222222222222222',
            status='active',
            moniker='bob',
        )
        self.carol = ValidatorWallet.objects.create(
            address='0xcccccccccccccccccccccccccccccccccccccccc',
            network='bradbury',
            operator_address='0x3333333333333333333333333333333333333333',
            status='active',
            moniker='carol',
        )
        # An inactive wallet that should NEVER appear in the sync.
        self.dave = ValidatorWallet.objects.create(
            address='0xdddddddddddddddddddddddddddddddddddddddd',
            network='bradbury',
            operator_address='0x4444444444444444444444444444444444444444',
            status='banned',
            moniker='dave',
        )

    @patch('validators.grafana_service.requests.post')
    def test_sync_assigns_correct_statuses(self, mock_post):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = GRAFANA_RESPONSE_FIXTURE
        mock_post.return_value = mock_response

        with self.settings(
            GRAFANA_BASE_URL='https://grafana.test',
            GRAFANA_API_TOKEN='test-token',
            GRAFANA_NETWORK_LABELS={'bradbury': 'bradbury-phase1', 'asimov': 'asimov-phase5'},
            GRAFANA_PROM_DS_UID='grafanacloud-prom',
            GRAFANA_LOKI_DS_UID='grafanacloud-logs',
        ):
            stats = GrafanaValidatorStatusService.sync_network('bradbury')

        self.assertEqual(stats['network'], 'bradbury')
        self.assertEqual(stats['wallets'], 3)  # alice, bob, carol — NOT dave (banned)
        self.assertEqual(stats['on'], 1)        # alice only
        self.assertEqual(stats['shame'], 2)     # bob, carol

        self.alice.refresh_from_db()
        self.bob.refresh_from_db()
        self.carol.refresh_from_db()
        self.dave.refresh_from_db()

        self.assertEqual(self.alice.metrics_status, 'on')
        self.assertEqual(self.alice.logs_status, 'on')
        self.assertEqual(self.bob.metrics_status, 'on')
        self.assertEqual(self.bob.logs_status, 'shame')
        self.assertEqual(self.carol.metrics_status, 'shame')
        self.assertEqual(self.carol.logs_status, 'shame')

        # Dave (banned) must be untouched — defaults remain.
        self.assertEqual(self.dave.metrics_status, 'unknown')
        self.assertEqual(self.dave.logs_status, 'unknown')
        self.assertIsNone(self.dave.last_grafana_check_at)

        self.assertIsNotNone(self.alice.last_grafana_check_at)

    @patch('validators.grafana_service.requests.post')
    def test_sync_skips_when_token_missing(self, mock_post):
        with self.settings(GRAFANA_API_TOKEN=''):
            stats = GrafanaValidatorStatusService.sync_network('bradbury')
        self.assertTrue(stats.get('skipped'))
        self.assertEqual(stats['reason'], 'config')
        mock_post.assert_not_called()

    @patch('validators.grafana_service.requests.post')
    def test_sync_handles_request_exception_without_corrupting_data(self, mock_post):
        import requests as _requests
        mock_post.side_effect = _requests.RequestException('boom')

        # Pre-set one wallet's status so we can verify it does NOT get overwritten on failure.
        self.alice.metrics_status = 'on'
        self.alice.logs_status = 'on'
        self.alice.save(update_fields=['metrics_status', 'logs_status'])

        with self.settings(
            GRAFANA_BASE_URL='https://grafana.test',
            GRAFANA_API_TOKEN='test-token',
            GRAFANA_NETWORK_LABELS={'bradbury': 'bradbury-phase1', 'asimov': 'asimov-phase5'},
        ):
            stats = GrafanaValidatorStatusService.sync_network('bradbury')

        self.assertIn('error', stats)
        self.alice.refresh_from_db()
        # Failure must not flip Alice to SHAME.
        self.assertEqual(self.alice.metrics_status, 'on')
        self.assertEqual(self.alice.logs_status, 'on')

    def test_failure_records_no_observations(self):
        import requests as _requests
        with patch('validators.grafana_service.requests.post',
                   side_effect=_requests.RequestException('boom')):
            with self.settings(
                GRAFANA_BASE_URL='https://grafana.test',
                GRAFANA_API_TOKEN='test-token',
                GRAFANA_NETWORK_LABELS={'bradbury': 'bradbury-phase1'},
            ):
                GrafanaValidatorStatusService.sync_network('bradbury')
        self.assertEqual(ValidatorWalletObservation.objects.count(), 0)


class GrafanaHistoryTests(TestCase):
    """Observation log + latched daily rollup captured by the Grafana sync."""

    def setUp(self):
        self.alice = ValidatorWallet.objects.create(
            address='0xAAAAaaaaAAAAaaaaAAAAaaaaAAAAaaaaAAAAaaaa',
            network='bradbury',
            operator_address='0x1111111111111111111111111111111111111111',
            status='active', moniker='alice',
        )
        self.bob = ValidatorWallet.objects.create(
            address='0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
            network='bradbury',
            operator_address='0x2222222222222222222222222222222222222222',
            status='active', moniker='bob',
        )
        self.carol = ValidatorWallet.objects.create(
            address='0xcccccccccccccccccccccccccccccccccccccccc',
            network='bradbury',
            operator_address='0x3333333333333333333333333333333333333333',
            status='active', moniker='carol',
        )

    def _sync(self, fixture):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = fixture
        with patch('validators.grafana_service.requests.post', return_value=mock_response):
            with self.settings(
                GRAFANA_BASE_URL='https://grafana.test',
                GRAFANA_API_TOKEN='test-token',
                GRAFANA_NETWORK_LABELS={'bradbury': 'bradbury-phase1', 'asimov': 'asimov-phase5'},
                GRAFANA_PROM_DS_UID='grafanacloud-prom',
                GRAFANA_LOKI_DS_UID='grafanacloud-logs',
            ):
                return GrafanaValidatorStatusService.sync_network('bradbury')

    def test_first_sync_writes_observations_and_rollup(self):
        self._sync(GRAFANA_RESPONSE_FIXTURE)

        # One observation per active wallet.
        self.assertEqual(ValidatorWalletObservation.objects.count(), 3)

        alice_snap = ValidatorWalletStatusSnapshot.objects.get(wallet=self.alice)
        self.assertEqual(alice_snap.metrics_status, 'on')
        self.assertEqual(alice_snap.logs_status, 'on')
        self.assertEqual(alice_snap.metrics_samples, 1)
        self.assertEqual(alice_snap.logs_samples, 1)
        self.assertEqual(alice_snap.node_version, '0.5.12')  # normalised at ingest

        # Bob reports metrics but no logs.
        bob_snap = ValidatorWalletStatusSnapshot.objects.get(wallet=self.bob)
        self.assertEqual(bob_snap.metrics_status, 'on')
        self.assertEqual(bob_snap.logs_status, 'shame')
        self.assertEqual(bob_snap.logs_samples, 0)

    def test_shame_latches_for_the_whole_day(self):
        # Run 1: alice healthy. Run 2 (same day): alice reports nothing.
        self._sync(GRAFANA_RESPONSE_FIXTURE)
        self._sync(EMPTY_GRAFANA_RESPONSE)

        self.assertEqual(ValidatorWalletObservation.objects.filter(wallet=self.alice).count(), 2)

        alice_snap = ValidatorWalletStatusSnapshot.objects.get(wallet=self.alice)
        # Once shamed at any sample, the whole day is shamed and does not revert.
        self.assertEqual(alice_snap.metrics_status, 'shame')
        self.assertEqual(alice_snap.logs_status, 'shame')
        # The healthy sample is still counted.
        self.assertEqual(alice_snap.metrics_samples, 1)
        self.assertEqual(alice_snap.logs_samples, 1)
        # Latest observed version is retained even after the node stops reporting.
        self.assertEqual(alice_snap.node_version, '0.5.12')

    def _obs(self, wallet, *, metrics='on', logs='on', version='on'):
        return {
            'wallet': wallet, 'onchain_status': 'active',
            'metrics_status': metrics, 'logs_status': logs, 'version_status': version,
            'node_version': '0.6.0',
            'metrics_ok': metrics == 'on', 'logs_ok': logs == 'on',
        }

    def test_version_latches_optimistically_within_a_day(self):
        now = timezone.now()
        # Same day: version shame first (running old build), then on (upgraded).
        GrafanaValidatorStatusService._record_history(
            [self._obs(self.alice, version='shame')], now)
        GrafanaValidatorStatusService._record_history(
            [self._obs(self.alice, version='on')], now)

        snap = ValidatorWalletStatusSnapshot.objects.get(wallet=self.alice)
        # One up-to-date sample makes the whole day OK for version.
        self.assertEqual(snap.version_status, 'on')

    def test_metrics_latches_pessimistically_within_a_day(self):
        now = timezone.now()
        # Same day: metrics on first, then shame — one shame shames the day.
        GrafanaValidatorStatusService._record_history(
            [self._obs(self.alice, metrics='on')], now)
        GrafanaValidatorStatusService._record_history(
            [self._obs(self.alice, metrics='shame')], now)

        snap = ValidatorWalletStatusSnapshot.objects.get(wallet=self.alice)
        self.assertEqual(snap.metrics_status, 'shame')

    def test_rebuild_days_cutoff_covers_full_days(self):
        """--days N must snap to a day boundary: a mid-day cutoff would rebuild the
        oldest day from partial observations and un-latch a real shame."""
        from datetime import datetime as dt, time as t
        from django.core.management import call_command

        yesterday = timezone.localdate() - timedelta(days=1)
        tz = timezone.get_current_timezone()
        early = timezone.make_aware(dt.combine(yesterday, t(3, 0)), tz)
        late = timezone.make_aware(dt.combine(yesterday, t(12, 0)), tz)

        # 03:00 shame + 12:00 clean → the day's rollup must latch to shame.
        for observed_at, metrics in ((early, 'shame'), (late, 'on')):
            ValidatorWalletObservation.objects.create(
                wallet=self.alice, observed_at=observed_at,
                onchain_status='active', metrics_status=metrics, logs_status='on',
            )

        call_command('rebuild_daily_snapshots', '--days', '1')

        snap = ValidatorWalletStatusSnapshot.objects.get(wallet=self.alice, date=yesterday)
        # A now()-based cutoff (mid-day) would have dropped the 03:00 observation
        # and rebuilt the day as clean.
        self.assertEqual(snap.metrics_status, 'shame')
        self.assertEqual(snap.logs_samples, 2)


class WallOfShameEndpointTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        # Two active validators on each network with different statuses.
        self.shame = ValidatorWallet.objects.create(
            address='0xshame00000000000000000000000000000000shame'[:42],
            network='bradbury',
            operator_address='0xop1111111111111111111111111111111111op1111'[:42],
            status='active',
            moniker='zelda-shame',
            metrics_status='shame',
            logs_status='shame',
        )
        self.ok = ValidatorWallet.objects.create(
            address='0xokokok00000000000000000000000000000okokok'[:42],
            network='bradbury',
            operator_address='0xop2222222222222222222222222222222222op2222'[:42],
            status='active',
            moniker='alpha-ok',
            metrics_status='on',
            logs_status='on',
        )
        self.asimov_validator = ValidatorWallet.objects.create(
            address='0xasimov0000000000000000000000000000000asimov'[:42],
            network='asimov',
            operator_address='0xop3333333333333333333333333333333333op3333'[:42],
            status='active',
            moniker='mid-asimov',
            metrics_status='on',
            logs_status='shame',
        )
        # Inactive wallet — must not appear.
        self.banned = ValidatorWallet.objects.create(
            address='0xbanned0000000000000000000000000000000banned'[:42],
            network='bradbury',
            operator_address='0xop4444444444444444444444444444444444op4444'[:42],
            status='banned',
            moniker='hidden',
            metrics_status='shame',
            logs_status='shame',
        )

    def tearDown(self):
        cache.clear()

    def test_returns_only_active_wallets(self):
        response = self.client.get('/api/v1/validators/wallets/wall-of-shame/')
        self.assertEqual(response.status_code, 200)
        monikers = [w['moniker'] for w in response.data['wallets']]
        self.assertNotIn('hidden', monikers)
        self.assertEqual(response.data['stats']['total'], 3)

    def test_shame_rows_sorted_first(self):
        response = self.client.get('/api/v1/validators/wallets/wall-of-shame/')
        wallets = response.data['wallets']
        # All SHAME rows must come before any OK row.
        def is_shame(w):
            return w['metrics_status'] == 'shame' or w['logs_status'] == 'shame'

        # Find the index of the first OK row, then assert no SHAME rows appear after it.
        seen_ok = False
        for w in wallets:
            if seen_ok:
                self.assertFalse(
                    is_shame(w),
                    f"SHAME row {w['moniker']} appeared after OK rows",
                )
            elif not is_shame(w):
                seen_ok = True

        # And alpha-ok (the only OK row) must NOT be first.
        self.assertNotEqual(wallets[0]['moniker'], 'alpha-ok')

    def test_filter_by_network(self):
        response = self.client.get('/api/v1/validators/wallets/wall-of-shame/?network=asimov')
        self.assertEqual(response.status_code, 200)
        wallets = response.data['wallets']
        self.assertEqual(len(wallets), 1)
        self.assertEqual(wallets[0]['network'], 'asimov')
        self.assertEqual(response.data['network'], 'asimov')

    def test_unknown_network_returns_400(self):
        response = self.client.get('/api/v1/validators/wallets/wall-of-shame/?network=ethereum')
        self.assertEqual(response.status_code, 400)

    def test_response_includes_observability_fields(self):
        response = self.client.get('/api/v1/validators/wallets/wall-of-shame/')
        first = response.data['wallets'][0]
        for field in ('metrics_status', 'logs_status', 'last_grafana_check_at',
                      'address', 'network', 'operator_address', 'moniker',
                      'operator_user', 'explorer_url'):
            self.assertIn(field, first)

    def test_stats_counts(self):
        response = self.client.get('/api/v1/validators/wallets/wall-of-shame/')
        stats = response.data['stats']
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['on'], 1)        # alpha-ok only
        self.assertEqual(stats['shame'], 2)     # zelda-shame + mid-asimov

    def test_grouped_validator_reasons_across_networks(self):
        user = User.objects.create_user(
            email='grouped@example.com',
            password='password',
            name='Grouped Operator',
            address='0xgroupedoperator0000000000000000000000000'[:42],
        )
        validator = Validator.objects.create(
            user=user,
            node_version_asimov='2.0.0',
            node_version_bradbury='2.0.0',
        )
        ValidatorWallet.objects.create(
            address='0xgroupedasimov0000000000000000000000000000'[:42],
            network='asimov',
            operator=validator,
            operator_address=user.address,
            status='active',
            moniker='grouped-asimov',
            metrics_status='shame',
            logs_status='on',
        )
        ValidatorWallet.objects.create(
            address='0xgroupedbradbury00000000000000000000000000'[:42],
            network='bradbury',
            operator=validator,
            operator_address=user.address,
            status='active',
            moniker='grouped-bradbury',
            metrics_status='on',
            logs_status='shame',
        )

        response = self.client.get('/api/v1/validators/wallets/wall-of-shame/')
        grouped = next(
            item for item in response.data['validators']
            if item['operator_user'] and item['operator_user']['id'] == user.id
        )

        self.assertEqual(grouped['status'], 'shame')
        self.assertEqual(len(grouped['networks']), 2)
        self.assertEqual(
            {(reason['network'], reason['type']) for reason in grouped['shame_reasons']},
            {('asimov', 'metrics'), ('bradbury', 'logs')},
        )

    def test_hidden_operator_identity_is_not_exposed(self):
        """A hidden (visible=False) operator must not have their profile
        identity surfaced on the public Wall of Shame, but the validator wallet
        itself should still appear (falling back to the on-chain address)."""
        user = User.objects.create_user(
            email='hidden-operator@example.com',
            password='password',
            name='Hidden Operator',
            address='0xhiddenoperator00000000000000000000000000'[:42],
            visible=False,
        )
        validator = Validator.objects.create(user=user)
        wallet = ValidatorWallet.objects.create(
            address='0xhiddenwallet0000000000000000000000000000'[:42],
            network='asimov',
            operator=validator,
            operator_address=user.address,
            status='active',
            moniker='hidden-asimov',
            metrics_status='shame',
            logs_status='on',
        )

        response = self.client.get('/api/v1/validators/wallets/wall-of-shame/')

        # operator_user must be withheld in both payloads for the hidden user.
        for entry in response.data['wallets']:
            if entry['address'] == wallet.address:
                self.assertIsNone(entry['operator_user'])

        group = next(
            item for item in response.data['validators']
            if item['operator_address'] == user.address
        )
        self.assertIsNone(group['operator_user'])
        # The validator still appears (so a misbehaving node isn't hidden),
        # identified only by its on-chain operator address.
        self.assertEqual(group['status'], 'shame')
        self.assertEqual(group['operator_address'], user.address)

    def test_outdated_version_is_warning_during_grace_period(self):
        TargetNodeVersion.objects.create(
            version='2.0.0',
            network='asimov',
            target_date=timezone.now() - timedelta(days=2),
            is_active=True,
        )
        user = User.objects.create_user(
            email='grace@example.com',
            password='password',
            name='Grace Operator',
            address='0xgraceoperator00000000000000000000000000'[:42],
        )
        validator = Validator.objects.create(user=user, node_version_asimov='1.0.0')
        wallet = ValidatorWallet.objects.create(
            address='0xgracewallet0000000000000000000000000000'[:42],
            network='asimov',
            operator=validator,
            operator_address=user.address,
            status='active',
            moniker='grace-asimov',
            metrics_status='on',
            logs_status='on',
        )

        response = self.client.get('/api/v1/validators/wallets/wall-of-shame/')
        grouped = next(
            item for item in response.data['validators']
            if item['operator_user'] and item['operator_user']['id'] == user.id
        )
        reason = grouped['shame_reasons'][0]

        self.assertEqual(grouped['status'], 'warning')
        self.assertEqual(reason['type'], 'version')
        self.assertEqual(reason['status'], 'warning')
        wallet.refresh_from_db()
        self.assertIsNone(wallet.version_shame_started_at)

    def test_outdated_version_becomes_persisted_shame_after_grace_period(self):
        target = TargetNodeVersion.objects.create(
            version='2.0.0',
            network='asimov',
            target_date=timezone.now() - timedelta(days=5),
            is_active=True,
        )
        user = User.objects.create_user(
            email='outdated@example.com',
            password='password',
            name='Outdated Operator',
            address='0xoutdatedoperator000000000000000000000000'[:42],
        )
        validator = Validator.objects.create(user=user, node_version_asimov='1.0.0')
        wallet = ValidatorWallet.objects.create(
            address='0xoutdatedwallet00000000000000000000000000'[:42],
            network='asimov',
            operator=validator,
            operator_address=user.address,
            status='active',
            moniker='outdated-asimov',
            metrics_status='on',
            logs_status='on',
        )

        response = self.client.get('/api/v1/validators/wallets/wall-of-shame/')
        grouped = next(
            item for item in response.data['validators']
            if item['operator_user'] and item['operator_user']['id'] == user.id
        )
        reason = grouped['shame_reasons'][0]

        self.assertEqual(grouped['status'], 'shame')
        self.assertEqual(reason['type'], 'version')
        self.assertEqual(reason['status'], 'shame')
        self.assertGreaterEqual(reason['days_in_shame'], 1)
        wallet.refresh_from_db()
        self.assertEqual(
            wallet.version_shame_started_at.replace(microsecond=0),
            (target.target_date + timedelta(days=3)).replace(microsecond=0),
        )
