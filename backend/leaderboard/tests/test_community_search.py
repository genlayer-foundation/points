from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from contributions.models import Category, Contribution, ContributionType
from leaderboard.models import GlobalLeaderboardMultiplier
from users.models import User


class CommunityLeaderboardSearchTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.viewer = User.objects.create_user(
            email='community-viewer@example.com',
            password='pass',
            address='0xffffffffffffffffffffffffffffffffffffffff',
        )
        self.client.force_authenticate(user=self.viewer)

        community_category, _ = Category.objects.get_or_create(
            slug='community',
            defaults={'name': 'Community'}
        )
        community_type = ContributionType.objects.create(
            name='Community Post',
            slug='community-post',
            category=community_category
        )
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=community_type,
            defaults={
                'multiplier_value': 1,
                'valid_from': timezone.now() - timezone.timedelta(days=30),
            },
        )

        for index, (name, points) in enumerate([
            ('Alice', 90),
            ('Bob', 60),
            ('Carol', 30),
        ]):
            user = User.objects.create_user(
                email=f'community-{index}@example.com',
                password='pass',
                address=f'0x{str(index) * 40}',
                name=name,
            )
            Contribution.objects.create(
                user=user,
                contribution_type=community_type,
                points=points,
                frozen_global_points=points,
                contribution_date=timezone.now()
            )

    def test_list_without_search_ranks_sequentially(self):
        response = self.client.get('/api/v1/leaderboard/community/')
        self.assertEqual(response.status_code, 200)
        results = response.data['results']
        self.assertEqual([r['user_name'] for r in results], ['Alice', 'Bob', 'Carol'])
        self.assertEqual([r['rank'] for r in results], [1, 2, 3])

    def test_search_keeps_true_rank(self):
        response = self.client.get('/api/v1/leaderboard/community/', {'search': 'carol'})
        self.assertEqual(response.status_code, 200)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['user_name'], 'Carol')
        self.assertEqual(results[0]['rank'], 3)

    def test_user_rank_ignores_search_filter(self):
        response = self.client.get(
            '/api/v1/leaderboard/community/',
            {'search': 'bob', 'user_address': '0x' + '1' * 40},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user_rank'], 2)

    def test_profile_context_ignores_search_filter(self):
        response = self.client.get(
            '/api/v1/leaderboard/community/',
            {
                'search': 'carol',
                'user_address': '0x' + '2' * 40,
                'profile_context': 'true',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user_rank'], 3)
        self.assertEqual(response.data['top_entry']['user_name'], 'Alice')
        context = response.data['context_results']
        self.assertEqual([r['user_name'] for r in context], ['Bob', 'Carol'])
        self.assertEqual([r['rank'] for r in context], [2, 3])
