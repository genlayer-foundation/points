from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from leaderboard.models import (
    LeaderboardEntry, 
    GlobalLeaderboardMultiplier,
    update_all_ranks,
    update_user_leaderboard_entry
)
from contributions.models import Contribution, ContributionType

User = get_user_model()


class LeaderboardEntryTest(TestCase):
    """Test the LeaderboardEntry model and its methods."""
    
    def setUp(self):
        """Set up test data."""
        # Create test users
        self.user1 = User.objects.create_user(
            email='user1@test.com',
            password='testpass123',
            name='User 1',
            address='0x1111111111111111111111111111111111111111'
        )
        
        self.user2 = User.objects.create_user(
            email='user2@test.com',
            password='testpass123',
            name='User 2',
            address='0x2222222222222222222222222222222222222222'
        )
        
        # Create contribution types
        self.uptime_type = ContributionType.objects.create(
            name='Uptime',
            description='Daily validator uptime',
            min_points=1,
            max_points=10
        )
        
        self.blog_type = ContributionType.objects.create(
            name='Blog Post',
            description='Blog post contribution',
            min_points=10,
            max_points=100
        )
        
        # Create multipliers
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.uptime_type,
            multiplier_value=Decimal('2.0'),
            valid_from=timezone.now() - timedelta(days=30)
        )
        
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.blog_type,
            multiplier_value=Decimal('3.0'),
            valid_from=timezone.now() - timedelta(days=30)
        )
    
    def test_update_points_without_ranking(self):
        """Test that update_points_without_ranking correctly updates points without changing ranks."""
        # Create contributions for user1
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.uptime_type,
            points=1,
            frozen_global_points=2,
            multiplier_at_creation=Decimal('2.0'),
            contribution_date=timezone.now()
        )
        
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.blog_type,
            points=10,
            frozen_global_points=30,
            multiplier_at_creation=Decimal('3.0'),
            contribution_date=timezone.now()
        )
        
        # Get leaderboard entry (it was created by the signal)
        entry = LeaderboardEntry.objects.get(user=self.user1)
        
        # Record the initial rank (it should be 1 since it's the only user)
        initial_rank = entry.rank
        
        # Update points without ranking
        total_points = entry.update_points_without_ranking()
        
        # Check that points are correctly calculated (2 + 30 = 32)
        self.assertEqual(total_points, 32)
        self.assertEqual(entry.total_points, 32)
        
        # Rank should remain the same since we didn't update ranks
        entry.refresh_from_db()
        self.assertEqual(entry.rank, initial_rank)
    
    def test_update_points_without_ranking_multiple_users(self):
        """Test batch updating multiple users' points without ranking."""
        # Create contributions for both users
        for i in range(3):
            Contribution.objects.create(
                user=self.user1,
                contribution_type=self.uptime_type,
                points=1,
                frozen_global_points=2,
                multiplier_at_creation=Decimal('2.0'),
                contribution_date=timezone.now() - timedelta(days=i)
            )
            
            Contribution.objects.create(
                user=self.user2,
                contribution_type=self.uptime_type,
                points=1,
                frozen_global_points=2,
                multiplier_at_creation=Decimal('2.0'),
                contribution_date=timezone.now() - timedelta(days=i)
            )
        
        # Add extra contribution for user2
        Contribution.objects.create(
            user=self.user2,
            contribution_type=self.blog_type,
            points=20,
            frozen_global_points=60,
            multiplier_at_creation=Decimal('3.0'),
            contribution_date=timezone.now()
        )
        
        # Get the leaderboard entries (created by signals)
        entry1 = LeaderboardEntry.objects.get(user=self.user1)
        entry2 = LeaderboardEntry.objects.get(user=self.user2)
        
        # Record initial ranks
        initial_rank1 = entry1.rank
        initial_rank2 = entry2.rank
        
        # Update both users' points without ranking
        points1 = entry1.update_points_without_ranking()
        points2 = entry2.update_points_without_ranking()
        
        # Check points
        self.assertEqual(points1, 6)  # 3 * 2
        self.assertEqual(points2, 66)  # 3 * 2 + 60
        
        # Ranks should not have changed since we didn't call update_all_ranks
        entry1.refresh_from_db()
        entry2.refresh_from_db()
        self.assertEqual(entry1.rank, initial_rank1)
        self.assertEqual(entry2.rank, initial_rank2)
        
        # Now update ranks
        update_all_ranks()
        
        # Refresh from database
        entry1.refresh_from_db()
        entry2.refresh_from_db()
        
        # Now check ranks are assigned correctly
        self.assertEqual(entry1.rank, 2)  # Lower points = rank 2
        self.assertEqual(entry2.rank, 1)  # Higher points = rank 1
    
    def test_update_points_with_no_contributions(self):
        """Test update_points_without_ranking when user has no contributions."""
        # Create leaderboard entry without contributions
        entry = LeaderboardEntry.objects.create(user=self.user1)
        
        # Update points
        total_points = entry.update_points_without_ranking()
        
        # Should be 0
        self.assertEqual(total_points, 0)
        self.assertEqual(entry.total_points, 0)
    
    def test_update_user_leaderboard_entry_triggers_ranking(self):
        """Test that update_user_leaderboard_entry updates both points and ranks."""
        # Create contributions
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.uptime_type,
            points=5,
            frozen_global_points=10,
            multiplier_at_creation=Decimal('2.0'),
            contribution_date=timezone.now()
        )
        
        Contribution.objects.create(
            user=self.user2,
            contribution_type=self.uptime_type,
            points=10,
            frozen_global_points=20,
            multiplier_at_creation=Decimal('2.0'),
            contribution_date=timezone.now()
        )
        
        # Update user1's leaderboard (this should trigger ranking)
        update_user_leaderboard_entry(self.user1)
        
        # Check that entry exists with correct points and rank
        entry1 = LeaderboardEntry.objects.get(user=self.user1)
        self.assertEqual(entry1.total_points, 10)
        self.assertIsNotNone(entry1.rank)
        
        # Update user2's leaderboard
        update_user_leaderboard_entry(self.user2)
        
        # Check rankings are correct
        entry1.refresh_from_db()
        entry2 = LeaderboardEntry.objects.get(user=self.user2)
        
        self.assertEqual(entry2.total_points, 20)
        self.assertEqual(entry1.rank, 2)  # user1 has less points
        self.assertEqual(entry2.rank, 1)  # user2 has more points
    
    def test_invisible_users_no_rank(self):
        """Test that invisible users don't get ranked."""
        # Create contributions for both first (while both are visible)
        Contribution.objects.create(
            user=self.user1,
            contribution_type=self.uptime_type,
            points=5,
            frozen_global_points=10,
            multiplier_at_creation=Decimal('2.0'),
            contribution_date=timezone.now()
        )
        
        Contribution.objects.create(
            user=self.user2,
            contribution_type=self.uptime_type,
            points=10,
            frozen_global_points=20,
            multiplier_at_creation=Decimal('2.0'),
            contribution_date=timezone.now()
        )
        
        # Now make user2 invisible
        self.user2.visible = False
        self.user2.save()
        
        # Get the leaderboard entries (they were created by the signal)
        entry1 = LeaderboardEntry.objects.get(user=self.user1)
        entry2 = LeaderboardEntry.objects.get(user=self.user2)
        
        # Update ranks
        update_all_ranks()
        
        # Refresh from database
        entry1.refresh_from_db()
        entry2.refresh_from_db()
        
        # User1 should have rank 1 (only visible user)
        self.assertEqual(entry1.rank, 1)
        
        # User2 should have no rank (invisible)
        self.assertIsNone(entry2.rank)
    
    def test_ranking_order_with_equal_points(self):
        """Test that users with equal points are ranked by name."""
        # Create a third user
        user3 = User.objects.create_user(
            email='user3@test.com',
            password='testpass123',
            name='AAA User',  # Alphabetically first
            address='0x3333333333333333333333333333333333333333',
            visible=True
        )
        
        # Give all users the same points
        for user in [self.user1, self.user2, user3]:
            Contribution.objects.create(
                user=user,
                contribution_type=self.uptime_type,
                points=5,
                frozen_global_points=10,
                multiplier_at_creation=Decimal('2.0'),
                contribution_date=timezone.now()
            )
        
        # Update ranks
        update_all_ranks()
        
        # Get entries
        entry1 = LeaderboardEntry.objects.get(user=self.user1)
        entry2 = LeaderboardEntry.objects.get(user=self.user2)
        entry3 = LeaderboardEntry.objects.get(user=user3)
        
        # All should have consecutive ranks based on name ordering
        # AAA User should be rank 1, User 1 should be rank 2, User 2 should be rank 3
        self.assertEqual(entry3.rank, 1)  # AAA User
        self.assertEqual(entry1.rank, 2)  # User 1
        self.assertEqual(entry2.rank, 3)  # User 2