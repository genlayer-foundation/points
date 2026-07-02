"""
Tests for consecutive "not shamed" uptime streaks derived from the daily rollup.
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from validators import streaks as streaks_lib
from validators.models import ValidatorWallet, ValidatorWalletStatusSnapshot


def _snap(wallet, day, *, status='active', metrics='on', logs='on',
          version='on', m_samples=3, l_samples=3):
    return ValidatorWalletStatusSnapshot.objects.create(
        wallet=wallet, date=day, status=status,
        metrics_status=metrics, logs_status=logs, version_status=version,
        metrics_samples=m_samples, logs_samples=l_samples,
    )


class CleanStreakTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.today = timezone.localdate(self.now)
        self.wallet = ValidatorWallet.objects.create(
            address='0xaaaa000000000000000000000000000000000000',
            network='asimov',
            operator_address='0x1111111111111111111111111111111111111111',
            status='active', moniker='alice',
        )

    def _streak(self, wallet_ids=None):
        wallet_ids = wallet_ids or [self.wallet.id]
        index = streaks_lib.load_snapshot_index(wallet_ids, self.now)
        return streaks_lib.clean_streak(wallet_ids, self.now, index)

    def test_counts_consecutive_clean_days_including_today(self):
        for i in range(5):
            _snap(self.wallet, self.today - timedelta(days=i))
        result = self._streak()
        self.assertEqual(result['days'], 5)
        self.assertEqual(result['broken_by'], [])
        self.assertEqual(result['since'], self.today - timedelta(days=4))

    def test_shame_day_breaks_streak_and_reports_dim(self):
        _snap(self.wallet, self.today)                       # clean
        _snap(self.wallet, self.today - timedelta(days=1))   # clean
        _snap(self.wallet, self.today - timedelta(days=2), logs='shame', l_samples=0)  # break
        _snap(self.wallet, self.today - timedelta(days=3))   # (behind the break)
        result = self._streak()
        self.assertEqual(result['days'], 2)
        self.assertIn('logs', result['broken_by'])

    def test_zero_sample_day_is_not_clean(self):
        # A day the node never reported metrics counts as shamed.
        _snap(self.wallet, self.today, metrics='shame', m_samples=0)
        result = self._streak()
        self.assertEqual(result['days'], 0)
        self.assertIn('metrics', result['broken_by'])

    def test_unsynced_today_does_not_break_streak(self):
        # No snapshot for today yet; yesterday+ are clean.
        _snap(self.wallet, self.today - timedelta(days=1))
        _snap(self.wallet, self.today - timedelta(days=2))
        result = self._streak()
        self.assertEqual(result['days'], 2)

    def test_missing_past_day_is_skipped_not_broken(self):
        """A day with no data (sync outage on our side) must not reset the fleet's
        streaks: it is skipped — it neither counts nor breaks."""
        _snap(self.wallet, self.today)
        # gap at today-1 (no snapshot at all)
        _snap(self.wallet, self.today - timedelta(days=2))
        result = self._streak()
        self.assertEqual(result['days'], 2)
        self.assertEqual(result['broken_by'], [])

    def test_non_active_day_breaks_streak_with_status(self):
        """A day spent quarantined breaks the streak even without Grafana data —
        the on-chain sync owns the status column and its verdict is trusted."""
        _snap(self.wallet, self.today)
        _snap(self.wallet, self.today - timedelta(days=1),
              status='quarantined', metrics='unknown', logs='unknown',
              version='unknown', m_samples=0, l_samples=0)
        result = self._streak()
        self.assertEqual(result['days'], 1)
        self.assertEqual(result['broken_by'], ['status'])

    def test_version_shame_breaks_streak(self):
        _snap(self.wallet, self.today, version='shame')
        result = self._streak()
        self.assertEqual(result['days'], 0)
        self.assertIn('version', result['broken_by'])

    def test_version_only_observation_counts_as_observed(self):
        """A rollup carrying only a version verdict (metrics/logs unknown, zero
        samples) is still an observed day: it must break the streak, not be
        skipped as not-yet-synced."""
        _snap(self.wallet, self.today, metrics='unknown', logs='unknown',
              version='shame', m_samples=0, l_samples=0)
        result = self._streak()
        self.assertEqual(result['days'], 0)
        self.assertIn('version', result['broken_by'])


class OperatorRollupTests(TestCase):
    """Any-node-clean: an operator is clean on a day if >=1 of their nodes was."""

    def setUp(self):
        self.now = timezone.now()
        self.today = timezone.localdate(self.now)
        self.node_a = ValidatorWallet.objects.create(
            address='0xaaaa000000000000000000000000000000000000',
            network='asimov',
            operator_address='0x1111111111111111111111111111111111111111',
            status='active', moniker='a',
        )
        self.node_b = ValidatorWallet.objects.create(
            address='0xbbbb000000000000000000000000000000000000',
            network='asimov',
            operator_address='0x1111111111111111111111111111111111111111',
            status='active', moniker='b',
        )

    def test_any_node_clean_keeps_operator_streak_alive(self):
        # Each node is shamed on alternating days, but at least one is clean every day.
        for i in range(4):
            a_shamed = (i % 2 == 0)
            _snap(self.node_a, self.today - timedelta(days=i),
                  logs='shame' if a_shamed else 'on',
                  l_samples=0 if a_shamed else 3)
            _snap(self.node_b, self.today - timedelta(days=i),
                  logs='on' if a_shamed else 'shame',
                  l_samples=3 if a_shamed else 0)

        ids = [self.node_a.id, self.node_b.id]
        index = streaks_lib.load_snapshot_index(ids, self.now)
        operator = streaks_lib.clean_streak(ids, self.now, index)
        self.assertEqual(operator['days'], 4)

        # But each individual node's streak is broken early.
        node_a = streaks_lib.clean_streak([self.node_a.id], self.now, index)
        self.assertLess(node_a['days'], 4)

    def test_operator_shamed_only_when_all_nodes_shamed(self):
        # Day 0: both clean. Day 1: both shamed → operator break here.
        _snap(self.node_a, self.today)
        _snap(self.node_b, self.today)
        _snap(self.node_a, self.today - timedelta(days=1), logs='shame', l_samples=0)
        _snap(self.node_b, self.today - timedelta(days=1), logs='shame', l_samples=0)
        ids = [self.node_a.id, self.node_b.id]
        index = streaks_lib.load_snapshot_index(ids, self.now)
        operator = streaks_lib.clean_streak(ids, self.now, index)
        self.assertEqual(operator['days'], 1)
        self.assertIn('logs', operator['broken_by'])
