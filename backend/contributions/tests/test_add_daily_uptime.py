from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from io import StringIO
from decimal import Decimal

from contributions.models import Category, Contribution, ContributionType
from leaderboard.models import LeaderboardEntry, GlobalLeaderboardMultiplier, ReferralPoints
from validators.models import Validator, ValidatorWallet, ValidatorWalletStatusSnapshot

User = get_user_model()


class AddDailyUptimeCommandTest(TestCase):
    """Test the add_daily_uptime management command."""
    
    def setUp(self):
        """Set up test data."""
        self.validator_category = Category.objects.create(
            name='Validator',
            slug='validator',
            description='Validator contributions',
        )
        # Create uptime contribution type
        self.uptime_type = ContributionType.objects.create(
            name='Uptime',
            description='Daily validator uptime',
            category=self.validator_category,
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

    def link_active_wallet(self, user, *, network='asimov', address=None, days_ago=0):
        validator, _ = Validator.objects.get_or_create(user=user)
        wallet = ValidatorWallet.objects.create(
            operator=validator,
            address=address or user.address,
            operator_address=user.address,
            network=network,
            status='active',
        )
        ValidatorWalletStatusSnapshot.objects.create(
            wallet=wallet,
            date=timezone.now().date() - timedelta(days=days_ago),
            status='active',
        )
        return wallet
    
    def test_command_creates_daily_uptime_contributions(self):
        """Test that the command creates today's uptime for active wallets."""
        self.link_active_wallet(self.user1)
        
        # Run the command
        out = StringIO()
        call_command('add_daily_uptime', stdout=out, verbosity=2)
        
        contributions = Contribution.objects.filter(
            user=self.user1,
            contribution_type=self.uptime_type
        )

        self.assertEqual(contributions.count(), 1)
        self.assertIn('(asimov)', contributions.first().notes)
        
        # Verify output
        output = out.getvalue()
        self.assertIn('Daily uptime generation completed!', output)
        self.assertIn('Validators with wallets: 1', output)
    
    def test_leaderboard_updates_correctly(self):
        """Test that the leaderboard is updated with correct total points."""
        self.link_active_wallet(self.user1)
        
        # Run the command
        call_command('add_daily_uptime', verbosity=0)
        
        # Check leaderboard entry
        leaderboard_entry = LeaderboardEntry.objects.get(user=self.user1, type='validator')
        
        self.assertEqual(leaderboard_entry.total_points, 2)
    
    def test_multiple_users_with_uptime(self):
        """Test that multiple users get their uptime updated correctly."""
        self.link_active_wallet(self.user1, network='asimov')
        self.link_active_wallet(
            self.user2,
            network='asimov',
            address='0xabcdefabcdefabcdefabcdefabcdefabcdefabce',
        )
        self.link_active_wallet(
            self.user2,
            network='bradbury',
            address='0xabcdefabcdefabcdefabcdefabcdefabcdefabcf',
        )
        
        # Run the command
        call_command('add_daily_uptime', verbosity=0)
        
        # Check both users have leaderboard entries
        entry1 = LeaderboardEntry.objects.get(user=self.user1, type='validator')
        entry2 = LeaderboardEntry.objects.get(user=self.user2, type='validator')
        
        self.assertEqual(entry1.total_points, 2)
        self.assertGreater(entry2.total_points, entry1.total_points)
    
    def test_no_duplicate_contributions(self):
        """Test that running the command multiple times doesn't create duplicates."""
        self.link_active_wallet(self.user1)
        
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
        self.link_active_wallet(self.user1)
        
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
        self.link_active_wallet(self.user1)
        
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

    def test_force_mode_updates_referrer_points(self):
        """Force-created uptime still updates referral points despite bypassing signals."""
        referrer = User.objects.create_user(
            email='referrer@test.com',
            password='testpass123',
            name='Referrer',
            address='0x7777777777777777777777777777777777777777'
        )
        self.user1.referred_by = referrer
        self.user1.save(update_fields=['referred_by'])
        self.link_active_wallet(self.user1)
        GlobalLeaderboardMultiplier.objects.all().delete()

        call_command('add_daily_uptime', force=True, points=10, verbosity=0)

        referral_points = ReferralPoints.objects.get(user=referrer)
        self.assertEqual(referral_points.validator_points, 1)
        self.assertEqual(referral_points.builder_points, 0)
    
    def test_custom_points_value(self):
        """Test that custom points value is applied correctly."""
        self.link_active_wallet(self.user1)
        
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
