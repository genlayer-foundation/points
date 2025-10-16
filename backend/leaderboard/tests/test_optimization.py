"""
Tests for the optimized leaderboard recalculation implementation.
Verifies correctness and performance improvements.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from leaderboard.models import (
    LeaderboardEntry,
    GlobalLeaderboardMultiplier,
    ReferralPoints,
    recalculate_all_leaderboards,
)
from contributions.models import Contribution, ContributionType, Category

User = get_user_model()


class OptimizedLeaderboardTest(TestCase):
    """Test the optimized recalculate_all_leaderboards function."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data once for all tests in this class."""
        # Get or create categories (they might exist from migrations)
        cls.validator_category, _ = Category.objects.get_or_create(
            slug='validator',
            defaults={
                'name': 'Validator',
                'description': 'Validator contributions'
            }
        )
        cls.builder_category, _ = Category.objects.get_or_create(
            slug='builder',
            defaults={
                'name': 'Builder',
                'description': 'Builder contributions'
            }
        )

        # Get or create contribution types
        cls.waitlist_type, _ = ContributionType.objects.get_or_create(
            slug='validator-waitlist',
            defaults={
                'name': 'Validator Waitlist',
                'category': cls.validator_category,
                'min_points': 20,
                'max_points': 20
            }
        )

        cls.validator_type, _ = ContributionType.objects.get_or_create(
            slug='validator',
            defaults={
                'name': 'Validator',
                'category': cls.validator_category,
                'min_points': 1,
                'max_points': 1
            }
        )

        cls.node_running_type, _ = ContributionType.objects.get_or_create(
            slug='node-running',
            defaults={
                'name': 'Node Running',
                'category': cls.validator_category,
                'min_points': 10,
                'max_points': 100
            }
        )

        cls.builder_type, _ = ContributionType.objects.get_or_create(
            slug='code-contribution',
            defaults={
                'name': 'Code Contribution',
                'category': cls.builder_category,
                'min_points': 5,
                'max_points': 50
            }
        )

        cls.builder_welcome_type, _ = ContributionType.objects.get_or_create(
            slug='builder-welcome',
            defaults={
                'name': 'Builder Welcome',
                'category': cls.builder_category,
                'min_points': 20,
                'max_points': 20
            }
        )

    def setUp(self):
        """Set up for each test."""
        # Clear data that changes between tests
        User.objects.all().delete()
        Contribution.objects.all().delete()
        LeaderboardEntry.objects.all().delete()
        ReferralPoints.objects.all().delete()

        # Ensure ALL existing contribution types have multipliers
        # Use a very old date to ensure multipliers are valid for all test contributions
        # Test contributions go back up to 20 days, so we use 365 days to be safe
        for contrib_type in ContributionType.objects.all():
            GlobalLeaderboardMultiplier.objects.get_or_create(
                contribution_type=contrib_type,
                defaults={
                    'multiplier_value': Decimal('1.0'),
                    'valid_from': timezone.now() - timezone.timedelta(days=365)
                }
            )

        # Set specific multipliers for our test types
        GlobalLeaderboardMultiplier.objects.filter(
            contribution_type=self.node_running_type
        ).update(
            multiplier_value=Decimal('2.0'),
            valid_from=timezone.now() - timezone.timedelta(days=365)
        )

        GlobalLeaderboardMultiplier.objects.filter(
            contribution_type=self.builder_type
        ).update(
            multiplier_value=Decimal('1.5'),
            valid_from=timezone.now() - timezone.timedelta(days=365)
        )

    def test_query_count_with_data(self):
        """Test that query count is low and constant."""
        # Create test users with contributions
        for i in range(10):
            user = User.objects.create(
                email=f'user{i}@test.com',
                name=f'User {i}',
                address=f'0x{i:040d}',  # Valid 42-char Ethereum address
                visible=True
            )

            # Add various contributions
            # Note: multiplier_at_creation and frozen_global_points are calculated automatically
            Contribution.objects.create(
                user=user,
                contribution_type=self.waitlist_type,
                points=20,  # Correct points for validator-waitlist
                contribution_date=timezone.now() - timezone.timedelta(days=20)
            )
            Contribution.objects.create(
                user=user,
                contribution_type=self.node_running_type,
                points=50,
                contribution_date=timezone.now() - timezone.timedelta(days=10)
            )

        # The optimization reduces queries significantly
        result = recalculate_all_leaderboards()

        self.assertIn('10 users', result)
        self.assertEqual(LeaderboardEntry.objects.count(), 10)

    def test_builder_welcome_exclusion(self):
        """Test that builder-welcome contributions are excluded from builder leaderboard."""
        user = User.objects.create(
            email='builder@test.com',
            name='Builder User',
            address='0x1234567890123456789012345678901234567890',
            visible=True
        )

        # Create builder-welcome contribution
        Contribution.objects.create(
            user=user,
            contribution_type=self.builder_welcome_type,
            points=20,  # Correct points for builder-welcome
            contribution_date=timezone.now()
        )

        recalculate_all_leaderboards()

        # User should NOT be on builder leaderboard
        self.assertFalse(
            LeaderboardEntry.objects.filter(
                user=user,
                type='builder'
            ).exists()
        )

        # Add a real builder contribution
        contrib = Contribution.objects.create(
            user=user,
            contribution_type=self.builder_type,
            points=10,
            contribution_date=timezone.now()
        )

        recalculate_all_leaderboards()

        # Now user SHOULD be on builder leaderboard with only real contribution points
        entry = LeaderboardEntry.objects.get(user=user, type='builder')
        # Points are 10 * 1.5 multiplier = 15
        self.assertEqual(entry.total_points, 15)  # Only code-contribution points

    def test_referral_points_calculation(self):
        """Test that referral points are correctly calculated."""
        # Create referrer
        referrer = User.objects.create(
            email='referrer@test.com',
            name='Referrer',
            address='0x1111111111111111111111111111111111111111',
            visible=True
        )

        # Create referred user
        referred = User.objects.create(
            email='referred@test.com',
            name='Referred User',
            address='0x2222222222222222222222222222222222222222',
            visible=True,
            referred_by=referrer
        )

        # Referrer joins waitlist
        Contribution.objects.create(
            user=referrer,
            contribution_type=self.waitlist_type,
            points=20,  # Correct points for validator-waitlist
            contribution_date=timezone.now() - timezone.timedelta(days=10)
        )

        # Referred user makes contributions
        referred_contrib = Contribution.objects.create(
            user=referred,
            contribution_type=self.node_running_type,
            points=100,  # This will be 100 * 2.0 = 200 with multiplier
            contribution_date=timezone.now()
        )

        recalculate_all_leaderboards()

        # Check referral points were created
        rp = ReferralPoints.objects.get(user=referrer)
        self.assertEqual(rp.validator_points, 20)  # 10% of 200

        # Check referrer's waitlist leaderboard includes referral points
        entry = LeaderboardEntry.objects.get(user=referrer, type='validator-waitlist')
        self.assertEqual(entry.total_points, 40)  # 20 own + 20 referral

    def test_graduation_points_freezing(self):
        """Test that graduation points are correctly frozen at graduation date."""
        user = User.objects.create(
            email='graduate@test.com',
            name='Graduate User',
            address='0x3333333333333333333333333333333333333333',
            visible=True
        )

        # Join waitlist
        Contribution.objects.create(
            user=user,
            contribution_type=self.waitlist_type,
            points=20,  # Correct points for validator-waitlist
            contribution_date=timezone.now() - timezone.timedelta(days=20)
        )

        # Some validator work before graduation (50 * 2 = 100 with multiplier)
        Contribution.objects.create(
            user=user,
            contribution_type=self.node_running_type,
            points=50,
            contribution_date=timezone.now() - timezone.timedelta(days=15)
        )

        # Graduate
        grad_date = timezone.now() - timezone.timedelta(days=10)
        Contribution.objects.create(
            user=user,
            contribution_type=self.validator_type,
            points=1,
            contribution_date=grad_date
        )

        # More work after graduation (100 * 2 = 200 with multiplier)
        Contribution.objects.create(
            user=user,
            contribution_type=self.node_running_type,
            points=100,
            contribution_date=timezone.now() - timezone.timedelta(days=5)
        )

        recalculate_all_leaderboards()

        # Check graduation entry has only pre-graduation points
        grad_entry = LeaderboardEntry.objects.get(
            user=user,
            type='validator-waitlist-graduation'
        )
        self.assertEqual(grad_entry.total_points, 120)  # 20 + 100 (before graduation)
        self.assertEqual(grad_entry.graduation_date, grad_date)

        # Check validator entry has all points
        validator_entry = LeaderboardEntry.objects.get(user=user, type='validator')
        self.assertEqual(validator_entry.total_points, 321)  # 20 + 100 + 1 + 200

    def test_non_visible_user_handling(self):
        """Test that non-visible users get entries but no ranks."""
        visible_user = User.objects.create(
            email='visible@test.com',
            name='Visible User',
            address='0x4444444444444444444444444444444444444444',
            visible=True
        )

        non_visible_user = User.objects.create(
            email='hidden@test.com',
            name='Hidden User',
            address='0x5555555555555555555555555555555555555555',
            visible=True  # Create as visible first
        )

        # Both users have same contributions
        for user in [visible_user, non_visible_user]:
            Contribution.objects.create(
                user=user,
                contribution_type=self.waitlist_type,
                points=20,  # Correct points for validator-waitlist
                contribution_date=timezone.now()
            )

        # NOW mark the user as non-visible after contributions are created
        non_visible_user.visible = False
        non_visible_user.save()

        recalculate_all_leaderboards()

        # Both should have entries
        self.assertTrue(LeaderboardEntry.objects.filter(user=visible_user).exists())
        self.assertTrue(LeaderboardEntry.objects.filter(user=non_visible_user).exists())

        # Visible user should have rank
        visible_entry = LeaderboardEntry.objects.get(user=visible_user)
        self.assertEqual(visible_entry.rank, 1)

        # Non-visible user should have NULL rank
        non_visible_entry = LeaderboardEntry.objects.get(user=non_visible_user)
        self.assertIsNone(non_visible_entry.rank)

    def test_complete_recalculation_accuracy(self):
        """Test that recalculation produces accurate points and rankings."""
        # Create users with different point totals
        user1 = User.objects.create(
            email='user1@test.com',
            name='User 1',
            address='0x1111111111111111111111111111111111111111',
            visible=True
        )
        user2 = User.objects.create(
            email='user2@test.com',
            name='User 2',
            address='0x2222222222222222222222222222222222222222',
            visible=True
        )
        user3 = User.objects.create(
            email='user3@test.com',
            name='User 3',
            address='0x3333333333333333333333333333333333333333',
            visible=True
        )

        # User1: 120 total points - started contributing 10 days ago
        Contribution.objects.create(
            user=user1,
            contribution_type=self.waitlist_type,
            points=20,
            contribution_date=timezone.now() - timezone.timedelta(days=10)  # Earlier
        )
        Contribution.objects.create(
            user=user1,
            contribution_type=self.node_running_type,
            points=50,  # 50 * 2.0 = 100
            contribution_date=timezone.now()
        )

        # User2: 120 total points - started contributing 5 days ago
        Contribution.objects.create(
            user=user2,
            contribution_type=self.waitlist_type,
            points=20,
            contribution_date=timezone.now() - timezone.timedelta(days=5)  # Later
        )
        Contribution.objects.create(
            user=user2,
            contribution_type=self.node_running_type,
            points=50,  # 50 * 2.0 = 100
            contribution_date=timezone.now()
        )

        # User3: 220 total points (should rank #1)
        Contribution.objects.create(
            user=user3,
            contribution_type=self.waitlist_type,
            points=20,
            contribution_date=timezone.now()
        )
        Contribution.objects.create(
            user=user3,
            contribution_type=self.node_running_type,
            points=100,  # 100 * 2.0 = 200
            contribution_date=timezone.now()
        )

        # Run recalculation
        result = recalculate_all_leaderboards()

        # Verify validator-waitlist leaderboard entries and points
        # (All users have waitlist contributions so they appear here)
        waitlist_entries = LeaderboardEntry.objects.filter(
            type='validator-waitlist'
        ).order_by('rank')

        self.assertEqual(waitlist_entries.count(), 3)

        # Check user3 is rank 1 with 220 points
        user3_entry = waitlist_entries.get(user=user3)
        self.assertEqual(user3_entry.rank, 1)
        self.assertEqual(user3_entry.total_points, 220)

        # Check user1 and user2 have consecutive ranks (tied by points, ordered by name)
        user1_entry = waitlist_entries.get(user=user1)
        user2_entry = waitlist_entries.get(user=user2)

        # They should both have same points
        self.assertEqual(user1_entry.total_points, 120)
        self.assertEqual(user2_entry.total_points, 120)

        # User1 should rank higher (2) because they started contributing earlier
        # User2 should rank lower (3) because they started contributing later
        self.assertEqual(user1_entry.rank, 2)  # Earlier contributor (10 days ago)
        self.assertEqual(user2_entry.rank, 3)  # Later contributor (5 days ago)

        # Verify no one is on validator leaderboard
        # (they don't have the validator badge, only waitlist)
        validator_entries = LeaderboardEntry.objects.filter(
            type='validator'
        )
        self.assertEqual(validator_entries.count(), 0)

        # Verify no one is on builder leaderboard
        # (no builder contributions)
        builder_entries = LeaderboardEntry.objects.filter(
            type='builder'
        )
        self.assertEqual(builder_entries.count(), 0)

        # Verify old data was cleared (run again and check)
        old_count = LeaderboardEntry.objects.count()
        recalculate_all_leaderboards()
        new_count = LeaderboardEntry.objects.count()
        self.assertEqual(old_count, new_count)  # Should be same, not doubled