"""Telegram data is private: it must never leak to other viewers.

These tests are the contract for the profile-header Telegram connection:
- telegram_connection appears ONLY for the owner (and staff)
- telegram_handle (legacy field) is never in public payloads
- search never matches on telegram_handle
- the profile update endpoint no longer accepts telegram_handle
"""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from social_connections.models import TelegramConnection

User = get_user_model()


class TelegramPrivacyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            email='owner@test.com',
            address='0x1111111111111111111111111111111111111111',
            password='testpass123',
        )
        # Bypass the update serializer on purpose: legacy data may still
        # hold handles, and those must not leak either.
        User.objects.filter(pk=self.owner.pk).update(telegram_handle='leakyhandle')
        self.owner.refresh_from_db()
        TelegramConnection.objects.create(
            user=self.owner,
            platform_user_id='424242',
            platform_username='secretusername',
            linked_at=timezone.now(),
        )
        self.viewer = User.objects.create_user(
            email='viewer@test.com',
            address='0x2222222222222222222222222222222222222222',
            password='testpass123',
        )
        self.staff = User.objects.create_user(
            email='staff@test.com',
            address='0x3333333333333333333333333333333333333333',
            password='testpass123',
            is_staff=True,
        )

    def get_profile(self, as_user):
        if as_user is not None:
            self.client.force_authenticate(user=as_user)
        return self.client.get(f'/api/v1/users/by-address/{self.owner.address}/')

    def test_other_viewer_sees_no_telegram_data_at_all(self):
        response = self.get_profile(self.viewer)
        self.assertEqual(response.status_code, 200)

        self.assertNotIn('telegram_connection', response.data)
        self.assertNotIn('telegram_handle', response.data)
        # Belt and braces: no telegram value anywhere in the raw payload.
        raw = json.dumps(response.data, default=str)
        self.assertNotIn('secretusername', raw)
        self.assertNotIn('leakyhandle', raw)
        self.assertNotIn('424242', raw)

    def test_owner_sees_own_connection_on_me(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/v1/users/me/')

        self.assertEqual(response.status_code, 200)
        connection = response.data['telegram_connection']
        self.assertEqual(connection['platform_username'], 'secretusername')
        self.assertIn('notifications_enabled', connection)
        # The numeric Telegram id is never serialized, even for the owner.
        self.assertNotIn('platform_user_id', connection)
        self.assertNotIn('424242', json.dumps(response.data, default=str))

    def test_owner_sees_connection_on_own_public_profile(self):
        response = self.get_profile(self.owner)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['telegram_connection']['platform_username'], 'secretusername'
        )

    def test_staff_can_see_connection(self):
        response = self.get_profile(self.staff)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['telegram_connection']['platform_username'], 'secretusername'
        )

    def test_search_does_not_match_telegram_handle(self):
        response = self.client.get('/api/v1/users/search/', {'q': 'leakyhandle'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_profile_update_ignores_telegram_handle(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            '/api/v1/users/me/',
            {'name': 'New Name', 'telegram_handle': 'injected'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.name, 'New Name')
        self.assertEqual(self.owner.telegram_handle, 'leakyhandle')


class SignupTelegramHandleTests(TestCase):
    """The signup flow must not accept the removed telegram_handle either."""

    def test_pending_signup_profile_drops_telegram_handle(self):
        from ethereum_auth.email_verification import _clean_profile_data
        from ethereum_auth.views import PENDING_SIGNUP_PROFILE_FIELDS

        cleaned = _clean_profile_data({
            'name': 'New User',
            'telegram_handle': 'sneaky',
            'linkedin_handle': 'fine',
        })
        self.assertNotIn('telegram_handle', cleaned)
        self.assertEqual(cleaned['name'], 'New User')
        self.assertEqual(cleaned['linkedin_handle'], 'fine')
        self.assertNotIn('telegram_handle', PENDING_SIGNUP_PROFILE_FIELDS)
