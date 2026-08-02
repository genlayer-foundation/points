from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from service_accounts.testing import service_account_auth_headers
from social_connections.models import TelegramConnection
from validators.models import TelegramGroupBindCode, Validator

User = get_user_model()

ISSUE_URL = '/api/v1/validators/telegram-bind-codes/'
MINE_URL = '/api/v1/validators/telegram-bind-codes/mine/'
REDEEM_URL = '/api/v1/validators/telegram-bind-codes/redeem/'

GROUP_CHAT_ID = '-1001234567890'
TELEGRAM_UID = '424242424242'


def redeem_payload(code, **overrides):
    payload = {
        'code': code,
        'group_chat_id': GROUP_CHAT_ID,
        'telegram_uid': TELEGRAM_UID,
        'telegram_username': 'validator_ops',
    }
    payload.update(overrides)
    return payload


class TelegramBindCodeIssuanceTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='validator@example.com',
            password='testpass123',
            address='0x1111111111111111111111111111111111111111',
            name='Validator One',
        )
        self.validator = Validator.objects.create(user=self.user)

    def test_anonymous_cannot_issue(self):
        response = self.client.post(ISSUE_URL)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
        self.assertEqual(TelegramGroupBindCode.objects.count(), 0)

    def test_user_without_validator_profile_cannot_issue(self):
        plain_user = User.objects.create_user(
            email='plain@example.com',
            password='testpass123',
        )
        self.client.force_authenticate(user=plain_user)
        response = self.client.post(ISSUE_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(TelegramGroupBindCode.objects.count(), 0)

    def test_validator_issues_code_and_plaintext_is_returned_once(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(ISSUE_URL)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        code = response.data['code']
        self.assertTrue(code.startswith(TelegramGroupBindCode.CODE_PREFIX))
        self.assertEqual(response.data['status'], TelegramGroupBindCode.STATUS_ISSUED)

        bind_code = TelegramGroupBindCode.objects.get(id=response.data['id'])
        self.assertEqual(bind_code.validator, self.validator)
        self.assertEqual(bind_code.created_by, self.user)
        # Only the digest is stored, never the plaintext.
        self.assertEqual(bind_code.digest, TelegramGroupBindCode.hash_code(code))
        self.assertNotIn(code, [bind_code.identifier, bind_code.digest])
        # 48h expiry window.
        ttl = bind_code.expires_at - timezone.now()
        self.assertGreater(ttl, timedelta(hours=47))
        self.assertLessEqual(ttl, timedelta(hours=48))

    def test_validator_can_hold_multiple_active_codes(self):
        self.client.force_authenticate(user=self.user)
        first = self.client.post(ISSUE_URL)
        second = self.client.post(ISSUE_URL)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            TelegramGroupBindCode.objects.filter(
                validator=self.validator,
                status=TelegramGroupBindCode.STATUS_ISSUED,
            ).count(),
            2,
        )

    def test_mine_lists_codes_without_raw_secrets(self):
        self.client.force_authenticate(user=self.user)
        issued = self.client.post(ISSUE_URL)

        response = self.client.get(MINE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        entry = response.data[0]
        self.assertEqual(entry['id'], issued.data['id'])
        self.assertNotIn('code', entry)
        self.assertNotIn('digest', entry)

    def test_mine_only_returns_own_codes(self):
        other = User.objects.create_user(
            email='other-validator@example.com',
            password='testpass123',
        )
        other_validator = Validator.objects.create(user=other)
        TelegramGroupBindCode.issue(other_validator, other)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(MINE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_mine_reports_lazy_expiry(self):
        self.client.force_authenticate(user=self.user)
        bind_code, _ = TelegramGroupBindCode.issue(self.validator, self.user)
        TelegramGroupBindCode.objects.filter(pk=bind_code.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )

        response = self.client.get(MINE_URL)
        self.assertEqual(
            response.data[0]['status'], TelegramGroupBindCode.STATUS_EXPIRED
        )


class TelegramBindCodeRevokeTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='validator@example.com',
            password='testpass123',
        )
        self.validator = Validator.objects.create(user=self.user)
        self.bind_code, self.plaintext = TelegramGroupBindCode.issue(
            self.validator, self.user
        )
        self.client.force_authenticate(user=self.user)

    def _revoke(self, code_id):
        return self.client.post(
            f'/api/v1/validators/telegram-bind-codes/{code_id}/revoke/'
        )

    def test_owner_can_revoke_issued_code(self):
        response = self._revoke(self.bind_code.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], TelegramGroupBindCode.STATUS_REVOKED)
        self.bind_code.refresh_from_db()
        self.assertEqual(self.bind_code.status, TelegramGroupBindCode.STATUS_REVOKED)

    def test_revoked_code_cannot_be_redeemed(self):
        from rest_framework.test import APIClient

        self._revoke(self.bind_code.id)
        response = APIClient().post(
            REDEEM_URL,
            redeem_payload(self.plaintext),
            format='json',
            **service_account_auth_headers(['telegram_bind:redeem']),
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['code'], 'revoked')

    def test_redeemed_code_cannot_be_revoked(self):
        TelegramGroupBindCode.objects.filter(pk=self.bind_code.pk).update(
            status=TelegramGroupBindCode.STATUS_REDEEMED
        )
        response = self._revoke(self.bind_code.id)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_non_owner_cannot_revoke(self):
        other = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
        )
        self.client.force_authenticate(user=other)
        response = self._revoke(self.bind_code.id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.bind_code.refresh_from_db()
        self.assertEqual(self.bind_code.status, TelegramGroupBindCode.STATUS_ISSUED)


class TelegramBindCodeRedeemTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='validator@example.com',
            password='testpass123',
            name='Validator One',
        )
        self.validator = Validator.objects.create(user=self.user)
        self.bind_code, self.plaintext = TelegramGroupBindCode.issue(
            self.validator, self.user
        )
        self.auth = service_account_auth_headers(['telegram_bind:redeem'])

    def _redeem(self, payload, auth=None):
        return self.client.post(
            REDEEM_URL, payload, format='json', **(auth if auth is not None else self.auth)
        )

    def test_redeem_requires_service_account_token(self):
        response = self._redeem(redeem_payload(self.plaintext), auth={})
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_session_authenticated_user_cannot_redeem(self):
        self.client.force_authenticate(user=self.user)
        response = self._redeem(redeem_payload(self.plaintext), auth={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_redeem_requires_matching_scope(self):
        wrong_scope = service_account_auth_headers(
            ['ai_review:read'], name='wrong-scope-account'
        )
        response = self._redeem(redeem_payload(self.plaintext), auth=wrong_scope)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.bind_code.refresh_from_db()
        self.assertEqual(self.bind_code.status, TelegramGroupBindCode.STATUS_ISSUED)

    def test_successful_redeem_binds_group_and_upserts_connection(self):
        response = self._redeem(redeem_payload(self.plaintext))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['validator_id'], self.validator.id)
        self.assertEqual(response.data['group_chat_id'], GROUP_CHAT_ID)

        self.bind_code.refresh_from_db()
        self.assertEqual(self.bind_code.status, TelegramGroupBindCode.STATUS_REDEEMED)
        self.assertEqual(self.bind_code.redeemed_group_chat_id, GROUP_CHAT_ID)
        self.assertEqual(self.bind_code.redeemed_by_telegram_uid, TELEGRAM_UID)
        self.assertIsNotNone(self.bind_code.redeemed_at)

        connection = TelegramConnection.objects.get(user=self.user)
        self.assertEqual(connection.platform_user_id, TELEGRAM_UID)
        self.assertEqual(connection.platform_username, 'validator_ops')

    def test_redeem_is_single_use(self):
        first = self._redeem(redeem_payload(self.plaintext))
        second = self._redeem(
            redeem_payload(self.plaintext, group_chat_id='-1009999999999')
        )

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(second.data['code'], 'already_redeemed')
        self.bind_code.refresh_from_db()
        # The original binding is untouched.
        self.assertEqual(self.bind_code.redeemed_group_chat_id, GROUP_CHAT_ID)

    def test_second_code_binds_second_group_for_same_validator(self):
        second_code, second_plaintext = TelegramGroupBindCode.issue(
            self.validator, self.user
        )
        first = self._redeem(redeem_payload(self.plaintext))
        second = self._redeem(
            redeem_payload(second_plaintext, group_chat_id='-1009999999999')
        )

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        second_code.refresh_from_db()
        self.assertEqual(second_code.redeemed_group_chat_id, '-1009999999999')

    def test_expired_code_cannot_be_redeemed(self):
        TelegramGroupBindCode.objects.filter(pk=self.bind_code.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        response = self._redeem(redeem_payload(self.plaintext))

        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        self.assertEqual(response.data['code'], 'expired')
        self.bind_code.refresh_from_db()
        self.assertEqual(self.bind_code.status, TelegramGroupBindCode.STATUS_EXPIRED)
        self.assertFalse(TelegramConnection.objects.filter(user=self.user).exists())

    def test_unknown_code_is_rejected(self):
        response = self._redeem(redeem_payload('tgb_deadbeefdead_notarealsecret'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['code'], 'invalid_code')

    def test_tampered_secret_is_rejected(self):
        # Same identifier, wrong secret: the constant-time digest compare fails.
        identifier = self.bind_code.identifier
        response = self._redeem(
            redeem_payload(f'tgb_{identifier}_wrongsecretvalue')
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.bind_code.refresh_from_db()
        self.assertEqual(self.bind_code.status, TelegramGroupBindCode.STATUS_ISSUED)

    def test_malformed_payload_is_rejected(self):
        missing_code = self._redeem({
            'group_chat_id': GROUP_CHAT_ID,
            'telegram_uid': TELEGRAM_UID,
        })
        bad_chat = self._redeem(
            redeem_payload(self.plaintext, group_chat_id='not-a-chat-id')
        )
        bad_uid = self._redeem(
            redeem_payload(self.plaintext, telegram_uid='abc')
        )
        for response in (missing_code, bad_chat, bad_uid):
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.bind_code.refresh_from_db()
        self.assertEqual(self.bind_code.status, TelegramGroupBindCode.STATUS_ISSUED)

    def test_redeem_updates_existing_connection_and_keeps_username(self):
        TelegramConnection.objects.create(
            user=self.user,
            platform_user_id='111',
            platform_username='old_handle',
            linked_at=timezone.now() - timedelta(days=30),
        )
        response = self._redeem(
            redeem_payload(self.plaintext, telegram_username='')
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        connection = TelegramConnection.objects.get(user=self.user)
        self.assertEqual(connection.platform_user_id, TELEGRAM_UID)
        # No username in the payload never blanks the stored handle.
        self.assertEqual(connection.platform_username, 'old_handle')
