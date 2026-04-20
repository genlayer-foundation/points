from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from contributions.models import Contribution, ContributionType, Category
from validators.models import Validator

User = get_user_model()


class ValidatorCategorySubmitGatingTest(TestCase):
    """Only users with a Validator profile may submit validator-category contributions.

    Having the validator-waitlist contribution no longer grants submit access.
    """

    def setUp(self):
        self.validator_category, _ = Category.objects.get_or_create(
            slug='validator',
            defaults={'name': 'Validator', 'description': 'Validator contributions'},
        )
        self.waitlist_type, _ = ContributionType.objects.get_or_create(
            slug='validator-waitlist',
            defaults={
                'name': 'Validator Waitlist',
                'description': 'Joined the validator waitlist',
                'category': self.validator_category,
                'min_points': 0,
                'max_points': 0,
            },
        )
        self.node_running_type, _ = ContributionType.objects.get_or_create(
            slug='node-running',
            defaults={
                'name': 'Node Running',
                'description': 'Running a validator node',
                'category': self.validator_category,
                'min_points': 10,
                'max_points': 100,
            },
        )

        self.waitlist_user = User.objects.create_user(
            email='waitlist@test.com',
            address='0x1111111111111111111111111111111111111111',
            password='testpass123',
        )
        self.plain_user = User.objects.create_user(
            email='plain@test.com',
            address='0x2222222222222222222222222222222222222222',
            password='testpass123',
        )
        self.validator_user = User.objects.create_user(
            email='validator@test.com',
            address='0x3333333333333333333333333333333333333333',
            password='testpass123',
        )
        Validator.objects.create(user=self.validator_user)

        Contribution.objects.create(
            user=self.waitlist_user,
            contribution_type=self.waitlist_type,
            points=0,
            frozen_global_points=0,
            contribution_date=timezone.now(),
        )

        self.client = APIClient()

    def _post_submission(self, user, contribution_type):
        self.client.force_authenticate(user=user)
        return self.client.post(
            '/api/v1/submissions/',
            {
                'contribution_type': contribution_type.id,
                'contribution_date': timezone.now().date().isoformat(),
                'notes': 'Attempted submission',
                'recaptcha': 'test-token',
            },
            format='json',
        )

    def test_user_without_validator_profile_is_blocked(self):
        response = self._post_submission(self.plain_user, self.node_running_type)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Only validators', response.data['error'])

    def test_waitlist_user_without_validator_profile_is_blocked(self):
        """A user with only the waitlist contribution cannot submit validator contributions."""
        response = self._post_submission(self.waitlist_user, self.node_running_type)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Only validators', response.data['error'])

    def test_user_with_validator_profile_passes_gating(self):
        response = self._post_submission(self.validator_user, self.node_running_type)
        # May be 201 or 400 depending on recaptcha config, but must not be 403
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
