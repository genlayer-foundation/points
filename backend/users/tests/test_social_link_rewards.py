from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contributions.models import Category, Contribution, ContributionType
from social_connections.models import DiscordConnection, TwitterConnection

User = get_user_model()


class SocialLinkRewardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='social-link@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )
        self.client.force_authenticate(user=self.user)
        self.community, _ = Category.objects.get_or_create(
            slug='community',
            defaults={
                'name': 'Community',
                'description': 'Community contributions',
            },
        )
        self.link_x_type, _ = ContributionType.objects.update_or_create(
            slug='community-link-x',
            defaults={
                'name': 'Link X Account',
                'description': 'Linked X account',
                'category': self.community,
                'min_points': 500,
                'max_points': 500,
                'is_submittable': False,
            },
        )
        self.link_discord_type, _ = ContributionType.objects.update_or_create(
            slug='community-link-discord',
            defaults={
                'name': 'Link Discord Account',
                'description': 'Linked Discord account',
                'category': self.community,
                'min_points': 500,
                'max_points': 500,
                'is_submittable': False,
            },
        )

    def test_link_x_account_awards_configured_points(self):
        TwitterConnection.objects.create(
            user=self.user,
            platform_user_id='tw-123',
            platform_username='social_user',
            linked_at=timezone.now(),
        )

        response = self.client.post('/api/v1/users/link_x_account/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'X account linked successfully! 500 points awarded.')
        contribution = Contribution.objects.get(user=self.user, contribution_type=self.link_x_type)
        self.assertEqual(contribution.points, 500)
        self.assertEqual(contribution.frozen_global_points, 500)

    def test_link_discord_account_awards_configured_points(self):
        DiscordConnection.objects.create(
            user=self.user,
            platform_user_id='dc-123',
            platform_username='social_user',
            linked_at=timezone.now(),
        )

        response = self.client.post('/api/v1/users/link_discord_account/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data['message'],
            'Discord account linked successfully! 500 points awarded.',
        )
        contribution = Contribution.objects.get(user=self.user, contribution_type=self.link_discord_type)
        self.assertEqual(contribution.points, 500)
        self.assertEqual(contribution.frozen_global_points, 500)
