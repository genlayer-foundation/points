from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, date
from contributions.models import ContributionType, Contribution
from contributions.validator_forms import CreateValidatorForm
from leaderboard.models import GlobalLeaderboardMultiplier

User = get_user_model()


class ValidatorCreationTestCase(TestCase):
    def setUp(self):
        """Set up test data."""
        # Create a superuser for admin access
        self.admin_user = User.objects.create_superuser(
            email='admin@test.com',
            password='testpass123',
            username='admin'
        )
        
        # Create contribution types
        self.contrib_type1 = ContributionType.objects.create(
            name='Node Running',
            description='Running a validator node',
            min_points=10,
            max_points=100,
            is_default=True
        )
        
        self.contrib_type2 = ContributionType.objects.create(
            name='Uptime',
            description='Node uptime contribution',
            min_points=5,
            max_points=50,
            is_default=True
        )
        
        self.contrib_type3 = ContributionType.objects.create(
            name='Bug Report',
            description='Reporting bugs',
            min_points=20,
            max_points=200,
            is_default=False  # Not default
        )
        
        # Create multipliers for contribution types (set valid_from to yesterday to ensure they're active)
        yesterday = timezone.now() - timezone.timedelta(days=1)
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.contrib_type1,
            multiplier_value=1.5,
            valid_from=yesterday,
            description='Node running multiplier'
        )
        
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.contrib_type2,
            multiplier_value=2.0,
            valid_from=yesterday,
            description='Uptime multiplier'
        )
        
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.contrib_type3,
            multiplier_value=1.0,
            valid_from=yesterday,
            description='Bug report multiplier'
        )
        
        self.client = Client()
        self.client.login(email='admin@test.com', password='testpass123')
    
    def test_form_initialization(self):
        """Test that the form initializes with correct default contribution types."""
        form = CreateValidatorForm()
        
        # Check that default contribution types have fields
        self.assertIn(f'include_{self.contrib_type1.id}', form.fields)
        self.assertIn(f'points_{self.contrib_type1.id}', form.fields)
        self.assertIn(f'include_{self.contrib_type2.id}', form.fields)
        self.assertIn(f'points_{self.contrib_type2.id}', form.fields)
        
        # Check that non-default contribution type doesn't have fields
        self.assertNotIn(f'include_{self.contrib_type3.id}', form.fields)
        self.assertNotIn(f'points_{self.contrib_type3.id}', form.fields)
        
        # Check that checkboxes are initially checked
        self.assertTrue(form.fields[f'include_{self.contrib_type1.id}'].initial)
        self.assertTrue(form.fields[f'include_{self.contrib_type2.id}'].initial)
    
    def test_form_validation_valid_data(self):
        """Test form validation with valid data."""
        form_data = {
            'name': 'John Validator',
            'address': '0x1234567890123456789012345678901234567890',
            'contribution_date': date.today(),
            f'include_{self.contrib_type1.id}': True,
            f'points_{self.contrib_type1.id}': 50,
            f'include_{self.contrib_type2.id}': True,
            f'points_{self.contrib_type2.id}': 25,
        }
        
        form = CreateValidatorForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Check cleaned data
        self.assertEqual(form.cleaned_data['name'], 'John Validator')
        self.assertEqual(form.cleaned_data['address'], '0x1234567890123456789012345678901234567890')
        
        # Check selected contributions
        contributions = form.get_selected_contributions()
        self.assertEqual(len(contributions), 2)
        
        contrib_ids = [c['contribution_type_id'] for c in contributions]
        self.assertIn(self.contrib_type1.id, contrib_ids)
        self.assertIn(self.contrib_type2.id, contrib_ids)
    
    def test_form_validation_invalid_address(self):
        """Test form validation with invalid blockchain address."""
        form_data = {
            'name': 'John Validator',
            'address': 'invalid_address',
            'contribution_date': date.today(),
            f'include_{self.contrib_type1.id}': True,
            f'points_{self.contrib_type1.id}': 50,
        }
        
        form = CreateValidatorForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('address', form.errors)
    
    def test_form_validation_future_date(self):
        """Test form validation with future contribution date."""
        from datetime import timedelta
        
        form_data = {
            'name': 'John Validator',
            'address': '0x1234567890123456789012345678901234567890',
            'contribution_date': date.today() + timedelta(days=1),
            f'include_{self.contrib_type1.id}': True,
            f'points_{self.contrib_type1.id}': 50,
        }
        
        form = CreateValidatorForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('contribution_date', form.errors)
    
    def test_form_validation_no_contributions_selected(self):
        """Test form validation when no contributions are selected."""
        form_data = {
            'name': 'John Validator',
            'address': '0x1234567890123456789012345678901234567890',
            'contribution_date': date.today(),
            f'include_{self.contrib_type1.id}': False,
            f'include_{self.contrib_type2.id}': False,
        }
        
        form = CreateValidatorForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('At least one contribution type must be selected', str(form.errors))
    
    def test_form_validation_points_out_of_range(self):
        """Test form validation with points outside allowed range."""
        form_data = {
            'name': 'John Validator',
            'address': '0x1234567890123456789012345678901234567890',
            'contribution_date': date.today(),
            f'include_{self.contrib_type1.id}': True,
            f'points_{self.contrib_type1.id}': 200,  # Max is 100
        }
        
        form = CreateValidatorForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn(f'points_{self.contrib_type1.id}', form.errors)
    
    def test_user_creation_new_user(self):
        """Test creating a new user through validator creation."""
        from contributions.admin import ContributionAdmin
        from django.test import RequestFactory
        
        # Create a mock request
        factory = RequestFactory()
        request = factory.post('/admin/contributions/contribution/create-validator/')
        request.user = self.admin_user
        
        # Create admin instance
        admin = ContributionAdmin(Contribution, None)
        
        # Create form with valid data
        form_data = {
            'name': 'New Validator',
            'address': '0xabcdef1234567890123456789012345678901234',
            'contribution_date': date.today(),
            f'include_{self.contrib_type1.id}': True,
            f'points_{self.contrib_type1.id}': 75,
        }
        
        form = CreateValidatorForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Process validator creation
        user = admin._process_validator_creation(form)
        
        # Check user was created
        self.assertIsNotNone(user)
        self.assertEqual(user.address, '0xabcdef1234567890123456789012345678901234')
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.last_name, 'Validator')
        self.assertTrue(user.visible)
        
        # Check contribution was created
        contributions = Contribution.objects.filter(user=user)
        self.assertEqual(contributions.count(), 1)
        
        contribution = contributions.first()
        self.assertEqual(contribution.contribution_type, self.contrib_type1)
        self.assertEqual(contribution.points, 75)
        self.assertEqual(contribution.frozen_global_points, 112)  # 75 * 1.5
    
    def test_user_lookup_existing_user(self):
        """Test looking up an existing user by blockchain address."""
        from contributions.admin import ContributionAdmin
        from django.test import RequestFactory
        
        # Create an existing user with valid address format
        existing_user = User.objects.create(
            username='existing',
            email='existing@test.com',
            address='0x1234567890123456789012345678901234567890',
            first_name='Old',
            last_name='Name',
            visible=True
        )
        
        # Create a mock request
        factory = RequestFactory()
        request = factory.post('/admin/contributions/contribution/create-validator/')
        request.user = self.admin_user
        
        # Create admin instance
        admin = ContributionAdmin(Contribution, None)
        
        # Create form with the existing user's address
        form_data = {
            'name': 'Updated Name',
            'address': '0x1234567890123456789012345678901234567890',
            'contribution_date': date.today(),
            f'include_{self.contrib_type1.id}': True,
            f'points_{self.contrib_type1.id}': 60,
        }
        
        form = CreateValidatorForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Process validator creation
        user = admin._process_validator_creation(form)
        
        # Check it's the same user
        self.assertEqual(user.id, existing_user.id)
        
        # Check name was updated
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Updated')
        self.assertEqual(user.last_name, 'Name')
        
        # Check contribution was created
        contributions = Contribution.objects.filter(user=user)
        self.assertEqual(contributions.count(), 1)
    
    def test_duplicate_contribution_prevention(self):
        """Test that duplicate contributions are prevented."""
        from contributions.admin import ContributionAdmin
        from django.test import RequestFactory
        from django.core.exceptions import ValidationError
        
        # Create a user with an existing contribution (valid address format)
        user = User.objects.create(
            username='validator',
            email='validator@test.com',
            address='0x1234567890123456789012345678901234567891',
            visible=True
        )
        
        # Create an existing contribution for today
        Contribution.objects.create(
            user=user,
            contribution_type=self.contrib_type1,
            points=50,
            contribution_date=timezone.now()
        )
        
        # Create a mock request
        factory = RequestFactory()
        request = factory.post('/admin/contributions/contribution/create-validator/')
        request.user = self.admin_user
        
        # Create admin instance
        admin = ContributionAdmin(Contribution, None)
        
        # Try to create duplicate contribution
        form_data = {
            'name': 'Validator Name',
            'address': '0x1234567890123456789012345678901234567891',
            'contribution_date': date.today(),
            f'include_{self.contrib_type1.id}': True,
            f'points_{self.contrib_type1.id}': 75,
        }
        
        form = CreateValidatorForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Should raise ValidationError for duplicate
        with self.assertRaises(ValidationError) as context:
            admin._process_validator_creation(form)
        
        self.assertIn('already exists', str(context.exception))
    
    def test_admin_view_access(self):
        """Test that the admin view is accessible to superusers."""
        # Ensure we're logged in
        self.assertTrue(self.client.login(email='admin@test.com', password='testpass123'))
        
        url = reverse('admin:contributions_create_validator')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Validator')  # Check for page title
        self.assertContains(response, 'Default Contributions')  # Check for contributions section
        self.assertContains(response, 'Node Running')  # Default contribution type
        self.assertContains(response, 'Uptime')  # Default contribution type
        self.assertNotContains(response, 'Bug Report')  # Non-default contribution type
    
    def test_admin_view_post_success(self):
        """Test successful validator creation through admin view."""
        # Ensure we're logged in
        self.assertTrue(self.client.login(email='admin@test.com', password='testpass123'))
        
        url = reverse('admin:contributions_create_validator')
        
        form_data = {
            'name': 'Test Admin Validator',
            'address': '0xABCDEF1234567890123456789012345678901234',  # Use uppercase to test normalization
            'contribution_date': date.today().strftime('%Y-%m-%d'),
            f'include_{self.contrib_type1.id}': 'on',
            f'points_{self.contrib_type1.id}': '80',
            f'include_{self.contrib_type2.id}': 'on',
            f'points_{self.contrib_type2.id}': '30',
        }
        
        response = self.client.post(url, form_data, follow=False)
        
        # Should redirect to user detail page
        self.assertEqual(response.status_code, 302)
        
        # Check user was created (address should be normalized to lowercase)
        user = User.objects.get(address='0xabcdef1234567890123456789012345678901234')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'Admin Validator')
        
        # Check contributions were created
        contributions = Contribution.objects.filter(user=user)
        self.assertEqual(contributions.count(), 2)
        
        # Check points
        node_contrib = contributions.get(contribution_type=self.contrib_type1)
        self.assertEqual(node_contrib.points, 80)
        
        uptime_contrib = contributions.get(contribution_type=self.contrib_type2)
        self.assertEqual(uptime_contrib.points, 30)