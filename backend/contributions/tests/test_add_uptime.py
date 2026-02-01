"""
Comprehensive test for add_daily_uptime management command.
Tests correctness of uptime calculation and basic performance.
"""
from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from decimal import Decimal
from io import StringIO
import time
import pytz

from contributions.models import Contribution, ContributionType, Category
from leaderboard.models import GlobalLeaderboardMultiplier
from validators.models import Validator
from django.db import models

User = get_user_model()


class AddDailyUptimeTest(TestCase):
    """Comprehensive test for the add_daily_uptime command."""

    def setUp(self):
        """Set up test data with realistic scenarios."""
        # Use a fixed reference time to avoid timing issues
        self.now = timezone.now()
        self.today = self.now.date()

        # Get or create category (migrations may have created it)
        self.validator_category, _ = Category.objects.get_or_create(
            slug='validator',
            defaults={
                'name': 'Validator',
                'description': 'Validator contributions'
            }
        )

        # Get or create uptime contribution type (may already exist)
        self.uptime_type, created = ContributionType.objects.get_or_create(
            slug='uptime',
            defaults={
                'name': 'Uptime',
                'description': 'Daily validator uptime',
                'category': self.validator_category,
                'min_points': 1,
                'max_points': 10
            }
        )

        # If uptime type already exists, ensure it has the right settings
        if not created:
            self.uptime_type.category = self.validator_category
            self.uptime_type.min_points = 1
            self.uptime_type.max_points = 10
            self.uptime_type.save()

        # Clean up any existing uptime contributions and multipliers for clean test state
        Contribution.objects.filter(contribution_type=self.uptime_type).delete()
        GlobalLeaderboardMultiplier.objects.filter(contribution_type=self.uptime_type).delete()

        # Create multipliers at midnight to match contribution dates
        # Contributions are created at midnight, so multipliers must also be at midnight
        # to avoid time-of-day boundary issues
        def date_to_midnight(days_ago):
            """Convert days ago to a datetime at midnight UTC."""
            date = (self.now - timedelta(days=days_ago)).date()
            return datetime.combine(date, datetime.min.time(), tzinfo=pytz.UTC)

        # Period 1: 90 days ago to 30 days ago (2.0x)
        self.multiplier1 = GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.uptime_type,
            multiplier_value=Decimal('2.0'),
            valid_from=date_to_midnight(90),
            description='Early multiplier'
        )

        # Period 2: 30 days ago to now (1.0x)
        self.multiplier2 = GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.uptime_type,
            multiplier_value=Decimal('1.0'),
            valid_from=date_to_midnight(30),
            description='Current multiplier'
        )

        # Validator 1: Has existing uptime from 60 days ago
        self.user1 = User.objects.create_user(
            email='validator1@test.com',
            password='test',
            name='Validator One',
            visible=True
        )
        self.validator1 = Validator.objects.create(user=self.user1)
        # Set creation date to 60 days ago
        self.validator1.created_at = self.now - timedelta(days=60)
        self.validator1.save()
        # Create initial uptime 60 days ago
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.uptime_type,
            points=1,
            contribution_date=self.now - timedelta(days=60),
            multiplier_at_creation=Decimal('2.0'),
            frozen_global_points=2
        )

        # Validator 2: Has uptime from 20 days ago
        self.user2 = User.objects.create_user(
            email='validator2@test.com',
            password='test',
            name='Validator Two',
            visible=True
        )
        self.validator2 = Validator.objects.create(user=self.user2)
        self.validator2.created_at = self.now - timedelta(days=40)
        self.validator2.save()
        # Create initial uptime 20 days ago
        Contribution.objects.create(
            user=self.user2,
            contribution_type=self.uptime_type,
            points=1,
            contribution_date=self.now - timedelta(days=20),
            multiplier_at_creation=Decimal('1.0'),
            frozen_global_points=1
        )

        # Validator 3: New validator with no uptime yet
        self.user3 = User.objects.create_user(
            email='validator3@test.com',
            password='test',
            name='Validator Three',
            visible=True
        )
        self.validator3 = Validator.objects.create(user=self.user3)
        self.validator3.created_at = self.now - timedelta(days=5)
        self.validator3.save()
        # No uptime contributions yet

    def test_add_daily_uptime_correctness_and_performance(self):
        """
        Comprehensive test that validates:
        1. Correct date ranges for validators with existing uptime
        2. Correct date ranges for new validators
        3. Correct multiplier application
        4. Idempotency (no duplicates on re-run)
        5. Acceptable performance
        """
        # === PART 1: First Run - Generate Missing Uptime ===
        start_time = time.time()
        out = StringIO()
        call_command('add_daily_uptime', stdout=out, verbosity=0)
        first_run_time = time.time() - start_time

        # === VALIDATE VALIDATOR 1 (has existing uptime from 60 days ago) ===
        # Should have uptime from 60 days ago to today (61 days total)
        user1_uptimes = Contribution.objects.filter(
            user=self.user1,
            contribution_type=self.uptime_type
        ).order_by('contribution_date')

        # Check count: 61 days (60 days ago + today, inclusive)
        self.assertEqual(
            user1_uptimes.count(),
            61,
            f"Validator 1 should have 61 days of uptime, got {user1_uptimes.count()}"
        )

        # Check date range is continuous (no gaps)
        dates1 = [u.contribution_date.date() for u in user1_uptimes]
        expected_start1 = self.today - timedelta(days=60)
        for i, date in enumerate(dates1):
            expected_date = expected_start1 + timedelta(days=i)
            self.assertEqual(
                date,
                expected_date,
                f"Validator 1: Gap or wrong date at position {i}"
            )

        # Check multipliers are correct based on date
        # Use midnight of 30 days ago as the cutoff (same as multiplier valid_from)
        cutoff_date = (self.now - timedelta(days=30)).date()
        multiplier_cutoff = datetime.combine(cutoff_date, datetime.min.time(), tzinfo=pytz.UTC)

        for uptime in user1_uptimes:
            date = uptime.contribution_date
            # Contributions before 30 days ago (midnight) should have 2.0x
            if date < multiplier_cutoff:
                self.assertEqual(
                    uptime.multiplier_at_creation,
                    Decimal('2.0'),
                    f"Expected 2.0x multiplier for {date.date()}"
                )
                self.assertEqual(uptime.frozen_global_points, 2)
            else:
                # After 30 days ago should have 1.0x
                self.assertEqual(
                    uptime.multiplier_at_creation,
                    Decimal('1.0'),
                    f"Expected 1.0x multiplier for {date.date()}"
                )
                self.assertEqual(uptime.frozen_global_points, 1)

        # === VALIDATE VALIDATOR 2 (has uptime from 20 days ago) ===
        # Should have uptime from 20 days ago to today (21 days total)
        user2_uptimes = Contribution.objects.filter(
            user=self.user2,
            contribution_type=self.uptime_type
        ).order_by('contribution_date')

        self.assertEqual(
            user2_uptimes.count(),
            21,
            f"Validator 2 should have 21 days of uptime, got {user2_uptimes.count()}"
        )

        # All should have 1.0x multiplier (within last 30 days)
        for uptime in user2_uptimes:
            self.assertEqual(uptime.multiplier_at_creation, Decimal('1.0'))
            self.assertEqual(uptime.frozen_global_points, 1)

        # === VALIDATE VALIDATOR 3 (new validator, no prior uptime) ===
        # Should have uptime from creation date (5 days ago) to today (6 days total)
        user3_uptimes = Contribution.objects.filter(
            user=self.user3,
            contribution_type=self.uptime_type
        ).order_by('contribution_date')

        self.assertEqual(
            user3_uptimes.count(),
            6,
            f"Validator 3 should have 6 days of uptime, got {user3_uptimes.count()}"
        )

        # Check continuous dates from creation to today
        dates3 = [u.contribution_date.date() for u in user3_uptimes]
        expected_start3 = self.today - timedelta(days=5)
        for i, date in enumerate(dates3):
            expected_date = expected_start3 + timedelta(days=i)
            self.assertEqual(date, expected_date)

        # === PART 2: Second Run - Test Idempotency ===
        start_time = time.time()
        call_command('add_daily_uptime', stdout=out, verbosity=0)
        second_run_time = time.time() - start_time

        # Counts should be identical (no new contributions created)
        self.assertEqual(
            Contribution.objects.filter(
                user=self.user1,
                contribution_type=self.uptime_type
            ).count(),
            61,
            "Second run should not create duplicates for Validator 1"
        )

        self.assertEqual(
            Contribution.objects.filter(
                user=self.user2,
                contribution_type=self.uptime_type
            ).count(),
            21,
            "Second run should not create duplicates for Validator 2"
        )

        self.assertEqual(
            Contribution.objects.filter(
                user=self.user3,
                contribution_type=self.uptime_type
            ).count(),
            6,
            "Second run should not create duplicates for Validator 3"
        )

        # === PART 3: Performance Validation ===
        # For 3 validators with ~88 total days of history, should complete quickly
        self.assertLess(
            first_run_time,
            5.0,
            f"First run took {first_run_time:.2f}s, should complete in under 5 seconds"
        )

        self.assertLess(
            second_run_time,
            2.0,
            f"Second run took {second_run_time:.2f}s, should be very fast (no new data)"
        )

        # === PART 4: Total Points Validation ===
        # Validator 1: 30 days at 2.0x (60 points) + 31 days at 1.0x (31 points) = 91 points
        user1_total = Contribution.objects.filter(
            user=self.user1,
            contribution_type=self.uptime_type
        ).aggregate(total=models.Sum('frozen_global_points'))['total']

        self.assertEqual(
            user1_total,
            91,
            f"Validator 1 should have 91 total points, got {user1_total}"
        )

        # Validator 2: 21 days at 1.0x = 21 points
        user2_total = Contribution.objects.filter(
            user=self.user2,
            contribution_type=self.uptime_type
        ).aggregate(total=models.Sum('frozen_global_points'))['total']

        self.assertEqual(
            user2_total,
            21,
            f"Validator 2 should have 21 total points, got {user2_total}"
        )

        # Validator 3: 6 days at 1.0x = 6 points
        user3_total = Contribution.objects.filter(
            user=self.user3,
            contribution_type=self.uptime_type
        ).aggregate(total=models.Sum('frozen_global_points'))['total']

        self.assertEqual(
            user3_total,
            6,
            f"Validator 3 should have 6 total points, got {user3_total}"
        )

        # === SUMMARY OUTPUT ===
        print(f"\n{'='*60}")
        print("ADD_DAILY_UPTIME TEST RESULTS")
        print(f"{'='*60}")
        print(f"✓ Validator 1: {user1_uptimes.count()} days, {user1_total} points")
        print(f"✓ Validator 2: {user2_uptimes.count()} days, {user2_total} points")
        print(f"✓ Validator 3: {user3_uptimes.count()} days, {user3_total} points")
        print(f"✓ First run: {first_run_time:.3f}s")
        print(f"✓ Second run (idempotent): {second_run_time:.3f}s")
        print(f"✓ All date ranges correct")
        print(f"✓ All multipliers correct")
        print(f"✓ No duplicates on re-run")
        print(f"{'='*60}\n")
