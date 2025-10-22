"""
Test to verify that the optimized recalculate_all_leaderboards produces
the exact same results as the original implementation.
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
    update_user_leaderboard_entries,
    recalculate_referrer_points,
    LEADERBOARD_CONFIG
)
from contributions.models import Contribution, ContributionType, Category

User = get_user_model()


class CalculationAccuracyTest(TestCase):
    """Compare optimized vs original calculation methods."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data once for all tests in this class."""
        # Get or create categories
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
        for contrib_type in ContributionType.objects.all():
            GlobalLeaderboardMultiplier.objects.get_or_create(
                contribution_type=contrib_type,
                defaults={
                    'multiplier_value': Decimal('1.0'),
                    'valid_from': timezone.now() - timezone.timedelta(days=365)
                }
            )

        # Set specific multipliers
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

    def test_compare_methods_complex_scenario(self):
        """Test that both methods produce identical results in a complex scenario."""
        # Create users with referrals
        referrer = User.objects.create(
            email='referrer@test.com',
            name='Referrer',
            address='0x1111111111111111111111111111111111111111',
            visible=True
        )

        referred1 = User.objects.create(
            email='referred1@test.com',
            name='Referred One',
            address='0x2222222222222222222222222222222222222222',
            visible=True,
            referred_by=referrer
        )

        referred2 = User.objects.create(
            email='referred2@test.com',
            name='Referred Two',
            address='0x3333333333333333333333333333333333333333',
            visible=True,
            referred_by=referrer
        )

        regular_user = User.objects.create(
            email='regular@test.com',
            name='Regular User',
            address='0x4444444444444444444444444444444444444444',
            visible=True
        )

        # Create various contributions
        # Referrer: waitlist + node running + graduation
        Contribution.objects.create(
            user=referrer,
            contribution_type=self.waitlist_type,
            points=20,
            contribution_date=timezone.now() - timezone.timedelta(days=30)
        )
        Contribution.objects.create(
            user=referrer,
            contribution_type=self.node_running_type,
            points=50,
            contribution_date=timezone.now() - timezone.timedelta(days=25)
        )
        Contribution.objects.create(
            user=referrer,
            contribution_type=self.validator_type,
            points=1,
            contribution_date=timezone.now() - timezone.timedelta(days=10)  # Graduation
        )
        Contribution.objects.create(
            user=referrer,
            contribution_type=self.node_running_type,
            points=75,
            contribution_date=timezone.now() - timezone.timedelta(days=5)  # After graduation
        )

        # Referred1: builder + validator contributions
        Contribution.objects.create(
            user=referred1,
            contribution_type=self.builder_welcome_type,
            points=20,
            contribution_date=timezone.now() - timezone.timedelta(days=20)
        )
        Contribution.objects.create(
            user=referred1,
            contribution_type=self.builder_type,
            points=30,
            contribution_date=timezone.now() - timezone.timedelta(days=15)
        )
        Contribution.objects.create(
            user=referred1,
            contribution_type=self.waitlist_type,
            points=20,
            contribution_date=timezone.now() - timezone.timedelta(days=12)
        )
        Contribution.objects.create(
            user=referred1,
            contribution_type=self.node_running_type,
            points=60,
            contribution_date=timezone.now() - timezone.timedelta(days=8)  # Before referrer graduation
        )
        Contribution.objects.create(
            user=referred1,
            contribution_type=self.node_running_type,
            points=40,
            contribution_date=timezone.now() - timezone.timedelta(days=3)  # After referrer graduation
        )

        # Referred2: only validator contributions
        Contribution.objects.create(
            user=referred2,
            contribution_type=self.waitlist_type,
            points=20,
            contribution_date=timezone.now() - timezone.timedelta(days=18)
        )
        Contribution.objects.create(
            user=referred2,
            contribution_type=self.node_running_type,
            points=80,
            contribution_date=timezone.now() - timezone.timedelta(days=7)  # Before referrer graduation
        )

        # Regular user: mixed contributions
        Contribution.objects.create(
            user=regular_user,
            contribution_type=self.waitlist_type,
            points=20,
            contribution_date=timezone.now() - timezone.timedelta(days=15)
        )
        Contribution.objects.create(
            user=regular_user,
            contribution_type=self.builder_type,
            points=25,
            contribution_date=timezone.now() - timezone.timedelta(days=10)
        )

        # Method 1: Use the optimized batch recalculation
        recalculate_all_leaderboards()

        # Save optimized results
        optimized_entries = {}
        optimized_referral_points = {}

        for entry in LeaderboardEntry.objects.all():
            key = (entry.user_id, entry.type)
            optimized_entries[key] = {
                'total_points': entry.total_points,
                'rank': entry.rank,
                'graduation_date': entry.graduation_date
            }

        for rp in ReferralPoints.objects.all():
            optimized_referral_points[rp.user_id] = {
                'builder_points': rp.builder_points,
                'validator_points': rp.validator_points
            }

        # Method 2: Use the original per-user functions
        LeaderboardEntry.objects.all().delete()
        ReferralPoints.objects.all().delete()

        # Recalculate using original methods
        from django.db import transaction
        with transaction.atomic():
            # Calculate referral points first
            referrers = User.objects.filter(referrals__isnull=False).distinct()
            for ref in referrers:
                recalculate_referrer_points(ref)

            # Update each user's leaderboard entries
            users = User.objects.filter(contributions__isnull=False).distinct()
            for user in users:
                update_user_leaderboard_entries(user)

            # Update ranks
            for leaderboard_type in LEADERBOARD_CONFIG.keys():
                LeaderboardEntry.update_leaderboard_ranks(leaderboard_type)

        # Compare results
        for entry in LeaderboardEntry.objects.all():
            key = (entry.user_id, entry.type)
            self.assertIn(key, optimized_entries,
                         f"Entry for user {entry.user_id} on {entry.type} leaderboard missing in optimized version")

            opt = optimized_entries[key]
            self.assertEqual(entry.total_points, opt['total_points'],
                           f"Points mismatch for user {entry.user_id} on {entry.type}: "
                           f"original={entry.total_points}, optimized={opt['total_points']}")
            self.assertEqual(entry.rank, opt['rank'],
                           f"Rank mismatch for user {entry.user_id} on {entry.type}: "
                           f"original={entry.rank}, optimized={opt['rank']}")
            self.assertEqual(entry.graduation_date, opt['graduation_date'],
                           f"Graduation date mismatch for user {entry.user_id} on {entry.type}")

        # Compare referral points
        for rp in ReferralPoints.objects.all():
            self.assertIn(rp.user_id, optimized_referral_points,
                         f"Referral points for user {rp.user_id} missing in optimized version")

            opt_rp = optimized_referral_points[rp.user_id]
            self.assertEqual(rp.builder_points, opt_rp['builder_points'],
                           f"Builder referral points mismatch for user {rp.user_id}: "
                           f"original={rp.builder_points}, optimized={opt_rp['builder_points']}")
            self.assertEqual(rp.validator_points, opt_rp['validator_points'],
                           f"Validator referral points mismatch for user {rp.user_id}: "
                           f"original={rp.validator_points}, optimized={opt_rp['validator_points']}")

        # Ensure same number of entries
        self.assertEqual(len(optimized_entries),
                        LeaderboardEntry.objects.count(),
                        "Different number of leaderboard entries between methods")
        self.assertEqual(len(optimized_referral_points),
                        ReferralPoints.objects.count(),
                        "Different number of referral point records between methods")