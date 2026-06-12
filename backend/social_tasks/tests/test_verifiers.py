from unittest.mock import patch, MagicMock

from cryptography.fernet import Fernet, InvalidToken
from django.test import TestCase, override_settings
from django.utils import timezone
from requests.exceptions import Timeout

from contributions.models import Category
from social_connections.encryption import encrypt_token
from social_connections.models import DiscordConnection, GitHubConnection, TwitterConnection
from social_tasks import verifiers
from social_tasks.models import SocialTask
from social_tasks.sorsa_client import SorsaClient, SorsaError
from users.models import User


TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()


def _make_user(email):
    user = User(email=email, name='Test', visible=True, is_banned=False)
    user.set_password('x')
    user.save()
    return user


@override_settings(
    GITHUB_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY,
    SOCIAL_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY,
    DISCORD_GUILD_ID='guild_123',
)
class TwitterFollowVerifierTest(TestCase):
    def setUp(self):
        self.user = _make_user('alice@example.com')
        self.category, _ = Category.objects.get_or_create(
            slug='community', defaults={'name': 'Community'},
        )
        self.task = SocialTask.objects.create(
            slug='follow-genlayer',
            name='Follow @genlayer',
            category=self.category,
            points=10,
            verification_type='twitter_follow',
            target_handle='genlayer',
            action_url='https://x.com/genlayer',
            cta_text='Follow',
        )

    def test_no_connection_returns_not_linked(self):
        result = verifiers.verify(self.task, self.user)
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'social_account_not_linked')
        self.assertEqual(result.audit.get('platform'), 'twitter')

    def test_clean_rejects_profile_url_handle(self):
        from django.core.exceptions import ValidationError

        bad = SocialTask(
            name='Bad handle task',
            slug='bad-handle-task',
            category=self.category,
            points=5,
            verification_type='twitter_follow',
            target_handle='https://x.com/genlayer',
            action_url='https://x.com/genlayer',
        )
        with self.assertRaises(ValidationError) as cm:
            bad.clean()
        self.assertIn('target_handle', cm.exception.message_dict)

    def test_blank_action_url_derives_follow_intent(self):
        task = SocialTask(
            name='Derived URL task',
            slug='derived-url-task',
            category=self.category,
            points=5,
            verification_type='twitter_follow',
            target_handle='@genlayer',
        )
        task.clean()  # passes: derivable
        task.save()
        self.assertEqual(task.action_url, 'https://x.com/intent/follow?screen_name=genlayer')

    @patch('social_tasks.verifiers.twitter_follow.get_default_client')
    def test_following_returns_ok(self, mock_get_client):
        TwitterConnection.objects.create(
            user=self.user,
            platform_user_id='1',
            platform_username='alice',
            access_token=encrypt_token('tok'),
            linked_at=timezone.now(),
        )
        client = MagicMock()
        client.is_following.return_value = (True, {'is_following': True})
        mock_get_client.return_value = client

        result = verifiers.verify(self.task, self.user)

        self.assertTrue(result.ok)
        self.assertIsNone(result.error_code)
        client.is_following.assert_called_once_with('alice', 'genlayer')

    @patch('social_tasks.verifiers.twitter_follow.get_default_client')
    def test_not_following_returns_failed(self, mock_get_client):
        TwitterConnection.objects.create(
            user=self.user,
            platform_user_id='1',
            platform_username='alice',
            access_token=encrypt_token('tok'),
            linked_at=timezone.now(),
        )
        client = MagicMock()
        client.is_following.return_value = (False, {'is_following': False})
        mock_get_client.return_value = client

        result = verifiers.verify(self.task, self.user)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'verification_failed')

    @patch('social_tasks.verifiers.twitter_follow.get_default_client')
    def test_sorsa_error_returns_unavailable(self, mock_get_client):
        TwitterConnection.objects.create(
            user=self.user,
            platform_user_id='1',
            platform_username='alice',
            access_token=encrypt_token('tok'),
            linked_at=timezone.now(),
        )
        client = MagicMock()
        client.is_following.side_effect = SorsaError('boom')
        mock_get_client.return_value = client

        result = verifiers.verify(self.task, self.user)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'verification_unavailable')


@override_settings(
    GITHUB_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY,
    SOCIAL_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY,
    DISCORD_GUILD_ID='guild_123',
)
class DiscordVerifierTest(TestCase):
    def setUp(self):
        self.user = _make_user('bob@example.com')
        self.category, _ = Category.objects.get_or_create(
            slug='community', defaults={'name': 'Community'},
        )
        self.task = SocialTask.objects.create(
            slug='join-discord',
            name='Join Discord',
            category=self.category,
            points=10,
            verification_type='discord_guild_join',
            action_url='https://discord.gg/x',
            cta_text='Join',
        )

    def _link_discord(self, token_value='tok'):
        return DiscordConnection.objects.create(
            user=self.user,
            platform_user_id='1',
            platform_username='bob',
            access_token=encrypt_token(token_value),
            linked_at=timezone.now(),
        )

    @patch('social_tasks.verifiers.discord_guild_join.requests.get')
    def test_custom_guild_check_does_not_touch_main_guild_flag(self, mock_get):
        """Tasks targeting a campaign guild must not overwrite the cached
        main-guild membership flag on DiscordConnection."""
        connection = self._link_discord()
        connection.guild_member = True
        connection.save(update_fields=['guild_member'])

        self.task.target_guild_id = 'campaign_guild_999'
        self.task.save()

        # 404: user is not in the campaign guild. Without the main-guild gate
        # this used to flip the cached main-guild flag to False.
        mock_get.return_value = MagicMock(status_code=404)
        result = verifiers.verify(self.task, self.user)

        self.assertFalse(result.ok)
        self.assertEqual(result.audit['guild_id'], 'campaign_guild_999')
        connection.refresh_from_db()
        self.assertTrue(connection.guild_member)

    def test_no_connection_returns_not_linked(self):
        result = verifiers.verify(self.task, self.user)
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'social_account_not_linked')

    @patch('social_tasks.verifiers.discord_guild_join.requests.get')
    def test_member_returns_ok(self, mock_get):
        self._link_discord()
        mock_get.return_value = MagicMock(status_code=200)

        result = verifiers.verify(self.task, self.user)

        self.assertTrue(result.ok)
        self.assertIsNone(result.error_code)
        self.assertEqual(result.audit['guild_id'], 'guild_123')
        self.assertEqual(result.audit['status_code'], 200)
        mock_get.assert_called_once()

    @patch('social_tasks.verifiers.discord_guild_join.requests.get')
    def test_not_member_returns_failed(self, mock_get):
        self._link_discord()
        mock_get.return_value = MagicMock(status_code=404)

        result = verifiers.verify(self.task, self.user)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'verification_failed')

    @patch('social_tasks.verifiers.discord_guild_join.requests.get')
    def test_token_expired_returns_relink(self, mock_get):
        # No refresh_token on the connection, so the one-shot refresh attempt
        # raises ValueError immediately and re-link is the remedy.
        self._link_discord()
        mock_get.return_value = MagicMock(status_code=401)

        result = verifiers.verify(self.task, self.user)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'token_invalid_relink_required')
        self.assertEqual(result.audit['platform'], 'discord')

    @patch('social_connections.oauth_service.DiscordOAuthService.refresh_stored_access_token')
    @patch('social_tasks.verifiers.discord_guild_join.requests.get')
    def test_expired_token_refreshes_and_retries(self, mock_get, mock_refresh):
        """Routine 7-day token expiry must refresh transparently, not re-link."""
        self._link_discord()
        mock_get.side_effect = [MagicMock(status_code=401), MagicMock(status_code=200)]
        mock_refresh.return_value = 'fresh-token'

        result = verifiers.verify(self.task, self.user)

        self.assertTrue(result.ok)
        self.assertIsNone(result.error_code)
        mock_refresh.assert_called_once()
        self.assertEqual(mock_get.call_count, 2)
        # The retry must use the refreshed token.
        retry_headers = mock_get.call_args_list[1].kwargs['headers']
        self.assertEqual(retry_headers['Authorization'], 'Bearer fresh-token')

    @patch('social_connections.oauth_service.DiscordOAuthService.refresh_stored_access_token')
    @patch('social_tasks.verifiers.discord_guild_join.requests.get')
    def test_refresh_transport_error_returns_unavailable(self, mock_get, mock_refresh):
        """A transient failure of the refresh itself is retryable, not a re-link."""
        self._link_discord()
        mock_get.return_value = MagicMock(status_code=401)
        mock_refresh.side_effect = Timeout('discord token endpoint slow')

        result = verifiers.verify(self.task, self.user)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'verification_unavailable')

    def test_clean_rejects_invite_link_guild_id(self):
        from django.core.exceptions import ValidationError

        bad = SocialTask(
            name='Bad guild task',
            slug='bad-guild-task',
            category=self.category,
            points=5,
            verification_type='discord_guild_join',
            target_guild_id='discord.gg/genlayer',
            action_url='https://discord.gg/genlayer',
        )
        with self.assertRaises(ValidationError) as cm:
            bad.clean()
        self.assertIn('target_guild_id', cm.exception.message_dict)

    @patch('social_tasks.verifiers.discord_guild_join.requests.get')
    def test_forbidden_token_returns_relink(self, mock_get):
        self._link_discord()
        mock_get.return_value = MagicMock(status_code=403)

        result = verifiers.verify(self.task, self.user)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'token_invalid_relink_required')

    @patch('social_tasks.verifiers.discord_guild_join.requests.get')
    def test_service_error_returns_unavailable(self, mock_get):
        self._link_discord()
        mock_get.return_value = MagicMock(status_code=503)

        result = verifiers.verify(self.task, self.user)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'verification_unavailable')

    @patch('social_tasks.verifiers.discord_guild_join.requests.get')
    def test_rate_limited_returns_unavailable(self, mock_get):
        self._link_discord()
        mock_get.return_value = MagicMock(status_code=429)

        result = verifiers.verify(self.task, self.user)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'verification_unavailable')

    @patch('social_tasks.verifiers.discord_guild_join.requests.get',
           side_effect=Timeout('slow'))
    def test_transport_error_returns_unavailable(self, _mock):
        self._link_discord()

        result = verifiers.verify(self.task, self.user)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'verification_unavailable')
        self.assertEqual(result.audit['platform'], 'discord')

    @patch('social_tasks.verifiers.discord_guild_join.decrypt_token', side_effect=InvalidToken())
    def test_invalid_token_decrypt_returns_relink(self, _mock):
        DiscordConnection.objects.create(
            user=self.user,
            platform_user_id='1',
            platform_username='bob',
            access_token='broken',
            linked_at=timezone.now(),
        )

        result = verifiers.verify(self.task, self.user)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'token_invalid_relink_required')


@override_settings(
    GITHUB_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY,
    SOCIAL_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY,
)
class GitHubStarVerifierTest(TestCase):
    def setUp(self):
        self.user = _make_user('dev@example.com')
        self.category, _ = Category.objects.get_or_create(
            slug='builder', defaults={'name': 'Builder'},
        )
        self.task = SocialTask.objects.create(
            slug='star-points-repo',
            name='Star the Points repo',
            category=self.category,
            points=10,
            verification_type='github_star',
            target_repo='genlayer-foundation/points',
            action_url='https://github.com/genlayer-foundation/points',
            cta_text='Star',
        )

    def _link_github(self, token_value='tok'):
        return GitHubConnection.objects.create(
            user=self.user,
            platform_user_id='1',
            platform_username='dev',
            access_token=encrypt_token(token_value),
            linked_at=timezone.now(),
        )

    def test_no_connection_returns_not_linked(self):
        result = verifiers.verify(self.task, self.user)
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'social_account_not_linked')
        self.assertEqual(result.audit['platform'], 'github')

    def test_empty_token_returns_relink(self):
        GitHubConnection.objects.create(
            user=self.user,
            platform_user_id='1',
            platform_username='dev',
            access_token='',
            linked_at=timezone.now(),
        )
        result = verifiers.verify(self.task, self.user)
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'token_invalid_relink_required')

    @patch('social_tasks.verifiers.github_star.requests.get')
    def test_starred_returns_ok(self, mock_get):
        self._link_github()
        mock_get.return_value = MagicMock(status_code=204)

        result = verifiers.verify(self.task, self.user)

        self.assertTrue(result.ok)
        self.assertIsNone(result.error_code)
        self.assertEqual(result.audit['repo'], 'genlayer-foundation/points')
        self.assertEqual(result.audit['status_code'], 204)
        called_url = mock_get.call_args[0][0]
        self.assertIn('/user/starred/genlayer-foundation/points', called_url)

    @patch('social_tasks.verifiers.github_star.requests.get')
    def test_not_starred_returns_failed(self, mock_get):
        self._link_github()
        mock_get.return_value = MagicMock(status_code=404)

        result = verifiers.verify(self.task, self.user)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'verification_failed')

    @patch('social_tasks.verifiers.github_star.requests.get')
    def test_bad_credentials_returns_relink(self, mock_get):
        self._link_github()
        mock_get.return_value = MagicMock(status_code=401)

        result = verifiers.verify(self.task, self.user)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'token_invalid_relink_required')

    @patch('social_tasks.verifiers.github_star.requests.get')
    def test_rate_limited_returns_unavailable(self, mock_get):
        self._link_github()
        mock_get.return_value = MagicMock(status_code=403)

        result = verifiers.verify(self.task, self.user)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'verification_unavailable')

    @patch('social_tasks.verifiers.github_star.requests.get')
    def test_service_error_returns_unavailable(self, mock_get):
        self._link_github()
        mock_get.return_value = MagicMock(status_code=502)

        result = verifiers.verify(self.task, self.user)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'verification_unavailable')

    @patch(
        'social_tasks.verifiers.github_star.requests.get',
        side_effect=Timeout('slow'),
    )
    def test_transport_error_returns_unavailable(self, _mock):
        self._link_github()
        result = verifiers.verify(self.task, self.user)
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'verification_unavailable')

    @patch('social_tasks.verifiers.github_star.decrypt_token', side_effect=InvalidToken())
    def test_undecryptable_token_returns_relink(self, _mock):
        self._link_github()
        result = verifiers.verify(self.task, self.user)
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'token_invalid_relink_required')

    def test_clean_rejects_malformed_repo(self):
        from django.core.exceptions import ValidationError

        bad = SocialTask(
            name='Bad repo task',
            slug='bad-repo-task',
            category=self.category,
            points=5,
            verification_type='github_star',
            target_repo='https://github.com/owner/repo',
            action_url='https://github.com/owner/repo',
        )
        with self.assertRaises(ValidationError) as cm:
            bad.clean()
        self.assertIn('target_repo', cm.exception.message_dict)

    def test_blank_action_url_derives_repo_page(self):
        task = SocialTask(
            name='Derived repo URL task',
            slug='derived-repo-url-task',
            category=self.category,
            points=5,
            verification_type='github_star',
            target_repo='genlayer-foundation/points',
        )
        task.clean()  # passes: derivable
        task.save()
        self.assertEqual(task.action_url, 'https://github.com/genlayer-foundation/points')


class ClickThroughVerifierTest(TestCase):
    def test_always_succeeds(self):
        user = _make_user('c@example.com')
        category, _ = Category.objects.get_or_create(slug='community', defaults={'name': 'Community'})
        task = SocialTask.objects.create(
            slug='like-tweet',
            name='Like a tweet',
            category=category,
            points=5,
            verification_type='click_through',
            action_url='https://x.com/example/status/1',
            cta_text='Like',
        )
        result = verifiers.verify(task, user)
        self.assertTrue(result.ok)
        self.assertIsNone(result.error_code)
        self.assertEqual(result.audit['kind'], 'click_through')


class RegistryTest(TestCase):
    def test_choices_contain_all_registered(self):
        choices = verifiers.get_choices()
        slugs = {slug for slug, _label in choices}
        self.assertIn('twitter_follow', slugs)
        self.assertIn('discord_guild_join', slugs)
        self.assertIn('github_star', slugs)
        self.assertIn('click_through', slugs)

    def test_requires_verification_per_type(self):
        self.assertTrue(verifiers.requires_verification_for('twitter_follow'))
        self.assertTrue(verifiers.requires_verification_for('discord_guild_join'))
        self.assertTrue(verifiers.requires_verification_for('github_star'))
        self.assertFalse(verifiers.requires_verification_for('click_through'))

    def test_required_fields_per_type(self):
        self.assertEqual(verifiers.required_fields_for('twitter_follow'), ('target_handle',))
        self.assertEqual(verifiers.required_fields_for('discord_guild_join'), ())
        self.assertEqual(verifiers.required_fields_for('github_star'), ('target_repo',))
        self.assertEqual(verifiers.required_fields_for('click_through'), ())

    def test_required_connection_per_type(self):
        self.assertEqual(verifiers.required_connection_for('twitter_follow'), 'twitter')
        self.assertEqual(verifiers.required_connection_for('discord_guild_join'), 'discord')
        self.assertEqual(verifiers.required_connection_for('github_star'), 'github')
        self.assertIsNone(verifiers.required_connection_for('click_through'))

    def test_unknown_type_returns_unsupported(self):
        class FakeTask:
            verification_type = 'no_such_type'
        result = verifiers.verify(FakeTask(), None)
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, 'unsupported_verification_type')


class SorsaClientTest(TestCase):
    def _client(self):
        return SorsaClient(
            base_url='https://sorsa.test',
            api_key='key',
            timeout=1.0,
            follow_path='/check-follow',
        )

    def test_unconfigured_raises(self):
        client = SorsaClient(base_url='', api_key='', timeout=1.0)
        with self.assertRaises(SorsaError):
            client.is_following('a', 'b')

    @patch('requests.Session.post')
    def test_success_returns_bool_and_audit(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {'is_following': True})
        is_following, audit = self._client().is_following('@actor', '@target')
        self.assertTrue(is_following)
        self.assertEqual(audit['actor_handle'], 'actor')
        self.assertEqual(audit['target_handle'], 'target')
        self.assertEqual(audit['response'], {'is_following': True})

    @patch('requests.Session.post')
    def test_500_raises(self, mock_post):
        mock_post.return_value = MagicMock(status_code=500, json=lambda: {})
        with self.assertRaises(SorsaError):
            self._client().is_following('a', 'b')

    @patch('requests.Session.post')
    def test_unauthorized_raises(self, mock_post):
        mock_post.return_value = MagicMock(status_code=401, json=lambda: {'error': 'nope'})
        with self.assertRaises(SorsaError):
            self._client().is_following('a', 'b')

    @patch('requests.Session.post', side_effect=Timeout('slow'))
    def test_timeout_raises(self, _mock):
        with self.assertRaises(SorsaError):
            self._client().is_following('a', 'b')

    @patch('requests.Session.post')
    def test_non_boolean_is_following_raises(self, mock_post):
        """Schema drift at Sorsa must fail loudly, not read as 'not following'."""
        mock_post.return_value = MagicMock(
            status_code=200, json=lambda: {'following': True}
        )
        with self.assertRaises(SorsaError):
            self._client().is_following('a', 'b')
