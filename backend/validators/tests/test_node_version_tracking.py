"""
Test node version tracking and points calculation.
"""
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from validators.models import Validator
from validators.node_version import calculate_early_upgrade_bonus
from contributions.models import ContributionType, SubmittedContribution, Category
from contributions.node_upgrade.models import TargetNodeVersion
from leaderboard.models import GlobalLeaderboardMultiplier

User = get_user_model()


class NodeVersionTrackingTestCase(TestCase):
    def setUp(self):
        """Set up test data."""
        # Create a user
        self.user = User.objects.create(
            email='validator@test.com',
            address='0x1234567890123456789012345678901234567890',
            visible=True
        )
        
        # Create validator category
        self.category, _ = Category.objects.get_or_create(
            name='Validator',
            slug='validator'
        )
        
        # Get or create node-upgrade contribution type
        self.contribution_type, _ = ContributionType.objects.get_or_create(
            slug='node-upgrade',
            defaults={
                'name': 'Node Upgrade',
                'category': self.category,
                'min_points': 10,
                'max_points': 100,
                'is_submittable': True
            }
        )
        
        # Create multiplier for the contribution type
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.contribution_type,
            multiplier_value=1.0,
            valid_from=timezone.now() - timedelta(days=30)
        )
        
        # Create a validator
        self.validator = Validator.objects.create(
            user=self.user,
            node_version='1.0.0'
        )
        
        # Create a target version
        self.target = TargetNodeVersion.objects.create(
            version='2.0.0',
            target_date=timezone.now() + timedelta(days=7),
            is_active=True
        )
    
    
    def test_early_upgrade_bonus(self):
        """Test the early upgrade bonus calculation."""
        now = timezone.now()
        
        # Same day upgrade
        self.assertEqual(calculate_early_upgrade_bonus(now, now), 4)
        
        # Day 1
        self.assertEqual(calculate_early_upgrade_bonus(now, now + timedelta(days=1)), 3)
        
        # Day 2
        self.assertEqual(calculate_early_upgrade_bonus(now, now + timedelta(days=2)), 2)
        
        # Day 3+
        self.assertEqual(calculate_early_upgrade_bonus(now, now + timedelta(days=3)), 1)
        self.assertEqual(calculate_early_upgrade_bonus(now, now + timedelta(days=10)), 1)
    
    
    def test_submission_creation_with_calculated_points(self):
        """Test that updating node version creates a submission with calculated points."""
        # Update validator to target version
        self.validator.node_version = '2.0.0'
        self.validator.save()
        
        # Check that a submission was created
        submissions = SubmittedContribution.objects.filter(user=self.user)
        self.assertEqual(submissions.count(), 1)
        
        submission = submissions.first()
        self.assertEqual(submission.contribution_type, self.contribution_type)
        self.assertEqual(submission.state, 'pending')
        
        # Check suggested points (should be 4 for same-day upgrade)
        self.assertEqual(submission.suggested_points, 4)
        
        # Check that no evidence was created for automatic submission
        self.assertEqual(submission.evidence_items.count(), 0)
    
    def test_submission_with_delayed_upgrade(self):
        """Test points calculation with delayed upgrade."""
        # Update target to have been available 3 days ago
        self.target.target_date = timezone.now() - timedelta(days=3)
        self.target.save()
        
        # Update to target version
        self.validator.node_version = '2.0.0'
        self.validator.save()
        
        # Check submission
        submission = SubmittedContribution.objects.filter(user=self.user).first()
        self.assertIsNotNone(submission)
        
        # Should have 1 point (minimum for 3+ days delay)
        self.assertEqual(submission.suggested_points, 1)
    
    def test_no_duplicate_submissions(self):
        """Test that duplicate submissions are not created for the same target."""
        # First upgrade
        self.validator.node_version = '2.0.0'
        self.validator.save()
        
        # Try to create another submission for the same target
        self.validator.node_version = '2.0.1'  # Minor version change
        self.validator.save()
        
        # Should still only have one submission
        submissions = SubmittedContribution.objects.filter(user=self.user)
        self.assertEqual(submissions.count(), 1)
    
    def test_invisible_user_no_submission(self):
        """Test that invisible users don't get submissions."""
        # Make user invisible
        self.user.visible = False
        self.user.save()
        
        # Update validator version
        self.validator.node_version = '2.0.0'
        self.validator.save()
        
        # Should not create submission
        submissions = SubmittedContribution.objects.filter(user=self.user)
        self.assertEqual(submissions.count(), 0)