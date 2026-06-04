from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from builders.models import Builder
from contributions.models import Category, Contribution, ContributionType
from users.models import User
from validators.models import Validator


class ParticipantsGrowthViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.authenticated_user = User.objects.create_user(
            email='metrics@example.com',
            password='pass',
            address='0x9999999999999999999999999999999999999999',
        )
        self.client.force_authenticate(user=self.authenticated_user)
        self.validator_category, _ = Category.objects.get_or_create(
            slug='validator',
            defaults={'name': 'Validator'},
        )
        self.builder_category, _ = Category.objects.get_or_create(
            slug='builder',
            defaults={'name': 'Builder'},
        )
        self.waitlist_type, _ = ContributionType.objects.get_or_create(
            slug='validator-waitlist',
            defaults={
                'name': 'Validator Waitlist',
                'category': self.validator_category,
            },
        )
        self.builder_welcome_type, _ = ContributionType.objects.get_or_create(
            slug='builder-welcome',
            defaults={
                'name': 'Builder Welcome',
                'category': self.builder_category,
            },
        )
        self.builder_real_type, _ = ContributionType.objects.get_or_create(
            slug='builder-submission',
            defaults={
                'name': 'Builder Submission',
                'category': self.builder_category,
            },
        )
        self.validator_real_type, _ = ContributionType.objects.get_or_create(
            slug='uptime',
            defaults={
                'name': 'Uptime',
                'category': self.validator_category,
            },
        )
        self.validator_graduation_type, _ = ContributionType.objects.get_or_create(
            slug='validator',
            defaults={
                'name': 'Validator',
                'category': self.validator_category,
            },
        )

    def test_participants_growth_allows_public_metrics_page(self):
        self.client.force_authenticate(user=None)

        response = self.client.get('/api/v1/metrics/participants-growth/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)

    def test_testnet_metrics_allows_public_metrics_page(self):
        self.client.force_authenticate(user=None)

        response = self.client.get('/api/v1/metrics/testnet-kpis/?network=unknown')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def _create_user(self, email, address):
        return User.objects.create_user(
            email=email,
            password='pass',
            address=address
        )

    def test_participants_growth_deduplicates_overlapping_roles(self):
        base = timezone.now() - timedelta(days=3)

        shared_user = self._create_user('shared@example.com', '0x0000000000000000000000000000000000000001')
        waitlist_only = self._create_user('waitlist@example.com', '0x0000000000000000000000000000000000000002')
        validator_only = self._create_user('validator@example.com', '0x0000000000000000000000000000000000000003')
        active_builder = self._create_user('builder@example.com', '0x0000000000000000000000000000000000000004')
        idle_builder = self._create_user('idle@example.com', '0x0000000000000000000000000000000000000005')

        Builder.objects.create(user=shared_user, created_at=base)
        Builder.objects.create(user=active_builder, created_at=base)
        Builder.objects.create(user=idle_builder, created_at=base)
        Validator.objects.create(user=shared_user, created_at=base + timedelta(days=1))
        Validator.objects.create(user=validator_only, created_at=base + timedelta(days=2))

        Contribution.objects.bulk_create([
            Contribution(
                user=shared_user,
                contribution_type=self.waitlist_type,
                points=0,
                frozen_global_points=0,
                contribution_date=base + timedelta(days=1)
            ),
            Contribution(
                user=shared_user,
                contribution_type=self.waitlist_type,
                points=0,
                frozen_global_points=0,
                contribution_date=base + timedelta(days=2)
            ),
            Contribution(
                user=waitlist_only,
                contribution_type=self.waitlist_type,
                points=0,
                frozen_global_points=0,
                contribution_date=base + timedelta(days=2)
            ),
            # active_builder has a real accepted contribution, so they count.
            Contribution(
                user=active_builder,
                contribution_type=self.builder_real_type,
                points=10,
                frozen_global_points=10,
                contribution_date=base + timedelta(days=2)
            ),
            # idle_builder only has the welcome auto-award, so they don't count.
            Contribution(
                user=idle_builder,
                contribution_type=self.builder_welcome_type,
                points=0,
                frozen_global_points=0,
                contribution_date=base + timedelta(days=1)
            ),
            # Both Validator-profile users need a real (non-waitlist, non-`validator`)
            # validator-category contribution to qualify under the active-validator
            # rule applied by ParticipantsGrowthView.
            Contribution(
                user=shared_user,
                contribution_type=self.validator_real_type,
                points=5,
                frozen_global_points=5,
                contribution_date=base + timedelta(days=2)
            ),
            Contribution(
                user=validator_only,
                contribution_type=self.validator_real_type,
                points=5,
                frozen_global_points=5,
                contribution_date=base + timedelta(days=1)
            ),
            Contribution(
                user=shared_user,
                contribution_type=self.validator_graduation_type,
                points=0,
                frozen_global_points=0,
                contribution_date=base + timedelta(days=2)
            ),
            Contribution(
                user=validator_only,
                contribution_type=self.validator_graduation_type,
                points=0,
                frozen_global_points=0,
                contribution_date=base + timedelta(days=2)
            ),
        ])

        response = self.client.get('/api/v1/metrics/participants-growth/')

        self.assertEqual(response.status_code, 200)
        final_point = response.data['data'][-1]
        point_before_graduation = next(
            point
            for point in response.data['data']
            if point['date'] == (base + timedelta(days=1)).date().isoformat()
        )

        # validator_only has real validator activity before graduation, but the
        # chart should only count validators from their graduation date.
        self.assertEqual(point_before_graduation['validators'], 0)
        self.assertEqual(final_point['builders'], 1)
        self.assertEqual(final_point['validators'], 2)
        self.assertEqual(final_point['waitlist'], 2)
        self.assertEqual(final_point['cohort_total'], 5)
        self.assertEqual(final_point['total'], 4)
        self.assertEqual(final_point['overlap_count'], 1)
