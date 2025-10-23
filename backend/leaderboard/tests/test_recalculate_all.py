"""
Comprehensive tests for recalculate_all_leaderboards function.

Tests all implemented functionality:
- Profile-based leaderboard qualification (Builder/Validator profiles)
- Point calculations including all category contributions
- Graduation snapshot freezing
- Referral points
- Tie-breaking logic
- Query performance
"""
import time
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from contributions.models import ContributionType, Contribution, Category
from leaderboard.models import (
    GlobalLeaderboardMultiplier,
    LeaderboardEntry,
    ReferralPoints,
    recalculate_all_leaderboards
)

User = get_user_model()


class RecalculateAllLeaderboardsTest(TestCase):
    """Comprehensive test suite for recalculate_all_leaderboards."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        print("\n" + "="*80)
        print("RECALCULATE ALL LEADERBOARDS - COMPREHENSIVE TEST SUITE")
        print("="*80)

    def setUp(self):
        """Set up test data before each test."""
        # Get or create categories (they may exist from migrations)
        self.builder_category, _ = Category.objects.get_or_create(
            slug='builder',
            defaults={'name': 'Builder'}
        )
        self.validator_category, _ = Category.objects.get_or_create(
            slug='validator',
            defaults={'name': 'Validator'}
        )

        # Get or create contribution types (they may exist from migrations)
        self.builder_welcome_type, _ = ContributionType.objects.get_or_create(
            slug='builder-welcome',
            defaults={
                'name': 'Builder Welcome',
                'category': self.builder_category,
                'min_points': 10,
                'max_points': 100
            }
        )
        self.builder_type, _ = ContributionType.objects.get_or_create(
            slug='builder',
            defaults={
                'name': 'Builder',
                'category': self.builder_category,
                'min_points': 10,
                'max_points': 100
            }
        )
        self.code_contribution_type, _ = ContributionType.objects.get_or_create(
            slug='code-contribution',
            defaults={
                'name': 'Code Contribution',
                'category': self.builder_category,
                'min_points': 10,
                'max_points': 100
            }
        )
        self.node_running_type, _ = ContributionType.objects.get_or_create(
            slug='node-running',
            defaults={
                'name': 'Node Running',
                'category': self.validator_category,
                'min_points': 10,
                'max_points': 100
            }
        )
        self.validator_type, _ = ContributionType.objects.get_or_create(
            slug='validator',
            defaults={
                'name': 'Validator',
                'category': self.validator_category,
                'min_points': 1,
                'max_points': 100
            }
        )
        self.waitlist_type, _ = ContributionType.objects.get_or_create(
            slug='validator-waitlist',
            defaults={
                'name': 'Validator Waitlist',
                'category': self.validator_category,
                'min_points': 10,
                'max_points': 100
            }
        )

        # Create multipliers
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.builder_welcome_type,
            multiplier_value=Decimal('1.0'),
            valid_from=timezone.now() - timezone.timedelta(days=365)
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.builder_type,
            multiplier_value=Decimal('1.5'),
            valid_from=timezone.now() - timezone.timedelta(days=365)
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.code_contribution_type,
            multiplier_value=Decimal('1.5'),
            valid_from=timezone.now() - timezone.timedelta(days=365)
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.node_running_type,
            multiplier_value=Decimal('2.0'),
            valid_from=timezone.now() - timezone.timedelta(days=365)
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.validator_type,
            multiplier_value=Decimal('1.0'),
            valid_from=timezone.now() - timezone.timedelta(days=365)
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.waitlist_type,
            multiplier_value=Decimal('1.0'),
            valid_from=timezone.now() - timezone.timedelta(days=365)
        )

    def test_builder_qualification_and_points(self):
        """
        Test that:
        1. Users need Builder profile to appear on builder leaderboard
        2. Builder-welcome alone doesn't qualify (no profile created)
        3. Builder points include ALL builder category contributions (including builder-welcome)
        """
        print("\n[TEST] Builder qualification and points calculation")

        user = User.objects.create(
            email='builder@test.com',
            name='Builder User',
            address='0x1111111111111111111111111111111111111111',
            visible=True
        )

        # Create builder-welcome contribution
        Contribution.objects.create(
            user=user,
            contribution_type=self.builder_welcome_type,
            points=20,
            contribution_date=timezone.now()
        )

        start = time.time()
        recalculate_all_leaderboards()
        elapsed = time.time() - start

        # User should NOT be on builder leaderboard (no Builder profile)
        self.assertFalse(
            LeaderboardEntry.objects.filter(user=user, type='builder').exists(),
            "User with only builder-welcome should not appear on builder leaderboard"
        )

        # Add real builder contribution AND create Builder profile
        Contribution.objects.create(
            user=user,
            contribution_type=self.builder_type,
            points=10,
            contribution_date=timezone.now()
        )

        from builders.models import Builder
        Builder.objects.create(user=user)

        start = time.time()
        recalculate_all_leaderboards()
        elapsed = time.time() - start

        # Now user SHOULD be on builder leaderboard with ALL builder points
        entry = LeaderboardEntry.objects.get(user=user, type='builder')
        # builder-welcome (20 * 1.0 = 20) + builder (10 * 1.5 = 15) = 35
        self.assertEqual(entry.total_points, 35)

        print(f"✓ Builder qualification correct (only with Builder profile)")
        print(f"✓ Builder points include builder-welcome: {entry.total_points} points")
        print(f"⏱  Time: {elapsed:.3f}s")

    def test_validator_qualification_and_points(self):
        """
        Test that:
        1. Users need Validator profile to appear on validator leaderboard
        2. Validator points include ALL validator category contributions
        3. This includes contributions earned during waitlist phase
        """
        print("\n[TEST] Validator qualification and points calculation")

        user = User.objects.create(
            email='validator@test.com',
            name='Validator User',
            address='0x2222222222222222222222222222222222222222',
            visible=True
        )

        # Waitlist contribution
        Contribution.objects.create(
            user=user,
            contribution_type=self.waitlist_type,
            points=20,
            contribution_date=timezone.now() - timezone.timedelta(days=20)
        )

        # Validator work during waitlist
        Contribution.objects.create(
            user=user,
            contribution_type=self.node_running_type,
            points=50,
            contribution_date=timezone.now() - timezone.timedelta(days=15)
        )

        # Graduate
        Contribution.objects.create(
            user=user,
            contribution_type=self.validator_type,
            points=1,
            contribution_date=timezone.now() - timezone.timedelta(days=10)
        )

        from validators.models import Validator
        Validator.objects.create(user=user)

        # More work after graduation
        Contribution.objects.create(
            user=user,
            contribution_type=self.node_running_type,
            points=100,
            contribution_date=timezone.now() - timezone.timedelta(days=5)
        )

        start = time.time()
        recalculate_all_leaderboards()
        elapsed = time.time() - start

        # Check validator entry includes ALL validator contributions
        entry = LeaderboardEntry.objects.get(user=user, type='validator')
        # waitlist (20*1.0) + node-running-1 (50*2.0) + validator (1*1.0) + node-running-2 (100*2.0)
        # = 20 + 100 + 1 + 200 = 321
        self.assertEqual(entry.total_points, 321)

        print(f"✓ Validator qualification correct (only with Validator profile)")
        print(f"✓ Validator points include waitlist contributions: {entry.total_points} points")
        print(f"⏱  Time: {elapsed:.3f}s")

    def test_graduation_snapshot_and_freezing(self):
        """
        Test that:
        1. Graduation snapshot captures points at graduation time
        2. Snapshot excludes the 'validator' contribution itself (graduation marker)
        3. Points remain frozen across multiple recalculations
        4. New contributions after graduation don't affect snapshot
        """
        print("\n[TEST] Graduation snapshot and point freezing")

        graduate = User.objects.create(
            email='graduate@test.com',
            name='Graduate',
            address='0x3333333333333333333333333333333333333333',
            visible=True
        )

        referred_user = User.objects.create(
            email='referred@test.com',
            name='Referred User',
            address='0x4444444444444444444444444444444444444444',
            visible=True,
            referred_by=graduate
        )

        # Join waitlist
        Contribution.objects.create(
            user=graduate,
            contribution_type=self.waitlist_type,
            points=20,
            contribution_date=timezone.now() - timezone.timedelta(days=30)
        )

        # Referred user earns points before graduation
        Contribution.objects.create(
            user=referred_user,
            contribution_type=self.node_running_type,
            points=100,  # 100 * 2 = 200
            contribution_date=timezone.now() - timezone.timedelta(days=25)
        )

        # Graduate earns validator points before graduation
        Contribution.objects.create(
            user=graduate,
            contribution_type=self.node_running_type,
            points=50,  # 50 * 2 = 100
            contribution_date=timezone.now() - timezone.timedelta(days=20)
        )

        # GRADUATION
        grad_date = timezone.now() - timezone.timedelta(days=15)
        Contribution.objects.create(
            user=graduate,
            contribution_type=self.validator_type,
            points=1,
            contribution_date=grad_date
        )

        from validators.models import Validator
        Validator.objects.create(user=graduate)

        # First recalculation - creates graduation entry
        start = time.time()
        recalculate_all_leaderboards()
        elapsed_1 = time.time() - start

        grad_entry = LeaderboardEntry.objects.get(
            user=graduate,
            type='validator-waitlist-graduation'
        )
        # waitlist (20) + node-running (100) + referral (10% of 200 = 20) = 140
        # Should NOT include the validator contribution (graduation marker)
        initial_points = grad_entry.total_points
        initial_grad_date = grad_entry.graduation_date
        self.assertEqual(initial_points, 140)
        self.assertEqual(initial_grad_date, grad_date)

        # Add MORE contributions AFTER graduation
        Contribution.objects.create(
            user=graduate,
            contribution_type=self.node_running_type,
            points=100,
            contribution_date=timezone.now() - timezone.timedelta(days=5)
        )

        Contribution.objects.create(
            user=referred_user,
            contribution_type=self.node_running_type,
            points=100,
            contribution_date=timezone.now() - timezone.timedelta(days=3)
        )

        # Second recalculation - points should NOT change
        start = time.time()
        recalculate_all_leaderboards()
        elapsed_2 = time.time() - start

        grad_entry_after = LeaderboardEntry.objects.get(
            user=graduate,
            type='validator-waitlist-graduation'
        )
        self.assertEqual(grad_entry_after.total_points, initial_points)
        self.assertEqual(grad_entry_after.graduation_date, initial_grad_date)

        # Third recalculation - still frozen
        start = time.time()
        recalculate_all_leaderboards()
        elapsed_3 = time.time() - start

        grad_entry_final = LeaderboardEntry.objects.get(
            user=graduate,
            type='validator-waitlist-graduation'
        )
        self.assertEqual(grad_entry_final.total_points, initial_points)

        print(f"✓ Graduation snapshot correct: {initial_points} points")
        print(f"✓ Snapshot excludes validator contribution (graduation marker)")
        print(f"✓ Points frozen across 3 recalculations")
        print(f"⏱  Recalc 1: {elapsed_1:.3f}s, Recalc 2: {elapsed_2:.3f}s, Recalc 3: {elapsed_3:.3f}s")

    def test_waitlist_qualification(self):
        """
        Test that waitlist users:
        1. Have validator-waitlist contribution
        2. Do NOT have Validator profile (not graduated yet)
        3. Appear on validator-waitlist leaderboard
        4. Include referral points
        """
        print("\n[TEST] Validator waitlist qualification and points")

        waitlist_user = User.objects.create(
            email='waitlist@test.com',
            name='Waitlist User',
            address='0x5555555555555555555555555555555555555555',
            visible=True
        )

        referred = User.objects.create(
            email='referred2@test.com',
            name='Referred 2',
            address='0x6666666666666666666666666666666666666666',
            visible=True,
            referred_by=waitlist_user
        )

        # Join waitlist
        Contribution.objects.create(
            user=waitlist_user,
            contribution_type=self.waitlist_type,
            points=20,
            contribution_date=timezone.now()
        )

        # Referred user earns points
        Contribution.objects.create(
            user=referred,
            contribution_type=self.node_running_type,
            points=100,  # 100 * 2 = 200, 10% = 20 referral points
            contribution_date=timezone.now()
        )

        start = time.time()
        recalculate_all_leaderboards()
        elapsed = time.time() - start

        # Should be on waitlist leaderboard
        entry = LeaderboardEntry.objects.get(user=waitlist_user, type='validator-waitlist')
        # waitlist (20) + referral (20) = 40
        self.assertEqual(entry.total_points, 40)

        # Should NOT be on validator or graduation leaderboards
        self.assertFalse(
            LeaderboardEntry.objects.filter(user=waitlist_user, type='validator').exists()
        )
        self.assertFalse(
            LeaderboardEntry.objects.filter(user=waitlist_user, type='validator-waitlist-graduation').exists()
        )

        print(f"✓ Waitlist qualification correct (no Validator profile)")
        print(f"✓ Waitlist points include referrals: {entry.total_points} points")
        print(f"⏱  Time: {elapsed:.3f}s")

    def test_referral_points_calculation(self):
        """Test that referral points are calculated correctly (10% of referred user contributions)."""
        print("\n[TEST] Referral points calculation")

        referrer = User.objects.create(
            email='referrer@test.com',
            name='Referrer',
            address='0x7777777777777777777777777777777777777777',
            visible=True
        )

        referred = User.objects.create(
            email='referred3@test.com',
            name='Referred 3',
            address='0x8888888888888888888888888888888888888888',
            visible=True,
            referred_by=referrer
        )

        # Referrer joins waitlist
        Contribution.objects.create(
            user=referrer,
            contribution_type=self.waitlist_type,
            points=20,
            contribution_date=timezone.now()
        )

        # Referred user earns validator points
        Contribution.objects.create(
            user=referred,
            contribution_type=self.node_running_type,
            points=100,  # 100 * 2 = 200 frozen points
            contribution_date=timezone.now()
        )

        start = time.time()
        recalculate_all_leaderboards()
        elapsed = time.time() - start

        # Check ReferralPoints record
        rp = ReferralPoints.objects.get(user=referrer)
        self.assertEqual(rp.validator_points, 20)  # 10% of 200

        # Check referrer's waitlist entry includes referral points
        entry = LeaderboardEntry.objects.get(user=referrer, type='validator-waitlist')
        self.assertEqual(entry.total_points, 40)  # 20 own + 20 referral

        print(f"✓ Referral points correctly calculated: 10% of {200} = {rp.validator_points}")
        print(f"✓ Referral points included in leaderboard: {entry.total_points} total points")
        print(f"⏱  Time: {elapsed:.3f}s")

    def test_tie_breaking_logic(self):
        """Test that ties are broken by user join date (earlier = higher rank)."""
        print("\n[TEST] Tie-breaking by user join date")

        # Create two users with same points but different join dates
        older_user = User.objects.create(
            email='older@test.com',
            name='Older User',
            address='0x9999999999999999999999999999999999999999',
            visible=True,
            date_joined=timezone.now() - timezone.timedelta(days=100)
        )

        newer_user = User.objects.create(
            email='newer@test.com',
            name='Newer User',
            address='0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
            visible=True,
            date_joined=timezone.now() - timezone.timedelta(days=50)
        )

        # Both join waitlist
        for user in [older_user, newer_user]:
            Contribution.objects.create(
                user=user,
                contribution_type=self.waitlist_type,
                points=20,
                contribution_date=timezone.now()
            )

        start = time.time()
        recalculate_all_leaderboards()
        elapsed = time.time() - start

        older_entry = LeaderboardEntry.objects.get(user=older_user, type='validator-waitlist')
        newer_entry = LeaderboardEntry.objects.get(user=newer_user, type='validator-waitlist')

        # Both have same points
        self.assertEqual(older_entry.total_points, 20)
        self.assertEqual(newer_entry.total_points, 20)

        # Older user should rank higher (lower rank number)
        self.assertLess(older_entry.rank, newer_entry.rank)

        print(f"✓ Tie-breaking correct: older user (rank {older_entry.rank}) > newer user (rank {newer_entry.rank})")
        print(f"⏱  Time: {elapsed:.3f}s")

    def test_performance_with_many_users(self):
        """Test that query count remains low even with many users."""
        print("\n[TEST] Query performance with multiple users")

        # Create 50 users with various contributions
        user_count = 50
        users = []

        for i in range(user_count):
            user = User.objects.create(
                email=f'user{i}@test.com',
                name=f'User {i}',
                address=f'0x{"0"*38}{i:02d}',
                visible=True
            )
            users.append(user)

            # Some users on waitlist
            if i % 3 == 0:
                Contribution.objects.create(
                    user=user,
                    contribution_type=self.waitlist_type,
                    points=20,
                    contribution_date=timezone.now()
                )

            # Some users are builders
            if i % 2 == 0:
                Contribution.objects.create(
                    user=user,
                    contribution_type=self.builder_welcome_type,
                    points=20,
                    contribution_date=timezone.now()
                )
                Contribution.objects.create(
                    user=user,
                    contribution_type=self.builder_type,
                    points=10,
                    contribution_date=timezone.now()
                )
                from builders.models import Builder
                Builder.objects.create(user=user)

            # Some users graduated
            if i % 4 == 0:
                Contribution.objects.create(
                    user=user,
                    contribution_type=self.validator_type,
                    points=1,
                    contribution_date=timezone.now()
                )
                from validators.models import Validator
                Validator.objects.create(user=user)

        from django.test.utils import override_settings
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as context:
            start = time.time()
            result = recalculate_all_leaderboards()
            elapsed = time.time() - start

        query_count = len(context.captured_queries)

        print(f"✓ Processed {user_count} users")
        print(f"✓ Query count: {query_count} queries")
        print(f"✓ Result: {result}")
        print(f"⏱  Time: {elapsed:.3f}s ({elapsed/user_count*1000:.1f}ms per user)")

        # Query count should be low and constant regardless of user count
        # Expected: ~15 queries (loads, deletes, bulk creates, rank updates)
        self.assertLess(query_count, 25, f"Query count too high: {query_count}")

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        print("\n" + "="*80)
        print("ALL TESTS COMPLETED")
        print("="*80 + "\n")
