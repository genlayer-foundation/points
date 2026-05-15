from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contributions.models import Category, ContributionType, SubmittedContribution

User = get_user_model()


class CanceledSubmissionMetricsTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Test', slug='test', description='Test',
        )
        self.contribution_type = ContributionType.objects.create(
            name='Test Type',
            slug='test-type',
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
        self.client = APIClient()

    def _create_submission(self, state, staff_reply=''):
        return SubmittedContribution.objects.create(
            user=self.user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Test submission',
            state=state,
            staff_reply=staff_reply,
            reviewed_at=timezone.now(),
        )

    def test_canceled_submissions_are_not_counted_as_rejected(self):
        self._create_submission(state='rejected', staff_reply='Not valid')
        self._create_submission(state='canceled', staff_reply='Canceled by user')

        today = timezone.now().date().isoformat()
        response = self.client.get(
            '/api/v1/steward-submissions/daily-metrics/',
            {
                'group_by': 'day',
                'start_date': today,
                'end_date': today,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['totals']['rejected'], 1)
        self.assertEqual(response.data['totals']['canceled'], 1)

    def test_canceled_submissions_are_not_reviewed_decisions(self):
        self._create_submission(state='rejected', staff_reply='Not valid')
        self._create_submission(state='canceled', staff_reply='Canceled by user')

        response = self.client.get('/api/v1/steward-submissions/stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_reviewed'], 1)
        self.assertEqual(response.data['total_rejected'], 1)
