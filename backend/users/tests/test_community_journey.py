"""Community journey: 5 steps -> Creator role. Step 5 (X post) verified via Sorsa."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contributions.models import Category, Contribution, ContributionType
from creators import community_journey as cj
from creators.models import Creator, CommunityPostProof
from leaderboard.models import GlobalLeaderboardMultiplier
from social_connections.models import TwitterConnection
from social_tasks.models import SocialTask, SocialTaskCompletion
from social_tasks.sorsa_client import SorsaError

User = get_user_model()

POST_URL = 'https://x.com/social_user/status/1790000000000000000'


class CommunityJourneyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='community@test.com',
            address='0x' + '1' * 40,
            password='testpass123',
        )
        self.client.force_authenticate(user=self.user)
        self.community, _ = Category.objects.get_or_create(
            slug='community', defaults={'name': 'Community', 'description': 'c'},
        )
        for slug, name in [('community-link-x', 'Link X'), ('community-link-discord', 'Link Discord')]:
            ContributionType.objects.update_or_create(
                slug=slug,
                defaults={'name': name, 'category': self.community,
                          'min_points': 500, 'max_points': 500, 'is_submittable': False},
            )
        # These are seeded by social_tasks migration 0001; reuse them.
        self.follow_task, _ = SocialTask.objects.get_or_create(
            slug='follow-genlayer-x',
            defaults={'name': 'Follow', 'category': self.community, 'points': 500,
                      'verification_type': 'twitter_follow', 'target_handle': 'genlayer',
                      'action_url': 'https://x.com/intent/follow?screen_name=genlayer'},
        )
        self.join_task, _ = SocialTask.objects.get_or_create(
            slug='join-genlayer-discord',
            defaults={'name': 'Join Discord', 'category': self.community, 'points': 500,
                      'verification_type': 'discord_guild_join', 'action_url': 'https://discord.gg/genlayer'},
        )

    # --- helpers ---
    def link_x(self, handle='social_user'):
        return TwitterConnection.objects.create(
            user=self.user, platform_user_id='tw1', platform_username=handle, linked_at=timezone.now(),
        )

    def mark_link(self, slug):
        ct = ContributionType.objects.get(slug=slug)
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=ct,
            defaults={'multiplier_value': 1.0, 'valid_from': timezone.now() - timezone.timedelta(days=1)},
        )
        Contribution.objects.create(
            user=self.user, contribution_type=ct, points=ct.min_points, contribution_date=timezone.now(),
        )

    def mark_task(self, task):
        SocialTaskCompletion.objects.create(
            user=self.user, task=task, points_awarded=task.points, verification_type=task.verification_type,
        )

    def start_journey(self):
        return self.client.post('/api/v1/users/start_role_journey/', {'role': 'community'})

    def complete_steps_1_to_4(self):
        self.mark_link('community-link-x')
        self.mark_link('community-link-discord')
        self.mark_task(self.follow_task)
        self.mark_task(self.join_task)

    def good_tweet(self):
        return {'full_text': f'Joining the @genlayer community! {cj.verification_code(self.user)}',
                'username': 'social_user'}

    # --- status ---
    def test_status_reflects_step_completion(self):
        res = self.client.get('/api/v1/users/community_journey/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data['started'])
        steps = res.data['steps']
        self.assertFalse(any(s['done'] for s in steps.values()))
        self.assertFalse(res.data['complete'])
        # step 5 ships the code + share/intent affordances
        self.assertTrue(steps['x_post']['verification_code'].startswith('GL-'))
        self.assertIn('intent/post', steps['x_post']['intent_url'])

        self.start_journey()
        self.complete_steps_1_to_4()
        res = self.client.get('/api/v1/users/community_journey/')
        s = res.data['steps']
        self.assertTrue(res.data['started'])
        self.assertTrue(s['link_x']['done'] and s['link_discord']['done']
                        and s['follow_x']['done'] and s['join_discord']['done'])
        self.assertFalse(s['x_post']['done'])
        self.assertFalse(res.data['complete'])

    def test_start_journey_creates_marker_without_creator(self):
        res = self.start_journey()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        marker = Contribution.objects.get(user=self.user, contribution_type__slug='community-welcome')
        self.assertEqual(marker.points, 0)
        self.assertFalse(Creator.objects.filter(user=self.user).exists())

    def test_community_contribution_does_not_auto_create_creator(self):
        self.mark_link('community-link-x')
        quest_type = ContributionType.objects.create(
            slug='community-quest',
            name='Community Quest',
            category=self.community,
            min_points=1,
            max_points=100,
            is_submittable=True,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=quest_type,
            multiplier_value=1.0,
            valid_from=timezone.now() - timezone.timedelta(days=1),
        )
        Contribution.objects.create(
            user=self.user,
            contribution_type=quest_type,
            points=25,
            contribution_date=timezone.now(),
        )

        self.assertFalse(Creator.objects.filter(user=self.user).exists())

    # --- verify post (step 5) ---
    @patch('social_tasks.sorsa_client.SorsaClient.get_tweet')
    def test_verify_post_success(self, mock_get_tweet):
        self.link_x('social_user')
        mock_get_tweet.return_value = self.good_tweet()
        res = self.client.post('/api/v1/users/verify_community_post/', {'post_url': POST_URL})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(CommunityPostProof.objects.filter(user=self.user).exists())
        self.assertTrue(res.data['journey']['steps']['x_post']['done'])

    def test_verify_post_requires_linked_x(self):
        res = self.client.post('/api/v1/users/verify_community_post/', {'post_url': POST_URL})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['error'], 'x_not_linked')

    def test_verify_post_invalid_url(self):
        self.link_x()
        res = self.client.post('/api/v1/users/verify_community_post/', {'post_url': 'https://example.com/foo'})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['error'], 'invalid_url')

    def test_verify_post_url_handle_mismatch(self):
        self.link_x('social_user')
        res = self.client.post('/api/v1/users/verify_community_post/',
                               {'post_url': 'https://x.com/someone_else/status/1790000000000000000'})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['error'], 'account_mismatch')

    @patch('social_tasks.sorsa_client.SorsaClient.get_tweet')
    def test_verify_post_code_missing(self, mock_get_tweet):
        self.link_x('social_user')
        mock_get_tweet.return_value = {'full_text': 'Joining the @genlayer community!', 'username': 'social_user'}
        res = self.client.post('/api/v1/users/verify_community_post/', {'post_url': POST_URL})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['error'], 'code_missing')

    @patch('social_tasks.sorsa_client.SorsaClient.get_tweet')
    def test_verify_post_tag_missing(self, mock_get_tweet):
        self.link_x('social_user')
        mock_get_tweet.return_value = {'full_text': f'Joining! {cj.verification_code(self.user)}', 'username': 'social_user'}
        res = self.client.post('/api/v1/users/verify_community_post/', {'post_url': POST_URL})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['error'], 'tag_missing')

    @patch('social_tasks.sorsa_client.SorsaClient.get_tweet')
    def test_verify_post_author_mismatch(self, mock_get_tweet):
        self.link_x('social_user')
        mock_get_tweet.return_value = {'full_text': f'@genlayer {cj.verification_code(self.user)}', 'username': 'imposter'}
        res = self.client.post('/api/v1/users/verify_community_post/', {'post_url': POST_URL})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['error'], 'account_mismatch')

    @patch('social_tasks.sorsa_client.SorsaClient.get_tweet')
    def test_verify_post_not_found(self, mock_get_tweet):
        self.link_x('social_user')
        mock_get_tweet.return_value = None
        res = self.client.post('/api/v1/users/verify_community_post/', {'post_url': POST_URL})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['error'], 'post_not_found')

    @patch('social_tasks.sorsa_client.SorsaClient.get_tweet')
    def test_verify_post_sorsa_unavailable(self, mock_get_tweet):
        self.link_x('social_user')
        mock_get_tweet.side_effect = SorsaError('down')
        res = self.client.post('/api/v1/users/verify_community_post/', {'post_url': POST_URL})
        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(res.data['error'], 'verification_unavailable')

    # --- complete ---
    def test_complete_requires_started_even_if_steps_done(self):
        self.complete_steps_1_to_4()
        CommunityPostProof.objects.create(user=self.user, post_url=POST_URL, tweet_id='1790000000000000000')
        res = self.client.post('/api/v1/users/complete_community_journey/')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['error'], 'not_started')
        self.assertFalse(Creator.objects.filter(user=self.user).exists())

    def test_complete_requires_all_steps(self):
        self.start_journey()
        self.complete_steps_1_to_4()  # step 5 missing
        res = self.client.post('/api/v1/users/complete_community_journey/')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['missing_steps'], ['x_post'])
        self.assertFalse(Creator.objects.filter(user=self.user).exists())

    def test_complete_grants_creator(self):
        self.start_journey()
        self.complete_steps_1_to_4()
        CommunityPostProof.objects.create(user=self.user, post_url=POST_URL, tweet_id='1790000000000000000')
        res = self.client.post('/api/v1/users/complete_community_journey/')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Creator.objects.filter(user=self.user).exists())

    def test_complete_is_idempotent(self):
        self.start_journey()
        self.complete_steps_1_to_4()
        CommunityPostProof.objects.create(user=self.user, post_url=POST_URL, tweet_id='1790000000000000000')
        first = self.client.post('/api/v1/users/complete_community_journey/')
        second = self.client.post('/api/v1/users/complete_community_journey/')
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(Creator.objects.filter(user=self.user).count(), 1)

    def test_existing_creator_does_not_bypass_incomplete_journey(self):
        self.start_journey()
        Creator.objects.create(user=self.user)
        status_res = self.client.get('/api/v1/users/community_journey/')
        self.assertFalse(status_res.data['is_member'])
        res = self.client.post('/api/v1/users/complete_community_journey/')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['error'], 'incomplete')

    def test_legacy_creator_join_requires_completed_journey(self):
        res = self.client.post('/api/v1/creators/join/')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['error'], 'not_started')
        self.assertFalse(Creator.objects.filter(user=self.user).exists())

        self.start_journey()
        res = self.client.post('/api/v1/creators/join/')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['error'], 'incomplete')
        self.assertFalse(Creator.objects.filter(user=self.user).exists())
