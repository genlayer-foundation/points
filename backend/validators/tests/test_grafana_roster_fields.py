"""
Tests for the raw link/identity facts on the public Grafana roster endpoint
(/validators/wallets/grafana/): `linked` (wallet attributed to a portal
account) plus the raw on-chain identity fields (`moniker`, `logo_uri`,
`has_description`). Verdicts (what's missing) are computed dashboard-side —
the endpoint only ships facts.
"""

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from users.models import User
from validators.models import Validator, ValidatorWallet


class GrafanaRosterRawFieldTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='alice@example.com',
            password='pass',
            address='0xAAAAaaaaAAAAaaaaAAAAaaaaAAAAaaaaAAAAaaaa',
            name='Alice',
            visible=True,
        )
        self.operator = Validator.objects.create(user=self.user)

    def _rows_by_node(self):
        cache.clear()
        response = self.client.get('/api/v1/validators/wallets/grafana/?network=asimov')
        self.assertEqual(response.status_code, 200)
        return {row['node']: row for row in response.data}

    def test_linked_wallet_exposes_raw_identity_facts(self):
        ValidatorWallet.objects.create(
            address='0x1111111111111111111111111111111111111111',
            network='asimov',
            operator=self.operator,
            operator_address='0x2222222222222222222222222222222222222222',
            status='active',
            moniker='alice-node',
            logo_uri='https://example.com/logo.png',
            description='A well set up validator.',
        )
        row = self._rows_by_node()['0x1111111111111111111111111111111111111111']
        self.assertTrue(row['linked'])
        self.assertEqual(row['moniker'], 'alice-node')
        self.assertEqual(row['logo_uri'], 'https://example.com/logo.png')
        self.assertTrue(row['has_description'])

    def test_unset_identity_fields_come_through_raw(self):
        ValidatorWallet.objects.create(
            address='0x3333333333333333333333333333333333333333',
            network='asimov',
            operator=self.operator,
            operator_address='0x2222222222222222222222222222222222222222',
            status='active',
            moniker='',
            logo_uri='',
            description='',
        )
        row = self._rows_by_node()['0x3333333333333333333333333333333333333333']
        self.assertEqual(row['moniker'], '')
        self.assertEqual(row['logo_uri'], '')
        self.assertFalse(row['has_description'])

    def test_unlinked_wallet_is_not_linked(self):
        ValidatorWallet.objects.create(
            address='0x4444444444444444444444444444444444444444',
            network='asimov',
            operator=None,
            operator_address='0x5555555555555555555555555555555555555555',
            status='active',
        )
        row = self._rows_by_node()['0x4444444444444444444444444444444444444444']
        self.assertFalse(row['linked'])

    def test_linked_is_true_for_non_visible_operator_without_leaking_account(self):
        # `linked` is a bare boolean fact — it must hold for non-visible
        # operators while account/account_name stay hidden.
        bob = User.objects.create_user(
            email='bob@example.com',
            password='pass',
            address='0xBBBBbbbbBBBBbbbbBBBBbbbbBBBBbbbbBBBBbbbb',
            name='Bob',
            visible=False,
        )
        bob_operator = Validator.objects.create(user=bob)
        ValidatorWallet.objects.create(
            address='0x6666666666666666666666666666666666666666',
            network='asimov',
            operator=bob_operator,
            operator_address='0x7777777777777777777777777777777777777777',
            status='active',
        )
        row = self._rows_by_node()['0x6666666666666666666666666666666666666666']
        self.assertTrue(row['linked'])
        self.assertIsNone(row['account'])
        self.assertIsNone(row['account_name'])

    def test_missing_rows_carry_null_facts(self):
        # Graduated validator with no wallet on the network: the synthetic
        # 'missing' row has no wallet to describe — facts are null, not False.
        rows = self._rows_by_node()
        row = rows[self.user.address.lower()]
        self.assertEqual(row['status'], 'missing')
        self.assertIsNone(row['linked'])
        self.assertIsNone(row['moniker'])
        self.assertIsNone(row['logo_uri'])
        self.assertIsNone(row['has_description'])
