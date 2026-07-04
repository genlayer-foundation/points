"""Builder journey role grants are point-free.

The boilerplate-star social task gates the role grant. The old farmable
`builder-welcome` (+20) / `builder` (+50) awards are gone for new journey
starts, while any configured task points remain normal earned points.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contributions.models import Category, Contribution, ContributionType
from leaderboard.models import GlobalLeaderboardMultiplier
from social_tasks.models import SocialTask, SocialTaskCompletion

User = get_user_model()


class BuilderJourneyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='builder@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )
        self.client.force_authenticate(user=self.user)
        self.builder_cat, _ = Category.objects.get_or_create(
            slug='builder', defaults={'name': 'Builder', 'description': 'Builder tasks.'},
        )
        # Self-contained: ensure the gate task exists regardless of seed state.
        self.star_task, _ = SocialTask.objects.get_or_create(
            slug=settings.BUILDER_JOURNEY_TASK_SLUG,
            defaults={
                'name': 'Star the GenLayer boilerplate',
                'category': self.builder_cat,
                'points': 500,
                'verification_type': 'github_star',
                'target_repo': 'genlayerlabs/genlayer-project-boilerplate',
                'action_url': 'https://github.com/genlayerlabs/genlayer-project-boilerplate',
                'platform': 'github',
            },
        )

    def complete_star_task(self):
        return SocialTaskCompletion.objects.create(
            user=self.user,
            task=self.star_task,
            points_awarded=self.star_task.points,
            verification_type='github_star',
        )

    def test_seed_migration_created_builder_star_task(self):
        """The 0004 seed registers the gate task as a builder github_star task."""
        task = SocialTask.objects.get(slug=settings.BUILDER_JOURNEY_TASK_SLUG)
        self.assertEqual(task.verification_type, 'github_star')
        self.assertEqual(task.category.slug, 'builder')

    def test_start_builder_journey_creates_point_free_marker(self):
        response = self.client.post('/api/v1/users/start_builder_journey/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # A 0-point "builder-welcome" marker persists "journey started" — no points.
        marker = Contribution.objects.get(
            user=self.user, contribution_type__slug='builder-welcome'
        )
        self.assertEqual(marker.points, 0)
        self.assertFalse(hasattr(self.user, 'builder'))

    def test_start_builder_journey_is_idempotent(self):
        first = self.client.post('/api/v1/users/start_builder_journey/')
        second = self.client.post('/api/v1/users/start_builder_journey/')

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Contribution.objects.filter(
                user=self.user, contribution_type__slug='builder-welcome'
            ).count(),
            1,
        )

    def test_start_role_journey_marks_validator_and_community_point_free(self):
        for role, slug in [('validator', 'validator-welcome'), ('community', 'community-welcome')]:
            resp = self.client.post('/api/v1/users/start_role_journey/', {'role': role})
            self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
            marker = Contribution.objects.get(
                user=self.user, contribution_type__slug=slug
            )
            self.assertEqual(marker.points, 0)

    def test_start_role_journey_is_idempotent(self):
        first = self.client.post('/api/v1/users/start_role_journey/', {'role': 'community'})
        second = self.client.post('/api/v1/users/start_role_journey/', {'role': 'community'})

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Contribution.objects.filter(
                user=self.user, contribution_type__slug='community-welcome'
            ).count(),
            1,
        )

    def test_start_role_journey_rejects_unknown_role(self):
        resp = self.client.post('/api/v1/users/start_role_journey/', {'role': 'steward'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_start_validator_journey_also_marks_journey_started(self):
        validator_cat, _ = Category.objects.get_or_create(
            slug='validator',
            defaults={'name': 'Validator', 'description': 'Validator tasks.'},
        )
        waitlist_type, _ = ContributionType.objects.update_or_create(
            slug='validator-waitlist',
            defaults={
                'name': 'Validator Waitlist',
                'category': validator_cat,
                'is_submittable': False,
                'min_points': 0,
                'max_points': 0,
            },
        )
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=waitlist_type,
            defaults={
                'multiplier_value': 1.0,
                'valid_from': timezone.now() - timezone.timedelta(days=1),
            },
        )

        resp = self.client.post('/api/v1/users/start_validator_journey/')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Contribution.objects.filter(
                user=self.user,
                contribution_type__slug='validator-welcome',
                points=0,
            ).exists()
        )
        self.assertTrue(
            Contribution.objects.filter(
                user=self.user,
                contribution_type__slug='validator-waitlist',
                points=0,
            ).exists()
        )

    def test_complete_requires_starring_the_boilerplate(self):
        response = self.client.post('/api/v1/users/complete_builder_journey/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(hasattr(self.user, 'builder'))

    def test_complete_grants_role_point_free(self):
        self.complete_star_task()

        response = self.client.post('/api/v1/users/complete_builder_journey/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.user.refresh_from_db()
        self.assertTrue(hasattr(self.user, 'builder'))
        # Role grant creates NO contribution and awards NO points.
        self.assertFalse(
            Contribution.objects.filter(user=self.user, contribution_type__slug='builder').exists()
        )
        self.assertEqual(
            Contribution.objects.filter(user=self.user).count(), 0
        )

    def test_complete_is_idempotent(self):
        self.complete_star_task()

        first = self.client.post('/api/v1/users/complete_builder_journey/')
        second = self.client.post('/api/v1/users/complete_builder_journey/')

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        from builders.models import Builder
        self.assertEqual(Builder.objects.filter(user=self.user).count(), 1)
