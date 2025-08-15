from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
import pytz
from io import StringIO
from decimal import Decimal

from contributions.models import Contribution, ContributionType
from leaderboard.models import LeaderboardEntry, GlobalLeaderboardMultiplier

User = get_user_model()


class AddDailyUptimeCommandTest(TestCase):
    """Test the add_daily_uptime management command."""
    
    def setUp(self):
        """Set up test data."""
        # Create uptime contribution type
        self.uptime_type = ContributionType.objects.create(
            name='Uptime',
            description='Daily validator uptime',
            min_points=1,
            max_points=10
        )
        
        # Create a multiplier for uptime
        self.multiplier = GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.uptime_type,
            multiplier_value=Decimal('2.0'),
            valid_from=timezone.now() - timedelta(days=30),
            description='Default uptime multiplier'
        )
        
        # Create test users
        self.user1 = User.objects.create_user(
            email='validator1@test.com',
            password='testpass123',
            name='Validator 1',
            address='0x1234567890123456789012345678901234567890'
        )
        
        self.user2 = User.objects.create_user(
            email='validator2@test.com',
            password='testpass123',
            name='Validator 2',
            address='0xabcdefabcdefabcdefabcdefabcdefabcdefabcd'
        )
        
        self.user_without_uptime = User.objects.create_user(
            email='novalidator@test.com',
            password='testpass123',
            name='Not a Validator',
            address='0x9999999999999999999999999999999999999999'
        )
    
    def test_command_creates_daily_uptime_contributions(self):
        """Test that the command creates daily uptime contributions from first uptime to today."""
        # Create an initial uptime contribution 5 days ago
        five_days_ago = timezone.now() - timedelta(days=5)
        initial_contribution = Contribution.objects.create(
            user=self.user1,
            contribution_type=self.uptime_type,
            points=1,
            contribution_date=five_days_ago,
            multiplier_at_creation=Decimal('2.0'),
            frozen_global_points=2
        )
        
        # Run the command
        out = StringIO()
        call_command('add_daily_uptime', stdout=out, verbosity=2)
        
        # Check that contributions were created for each day
        contributions = Contribution.objects.filter(
            user=self.user1,
            contribution_type=self.uptime_type
        ).count()
        
        # Should have 6 contributions (initial + 5 days up to today)
        self.assertGreaterEqual(contributions, 6)
        
        # Verify output
        output = out.getvalue()
        self.assertIn('Daily uptime generation completed!', output)
        self.assertIn('Users with uptime: 1', output)
    
    def test_leaderboard_updates_correctly(self):
        """Test that the leaderboard is updated with correct total points."""
        # Create initial uptime 3 days ago
        three_days_ago = timezone.now() - timedelta(days=3)
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.uptime_type,
            points=1,
            contribution_date=three_days_ago,
            multiplier_at_creation=Decimal('2.0'),
            frozen_global_points=2
        )
        
        # Run the command
        call_command('add_daily_uptime', verbosity=0)
        
        # Check leaderboard entry
        leaderboard_entry = LeaderboardEntry.objects.get(user=self.user1)
        
        # Should have 4 days worth of points (3 days + today) * 2 points each = 8 points
        self.assertGreaterEqual(leaderboard_entry.total_points, 8)
    
    def test_multiple_users_with_uptime(self):
        """Test that multiple users get their uptime updated correctly."""
        # Create initial uptimes for both users
        two_days_ago = timezone.now() - timedelta(days=2)
        
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.uptime_type,
            points=1,
            contribution_date=two_days_ago,
            multiplier_at_creation=Decimal('2.0'),
            frozen_global_points=2
        )
        
        Contribution.objects.create(
            user=self.user2,
            contribution_type=self.uptime_type,
            points=1,
            contribution_date=two_days_ago - timedelta(days=1),  # User2 started earlier
            multiplier_at_creation=Decimal('2.0'),
            frozen_global_points=2
        )
        
        # Run the command
        call_command('add_daily_uptime', verbosity=0)
        
        # Check both users have leaderboard entries
        entry1 = LeaderboardEntry.objects.get(user=self.user1)
        entry2 = LeaderboardEntry.objects.get(user=self.user2)
        
        # User1 should have at least 3 days of uptime (2 days ago + 1 day + today)
        self.assertGreaterEqual(entry1.total_points, 6)
        
        # User2 should have more points since they started earlier
        self.assertGreater(entry2.total_points, entry1.total_points)
    
    def test_no_duplicate_contributions(self):
        """Test that running the command multiple times doesn't create duplicates."""
        # Create initial uptime
        yesterday = timezone.now() - timedelta(days=1)
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.uptime_type,
            points=1,
            contribution_date=yesterday,
            multiplier_at_creation=Decimal('2.0'),
            frozen_global_points=2
        )
        
        # Run the command twice
        call_command('add_daily_uptime', verbosity=0)
        first_count = Contribution.objects.filter(
            user=self.user1,
            contribution_type=self.uptime_type
        ).count()
        
        call_command('add_daily_uptime', verbosity=0)
        second_count = Contribution.objects.filter(
            user=self.user1,
            contribution_type=self.uptime_type
        ).count()
        
        # Count should be the same
        self.assertEqual(first_count, second_count)
    
    def test_dry_run_mode(self):
        """Test that dry run mode doesn't create any contributions."""
        # Create initial uptime
        yesterday = timezone.now() - timedelta(days=1)
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.uptime_type,
            points=1,
            contribution_date=yesterday,
            multiplier_at_creation=Decimal('2.0'),
            frozen_global_points=2
        )
        
        initial_count = Contribution.objects.count()
        
        # Run in dry-run mode
        out = StringIO()
        call_command('add_daily_uptime', dry_run=True, stdout=out)
        
        # No new contributions should be created
        self.assertEqual(Contribution.objects.count(), initial_count)
        
        # Check output mentions dry run
        output = out.getvalue()
        self.assertIn('DRY RUN', output)
    
    def test_users_without_uptime_are_skipped(self):
        """Test that users without any uptime contributions are skipped."""
        # Run the command (user_without_uptime has no contributions)
        out = StringIO()
        call_command('add_daily_uptime', stdout=out, verbosity=2)
        
        # Check that no contributions were created for user_without_uptime
        contributions = Contribution.objects.filter(
            user=self.user_without_uptime,
            contribution_type=self.uptime_type
        ).count()
        
        self.assertEqual(contributions, 0)
        
        # Check that no leaderboard entry was created
        self.assertFalse(
            LeaderboardEntry.objects.filter(user=self.user_without_uptime).exists()
        )
    
    def test_force_mode_with_missing_multiplier(self):
        """Test that force mode uses default multiplier when none exists."""
        # Create initial uptime with existing multiplier first
        yesterday = timezone.now() - timedelta(days=1)
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.uptime_type,
            points=1,
            contribution_date=yesterday,
            multiplier_at_creation=Decimal('2.0'),
            frozen_global_points=2
        )
        
        # Now delete the multiplier for future dates
        GlobalLeaderboardMultiplier.objects.all().delete()
        
        # Run with force flag
        out = StringIO()
        call_command('add_daily_uptime', force=True, stdout=out, verbosity=2)
        
        # Check that contributions were created with default multiplier
        new_contributions = Contribution.objects.filter(
            user=self.user1,
            contribution_type=self.uptime_type,
            multiplier_at_creation=Decimal('1.0')
        ).count()
        
        self.assertGreater(new_contributions, 0)
        
        output = out.getvalue()
        self.assertIn('using default of 1.0', output)
    
    def test_custom_points_value(self):
        """Test that custom points value is applied correctly."""
        # Create initial uptime
        yesterday = timezone.now() - timedelta(days=1)
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.uptime_type,
            points=1,
            contribution_date=yesterday,
            multiplier_at_creation=Decimal('2.0'),
            frozen_global_points=2
        )
        
        # Run with custom points value
        call_command('add_daily_uptime', points=5, verbosity=0)
        
        # Check that new contributions have 5 points
        today = timezone.now().date()
        todays_contribution = Contribution.objects.filter(
            user=self.user1,
            contribution_type=self.uptime_type,
            contribution_date__date=today
        ).first()
        
        self.assertIsNotNone(todays_contribution)
        self.assertEqual(todays_contribution.points, 5)
        self.assertEqual(todays_contribution.frozen_global_points, 10)  # 5 * 2.0 multiplier