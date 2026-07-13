"""Telegram account-linking flow: link-token endpoint, webhook auth, /start."""
import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from social_connections.models import (
    PendingOAuthState,
    TelegramConnection,
    TelegramMessage,
)

User = get_user_model()

WEBHOOK_URL = '/api/webhooks/telegram/'
LINK_TOKEN_URL = '/api/v1/users/telegram/link-token/'
DISCONNECT_URL = '/api/v1/users/telegram/disconnect/'

TELEGRAM_SETTINGS = {
    'TELEGRAM_BOT_TOKEN': 'test-token',
    'TELEGRAM_BOT_USERNAME': 'TestPortalBot',
    'TELEGRAM_WEBHOOK_SECRET': 's3cret',
}


def make_user(email, address):
    return User.objects.create_user(email=email, address=address, password='testpass123')


def start_update(telegram_id, text, username='tester'):
    return {
        'update_id': 1,
        'message': {
            'message_id': 1,
            'chat': {'id': telegram_id, 'type': 'private'},
            'from': {'id': telegram_id, 'username': username},
            'text': text,
        },
    }


@override_settings(**TELEGRAM_SETTINGS)
class TelegramLinkTokenTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user('user@test.com', '0x1234567890123456789012345678901234567890')

    def test_requires_authentication(self):
        response = self.client.post(LINK_TOKEN_URL)
        self.assertIn(response.status_code, (401, 403))

    def test_returns_deep_link_and_creates_pending_state(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(LINK_TOKEN_URL)

        self.assertEqual(response.status_code, 200)
        deep_link = response.data['deep_link']
        self.assertTrue(deep_link.startswith('https://t.me/TestPortalBot?start='))

        token = deep_link.split('start=')[1]
        self.assertRegex(token, r'^[A-Za-z0-9_-]{20,64}$')
        pending = PendingOAuthState.objects.get(state_id=token)
        self.assertEqual(pending.platform, 'telegram')
        self.assertEqual(pending.user, self.user)

    @override_settings(TELEGRAM_BOT_USERNAME='')
    def test_unconfigured_bot_returns_503(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(LINK_TOKEN_URL)
        self.assertEqual(response.status_code, 503)


@override_settings(**TELEGRAM_SETTINGS)
class TelegramWebhookAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def post_webhook(self, secret=None, payload=None):
        kwargs = {}
        if secret is not None:
            kwargs['HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN'] = secret
        return self.client.post(
            WEBHOOK_URL,
            data=json.dumps(payload or {}),
            content_type='application/json',
            **kwargs,
        )

    def test_missing_secret_rejected(self):
        self.assertEqual(self.post_webhook().status_code, 403)

    def test_wrong_secret_rejected(self):
        self.assertEqual(self.post_webhook(secret='wrong').status_code, 403)

    @override_settings(TELEGRAM_WEBHOOK_SECRET='')
    def test_empty_configured_secret_rejects_everything(self):
        self.assertEqual(self.post_webhook(secret='').status_code, 403)

    def test_correct_secret_returns_ok(self):
        response = self.post_webhook(secret='s3cret')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'ok': True})

    def test_get_not_allowed(self):
        response = self.client.get(WEBHOOK_URL)
        self.assertEqual(response.status_code, 405)


@override_settings(**TELEGRAM_SETTINGS)
class TelegramStartLinkTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user('user@test.com', '0x1234567890123456789012345678901234567890')
        self.other = make_user('other@test.com', '0x9999999999999999999999999999999999999999')
        patcher = patch(
            'social_connections.telegram_bot.send_telegram_message',
            return_value=(True, None, ''),
        )
        self.send_mock = patcher.start()
        self.addCleanup(patcher.stop)

    def make_token(self, user=None):
        pending = PendingOAuthState.objects.create(
            state_id=f'token-for-{(user or self.user).pk}-{PendingOAuthState.objects.count()}',
            platform='telegram',
            user=user or self.user,
        )
        return pending.state_id

    def post_start(self, telegram_id, token, username='tester'):
        return self.client.post(
            WEBHOOK_URL,
            data=json.dumps(start_update(telegram_id, f'/start {token}', username=username)),
            content_type='application/json',
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN='s3cret',
        )

    def last_reply(self):
        return self.send_mock.call_args[0][1]

    def test_start_with_valid_token_links_account(self):
        token = self.make_token()
        response = self.post_start(111, token)

        self.assertEqual(response.status_code, 200)
        connection = TelegramConnection.objects.get(user=self.user)
        self.assertEqual(connection.platform_user_id, '111')
        self.assertEqual(connection.platform_username, 'tester')
        self.assertIsNotNone(connection.linked_at)
        self.assertTrue(connection.notifications_enabled)
        self.assertIsNone(connection.blocked_at)
        # Inbound update and outbound welcome are both logged.
        self.assertEqual(
            TelegramMessage.objects.filter(direction=TelegramMessage.DIRECTION_IN).count(), 1
        )
        self.assertEqual(
            TelegramMessage.objects.filter(direction=TelegramMessage.DIRECTION_OUT).count(), 1
        )

    def test_token_cannot_be_reused(self):
        token = self.make_token()
        self.post_start(111, token)
        self.post_start(222, token)

        self.assertEqual(TelegramConnection.objects.count(), 1)
        self.assertEqual(TelegramConnection.objects.get().platform_user_id, '111')
        self.assertIn('expired', self.last_reply().lower())

    def test_expired_token_rejected(self):
        token = self.make_token()
        PendingOAuthState.objects.filter(state_id=token).update(
            created_at=timezone.now() - timedelta(minutes=30)
        )
        self.post_start(111, token)

        self.assertFalse(TelegramConnection.objects.exists())
        self.assertIn('expired', self.last_reply().lower())

    def test_telegram_account_linked_to_other_user_rejected(self):
        TelegramConnection.objects.create(
            user=self.other,
            platform_user_id='111',
            platform_username='taken',
            linked_at=timezone.now(),
        )
        token = self.make_token(self.user)
        self.post_start(111, token)

        self.assertFalse(TelegramConnection.objects.filter(user=self.user).exists())
        self.assertEqual(
            TelegramConnection.objects.get(user=self.other).platform_username, 'taken'
        )
        self.assertIn('different portal account', self.last_reply())

    def test_relink_replaces_account_and_clears_blocked(self):
        TelegramConnection.objects.create(
            user=self.user,
            platform_user_id='111',
            platform_username='old',
            linked_at=timezone.now(),
            notifications_enabled=False,
            blocked_at=timezone.now(),
        )
        token = self.make_token()
        self.post_start(222, token, username='newname')

        connection = TelegramConnection.objects.get(user=self.user)
        self.assertEqual(connection.platform_user_id, '222')
        self.assertEqual(connection.platform_username, 'newname')
        self.assertTrue(connection.notifications_enabled)
        self.assertIsNone(connection.blocked_at)

    def test_start_without_token_prompts_portal_link(self):
        response = self.client.post(
            WEBHOOK_URL,
            data=json.dumps(start_update(111, '/start')),
            content_type='application/json',
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN='s3cret',
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TelegramConnection.objects.exists())
        self.send_mock.assert_called_once()


@override_settings(**TELEGRAM_SETTINGS)
class TelegramDisconnectTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user('user@test.com', '0x1234567890123456789012345678901234567890')

    def test_disconnect_deletes_connection_and_pending_outbox(self):
        connection = TelegramConnection.objects.create(
            user=self.user,
            platform_user_id='111',
            platform_username='tester',
            linked_at=timezone.now(),
        )
        TelegramMessage.objects.create(
            direction=TelegramMessage.DIRECTION_OUT,
            connection=connection,
            chat_id='111',
            text='queued',
            status=TelegramMessage.STATUS_PENDING,
        )
        sent = TelegramMessage.objects.create(
            direction=TelegramMessage.DIRECTION_OUT,
            connection=connection,
            chat_id='111',
            text='already sent',
            status=TelegramMessage.STATUS_SENT,
            sent_at=timezone.now(),
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(DISCONNECT_URL)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(TelegramConnection.objects.filter(user=self.user).exists())
        self.assertFalse(
            TelegramMessage.objects.filter(status=TelegramMessage.STATUS_PENDING).exists()
        )
        # Sent history is kept (connection FK nulled).
        sent.refresh_from_db()
        self.assertIsNone(sent.connection)

        # Idempotent.
        self.assertEqual(self.client.post(DISCONNECT_URL).status_code, 200)


@override_settings(**TELEGRAM_SETTINGS)
class TelegramIdentityUniquenessTests(TestCase):
    """One Telegram account can only link to one portal user: the /start
    pre-check is racy on its own, so the DB constraint is the real guard."""

    def test_platform_user_id_is_unique(self):
        from django.db import IntegrityError, transaction
        user_a = make_user('a@test.com', '0x1111111111111111111111111111111111111111')
        user_b = make_user('b@test.com', '0x2222222222222222222222222222222222222222')
        TelegramConnection.objects.create(
            user=user_a,
            platform_user_id='111',
            platform_username='a',
            linked_at=timezone.now(),
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            TelegramConnection.objects.create(
                user=user_b,
                platform_user_id='111',
                platform_username='b',
                linked_at=timezone.now(),
            )

    def test_start_race_loser_gets_friendly_reply(self):
        from unittest.mock import patch
        from django.db import IntegrityError
        user = make_user('a@test.com', '0x1111111111111111111111111111111111111111')
        PendingOAuthState.objects.create(state_id='race-token', platform='telegram', user=user)

        with patch(
            'social_connections.telegram_bot.send_telegram_message',
            return_value=(True, None, ''),
        ) as send_mock, patch.object(
            TelegramConnection.objects, 'update_or_create', side_effect=IntegrityError
        ):
            from social_connections.telegram_bot import handle_update
            handle_update(start_update(111, '/start race-token'))

        self.assertFalse(TelegramConnection.objects.exists())
        self.assertIn('different portal account', send_mock.call_args[0][1])


@override_settings(**TELEGRAM_SETTINGS)
class TelegramTokenLifetimeTests(TestCase):
    """OAuth flows sweep expired states with a 10-minute lifetime; Telegram
    tokens live 15. Cleanup must be platform-scoped or an unrelated OAuth
    initiation would expire Telegram tokens five minutes early."""

    def test_platform_scoped_cleanup_spares_other_platforms(self):
        user = make_user('user@test.com', '0x1234567890123456789012345678901234567890')
        for platform in ('telegram', 'github'):
            pending = PendingOAuthState.objects.create(
                state_id=f'{platform}-token', platform=platform, user=user,
            )
            PendingOAuthState.objects.filter(pk=pending.pk).update(
                created_at=timezone.now() - timedelta(minutes=12)
            )

        PendingOAuthState.cleanup_old(minutes=10, platform='github')

        self.assertFalse(PendingOAuthState.objects.filter(platform='github').exists())
        self.assertTrue(PendingOAuthState.objects.filter(platform='telegram').exists())
        # A 12-minute-old Telegram token is still redeemable.
        self.assertIsNotNone(
            PendingOAuthState.consume_deep_link('telegram-token', 'telegram', max_age_minutes=15)
        )


@override_settings(**TELEGRAM_SETTINGS)
class TelegramInactiveUserTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user('user@test.com', '0x1234567890123456789012345678901234567890')
        patcher = patch(
            'social_connections.telegram_bot.send_telegram_message',
            return_value=(True, None, ''),
        )
        self.send_mock = patcher.start()
        self.addCleanup(patcher.stop)

    def test_start_token_for_deactivated_user_rejected(self):
        pending = PendingOAuthState.objects.create(
            state_id='inactive-token', platform='telegram', user=self.user,
        )
        User.objects.filter(pk=self.user.pk).update(is_active=False)

        self.client.post(
            WEBHOOK_URL,
            data=json.dumps(start_update(111, f'/start {pending.state_id}')),
            content_type='application/json',
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN='s3cret',
        )

        self.assertFalse(TelegramConnection.objects.exists())
        self.assertIn('deactivated', self.send_mock.call_args[0][1])

    def test_commands_from_deactivated_user_resolve_as_unlinked(self):
        from social_connections.telegram_bot import handle_update
        from leaderboard.models import LeaderboardEntry
        TelegramConnection.objects.create(
            user=self.user,
            platform_user_id='111',
            platform_username='tester',
            linked_at=timezone.now(),
        )
        LeaderboardEntry.objects.create(user=self.user, type='builder', total_points=999, rank=1)
        User.objects.filter(pk=self.user.pk).update(is_active=False)

        handle_update(start_update(111, '/rank'))

        reply = self.send_mock.call_args[0][1]
        self.assertIn("isn't linked", reply)
        self.assertNotIn('999', reply)
