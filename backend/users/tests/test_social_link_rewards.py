from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contributions.models import Category, Contribution, ContributionType
from social_connections.models import DiscordConnection, GitHubConnection, TwitterConnection

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
        self.link_github_type, _ = ContributionType.objects.update_or_create(
            slug='community-link-github',
            defaults={
                'name': 'Link GitHub Account',
                'description': 'Linked GitHub account',
                'category': self.community,
                'min_points': 25,
                'max_points': 25,
                'is_submittable': False,
            },
        )

    def link_github(self):
        return GitHubConnection.objects.create(
            user=self.user,
            platform_user_id='gh-123',
            platform_username='social_user',
            linked_at=timezone.now(),
        )

    def link_twitter(self):
        return TwitterConnection.objects.create(
            user=self.user,
            platform_user_id='tw-123',
            platform_username='social_user',
            linked_at=timezone.now(),
        )

    def link_discord(self):
        return DiscordConnection.objects.create(
            user=self.user,
            platform_user_id='dc-123',
            platform_username='social_user',
            linked_at=timezone.now(),
        )

    def test_link_x_account_awards_configured_points(self):
        self.link_twitter()

        response = self.client.post('/api/v1/users/link_x_account/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'X account linked successfully! 500 points awarded.')
        contribution = Contribution.objects.get(user=self.user, contribution_type=self.link_x_type)
        self.assertEqual(contribution.points, 500)
        self.assertEqual(contribution.frozen_global_points, 500)

    def test_link_discord_account_awards_configured_points(self):
        self.link_discord()

        response = self.client.post('/api/v1/users/link_discord_account/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data['message'],
            'Discord account linked successfully! 500 points awarded.',
        )
        contribution = Contribution.objects.get(user=self.user, contribution_type=self.link_discord_type)
        self.assertEqual(contribution.points, 500)
        self.assertEqual(contribution.frozen_global_points, 500)

    def test_link_github_account_awards_configured_points(self):
        self.link_github()

        response = self.client.post('/api/v1/users/link_github_account/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'GitHub account linked successfully! 25 points awarded.')
        contribution = Contribution.objects.get(user=self.user, contribution_type=self.link_github_type)
        self.assertEqual(contribution.points, 25)
        self.assertEqual(contribution.frozen_global_points, 25)

    def test_link_github_account_requires_github_connection(self):
        response = self.client.post('/api/v1/users/link_github_account/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'You must link your GitHub account first')

    def test_link_github_account_is_idempotent(self):
        self.link_github()

        first_response = self.client.post('/api/v1/users/link_github_account/')
        second_response = self.client.post('/api/v1/users/link_github_account/')

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            second_response.data['message'],
            'You already earned points for linking your GitHub account',
        )
        self.assertEqual(
            Contribution.objects.filter(user=self.user, contribution_type=self.link_github_type).count(),
            1,
        )

    def test_link_x_account_requires_twitter_connection(self):
        response = self.client.post('/api/v1/users/link_x_account/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'You must link your X (Twitter) account first')

    def test_link_discord_account_requires_discord_connection(self):
        response = self.client.post('/api/v1/users/link_discord_account/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'You must link your Discord account first')

    def test_link_x_account_is_idempotent(self):
        self.link_twitter()

        first_response = self.client.post('/api/v1/users/link_x_account/')
        second_response = self.client.post('/api/v1/users/link_x_account/')

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            second_response.data['message'],
            'You already earned points for linking your X account',
        )
        contributions = Contribution.objects.filter(
            user=self.user,
            contribution_type=self.link_x_type,
        )
        self.assertEqual(contributions.count(), 1)
        contribution = contributions.get()
        self.assertEqual(contribution.points, 500)
        self.assertEqual(contribution.frozen_global_points, 500)

    def test_link_discord_account_is_idempotent(self):
        self.link_discord()

        first_response = self.client.post('/api/v1/users/link_discord_account/')
        second_response = self.client.post('/api/v1/users/link_discord_account/')

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            second_response.data['message'],
            'You already earned points for linking your Discord account',
        )
        contributions = Contribution.objects.filter(
            user=self.user,
            contribution_type=self.link_discord_type,
        )
        self.assertEqual(contributions.count(), 1)
        contribution = contributions.get()
        self.assertEqual(contribution.points, 500)
        self.assertEqual(contribution.frozen_global_points, 500)

    def test_link_x_account_requires_configured_contribution_type(self):
        self.link_twitter()
        self.link_x_type.delete()

        response = self.client.post('/api/v1/users/link_x_account/')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data['error'], 'Community link X contribution type not configured')

    def test_link_discord_account_requires_configured_contribution_type(self):
        self.link_discord()
        self.link_discord_type.delete()

        response = self.client.post('/api/v1/users/link_discord_account/')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data['error'], 'Community link Discord contribution type not configured')
