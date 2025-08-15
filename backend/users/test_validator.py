from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from users.models import User, Validator
from contributions.models import ContributionType, Contribution, Evidence
from contributions.node_upgrade.models import TargetNodeVersion
from leaderboard.models import GlobalLeaderboardMultiplier


class ValidatorModelTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='validator@example.com',
            password='testpass123',
            name='Test Validator',
            address='0x1234567890abcdef'
        )
        
        # Get or create node-upgrade contribution type (migration might have created it)
        self.contribution_type, _ = ContributionType.objects.get_or_create(
            slug='node-upgrade',
            defaults={
                'name': 'Node Upgrade',
                'description': 'Points are assigned based on upgrade time',
                'min_points': 1,
                'max_points': 4
            }
        )
        
        # Create multiplier for the contribution type
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.contribution_type,
            multiplier_value=10.0,
            valid_from=timezone.now() - timedelta(days=30),
            description="Test multiplier"
        )
        
    def test_validator_creation(self):
        """Test creating a validator"""
        validator = Validator.objects.create(
            user=self.user,
            node_version='1.2.3'
        )
        
        self.assertEqual(validator.user, self.user)
        self.assertEqual(validator.node_version, '1.2.3')
        self.assertEqual(str(validator), 'validator@example.com - Node: 1.2.3')
        
    def test_validator_version_parsing(self):
        """Test version parsing logic"""
        validator = Validator.objects.create(user=self.user)
        
        # Test valid versions - full X.Y.Z
        self.assertEqual(validator.clean_version('1.2.3'), (1, 2, 3))
        self.assertEqual(validator.clean_version('v1.2.3'), (1, 2, 3))
        self.assertEqual(validator.clean_version('1.2.3-rc1'), (1, 2, 3))
        self.assertEqual(validator.clean_version('v1.2.3-beta'), (1, 2, 3))
        
        # Test valid versions - X.Y format
        self.assertEqual(validator.clean_version('1.2'), (1, 2, 0))
        self.assertEqual(validator.clean_version('0.4'), (0, 4, 0))
        self.assertEqual(validator.clean_version('v0.3'), (0, 3, 0))
        
        # Test valid versions - X format
        self.assertEqual(validator.clean_version('1'), (1, 0, 0))
        self.assertEqual(validator.clean_version('v2'), (2, 0, 0))
        
        # Test invalid versions
        self.assertIsNone(validator.clean_version(''))
        self.assertIsNone(validator.clean_version('invalid'))
        
    def test_version_comparison(self):
        """Test version matching logic"""
        validator = Validator.objects.create(
            user=self.user,
            node_version='1.2.3'
        )
        
        # Test exact match
        self.assertTrue(validator.version_matches_or_higher('1.2.3'))
        self.assertTrue(validator.version_matches_or_higher('v1.2.3'))
        
        # Test lower versions
        self.assertTrue(validator.version_matches_or_higher('1.2.2'))
        self.assertTrue(validator.version_matches_or_higher('1.1.9'))
        self.assertTrue(validator.version_matches_or_higher('0.9.9'))
        
        # Test higher versions
        self.assertFalse(validator.version_matches_or_higher('1.2.4'))
        self.assertFalse(validator.version_matches_or_higher('1.3.0'))
        self.assertFalse(validator.version_matches_or_higher('2.0.0'))
        
    def test_automatic_contribution_creation(self):
        """Test that updating to target version creates contribution"""
        # Create target version
        target = TargetNodeVersion.objects.create(
            version='2.0.0',
            target_date=timezone.now() + timedelta(days=7),
            is_active=True
        )
        
        # Create validator without version
        validator = Validator.objects.create(user=self.user)
        
        # Update to matching version
        validator.node_version = '2.0.0'
        validator.save()
        
        # Check contribution was created
        self.assertEqual(Contribution.objects.count(), 1)
        contribution = Contribution.objects.first()
        self.assertEqual(contribution.user, self.user)
        self.assertEqual(contribution.contribution_type, self.contribution_type)
        self.assertEqual(contribution.points, 4)  # Day 1 = 4 points
        
        # Check evidence was created
        self.assertEqual(Evidence.objects.count(), 1)
        evidence = Evidence.objects.first()
        self.assertIn('Target version: 2.0.0', evidence.description)
        
    def test_points_calculation_based_on_time(self):
        """Test that points decrease over time"""
        # Create target version 2 days ago (to get 2 points)
        target = TargetNodeVersion.objects.create(
            version='2.0.0',
            target_date=timezone.now() + timedelta(days=7),
            is_active=True
        )
        # Manually set created_at to 2 days ago
        TargetNodeVersion.objects.filter(pk=target.pk).update(
            created_at=timezone.now() - timedelta(days=2, hours=1)  # A bit more than 2 days
        )
        
        # Create and update validator
        validator = Validator.objects.create(user=self.user)
        validator.node_version = '2.0.0'
        validator.save()
        
        # Should get 2 points (day 3 = index 2)
        contribution = Contribution.objects.first()
        self.assertEqual(contribution.points, 2)
        
    def test_no_duplicate_contributions(self):
        """Test that duplicate contributions are not created"""
        # Create target version
        target = TargetNodeVersion.objects.create(
            version='2.0.0',
            target_date=timezone.now() + timedelta(days=7),
            is_active=True
        )
        
        # Create validator and update to target
        validator = Validator.objects.create(user=self.user)
        validator.node_version = '2.0.0'
        validator.save()
        
        # First contribution should be created
        self.assertEqual(Contribution.objects.count(), 1)
        
        # Change version and change back
        validator.node_version = '1.9.9'
        validator.save()
        validator.node_version = '2.0.0'
        validator.save()
        
        # Should still have only one contribution
        self.assertEqual(Contribution.objects.count(), 1)
        
    def test_higher_version_creates_contribution(self):
        """Test that higher versions also create contributions"""
        # Create target version
        target = TargetNodeVersion.objects.create(
            version='2.0.0',
            target_date=timezone.now() + timedelta(days=7),
            is_active=True
        )
        
        # Create validator with higher version
        validator = Validator.objects.create(user=self.user)
        validator.node_version = '2.1.0'
        validator.save()
        
        # Contribution should be created
        self.assertEqual(Contribution.objects.count(), 1)
        
    def test_no_contribution_without_target(self):
        """Test that no contribution is created without active target"""
        # No target version exists
        
        # Create validator and set version
        validator = Validator.objects.create(user=self.user)
        validator.node_version = '2.0.0'
        validator.save()
        
        # No contribution should be created
        self.assertEqual(Contribution.objects.count(), 0)
        
    def test_only_active_target_triggers_contribution(self):
        """Test that only active targets trigger contributions"""
        # Create inactive target
        target = TargetNodeVersion.objects.create(
            version='2.0.0',
            target_date=timezone.now() + timedelta(days=7),
            is_active=False
        )
        
        # Create validator and update to target version
        validator = Validator.objects.create(user=self.user)
        validator.node_version = '2.0.0'
        validator.save()
        
        # No contribution should be created
        self.assertEqual(Contribution.objects.count(), 0)