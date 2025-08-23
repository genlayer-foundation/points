from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from contributions.models import ContributionType, Category
from users.models import User


class ContributionTypeIsSubmittableTest(TestCase):
    """Test the is_submittable field and filtering functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Get or create test categories to avoid conflicts
        self.validator_category, _ = Category.objects.get_or_create(
            slug='test-validator',
            defaults={
                'name': 'Test Validator',
                'description': 'Test validator category'
            }
        )
        
        self.builder_category, _ = Category.objects.get_or_create(
            slug='test-builder',
            defaults={
                'name': 'Test Builder',
                'description': 'Test builder category'
            }
        )
        
        # Create test contribution types with different is_submittable values
        self.submittable_type_1 = ContributionType.objects.create(
            name='Submittable Type 1',
            slug='submittable-1',
            description='This can be submitted by users',
            category=self.validator_category,
            min_points=1,
            max_points=10,
            is_submittable=True
        )
        
        self.submittable_type_2 = ContributionType.objects.create(
            name='Submittable Type 2',
            slug='submittable-2',
            description='This can also be submitted by users',
            category=self.builder_category,
            min_points=5,
            max_points=20,
            is_submittable=True
        )
        
        self.non_submittable_type = ContributionType.objects.create(
            name='Non-Submittable Type',
            slug='non-submittable',
            description='This cannot be submitted by users',
            category=self.validator_category,
            min_points=10,
            max_points=50,
            is_submittable=False
        )
        
        self.api_url = reverse('contributiontype-list')
    
    def test_is_submittable_field_default_value(self):
        """Test that is_submittable defaults to True."""
        new_type = ContributionType.objects.create(
            name='Default Type',
            slug='default-type',
            description='Testing default value',
            category=self.validator_category,
            min_points=1,
            max_points=5
        )
        self.assertTrue(new_type.is_submittable)
    
    def test_filter_by_is_submittable_true(self):
        """Test filtering contribution types where is_submittable=true."""
        response = self.client.get(self.api_url, {'is_submittable': 'true'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Check that our submittable types are in the results
        result_ids = [item['id'] for item in data['results']]
        self.assertIn(self.submittable_type_1.id, result_ids)
        self.assertIn(self.submittable_type_2.id, result_ids)
        self.assertNotIn(self.non_submittable_type.id, result_ids)
        
        # Verify all returned types have is_submittable=true
        for item in data['results']:
            self.assertTrue(item['is_submittable'])
    
    def test_filter_by_is_submittable_false(self):
        """Test filtering contribution types where is_submittable=false."""
        response = self.client.get(self.api_url, {'is_submittable': 'false'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Check that we only get non-submittable types
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['id'], self.non_submittable_type.id)
        self.assertFalse(data['results'][0]['is_submittable'])
    
    def test_no_filter_returns_all_types(self):
        """Test that not providing is_submittable filter returns all types."""
        response = self.client.get(self.api_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should return all our test types (there may be others from migrations)
        result_ids = [item['id'] for item in data['results']]
        self.assertIn(self.submittable_type_1.id, result_ids)
        self.assertIn(self.submittable_type_2.id, result_ids)
        self.assertIn(self.non_submittable_type.id, result_ids)
    
    def test_combined_filters(self):
        """Test combining is_submittable with category filter."""
        # Test validator category with is_submittable=true
        response = self.client.get(self.api_url, {
            'category': 'test-validator',
            'is_submittable': 'true'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should only get submittable validator type
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['id'], self.submittable_type_1.id)
        
        # Test validator category with is_submittable=false
        response = self.client.get(self.api_url, {
            'category': 'test-validator',
            'is_submittable': 'false'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should only get non-submittable validator type
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['id'], self.non_submittable_type.id)
        
        # Test builder category with is_submittable=true
        response = self.client.get(self.api_url, {
            'category': 'test-builder',
            'is_submittable': 'true'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should only get submittable builder type
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['id'], self.submittable_type_2.id)
    
    def test_is_submittable_in_serialized_response(self):
        """Test that is_submittable field is included in API response."""
        response = self.client.get(f"{self.api_url}{self.submittable_type_1.id}/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Check that is_submittable field is present and correct
        self.assertIn('is_submittable', data)
        self.assertTrue(data['is_submittable'])
        
        # Test for non-submittable type
        response = self.client.get(f"{self.api_url}{self.non_submittable_type.id}/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertIn('is_submittable', data)
        self.assertFalse(data['is_submittable'])
    
    def test_case_insensitive_filter_value(self):
        """Test that filter values are case-insensitive."""
        # Test with uppercase TRUE
        response = self.client.get(self.api_url, {'is_submittable': 'TRUE'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        result_ids = [item['id'] for item in data['results']]
        self.assertIn(self.submittable_type_1.id, result_ids)
        self.assertIn(self.submittable_type_2.id, result_ids)
        
        # Test with mixed case False
        response = self.client.get(self.api_url, {'is_submittable': 'False'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        result_ids = [item['id'] for item in data['results']]
        self.assertIn(self.non_submittable_type.id, result_ids)
        
        # Test with lowercase
        response = self.client.get(self.api_url, {'is_submittable': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        result_ids = [item['id'] for item in data['results']]
        self.assertIn(self.non_submittable_type.id, result_ids)


class StewardModeTest(TestCase):
    """Test that stewards can see all contribution types regardless of is_submittable."""
    
    def setUp(self):
        """Set up test data for steward mode tests."""
        self.client = APIClient()
        
        # Get or create test category to avoid conflicts
        self.category, _ = Category.objects.get_or_create(
            slug='test-steward',
            defaults={
                'name': 'Test Steward Category',
                'description': 'Test steward category'
            }
        )
        
        # Create a mix of submittable and non-submittable types
        for i in range(5):
            ContributionType.objects.create(
                name=f'Type {i}',
                slug=f'type-{i}',
                description=f'Test type {i}',
                category=self.category,
                min_points=1,
                max_points=10,
                is_submittable=(i % 2 == 0)  # Even numbers are submittable
            )
        
        # Create steward user with email
        self.steward_user = User.objects.create_user(
            email='steward@test.com',
            address='0x1234567890123456789012345678901234567890',
            is_staff=True
        )
        
        self.api_url = reverse('contributiontype-list')
    
    def test_steward_can_see_all_types_without_filter(self):
        """Test that when no is_submittable filter is provided, all types are returned."""
        # This simulates steward mode where they don't send the is_submittable filter
        response = self.client.get(self.api_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Filter to only our test types (by category)
        test_types = [item for item in data['results'] if item['category'] == 'test-steward']
        
        # Should have all 5 of our test types
        self.assertEqual(len(test_types), 5)
        
        # Verify we have both submittable and non-submittable types
        submittable_count = sum(1 for item in test_types if item['is_submittable'])
        non_submittable_count = sum(1 for item in test_types if not item['is_submittable'])
        
        self.assertEqual(submittable_count, 3)  # Types 0, 2, 4
        self.assertEqual(non_submittable_count, 2)  # Types 1, 3