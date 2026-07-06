"""
Wallet address privacy: public API surfaces only expose truncated user
account addresses, address search is exact-full-address only (no substring
oracle), and user lookups accept id or full address.
"""
import re

from django.test import TestCase
from rest_framework.test import APIClient

from leaderboard.models import LeaderboardEntry
from users.models import User
from users.utils import is_full_address, truncate_address, user_lookup_kwargs

ALICE_ADDRESS = '0xaaaa567890abcdef1234567890abcdef1234aaaa'
BOB_ADDRESS = '0xbbbb567890abcdef1234567890abcdef1234bbbb'
FULL_ADDRESS_RE = re.compile(r'0x[0-9a-fA-F]{40}')


class AddressHelperTests(TestCase):
    def test_truncate_format_and_idempotence(self):
        truncated = truncate_address(ALICE_ADDRESS)
        self.assertEqual(truncated, '0xaaaa...aaaa')
        self.assertEqual(truncate_address(truncated), truncated)
        self.assertEqual(truncate_address(''), '')
        self.assertIsNone(truncate_address(None))

    def test_is_full_address(self):
        self.assertTrue(is_full_address(ALICE_ADDRESS))
        self.assertFalse(is_full_address(truncate_address(ALICE_ADDRESS)))
        self.assertFalse(is_full_address(ALICE_ADDRESS[:20]))

    def test_user_lookup_kwargs(self):
        self.assertEqual(user_lookup_kwargs('42'), {'pk': 42})
        self.assertEqual(
            user_lookup_kwargs(ALICE_ADDRESS),
            {'address__iexact': ALICE_ADDRESS},
        )
        self.assertEqual(user_lookup_kwargs('42', user_field='user'), {'user_id': 42})
        self.assertEqual(
            user_lookup_kwargs(ALICE_ADDRESS, user_field='user'),
            {'user__address__iexact': ALICE_ADDRESS},
        )


class AddressPrivacyAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.alice = User.objects.create_user(
            email='alice@example.com', password='pass',
            name='Alice', address=ALICE_ADDRESS, visible=True,
        )
        self.bob = User.objects.create_user(
            email='bob@example.com', password='pass',
            name='Bob', address=BOB_ADDRESS, visible=True,
        )
        LeaderboardEntry.objects.create(
            user=self.alice, type='validator', total_points=100, rank=1,
        )

    def _full_addresses_in(self, response):
        return FULL_ADDRESS_RE.findall(response.content.decode())

    def test_public_profile_returns_truncated_address(self):
        response = self.client.get(f'/api/v1/users/by-address/{ALICE_ADDRESS}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['address'], truncate_address(ALICE_ADDRESS))
        self.assertEqual(self._full_addresses_in(response), [])

    def test_profile_lookup_by_id(self):
        response = self.client.get(f'/api/v1/users/by-address/{self.alice.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], self.alice.id)

    def test_owner_sees_full_address(self):
        self.client.force_authenticate(user=self.alice)
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['address'], ALICE_ADDRESS)

    def test_other_authenticated_user_sees_truncated_address(self):
        self.client.force_authenticate(user=self.bob)
        response = self.client.get(f'/api/v1/users/by-address/{self.alice.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['address'], truncate_address(ALICE_ADDRESS))

    def test_search_rejects_address_prefix_probe(self):
        # Substring matching on addresses would let anyone reconstruct a
        # truncated address one character at a time.
        response = self.client.get('/api/v1/users/search/', {'q': ALICE_ADDRESS[:10]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_search_matches_exact_full_address(self):
        response = self.client.get('/api/v1/users/search/', {'q': ALICE_ADDRESS})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.alice.id)
        self.assertEqual(response.data[0]['address'], truncate_address(ALICE_ADDRESS))

    def test_search_by_name_still_works(self):
        response = self.client.get('/api/v1/users/search/', {'q': 'Alice'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(self._full_addresses_in(response), [])

    def test_public_leaderboard_has_no_full_addresses(self):
        response = self.client.get('/api/v1/leaderboard/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._full_addresses_in(response), [])
        entry = response.data[0]
        self.assertEqual(entry['user_details']['id'], self.alice.id)
        self.assertEqual(
            entry['user_details']['address'], truncate_address(ALICE_ADDRESS)
        )

    def test_leaderboard_user_address_param_accepts_id_and_address(self):
        by_address = self.client.get(
            '/api/v1/leaderboard/', {'user_address': ALICE_ADDRESS}
        )
        by_id = self.client.get(
            '/api/v1/leaderboard/', {'user_address': str(self.alice.id)}
        )
        self.assertEqual(by_address.status_code, 200)
        self.assertEqual(by_id.status_code, 200)
        self.assertEqual(len(by_address.data), 1)
        self.assertEqual(len(by_id.data), 1)
