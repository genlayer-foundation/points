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
        # Get or create categories (they might exist from migrations)
        self.validator_category, _ = Category.objects.get_or_create(
            slug='validator',
            defaults={
                'name': 'Validator',
                'description': 'Validator contributions'
            }
        )
        self.builder_category, _ = Category.objects.get_or_create(
            slug='builder',
            defaults={
                'name': 'Builder',
                'description': 'Builder contributions'
            }
        )
        
        # Get or create contribution types (some might exist from migrations)
        self.waitlist_type, _ = ContributionType.objects.get_or_create(
            slug='validator-waitlist',
            defaults={
                'name': 'Validator Waitlist',
                'description': 'Join the validator waitlist',
                'category': self.validator_category,
                'min_points': 1,
                'max_points': 1
            }
        )
        
        self.validator_type, _ = ContributionType.objects.get_or_create(
            slug='validator',
            defaults={
                'name': 'Validator',
                'description': 'Become a validator',
                'category': self.validator_category,
                'min_points': 1,
                'max_points': 1
            }
        )
        
        self.node_running_type, _ = ContributionType.objects.get_or_create(
            slug='node-running',
            defaults={
                'name': 'Node Running',
                'description': 'Running a validator node',
                'category': self.validator_category,
                'min_points': 10,
                'max_points': 100
            }
        )
        
        self.builder_type, _ = ContributionType.objects.get_or_create(
            slug='code-contribution',
            defaults={
                'name': 'Code Contribution',
                'description': 'Contributing code',
                'category': self.builder_category,
                'min_points': 5,
                'max_points': 50
            }
        )
        
        # Create users
        self.user1 = User.objects.create(
            email='user1@test.com',
            name='User One',
            address='0x1234567890123456789012345678901234567890',
            visible=True
        )
        
        self.user2 = User.objects.create(
            email='user2@test.com',
            name='User Two',
            address='0x2345678901234567890123456789012345678901',
            visible=True
        )
        
        self.user3 = User.objects.create(
            email='user3@test.com',
            name='User Three',
            address='0x3456789012345678901234567890123456789012',
            visible=False  # Non-visible user
        )
        
        # Create global multipliers for all contribution types
        self.multiplier1, _ = GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=self.node_running_type,
            defaults={
                'multiplier_value': Decimal('2.0'),
                'valid_from': timezone.now() - timezone.timedelta(days=30),
                'description': 'Double points for node running'
            }
        )
        
        self.multiplier2, _ = GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=self.builder_type,
            defaults={
                'multiplier_value': Decimal('1.5'),
                'valid_from': timezone.now() - timezone.timedelta(days=20),
                'description': '1.5x points for builders'
            }
        )
        
        # Add multipliers for waitlist and validator types too
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=self.waitlist_type,
            defaults={
                'multiplier_value': Decimal('1.0'),
                'valid_from': timezone.now() - timezone.timedelta(days=30),
                'description': 'Standard points for waitlist'
            }
        )
        
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=self.validator_type,
            defaults={
                'multiplier_value': Decimal('1.0'),
                'valid_from': timezone.now() - timezone.timedelta(days=30),
                'description': 'Standard points for validator'
            }
        )
    
    def test_recalculate_all_leaderboards_empty(self):
        """Test recalculation with no contributions."""
        result = recalculate_all_leaderboards()
        self.assertIn('0 users', result)
        self.assertEqual(LeaderboardEntry.objects.count(), 0)
    
    def test_recalculate_all_leaderboards_with_waitlist(self):
        """Test recalculation with waitlist users."""
        # Create waitlist contributions
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.waitlist_type,
            points=1,
            frozen_global_points=1,
            contribution_date=timezone.now() - timezone.timedelta(days=10)
        )
        
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.node_running_type,
            points=50,
            frozen_global_points=100,  # 50 * 2.0 multiplier
            contribution_date=timezone.now() - timezone.timedelta(days=5)
        )
        
        # Recalculate
        result = recalculate_all_leaderboards()
        
        # Check result
        self.assertIn('1 users', result)
        self.assertIn('4 leaderboards', result)
        
        # Check user is on waitlist leaderboard
        waitlist_entry = LeaderboardEntry.objects.filter(
            user=self.user1,
            type='validator-waitlist'
        ).first()
        self.assertIsNotNone(waitlist_entry)
        self.assertEqual(waitlist_entry.total_points, 101)  # 1 + 100
        self.assertEqual(waitlist_entry.rank, 1)
    
    def test_recalculate_with_graduation(self):
        """Test recalculation when user graduates from waitlist to validator."""
        # User starts on waitlist
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.waitlist_type,
            points=1,
            frozen_global_points=1,
            contribution_date=timezone.now() - timezone.timedelta(days=10)
        )
        
        # Add some validator category contributions
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.node_running_type,
            points=50,
            frozen_global_points=100,
            contribution_date=timezone.now() - timezone.timedelta(days=5)
        )
        
        # First recalculation - user should be on waitlist
        recalculate_all_leaderboards()
        
        self.assertTrue(
            LeaderboardEntry.objects.filter(
                user=self.user1,
                type='validator-waitlist'
            ).exists()
        )
        self.assertFalse(
            LeaderboardEntry.objects.filter(
                user=self.user1,
                type='validator'
            ).exists()
        )
        
        # User graduates to validator
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.validator_type,
            points=1,
            frozen_global_points=200,  # High multiplier for testing
            contribution_date=timezone.now()
        )
        
        # Second recalculation - user should move to validator and graduation
        recalculate_all_leaderboards()
        
        # Check user is NOT on waitlist anymore
        self.assertFalse(
            LeaderboardEntry.objects.filter(
                user=self.user1,
                type='validator-waitlist'
            ).exists()
        )
        
        # Check user IS on validator leaderboard
        validator_entry = LeaderboardEntry.objects.filter(
            user=self.user1,
            type='validator'
        ).first()
        self.assertIsNotNone(validator_entry)
        self.assertEqual(validator_entry.total_points, 301)  # 1 + 100 + 200
        
        # Check user IS on graduation leaderboard with frozen points
        grad_entry = LeaderboardEntry.objects.filter(
            user=self.user1,
            type='validator-waitlist-graduation'
        ).first()
        self.assertIsNotNone(grad_entry)
        self.assertEqual(grad_entry.total_points, 101)  # Points before graduation
        self.assertIsNotNone(grad_entry.graduation_date)
    
    def test_recalculate_with_multiple_users(self):
        """Test recalculation with multiple users in different states."""
        # User 1: On waitlist
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.waitlist_type,
            points=1,
            frozen_global_points=1,
            contribution_date=timezone.now() - timezone.timedelta(days=10)
        )
        
        # User 2: Graduated validator
        Contribution.objects.create(
            user=self.user2,
            contribution_type=self.waitlist_type,
            points=1,
            frozen_global_points=1,
            contribution_date=timezone.now() - timezone.timedelta(days=20)
        )
        Contribution.objects.create(
            user=self.user2,
            contribution_type=self.node_running_type,
            points=30,
            frozen_global_points=60,
            contribution_date=timezone.now() - timezone.timedelta(days=15)
        )
        Contribution.objects.create(
            user=self.user2,
            contribution_type=self.validator_type,
            points=1,
            frozen_global_points=1,
            contribution_date=timezone.now() - timezone.timedelta(days=5)
        )
        
        # User 3: Non-visible (should not have ranks)
        Contribution.objects.create(
            user=self.user3,
            contribution_type=self.waitlist_type,
            points=1,
            frozen_global_points=1,
            contribution_date=timezone.now() - timezone.timedelta(days=10)
        )
        
        # Recalculate
        result = recalculate_all_leaderboards()
        
        # Check counts
        self.assertIn('3 users', result)
        
        # Check User 1 is on waitlist
        self.assertTrue(
            LeaderboardEntry.objects.filter(
                user=self.user1,
                type='validator-waitlist',
                rank=1  # Should be ranked
            ).exists()
        )
        
        # Check User 2 is on validator and graduation
        self.assertTrue(
            LeaderboardEntry.objects.filter(
                user=self.user2,
                type='validator',
                rank=1
            ).exists()
        )
        self.assertTrue(
            LeaderboardEntry.objects.filter(
                user=self.user2,
                type='validator-waitlist-graduation',
                rank=1
            ).exists()
        )
        
        # Check User 3 has entries but no ranks (not visible)
        user3_entry = LeaderboardEntry.objects.filter(
            user=self.user3,
            type='validator-waitlist'
        ).first()
        self.assertIsNotNone(user3_entry)
        self.assertIsNone(user3_entry.rank)  # No rank for non-visible users
    
    def test_recalculate_with_builder(self):
        """Test recalculation with builder contributions."""
        # Create builder contributions
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.builder_type,
            points=20,
            frozen_global_points=30,  # 20 * 1.5
            contribution_date=timezone.now() - timezone.timedelta(days=5)
        )
        
        # Recalculate
        recalculate_all_leaderboards()
        
        # Check user is on builder leaderboard
        builder_entry = LeaderboardEntry.objects.filter(
            user=self.user1,
            type='builder'
        ).first()
        self.assertIsNotNone(builder_entry)
        self.assertEqual(builder_entry.total_points, 30)
        self.assertEqual(builder_entry.rank, 1)
    
    def test_update_leaderboard_command(self):
        """Test the update_leaderboard management command."""
        # Create contributions
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.node_running_type,
            points=50,
            frozen_global_points=50,  # Will be updated to 100
            multiplier_at_creation=1.0,  # Will be updated to 2.0
            contribution_date=timezone.now() - timezone.timedelta(days=5)
        )
        
        # Run the command
        out = StringIO()
        call_command('update_leaderboard', stdout=out)
        output = out.getvalue()
        
        # Check output
        self.assertIn('Starting leaderboard update', output)
        self.assertIn('Processing 1 contributions', output)
        self.assertIn('Updated 1 contributions', output)
        self.assertIn('Recalculated 1 users', output)
        self.assertIn('completed successfully', output)
        
        # Check contribution was updated
        contribution = Contribution.objects.get(user=self.user1)
        self.assertEqual(contribution.multiplier_at_creation, Decimal('2.0'))
        self.assertEqual(contribution.frozen_global_points, 100)
        
        # Check leaderboard entry exists
        self.assertTrue(
            LeaderboardEntry.objects.filter(
                user=self.user1,
                total_points=100
            ).exists()
        )
    
    def test_leaderboard_config_integrity(self):
        """Test that LEADERBOARD_CONFIG is properly configured."""
        # Check all required keys exist
        for key, config in LEADERBOARD_CONFIG.items():
            self.assertIn('name', config)
            self.assertIn('participants', config)
            self.assertIn('points_calculator', config)
            self.assertIn('ranking_order', config)
            
            # Check callables
            self.assertTrue(callable(config['participants']))
            self.assertTrue(callable(config['points_calculator']))
            
            # Check ranking order is valid
            self.assertIn(config['ranking_order'], ['-total_points', '-graduation_date'])
    
    def test_frozen_graduation_points(self):
        """Test that graduation points are properly frozen."""
        # User on waitlist with some points
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.waitlist_type,
            points=1,
            frozen_global_points=1,
            contribution_date=timezone.now() - timezone.timedelta(days=10)
        )
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.node_running_type,
            points=50,
            frozen_global_points=100,
            contribution_date=timezone.now() - timezone.timedelta(days=5)
        )
        
        # Recalculate
        recalculate_all_leaderboards()
        
        # Graduate user
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.validator_type,
            points=1,
            frozen_global_points=1,
            contribution_date=timezone.now() - timezone.timedelta(days=2)
        )
        
        # Recalculate after graduation
        recalculate_all_leaderboards()
        
        # Check graduation entry has frozen points
        grad_entry = LeaderboardEntry.objects.get(
            user=self.user1,
            type='validator-waitlist-graduation'
        )
        frozen_points = grad_entry.total_points
        
        # Add more contributions after graduation
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.node_running_type,
            points=100,
            frozen_global_points=200,
            contribution_date=timezone.now()
        )
        
        # Recalculate again
        recalculate_all_leaderboards()
        
        # Check graduation points are still frozen
        grad_entry.refresh_from_db()
        self.assertEqual(grad_entry.total_points, frozen_points)
        
        # Check validator points increased
        validator_entry = LeaderboardEntry.objects.get(
            user=self.user1,
            type='validator'
        )
        self.assertEqual(validator_entry.total_points, 302)  # 1 + 100 + 1 + 200