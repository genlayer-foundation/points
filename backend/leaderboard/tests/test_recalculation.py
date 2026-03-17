"""
Tests for leaderboard recalculation functionality.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.management import call_command
from decimal import Decimal
from io import StringIO

from leaderboard.models import (
    LeaderboardEntry, 
    GlobalLeaderboardMultiplier,
    recalculate_all_leaderboards,
    LEADERBOARD_CONFIG
)
from contributions.models import Contribution, ContributionType, Category

User = get_user_model()


class LeaderboardRecalculationTest(TestCase):
    """Test the leaderboard recalculation functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.validator_category, _ = Category.objects.get_or_create(
            slug='validator',
            defaults={'name': 'Validator', 'description': 'Validator contributions'}
        )
        self.builder_category, _ = Category.objects.get_or_create(
            slug='builder',
            defaults={'name': 'Builder', 'description': 'Builder contributions'}
        )

        # Get or create contribution types. Always update min/max_points so
        # validation does not reject contributions created with small values in tests.
        self.waitlist_type, _ = ContributionType.objects.get_or_create(
            slug='validator-waitlist',
            defaults={'name': 'Validator Waitlist', 'description': 'Join the validator waitlist',
                      'category': self.validator_category, 'min_points': 1, 'max_points': 100}
        )
        self.waitlist_type.min_points = 1
        self.waitlist_type.max_points = 100
        self.waitlist_type.save(update_fields=['min_points', 'max_points'])

        self.validator_type, _ = ContributionType.objects.get_or_create(
            slug='validator',
            defaults={'name': 'Validator', 'description': 'Become a validator',
                      'category': self.validator_category, 'min_points': 1, 'max_points': 100}
        )
        self.validator_type.min_points = 1
        self.validator_type.max_points = 100
        self.validator_type.save(update_fields=['min_points', 'max_points'])

        self.node_running_type, _ = ContributionType.objects.get_or_create(
            slug='node-running',
            defaults={'name': 'Node Running', 'description': 'Running a validator node',
                      'category': self.validator_category, 'min_points': 1, 'max_points': 100}
        )
        self.node_running_type.min_points = 1
        self.node_running_type.max_points = 100
        self.node_running_type.save(update_fields=['min_points', 'max_points'])

        self.builder_type, _ = ContributionType.objects.get_or_create(
            slug='code-contribution',
            defaults={'name': 'Code Contribution', 'description': 'Contributing code',
                      'category': self.builder_category, 'min_points': 1, 'max_points': 100}
        )
        self.builder_type.min_points = 1
        self.builder_type.max_points = 100
        self.builder_type.save(update_fields=['min_points', 'max_points'])

        # builder-welcome and builder types are required by ensure_builder_status()
        # to auto-grant Builder profiles during recalculate_all_leaderboards().
        self.builder_welcome_type, _ = ContributionType.objects.get_or_create(
            slug='builder-welcome',
            defaults={'name': 'Builder Welcome', 'description': 'Complete the builder welcome journey',
                      'category': self.builder_category, 'min_points': 1, 'max_points': 100}
        )
        self.builder_welcome_type.min_points = 1
        self.builder_welcome_type.max_points = 100
        self.builder_welcome_type.save(update_fields=['min_points', 'max_points'])

        self.builder_badge_type, _ = ContributionType.objects.get_or_create(
            slug='builder',
            defaults={'name': 'Builder', 'description': 'Become a builder',
                      'category': self.builder_category, 'min_points': 1, 'max_points': 100}
        )
        self.builder_badge_type.min_points = 1
        self.builder_badge_type.max_points = 100
        self.builder_badge_type.save(update_fields=['min_points', 'max_points'])

        # Create users
        self.user1 = User.objects.create(
            email='user1@test.com', name='User One',
            address='0x1234567890123456789012345678901234567890', visible=True
        )
        self.user2 = User.objects.create(
            email='user2@test.com', name='User Two',
            address='0x2345678901234567890123456789012345678901', visible=True
        )
        # user3 starts visible so contributions can be added via Contribution.objects.create().
        # Tests that need non-visible behaviour call User.objects.filter().update(visible=False)
        # AFTER contributions are created (the model blocks creation for non-visible users).
        self.user3 = User.objects.create(
            email='user3@test.com', name='User Three',
            address='0x3456789012345678901234567890123456789012', visible=True
        )

        # Create global multipliers
        self.multiplier1, _ = GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=self.node_running_type,
            defaults={'multiplier_value': Decimal('2.0'),
                      'valid_from': timezone.now() - timezone.timedelta(days=30),
                      'description': 'Double points for node running'}
        )
        self.multiplier2, _ = GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=self.builder_type,
            defaults={'multiplier_value': Decimal('1.5'),
                      'valid_from': timezone.now() - timezone.timedelta(days=20),
                      'description': '1.5x points for builders'}
        )
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=self.waitlist_type,
            defaults={'multiplier_value': Decimal('1.0'),
                      'valid_from': timezone.now() - timezone.timedelta(days=30),
                      'description': 'Standard points for waitlist'}
        )
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=self.validator_type,
            defaults={'multiplier_value': Decimal('1.0'),
                      'valid_from': timezone.now() - timezone.timedelta(days=30),
                      'description': 'Standard points for validator'}
        )
        # Multipliers for builder-welcome and builder badge types, which are
        # auto-created by ensure_builder_status() during recalculate_all_leaderboards().
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=self.builder_welcome_type,
            defaults={'multiplier_value': Decimal('1.0'),
                      'valid_from': timezone.now() - timezone.timedelta(days=30),
                      'description': 'Standard points for builder welcome'}
        )
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=self.builder_badge_type,
            defaults={'multiplier_value': Decimal('1.0'),
                      'valid_from': timezone.now() - timezone.timedelta(days=30),
                      'description': 'Standard points for builder badge'}
        )

    def test_recalculate_all_leaderboards_empty(self):
        """Test recalculation with no contributions."""
        result = recalculate_all_leaderboards()
        self.assertIn('0 users', result)
        self.assertEqual(LeaderboardEntry.objects.count(), 0)

    def test_recalculate_all_leaderboards_with_waitlist(self):
        """Test recalculation with waitlist users."""
        Contribution.objects.create(
            user=self.user1, contribution_type=self.waitlist_type, points=1,
            frozen_global_points=1, contribution_date=timezone.now() - timezone.timedelta(days=10)
        )
        Contribution.objects.create(
            user=self.user1, contribution_type=self.node_running_type, points=50,
            frozen_global_points=100, contribution_date=timezone.now() - timezone.timedelta(days=5)
        )

        result = recalculate_all_leaderboards()

        self.assertIn('1 users', result)
        self.assertIn('4 leaderboards', result)

        waitlist_entry = LeaderboardEntry.objects.filter(
            user=self.user1, type='validator-waitlist'
        ).first()
        self.assertIsNotNone(waitlist_entry)
        self.assertEqual(waitlist_entry.total_points, 101)
        self.assertEqual(waitlist_entry.rank, 1)

    def test_recalculate_with_graduation(self):
        """Test recalculation when user graduates from waitlist to validator."""
        Contribution.objects.create(
            user=self.user1, contribution_type=self.waitlist_type, points=1,
            frozen_global_points=1, contribution_date=timezone.now() - timezone.timedelta(days=10)
        )
        Contribution.objects.create(
            user=self.user1, contribution_type=self.node_running_type, points=50,
            frozen_global_points=100, contribution_date=timezone.now() - timezone.timedelta(days=5)
        )

        recalculate_all_leaderboards()

        self.assertTrue(LeaderboardEntry.objects.filter(user=self.user1, type='validator-waitlist').exists())
        self.assertFalse(LeaderboardEntry.objects.filter(user=self.user1, type='validator').exists())

        # User graduates to validator.
        # The admin shortcut (Bug 3 from FIXES.md) is supposed to create the Validator
        # profile alongside the 'validator' contribution. We simulate that here.
        from validators.models import Validator as ValidatorModel
        ValidatorModel.objects.create(user=self.user1)
        Contribution.objects.create(
            user=self.user1, contribution_type=self.validator_type,
            points=1, contribution_date=timezone.now()
        )

        recalculate_all_leaderboards()

        self.assertFalse(LeaderboardEntry.objects.filter(user=self.user1, type='validator-waitlist').exists())

        # Points: waitlist(1*1.0=1) + node-running(50*2.0=100) + validator(1*1.0=1) = 102
        validator_entry = LeaderboardEntry.objects.filter(user=self.user1, type='validator').first()
        self.assertIsNotNone(validator_entry)
        self.assertEqual(validator_entry.total_points, 102)

        # Graduation points = validator-category contributions before graduation date
        # excluding the 'validator' badge itself: waitlist(1) + node-running(100) = 101
        grad_entry = LeaderboardEntry.objects.filter(user=self.user1, type='validator-waitlist-graduation').first()
        self.assertIsNotNone(grad_entry)
        self.assertEqual(grad_entry.total_points, 101)
        self.assertIsNotNone(grad_entry.graduation_date)

    def test_recalculate_with_multiple_users(self):
        """Test recalculation with multiple users in different states."""
        # User 1: On waitlist
        Contribution.objects.create(
            user=self.user1, contribution_type=self.waitlist_type, points=1,
            frozen_global_points=1, contribution_date=timezone.now() - timezone.timedelta(days=10)
        )

        # User 2: Graduated validator — Validator profile must exist to appear on validator leaderboard
        from validators.models import Validator as ValidatorModel
        Contribution.objects.create(
            user=self.user2, contribution_type=self.waitlist_type, points=1,
            contribution_date=timezone.now() - timezone.timedelta(days=20)
        )
        Contribution.objects.create(
            user=self.user2, contribution_type=self.node_running_type, points=30,
            contribution_date=timezone.now() - timezone.timedelta(days=15)
        )
        ValidatorModel.objects.create(user=self.user2)
        Contribution.objects.create(
            user=self.user2, contribution_type=self.validator_type, points=1,
            contribution_date=timezone.now() - timezone.timedelta(days=5)
        )

        # User 3: create contribution while visible, then flip to non-visible.
        Contribution.objects.create(
            user=self.user3, contribution_type=self.waitlist_type, points=1,
            contribution_date=timezone.now() - timezone.timedelta(days=10)
        )
        User.objects.filter(pk=self.user3.pk).update(visible=False)
        self.user3.refresh_from_db()

        result = recalculate_all_leaderboards()

        self.assertIn('3 users', result)

        self.assertTrue(LeaderboardEntry.objects.filter(user=self.user1, type='validator-waitlist', rank=1).exists())
        self.assertTrue(LeaderboardEntry.objects.filter(user=self.user2, type='validator', rank=1).exists())
        self.assertTrue(LeaderboardEntry.objects.filter(user=self.user2, type='validator-waitlist-graduation', rank=1).exists())

        user3_entry = LeaderboardEntry.objects.filter(user=self.user3, type='validator-waitlist').first()
        self.assertIsNotNone(user3_entry)
        self.assertIsNone(user3_entry.rank)

    def test_recalculate_with_builder(self):
        """Test recalculation with builder contributions."""
        # recalculate_all_leaderboards() calls ensure_builder_status() which
        # auto-creates builder-welcome (20pt) and builder badge (50pt) contributions.
        # Total: welcome(20*1.0=20) + badge(50*1.0=50) + code(20*1.5=30) = 100
        Contribution.objects.create(
            user=self.user1, contribution_type=self.builder_type, points=20,
            contribution_date=timezone.now() - timezone.timedelta(days=5)
        )

        recalculate_all_leaderboards()

        builder_entry = LeaderboardEntry.objects.filter(user=self.user1, type='builder').first()
        self.assertIsNotNone(builder_entry)
        self.assertEqual(builder_entry.total_points, 100)
        self.assertEqual(builder_entry.rank, 1)

    def test_update_leaderboard_command(self):
        """Test the update_leaderboard management command."""
        Contribution.objects.create(
            user=self.user1, contribution_type=self.waitlist_type, points=1,
            contribution_date=timezone.now() - timezone.timedelta(days=10)
        )
        contribution = Contribution.objects.create(
            user=self.user1, contribution_type=self.node_running_type, points=50,
            contribution_date=timezone.now() - timezone.timedelta(days=5)
        )

        # Simulate stale data by bypassing model clean() via .update()
        Contribution.objects.filter(pk=contribution.pk).update(
            multiplier_at_creation=1.0, frozen_global_points=50
        )
        contribution.refresh_from_db()
        self.assertEqual(contribution.multiplier_at_creation, 1.0)
        self.assertEqual(contribution.frozen_global_points, 50)

        out = StringIO()
        call_command('update_leaderboard', stdout=out)
        output = out.getvalue()

        # 2 contributions total (waitlist + node-running), 1 corrected (node-running)
        self.assertIn('Starting leaderboard update', output)
        self.assertIn('Processing 2 contributions', output)
        self.assertIn('Updated 1 contributions', output)
        self.assertIn('Recalculated 1 users', output)
        self.assertIn('completed successfully', output)

        contribution.refresh_from_db()
        self.assertEqual(contribution.multiplier_at_creation, Decimal('2.0'))
        self.assertEqual(contribution.frozen_global_points, 100)

        self.assertTrue(
            LeaderboardEntry.objects.filter(user=self.user1, type='validator-waitlist', total_points=101).exists()
        )

    def test_leaderboard_config_integrity(self):
        """Test that LEADERBOARD_CONFIG is properly configured."""
        for key, config in LEADERBOARD_CONFIG.items():
            self.assertIn('name', config)
            self.assertIn('participants', config)
            self.assertIn('points_calculator', config)
            self.assertIn('ranking_order', config)
            self.assertTrue(callable(config['participants']))
            self.assertTrue(callable(config['points_calculator']))
            self.assertIn(config['ranking_order'], ['-total_points', '-graduation_date'])

    def test_frozen_graduation_points(self):
        """Test that graduation points are properly frozen."""
        Contribution.objects.create(
            user=self.user1, contribution_type=self.waitlist_type, points=1,
            contribution_date=timezone.now() - timezone.timedelta(days=10)
        )
        Contribution.objects.create(
            user=self.user1, contribution_type=self.node_running_type, points=50,
            contribution_date=timezone.now() - timezone.timedelta(days=5)
        )

        recalculate_all_leaderboards()

        # Graduate: create Validator profile first (simulates the admin shortcut)
        from validators.models import Validator as ValidatorModel
        ValidatorModel.objects.create(user=self.user1)
        Contribution.objects.create(
            user=self.user1, contribution_type=self.validator_type, points=1,
            contribution_date=timezone.now() - timezone.timedelta(days=2)
        )

        recalculate_all_leaderboards()

        grad_entry = LeaderboardEntry.objects.get(user=self.user1, type='validator-waitlist-graduation')
        frozen_points = grad_entry.total_points

        Contribution.objects.create(
            user=self.user1, contribution_type=self.node_running_type, points=100,
            contribution_date=timezone.now()
        )

        recalculate_all_leaderboards()

        # Re-fetch since recalculate deletes and recreates all entries
        grad_entry = LeaderboardEntry.objects.get(user=self.user1, type='validator-waitlist-graduation')
        self.assertEqual(grad_entry.total_points, frozen_points)

        # waitlist(1) + node-running(100) + validator-badge(1) + new node-running(200) = 302
        validator_entry = LeaderboardEntry.objects.get(user=self.user1, type='validator')
        self.assertEqual(validator_entry.total_points, 302)
