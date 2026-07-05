from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from api.models import MetricSnapshot
from builders.models import Builder
from community_xp.models import Mee6CurrentXP, Mee6SyncRun
from contributions.models import Category, Contribution, ContributionType
from users.models import User
from validators.models import Validator, ValidatorWallet


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
        self.community_category, _ = Category.objects.get_or_create(
            slug='community',
            defaults={'name': 'Community'},
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
        self.community_real_type, _ = ContributionType.objects.get_or_create(
            slug='community-article',
            defaults={
                'name': 'Community Article',
                'category': self.community_category,
            },
        )
        self.community_link_type, _ = ContributionType.objects.get_or_create(
            slug='community-link-x',
            defaults={
                'name': 'Link X Account',
                'category': self.community_category,
            },
        )

    def test_participants_growth_allows_public_metrics_page(self):
        self.client.force_authenticate(user=None)

        response = self.client.get('/api/v1/metrics/participants-growth/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)

    def _create_user(self, email, address, **extra_fields):
        return User.objects.create_user(
            email=email,
            password='pass',
            address=address,
            **extra_fields,
        )

    def _create_current_mee6_xp(self, user, guild_id, discord_id, xp, synced_at):
        run = Mee6SyncRun.objects.create(
            guild_id=guild_id,
            guild_name=f'Guild {guild_id}',
            status=Mee6SyncRun.STATUS_SUCCESS,
            page_size=50,
            pages_fetched=1,
            players_fetched=1,
            matched_players=1,
            unmatched_players=0,
            completed_at=synced_at,
            applied_at=synced_at,
        )
        return Mee6CurrentXP.objects.create(
            guild_id=guild_id,
            discord_id=discord_id,
            username=f'discord-{discord_id}',
            rank=1,
            xp=xp,
            level=1,
            message_count=3,
            sync_run=run,
            matched_user=user,
            matched_at=synced_at,
            synced_at=synced_at,
        )

    @override_settings(MEE6_GUILD_ID='main-guild', DISCORD_GUILD_ID='discord-guild')
    def test_participants_growth_scopes_mee6_members_to_default_guild(self):
        base = timezone.now() - timedelta(days=2)

        default_guild_member = self._create_user(
            'default-guild@example.com',
            '0x0000000000000000000000000000000000000101',
        )
        other_guild_member = self._create_user(
            'other-guild@example.com',
            '0x0000000000000000000000000000000000000102',
        )

        self._create_current_mee6_xp(
            default_guild_member,
            'main-guild',
            'discord-main',
            10,
            base,
        )
        self._create_current_mee6_xp(
            other_guild_member,
            'other-guild',
            'discord-other',
            25,
            base,
        )

        response = self.client.get('/api/v1/metrics/participants-growth/')

        self.assertEqual(response.status_code, 200)
        final_point = response.data['data'][-1]
        self.assertEqual(final_point['community_members'], 1)
        self.assertEqual(final_point['unique_contributors'], 1)
        self.assertEqual(final_point['total'], 1)

    def test_participants_growth_deduplicates_overlapping_roles(self):
        base = timezone.now() - timedelta(days=3)

        shared_user = self._create_user('shared@example.com', '0x0000000000000000000000000000000000000001')
        waitlist_only = self._create_user('waitlist@example.com', '0x0000000000000000000000000000000000000002')
        validator_only = self._create_user('validator@example.com', '0x0000000000000000000000000000000000000003')
        active_builder = self._create_user('builder@example.com', '0x0000000000000000000000000000000000000004')
        idle_builder = self._create_user('idle@example.com', '0x0000000000000000000000000000000000000005')
        community_only = self._create_user('community@example.com', '0x0000000000000000000000000000000000000006')
        link_only = self._create_user('link-only@example.com', '0x0000000000000000000000000000000000000007')
        hidden_community = self._create_user(
            'hidden-community@example.com',
            '0x0000000000000000000000000000000000000008',
            visible=False,
        )

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
            # active_builder also has community contributions, so the displayed
            # "unique contributors" total must not count them twice.
            Contribution(
                user=active_builder,
                contribution_type=self.community_real_type,
                points=12,
                frozen_global_points=12,
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
            Contribution(
                user=community_only,
                contribution_type=self.community_real_type,
                points=15,
                frozen_global_points=15,
                contribution_date=base + timedelta(days=1)
            ),
            Contribution(
                user=shared_user,
                contribution_type=self.community_real_type,
                points=20,
                frozen_global_points=20,
                contribution_date=base + timedelta(days=2)
            ),
            Contribution(
                user=link_only,
                contribution_type=self.community_link_type,
                points=5,
                frozen_global_points=5,
                contribution_date=base + timedelta(days=2)
            ),
            Contribution(
                user=hidden_community,
                contribution_type=self.community_real_type,
                points=99,
                frozen_global_points=99,
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
        self.assertEqual(point_before_graduation['community_members'], 1)
        self.assertEqual(final_point['builders'], 1)
        self.assertEqual(final_point['validators'], 2)
        self.assertEqual(final_point['waitlist'], 2)
        self.assertEqual(final_point['community_members'], 3)
        self.assertEqual(final_point['cohort_total'], 8)
        self.assertEqual(final_point['total'], 5)
        self.assertEqual(final_point['overlap_count'], 3)
        self.assertEqual(final_point['unique_contributors'], 4)
        self.assertEqual(final_point['contributor_cohort_total'], 6)
        self.assertEqual(final_point['contributor_overlap_count'], 2)


class OverviewMetricsViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _create_user(self, email, address, name=''):
        return User.objects.create_user(
            email=email,
            password='pass',
            address=address,
            name=name,
        )

    def test_public_overview_returns_latest_aggregated_payload(self):
        builder_user = self._create_user(
            'overview-builder@example.com',
            '0x0000000000000000000000000000000000000201',
            'Builder One',
        )
        validator_user = self._create_user(
            'overview-validator@example.com',
            '0x0000000000000000000000000000000000000202',
            'Validator One',
        )
        community_user = self._create_user(
            'overview-community@example.com',
            '0x0000000000000000000000000000000000000203',
            'Community One',
        )
        Builder.objects.create(user=builder_user)
        validator = Validator.objects.create(user=validator_user)

        builder_category, _ = Category.objects.get_or_create(
            slug='builder',
            defaults={'name': 'Builder'},
        )
        builder_type, _ = ContributionType.objects.get_or_create(
            slug='overview-builder-work',
            defaults={
                'name': 'Builder work',
                'category': builder_category,
                'is_submittable': True,
            },
        )
        community_category, _ = Category.objects.get_or_create(
            slug='community',
            defaults={'name': 'Community'},
        )
        community_type, _ = ContributionType.objects.get_or_create(
            slug='overview-community-post',
            defaults={
                'name': 'Community post',
                'category': community_category,
                'is_submittable': True,
            },
        )
        Contribution.objects.bulk_create([
            Contribution(
                user=builder_user,
                contribution_type=builder_type,
                points=10,
                frozen_global_points=10,
                contribution_date=timezone.now(),
            ),
            Contribution(
                user=community_user,
                contribution_type=community_type,
                points=5,
                frozen_global_points=5,
                contribution_date=timezone.now(),
            )
        ])

        ValidatorWallet.objects.create(
            operator=validator,
            operator_address='0x0000000000000000000000000000000000000202',
            address='0x0000000000000000000000000000000000000301',
            network='asimov',
            status='active',
            moniker='Validator One',
            v_stake=str(200 * 10 ** 18),
            d_stake=str(50 * 10 ** 18),
        )
        ValidatorWallet.objects.create(
            operator_address='0x0000000000000000000000000000000000000402',
            address='0x0000000000000000000000000000000000000302',
            network='bradbury',
            status='active',
            moniker='Independent Two',
            v_stake=str(500 * 10 ** 18),
            d_stake='0',
        )

        MetricSnapshot.objects.create(metric_key='decisions_made', source='genlayer_explorer', value=1234)
        MetricSnapshot.objects.create(metric_key='chain_transactions', source='genlayer_explorer', value=9876)
        MetricSnapshot.objects.create(metric_key='discord_members', source='discord', value=111)
        MetricSnapshot.objects.create(metric_key='x_followers', source='x', value=222)
        MetricSnapshot.objects.create(metric_key='github_boilerplate_stars', source='github', value=333)
        MetricSnapshot.objects.create(metric_key='defillama_fees_rank', source='defillama', value=15, unit='rank')

        from api.overview_metrics import collect_overview_payload
        collect_overview_payload()

        # These newer source rows/local writes must not affect the public response
        # until the next refresh stores a new composite overview_payload.
        MetricSnapshot.objects.create(metric_key='discord_members', source='discord', value=999)
        Contribution.objects.bulk_create([
            Contribution(
                user=community_user,
                contribution_type=community_type,
                points=1,
                frozen_global_points=1,
                contribution_date=timezone.now(),
            )
        ])

        response = self.client.get('/api/v1/metrics/overview/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['version'], 1)
        self.assertEqual(response.data['metrics']['decisions_made']['value'], 1234.0)
        self.assertEqual(response.data['metrics']['chain_transactions']['value'], 9876.0)
        self.assertEqual(response.data['metrics']['builders']['value'], 1)
        self.assertEqual(response.data['metrics']['validators']['value'], 1)
        self.assertEqual(response.data['metrics']['community_members']['value'], 1)
        # Public contributions count comes from the stored payload, not the row added after refresh.
        self.assertEqual(response.data['metrics']['contributions']['value'], 2)
        self.assertEqual(response.data['metrics']['discord_members']['value'], 111.0)
        self.assertEqual(response.data['metrics']['x_followers']['value'], 222.0)
        self.assertEqual(response.data['metrics']['github_boilerplate_stars']['value'], 333.0)
        self.assertEqual(response.data['metrics']['defillama_fees_rank']['value'], 15.0)
        self.assertEqual(response.data['top_validators'][0]['name'], 'Independent Two')
        self.assertEqual(response.data['top_validators'][0]['total_stake_gen'], 500)
        self.assertEqual(response.data['top_validators'][1]['name'], 'Validator One')
        self.assertEqual(response.data['top_validators'][1]['total_stake_gen'], 250)

    def test_public_overview_without_aggregate_includes_live_portal_counts(self):
        builder_user = self._create_user(
            'overview-fallback-builder@example.com',
            '0x0000000000000000000000000000000000001201',
            'Fallback Builder',
        )
        validator_user = self._create_user(
            'overview-fallback-validator@example.com',
            '0x0000000000000000000000000000000000001202',
            'Fallback Validator',
        )
        community_user = self._create_user(
            'overview-fallback-community@example.com',
            '0x0000000000000000000000000000000000001203',
            'Fallback Community',
        )
        Validator.objects.create(user=validator_user)

        builder_category, _ = Category.objects.get_or_create(
            slug='builder',
            defaults={'name': 'Builder'},
        )
        builder_type, _ = ContributionType.objects.get_or_create(
            slug='overview-fallback-builder-work',
            defaults={
                'name': 'Fallback builder work',
                'category': builder_category,
                'is_submittable': True,
            },
        )
        community_category, _ = Category.objects.get_or_create(
            slug='community',
            defaults={'name': 'Community'},
        )
        community_type, _ = ContributionType.objects.get_or_create(
            slug='overview-fallback-community-post',
            defaults={
                'name': 'Fallback community post',
                'category': community_category,
                'is_submittable': True,
            },
        )
        Contribution.objects.bulk_create([
            Contribution(
                user=builder_user,
                contribution_type=builder_type,
                points=10,
                frozen_global_points=10,
                contribution_date=timezone.now(),
            ),
            Contribution(
                user=community_user,
                contribution_type=community_type,
                points=5,
                frozen_global_points=5,
                contribution_date=timezone.now(),
            )
        ])
        MetricSnapshot.objects.create(metric_key='discord_members', source='discord', value=111)

        response = self.client.get('/api/v1/metrics/overview/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['version'], 1)
        self.assertEqual(response.data['metrics']['builders']['value'], 1)
        self.assertEqual(response.data['metrics']['validators']['value'], 1)
        self.assertEqual(response.data['metrics']['community_members']['value'], 1)
        self.assertEqual(response.data['metrics']['contributions']['value'], 2)
        self.assertEqual(response.data['metrics']['discord_members']['value'], 111.0)
        self.assertEqual(response.data['top_validators'], [])

    @override_settings(CRON_SYNC_TOKEN='overview-secret')
    @patch('api.metrics_views.refresh_overview_metrics')
    def test_refresh_overview_metrics_requires_cron_token(self, refresh_mock):
        blocked = self.client.post('/api/v1/metrics/overview/refresh/')
        self.assertEqual(blocked.status_code, status.HTTP_403_FORBIDDEN)
        refresh_mock.assert_not_called()

        refresh_mock.return_value = [
            MetricSnapshot(metric_key='decisions_made', source='test', status=MetricSnapshot.STATUS_OK)
        ]
        allowed = self.client.post(
            '/api/v1/metrics/overview/refresh/',
            HTTP_X_CRON_TOKEN='overview-secret',
        )

        self.assertEqual(allowed.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(allowed.data['count'], 1)
        refresh_mock.assert_called_once()


class OverviewMetricCollectorTests(TestCase):
    @override_settings(SORSA_API_KEY='sorsa-secret', SORSA_API_BASE_URL='https://sorsa.test/v3', X_METRICS_USERNAME='GenLayer')
    @patch('api.overview_metrics.requests.get')
    def test_collect_x_followers_uses_sorsa_profile_api(self, mock_get):
        from api.overview_metrics import collect_x_followers

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {'users': [{'username': 'GenLayer', 'followers_count': 42420}]}

        mock_get.return_value = FakeResponse()

        snap = collect_x_followers()

        self.assertEqual(snap.metric_key, 'x_followers')
        self.assertEqual(snap.source, 'sorsa')
        self.assertEqual(float(snap.value), 42420.0)
        mock_get.assert_called_once_with(
            'https://sorsa.test/v3/info-batch',
            params={'usernames': ['GenLayer']},
            headers={'ApiKey': 'sorsa-secret', 'Accept': 'application/json'},
            timeout=12,
        )

    @override_settings(TELEGRAM_BOT_TOKEN='', TELEGRAM_CHAT_ID='', TELEGRAM_MEMBERS='')
    @patch('api.overview_metrics.requests.get')
    def test_collect_telegram_members_defaults_to_curated_value_without_bot_token(self, mock_get):
        from api.overview_metrics import collect_telegram_members

        snap = collect_telegram_members()

        self.assertEqual(snap.metric_key, 'telegram_members')
        self.assertEqual(float(snap.value), 13300.0)
        self.assertEqual(snap.dimensions, {'fallback': 'bot_token_missing'})
        mock_get.assert_not_called()

    @patch('api.overview_metrics.collect_network_activity')
    @patch('api.overview_metrics.collect_external_metrics')
    @patch('api.overview_metrics.collect_portal_metrics')
    @patch('api.overview_metrics.collect_testnet_metrics')
    def test_refresh_overview_metrics_stores_composite_overview_payload(
        self,
        collect_testnet_mock,
        collect_portal_mock,
        collect_external_mock,
        collect_network_mock,
    ):
        from api.overview_metrics import OVERVIEW_PAYLOAD_METRIC_KEY, refresh_overview_metrics

        MetricSnapshot.objects.create(metric_key='decisions_made', source='genlayer_explorer', value=123)
        MetricSnapshot.objects.create(metric_key='chain_transactions', source='genlayer_explorer', value=456)
        MetricSnapshot.objects.create(metric_key='discord_members', source='discord', value=111)
        MetricSnapshot.objects.create(metric_key='telegram_members', source='telegram', value=13300)
        MetricSnapshot.objects.create(metric_key='x_followers', source='sorsa', value=222)
        MetricSnapshot.objects.create(metric_key='github_boilerplate_stars', source='github', value=333)

        collect_testnet_mock.return_value = []
        collect_portal_mock.return_value = []
        collect_external_mock.return_value = []
        collect_network_mock.return_value = MetricSnapshot(
            metric_key='network_activity',
            source='composite',
            status=MetricSnapshot.STATUS_OK,
        )

        results = refresh_overview_metrics()

        self.assertEqual(results[-1].metric_key, OVERVIEW_PAYLOAD_METRIC_KEY)
        self.assertEqual(results[-1].status, MetricSnapshot.STATUS_OK)
        payload = results[-1].raw_payload
        self.assertEqual(payload['version'], 1)
        self.assertEqual(payload['metrics']['decisions_made']['value'], 123.0)
        self.assertEqual(payload['metrics']['discord_members']['value'], 111.0)
        self.assertEqual(payload['metrics']['telegram_members']['value'], 13300.0)
        self.assertEqual(payload['metrics']['x_followers']['value'], 222.0)
        self.assertEqual(payload['metrics']['github_boilerplate_stars']['value'], 333.0)


class NetworkActivityViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()
        self.fixed_now = datetime(2026, 6, 19, tzinfo=dt_timezone.utc)
        self.now_patcher = patch('api.overview_metrics.timezone.now', return_value=self.fixed_now)
        self.now_patcher.start()

    def tearDown(self):
        self.now_patcher.stop()
        cache.clear()

    def _fake_get(self, url, params=None, timeout=None, **kwargs):
        class FakeResp:
            def __init__(self, payload, ok=True):
                self._payload = payload
                self.ok = ok
                self.status_code = 200 if ok else 500

            def raise_for_status(self):
                if not self.ok:
                    raise RuntimeError('upstream error')

            def json(self):
                return self._payload

        if 'executive' in url or 'studio' in url:
            return FakeResp({'metrics': [
                {'id': 'total-decisions', 'sparkline': list(range(1, 27)), 'allTimeValue': 1000},
                {'id': 'chain-transactions', 'sparkline': list(range(1, 27)), 'allTimeValue': 5000},
            ]})
        if 'kpi-histories' in url:
            base = int(datetime(2026, 5, 25, tzinfo=dt_timezone.utc).timestamp())
            base_value = 200 if (params or {}).get('metric') == 'total_rollup_transactions' else 100
            return FakeResp({'histories': [
                {'timestamp': base + i * 86400, 'metric': (params or {}).get('metric'),
                 'interval': 'D1', 'value': str(base_value + i)}
                for i in range(26)
            ]})
        return FakeResp({}, ok=False)

    @patch('api.overview_metrics.requests.get')
    def test_build_network_activity_aggregates_three_weekly_curves(self, mock_get):
        mock_get.side_effect = self._fake_get
        MetricSnapshot.objects.create(metric_key='defillama_fees_rank', source='defillama', value=15, unit='rank')

        from api.overview_metrics import build_network_activity
        payload = build_network_activity()

        self.assertEqual(payload['version'], 5)
        self.assertEqual(payload['interval'], 'week')
        self.assertEqual(payload['activity_window'], {'start': '2026-01-01', 'end': '2026-06-30'})
        self.assertEqual([s['key'] for s in payload['series']], ['studio', 'asimov', 'bradbury'])
        self.assertEqual(payload['labels'], ['May 22-29', 'May 29 - Jun 5', 'Jun 5-12', 'Jun 12-19'])
        for s in payload['series']:
            self.assertEqual(len(s['values']), 4)
        self.assertEqual(payload['series'][0]['values'], [15, 63, 112, 161])
        self.assertEqual(payload['series'][1]['values'], [510, 756, 805, 854])
        self.assertEqual(payload['latest_week']['label'], 'Jun 12-19')
        self.assertEqual(payload['totals']['decisions_made'], 1869)
        self.assertEqual(payload['totals']['chain_transactions'], 3269)
        self.assertEqual(payload['totals']['daily_decisions_made'], 267)
        self.assertEqual(payload['totals']['daily_chain_transactions'], 467)
        self.assertAlmostEqual(payload['totals']['transactions_per_second'], 3269 / (7 * 24 * 60 * 60))
        self.assertEqual(len(payload['activity']), 181)
        self.assertEqual(payload['activity'][0]['date'], '2026-01-01')
        self.assertEqual(payload['activity'][0]['decisions_made'], 0)
        self.assertEqual(payload['activity'][-1]['date'], '2026-06-30')
        self.assertEqual(payload['activity'][-1]['decisions_made'], 0)
        latest_observed = next(day for day in payload['activity'] if day['date'] == '2026-06-19')
        self.assertEqual(latest_observed['decisions_made'], 276)
        self.assertEqual(latest_observed['chain_transactions'], 476)
        self.assertEqual(latest_observed['sources']['studio']['decisions_made'], 26)
        self.assertEqual(latest_observed['sources']['asimov']['chain_transactions'], 225)
        studio_call = next(call for call in mock_get.call_args_list if 'executive' in call.args[0])
        self.assertEqual(studio_call.kwargs['params'], {'instanceId': 'all', 'range': 'year'})
        history_calls = [call for call in mock_get.call_args_list if 'kpi-histories' in call.args[0]]
        self.assertEqual(len(history_calls), 4)
        self.assertEqual(
            sorted(call.kwargs['params']['metric'] for call in history_calls),
            [
                'total_finalized_transactions',
                'total_finalized_transactions',
                'total_rollup_transactions',
                'total_rollup_transactions',
            ],
        )
        expected_from = int(datetime(2026, 1, 1, tzinfo=dt_timezone.utc).timestamp())
        for call in history_calls:
            self.assertEqual(call.kwargs['params']['interval'], 'D1')
            self.assertEqual(call.kwargs['params']['from_timestamp'], expected_from)
            self.assertEqual(call.kwargs['params']['to_timestamp'], int(self.fixed_now.timestamp()))

    @patch('api.overview_metrics.requests.get')
    def test_build_network_activity_degrades_when_studio_fails(self, mock_get):
        def partial(url, params=None, timeout=None, **kwargs):
            if 'executive' in url or 'studio' in url:
                raise RuntimeError('studio down')
            return self._fake_get(url, params=params, timeout=timeout, **kwargs)

        mock_get.side_effect = partial
        from api.overview_metrics import build_network_activity
        payload = build_network_activity()

        self.assertEqual([s['key'] for s in payload['series']], ['asimov', 'bradbury'])
        # only the two testnets contribute to totals now
        self.assertEqual(payload['totals']['decisions_made'], 1708)
        self.assertEqual(payload['totals']['daily_decisions_made'], 244)

    @patch('api.overview_metrics.requests.get')
    def test_build_network_activity_keeps_explorer_curves_when_chain_history_fails(self, mock_get):
        def partial(url, params=None, timeout=None, **kwargs):
            if 'kpi-histories' in url and (params or {}).get('metric') == 'total_rollup_transactions':
                raise RuntimeError('chain history unsupported')
            return self._fake_get(url, params=params, timeout=timeout, **kwargs)

        mock_get.side_effect = partial
        from api.overview_metrics import build_network_activity
        payload = build_network_activity()

        self.assertEqual([s['key'] for s in payload['series']], ['studio', 'asimov', 'bradbury'])
        self.assertEqual(payload['series'][1]['values'], [510, 756, 805, 854])
        self.assertEqual(payload['series'][2]['values'], [510, 756, 805, 854])
        self.assertEqual(payload['latest_week_by_source']['asimov']['chain_transactions'], 0)
        self.assertEqual(payload['latest_week_by_source']['bradbury']['chain_transactions'], 0)
        self.assertEqual(payload['totals']['decisions_made'], 1869)
        self.assertEqual(payload['totals']['chain_transactions'], 161)

    @patch('api.overview_metrics.requests.get')
    def test_collect_network_activity_persists_snapshot(self, mock_get):
        from api.overview_metrics import collect_network_activity
        mock_get.side_effect = self._fake_get

        snap = collect_network_activity()

        self.assertEqual(snap.metric_key, 'network_activity')
        self.assertEqual(snap.status, MetricSnapshot.STATUS_OK)
        self.assertEqual(snap.raw_payload['version'], 5)
        self.assertEqual(snap.raw_payload['interval'], 'week')
        self.assertEqual([s['key'] for s in snap.raw_payload['series']], ['studio', 'asimov', 'bradbury'])
        self.assertEqual(snap.raw_payload['totals']['decisions_made'], 1869)

    @patch('api.overview_metrics.requests.get')
    def test_network_activity_served_from_snapshot_without_fetching(self, mock_get):
        # A stored snapshot must be served straight from the DB (no upstream calls),
        # and null padding in a curve must survive the JSON round-trip.
        mock_get.side_effect = AssertionError('upstreams must not be hit when a snapshot exists')
        stored = {
            'labels': ['Jun 1-7', 'Jun 8-14', 'Jun 15-21'],
            'series': [{'key': 'studio', 'label': 'Studio', 'values': [None, 5, 9]}],
            'version': 5,
            'interval': 'week',
            'activity_window': {'start': '2026-01-01', 'end': '2026-06-30'},
            'activity': [
                {
                    'date': '2026-06-15',
                    'decisions_made': 5,
                    'chain_transactions': 2,
                    'sources': {'studio': {'label': 'Studio', 'decisions_made': 5, 'chain_transactions': 2}},
                },
            ],
            'latest_week': {'week_start': '2026-06-15', 'week_end': '2026-06-21', 'label': 'Jun 15-21'},
            'totals': {
                'decisions_made': 4242,
                'chain_transactions': 99,
                'daily_decisions_made': 606,
                'daily_chain_transactions': 14,
                'transactions_per_second': 99 / (7 * 24 * 60 * 60),
            },
        }
        MetricSnapshot.objects.create(
            metric_key='network_activity', source='composite', value=4242,
            unit='count', raw_payload=stored,
        )

        resp = self.client.get('/api/v1/metrics/overview/network-activity/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['interval'], 'week')
        self.assertEqual(resp.data['version'], 5)
        self.assertEqual(resp.data['totals']['decisions_made'], 4242)
        self.assertEqual([s['key'] for s in resp.data['series']], ['studio'])
        self.assertEqual(resp.data['series'][0]['values'], [None, 5, 9])  # null padding preserved
        self.assertEqual(resp.data['activity'][0]['date'], '2026-06-15')
        mock_get.assert_not_called()

    @patch('api.overview_metrics.requests.get')
    def test_v3_weekly_snapshot_keeps_graph_available_until_v4_refresh(self, mock_get):
        mock_get.side_effect = AssertionError('public read must not fetch upstreams')
        stored = {
            'labels': ['Jun 1-7'],
            'series': [{'key': 'studio', 'label': 'Studio', 'values': [42]}],
            'version': 3,
            'interval': 'week',
            'latest_week': {'week_start': '2026-06-01', 'week_end': '2026-06-07', 'label': 'Jun 1-7'},
            'totals': {
                'decisions_made': 42,
                'chain_transactions': 7,
                'daily_decisions_made': 6,
                'daily_chain_transactions': 1,
                'transactions_per_second': 7 / (7 * 24 * 60 * 60),
            },
        }
        MetricSnapshot.objects.create(
            metric_key='network_activity', source='composite', value=42,
            unit='count', raw_payload=stored,
        )

        resp = self.client.get('/api/v1/metrics/overview/network-activity/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['version'], 5)
        self.assertEqual(resp.data['series'][0]['values'], [42])
        self.assertEqual(resp.data['activity'], [])
        self.assertEqual(resp.data['latest_week_by_source'], {})
        mock_get.assert_not_called()

    @patch('api.overview_metrics.requests.get')
    def test_network_activity_without_valid_snapshot_does_not_fetch_live(self, mock_get):
        mock_get.side_effect = AssertionError('public read must not fetch upstreams')

        resp = self.client.get('/api/v1/metrics/overview/network-activity/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['version'], 5)
        self.assertEqual(resp.data['interval'], 'week')
        self.assertEqual(resp.data['labels'], [])
        self.assertEqual(resp.data['series'], [])
        self.assertIsNone(resp.data['totals']['decisions_made'])
        mock_get.assert_not_called()

    @patch('api.overview_metrics.requests.get')
    def test_legacy_daily_snapshot_is_ignored_without_live_rebuild(self, mock_get):
        mock_get.side_effect = AssertionError('public read must not fetch upstreams')
        stored = {
            'labels': ['Jun 17', 'Jun 18', 'Jun 19'],
            'series': [{'key': 'studio', 'label': 'Studio', 'values': [5, 7, 2]}],
            'interval': 'day',
            'totals': {'decisions_made': 14, 'chain_transactions': 99, 'defillama_fees_rank': None},
            'all_time_by_source': {'studio': {'decisions': 1000, 'chain': 5000}},
        }
        MetricSnapshot.objects.create(
            metric_key='network_activity', source='composite', value=14,
            unit='count', raw_payload=stored,
        )

        resp = self.client.get('/api/v1/metrics/overview/network-activity/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['interval'], 'week')
        self.assertEqual(resp.data['labels'], [])
        self.assertEqual(resp.data['series'], [])
        mock_get.assert_not_called()

    @patch('api.overview_metrics.requests.get')
    def test_total_source_failure_does_not_clobber_good_snapshot(self, mock_get):
        # A good snapshot exists; a cron run where every source fails must NOT
        # overwrite it — it records an error snapshot and the OK one keeps serving.
        good = {
            'labels': ['Jun 1'],
            'series': [{'key': 'studio', 'label': 'Studio', 'values': [7]}],
            'version': 4,
            'interval': 'week',
            'activity': [],
            'latest_week': {'week_start': '2026-05-26', 'week_end': '2026-06-01', 'label': 'May 26 - Jun 1'},
            'totals': {
                'decisions_made': 1234,
                'chain_transactions': 5,
                'daily_decisions_made': 176,
                'daily_chain_transactions': 1,
                'transactions_per_second': 5 / (7 * 24 * 60 * 60),
            },
        }
        MetricSnapshot.objects.create(
            metric_key='network_activity', source='composite', value=1234,
            unit='count', raw_payload=good,
        )

        from api.overview_metrics import collect_network_activity, latest_network_activity
        mock_get.side_effect = RuntimeError('all upstreams down')
        snap = collect_network_activity()

        self.assertEqual(snap.status, MetricSnapshot.STATUS_ERROR)
        # The latest *OK* snapshot is still the good one.
        self.assertEqual(latest_network_activity()['totals']['decisions_made'], 1234)

    @patch('api.overview_metrics.requests.get')
    def test_partial_source_failure_uses_only_sources_that_resolved_this_run(self, mock_get):
        # Rolling-week totals should not backfill stale all-time figures from an
        # older snapshot; they reflect the sources that resolved for this run.
        prev = {
            'labels': ['Jun 1'],
            'series': [{'key': 'studio', 'label': 'Studio', 'values': [1]}],
            'interval': 'day',
            'totals': {'decisions_made': 1400, 'chain_transactions': 6800, 'defillama_fees_rank': None},
            'all_time_by_source': {
                'studio': {'decisions': 1000, 'chain': 5000},
                'asimov': {'decisions': 200, 'chain': 900},
                'bradbury': {'decisions': 200, 'chain': 900},
            },
        }
        MetricSnapshot.objects.create(
            metric_key='network_activity', source='composite', value=1400, raw_payload=prev,
        )

        # This run: studio is down, the two explorers respond.
        def partial(url, params=None, timeout=None, **kwargs):
            if 'executive' in url or 'studio' in url:
                raise RuntimeError('studio down')
            return self._fake_get(url, params=params, timeout=timeout, **kwargs)

        mock_get.side_effect = partial
        from api.overview_metrics import build_network_activity
        payload = build_network_activity()

        self.assertEqual(payload['totals']['decisions_made'], 1708)
        self.assertEqual(payload['totals']['chain_transactions'], 3108)
        self.assertEqual(payload['totals']['daily_decisions_made'], 244)
        self.assertEqual(payload['totals']['daily_chain_transactions'], 444)
        # The chart curves still only include the sources that resolved.
        self.assertEqual([s['key'] for s in payload['series']], ['asimov', 'bradbury'])

    @patch('api.overview_metrics.requests.get')
    def test_first_run_no_previous_snapshot_does_not_invent_missing_source(self, mock_get):
        # First ever run (no prior snapshot), studio down: its weekly totals must
        # NOT be invented — totals come from the two testnets only.
        def partial(url, params=None, timeout=None, **kwargs):
            if 'executive' in url or 'studio' in url:
                raise RuntimeError('studio down')
            return self._fake_get(url, params=params, timeout=timeout, **kwargs)

        mock_get.side_effect = partial
        from api.overview_metrics import build_network_activity
        payload = build_network_activity()

        self.assertNotIn('studio', payload['latest_week_by_source'])
        self.assertEqual([s['key'] for s in payload['series']], ['asimov', 'bradbury'])
        self.assertEqual(payload['totals']['decisions_made'], 1708)
        self.assertEqual(payload['totals']['chain_transactions'], 3108)

    @override_settings(CRON_SYNC_TOKEN='na-secret')
    @patch('api.overview_metrics.requests.get')
    def test_refresh_endpoint_invalidates_network_activity_cache(self, mock_get):
        mock_get.side_effect = AssertionError('served from DB, no upstream calls expected')
        first = {
            'labels': ['Jun 1'], 'series': [{'key': 'studio', 'label': 'Studio', 'values': [1]}],
            'version': 4,
            'interval': 'week',
            'activity': [],
            'latest_week': {'week_start': '2026-05-26', 'week_end': '2026-06-01', 'label': 'May 26 - Jun 1'},
            'totals': {
                'decisions_made': 100,
                'chain_transactions': 1,
                'daily_decisions_made': 14,
                'daily_chain_transactions': 0,
                'transactions_per_second': 1 / (7 * 24 * 60 * 60),
            },
        }
        MetricSnapshot.objects.create(metric_key='network_activity', source='composite', value=100, raw_payload=first)

        # Warms the cache with the first snapshot.
        r1 = self.client.get('/api/v1/metrics/overview/network-activity/')
        self.assertEqual(r1.data['totals']['decisions_made'], 100)

        # A newer snapshot lands (as the cron would persist it).
        second = {
            'labels': ['Jun 2'], 'series': [{'key': 'studio', 'label': 'Studio', 'values': [2]}],
            'version': 4,
            'interval': 'week',
            'activity': [],
            'latest_week': {'week_start': '2026-05-27', 'week_end': '2026-06-02', 'label': 'May 27 - Jun 2'},
            'totals': {
                'decisions_made': 200,
                'chain_transactions': 2,
                'daily_decisions_made': 29,
                'daily_chain_transactions': 0,
                'transactions_per_second': 2 / (7 * 24 * 60 * 60),
            },
        }
        MetricSnapshot.objects.create(metric_key='network_activity', source='composite', value=200, raw_payload=second)

        # Without invalidation the cache would still serve 100; the refresh endpoint clears it.
        with patch('api.metrics_views.refresh_overview_metrics', return_value=[]):
            self.client.post('/api/v1/metrics/overview/refresh/', HTTP_X_CRON_TOKEN='na-secret')

        r2 = self.client.get('/api/v1/metrics/overview/network-activity/')
        self.assertEqual(r2.data['totals']['decisions_made'], 200)
