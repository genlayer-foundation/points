from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contributions.models import Category, ContributionType, Mission, SubmittedContribution

User = get_user_model()


class SubmissionLimitTest(TestCase):
    """Tests optional submission caps for contribution types and missions."""

    def setUp(self):
        self.category = Category.objects.create(
            name='Test', slug='test', description='Test',
        )
        self.contribution_type = ContributionType.objects.create(
            name='Limited Type',
            slug='limited-type',
            description='Test type',
            category=self.category,
            min_points=1,
            max_points=10,
        )
        self.user = User.objects.create_user(
            email='user@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )
        self.other_user = User.objects.create_user(
            email='other@test.com',
            address='0x2222222222222222222222222222222222222222',
            password='testpass123',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.recaptcha_patcher = patch(
            'contributions.recaptcha_field.ReCaptchaField.to_internal_value',
            return_value='test-token',
        )
        self.recaptcha_patcher.start()
        self.addCleanup(self.recaptcha_patcher.stop)

    def _create_submission(self, state='pending', mission=None, user=None):
        return SubmittedContribution.objects.create(
            user=user or self.other_user,
            contribution_type=self.contribution_type,
            mission=mission,
            contribution_date=timezone.now(),
            notes='Existing submission',
            state=state,
        )

    def _post_submission(self, contribution_type=None, mission=None):
        payload = {
            'contribution_type': (contribution_type or self.contribution_type).id,
            'contribution_date': timezone.now().date().isoformat(),
            'notes': 'Attempted submission',
            'recaptcha': 'test-token',
            'evidence_items': [
                {
                    'description': 'Evidence',
                    'url': f'https://example.com/evidence/{timezone.now().timestamp()}',
                },
            ],
        }
        if mission:
            payload['mission'] = mission.id
        return self.client.post('/api/v1/submissions/', payload, format='json')

    def test_contribution_type_limit_blocks_new_submissions(self):
        self.contribution_type.max_submissions = 1
        self.contribution_type.save(update_fields=['max_submissions'])
        self._create_submission(state='pending')

        response = self._post_submission()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('contribution type', response.data['error'])
        self.assertIn('submission limit', response.data['error'])

    def test_rejected_submissions_do_not_consume_type_capacity(self):
        self.contribution_type.max_submissions = 1
        self.contribution_type.save(update_fields=['max_submissions'])
        self._create_submission(state='rejected')

        response = self._post_submission()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_canceled_submissions_do_not_consume_type_capacity(self):
        self.contribution_type.max_submissions = 1
        self.contribution_type.save(update_fields=['max_submissions'])
        self._create_submission(state='canceled')

        response = self._post_submission()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_mission_limit_blocks_new_submissions(self):
        mission = Mission.objects.create(
            name='Limited Mission',
            description='Test mission',
            contribution_type=self.contribution_type,
            max_submissions=1,
        )
        self._create_submission(state='accepted', mission=mission)

        response = self._post_submission(mission=mission)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('mission', response.data['error'])
        self.assertIn('submission limit', response.data['error'])

    def test_rejected_submissions_do_not_consume_mission_capacity(self):
        mission = Mission.objects.create(
            name='Limited Mission',
            description='Test mission',
            contribution_type=self.contribution_type,
            max_submissions=1,
        )
        self._create_submission(state='rejected', mission=mission)

        response = self._post_submission(mission=mission)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_canceled_submissions_do_not_consume_mission_capacity(self):
        mission = Mission.objects.create(
            name='Limited Mission',
            description='Test mission',
            contribution_type=self.contribution_type,
            max_submissions=1,
        )
        self._create_submission(state='canceled', mission=mission)

        response = self._post_submission(mission=mission)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_mission_per_user_limit_blocks_same_user(self):
        mission = Mission.objects.create(
            name='Per User Limited Mission',
            description='Test mission',
            contribution_type=self.contribution_type,
            max_submissions_per_user=1,
        )
        self._create_submission(state='pending', mission=mission, user=self.user)

        response = self._post_submission(mission=mission)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('your submission limit', response.data['error'])
        self.assertIn('mission', response.data['error'])

    def test_other_users_do_not_consume_mission_per_user_capacity(self):
        mission = Mission.objects.create(
            name='Per User Limited Mission',
            description='Test mission',
            contribution_type=self.contribution_type,
            max_submissions_per_user=1,
        )
        self._create_submission(state='pending', mission=mission, user=self.other_user)

        response = self._post_submission(mission=mission)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_rejected_submissions_do_not_consume_mission_per_user_capacity(self):
        mission = Mission.objects.create(
            name='Per User Limited Mission',
            description='Test mission',
            contribution_type=self.contribution_type,
            max_submissions_per_user=1,
        )
        self._create_submission(state='rejected', mission=mission, user=self.user)

        response = self._post_submission(mission=mission)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_canceled_submissions_do_not_consume_mission_per_user_capacity(self):
        mission = Mission.objects.create(
            name='Per User Limited Mission',
            description='Test mission',
            contribution_type=self.contribution_type,
            max_submissions_per_user=1,
        )
        self._create_submission(state='canceled', mission=mission, user=self.user)

        response = self._post_submission(mission=mission)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_mission_api_exposes_capacity_fields(self):
        mission = Mission.objects.create(
            name='Limited Mission',
            description='Test mission',
            contribution_type=self.contribution_type,
            max_submissions=2,
            max_submissions_per_user=1,
        )
        self._create_submission(state='pending', mission=mission, user=self.user)

        response = self.client.get(f'/api/v1/missions/{mission.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['max_submissions'], 2)
        self.assertEqual(response.data['max_submissions_per_user'], 1)
        self.assertEqual(response.data['submission_count'], 1)
        self.assertEqual(response.data['submissions_remaining'], 1)
        self.assertFalse(response.data['is_full'])
        self.assertEqual(response.data['user_submission_count'], 1)
        self.assertEqual(response.data['user_submissions_remaining'], 0)
        self.assertTrue(response.data['user_is_full'])

    def test_mission_list_exposes_capacity_fields_with_constant_queries(self):
        self.contribution_type.max_submissions = 4
        self.contribution_type.save(update_fields=['max_submissions'])
        mission = Mission.objects.create(
            name='Limited Mission',
            description='Test mission',
            contribution_type=self.contribution_type,
            max_submissions=3,
            max_submissions_per_user=1,
        )
        other_mission = Mission.objects.create(
            name='Other Mission',
            description='Other mission',
            contribution_type=self.contribution_type,
        )
        self._create_submission(state='pending', mission=mission, user=self.user)
        self._create_submission(state='accepted', mission=mission, user=self.other_user)
        self._create_submission(state='canceled', mission=mission, user=self.other_user)
        self._create_submission(state='pending', mission=other_mission, user=self.other_user)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get('/api/v1/missions/?include_inactive=true&page_size=100')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(queries), 4)

        missions = response.data['results']
        mission_data = next(
            item for item in missions if item['id'] == mission.id
        )
        type_data = mission_data['contribution_type_details']

        self.assertEqual(mission_data['submission_count'], 2)
        self.assertEqual(mission_data['submissions_remaining'], 1)
        self.assertFalse(mission_data['is_full'])
        self.assertEqual(mission_data['user_submission_count'], 1)
        self.assertEqual(mission_data['user_submissions_remaining'], 0)
        self.assertTrue(mission_data['user_is_full'])
        self.assertEqual(type_data['submission_count'], 3)
        self.assertEqual(type_data['submissions_remaining'], 1)
        self.assertFalse(type_data['is_full'])

    def test_contribution_type_api_exposes_capacity_fields(self):
        self.contribution_type.max_submissions = 2
        self.contribution_type.save(update_fields=['max_submissions'])
        self._create_submission(state='pending')
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            f'/api/v1/contribution-types/{self.contribution_type.id}/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['max_submissions'], 2)
        self.assertEqual(response.data['submission_count'], 1)
        self.assertEqual(response.data['submissions_remaining'], 1)
        self.assertFalse(response.data['is_full'])
