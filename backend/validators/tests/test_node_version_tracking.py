"""
Test node version tracking and points calculation.
"""
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from validators.models import Validator
from validators.node_version import calculate_early_upgrade_bonus
from contributions.models import ContributionType, SubmittedContribution, Category
from contributions.node_upgrade.models import TargetNodeVersion
from leaderboard.models import GlobalLeaderboardMultiplier

User = get_user_model()


class NodeVersionTrackingTestCase(TestCase):
    def setUp(self):
        """Set up test data."""
        # Create a user
        self.user = User.objects.create(
            email='validator@test.com',
            address='0x1234567890123456789012345678901234567890',
            visible=True
        )

        # Create validator category
        self.category, _ = Category.objects.get_or_create(
            name='Validator',
            slug='validator'
        )

        # Get or create node-upgrade contribution type
        self.contribution_type, _ = ContributionType.objects.get_or_create(
            slug='node-upgrade',
            defaults={
                'name': 'Node Upgrade',
                'category': self.category,
                'min_points': 10,
                'max_points': 100,
                'is_submittable': True
            }
        )

        # Create multiplier for the contribution type
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.contribution_type,
            multiplier_value=1.0,
            valid_from=timezone.now() - timedelta(days=30)
        )

        # Create a validator
        self.validator = Validator.objects.create(
            user=self.user,
            node_version_asimov='1.0.0'
        )

        # Create a target version for asimov
        self.target = TargetNodeVersion.objects.create(
            version='2.0.0',
            network='asimov',
            target_date=timezone.now() + timedelta(days=7),
            is_active=True
        )


    def test_early_upgrade_bonus(self):
        """Test the early upgrade bonus calculation."""
        now = timezone.now()

        # Same day upgrade
        self.assertEqual(calculate_early_upgrade_bonus(now, now), 4)

        # Day 1
        self.assertEqual(calculate_early_upgrade_bonus(now, now + timedelta(days=1)), 3)

        # Day 2
        self.assertEqual(calculate_early_upgrade_bonus(now, now + timedelta(days=2)), 2)

        # Day 3+
        self.assertEqual(calculate_early_upgrade_bonus(now, now + timedelta(days=3)), 1)
        self.assertEqual(calculate_early_upgrade_bonus(now, now + timedelta(days=10)), 1)


    def test_submission_creation_with_calculated_points(self):
        """Test that updating node version creates a submission with calculated points."""
        # Update validator to target version
        self.validator.node_version_asimov = '2.0.0'
        self.validator.save()

        # Check that a submission was created
        submissions = SubmittedContribution.objects.filter(user=self.user)
        self.assertEqual(submissions.count(), 1)

        submission = submissions.first()
        self.assertEqual(submission.contribution_type, self.contribution_type)
        self.assertEqual(submission.state, 'pending')

        # Check suggested points (should be 4 for same-day upgrade)
        self.assertEqual(submission.proposed_points, 4)

        # Check that no evidence was created for automatic submission
        self.assertEqual(submission.evidence_items.count(), 0)

    def test_submission_with_delayed_upgrade(self):
        """Test points calculation with delayed upgrade."""
        # Update target to have been available 3 days ago
        self.target.target_date = timezone.now() - timedelta(days=3)
        self.target.save()

        # Update to target version
        self.validator.node_version_asimov = '2.0.0'
        self.validator.save()

        # Check submission
        submission = SubmittedContribution.objects.filter(user=self.user).first()
        self.assertIsNotNone(submission)

        # Should have 1 point (minimum for 3+ days delay)
        self.assertEqual(submission.proposed_points, 1)

    def test_no_duplicate_submissions(self):
        """Test that duplicate submissions are not created for the same target."""
        # First upgrade
        self.validator.node_version_asimov = '2.0.0'
        self.validator.save()

        # Try to create another submission for the same target
        self.validator.node_version_asimov = '2.0.1'  # Minor version change
        self.validator.save()

        # Should still only have one submission
        submissions = SubmittedContribution.objects.filter(user=self.user)
        self.assertEqual(submissions.count(), 1)

    def test_invisible_user_no_submission(self):
        """Test that invisible users don't get submissions."""
        # Make user invisible
        self.user.visible = False
        self.user.save()

        # Update validator version
        self.validator.node_version_asimov = '2.0.0'
        self.validator.save()

        # Should not create submission
        submissions = SubmittedContribution.objects.filter(user=self.user)
        self.assertEqual(submissions.count(), 0)

    def test_per_network_targets(self):
        """Test that targets are per-network and deactivation is scoped."""
        # Create a bradbury target
        bradbury_target = TargetNodeVersion.objects.create(
            version='3.0.0',
            network='bradbury',
            target_date=timezone.now() + timedelta(days=7),
            is_active=True
        )

        # Asimov target should still be active
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_active)

        # Both should be retrievable by network
        asimov_active = TargetNodeVersion.get_active(network='asimov')
        bradbury_active = TargetNodeVersion.get_active(network='bradbury')
        self.assertEqual(asimov_active.version, '2.0.0')
        self.assertEqual(bradbury_active.version, '3.0.0')

    def test_bradbury_version_creates_submission(self):
        """Test that updating bradbury version creates a separate submission."""
        # Create bradbury target
        bradbury_target = TargetNodeVersion.objects.create(
            version='3.0.0',
            network='bradbury',
            target_date=timezone.now() + timedelta(days=7),
            is_active=True
        )

        # Update both versions
        self.validator.node_version_asimov = '2.0.0'
        self.validator.node_version_bradbury = '3.0.0'
        self.validator.save()

        # Should have two submissions (one per network)
        submissions = SubmittedContribution.objects.filter(user=self.user)
        self.assertEqual(submissions.count(), 2)

        # Check dedup keys in notes
        notes = list(submissions.values_list('notes', flat=True))
        self.assertTrue(any('[asimov]' in n for n in notes))
        self.assertTrue(any('[bradbury]' in n for n in notes))

    def test_deactivate_only_same_network(self):
        """Test that activating a new target only deactivates same network."""
        # Create a bradbury target
        bradbury_target = TargetNodeVersion.objects.create(
            version='1.0.0',
            network='bradbury',
            target_date=timezone.now(),
            is_active=True
        )

        # Create a new asimov target
        new_asimov = TargetNodeVersion.objects.create(
            version='3.0.0',
            network='asimov',
            target_date=timezone.now(),
            is_active=True
        )

        # Old asimov should be deactivated
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)

        # Bradbury should still be active
        bradbury_target.refresh_from_db()
        self.assertTrue(bradbury_target.is_active)

    def test_compare_versions_static(self):
        """Test the static _compare_versions helper."""
        from validators.node_version import NodeVersionMixin
        self.assertTrue(NodeVersionMixin._compare_versions('2.0.0', '1.0.0'))
        self.assertTrue(NodeVersionMixin._compare_versions('2.0.0', '2.0.0'))
        self.assertFalse(NodeVersionMixin._compare_versions('1.0.0', '2.0.0'))
        self.assertFalse(NodeVersionMixin._compare_versions(None, '2.0.0'))
        self.assertFalse(NodeVersionMixin._compare_versions('2.0.0', None))
