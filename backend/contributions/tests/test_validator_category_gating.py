from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from contributions.models import Contribution, ContributionType, Category, SubmittedContribution
from creators.models import Creator
from leaderboard.models import GlobalLeaderboardMultiplier
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
        self.builder_category, _ = Category.objects.get_or_create(
            slug='builder',
            defaults={'name': 'Builder', 'description': 'Builder contributions'},
        )
        self.builder_type, _ = ContributionType.objects.get_or_create(
            slug='builder-only-test',
            defaults={
                'name': 'Builder Only Test',
                'description': 'Builder restricted test type',
                'category': self.builder_category,
                'min_points': 10,
                'max_points': 100,
            },
        )
        self.community_category, _ = Category.objects.get_or_create(
            slug='community',
            defaults={'name': 'Community', 'description': 'Community contributions'},
        )
        self.community_type, _ = ContributionType.objects.get_or_create(
            slug='community-test',
            defaults={
                'name': 'Community Test',
                'description': 'Creator restricted test type',
                'category': self.community_category,
                'min_points': 1,
                'max_points': 10,
            },
        )
        self.unrestricted_type, _ = ContributionType.objects.get_or_create(
            slug='unrestricted-test',
            defaults={
                'name': 'Unrestricted Test',
                'description': 'Unrestricted test type',
                'category': None,
                'min_points': 1,
                'max_points': 10,
            },
        )
        self.capacity_limited_type, _ = ContributionType.objects.get_or_create(
            slug='capacity-limited-test',
            defaults={
                'name': 'Capacity Limited Test',
                'description': 'Capacity-limited unrestricted test type',
                'category': None,
                'min_points': 1,
                'max_points': 10,
                'max_submissions': 1,
            },
        )
        self.mission_only_type, _ = ContributionType.objects.get_or_create(
            slug='mission-only-test',
            defaults={
                'name': 'Mission Only Test',
                'description': 'Mission-only test type',
                'category': None,
                'min_points': 1,
                'max_points': 10,
                'is_submittable': False,
            },
        )
        for contribution_type in [
            self.waitlist_type,
            self.node_running_type,
            self.builder_type,
            self.community_type,
            self.unrestricted_type,
            self.capacity_limited_type,
            self.mission_only_type,
        ]:
            GlobalLeaderboardMultiplier.objects.create(
                contribution_type=contribution_type,
                multiplier_value=1,
                valid_from=timezone.now() - timezone.timedelta(days=1),
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
        self.creator_user = User.objects.create_user(
            email='creator@test.com',
            address='0x4444444444444444444444444444444444444444',
            password='testpass123',
        )
        Creator.objects.create(user=self.creator_user)

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

    def test_user_without_creator_profile_is_blocked_from_community_category(self):
        response = self._post_submission(self.plain_user, self.community_type)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Only creators', response.data['error'])

    def test_user_with_creator_profile_passes_community_gating(self):
        response = self._post_submission(self.creator_user, self.community_type)
        # May be 201 or 400 depending on recaptcha config, but must not be 403
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def _pending_submission(self, user=None):
        return SubmittedContribution.objects.create(
            user=user or self.plain_user,
            contribution_type=self.unrestricted_type,
            contribution_date=timezone.now(),
            notes='Original unrestricted submission',
            state='pending',
        )

    def test_plain_user_cannot_edit_submission_into_validator_type(self):
        submission = self._pending_submission()
        self.client.force_authenticate(user=self.plain_user)

        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            {'contribution_type': self.node_running_type.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        submission.refresh_from_db()
        self.assertEqual(submission.contribution_type, self.unrestricted_type)

    def test_plain_user_cannot_edit_submission_into_builder_type(self):
        submission = self._pending_submission()
        self.client.force_authenticate(user=self.plain_user)

        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            {'contribution_type': self.builder_type.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        submission.refresh_from_db()
        self.assertEqual(submission.contribution_type, self.unrestricted_type)

    def test_plain_user_cannot_edit_submission_into_community_type(self):
        submission = self._pending_submission()
        self.client.force_authenticate(user=self.plain_user)

        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            {'contribution_type': self.community_type.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Only creators', response.data['error'])
        submission.refresh_from_db()
        self.assertEqual(submission.contribution_type, self.unrestricted_type)

    def test_plain_user_cannot_edit_submission_into_mission_only_type(self):
        submission = self._pending_submission()
        self.client.force_authenticate(user=self.plain_user)

        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            {'contribution_type': self.mission_only_type.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        submission.refresh_from_db()
        self.assertEqual(submission.contribution_type, self.unrestricted_type)

    def test_user_can_edit_submission_when_unchanged_type_is_full(self):
        submission = SubmittedContribution.objects.create(
            user=self.plain_user,
            contribution_type=self.capacity_limited_type,
            contribution_date=timezone.now(),
            notes='Original notes',
            state='pending',
        )
        self.assertTrue(self.capacity_limited_type.is_full())
        self.client.force_authenticate(user=self.plain_user)

        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            {'notes': 'Updated notes'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        submission.refresh_from_db()
        self.assertEqual(submission.notes, 'Updated notes')
        self.assertEqual(submission.contribution_type, self.capacity_limited_type)
