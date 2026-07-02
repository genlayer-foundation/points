"""
Tests for Grafana-driven node version detection: auto-target creation,
node_version write-back, and direct (auto-approved) node-upgrade awards.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from contributions.models import Category, Contribution, ContributionType
from contributions.node_upgrade.models import TargetNodeVersion
from leaderboard.models import GlobalLeaderboardMultiplier
from validators.grafana_service import GrafanaValidatorStatusService
from validators.models import Validator, ValidatorWallet

User = get_user_model()


class NodeVersionSyncTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.category, _ = Category.objects.get_or_create(name='Validator', slug='validator')
        self.ctype, _ = ContributionType.objects.get_or_create(
            slug='node-upgrade',
            defaults={'name': 'Node Upgrade', 'category': self.category,
                      'min_points': 1, 'max_points': 100, 'is_submittable': True},
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.ctype,
            multiplier_value=1.0,
            valid_from=self.now - timedelta(days=30),
        )

    def _operator(self, email, address, visible=True):
        user = User.objects.create(email=email, address=address, visible=visible)
        return Validator.objects.create(user=user)

    def _wallet(self, address, operator, network='asimov', status='active'):
        return ValidatorWallet.objects.create(
            address=address, network=network, operator=operator,
            operator_address=operator.user.address, status=status,
        )

    def _sync(self, network, version_by_wallet):
        # _sync_node_versions takes {address_lower: version}
        GrafanaValidatorStatusService._sync_node_versions(
            network,
            {w.address.lower(): v for w, v in version_by_wallet.items()},
            self.now,
        )

    def test_corroborated_stable_release_creates_active_target(self):
        """A stable release reported by two distinct operators becomes the target."""
        op1 = self._operator('a@x.com', '0x' + 'a' * 40)
        w1 = self._wallet('0x' + '1' * 40, op1)
        op2 = self._operator('a2@x.com', '0x' + 'e' * 39 + '1')
        w2 = self._wallet('0x' + 'f' * 39 + '1', op2)
        self._sync('asimov', {w1: 'v0.6.0', w2: 'v0.6.0'})

        target = TargetNodeVersion.get_active(network='asimov')
        self.assertIsNotNone(target)
        self.assertEqual(target.version, '0.6.0')  # 'v' stripped

    def test_single_operator_cannot_create_target(self):
        """The version label is self-reported by the node being rewarded: one
        operator alone must not be able to pin a fleet-wide target (and shame
        everyone else / bank the first-adopter bonus)."""
        op = self._operator('solo@x.com', '0x' + 'a' * 39 + '2')
        w1 = self._wallet('0x' + '1' * 39 + '2', op)
        w2 = self._wallet('0x' + '1' * 39 + '3', op)  # same operator, two nodes
        self._sync('asimov', {w1: 'v9.9.9', w2: 'v9.9.9'})

        self.assertIsNone(TargetNodeVersion.get_active(network='asimov'))
        # ...but their own running version is still recorded.
        op.refresh_from_db()
        self.assertEqual(op.node_version_asimov, '9.9.9')

    @override_settings(NODE_VERSION_MIN_OPERATORS_FOR_AUTO_TARGET=1)
    def test_auto_target_operator_threshold_is_configurable(self):
        """The anti-collusion threshold is a setting, read at evaluation time."""
        op = self._operator('cfg@x.com', '0x' + 'f' * 39 + '2')
        w = self._wallet('0x' + 'f' * 39 + '3', op)
        self._sync('asimov', {w: 'v0.6.0'})

        target = TargetNodeVersion.get_active(network='asimov')
        self.assertIsNotNone(target)
        self.assertEqual(target.version, '0.6.0')

    def test_unknown_addresses_cannot_create_target(self):
        """Prometheus series for addresses we don't know (test rigs, spoofed or
        stale nodes) must not move targets or earn anything."""
        GrafanaValidatorStatusService._sync_node_versions(
            'asimov',
            {'0x' + 'd' * 39 + '1': '9.9.9', '0x' + 'd' * 39 + '2': '9.9.9'},
            self.now,
        )
        self.assertIsNone(TargetNodeVersion.get_active(network='asimov'))

    def test_prerelease_does_not_create_target(self):
        op = self._operator('b@x.com', '0x' + 'b' * 40)
        w = self._wallet('0x' + '2' * 40, op)
        self._sync('asimov', {w: 'v0.6.0-rc1'})

        self.assertIsNone(TargetNodeVersion.get_active(network='asimov'))
        # ...but the running (pre-release) version is still recorded on the profile.
        op.refresh_from_db()
        self.assertEqual(op.node_version_asimov, '0.6.0-rc1')

    def test_build_metadata_version_is_ignored_for_target(self):
        op = self._operator('c@x.com', '0x' + 'c' * 40)
        w = self._wallet('0x' + '3' * 40, op)
        self._sync('asimov', {w: 'v0.6.0+dev'})
        self.assertIsNone(TargetNodeVersion.get_active(network='asimov'))

    def test_node_version_is_max_across_operator_nodes(self):
        op = self._operator('d@x.com', '0x' + 'd' * 40)
        w1 = self._wallet('0x' + '4' * 40, op)
        w2 = self._wallet('0x' + '5' * 40, op)
        self._sync('asimov', {w1: 'v0.5.10', w2: 'v0.6.0'})

        op.refresh_from_db()
        self.assertEqual(op.node_version_asimov, '0.6.0')

    def test_reaching_target_awards_direct_contribution_once(self):
        TargetNodeVersion.objects.create(
            version='0.6.0', network='asimov', target_date=self.now, is_active=True,
        )
        op = self._operator('e@x.com', '0x' + 'e' * 40)
        w = self._wallet('0x' + '6' * 40, op)
        self._sync('asimov', {w: 'v0.6.0'})

        awards = Contribution.objects.filter(
            user=op.user, contribution_type=self.ctype,
            notes__contains='version 0.6.0 [asimov]',
        )
        self.assertEqual(awards.count(), 1)
        # target_date == now → same-day bonus of 4.
        self.assertEqual(awards.first().points, 4)

        # Running the sync again must not double-award.
        self._sync('asimov', {w: 'v0.6.0'})
        self.assertEqual(awards.count(), 1)

    def test_award_skipped_when_no_multiplier(self):
        """Removing the multiplier is the stewards' kill switch for a points
        program; the auto-award must respect it instead of awarding at 1.0."""
        GlobalLeaderboardMultiplier.objects.all().delete()
        TargetNodeVersion.objects.create(
            version='0.6.0', network='asimov', target_date=self.now, is_active=True,
        )
        op = self._operator('nm@x.com', '0x' + 'b' * 39 + '2')
        w = self._wallet('0x' + 'b' * 39 + '3', op)
        self._sync('asimov', {w: 'v0.6.0'})

        self.assertFalse(
            Contribution.objects.filter(user=op.user, contribution_type=self.ctype).exists()
        )
        # The version itself is still recorded.
        op.refresh_from_db()
        self.assertEqual(op.node_version_asimov, '0.6.0')

    def test_banned_wallet_gets_no_version_or_award(self):
        TargetNodeVersion.objects.create(
            version='0.6.0', network='asimov', target_date=self.now, is_active=True,
        )
        op = self._operator('ban@x.com', '0x' + 'c' * 39 + '2')
        w = self._wallet('0x' + 'c' * 39 + '3', op, status='banned')
        self._sync('asimov', {w: 'v0.6.0'})

        op.refresh_from_db()
        self.assertIsNone(op.node_version_asimov)
        self.assertFalse(
            Contribution.objects.filter(user=op.user, contribution_type=self.ctype).exists()
        )

    def test_missing_scrape_does_not_downgrade_version(self):
        """When one of an operator's wallets skips a scrape cycle, the recorded
        version must not regress to the remaining (lower) wallet's version."""
        op = self._operator('mono@x.com', '0x' + 'd' * 39 + '3')
        op.node_version_asimov = '0.6.0'
        op.save()
        w_low = self._wallet('0x' + 'd' * 39 + '4', op)
        # Only the 0.5.0 wallet reports this cycle.
        self._sync('asimov', {w_low: 'v0.5.0'})

        op.refresh_from_db()
        self.assertEqual(op.node_version_asimov, '0.6.0')

    def test_auto_created_target_broadcasts_notification(self):
        from notifications.models import Notification

        op1 = self._operator('n1@x.com', '0x' + 'e' * 39 + '2')
        w1 = self._wallet('0x' + 'e' * 39 + '3', op1)
        op2 = self._operator('n2@x.com', '0x' + 'e' * 39 + '4')
        w2 = self._wallet('0x' + 'e' * 39 + '5', op2)
        self._sync('asimov', {w1: 'v0.6.0', w2: 'v0.6.0'})

        self.assertTrue(
            Notification.objects.filter(title__contains='0.6.0').exists()
        )

    def test_invisible_operator_gets_version_but_no_award(self):
        op = self._operator('f@x.com', '0x' + 'f' * 40, visible=False)
        w = self._wallet('0x' + '7' * 40, op)
        self._sync('asimov', {w: 'v0.6.0'})

        op.refresh_from_db()
        self.assertEqual(op.node_version_asimov, '0.6.0')
        self.assertFalse(
            Contribution.objects.filter(user=op.user, contribution_type=self.ctype).exists()
        )

    def test_higher_stable_version_supersedes_active_target(self):
        TargetNodeVersion.objects.create(
            version='0.5.0', network='asimov',
            target_date=self.now - timedelta(days=10), is_active=True,
        )
        op1 = self._operator('g@x.com', '0x' + '9' * 40)
        w1 = self._wallet('0x' + '8' * 40, op1)
        op2 = self._operator('g2@x.com', '0x' + '9' * 39 + '1')
        w2 = self._wallet('0x' + '8' * 39 + '1', op2)
        self._sync('asimov', {w1: 'v0.6.0', w2: 'v0.6.0'})

        active = TargetNodeVersion.get_active(network='asimov')
        self.assertEqual(active.version, '0.6.0')
        self.assertEqual(
            TargetNodeVersion.objects.filter(network='asimov', is_active=True).count(), 1
        )

    def test_no_new_target_when_fleet_matches_active(self):
        TargetNodeVersion.objects.create(
            version='0.6.0', network='asimov',
            target_date=self.now - timedelta(days=1), is_active=True,
        )
        op = self._operator('h@x.com', '0x' + '7' * 40)
        w = self._wallet('0x' + 'aa'[0] * 40, op)
        self._sync('asimov', {w: 'v0.6.0'})
        self.assertEqual(TargetNodeVersion.objects.filter(network='asimov').count(), 1)

    def test_quarantined_wallet_still_gets_version_and_award(self):
        """Version detection covers every reporting node, not just active wallets —
        a quarantined validator that upgrades must still record it and be awarded."""
        TargetNodeVersion.objects.create(
            version='0.6.0', network='asimov', target_date=self.now, is_active=True,
        )
        op = self._operator('q@x.com', '0x' + '1' * 39 + '2')
        w = self._wallet('0x' + '2' * 39 + '3', op, status='quarantined')
        self._sync('asimov', {w: 'v0.6.0'})

        op.refresh_from_db()
        self.assertEqual(op.node_version_asimov, '0.6.0')
        self.assertTrue(
            Contribution.objects.filter(
                user=op.user, contribution_type=self.ctype,
                notes__contains='version 0.6.0 [asimov]',
            ).exists()
        )

    def test_pep440_invalid_semver_does_not_abort_other_operators(self):
        """'0.6.0-genlayer.1' is valid semver but packaging.parse raises
        InvalidVersion on it; one such node must not abort the whole network."""
        TargetNodeVersion.objects.create(
            version='0.6.0', network='asimov', target_date=self.now, is_active=True,
        )
        bad_op = self._operator('bad@x.com', '0x' + '3' * 39 + '4')
        bad_w = self._wallet('0x' + '4' * 39 + '5', bad_op)
        good_op = self._operator('good@x.com', '0x' + '5' * 39 + '6')
        good_w = self._wallet('0x' + '6' * 39 + '7', good_op)

        self._sync('asimov', {bad_w: 'v0.6.0-genlayer.1', good_w: 'v0.6.0'})

        # The good operator's version + award went through untouched.
        good_op.refresh_from_db()
        self.assertEqual(good_op.node_version_asimov, '0.6.0')
        self.assertTrue(
            Contribution.objects.filter(user=good_op.user, contribution_type=self.ctype).exists()
        )
        # The unparseable version is excluded (can't be compared), not crashed on.
        bad_op.refresh_from_db()
        self.assertIsNone(bad_op.node_version_asimov)

    def test_one_failing_operator_does_not_block_the_rest(self):
        """A per-operator failure (e.g. Contribution validation) must not stop
        version updates and awards for the other operators in the same run."""
        from unittest.mock import patch

        op1 = self._operator('p1@x.com', '0x' + '7' * 39 + '8')
        w1 = self._wallet('0x' + '8' * 39 + '9', op1)
        op2 = self._operator('p2@x.com', '0x' + '9' * 39 + 'a')
        w2 = self._wallet('0x' + 'a' * 39 + 'b', op2)

        real_award = GrafanaValidatorStatusService._award_node_upgrade
        calls = []

        def flaky_award(operator, network, target, now):
            calls.append(operator.pk)
            if len(calls) == 1:
                raise RuntimeError('boom')
            return real_award(operator, network, target, now)

        with patch.object(
            GrafanaValidatorStatusService, '_award_node_upgrade',
            side_effect=flaky_award,
        ):
            self._sync('asimov', {w1: 'v0.6.0', w2: 'v0.6.0'})

        # Both operators were attempted; exactly one award landed despite the failure.
        self.assertEqual(len(calls), 2)
        self.assertEqual(
            Contribution.objects.filter(contribution_type=self.ctype).count(), 1
        )
        # Both got their version recorded (the update happens before the award).
        op1.refresh_from_db()
        op2.refresh_from_db()
        self.assertEqual(op1.node_version_asimov, '0.6.0')
        self.assertEqual(op2.node_version_asimov, '0.6.0')
