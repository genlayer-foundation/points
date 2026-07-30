"""
Query-count guards for the community score paths.

The community ranking queryset scans every visible user with correlated
subqueries, so each extra evaluation of it is a full population scan. These
tests pin how many times a request is allowed to run one.
"""

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from contributions.models import Category, Contribution, ContributionType
from leaderboard.models import GlobalLeaderboardMultiplier
from users.models import User
from community_xp.cache import clear_community_caches


# A full-population scan selects from users_user and carries the correlated
# MEE6 subquery. Matching on annotation aliases does not work here: values_list()
# inlines the expressions and drops the alias names. The bounded full-detail
# hydration query shares both markers, so it is excluded by the one annotation
# only it selects.
SCAN_FROM_MARKER = 'FROM "users_user"'
SCAN_SUBQUERY_MARKER = '"community_xp_mee6currentxp" U0'
DETAIL_MARKER = 'tracked_portal_points_all_time'


def count_ranking_scans(captured_queries):
    return len([
        query for query in captured_queries
        if SCAN_FROM_MARKER in query['sql']
        and SCAN_SUBQUERY_MARKER in query['sql']
        and DETAIL_MARKER not in query['sql']
    ])


class CommunityRankingQueryCountTest(TestCase):
    def setUp(self):
        # The community ranking/summary aggregates are cached briefly and
        # LocMemCache is not reset between tests.
        clear_community_caches()
        self.client = APIClient()
        self.viewer = User.objects.create_user(
            email='counts-viewer@example.com',
            password='pass',
            address='0xffffffffffffffffffffffffffffffffffffffff',
        )
        self.client.force_authenticate(user=self.viewer)

        community_category, _ = Category.objects.get_or_create(
            slug='community',
            defaults={'name': 'Community'},
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

        for index, points in enumerate([9000, 6000, 3000]):
            user = User.objects.create_user(
                email=f'counts-{index}@example.com',
                password='pass',
                address=f'0x{str(index) * 40}',
                name=f'User {index}',
            )
            Contribution.objects.create(
                user=user,
                contribution_type=community_type,
                points=points,
                frozen_global_points=points,
                contribution_date=timezone.now(),
            )

    def test_community_stats_runs_one_ranking_scan(self):
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get('/api/v1/leaderboard/stats/?type=community')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(count_ranking_scans(ctx.captured_queries), 1)

    def test_validator_stats_runs_one_ranking_scan(self):
        """The response always carries community_member_count, so validator
        stats still pay for the community summary, but only once."""
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get('/api/v1/leaderboard/stats/?type=validator')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(count_ranking_scans(ctx.captured_queries), 1)

    def test_global_stats_runs_one_ranking_scan(self):
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get('/api/v1/leaderboard/stats/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(count_ranking_scans(ctx.captured_queries), 1)

    def test_community_list_runs_one_ranking_scan(self):
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get('/api/v1/leaderboard/community/?limit=5')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(count_ranking_scans(ctx.captured_queries), 1)

    def test_marker_detects_a_ranking_scan(self):
        """Keeps the guards above honest if the SQL shape ever changes."""
        from community_xp.utils import build_effective_community_ranking_queryset

        with CaptureQueriesContext(connection) as ctx:
            list(
                build_effective_community_ranking_queryset(visible_only=True)
                .values_list('id', 'total_points')
            )

        self.assertEqual(count_ranking_scans(ctx.captured_queries), 1)

    def test_repeated_community_reads_share_one_ranking_scan(self):
        with CaptureQueriesContext(connection) as ctx:
            self.client.get('/api/v1/leaderboard/community/?limit=5')
            self.client.get('/api/v1/leaderboard/community/?limit=5')
            self.client.get('/api/v1/leaderboard/community/?limit=20&offset=0')

        self.assertEqual(count_ranking_scans(ctx.captured_queries), 1)

    def test_personalized_fields_stay_live_on_a_cached_snapshot(self):
        """Ranks come from the shared snapshot; user_rank is resolved per request."""
        first = self.client.get('/api/v1/leaderboard/community/?limit=5')
        self.assertEqual(first.status_code, 200)

        ranked = [
            (entry['user_name'], entry['rank'])
            for entry in first.data['results']
        ]
        self.assertEqual([rank for _, rank in ranked], [1, 2, 3])

        for index in range(3):
            user = User.objects.get(email=f'counts-{index}@example.com')
            with self.subTest(user=user.email):
                response = self.client.get(
                    f'/api/v1/leaderboard/community/?limit=5&user_address={user.id}'
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['user_rank'], index + 1)
