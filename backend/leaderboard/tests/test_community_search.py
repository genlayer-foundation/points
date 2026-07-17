from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from community_xp.utils import build_effective_community_scores_queryset
from contributions.models import Category, Contribution, ContributionType
from creators.models import Creator
from leaderboard.models import GlobalLeaderboardMultiplier
from poaps.models import PoapClaim, PoapDrop
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
            category=community_category,
            max_points=10000,
        )
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=community_type,
            defaults={
                'multiplier_value': 1,
                'valid_from': timezone.now() - timezone.timedelta(days=30),
            },
        )

        self.ranked_users = {}
        for index, (name, points) in enumerate([
            ('Alice', 9000),
            ('Bob', 6000),
            ('Carol', 3000),
        ]):
            user = User.objects.create_user(
                email=f'community-{index}@example.com',
                password='pass',
                address=f'0x{str(index) * 40}',
                name=name,
            )
            self.ranked_users[name] = user
            Contribution.objects.create(
                user=user,
                contribution_type=community_type,
                points=points,
                frozen_global_points=points,
                contribution_date=timezone.now()
            )

    def create_ranked_user(self, *, name, points, suffix):
        user = User.objects.create_user(
            email=f'community-extra-{suffix}@example.com',
            password='pass',
            address=f'0x{suffix:040x}',
            name=name,
        )
        Contribution.objects.create(
            user=user,
            contribution_type=ContributionType.objects.get(slug='community-post'),
            points=points,
            frozen_global_points=points,
            contribution_date=timezone.now(),
        )
        return user

    def test_list_without_search_ranks_sequentially(self):
        response = self.client.get('/api/v1/leaderboard/community/')
        self.assertEqual(response.status_code, 200)
        results = response.data['results']
        self.assertEqual([r['user_name'] for r in results], ['Alice', 'Bob', 'Carol'])
        self.assertEqual([r['rank'] for r in results], [1, 2, 3])

    def test_negative_offset_is_clamped_to_first_page(self):
        response = self.client.get(
            '/api/v1/leaderboard/community/',
            {'limit': 2, 'offset': -1},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row['user_name'] for row in response.data['results']],
            ['Alice', 'Bob'],
        )
        self.assertEqual(
            [row['rank'] for row in response.data['results']],
            [1, 2],
        )

    def test_search_keeps_true_rank(self):
        response = self.client.get('/api/v1/leaderboard/community/', {'search': 'carol'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
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

    def test_numeric_user_lookup_keeps_true_rank(self):
        carol = self.ranked_users['Carol']

        response = self.client.get(
            '/api/v1/leaderboard/community/',
            {'user_address': str(carol.id)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user_rank'], 3)
        self.assertEqual(response.data['user_total_points'], 3000)

    def test_ties_floor_and_pagination_preserve_public_ranks(self):
        tie_before_bob = self.create_ranked_user(
            name='Aaron Tie',
            points=6000,
            suffix=10,
        )
        tie_after_bob = self.create_ranked_user(
            name='Bob',
            points=6000,
            suffix=11,
        )
        floor_user = self.create_ranked_user(
            name='Floor',
            points=2500,
            suffix=12,
        )
        below_floor = self.create_ranked_user(
            name='Below Floor',
            points=2499,
            suffix=13,
        )

        response = self.client.get(
            '/api/v1/leaderboard/community/',
            {'limit': 3, 'offset': 1},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 6)
        results = response.data['results']
        self.assertEqual(
            [row['id'] for row in results],
            [
                tie_before_bob.id,
                self.ranked_users['Bob'].id,
                tie_after_bob.id,
            ],
        )
        self.assertEqual([row['rank'] for row in results], [2, 3, 4])

        all_response = self.client.get('/api/v1/leaderboard/community/')
        self.assertEqual(all_response.data['results'][-1]['id'], floor_user.id)
        self.assertNotIn(
            below_floor.id,
            [row['id'] for row in all_response.data['results']],
        )

    def test_full_detail_scoring_query_runs_once_for_selected_page(self):
        bob = self.ranked_users['Bob']

        with patch(
            'community_xp.utils.build_effective_community_scores_queryset',
            wraps=build_effective_community_scores_queryset,
        ) as full_detail_builder:
            with CaptureQueriesContext(connection) as queries:
                response = self.client.get(
                    '/api/v1/leaderboard/community/',
                    {'limit': 1, 'offset': 1},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['id'] for row in response.data['results']], [bob.id])
        full_detail_builder.assert_called_once_with(
            user_ids=[bob.id],
            visible_only=True,
        )
        detail_queries = [
            query['sql'] for query in queries
            if '"tracked_portal_points_all_time"' in query['sql']
        ]
        self.assertEqual(len(detail_queries), 1)
        self.assertIn(
            f'"users_user"."id" IN ({bob.id})',
            detail_queries[0],
        )

    def test_hydration_skips_user_hidden_after_ranking_snapshot(self):
        bob = self.ranked_users['Bob']
        carol = self.ranked_users['Carol']

        def hide_bob_before_hydration(*, user_ids, visible_only):
            User.objects.filter(id=bob.id).update(visible=False)
            return build_effective_community_scores_queryset(
                user_ids=user_ids,
                visible_only=visible_only,
            )

        with patch(
            'community_xp.utils.build_effective_community_scores_queryset',
            side_effect=hide_bob_before_hydration,
        ):
            page_response = self.client.get(
                '/api/v1/leaderboard/community/',
                {'limit': 1, 'offset': 1},
            )

        self.assertEqual(page_response.status_code, 200)
        self.assertEqual(page_response.data['count'], 3)
        self.assertEqual(page_response.data['results'], [])

        User.objects.filter(id=bob.id).update(visible=True)
        with patch(
            'community_xp.utils.build_effective_community_scores_queryset',
            side_effect=hide_bob_before_hydration,
        ):
            context_response = self.client.get(
                '/api/v1/leaderboard/community/',
                {
                    'user_address': carol.address,
                    'profile_context': 'true',
                },
            )

        self.assertEqual(context_response.status_code, 200)
        self.assertEqual(context_response.data['count'], 3)
        self.assertEqual(context_response.data['user_rank'], 3)
        self.assertEqual(context_response.data['top_entry']['user_name'], 'Alice')
        self.assertEqual(
            [row['user_name'] for row in context_response.data['context_results']],
            ['Carol'],
        )
        self.assertEqual(
            [row['rank'] for row in context_response.data['context_results']],
            [3],
        )

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

    def test_list_uses_public_ranking_floor_not_member_role(self):
        creator_only = User.objects.create_user(
            email='creator-only@example.com',
            password='pass',
            address='0x' + '4' * 40,
            name='Creator Only',
        )
        Creator.objects.create(user=creator_only)

        link_type, _ = ContributionType.objects.get_or_create(
            slug='community-link-x',
            defaults={
                'name': 'Community Link X',
                'category': Category.objects.get(slug='community'),
                'max_points': 500,
            },
        )
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=link_type,
            defaults={
                'multiplier_value': 1,
                'valid_from': timezone.now() - timezone.timedelta(days=30),
            },
        )
        link_only = User.objects.create_user(
            email='link-only@example.com',
            password='pass',
            address='0x' + '5' * 40,
            name='Link Only',
        )
        Contribution.objects.create(
            user=link_only,
            contribution_type=link_type,
            points=500,
            frozen_global_points=500,
            contribution_date=timezone.now()
        )

        poap_user = User.objects.create_user(
            email='poap-member@example.com',
            password='pass',
            address='0x' + '6' * 40,
            name='POAP Member',
        )
        drop = PoapDrop.objects.create(
            title='Community Call',
            slug='community-call',
            event_start_at=timezone.now(),
            status=PoapDrop.STATUS_ACTIVE,
        )
        PoapClaim.objects.create(
            drop=drop,
            user=poap_user,
            claim_method=PoapClaim.CLAIM_ADMIN,
        )

        response = self.client.get('/api/v1/leaderboard/community/')

        self.assertEqual(response.status_code, 200)
        names = [r['user_name'] for r in response.data['results']]
        self.assertNotIn('Creator Only', names)
        self.assertNotIn('Link Only', names)
        self.assertNotIn('POAP Member', names)
        self.assertEqual(response.data['count'], 3)

    def test_low_point_member_profile_context_has_no_rank(self):
        low_point_user = User.objects.create_user(
            email='low-point-community@example.com',
            password='pass',
            address='0x' + '8' * 40,
            name='Low Point Member',
        )
        Contribution.objects.create(
            user=low_point_user,
            contribution_type=ContributionType.objects.get(slug='community-post'),
            points=1200,
            frozen_global_points=1200,
            contribution_date=timezone.now()
        )

        response = self.client.get(
            '/api/v1/leaderboard/community/',
            {
                'user_address': low_point_user.address,
                'profile_context': 'true',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['user_rank'])
        self.assertEqual(response.data['context_results'], [])
        self.assertEqual(response.data['top_entry']['user_name'], 'Alice')

    def test_creator_only_profile_context_has_no_rank(self):
        creator_only = User.objects.create_user(
            email='unranked-creator@example.com',
            password='pass',
            address='0x' + '7' * 40,
            name='Unranked Creator',
        )
        Creator.objects.create(user=creator_only)

        response = self.client.get(
            '/api/v1/leaderboard/community/',
            {
                'user_address': creator_only.address,
                'profile_context': 'true',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['user_rank'])
        self.assertEqual(response.data['context_results'], [])
        self.assertEqual(response.data['top_entry']['user_name'], 'Alice')
