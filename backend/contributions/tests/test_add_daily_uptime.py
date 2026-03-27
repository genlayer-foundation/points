from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from io import StringIO
from decimal import Decimal

from contributions.models import Contribution, ContributionType, Category
from leaderboard.models import LeaderboardEntry, GlobalLeaderboardMultiplier
from validators.models import Validator, ValidatorWallet, ValidatorWalletStatusSnapshot

User = get_user_model()


class AddDailyUptimeCommandTest(TestCase):
    """Test the add_daily_uptime management command."""

    def setUp(self):
        """Set up test data with proper Validator/Wallet/Snapshot fixtures."""
        # Get or create validator category (may exist from migrations)
        self.validator_category, _ = Category.objects.get_or_create(
            slug='validator',
            defaults={
                'name': 'Validator',
                'profile_model': 'validators.Validator'
            }
        )

        # Get or create uptime contribution type
        self.uptime_type, _ = ContributionType.objects.get_or_create(
            name='Uptime',
            defaults={
                'slug': 'uptime',
                'description': 'Daily validator uptime',
                'category': self.validator_category,
                'min_points': 1,
                'max_points': 10
            }
        )
        # Ensure the type has proper settings for tests
        self.uptime_type.min_points = 1
        self.uptime_type.max_points = 10
        self.uptime_type.category = self.validator_category
        self.uptime_type.save()

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
        self.user_no_validator = User.objects.create_user(
            email='novalidator@test.com',
            password='testpass123',
            name='Not a Validator',
            address='0x9999999999999999999999999999999999999999'
        )

        # Create Validator profiles
        self.validator1 = Validator.objects.create(user=self.user1)
        self.validator2 = Validator.objects.create(user=self.user2)

        # Create wallets on asimov for validator1
        self.wallet1_asimov = ValidatorWallet.objects.create(
            address='0xwallet1asimov',
            network='asimov',
            status='active',
            operator=self.validator1,
            operator_address='0x1234567890123456789012345678901234567890'
        )

        # Create wallets on bradbury for validator1
        self.wallet1_bradbury = ValidatorWallet.objects.create(
            address='0xwallet1bradbury',
            network='bradbury',
            status='active',
            operator=self.validator1,
            operator_address='0x1234567890123456789012345678901234567890'
        )

        # Create wallet on asimov for validator2
        self.wallet2_asimov = ValidatorWallet.objects.create(
            address='0xwallet2asimov',
            network='asimov',
            status='active',
            operator=self.validator2,
            operator_address='0xabcdefabcdefabcdefabcdefabcdefabcdefabcd'
        )

        # Create active snapshots for today
        today = timezone.now().date()
        ValidatorWalletStatusSnapshot.objects.create(
            wallet=self.wallet1_asimov, date=today, status='active'
        )
        ValidatorWalletStatusSnapshot.objects.create(
            wallet=self.wallet1_bradbury, date=today, status='active'
        )
        ValidatorWalletStatusSnapshot.objects.create(
            wallet=self.wallet2_asimov, date=today, status='active'
        )

    def test_creates_uptime_for_active_validator(self):
        """Active validator with snapshots gets 1 contribution per network."""
        call_command('add_daily_uptime', verbosity=0)

        # Validator1 has wallets on both networks → 2 contributions
        contributions = Contribution.objects.filter(
            user=self.user1, contribution_type=self.uptime_type
        )
        self.assertEqual(contributions.count(), 2)

        # Check both networks are present
        notes = set(contributions.values_list('notes', flat=True))
        today = timezone.now().date()
        self.assertIn(f'Auto-generated daily uptime for {today} (asimov)', notes)
        self.assertIn(f'Auto-generated daily uptime for {today} (bradbury)', notes)

    def test_skips_inactive_validator(self):
        """Validator with only inactive snapshots gets no contributions."""
        # Change all snapshots to inactive
        ValidatorWalletStatusSnapshot.objects.filter(
            wallet=self.wallet2_asimov
        ).update(status='inactive')

        call_command('add_daily_uptime', verbosity=0)

        contributions = Contribution.objects.filter(
            user=self.user2, contribution_type=self.uptime_type
        )
        self.assertEqual(contributions.count(), 0)

    def test_no_duplicate_on_rerun(self):
        """Running the command twice doesn't create duplicate contributions."""
        call_command('add_daily_uptime', verbosity=0)
        first_count = Contribution.objects.filter(contribution_type=self.uptime_type).count()

        call_command('add_daily_uptime', verbosity=0)
        second_count = Contribution.objects.filter(contribution_type=self.uptime_type).count()

        self.assertEqual(first_count, second_count)

    def test_date_range_backfill(self):
        """--start-date and --end-date create contributions for each date in range."""
        today = timezone.now().date()
        start = today - timedelta(days=2)
        end = today

        # Create snapshots for past dates too
        for d in [start, start + timedelta(days=1)]:
            ValidatorWalletStatusSnapshot.objects.create(
                wallet=self.wallet1_asimov, date=d, status='active'
            )

        call_command(
            'add_daily_uptime',
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            verbosity=0
        )

        # Validator1 has asimov wallet → 3 days × 1 contribution (asimov only for date range)
        # Plus bradbury for dates where snapshots exist (only today)
        asimov_contributions = Contribution.objects.filter(
            user=self.user1,
            contribution_type=self.uptime_type,
            notes__contains='(asimov)'
        )
        self.assertEqual(asimov_contributions.count(), 3)

    def test_single_date_param(self):
        """--date processes only that specific date."""
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        # Create snapshot for yesterday
        ValidatorWalletStatusSnapshot.objects.create(
            wallet=self.wallet1_asimov, date=yesterday, status='active'
        )

        call_command('add_daily_uptime', date=yesterday.isoformat(), verbosity=0)

        # Should create contributions for yesterday only
        contributions = Contribution.objects.filter(
            user=self.user1,
            contribution_type=self.uptime_type,
            contribution_date__date=yesterday,
        )
        self.assertTrue(contributions.exists())

        # Should NOT create contributions for today
        today_contributions = Contribution.objects.filter(
            user=self.user1,
            contribution_type=self.uptime_type,
            contribution_date__date=today,
        )
        self.assertFalse(today_contributions.exists())

    def test_lookback_window(self):
        """Snapshot 3 days ago but not today still qualifies within 7-day window."""
        today = timezone.now().date()
        three_days_ago = today - timedelta(days=3)

        # Remove today's snapshots for wallet2
        ValidatorWalletStatusSnapshot.objects.filter(wallet=self.wallet2_asimov).delete()

        # Add snapshot from 3 days ago
        ValidatorWalletStatusSnapshot.objects.create(
            wallet=self.wallet2_asimov, date=three_days_ago, status='active'
        )

        call_command('add_daily_uptime', verbosity=0)

        contributions = Contribution.objects.filter(
            user=self.user2, contribution_type=self.uptime_type
        )
        self.assertEqual(contributions.count(), 1)

    def test_snapshot_gap_fallback(self):
        """No snapshots for target date but wallet status is active → uses fallback."""
        today = timezone.now().date()

        # Remove ALL snapshots for wallet2 (simulating sync failure)
        ValidatorWalletStatusSnapshot.objects.filter(wallet=self.wallet2_asimov).delete()

        # Wallet status is still 'active' in the model
        self.assertEqual(self.wallet2_asimov.status, 'active')

        out = StringIO()
        call_command('add_daily_uptime', verbose=True, stdout=out)

        contributions = Contribution.objects.filter(
            user=self.user2, contribution_type=self.uptime_type
        )
        self.assertEqual(contributions.count(), 1)

        # Check that fallback warning was logged
        output = out.getvalue()
        self.assertIn('Using current wallet status as fallback', output)

    def test_multi_network(self):
        """Validator with wallets on both networks gets 2 contributions per day."""
        call_command('add_daily_uptime', verbosity=0)

        contributions = Contribution.objects.filter(
            user=self.user1, contribution_type=self.uptime_type
        )
        self.assertEqual(contributions.count(), 2)

        networks_in_notes = [c.notes for c in contributions]
        self.assertTrue(any('(asimov)' in n for n in networks_in_notes))
        self.assertTrue(any('(bradbury)' in n for n in networks_in_notes))

    def test_dry_run(self):
        """Dry run mode doesn't create any contributions."""
        initial_count = Contribution.objects.count()

        out = StringIO()
        call_command('add_daily_uptime', dry_run=True, stdout=out)

        self.assertEqual(Contribution.objects.count(), initial_count)
        self.assertIn('DRY RUN', out.getvalue())

    def test_force_mode(self):
        """--force uses 1.0 multiplier when none exists."""
        # Delete all multipliers
        GlobalLeaderboardMultiplier.objects.all().delete()

        out = StringIO()
        call_command('add_daily_uptime', force=True, stdout=out)

        # Should create contributions with multiplier 1.0
        contributions = Contribution.objects.filter(
            contribution_type=self.uptime_type,
            multiplier_at_creation=Decimal('1.0')
        )
        self.assertGreater(contributions.count(), 0)
        self.assertIn('using default of 1.0', out.getvalue())

    def test_no_multiplier_without_force(self):
        """Without --force, missing multiplier raises CommandError."""
        GlobalLeaderboardMultiplier.objects.all().delete()

        with self.assertRaises(CommandError):
            call_command('add_daily_uptime', verbosity=0)

        contributions = Contribution.objects.filter(contribution_type=self.uptime_type)
        self.assertEqual(contributions.count(), 0)

    def test_leaderboard_updated(self):
        """Contributions update leaderboard entries."""
        call_command('add_daily_uptime', verbosity=0)

        # Validator1 should have a leaderboard entry
        entries = LeaderboardEntry.objects.filter(user=self.user1, type='validator')
        self.assertTrue(entries.exists())
        self.assertGreater(entries.first().total_points, 0)

    def test_points_calculation(self):
        """Frozen global points = points × multiplier."""
        call_command('add_daily_uptime', points=3, verbosity=0)

        contribution = Contribution.objects.filter(
            user=self.user1, contribution_type=self.uptime_type
        ).first()

        self.assertEqual(contribution.points, 3)
        self.assertEqual(contribution.frozen_global_points, 6)  # 3 × 2.0
        self.assertEqual(contribution.multiplier_at_creation, Decimal('2.0'))

    def test_network_filter(self):
        """--network flag limits processing to one network."""
        call_command('add_daily_uptime', network='asimov', verbosity=0)

        # Only asimov contributions should exist
        contributions = Contribution.objects.filter(
            user=self.user1, contribution_type=self.uptime_type
        )
        self.assertEqual(contributions.count(), 1)
        self.assertIn('(asimov)', contributions.first().notes)

    def test_user_without_validator_skipped(self):
        """Users without a Validator profile get no contributions."""
        call_command('add_daily_uptime', verbosity=0)

        contributions = Contribution.objects.filter(
            user=self.user_no_validator, contribution_type=self.uptime_type
        )
        self.assertEqual(contributions.count(), 0)

    def test_output_summary(self):
        """Command outputs a summary with stats."""
        out = StringIO()
        call_command('add_daily_uptime', stdout=out)

        output = out.getvalue()
        self.assertIn('Daily uptime generation completed!', output)
        self.assertIn('Validators with wallets:', output)
        self.assertIn('New uptime contributions added:', output)
