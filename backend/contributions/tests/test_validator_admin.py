"""
Tests for validator admin creation functionality.
"""
from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.utils import timezone
from datetime import date, datetime
from decimal import Decimal

from contributions.models import Contribution, ContributionType, Category
from contributions.validator_admin import ValidatorAdmin

User = get_user_model()


class MockRequest:
    """Mock request object for testing admin views."""
    def __init__(self, method='GET', post_data=None):
        self.method = method
        self.POST = post_data or {}
        self.session = {}
        self._messages = FallbackStorage(self)
        self.META = {}


class ValidatorAdminTest(TestCase):
    """Test the validator admin creation functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create admin site instance
        self.site = AdminSite()
        self.admin = ValidatorAdmin()
        self.admin.admin_site = self.site
        
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
        self.validator_type, _ = ContributionType.objects.get_or_create(
            slug='validator',
            defaults={
                'name': 'Validator',
                'description': 'Validator badge',
                'category': self.validator_category,
                'min_points': 1,
                'max_points': 1,
                'is_default': False
            }
        )
        
        self.node_running_type, _ = ContributionType.objects.get_or_create(
            slug='node-running',
            defaults={
                'name': 'Node Running',
                'description': 'Running a validator node',
                'category': self.validator_category,
                'min_points': 10,
                'max_points': 100,
                'is_default': True
            }
        )
        
        self.bug_report_type, _ = ContributionType.objects.get_or_create(
            slug='bug-report',
            defaults={
                'name': 'Bug Report',
                'description': 'Reporting bugs',
                'category': self.builder_category,
                'min_points': 5,
                'max_points': 50,
                'is_default': True
            }
        )
        
        # Create global multipliers for the contribution types
        from leaderboard.models import GlobalLeaderboardMultiplier
        
        # Create multipliers valid from 2024-01-01 to cover all test dates
        multiplier_start = timezone.make_aware(datetime(2024, 1, 1))
        
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=self.validator_type,
            defaults={
                'multiplier_value': Decimal('1.0'),
                'valid_from': multiplier_start,
                'description': 'Test multiplier for validator'
            }
        )
        
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=self.node_running_type,
            defaults={
                'multiplier_value': Decimal('2.0'),
                'valid_from': multiplier_start,
                'description': 'Test multiplier for node running'
            }
        )
        
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=self.bug_report_type,
            defaults={
                'multiplier_value': Decimal('1.5'),
                'valid_from': multiplier_start,
                'description': 'Test multiplier for bug reports'
            }
        )
    
    def test_validator_creation_creates_validator_contribution(self):
        """Test that creating a validator also creates the validator contribution."""
        from contributions.validator_forms import CreateValidatorForm
        from datetime import date
        
        # Prepare form data
        form_data = {
            'name': 'Test Validator',
            'address': '0x1234567890123456789012345678901234567890',
            'contribution_date': date(2024, 1, 15),
            # Selected contributions
            f'include_{self.node_running_type.id}': True,
            f'points_{self.node_running_type.id}': 50
        }
        
        form = CreateValidatorForm(form_data)
        self.assertTrue(form.is_valid())
        
        # Process the validator creation
        user = self.admin._process_validator_creation(form)
        
        # Check user was created
        user = User.objects.filter(address='0x1234567890123456789012345678901234567890').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.name, 'Test Validator')
        
        # Check Validator model was created
        from validators.models import Validator
        validator = Validator.objects.filter(user=user).first()
        self.assertIsNotNone(validator)
        
        # Check validator contribution was created automatically
        validator_contrib = Contribution.objects.filter(
            user=user,
            contribution_type=self.validator_type
        ).first()
        self.assertIsNotNone(validator_contrib)
        self.assertEqual(validator_contrib.points, 1)
        self.assertIn('Validator badge created via admin', validator_contrib.notes)
        
        # Check the manually selected contribution was created
        node_contrib = Contribution.objects.filter(
            user=user,
            contribution_type=self.node_running_type
        ).first()
        self.assertIsNotNone(node_contrib)
        self.assertEqual(node_contrib.points, 50)
    
    def test_validator_creation_skips_existing_validator_contribution(self):
        """Test that validator contribution is not duplicated if it already exists."""
        from contributions.validator_forms import CreateValidatorForm
        from datetime import date
        
        # Create existing user with validator contribution
        existing_user = User.objects.create(
            email='existing@test.com',
            name='Existing User',
            address='0x2345678901234567890123456789012345678901',
            visible=True
        )
        
        # Create existing validator contribution
        Contribution.objects.create(
            user=existing_user,
            contribution_type=self.validator_type,
            points=1,
            contribution_date=timezone.now()
        )
        
        # Try to create validator for same user
        form_data = {
            'name': 'Updated Name',
            'address': '0x2345678901234567890123456789012345678901',
            'contribution_date': date(2024, 1, 20),
            f'include_{self.bug_report_type.id}': True,
            f'points_{self.bug_report_type.id}': 25
        }
        
        form = CreateValidatorForm(form_data)
        self.assertTrue(form.is_valid())
        user = self.admin._process_validator_creation(form)
        
        # Check only one validator contribution exists
        validator_contribs = Contribution.objects.filter(
            user=existing_user,
            contribution_type=self.validator_type
        )
        self.assertEqual(validator_contribs.count(), 1)
        
        # Check the new contribution was still created
        bug_contrib = Contribution.objects.filter(
            user=existing_user,
            contribution_type=self.bug_report_type
        ).first()
        self.assertIsNotNone(bug_contrib)
        self.assertEqual(bug_contrib.points, 25)
    
    def test_validator_creation_with_multiple_contributions(self):
        """Test creating a validator with multiple contributions."""
        from contributions.validator_forms import CreateValidatorForm
        from datetime import date
        
        form_data = {
            'name': 'Multi Contributor',
            'address': '0x3456789012345678901234567890123456789012',
            'contribution_date': date(2024, 2, 1),
            f'include_{self.node_running_type.id}': True,
            f'points_{self.node_running_type.id}': 75,
            f'include_{self.bug_report_type.id}': True,
            f'points_{self.bug_report_type.id}': 30
        }
        
        form = CreateValidatorForm(form_data)
        self.assertTrue(form.is_valid())
        user = self.admin._process_validator_creation(form)
        
        # Check user was created
        user = User.objects.filter(address='0x3456789012345678901234567890123456789012').first()
        self.assertIsNotNone(user)
        
        # Check all contributions were created
        self.assertEqual(user.contributions.count(), 3)  # validator + 2 selected
        
        # Verify each contribution
        self.assertTrue(
            Contribution.objects.filter(
                user=user,
                contribution_type=self.validator_type,
                points=1
            ).exists()
        )
        self.assertTrue(
            Contribution.objects.filter(
                user=user,
                contribution_type=self.node_running_type,
                points=75
            ).exists()
        )
        self.assertTrue(
            Contribution.objects.filter(
                user=user,
                contribution_type=self.bug_report_type,
                points=30
            ).exists()
        )
    
    def test_validator_creation_updates_existing_user_name(self):
        """Test that creating a validator for existing user updates their name."""
        from contributions.validator_forms import CreateValidatorForm
        from datetime import date
        
        # Create existing user with different name
        existing_user = User.objects.create(
            email='oldname@test.com',
            username='0x4567890123456789012345678901234567890123',
            name='Old Name',
            address='0x4567890123456789012345678901234567890123',
            visible=True
        )
        
        form_data = {
            'name': 'New Name',
            'address': '0x4567890123456789012345678901234567890123',
            'contribution_date': date(2024, 2, 10),
            f'include_{self.node_running_type.id}': True,
            f'points_{self.node_running_type.id}': 40
        }
        
        form = CreateValidatorForm(form_data)
        self.assertTrue(form.is_valid())
        user = self.admin._process_validator_creation(form)
        
        # Check name was updated
        existing_user.refresh_from_db()
        self.assertEqual(existing_user.name, 'New Name')
        
        # Check validator and contributions were created
        from validators.models import Validator
        self.assertTrue(Validator.objects.filter(user=existing_user).exists())
        self.assertEqual(existing_user.contributions.count(), 2)  # validator + node-running
    
    def test_validator_creation_with_invalid_data(self):
        """Test validator creation with invalid data."""
        from contributions.validator_forms import CreateValidatorForm
        from datetime import date
        
        # Missing required fields
        form_data = {
            'name': 'Invalid User',
            # Missing address
            'contribution_date': date(2024, 2, 15)
        }
        
        form = CreateValidatorForm(form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('address', form.errors)
        
        # Check no user was created
        self.assertFalse(User.objects.filter(name='Invalid User').exists())
    
    def test_validator_creation_prevents_duplicate_contributions(self):
        """Test that duplicate contributions are prevented."""
        from contributions.validator_forms import CreateValidatorForm
        from django.core.exceptions import ValidationError
        
        # Create user with existing contribution
        user = User.objects.create(
            email='duplicate@test.com',
            name='Duplicate Test',
            address='0x5678901234567890123456789012345678901234',
            visible=True
        )
        
        contribution_date = date(2024, 2, 20)
        Contribution.objects.create(
            user=user,
            contribution_type=self.node_running_type,
            points=50,
            contribution_date=timezone.make_aware(datetime.combine(contribution_date, datetime.min.time()))
        )
        
        # Try to create same contribution type on same date
        form_data = {
            'name': 'Duplicate Test',
            'address': '0x5678901234567890123456789012345678901234',
            'contribution_date': contribution_date,
            f'include_{self.node_running_type.id}': True,
            f'points_{self.node_running_type.id}': 60
        }
        
        form = CreateValidatorForm(form_data)
        self.assertTrue(form.is_valid())
        
        # Should raise validation error
        with self.assertRaises(ValidationError) as context:
            user = self.admin._process_validator_creation(form)
        
        # Check only original contribution exists
        node_contribs = Contribution.objects.filter(
            user=user,
            contribution_type=self.node_running_type
        )
        self.assertEqual(node_contribs.count(), 1)
        self.assertEqual(node_contribs.first().points, 50)  # Original value
    
    def test_validator_creation_datetime_conversion(self):
        """Test that contribution dates are properly converted to datetime."""
        from contributions.validator_forms import CreateValidatorForm
        from datetime import date
        
        form_data = {
            'name': 'DateTime Test',
            'address': '0x6789012345678901234567890123456789012345',
            'contribution_date': date(2024, 3, 1),
            f'include_{self.node_running_type.id}': True,
            f'points_{self.node_running_type.id}': 80
        }
        
        form = CreateValidatorForm(form_data)
        self.assertTrue(form.is_valid())
        user = self.admin._process_validator_creation(form)
        
        user = User.objects.get(address='0x6789012345678901234567890123456789012345')
        
        # Check all contributions have proper datetime
        for contribution in user.contributions.all():
            self.assertIsNotNone(contribution.contribution_date)
            self.assertEqual(contribution.contribution_date.date(), date(2024, 3, 1))
            # Should be timezone-aware
            self.assertIsNotNone(contribution.contribution_date.tzinfo)
    
    def test_get_urls_includes_create_validator(self):
        """Test that custom URLs are properly configured."""
        urls = self.admin.get_urls()
        
        # Check that create-validator URL is included
        url_names = [url.name for url in urls]
        self.assertIn('contributions_create_validator', url_names)
    
    def test_validator_creation_with_no_validator_contribution_type(self):
        """Test behavior when 'validator' contribution type doesn't exist."""
        from contributions.validator_forms import CreateValidatorForm
        from datetime import date
        
        # Delete the validator contribution type
        self.validator_type.delete()
        
        form_data = {
            'name': 'No Validator Type',
            'address': '0x7890123456789012345678901234567890123456',
            'contribution_date': date(2024, 3, 10),
            f'include_{self.node_running_type.id}': True,
            f'points_{self.node_running_type.id}': 90
        }
        
        form = CreateValidatorForm(form_data)
        self.assertTrue(form.is_valid())
        user = self.admin._process_validator_creation(form)
        
        # User should still be created
        user = User.objects.filter(address='0x7890123456789012345678901234567890123456').first()
        self.assertIsNotNone(user)
        
        # Validator model should be created
        from validators.models import Validator
        self.assertTrue(Validator.objects.filter(user=user).exists())
        
        # Only the selected contribution should exist (no validator contribution)
        self.assertEqual(user.contributions.count(), 1)
        self.assertTrue(
            user.contributions.filter(contribution_type=self.node_running_type).exists()
        )