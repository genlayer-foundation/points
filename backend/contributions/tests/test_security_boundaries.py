"""
Regression tests for the security-hardening boundaries:

- StewardSubmissionViewSet no longer exposes router-generated write routes;
  all mutations go through the explicit custom actions.
- Evidence on pending/rejected submissions is visible only to its owner,
  staff, and stewards holding a permission on the submission's type.
- Unstarted (unannounced) missions are hidden from non-steward callers on
  list, retrieve, and stats endpoints, while expired missions stay available.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contributions.models import (
    Category,
    Contribution,
    ContributionType,
    Evidence,
    Mission,
    SubmittedContribution,
)
from leaderboard.models import GlobalLeaderboardMultiplier
from stewards.models import Steward, StewardPermission

User = get_user_model()


def _make_type(name, slug, category):
    contribution_type = ContributionType.objects.create(
        name=name,
        slug=slug,
        description=f"{name} description",
        category=category,
        min_points=1,
        max_points=100,
    )
    GlobalLeaderboardMultiplier.objects.create(
        contribution_type=contribution_type,
        multiplier_value=1,
        valid_from=timezone.now() - timezone.timedelta(days=30),
    )
    return contribution_type


class StewardSubmissionRouterLockdownTest(TestCase):
    """The steward viewset must be read-only at the router level."""

    def setUp(self):
        self.category = Category.objects.create(name="Cat", slug="cat", description="c")
        self.contribution_type = _make_type("Type A", "type-a", self.category)

        self.submitter = User.objects.create_user(
            email='submitter@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )
        self.steward_user = User.objects.create_user(
            email='steward@test.com',
            address='0x0987654321098765432109876543210987654321',
            password='testpass123',
        )
        steward = Steward.objects.create(user=self.steward_user)
        for action in ['propose', 'accept', 'reject', 'request_more_info']:
            StewardPermission.objects.create(
                steward=steward,
                contribution_type=self.contribution_type,
                action=action,
            )

        self.submission = SubmittedContribution.objects.create(
            user=self.submitter,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes="Test submission",
            state='pending',
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.steward_user)
        self.detail_url = f'/api/v1/steward-submissions/{self.submission.id}/'

    def test_router_write_methods_are_not_exposed(self):
        """PATCH/PUT/DELETE on the detail route and POST on the list route
        must not exist: state changes only happen via the custom actions."""
        response = self.client.patch(self.detail_url, {'state': 'accepted'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.put(self.detail_url, {'state': 'accepted'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.post(
            '/api/v1/steward-submissions/',
            {'user': self.submitter.id, 'contribution_type': self.contribution_type.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.state, 'pending')

    def test_read_and_custom_actions_still_work(self):
        response = self.client.get('/api/v1/steward-submissions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            f'{self.detail_url}notes/', {'message': 'A note'}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(f'{self.detail_url}notes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class EvidenceVisibilityTest(TestCase):
    """Submission evidence is scoped to owner, staff, and permitted stewards."""

    def setUp(self):
        self.category = Category.objects.create(name="Cat", slug="cat", description="c")
        self.type_a = _make_type("Type A", "type-a", self.category)
        self.type_b = _make_type("Type B", "type-b", self.category)

        self.owner = User.objects.create_user(
            email='owner@test.com',
            address='0x1111111111111111111111111111111111111111',
            password='testpass123',
        )
        self.other_user = User.objects.create_user(
            email='other@test.com',
            address='0x2222222222222222222222222222222222222222',
            password='testpass123',
        )
        self.staff_user = User.objects.create_user(
            email='staff@test.com',
            address='0x3333333333333333333333333333333333333333',
            password='testpass123',
            is_staff=True,
        )

        self.steward_a_user = User.objects.create_user(
            email='steward-a@test.com',
            address='0x4444444444444444444444444444444444444444',
            password='testpass123',
        )
        steward_a = Steward.objects.create(user=self.steward_a_user)
        StewardPermission.objects.create(
            steward=steward_a, contribution_type=self.type_a, action='accept',
        )

        self.steward_b_user = User.objects.create_user(
            email='steward-b@test.com',
            address='0x5555555555555555555555555555555555555555',
            password='testpass123',
        )
        steward_b = Steward.objects.create(user=self.steward_b_user)
        StewardPermission.objects.create(
            steward=steward_b, contribution_type=self.type_b, action='accept',
        )

        submission = SubmittedContribution.objects.create(
            user=self.owner,
            contribution_type=self.type_a,
            contribution_date=timezone.now(),
            notes="Pending submission",
            state='pending',
        )
        self.submission_evidence = Evidence.objects.create(
            submitted_contribution=submission,
            description="Pending evidence",
            url="https://example.com/pending",
        )

        contribution = Contribution.objects.create(
            user=self.owner,
            contribution_type=self.type_a,
            contribution_date=timezone.now(),
            points=10,
        )
        self.contribution_evidence = Evidence.objects.create(
            contribution=contribution,
            description="Accepted evidence",
            url="https://example.com/accepted",
        )

        self.client = APIClient()

    def _visible_ids(self, user):
        self.client.force_authenticate(user=user)
        response = self.client.get('/api/v1/evidence/', {'page_size': 100})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        return {item['id'] for item in results}

    def test_owner_sees_own_submission_evidence(self):
        ids = self._visible_ids(self.owner)
        self.assertIn(self.submission_evidence.id, ids)
        self.assertIn(self.contribution_evidence.id, ids)

    def test_other_user_cannot_see_foreign_submission_evidence(self):
        ids = self._visible_ids(self.other_user)
        self.assertNotIn(self.submission_evidence.id, ids)
        self.assertIn(self.contribution_evidence.id, ids)

    def test_steward_with_type_permission_sees_submission_evidence(self):
        ids = self._visible_ids(self.steward_a_user)
        self.assertIn(self.submission_evidence.id, ids)

    def test_steward_without_type_permission_cannot_see_submission_evidence(self):
        ids = self._visible_ids(self.steward_b_user)
        self.assertNotIn(self.submission_evidence.id, ids)
        self.assertIn(self.contribution_evidence.id, ids)

    def test_staff_sees_everything(self):
        ids = self._visible_ids(self.staff_user)
        self.assertIn(self.submission_evidence.id, ids)
        self.assertIn(self.contribution_evidence.id, ids)


class MySubmissionsDeepLinkTest(TestCase):
    """Submission notification deep links must stay reliable and owner-scoped."""

    def setUp(self):
        self.category = Category.objects.create(name="Deep", slug="deep", description="d")
        self.contribution_type = _make_type("Deep Type", "deep-type", self.category)
        self.owner = User.objects.create_user(
            email='deep-owner@test.com',
            address='0x6666666666666666666666666666666666666666',
            password='testpass123',
        )
        self.other_user = User.objects.create_user(
            email='deep-other@test.com',
            address='0x7777777777777777777777777777777777777777',
            password='testpass123',
        )
        self.submission = SubmittedContribution.objects.create(
            user=self.owner,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes="Moved on after notification",
            state='accepted',
        )
        self.other_submission = SubmittedContribution.objects.create(
            user=self.other_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes="Foreign submission",
            state='accepted',
        )
        self.client = APIClient()

    def _result_ids(self, response):
        results = response.data.get('results', response.data)
        return {item['id'] for item in results}

    def test_submission_id_filter_ignores_stale_state(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(
            '/api/v1/submissions/my/',
            {
                'state': 'more_info_needed',
                'submission': str(self.submission.id),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._result_ids(response), {str(self.submission.id)})

    def test_submission_id_filter_stays_owner_scoped(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(
            '/api/v1/submissions/my/',
            {'submission': str(self.other_submission.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._result_ids(response), set())


class MissionVisibilityTest(TestCase):
    """Unstarted missions are steward/staff-only; expired ones stay public."""

    def setUp(self):
        self.category = Category.objects.create(name="Cat", slug="cat", description="c")
        self.contribution_type = _make_type("Type A", "type-a", self.category)

        now = timezone.now()
        self.active_mission = Mission.objects.create(
            name="Active mission",
            description="Active",
            contribution_type=self.contribution_type,
            start_date=now - timezone.timedelta(days=1),
            end_date=now + timezone.timedelta(days=1),
        )
        self.expired_mission = Mission.objects.create(
            name="Expired mission",
            description="Expired",
            contribution_type=self.contribution_type,
            start_date=now - timezone.timedelta(days=10),
            end_date=now - timezone.timedelta(days=5),
        )
        self.unstarted_mission = Mission.objects.create(
            name="Unstarted mission",
            description="Unannounced",
            contribution_type=self.contribution_type,
            start_date=now + timezone.timedelta(days=5),
        )

        self.steward_user = User.objects.create_user(
            email='steward@test.com',
            address='0x0987654321098765432109876543210987654321',
            password='testpass123',
        )
        Steward.objects.create(user=self.steward_user)

        self.client = APIClient()

    def _listed_ids(self, params=None):
        response = self.client.get('/api/v1/missions/', params or {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        return {item['id'] for item in results}

    def test_anonymous_list_hides_unstarted_missions(self):
        ids = self._listed_ids({'include_inactive': '1', 'page_size': 100})
        self.assertIn(self.active_mission.id, ids)
        self.assertIn(self.expired_mission.id, ids)  # historical filters need these
        self.assertNotIn(self.unstarted_mission.id, ids)

    def test_anonymous_cannot_retrieve_unstarted_mission(self):
        response = self.client.get(f'/api/v1/missions/{self.unstarted_mission.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.get(f'/api/v1/missions/{self.unstarted_mission.id}/stats/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_can_still_access_expired_mission_detail_and_stats(self):
        response = self.client.get(f'/api/v1/missions/{self.expired_mission.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(f'/api/v1/missions/{self.expired_mission.id}/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_steward_sees_unstarted_missions(self):
        self.client.force_authenticate(user=self.steward_user)
        ids = self._listed_ids({'include_inactive': '1', 'page_size': 100})
        self.assertIn(self.unstarted_mission.id, ids)

        response = self.client.get(f'/api/v1/missions/{self.unstarted_mission.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(f'/api/v1/missions/{self.unstarted_mission.id}/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
