from unittest.mock import patch

from cryptography.fernet import Fernet
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from contributions.models import Category, Contribution, ContributionType
from leaderboard.models import GlobalLeaderboardMultiplier
from social_connections.encryption import encrypt_token
from social_connections.models import DiscordConnection, TwitterConnection
from social_tasks.models import SocialTask, SocialTaskCompletion
from users.models import User
from validators.models import Validator


TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()


def _make_user(email):
    user = User(email=email, name='Test', visible=True, is_banned=False)
    user.set_password('x')
    user.save()
    return user


def _make_contribution_type(category, slug, is_submittable=True, points=10):
    contribution_type = ContributionType.objects.create(
        name=slug.replace('-', ' ').title(),
        slug=slug,
        category=category,
        min_points=points,
        max_points=points,
        is_submittable=is_submittable,
    )
    GlobalLeaderboardMultiplier.objects.create(
        contribution_type=contribution_type,
        multiplier_value=1.0,
        valid_from=timezone.now() - timezone.timedelta(days=1),
    )
    return contribution_type


@override_settings(
    GITHUB_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY,
    SOCIAL_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY,
    DISCORD_GUILD_ID='guild_123',
)
class SocialTaskViewSetTest(TestCase):
    def setUp(self):
        self.user = _make_user('alice@example.com')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.category, _ = Category.objects.get_or_create(
            slug='community', defaults={'name': 'Community'}
        )
        self.click_task = SocialTask.objects.create(
            slug='click-task',
            name='Click Task',
            category=self.category,
            points=5,
            verification_type='click_through',
            action_url='https://example.com',
        )
        self.twitter_task = SocialTask.objects.create(
            slug='twitter-task',
            name='Twitter Task',
            category=self.category,
            points=10,
            verification_type='twitter_follow',
            target_handle='genlayer',
            action_url='https://x.com/genlayer',
        )
        self.discord_task = SocialTask.objects.create(
            slug='discord-task',
            name='Discord Task',
            category=self.category,
            points=10,
            verification_type='discord_guild_join',
            action_url='https://discord.gg/x',
        )

    def test_save_derives_platform_from_registry(self):
        self.assertEqual(self.click_task.platform, 'generic')
        self.assertEqual(self.twitter_task.platform, 'twitter')
        self.assertEqual(self.discord_task.platform, 'discord')

    def test_list_returns_all_with_requires_verification_flag(self):
        response = self.client.get('/api/v1/social-tasks/')
        self.assertEqual(response.status_code, 200)
        by_slug = {t['slug']: t for t in response.json()}
        self.assertEqual(by_slug[self.click_task.slug]['status'], 'active')
        self.assertFalse(by_slug[self.click_task.slug]['requires_verification'])
        self.assertTrue(by_slug[self.twitter_task.slug]['requires_verification'])
        self.assertTrue(by_slug[self.discord_task.slug]['requires_verification'])

    def test_list_exposes_required_connection_not_verification_type(self):
        """The frontend contract: derived flags ship, internal slugs do not."""
        response = self.client.get('/api/v1/social-tasks/')
        by_slug = {t['slug']: t for t in response.json()}
        self.assertIsNone(by_slug[self.click_task.slug]['required_connection'])
        self.assertEqual(by_slug[self.twitter_task.slug]['required_connection'], 'twitter')
        self.assertEqual(by_slug[self.discord_task.slug]['required_connection'], 'discord')
        self.assertNotIn('verification_type', by_slug[self.click_task.slug])

    def test_list_filters_by_status(self):
        SocialTaskCompletion.objects.create(
            user=self.user, task=self.click_task, points_awarded=5,
            verification_type='click_through',
        )
        response = self.client.get('/api/v1/social-tasks/?status=completed')
        self.assertEqual(response.status_code, 200)
        slugs = [t['slug'] for t in response.json()]
        self.assertEqual(slugs, [self.click_task.slug])

        response = self.client.get('/api/v1/social-tasks/?status=active')
        active_slugs = {t['slug'] for t in response.json()}
        self.assertNotIn(self.click_task.slug, active_slugs)
        self.assertIn(self.twitter_task.slug, active_slugs)

    def test_complete_click_through_creates_completion(self):
        response = self.client.post(f'/api/v1/social-tasks/{self.click_task.slug}/complete/')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['points_awarded'], 5)
        self.assertEqual(SocialTaskCompletion.objects.filter(user=self.user).count(), 1)

        completion = SocialTaskCompletion.objects.get(user=self.user, task=self.click_task)
        self.assertEqual(completion.verification_type, 'click_through')

    def test_complete_is_idempotent(self):
        first = self.client.post(f'/api/v1/social-tasks/{self.click_task.slug}/complete/')
        self.assertEqual(first.status_code, 201)
        second = self.client.post(f'/api/v1/social-tasks/{self.click_task.slug}/complete/')
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()['status'], 'already_completed')
        self.assertEqual(SocialTaskCompletion.objects.filter(user=self.user).count(), 1)

    def test_complete_twitter_without_link_returns_not_linked(self):
        response = self.client.post(f'/api/v1/social-tasks/{self.twitter_task.slug}/complete/')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'social_account_not_linked')
        self.assertEqual(response.json()['platform'], 'twitter')

    @patch('social_tasks.verifiers.twitter_follow.get_default_client')
    def test_complete_twitter_with_link_succeeds_when_following(self, mock_get_client):
        TwitterConnection.objects.create(
            user=self.user,
            platform_user_id='1',
            platform_username='alice',
            access_token=encrypt_token('tok'),
            linked_at=timezone.now(),
        )
        client = mock_get_client.return_value
        client.is_following.return_value = (True, {})

        response = self.client.post(f'/api/v1/social-tasks/{self.twitter_task.slug}/complete/')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['points_awarded'], 10)

    @patch('social_tasks.verifiers.discord_guild_join.requests.get')
    def test_complete_discord_with_membership(self, mock_get):
        DiscordConnection.objects.create(
            user=self.user,
            platform_user_id='1',
            platform_username='alice',
            access_token=encrypt_token('tok'),
            linked_at=timezone.now(),
        )
        mock_get.return_value.status_code = 200

        response = self.client.post(f'/api/v1/social-tasks/{self.discord_task.slug}/complete/')
        self.assertEqual(response.status_code, 201)

    @patch('social_tasks.verifiers.discord_guild_join.requests.get')
    def test_complete_discord_without_membership_returns_400(self, mock_get):
        DiscordConnection.objects.create(
            user=self.user,
            platform_user_id='1',
            platform_username='alice',
            access_token=encrypt_token('tok'),
            linked_at=timezone.now(),
        )
        mock_get.return_value.status_code = 404

        response = self.client.post(f'/api/v1/social-tasks/{self.discord_task.slug}/complete/')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'verification_failed')

    @patch('social_tasks.verifiers.discord_guild_join.requests.get')
    def test_complete_discord_with_expired_token_returns_relink(self, mock_get):
        DiscordConnection.objects.create(
            user=self.user,
            platform_user_id='1',
            platform_username='alice',
            access_token=encrypt_token('tok'),
            linked_at=timezone.now(),
        )
        mock_get.return_value.status_code = 401

        response = self.client.post(f'/api/v1/social-tasks/{self.discord_task.slug}/complete/')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'token_invalid_relink_required')
        self.assertEqual(response.json()['platform'], 'discord')

    @patch('social_tasks.verifiers.discord_guild_join.requests.get')
    def test_complete_discord_with_service_error_returns_503(self, mock_get):
        DiscordConnection.objects.create(
            user=self.user,
            platform_user_id='1',
            platform_username='alice',
            access_token=encrypt_token('tok'),
            linked_at=timezone.now(),
        )
        mock_get.return_value.status_code = 503

        response = self.client.post(f'/api/v1/social-tasks/{self.discord_task.slug}/complete/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error'], 'verification_unavailable')

    def test_complete_inactive_task_returns_410(self):
        self.click_task.is_active = False
        self.click_task.save()

        response = self.client.post(f'/api/v1/social-tasks/{self.click_task.slug}/complete/')
        self.assertEqual(response.status_code, 410)

    def test_completed_then_deactivated_stays_idempotent(self):
        """A retry on an already-completed task must return 200 already_completed
        even after the task is deactivated — matching the list endpoint, which
        keeps completed tasks visible regardless of lifecycle."""
        response = self.client.post(f'/api/v1/social-tasks/{self.click_task.slug}/complete/')
        self.assertEqual(response.status_code, 201)

        self.click_task.is_active = False
        self.click_task.save()

        response = self.client.post(f'/api/v1/social-tasks/{self.click_task.slug}/complete/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'already_completed')

    def test_task_deactivated_during_verification_does_not_award(self):
        """The active window is re-checked inside the award transaction:
        verification can take seconds (external API), and a task that expires
        or is deactivated in that window must not award."""
        from social_tasks.verifiers import get_verifier

        verifier = get_verifier('click_through')
        real_verify = verifier.verify

        def deactivate_then_verify(task, user):
            SocialTask.objects.filter(pk=task.pk).update(is_active=False)
            return real_verify(task, user)

        with patch.object(verifier, 'verify', side_effect=deactivate_then_verify):
            response = self.client.post(
                f'/api/v1/social-tasks/{self.click_task.slug}/complete/'
            )

        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.json()['error'], 'task_unavailable')
        self.assertFalse(
            SocialTaskCompletion.objects.filter(
                user=self.user, task=self.click_task
            ).exists()
        )

    def test_complete_unknown_slug_returns_404(self):
        response = self.client.post('/api/v1/social-tasks/does-not-exist/complete/')
        self.assertEqual(response.status_code, 404)

    def test_banned_user_cannot_complete(self):
        self.user.is_banned = True
        self.user.save()

        response = self.client.post(f'/api/v1/social-tasks/{self.click_task.slug}/complete/')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'account_banned')

    def test_anonymous_user_can_list_active_only(self):
        inactive = SocialTask.objects.create(
            slug='inactive-task',
            name='Inactive Task',
            category=self.category,
            points=1,
            verification_type='click_through',
            action_url='https://example.com/inactive',
            is_active=False,
        )
        anon = APIClient()
        response = anon.get('/api/v1/social-tasks/')
        self.assertEqual(response.status_code, 200)
        slugs = {t['slug'] for t in response.json()}
        self.assertIn(self.click_task.slug, slugs)
        self.assertNotIn(inactive.slug, slugs)

    def test_clean_rejects_unsurfaced_category(self):
        from django.core.exceptions import ValidationError

        steward, _ = Category.objects.get_or_create(
            slug='steward', defaults={'name': 'Steward'},
        )
        bad = SocialTask(
            name='Steward task',
            slug='steward-task',
            category=steward,
            points=5,
            verification_type='click_through',
            action_url='https://example.com',
        )
        with self.assertRaises(ValidationError) as cm:
            bad.clean()
        self.assertIn('category', cm.exception.message_dict)

    def test_clean_requires_action_url_when_not_derivable(self):
        from django.core.exceptions import ValidationError

        bad = SocialTask(
            name='No URL click task',
            slug='no-url-click-task',
            category=self.category,
            points=5,
            verification_type='click_through',
        )
        with self.assertRaises(ValidationError) as cm:
            bad.clean()
        self.assertIn('action_url', cm.exception.message_dict)

    def test_cleaning_twitter_task_without_handle_fails(self):
        from django.core.exceptions import ValidationError

        bad = SocialTask(
            name='Bad twitter task',
            slug='bad-twitter-task',
            category=self.category,
            points=5,
            verification_type='twitter_follow',
            action_url='https://x.com/x',
        )
        with self.assertRaises(ValidationError) as cm:
            bad.full_clean()
        self.assertIn('target_handle', cm.exception.message_dict)

    def test_list_marks_task_locked_until_required_category_contribution_exists(self):
        self.click_task.eligibility_requirements = {
            'type': 'accepted_submittable_contribution',
            'category': 'task',
            'minimum': 1,
        }
        self.click_task.save()

        response = self.client.get('/api/v1/social-tasks/')
        by_slug = {t['slug']: t for t in response.json()}
        self.assertEqual(by_slug[self.click_task.slug]['status'], 'locked')
        self.assertFalse(by_slug[self.click_task.slug]['can_complete'])
        self.assertFalse(by_slug[self.click_task.slug]['eligibility']['eligible'])

        non_submittable_type = _make_contribution_type(
            self.category, 'community-internal', is_submittable=False
        )
        Contribution.objects.create(
            user=self.user,
            contribution_type=non_submittable_type,
            points=10,
            contribution_date=timezone.now(),
        )
        response = self.client.get('/api/v1/social-tasks/')
        by_slug = {t['slug']: t for t in response.json()}
        self.assertEqual(by_slug[self.click_task.slug]['status'], 'locked')

        submittable_type = _make_contribution_type(
            self.category, 'community-submittable', is_submittable=True
        )
        Contribution.objects.create(
            user=self.user,
            contribution_type=submittable_type,
            points=10,
            contribution_date=timezone.now(),
        )
        response = self.client.get('/api/v1/social-tasks/')
        by_slug = {t['slug']: t for t in response.json()}
        self.assertEqual(by_slug[self.click_task.slug]['status'], 'active')
        self.assertTrue(by_slug[self.click_task.slug]['can_complete'])

    def test_complete_locked_task_returns_403_before_verification(self):
        self.click_task.eligibility_requirements = {
            'type': 'accepted_submittable_contribution',
            'category': 'task',
            'minimum': 1,
        }
        self.click_task.save()

        response = self.client.post(f'/api/v1/social-tasks/{self.click_task.slug}/complete/')

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'eligibility_failed')
        self.assertFalse(
            SocialTaskCompletion.objects.filter(user=self.user, task=self.click_task).exists()
        )

    def test_validator_task_is_locked_for_view_only_non_validator(self):
        validator_category, _ = Category.objects.get_or_create(
            slug='validator', defaults={'name': 'Validator'}
        )
        task = SocialTask.objects.create(
            slug='validator-click-task',
            name='Validator Click Task',
            category=validator_category,
            points=25,
            verification_type='click_through',
            action_url='https://example.com/validator',
        )

        with override_settings(VALIDATOR_SECTION_VIEWER_USER_ID=self.user.id):
            list_response = self.client.get('/api/v1/social-tasks/?category=validator')
            complete_response = self.client.post(
                f'/api/v1/social-tasks/{task.slug}/complete/'
            )

        self.assertEqual(list_response.status_code, 200)
        listed_task = list_response.json()[0]
        self.assertEqual(listed_task['status'], 'locked')
        self.assertFalse(listed_task['can_complete'])
        self.assertEqual(listed_task['eligibility']['required_role'], 'validator')
        self.assertEqual(complete_response.status_code, 403)
        self.assertEqual(complete_response.json()['error'], 'eligibility_failed')
        self.assertFalse(
            SocialTaskCompletion.objects.filter(user=self.user, task=task).exists()
        )

    def test_validator_can_complete_validator_task(self):
        validator_category, _ = Category.objects.get_or_create(
            slug='validator', defaults={'name': 'Validator'}
        )
        task = SocialTask.objects.create(
            slug='validator-role-task',
            name='Validator Role Task',
            category=validator_category,
            points=25,
            verification_type='click_through',
            action_url='https://example.com/validator-role',
        )
        Validator.objects.create(user=self.user)

        response = self.client.post(f'/api/v1/social-tasks/{task.slug}/complete/')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['points_awarded'], 25)
        self.assertTrue(
            SocialTaskCompletion.objects.filter(user=self.user, task=task).exists()
        )

    def test_any_requirement_allows_community_points_or_accepted_contribution(self):
        self.click_task.eligibility_requirements = {
            'any': [
                {'type': 'community_points', 'minimum': 20},
                {
                    'type': 'accepted_submittable_contribution',
                    'category': 'task',
                    'minimum': 1,
                },
            ],
        }
        self.click_task.save()

        response = self.client.get('/api/v1/social-tasks/')
        by_slug = {t['slug']: t for t in response.json()}
        self.assertEqual(by_slug[self.click_task.slug]['status'], 'locked')

        non_submittable_type = _make_contribution_type(
            self.category,
            'community-points-only',
            is_submittable=False,
            points=25,
        )
        Contribution.objects.create(
            user=self.user,
            contribution_type=non_submittable_type,
            points=25,
            contribution_date=timezone.now(),
        )

        response = self.client.get('/api/v1/social-tasks/')
        by_slug = {t['slug']: t for t in response.json()}
        self.assertEqual(by_slug[self.click_task.slug]['status'], 'active')

    def test_clean_rejects_unknown_eligibility_rule(self):
        from django.core.exceptions import ValidationError

        bad = SocialTask(
            name='Bad gate task',
            slug='bad-gate-task',
            category=self.category,
            points=5,
            verification_type='click_through',
            action_url='https://example.com',
            eligibility_requirements={'type': 'made_up_gate'},
        )
        with self.assertRaises(ValidationError) as cm:
            bad.full_clean()
        self.assertIn('eligibility_requirements', cm.exception.message_dict)
