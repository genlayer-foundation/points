"""Telegram bot commands (handle_update driven directly) and the send utility."""
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from contributions.models import Category, ContributionType, Mission
from leaderboard.models import LeaderboardEntry
from social_connections.models import TelegramConnection, TelegramMessage
from social_connections.telegram import escape, send_telegram_message, truncate
from social_connections.telegram_bot import handle_update

User = get_user_model()

TELEGRAM_SETTINGS = {
    'TELEGRAM_BOT_TOKEN': 'test-token',
    'TELEGRAM_BOT_USERNAME': 'TestPortalBot',
    'TELEGRAM_WEBHOOK_SECRET': 's3cret',
}


def make_update(telegram_id, text, chat_type='private'):
    return {
        'update_id': 1,
        'message': {
            'message_id': 1,
            'chat': {'id': telegram_id, 'type': chat_type},
            'from': {'id': telegram_id, 'username': 'tester'},
            'text': text,
        },
    }


@override_settings(**TELEGRAM_SETTINGS)
class TelegramCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )
        self.connection = TelegramConnection.objects.create(
            user=self.user,
            platform_user_id='111',
            platform_username='tester',
            linked_at=timezone.now(),
        )
        patcher = patch(
            'social_connections.telegram_bot.send_telegram_message',
            return_value=(True, None, ''),
        )
        self.send_mock = patcher.start()
        self.addCleanup(patcher.stop)

    def last_reply(self):
        return self.send_mock.call_args[0][1]

    def test_group_chat_messages_ignored(self):
        handle_update(make_update(111, '/rank', chat_type='group'))
        self.send_mock.assert_not_called()
        self.assertEqual(TelegramMessage.objects.count(), 0)

    def test_non_message_updates_ignored(self):
        handle_update({'update_id': 2, 'edited_message': {'text': 'hi'}})
        self.send_mock.assert_not_called()

    def test_unlinked_sender_gets_link_prompt(self):
        handle_update(make_update(999, '/rank'))
        self.assertIn("isn't linked", self.last_reply())

    def test_inbound_messages_are_logged(self):
        handle_update(make_update(111, 'hello there'))
        inbound = TelegramMessage.objects.get(direction=TelegramMessage.DIRECTION_IN)
        self.assertEqual(inbound.text, 'hello there')
        self.assertEqual(inbound.connection, self.connection)

    def test_rank_with_entries(self):
        LeaderboardEntry.objects.create(user=self.user, type='builder', total_points=3450, rank=12)
        LeaderboardEntry.objects.create(user=self.user, type='validator', total_points=100, rank=None)

        handle_update(make_update(111, '/rank'))

        reply = self.last_reply()
        self.assertIn('Builder', reply)
        self.assertIn('#12', reply)
        self.assertIn('3,450', reply)
        self.assertIn('unranked', reply)

    def test_rank_without_entries(self):
        handle_update(make_update(111, '/rank'))
        self.assertIn('No leaderboard entries yet', self.last_reply())

    def test_points_without_entries(self):
        handle_update(make_update(111, '/points'))
        self.assertIn('No points yet', self.last_reply())

    def test_command_with_bot_suffix_routes(self):
        handle_update(make_update(111, '/rank@TestPortalBot'))
        self.assertIn('No leaderboard entries yet', self.last_reply())

    def test_missions_lists_active_and_escapes_html(self):
        category = Category.objects.create(name='Test', slug='test', description='Test')
        contribution_type = ContributionType.objects.create(
            name='Type', slug='type', description='d', category=category,
            min_points=1, max_points=10,
        )
        Mission.objects.create(
            name='Break <b>&stuff',
            description='d',
            contribution_type=contribution_type,
        )
        Mission.objects.create(
            name='Expired mission',
            description='d',
            contribution_type=contribution_type,
            end_date=timezone.now() - timedelta(days=1),
        )

        handle_update(make_update(111, '/missions'))

        reply = self.last_reply()
        self.assertIn('Break &lt;b&gt;&amp;stuff', reply)
        self.assertNotIn('Break <b>', reply)
        self.assertNotIn('Expired mission', reply)
        self.assertIn(f'/contribution-type/{contribution_type.id}', reply)

    def test_missions_empty(self):
        handle_update(make_update(111, '/missions'))
        self.assertIn('No active missions', self.last_reply())

    def test_mute_and_unmute(self):
        handle_update(make_update(111, '/mute'))
        self.connection.refresh_from_db()
        self.assertFalse(self.connection.notifications_enabled)

        handle_update(make_update(111, '/unmute'))
        self.connection.refresh_from_db()
        self.assertTrue(self.connection.notifications_enabled)

    def test_inbound_message_clears_blocked_flag(self):
        """Receiving any message proves the user unblocked the bot, so
        delivery eligibility (and /unmute) must be able to recover."""
        self.connection.blocked_at = timezone.now()
        self.connection.notifications_enabled = False
        self.connection.save(update_fields=['blocked_at', 'notifications_enabled'])

        handle_update(make_update(111, '/unmute'))

        self.connection.refresh_from_db()
        self.assertIsNone(self.connection.blocked_at)
        self.assertTrue(self.connection.notifications_enabled)

    def test_unlink_deletes_connection_and_pending_rows(self):
        TelegramMessage.objects.create(
            direction=TelegramMessage.DIRECTION_OUT,
            connection=self.connection,
            chat_id='111',
            text='queued',
            status=TelegramMessage.STATUS_PENDING,
        )
        handle_update(make_update(111, '/unlink'))

        self.assertFalse(TelegramConnection.objects.filter(user=self.user).exists())
        self.assertFalse(
            TelegramMessage.objects.filter(status=TelegramMessage.STATUS_PENDING).exists()
        )
        self.assertIn('unlinked', self.last_reply().lower())

    def test_unknown_command_shows_help(self):
        handle_update(make_update(111, '/bogus'))
        self.assertIn('/help', self.last_reply())


@override_settings(**TELEGRAM_SETTINGS)
class SendTelegramMessageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )
        self.connection = TelegramConnection.objects.create(
            user=self.user,
            platform_user_id='111',
            platform_username='tester',
            linked_at=timezone.now(),
        )

    def mock_response(self, status_code, payload=None, text=''):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        if payload is not None:
            response.json.return_value = payload
        else:
            response.json.side_effect = ValueError()
        return response

    def test_escape(self):
        self.assertEqual(escape('<b>&'), '&lt;b&gt;&amp;')

    def test_truncate_caps_at_limit(self):
        self.assertEqual(len(truncate('x' * 5000)), 4096)
        self.assertEqual(truncate('short'), 'short')

    def test_success(self):
        with patch('social_connections.telegram.requests.post') as post:
            post.return_value = self.mock_response(200, {'ok': True})
            ok, retry_after, description = send_telegram_message('111', 'hi')
        self.assertTrue(ok)
        self.assertIsNone(retry_after)
        self.assertEqual(post.call_args.kwargs['json']['parse_mode'], 'HTML')

    def test_blocked_marks_connection(self):
        with patch('social_connections.telegram.requests.post') as post:
            post.return_value = self.mock_response(
                403, {'ok': False, 'description': 'Forbidden: bot was blocked by the user'}
            )
            ok, retry_after, description = send_telegram_message(
                '111', 'hi', connection=self.connection
            )
        self.assertFalse(ok)
        self.assertEqual(description, 'blocked')
        self.connection.refresh_from_db()
        self.assertIsNotNone(self.connection.blocked_at)
        self.assertFalse(self.connection.notifications_enabled)

    def test_rate_limited_returns_retry_after(self):
        with patch('social_connections.telegram.requests.post') as post:
            post.return_value = self.mock_response(
                429, {'ok': False, 'parameters': {'retry_after': 17}}
            )
            ok, retry_after, description = send_telegram_message('111', 'hi')
        self.assertFalse(ok)
        self.assertEqual(retry_after, 17)
        self.assertEqual(description, 'rate_limited')

    def test_reply_markup_included_in_payload(self):
        markup = {'inline_keyboard': [[{'text': 'Open', 'url': 'https://example.com'}]]}
        with patch('social_connections.telegram.requests.post') as post:
            post.return_value = self.mock_response(200, {'ok': True})
            send_telegram_message('111', 'hi', reply_markup=markup)
        self.assertEqual(post.call_args.kwargs['json']['reply_markup'], markup)

    def test_rejected_button_retries_without_reply_markup(self):
        bad = self.mock_response(
            400, {'ok': False, 'description': 'Bad Request: BUTTON_URL_INVALID'}
        )
        good = self.mock_response(200, {'ok': True})
        markup = {'inline_keyboard': [[{'text': 'Open', 'url': 'not-a-url'}]]}
        with patch('social_connections.telegram.requests.post', side_effect=[bad, good]) as post:
            ok, _, _ = send_telegram_message('111', 'hi', reply_markup=markup)
        self.assertTrue(ok)
        self.assertEqual(post.call_count, 2)
        self.assertNotIn('reply_markup', post.call_args.kwargs['json'])

    def test_parse_error_retries_as_plain_text(self):
        bad = self.mock_response(
            400, {'ok': False, 'description': "Bad Request: can't parse entities: ..."}
        )
        good = self.mock_response(200, {'ok': True})
        with patch('social_connections.telegram.requests.post', side_effect=[bad, good]) as post:
            ok, _, _ = send_telegram_message('111', '<broken')
        self.assertTrue(ok)
        self.assertEqual(post.call_count, 2)
        self.assertNotIn('parse_mode', post.call_args.kwargs['json'])

    def test_oversize_text_truncated_in_payload(self):
        with patch('social_connections.telegram.requests.post') as post:
            post.return_value = self.mock_response(200, {'ok': True})
            send_telegram_message('111', 'x' * 6000)
        self.assertLessEqual(len(post.call_args.kwargs['json']['text']), 4096)

    @override_settings(TELEGRAM_BOT_TOKEN='')
    def test_missing_token_fails_without_request(self):
        with patch('social_connections.telegram.requests.post') as post:
            ok, _, description = send_telegram_message('111', 'hi')
        self.assertFalse(ok)
        self.assertEqual(description, 'bot_token_not_configured')
        post.assert_not_called()
