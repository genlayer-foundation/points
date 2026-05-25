from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contributions.models import Category, Contribution, ContributionType, Mission
from leaderboard.models import GlobalLeaderboardMultiplier

User = get_user_model()


class PublicExplorerFiltersTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(
            name='Explorer Test',
            slug='explorer-test',
            description='Explorer test category',
        )
        self.user = User.objects.create_user(
            email='explorer-user@test.com',
            address='0x0000000000000000000000000000000000000001',
            password='testpass123',
        )

        self.submittable_type = self._create_type(
            'Submittable Explorer Type',
            'submittable-explorer-type',
            is_submittable=True,
        )
        self.visible_type = self._create_type(
            'Visible Non-Submittable Explorer Type',
            'visible-non-submittable-explorer-type',
            is_submittable=False,
            show_in_contributions=True,
        )
        self.hidden_type = self._create_type(
            'Hidden Non-Submittable Explorer Type',
            'hidden-non-submittable-explorer-type',
            is_submittable=False,
            show_in_contributions=False,
        )

        self.active_mission = Mission.objects.create(
            name='Active Explorer Mission',
            description='Active mission',
            contribution_type=self.submittable_type,
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=1),
        )
        self.inactive_mission = Mission.objects.create(
            name='Inactive Explorer Mission',
            description='Inactive mission',
            contribution_type=self.submittable_type,
            start_date=timezone.now() - timedelta(days=3),
            end_date=timezone.now() - timedelta(days=1),
        )

        self.submittable_contribution = self._create_contribution(self.submittable_type)
        self.visible_contribution = self._create_contribution(self.visible_type)
        self.hidden_contribution = self._create_contribution(self.hidden_type)
        self.active_mission_contribution = self._create_contribution(
            self.submittable_type,
            mission=self.active_mission,
        )
        self.inactive_mission_contribution = self._create_contribution(
            self.submittable_type,
            mission=self.inactive_mission,
        )

    def _create_type(self, name, slug, **kwargs):
        contribution_type = ContributionType.objects.create(
            name=name,
            slug=slug,
            description=name,
            category=self.category,
            min_points=1,
            max_points=100,
            **kwargs,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=contribution_type,
            multiplier_value=1,
            valid_from=timezone.now() - timedelta(days=30),
        )
        return contribution_type

    def _create_contribution(self, contribution_type, mission=None):
        return Contribution.objects.create(
            user=self.user,
            contribution_type=contribution_type,
            mission=mission,
            points=10,
            contribution_date=timezone.now(),
            title=f'{contribution_type.name} contribution',
        )

    def _result_ids(self, response):
        data = response.json()
        return {item['id'] for item in data['results']}

    def test_public_explorer_includes_public_non_submittable_types(self):
        response = self.client.get('/api/v1/contributions/', {
            'category': self.category.slug,
            'public_explorer_only': 'true',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = self._result_ids(response)
        self.assertIn(self.submittable_contribution.id, result_ids)
        self.assertIn(self.visible_contribution.id, result_ids)
        self.assertNotIn(self.hidden_contribution.id, result_ids)

    def test_public_explorer_does_not_leak_hidden_type_when_type_is_explicit(self):
        response = self.client.get('/api/v1/contributions/', {
            'contribution_type': self.hidden_type.id,
            'public_explorer_only': 'true',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.hidden_contribution.id, self._result_ids(response))

    def test_contributions_can_filter_by_inactive_mission(self):
        response = self.client.get('/api/v1/contributions/', {
            'category': self.category.slug,
            'mission': self.inactive_mission.id,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = self._result_ids(response)
        self.assertIn(self.inactive_mission_contribution.id, result_ids)
        self.assertNotIn(self.active_mission_contribution.id, result_ids)
        self.assertNotIn(self.submittable_contribution.id, result_ids)

    def test_mission_list_can_include_inactive_missions(self):
        response = self.client.get('/api/v1/missions/', {
            'include_inactive': 'true',
            'category': self.category.slug,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = {item['id'] for item in response.json()['results']}
        self.assertIn(self.inactive_mission.id, result_ids)
        self.assertIn(self.active_mission.id, result_ids)
